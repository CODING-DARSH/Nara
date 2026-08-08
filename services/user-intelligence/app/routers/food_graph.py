from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_neon_db
from app.core.redis import get_redis
from app.dependencies.auth import CurrentUserId
from app.models.intelligence import FoodGraph, UserHealthProfile
from app.schemas.intelligence import FoodGraphResponse, InsightResponse, NutritionalGap
from app.workers.graph_computer import compute_food_graph

import json

router = APIRouter(prefix="/v1/food-graph", tags=["food-graph"])


@router.get("", response_model=FoodGraphResponse)
async def get_food_graph(
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_neon_db),
):
    """
    Get the user's food graph.
    Checks Redis cache first — cache hit returns in <5ms.
    Cache miss recomputes from food_events table.
    """
    redis = await get_redis()
    cache_key = f"foodgraph:{current_user_id}"

    # Try cache first
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        try:
            return FoodGraphResponse(**data)
        except Exception:
            # Cached entry predates a schema change (e.g. total_meals_pending
            # added after this was cached) and is missing a now-required
            # field. Don't crash the request over a stale cache — drop it
            # and fall through to a fresh DB read/recompute below. This is
            # exactly the failure mode that hit total_meals_pending here;
            # this guard means future schema additions degrade gracefully
            # instead of 500ing every cached user until TTL expiry.
            await redis.delete(cache_key)

    # Cache miss — fetch or compute
    result = await db.execute(
        select(FoodGraph).where(FoodGraph.user_id == current_user_id)
    )
    graph = result.scalar_one_or_none()

    if not graph:
        # First time — compute from scratch
        graph = await compute_food_graph(current_user_id, db)
        if not graph:
            # No food events yet — return empty graph
            return FoodGraphResponse(
                user_id=current_user_id,
                last_24h={},
                last_7d={},
                last_30d={},
                nutritional_gaps=[],
                cuisine_affinity={},
                meal_timing_patterns={},
                top_dishes=[],
                detected_patterns={},
                total_meals_logged=0,
                total_meals_pending=0,
                last_computed_at=None,
            )

    response = FoodGraphResponse(
        user_id=graph.user_id,
        last_24h=graph.last_24h,
        last_7d=graph.last_7d,
        last_30d=graph.last_30d,
        nutritional_gaps=graph.nutritional_gaps,
        cuisine_affinity=graph.cuisine_affinity,
        meal_timing_patterns=graph.meal_timing_patterns,
        top_dishes=graph.top_dishes,
        detected_patterns=graph.detected_patterns,
        total_meals_logged=graph.total_meals_logged,
        total_meals_pending=graph.total_meals_pending,
        last_computed_at=graph.last_computed_at,
    )

    # Cache it
    from app.core.config import get_settings
    settings = get_settings()
    await redis.setex(cache_key, settings.food_graph_cache_ttl, response.model_dump_json())

    return response


@router.get("/insights", response_model=InsightResponse)
async def get_nutritional_insights(
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_neon_db),
):
    """
    Analyse food graph against health profile goals.
    Returns ranked nutritional gaps with severity and plain-English hints.
    These hints feed directly into the recommendation engine.
    """
    # Get food graph
    result = await db.execute(
        select(FoodGraph).where(FoodGraph.user_id == current_user_id)
    )
    graph = result.scalar_one_or_none()

    # Get health profile
    profile_result = await db.execute(
        select(UserHealthProfile).where(
            UserHealthProfile.user_id == current_user_id,
            UserHealthProfile.is_active == True,
        )
    )
    profile = profile_result.scalar_one_or_none()

    if not graph or not profile:
        return InsightResponse(
            gaps=[],
            summary="Not enough data yet. Log some meals to get insights.",
            recommendations_hint=[]
        )

    goals = profile.nutritional_goals
    last_7d = graph.last_7d
    gaps = []
    hints = []

    # Analyse each nutritional goal
    nutrient_labels = {
        "target_protein_g": ("protein_g", "protein"),
        "target_fiber_g": ("fiber_g", "fiber"),
        "target_carbs_g": ("carbs_g", "carbohydrates"),
        "target_fat_g": ("fat_g", "healthy fats"),
    }

    for goal_key, (data_key, label) in nutrient_labels.items():
        if goal_key not in goals:
            continue

        target = goals[goal_key]
        actual = last_7d.get(data_key, 0) / 7  # daily average

        if actual < target * 0.75:
            deficit_pct = (target - actual) / target
            consecutive = _count_consecutive_deficit_days(
                graph, data_key, target
            )

            severity = "high" if deficit_pct > 0.4 else "medium" if deficit_pct > 0.2 else "low"

            gaps.append(NutritionalGap(
                nutrient=data_key,
                target=target,
                actual_avg=round(actual, 1),
                deficit_pct=round(deficit_pct, 2),
                consecutive_days=consecutive,
                severity=severity,
            ))

            if severity == "high":
                hints.append(f"Prioritize high-{label} dishes — significantly below target for {consecutive} days")
            else:
                hints.append(f"Consider {label}-rich options — slightly below weekly target")

    # Check max limits (sugar, sodium, calories)
    limit_checks = [
        ("max_sugar_g", "sugar_g", "sugar", True),
        ("max_sodium_mg", "sodium_mg", "sodium", True),
        ("max_calories", "calories", "calories", True),
    ]
    for goal_key, data_key, label, is_max in limit_checks:
        if goal_key not in goals:
            continue
        limit = goals[goal_key]
        actual = last_7d.get(data_key, 0) / 7
        if actual > limit * 1.1:
            hints.append(f"Reduce {label} intake — averaging {round(actual)} vs target {limit} daily")

    # Condition-specific hints
    conditions = profile.declared_conditions
    if "prediabetes" in conditions or "type2_diabetes" in conditions:
        hints.append("Low glycemic load options preferred — monitor carb sources")
    if "hypertension" in conditions:
        hints.append("Low sodium dishes recommended")
    if "high_cholesterol" in conditions:
        hints.append("Avoid deep-fried options — prefer steamed, grilled, or baked")

    # Build summary
    if not gaps:
        summary = "Nutritional balance looks good this week. Keep it up."
    elif len(gaps) == 1:
        summary = f"One nutritional gap detected: {gaps[0].nutrient.replace('_g','').replace('_',' ')}. Recommendations adjusted."
    else:
        gap_names = ", ".join(g.nutrient.replace("_g", "").replace("_", " ") for g in gaps[:3])
        summary = f"{len(gaps)} gaps detected this week: {gap_names}. Recommendations prioritize these."

    return InsightResponse(gaps=gaps, summary=summary, recommendations_hint=hints)


@router.post("/recompute", response_model=FoodGraphResponse)
async def recompute_food_graph(
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_neon_db),
):
    """Force recompute food graph from raw food events. Invalidates cache."""
    redis = await get_redis()
    await redis.delete(f"foodgraph:{current_user_id}")

    graph = await compute_food_graph(current_user_id, db)
    if not graph:
        raise HTTPException(status_code=404, detail="No food events found to compute graph from")

    return FoodGraphResponse(
        user_id=graph.user_id,
        last_24h=graph.last_24h,
        last_7d=graph.last_7d,
        last_30d=graph.last_30d,
        nutritional_gaps=graph.nutritional_gaps,
        cuisine_affinity=graph.cuisine_affinity,
        meal_timing_patterns=graph.meal_timing_patterns,
        top_dishes=graph.top_dishes,
        detected_patterns=graph.detected_patterns,
        total_meals_logged=graph.total_meals_logged,
        total_meals_pending=graph.total_meals_pending,
        last_computed_at=graph.last_computed_at,
    )


def _count_consecutive_deficit_days(graph: FoodGraph, nutrient: str, target: float) -> int:
    """Count how many consecutive days the user has been below target."""
    # In a full implementation this reads daily breakdown from food_events
    # For now returns a reasonable estimate from weekly data
    weekly_avg = graph.last_7d.get(nutrient, 0) / 7
    if weekly_avg < target * 0.5:
        return 7
    elif weekly_avg < target * 0.7:
        return 5
    elif weekly_avg < target * 0.85:
        return 3
    return 1
