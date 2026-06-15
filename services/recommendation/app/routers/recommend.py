"""
NARA — Recommendation Router
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import LocalSession
from app.core.security import get_current_user
from app.core.model_loader import model_store
from app.pipeline.ranker import get_recommendations, set_dish_candidates

log      = logging.getLogger("nara.recommendation.router")
router   = APIRouter(prefix="/v1/recommend", tags=["recommend"])
settings = get_settings()


async def fetch_food_graph(user_id: str, token: str) -> dict:
    """Fetch user food graph from user-intelligence service."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.user_intelligence_url}/v1/food-graph",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        log.warning(f"Food graph fetch failed: {e}")
    return {}


async def fetch_user_profile(user_id: str, token: str) -> dict:
    """Fetch user health profile from user-intelligence service."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.user_intelligence_url}/v1/health-profile",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        log.warning(f"Health profile fetch failed: {e}")
    return {}


async def ensure_dishes_loaded():
    """Load dishes from KB if not already loaded."""
    from app.pipeline.ranker import DISH_CANDIDATES
    if DISH_CANDIDATES:
        return
    async with LocalSession() as db:
        result = await db.execute(text("""
            SELECT dish_name, cuisine_type, is_veg, allergens,
                   glycemic_index, glycemic_load,
                   per_serving->>'calories_kcal' as calories_kcal,
                   per_serving->>'protein_g'     as protein_g,
                   per_serving->>'carbs_g'        as carbs_g,
                   per_serving->>'fat_g'          as fat_g,
                   per_serving->>'fiber_g'        as fiber_g
            FROM nutrition_kb
            WHERE per_serving != '{}'
        """))
        rows = result.mappings().all()
        dishes = []
        for r in rows:
            d = dict(r)
            for key in ["calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g"]:
                try:
                    d[key] = float(d[key]) if d[key] else None
                except (TypeError, ValueError):
                    d[key] = None
            dishes.append(d)
        set_dish_candidates(dishes)
        log.info(f"Loaded {len(dishes)} dishes from KB")


@router.get("/")
async def recommend(
    lat: Optional[float] = Query(None, description="User latitude"),
    lng: Optional[float] = Query(None, description="User longitude"),
    occasion: Optional[str] = Query(None, description="breakfast/lunch/snack/dinner"),
    n: int = Query(10, ge=1, le=20),
    current_user: dict = Depends(get_current_user),
    token: str = Depends(lambda c=Depends(__import__('fastapi').security.HTTPBearer()): c.credentials),
):
    """
    Get personalised dish recommendations for the current user.
    Uses trained ML models to rank dishes based on:
    - User health profile and conditions
    - Food graph (eating history)
    - Current context (time, occasion, location)
    """
    await ensure_dishes_loaded()

    user_id = current_user["user_id"]

    # Fetch user data
    food_graph = await fetch_food_graph(user_id, token)
    profile    = await fetch_user_profile(user_id, token)

    # Build context
    now = datetime.now()
    context = {
        "hour":             now.hour,
        "day_of_week":      now.weekday(),
        "month":            now.month,
        "is_weekend":       now.weekday() >= 5,
        "season":           _get_season(now.month),
        "stress_level":     "medium",
        "budget_multiplier":1.0,
        "lat":              lat,
        "lng":              lng,
        "occasion":         occasion,
    }

    # Build user dict from profile
    conditions   = profile.get("declared_conditions", [])
    restrictions = profile.get("dietary_restrictions", [])
    user = {
        "user_id":             user_id,
        "age":                 profile.get("age", 30),
        "bmi":                 _calc_bmi(profile),
        "health_literacy":     0.6,
        "habit_strength":      0.6,
        "income_tier":         "medium",
        "region":              "north",
        "is_vegetarian":       "vegetarian" in restrictions,
        "conditions":          "|".join(conditions) if isinstance(conditions, list) else conditions,
        "dietary_restrictions":"|".join(restrictions) if isinstance(restrictions, list) else restrictions,
    }

    recommendations = get_recommendations(user, context, food_graph, n=n)

    return {
        "user_id":        user_id,
        "occasion":       context["occasion"],
        "count":          len(recommendations),
        "recommendations":recommendations,
        "models_used": {
            "ranker":        model_store.ranker_type,
            "health_scorer": model_store.health_type,
            "occasion":      model_store.occasion_type,
        },
    }


@router.get("/cold-start")
async def cold_start_recommend(
    birthplace_state: str = Query("Karnataka"),
    religion: str = Query("hindu"),
    age: int = Query(28),
    gender: str = Query("male"),
    is_vegetarian: bool = Query(False),
    conditions: str = Query(""),
    n: int = Query(10),
):
    """
    Recommendations for new users with no meal history.
    Uses demographic embedding / Wide&Deep model.
    """
    await ensure_dishes_loaded()

    user = {
        "user_id":        "new_user",
        "age":             age,
        "bmi":             23.0,
        "health_literacy": 0.5,
        "habit_strength":  0.6,
        "income_tier":     "medium",
        "region":          _state_to_region(birthplace_state),
        "is_vegetarian":   is_vegetarian,
        "conditions":      conditions,
        "dietary_restrictions": "vegetarian" if is_vegetarian else "",
        "religion":        religion,
    }
    context = {
        "hour":             datetime.now().hour,
        "day_of_week":      datetime.now().weekday(),
        "month":            datetime.now().month,
        "is_weekend":       datetime.now().weekday() >= 5,
        "season":           _get_season(datetime.now().month),
        "stress_level":     "medium",
        "budget_multiplier":1.0,
    }

    recommendations = get_recommendations(user, context, {}, n=n)
    return {
        "user_type":      "cold_start",
        "count":          len(recommendations),
        "recommendations":recommendations,
    }


@router.get("/nearby-restaurants")
async def nearby_restaurants(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_km: float = Query(5.0),
    cuisine: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Find nearby restaurants using PostGIS.
    Returns restaurants within radius sorted by distance.
    """
    async with LocalSession() as db:
        cuisine_filter = "AND :cuisine = ANY(ARRAY(SELECT jsonb_array_elements_text(cuisine_types)))" if cuisine else ""
        result = await db.execute(
            text(f"""
                SELECT
                    id, name, cuisine_types, area, avg_cost_for_two,
                    rating, delivery_enabled, delivery_time_min,
                    ST_Distance(
                        location::geography,
                        ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                    ) / 1000 AS distance_km
                FROM restaurants
                WHERE
                    is_active = TRUE
                    AND ST_DWithin(
                        location::geography,
                        ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                        :radius_m
                    )
                    {cuisine_filter}
                ORDER BY distance_km
                LIMIT 20
            """),
            {
                "lat": lat, "lng": lng,
                "radius_m": radius_km * 1000,
                "cuisine": cuisine,
            }
        )
        rows = result.mappings().all()
        restaurants = [dict(r) for r in rows]
        for r in restaurants:
            r["distance_km"] = round(float(r["distance_km"]), 2)
        return {"count": len(restaurants), "restaurants": restaurants}


def _get_season(month: int) -> str:
    m = {1: "winter", 2: "winter", 3: "summer_onset", 4: "summer",
         5: "summer", 6: "monsoon_onset", 7: "monsoon", 8: "monsoon",
         9: "monsoon_end", 10: "autumn", 11: "winter_onset", 12: "winter"}
    return m.get(month, "summer")


def _calc_bmi(profile: dict) -> float:
    w = profile.get("weight_kg", 0)
    h = profile.get("height_cm", 0)
    if w and h:
        return round(w / ((h / 100) ** 2), 1)
    return 23.0


def _state_to_region(state: str) -> str:
    south = ["Tamil Nadu", "Karnataka", "Kerala", "Andhra Pradesh", "Telangana"]
    west  = ["Maharashtra", "Gujarat", "Goa", "Rajasthan"]
    east  = ["West Bengal", "Odisha", "Assam"]
    if state in south:
        return "south"
    if state in west:
        return "west"
    if state in east:
        return "east"
    return "north"