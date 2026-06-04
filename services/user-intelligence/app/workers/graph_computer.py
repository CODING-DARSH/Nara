"""
Food Graph Computer
Aggregates raw food_events + food_event_nutrition into the FoodGraph model.
Called on cache miss and by the Kafka worker on new enriched events.
"""
from uuid import UUID
from datetime import datetime, timedelta, timezone
from typing import Optional
from collections import defaultdict

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import FoodGraph


async def compute_food_graph(
    user_id: UUID,
    db: AsyncSession,
) -> Optional[FoodGraph]:
    """
    Full recompute of food graph from food_events + food_event_nutrition.
    Returns updated FoodGraph ORM object saved to DB.
    """
    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    # Raw SQL to avoid importing food_events model (lives in ingestion service)
    # Cross-service: read from shared Neon DB tables
    from sqlalchemy import text

    query = text("""
        SELECT
            fe.id,
            fe.occurred_at,
            fe.meal_context,
            fe.raw_input,
            fen.dish_name,
            fen.cuisine_type,
            fen.estimated_nutrition,
            fen.confidence_score
        FROM food_events fe
        LEFT JOIN food_event_nutrition fen ON fen.event_id = fe.id
        WHERE fe.user_id = :user_id
          AND fe.occurred_at >= :cutoff_30d
          AND fe.enrichment_status = 'done'
        ORDER BY fe.occurred_at DESC
    """)

    result = await db.execute(query, {"user_id": str(user_id), "cutoff_30d": cutoff_30d})
    rows = result.fetchall()

    if not rows:
        return None

    # ── Aggregate nutritional windows ──────────────────────────
    def empty_nutrition():
        return defaultdict(float)

    agg_24h = empty_nutrition()
    agg_7d = empty_nutrition()
    agg_30d = empty_nutrition()

    cuisine_counts = defaultdict(int)
    dish_counts = defaultdict(int)
    meal_hours = []
    total = 0

    for row in rows:
        nutrition = row.estimated_nutrition or {}
        occurred_at = row.occurred_at
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)

        # Add to appropriate windows
        if occurred_at >= cutoff_24h:
            for k, v in nutrition.items():
                agg_24h[k] += v or 0

        if occurred_at >= cutoff_7d:
            for k, v in nutrition.items():
                agg_7d[k] += v or 0

        # All rows are within 30d
        for k, v in nutrition.items():
            agg_30d[k] += v or 0

        # Cuisine affinity
        if row.cuisine_type:
            cuisine_counts[row.cuisine_type] += 1

        # Dish frequency
        if row.dish_name:
            dish_counts[row.dish_name] += 1

        # Meal timing
        meal_hours.append(occurred_at.hour)
        total += 1

    # ── Normalise cuisine affinity to 0-1 scores ───────────────
    max_cuisine = max(cuisine_counts.values(), default=1)
    cuisine_affinity = {k: round(v / max_cuisine, 2) for k, v in cuisine_counts.items()}

    # ── Top dishes ────────────────────────────────────────────
    top_dishes = [
        {"dish": dish, "count": count}
        for dish, count in sorted(dish_counts.items(), key=lambda x: -x[1])[:10]
    ]

    # ── Meal timing patterns ───────────────────────────────────
    meal_timing = {}
    if meal_hours:
        breakfast_hours = [h for h in meal_hours if 5 <= h <= 10]
        lunch_hours = [h for h in meal_hours if 11 <= h <= 15]
        dinner_hours = [h for h in meal_hours if 18 <= h <= 23]

        if breakfast_hours:
            meal_timing["breakfast_avg_hour"] = round(sum(breakfast_hours) / len(breakfast_hours), 1)
        if lunch_hours:
            meal_timing["lunch_avg_hour"] = round(sum(lunch_hours) / len(lunch_hours), 1)
        if dinner_hours:
            meal_timing["dinner_avg_hour"] = round(sum(dinner_hours) / len(dinner_hours), 1)

    # ── Detect patterns ────────────────────────────────────────
    detected = {}

    breakfast_count = sum(1 for h in meal_hours if 5 <= h <= 10)
    if total > 7 and breakfast_count / total < 0.3:
        detected["skips_breakfast"] = True

    if agg_7d.get("calories", 0) > 0:
        dinner_cal_ratio = sum(
            (row.estimated_nutrition or {}).get("calories", 0)
            for row in rows
            if row.occurred_at.hour >= 18
        ) / max(agg_7d["calories"], 1)
        if dinner_cal_ratio > 0.45:
            detected["heavy_dinner"] = True

    # ── Save or update FoodGraph ───────────────────────────────
    result2 = await db.execute(
        select(FoodGraph).where(FoodGraph.user_id == user_id)
    )
    graph = result2.scalar_one_or_none()

    if not graph:
        graph = FoodGraph(user_id=user_id)
        db.add(graph)

    graph.last_24h = dict(agg_24h)
    graph.last_7d = dict(agg_7d)
    graph.last_30d = dict(agg_30d)
    graph.cuisine_affinity = cuisine_affinity
    graph.top_dishes = top_dishes
    graph.meal_timing_patterns = meal_timing
    graph.detected_patterns = detected
    graph.total_meals_logged = total
    graph.last_computed_at = now
    graph.updated_at = now

    await db.commit()
    await db.refresh(graph)
    return graph
