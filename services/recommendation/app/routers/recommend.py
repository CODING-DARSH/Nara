"""
NARA — Recommendation Router (FIXED)
Fixes applied:
  2. occasion query param now forces STRICT filtering (occasion_explicit=True)
     so tabs in the UI actually change results instead of returning the
     same list regardless of selected tab.
  1. Dish-level occasion_tags (not cuisine-level) are now loaded from KB
     and used for real per-dish filtering — fixes "same food suggested
     for breakfast/lunch/dinner".
  5. New endpoint /v1/recommend/with-restaurants combines dish
     recommendations with nearby restaurants matched by cuisine_type,
     using the existing PostGIS-backed restaurants table.
"""
import json
import logging
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPBearer
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import LocalSession
from app.core.security import get_current_user
from app.core.model_loader import model_store
from app.pipeline.ranker import get_recommendations, set_dish_candidates

log      = logging.getLogger("nara.recommendation.router")
router   = APIRouter(prefix="/v1/recommend", tags=["recommend"])
settings = get_settings()
bearer   = HTTPBearer()


async def fetch_food_graph(token: str) -> dict:
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


async def fetch_user_profile(token: str) -> dict:
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
    from app.pipeline.ranker import DISH_CANDIDATES
    if DISH_CANDIDATES:
        return
    async with LocalSession() as db:
        result = await db.execute(text("""
            SELECT dish_name, cuisine_type, is_veg, allergens, occasion_tags,
                   glycemic_index, glycemic_load,
                   per_serving->>'calories_kcal' as calories_kcal,
                   per_serving->>'protein_g'     as protein_g,
                   per_serving->>'carbs_g'        as carbs_g,
                   per_serving->>'fat_g'          as fat_g,
                   per_serving->>'fiber_g'        as fiber_g
            FROM nutrition_kb
            WHERE per_serving != '{}'
        """))
        rows   = result.mappings().all()
        dishes = []
        for r in rows:
            d = dict(r)
            for key in ["calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g"]:
                try:
                    d[key] = float(d[key]) if d[key] else None
                except (TypeError, ValueError):
                    d[key] = None
            # occasion_tags comes back as a list already (JSONB), but guard
            # against it arriving as a raw string from older rows.
            tags = d.get("occasion_tags")
            if isinstance(tags, str):
                try:
                    d["occasion_tags"] = json.loads(tags)
                except Exception:
                    d["occasion_tags"] = []
            elif tags is None:
                d["occasion_tags"] = []
            dishes.append(d)
        set_dish_candidates(dishes)
        log.info(f"Loaded {len(dishes)} dishes from KB (with occasion_tags)")


def _build_context(now: datetime, lat, lng, occasion, profile: dict | None = None):
    """
    FIX: stress_level was hardcoded to "medium" for every request. We don't
    have a real-time stress signal (would need wearable integration or an
    in-app check-in), so the honest fix is: use the user's self-reported
    stress_level from their health profile if they've set one, and fall
    back to "medium" only when truly absent — not silently override a real
    value the user provided.
    """
    profile = profile or {}
    return {
        "hour":              now.hour,
        "day_of_week":       now.weekday(),
        "month":             now.month,
        "is_weekend":        now.weekday() >= 5,
        "season":            _get_season(now.month),
        "stress_level":      profile.get("stress_level") or "medium",
        "budget_multiplier": 1.0,
        "lat":               lat,
        "lng":               lng,
        "occasion":          occasion,
    }


def _compute_health_literacy(profile: dict, food_graph: dict) -> float:
    """
    No direct signal exists for this (would need explicit quiz or repeated
    override tracking). Honest proxy until real interaction data exists:
    profile completeness — someone who filled in conditions, restrictions,
    goals, and budget has demonstrated more engagement with health framing
    than someone who skipped onboarding. Bounded 0.3-0.9, never a flat
    constant for everyone.
    """
    fields_present = sum([
        bool(profile.get("declared_conditions")),
        bool(profile.get("dietary_restrictions")),
        bool(profile.get("nutritional_goals")),
        bool(profile.get("allergies")),
        bool(profile.get("activity_level") and profile.get("activity_level") != "moderately_active"),
    ])
    base = 0.3 + (fields_present / 5) * 0.6
    return round(min(0.9, base), 2)


def _compute_habit_strength(food_graph: dict) -> float:
    """
    Real proxy from actual logging behavior instead of a flat constant.
    Uses total_meals_logged (30d window) as a consistency signal: someone
    logging ~3 meals/day for 30 days (90 logs) is a strong, habitual user;
    someone with 1-2 total logs has shown almost no habit yet. This is a
    genuine behavioral signal, not a guess — it directly reflects what the
    user has actually done, unlike the old flat 0.6 for every user.
    """
    total = food_graph.get("total_meals_logged", 0) or 0
    if total <= 0:
        return 0.3  # no behavior yet — neutral-low, not the old flat 0.6
    # 90 logs/30d (~3/day) treated as "fully habitual" ceiling
    return round(min(0.95, 0.3 + (total / 90) * 0.65), 2)


def _build_user(profile: dict, user_id: str, food_graph: dict | None = None) -> dict:
    food_graph = food_graph or {}
    conditions   = profile.get("declared_conditions", [])
    restrictions = profile.get("dietary_restrictions", [])
    return {
        "user_id":              user_id,
        "age":                  profile.get("age", 30),
        "bmi":                  _calc_bmi(profile),
        # FIX: these four were flat constants for every user. Two now come
        # straight from the health profile (real, user-stated facts, with
        # an honest "unknown" fallback rather than a fabricated default);
        # two are computed from real behavioral signal since no direct
        # field for them exists or could exist without new infrastructure.
        "health_literacy":      _compute_health_literacy(profile, food_graph),
        "habit_strength":       _compute_habit_strength(food_graph),
        "income_tier":          profile.get("income_tier") or "unknown",
        "region":               profile.get("region") or "unknown",
        "occupation":           profile.get("occupation"),
        "living_situation":     profile.get("living_situation"),
        "is_wfh":               profile.get("is_wfh"),
        "is_vegetarian":        "vegetarian" in restrictions,
        "conditions":           "|".join(conditions) if isinstance(conditions, list) else conditions,
        "dietary_restrictions": "|".join(restrictions) if isinstance(restrictions, list) else restrictions,
    }


@router.get("/")
async def recommend(
    lat: Optional[float]      = Query(None, description="User latitude"),
    lng: Optional[float]      = Query(None, description="User longitude"),
    occasion: Optional[str]   = Query(None, description="breakfast/lunch/snack/dinner — when set, filtering is STRICT"),
    n: int                    = Query(10, ge=1, le=20),
    current_user: dict        = Depends(get_current_user),
    credentials               = Depends(bearer),
):
    await ensure_dishes_loaded()

    user_id = current_user["user_id"]
    token   = credentials.credentials

    food_graph = await fetch_food_graph(token)
    profile    = await fetch_user_profile(token)

    now     = datetime.now()
    context = _build_context(now, lat, lng, occasion, profile)
    user    = _build_user(profile, user_id, food_graph)

    # FIX 2: occasion_explicit=True whenever the caller passed an occasion
    # (i.e. the user tapped a specific tab in the UI) -> strict filtering,
    # no silent fallback to the unfiltered list.
    recommendations = get_recommendations(
        user, context, food_graph, n=n,
        occasion_explicit=bool(occasion),
    )

    return {
        "user_id":         user_id,
        "occasion":        context["occasion"],
        "occasion_strict": bool(occasion),
        "count":           len(recommendations),
        "recommendations": recommendations,
        "models_used": {
            "ranker":        model_store.ranker_type,
            "health_scorer": model_store.health_type,
            "occasion":      model_store.occasion_type,
            "reorder":       model_store.reorder_type,
        },
    }


@router.get("/with-restaurants")
async def recommend_with_restaurants(
    lat: float                = Query(...),
    lng: float                 = Query(...),
    occasion: Optional[str]    = Query(None),
    radius_km: float           = Query(5.0),
    n: int                     = Query(10, ge=1, le=20),
    current_user: dict         = Depends(get_current_user),
    credentials                 = Depends(bearer),
):
    """
    FIX 5: Combines dish recommendations with real nearby restaurants
    (PostGIS) matched on cuisine_type — the only reliable join key we
    have since per-restaurant menu data doesn't exist yet.
    """
    await ensure_dishes_loaded()

    user_id = current_user["user_id"]
    token   = credentials.credentials

    food_graph = await fetch_food_graph(token)
    profile    = await fetch_user_profile(token)

    now     = datetime.now()
    context = _build_context(now, lat, lng, occasion, profile)
    user    = _build_user(profile, user_id, food_graph)

    recommendations = get_recommendations(
        user, context, food_graph, n=n,
        occasion_explicit=bool(occasion),
    )

    cuisines_needed = list({r["cuisine_type"] for r in recommendations if r.get("cuisine_type")})

    restaurants_by_cuisine = {}
    if cuisines_needed:
        async with LocalSession() as db:
            for cuisine in cuisines_needed:
                result = await db.execute(
                    text("""
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
                            AND cuisine_types ? :cuisine
                            AND ST_DWithin(
                                location::geography,
                                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                                :radius_m
                            )
                        ORDER BY distance_km
                        LIMIT 5
                    """),
                    {"lat": lat, "lng": lng, "radius_m": radius_km * 1000, "cuisine": cuisine},
                )
                rows = result.mappings().all()
                restos = [dict(r) for r in rows]
                for r in restos:
                    r["distance_km"] = round(float(r["distance_km"]), 2)
                restaurants_by_cuisine[cuisine] = restos

    for rec in recommendations:
        rec["nearby_restaurants"] = restaurants_by_cuisine.get(rec.get("cuisine_type"), [])

    return {
        "user_id":         user_id,
        "occasion":        context["occasion"],
        "occasion_strict": bool(occasion),
        "count":           len(recommendations),
        "recommendations": recommendations,
    }


@router.get("/cold-start")
async def cold_start_recommend(
    birthplace_state: str = Query("Karnataka"),
    religion: str          = Query("hindu"),
    age: int               = Query(28),
    gender: str            = Query("male"),
    is_vegetarian: bool    = Query(False),
    conditions: str        = Query(""),
    income_tier: str       = Query("unknown", description="low/medium/high if known, unknown otherwise"),
    n: int                 = Query(10),
):
    """
    Cold-start priors (health_literacy=0.5, habit_strength=0.6 baseline)
    are legitimate here — there is no profile or food_graph yet for a
    brand-new user, that's the definition of cold-start. This differs
    from the _build_user bug: those constants applied to EVERY user
    forever, including ones with months of real history. Here it's only
    ever used for users with zero interactions (see cold-start blend in
    the ranker, which fades this out as order_count grows toward 10).
    """
    await ensure_dishes_loaded()

    user = {
        "user_id":              "new_user",
        "age":                  age,
        "bmi":                  23.0,
        "health_literacy":      0.5,
        "habit_strength":       0.6,
        "income_tier":          income_tier,
        "region":               _state_to_region(birthplace_state),
        "is_vegetarian":        is_vegetarian,
        "conditions":           conditions,
        "dietary_restrictions": "vegetarian" if is_vegetarian else "",
        "religion":             religion,
    }
    now     = datetime.now()
    context = _build_context(now, None, None, None, None)

    recommendations = get_recommendations(user, context, {}, n=n, occasion_explicit=False)
    return {
        "user_type":       "cold_start",
        "count":           len(recommendations),
        "recommendations": recommendations,
    }


@router.get("/nearby-restaurants")
async def nearby_restaurants(
    lat: float              = Query(...),
    lng: float              = Query(...),
    radius_km: float        = Query(5.0),
    cuisine: Optional[str]  = Query(None),
    current_user: dict      = Depends(get_current_user),
):
    cuisine_filter = "AND cuisine_types ? :cuisine" if cuisine else ""
    async with LocalSession() as db:
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
            {"lat": lat, "lng": lng, "radius_m": radius_km * 1000, "cuisine": cuisine},
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
    """
    FIX: previously had no "northeast" bucket at all, even though the real
    trained encoder (confirmed via inspect_encoders.py against
    services/ml-training/models/encoders.joblib) has 5 region classes
    including "northeast" — meaning that class was permanently unreachable
    from this function regardless of what a real Northeastern user
    selected. Also fixed: Assam was wrongly bucketed as "east" — Assam is
    a Northeastern state, not Eastern.
    """
    south     = ["Tamil Nadu", "Karnataka", "Kerala", "Andhra Pradesh", "Telangana"]
    west      = ["Maharashtra", "Gujarat", "Goa", "Rajasthan"]
    east      = ["West Bengal", "Odisha", "Bihar", "Jharkhand"]
    northeast = ["Assam", "Meghalaya", "Manipur", "Mizoram", "Nagaland",
                 "Tripura", "Arunachal Pradesh", "Sikkim"]
    if state in south:     return "south"
    if state in west:      return "west"
    if state in east:      return "east"
    if state in northeast: return "northeast"
    return "north"