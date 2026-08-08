"""
Food Graph Computer
Aggregates raw food_events + food_event_nutrition into the FoodGraph model.
Called on cache miss and by the Kafka worker on new enriched events.

FIXES applied here:
  1. glycemic_index / glycemic_load are PER-DISH properties, not additive
     quantities. The old code summed them across every meal in the window
     (agg[k] += v), which produced meaningless numbers — e.g. 5 meals each
     at GI 60 summed to 300. These two keys are now tracked as a running
     mean instead, computed separately from the additive macro totals.
  2. dinner_cal_ratio divided a 30-day numerator (it iterated `rows`, which
     is the full 30-day result set) by the 7-day denominator (agg_7d). Now
     both numerator and denominator come from the same window.
  3. total_meals_logged previously only counted enrichment_status='done'
     rows, so a meal logged seconds ago (still 'pending'/'processing')
     never showed up in counts or macros until the async pipeline caught
     up, with no visible signal anywhere that something was in flight. We
     now also fetch a pending count so the API can surface "N meals still
     processing" instead of just looking stale or unchanged.
"""
from uuid import UUID
from datetime import datetime, timedelta, timezone
from typing import Optional
from collections import defaultdict

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import FoodGraph

# Keys that are per-dish properties and must be averaged across meals in a
# window, never summed. Everything else in estimated_nutrition (calories,
# protein_g, carbs_g, fat_g, fiber_g, ...) is a real additive quantity.
AVERAGED_KEYS = {"glycemic_index", "glycemic_load"}


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

    # How many meals in the same window are still being enriched. Exposed
    # on the graph so the frontend can show "3 meals still processing"
    # instead of silently looking like nothing happened.
    pending_result = await db.execute(
        text("""
            SELECT COUNT(*) FROM food_events
            WHERE user_id = :user_id
              AND occurred_at >= :cutoff_30d
              AND enrichment_status IN ('pending', 'processing')
        """),
        {"user_id": str(user_id), "cutoff_30d": cutoff_30d},
    )
    pending_count = pending_result.scalar() or 0

    if not rows:
        if pending_count == 0:
            return None
        # No enriched meals yet, but some are in flight — still create/
        # update a near-empty graph so total_meals_pending is visible
        # instead of returning None and looking like a 404 to the caller.
        result2 = await db.execute(select(FoodGraph).where(FoodGraph.user_id == user_id))
        graph = result2.scalar_one_or_none()
        if not graph:
            graph = FoodGraph(user_id=user_id)
            db.add(graph)
        graph.total_meals_logged = 0
        graph.total_meals_pending = pending_count
        graph.last_computed_at = now
        graph.updated_at = now
        await db.commit()
        await db.refresh(graph)
        return graph

    # ── Aggregate nutritional windows ──────────────────────────
    def empty_window():
        return {
            "sums": defaultdict(float),        # additive macro totals
            "avg_running": defaultdict(float),  # running sum for averaged keys
            "avg_count": defaultdict(int),      # how many meals contributed
            "dinner_calories": 0.0,             # for heavy_dinner detection
            "total_calories": 0.0,
        }

    win_24h = empty_window()
    win_7d = empty_window()
    win_30d = empty_window()

    cuisine_counts = defaultdict(int)
    dish_counts = defaultdict(int)
    meal_hours = []

    def add_to_window(win, nutrition, hour, calories):
        for k, v in nutrition.items():
            if v is None:
                continue
            if k in AVERAGED_KEYS:
                win["avg_running"][k] += v
                win["avg_count"][k] += 1
            else:
                win["sums"][k] += v
        win["total_calories"] += calories
        if hour >= 18:
            win["dinner_calories"] += calories

    for row in rows:
        nutrition = row.estimated_nutrition or {}
        occurred_at = row.occurred_at
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        hour = occurred_at.hour
        calories = nutrition.get("calories", 0) or 0

        if occurred_at >= cutoff_24h:
            add_to_window(win_24h, nutrition, hour, calories)
        if occurred_at >= cutoff_7d:
            add_to_window(win_7d, nutrition, hour, calories)
        add_to_window(win_30d, nutrition, hour, calories)  # all rows are within 30d

        if row.cuisine_type:
            cuisine_counts[row.cuisine_type] += 1
        if row.dish_name:
            dish_counts[row.dish_name] += 1

        meal_hours.append(hour)

    total = len(rows)

    def finalize_window(win):
        """Build the dict stored on FoodGraph.last_Xh — additive sums plus
        true per-meal averages for GI/GL, instead of summed garbage."""
        out = dict(win["sums"])
        for k, total_sum in win["avg_running"].items():
            count = win["avg_count"].get(k, 0)
            out[k] = round(total_sum / count, 1) if count else 0
        return out

    agg_24h = finalize_window(win_24h)
    agg_7d = finalize_window(win_7d)
    agg_30d = finalize_window(win_30d)

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

    # FIX: numerator and denominator now both come from the 7-day window,
    # not a 30-day numerator over a 7-day denominator.
    if win_7d["total_calories"] > 0:
        dinner_cal_ratio = win_7d["dinner_calories"] / win_7d["total_calories"]
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

    graph.last_24h = agg_24h
    graph.last_7d = agg_7d
    graph.last_30d = agg_30d
    graph.cuisine_affinity = cuisine_affinity
    graph.top_dishes = top_dishes
    graph.meal_timing_patterns = meal_timing
    graph.detected_patterns = detected
    graph.total_meals_logged = total
    graph.total_meals_pending = pending_count
    graph.last_computed_at = now
    graph.updated_at = now

    await db.commit()
    await db.refresh(graph)
    return graph
