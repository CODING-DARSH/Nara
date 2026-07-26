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
import uuid
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import LocalSession
from app.core.security import get_current_user
from app.core.model_loader import model_store
from app.core.redis import (
    get_cached_recommendations, set_cached_recommendations,
    get_recently_shown, record_shown_dishes, invalidate_recs_cache,
    get_dish_interactions, record_dish_interaction,
)
from app.core.kafka import publish_feedback_event
from app.core.events import log_event, log_events_bulk
from app.pipeline.ranker import get_recommendations, set_dish_candidates
from app.pipeline import ranker as ranker_module

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
            # FIX: the SQL above never actually selected occasion_tags at
            # all until now, so this guard was dead code protecting a key
            # that could never be present. Both are needed together.
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

    now         = datetime.now()
    hour_bucket = now.hour  # cache granularity — a request 3 min apart in the
                             # same hour/occasion reuses the cached list instead
                             # of re-running the full ensemble.

    cached = await get_cached_recommendations(user_id, occasion, hour_bucket)
    if cached is not None:
        return {**cached, "_cache": "hit"}

    food_graph = await fetch_food_graph(token)
    profile    = await fetch_user_profile(token)

    context = _build_context(now, lat, lng, occasion, profile)
    user    = _build_user(profile, user_id, food_graph)

    recently_shown    = await get_recently_shown(user_id)
    dish_interactions = await get_dish_interactions(user_id)

    # FIX 2: occasion_explicit=True whenever the caller passed an occasion
    # (i.e. the user tapped a specific tab in the UI) -> strict filtering,
    # no silent fallback to the unfiltered list.
    recommendations = get_recommendations(
        user, context, food_graph, n=n,
        occasion_explicit=bool(occasion),
        recently_shown=recently_shown,
        dish_interactions=dish_interactions,
    )

    response = {
        "user_id":         user_id,
        "occasion":        context["occasion"],
        "occasion_strict": bool(occasion),
        "count":           len(recommendations),
        "recommendations": recommendations,
        "_models": model_store.status(),
    }

    await set_cached_recommendations(user_id, occasion, hour_bucket, response)

    session_id   = str(uuid.uuid4())
    shown_dishes = [{"dish_name": r["dish_name"], "cuisine_type": r.get("cuisine_type")}
                    for r in recommendations if r.get("dish_name")]
    dish_names   = [d["dish_name"] for d in shown_dishes]
    await record_shown_dishes(user_id, dish_names)

    # Feedback loop: log this impression so it can eventually be joined
    # against clicks/orders for retraining. Fire-and-forget — never blocks
    # or fails the response.
    await publish_feedback_event({
        "event_type":  "impression",
        "user_id":     user_id,
        "occasion":    context["occasion"],
        "dishes":      shown_dishes,
    })

    # Durable raw event log — see core/events.py. This is what Kafka's
    # impression event above couldn't be: permanent (not 7-day retention)
    # and queryable later for offline evaluation, with rank/score captured
    # AT THE MOMENT OF SHOWING rather than recomputed after the fact.
    await log_events_bulk([
        {
            "user_id":     user_id,
            "event_type":  "impression",
            "dish_name":   r.get("dish_name"),
            "cuisine_type": r.get("cuisine_type"),
            "occasion":    context["occasion"],
            "rank":        i,
            "score":       r.get("score"),
            "session_id":  session_id,
        }
        for i, r in enumerate(recommendations) if r.get("dish_name")
    ])

    response["session_id"] = session_id
    return response


class FeedbackIn(BaseModel):
    dish_name: str
    cuisine_type: Optional[str] = None  # lets the consumer update cuisine_affinity
                                         # without a cross-service dish_name lookup
    action: str            # "skip" | "click" | "order"
    occasion: Optional[str] = None
    rank: Optional[int]     = None  # position it was shown at, if known
    session_id: Optional[str] = None  # ties this action back to the impression
                                       # batch it came from, once the frontend
                                       # round-trips the session_id returned by
                                       # `/` — not wired on the frontend yet,
                                       # accepted now so no API change is
                                       # needed later.


@router.post("/feedback")
async def submit_feedback(
    body: FeedbackIn,
    current_user: dict = Depends(get_current_user),
):
    """
    Explicit user action on a recommended dish. This is the other half of
    the feedback loop alongside the impression event published in `/` —
    together they let a future retraining job join "what was shown" against
    "what the user actually did with it" instead of that data disappearing
    on every request like it did before.

    Two things happen on click/order:
      1. Published to Kafka -> consumed by
         user-intelligence/app/workers/feedback_update_worker.py, which
         nudges FoodGraph.cuisine_affinity (CATEGORY-level signal — "you
         like Gujarati food more now").
      2. Recorded directly in this service's own Redis
         (core/redis.record_dish_interaction) -> read by reorder_boost()
         (DISH-level signal — "you specifically keep ordering Khichadi").
         This is synchronous and immediate, unlike (1) which depends on a
         Kafka round-trip — a specific dish should reinforce itself on the
         very next request, not wait on cross-service consumer lag.
    """
    if body.action not in ("skip", "click", "order"):
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail="action must be one of: skip, click, order")

    user_id = current_user["user_id"]

    await publish_feedback_event({
        "event_type":   "feedback",
        "user_id":      user_id,
        "dish_name":    body.dish_name,
        "cuisine_type": body.cuisine_type,
        "action":       body.action,
        "occasion":     body.occasion,
        "rank":         body.rank,
    })

    if body.action in ("click", "order"):
        await record_dish_interaction(user_id, body.dish_name, body.action)
        # An order/click is a real signal that should be reflected on the
        # very next request, not up to RECS_CACHE_TTL_SECONDS later.
        await invalidate_recs_cache(user_id)

    await log_event(
        user_id=user_id,
        event_type=body.action,
        dish_name=body.dish_name,
        cuisine_type=body.cuisine_type,
        occasion=body.occasion,
        rank=body.rank,
        session_id=body.session_id,
    )

    return {"status": "recorded"}


@router.get("/with-restaurants")
async def recommend_with_restaurants(
    lat: float                = Query(...),
    lng: float                 = Query(...),
    occasion: Optional[str]    = Query(None),
    n: int                     = Query(10, ge=1, le=20),
    current_user: dict         = Depends(get_current_user),
    credentials                 = Depends(bearer),
):
    """
    FIX 5: Combines dish recommendations with real nearby restaurants
    (PostGIS) matched on cuisine_type — the only reliable join key we
    have since per-restaurant menu data doesn't exist yet.

    No distance cutoff — this is a fixed seeded restaurant dataset, not a
    live delivery-radius system, so an arbitrary km cutoff only created
    artificial scarcity unrelated to actual cuisine-match quality.
    Distance is still computed and used to sort (nearest cuisine match
    first), just never used to exclude.
    """
    await ensure_dishes_loaded()

    user_id = current_user["user_id"]
    token   = credentials.credentials

    food_graph = await fetch_food_graph(token)
    profile    = await fetch_user_profile(token)

    now     = datetime.now()
    context = _build_context(now, lat, lng, occasion, profile)
    user    = _build_user(profile, user_id, food_graph)

    # FIX: this endpoint used to fetch exactly `n` recommendations, match
    # each to nearby restaurants, and return whatever came back — but any
    # dish whose cuisine has ZERO real restaurants anywhere in the dataset gets
    # silently dropped by the frontend (it only builds a restaurant card
    # per dish that actually has nearby_restaurants). If a user's genuine
    # top-preference cuisine (e.g. gujarati) has little/no restaurant
    # coverage near their current location, their top recommendations
    # would vanish from this view entirely — while /v1/recommend/ (no
    # restaurant matching) kept showing them correctly, producing exactly
    # the "Home shows gujarati, Discover shows north_indian/idli instead"
    # mismatch. Fix: over-fetch and keep expanding the candidate pool
    # until we have `n` dishes that actually have a nearby match (or we
    # hit a sane cap), preserving score order throughout — so among
    # dishes that DO have real coverage, the user's true preference order
    # still wins, instead of an arbitrary lower-affinity cuisine
    # dominating purely because it happens to have nearby restaurants.
    MAX_FETCH_MULTIPLIER = 4
    fetch_n = n
    recommendations = []
    matched = []
    restaurants_by_cuisine = {}
    dish_interactions = await get_dish_interactions(user_id)

    async with LocalSession() as db:
        for attempt in range(MAX_FETCH_MULTIPLIER):
            recommendations = get_recommendations(
                user, context, food_graph, n=fetch_n,
                occasion_explicit=bool(occasion),
                dish_interactions=dish_interactions,
            )
            cuisines_needed = list({r["cuisine_type"] for r in recommendations
                                     if r.get("cuisine_type") and r["cuisine_type"] not in restaurants_by_cuisine})

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
                        ORDER BY distance_km
                        LIMIT 5
                    """),
                    {"lat": lat, "lng": lng, "cuisine": cuisine},
                )
                rows = result.mappings().all()
                restos = [dict(r) for r in rows]
                for r in restos:
                    r["distance_km"] = round(float(r["distance_km"]), 2)
                restaurants_by_cuisine[cuisine] = restos

            for rec in recommendations:
                rec["nearby_restaurants"] = restaurants_by_cuisine.get(rec.get("cuisine_type"), [])

            matched = [r for r in recommendations if r["nearby_restaurants"]]
            if len(matched) >= n or fetch_n >= len(ranker_module.DISH_CANDIDATES):
                break
            # Not enough dishes with real restaurant coverage yet — pull a
            # wider candidate pool (still in original score order) and
            # retry the match instead of returning a thin/skewed result.
            fetch_n = min(fetch_n * 3, len(ranker_module.DISH_CANDIDATES) or fetch_n * 3)

    # Keep original ranking order (score-sorted), just filtered down to
    # ones with a real nearby option — this is what actually fixes the
    # "shows a different, lower-preference cuisine" symptom, since it's
    # no longer "whatever happened to have coverage" but "your best
    # matches, restricted to what's actually deliverable near you."
    recommendations = matched[:n]

    session_id = str(uuid.uuid4())
    await log_events_bulk([
        {
            "user_id":       user_id,
            "event_type":    "impression",
            "dish_name":     r.get("dish_name"),
            "cuisine_type":  r.get("cuisine_type"),
            "restaurant_id": (r.get("nearby_restaurants") or [{}])[0].get("id"),
            "occasion":      context["occasion"],
            "rank":          i,
            "score":         r.get("score"),
            "session_id":    session_id,
        }
        for i, r in enumerate(recommendations) if r.get("dish_name")
    ])

    return {
        "user_id":         user_id,
        "occasion":        context["occasion"],
        "occasion_strict": bool(occasion),
        "count":           len(recommendations),
        "recommendations": recommendations,
        "session_id":      session_id,
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
                    {cuisine_filter}
                ORDER BY distance_km
                LIMIT 20
            """),
            {"lat": lat, "lng": lng, "cuisine": cuisine},
        )
        rows = result.mappings().all()
        restaurants = [dict(r) for r in rows]
        for r in restaurants:
            r["distance_km"] = round(float(r["distance_km"]), 2)
        return {"count": len(restaurants), "restaurants": restaurants}


@router.get("/restaurants/{restaurant_id}")
async def get_restaurant_detail(
    restaurant_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Returns a single restaurant's details + its full menu scored and ranked
    by the recommendation pipeline. This is the backend for the
    restaurant-detail page (tap a restaurant card → see its ranked menu).

    Dish candidates are scoped to this restaurant's real menu_items from
    restaurant_menu_items, not the global nutrition_kb pool — this is the
    first endpoint where price_match_score is genuinely computed from a
    real dish price rather than a placeholder.
    """
    user_id = current_user.get("user_id")
    token   = current_user.get("token")

    async with LocalSession() as db:
        # Fetch restaurant details
        resto_result = await db.execute(
            text("""
                SELECT id, name, cuisine_types, area, avg_cost_for_two,
                       rating, delivery_enabled, delivery_time_min
                FROM restaurants
                WHERE id = :rid AND is_active = TRUE
            """),
            {"rid": restaurant_id},
        )
        resto = resto_result.mappings().first()
        if not resto:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Restaurant not found")
        resto = dict(resto)

        # Fetch this restaurant's real menu items joined with nutrition_kb
        # for the full feature vector — this is the real candidate set for
        # this endpoint, not the global DISH_CANDIDATES pool.
        menu_result = await db.execute(
            text("""
                SELECT
                    rmi.dish_name,
                    rmi.cuisine_type,
                    rmi.price,
                    rmi.is_available,
                    nk.is_veg,
                    nk.allergens,
                    nk.occasion_tags,
                    nk.glycemic_index,
                    nk.glycemic_load,
                    nk.per_serving->>'calories_kcal'  AS calories_kcal,
                    nk.per_serving->>'protein_g'      AS protein_g,
                    nk.per_serving->>'carbs_g'        AS carbs_g,
                    nk.per_serving->>'fat_g'          AS fat_g,
                    nk.per_serving->>'fiber_g'        AS fiber_g
                FROM restaurant_menu_items rmi
                LEFT JOIN nutrition_kb nk ON nk.dish_name = rmi.dish_name
                WHERE rmi.restaurant_id = :rid
                  AND rmi.is_available = TRUE
                ORDER BY rmi.dish_name
            """),
            {"rid": restaurant_id},
        )
        menu_items = [dict(r) for r in menu_result.mappings().all()]

    if not menu_items:
        return {
            "restaurant": resto,
            "count": 0,
            "menu": [],
        }

    # Score and rank the menu using the same full pipeline as the main
    # recommend endpoint — the key difference is the candidate set is this
    # restaurant's menu only, and each dish carries a real price from
    # restaurant_menu_items, making price_match_score a real computation
    # instead of the placeholder it is for the global pool.
    profile    = await fetch_user_profile(token)
    food_graph = await fetch_food_graph(token)

    now     = datetime.now()
    context = _build_context(now, None, None, None, profile)
    user    = _build_user(profile, user_id, food_graph)
    # Pass avg_cost_for_two from this specific restaurant so the budget
    # midpoint in price_match_score reflects where this restaurant sits
    # price-wise, not a generic user default.
    user["avg_cost_for_two"] = resto.get("avg_cost_for_two", 400)

    # Score every available menu item through the pipeline
    scored = []
    for item in menu_items:
        # Temporarily inject this restaurant's menu item as the candidate
        # so get_recommendations' per-dish scoring logic runs on it.
        # We call the individual scoring functions directly rather than
        # going through get_recommendations() (which works on DISH_CANDIDATES
        # as the candidate pool) to avoid replacing the global pool.
        from app.pipeline.ranker import (
            score_dish, health_score_dish, reorder_boost,
            REGION_CUISINE_AFFINITY,
        )

        cuisine = item.get("cuisine_type", "north_indian")
        region  = user.get("region")
        region_affinity = REGION_CUISINE_AFFINITY.get(region, {}).get(cuisine, 0.0)
        cuisine_affinity = (food_graph or {}).get("cuisine_affinity", {})
        behavioral = cuisine_affinity.get(cuisine)
        if behavioral is not None:
            user["cuisine_affinity_score"] = round(0.75 * behavioral + 0.25 * region_affinity, 3)
        else:
            user["cuisine_affinity_score"] = region_affinity if region_affinity else 0.3

        health_info = health_score_dish(user, item, context)
        user["health_match_score"] = health_info["confidence"]

        # Real price computation — this is what makes this endpoint
        # different from the global pool. dish["price"] comes from
        # restaurant_menu_items, not nutrition_kb.
        dish_price = float(item.get("price") or 0)
        budget_midpoint = float(
            (user.get("budget_preferences") or {}).get("preferred_range")
            or (resto.get("avg_cost_for_two", 400) / 2)
        )
        raw = 1.0 - abs(dish_price - budget_midpoint) / max(budget_midpoint, 1)
        user["price_match_score"] = round(max(0.0, min(1.0, raw)), 3)

        dish_score, _ranker_breakdown = score_dish(user, item, context, len(scored))
        boost      = reorder_boost(user, item, food_graph or {})
        final      = round(dish_score + boost, 4)

        scored.append({
            "dish_name":         item["dish_name"],
            "cuisine_type":      item["cuisine_type"],
            "price":             float(item["price"]),
            "score":             final,
            "health_compliant":  health_info["compliant"],
            "health_confidence": health_info["confidence"],
            "health_reasons":    health_info["reasons"],
            "nutrition": {
                "calories":  item.get("calories_kcal"),
                "protein_g": item.get("protein_g"),
                "carbs_g":   item.get("carbs_g"),
                "fat_g":     item.get("fat_g"),
                "fiber_g":   item.get("fiber_g"),
                "gi":        item.get("glycemic_index"),
            },
            "is_veg":    item.get("is_veg"),
            "allergens": item.get("allergens", []),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    return {
        "restaurant": resto,
        "count":      len(scored),
        "menu":       scored,
    }


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