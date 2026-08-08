"""
NARA — Recommendation Service Redis Client

redis_url was configured in settings but never actually used anywhere in
this service — every request recomputed the full ranking pipeline from
scratch. This adds:
  1. A short-TTL cache of the final scored/diversified recommendation list
     per (user, occasion, hour-bucket), so repeated requests in the same
     window don't re-run the whole ensemble.
  2. A rolling "recently shown dish names" set per user, so the ranker can
     apply an anti-repeat penalty across requests (not just within one).
  3. Per-dish interaction weights (click/order) — dish-level reinforcement
     distinct from both meal-log top_dishes (LogMeal.jsx only) and
     cuisine_affinity (category-level, updated by user-intelligence's
     feedback_update_worker). A specific dish you keep clicking/ordering
     in the recommendation UI previously had zero individual effect on
     THAT dish surfacing again — only its cuisine bucket moved.
"""
import json
import time
import redis.asyncio as aioredis
from app.core.config import get_settings

settings = get_settings()
_redis_client = None

RECS_CACHE_TTL_SECONDS   = 600      # 10 min — short enough to reflect a changed profile/context quickly
RECENTLY_SHOWN_TTL_SECONDS = 60 * 60 * 24  # 24h rolling window
RECENTLY_SHOWN_MAX_ITEMS   = 30

DISH_INTERACTION_TTL_SECONDS = 60 * 60 * 24 * 90  # 90d — dish-level taste is
                                                    # slower-moving than a
                                                    # session; don't decay it
                                                    # away too fast
DISH_INTERACTION_WEIGHTS = {"click": 0.5, "order": 1.5}  # order counts more
                                                            # than a click —
                                                            # matches the
                                                            # target=0.8 vs
                                                            # 1.0 split used
                                                            # for cuisine
                                                            # affinity in
                                                            # feedback_update_worker,
                                                            # kept consistent
                                                            # in spirit


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis():
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


def recs_cache_key(user_id: str, occasion: str | None, hour_bucket: int) -> str:
    return f"recs:{user_id}:{occasion or 'auto'}:{hour_bucket}"


def recently_shown_key(user_id: str) -> str:
    return f"recently_shown:{user_id}"


def dish_interactions_key(user_id: str) -> str:
    return f"dish_interactions:{user_id}"


async def get_cached_recommendations(user_id: str, occasion: str | None, hour_bucket: int):
    try:
        redis = await get_redis()
        raw = await redis.get(recs_cache_key(user_id, occasion, hour_bucket))
        return json.loads(raw) if raw else None
    except Exception:
        # Cache is a perf optimization, never a hard dependency — any
        # failure here should fall through to a normal recompute.
        return None


async def set_cached_recommendations(user_id: str, occasion: str | None, hour_bucket: int, recommendations: list):
    try:
        redis = await get_redis()
        await redis.set(
            recs_cache_key(user_id, occasion, hour_bucket),
            json.dumps(recommendations),
            ex=RECS_CACHE_TTL_SECONDS,
        )
    except Exception:
        pass


async def get_recently_shown(user_id: str) -> set:
    try:
        redis = await get_redis()
        members = await redis.smembers(recently_shown_key(user_id))
        return set(members) if members else set()
    except Exception:
        return set()


async def record_shown_dishes(user_id: str, dish_names: list):
    if not dish_names:
        return
    try:
        redis = await get_redis()
        key = recently_shown_key(user_id)
        await redis.sadd(key, *dish_names)
        await redis.expire(key, RECENTLY_SHOWN_TTL_SECONDS)
        # Keep the set bounded — trim occasionally so it can't grow forever
        # for very active users.
        size = await redis.scard(key)
        if size > RECENTLY_SHOWN_MAX_ITEMS * 2:
            members = list(await redis.smembers(key))
            drop = members[: len(members) - RECENTLY_SHOWN_MAX_ITEMS]
            if drop:
                await redis.srem(key, *drop)
    except Exception:
        pass


async def invalidate_recs_cache(user_id: str):
    """Called after feedback (skip/click/order) so the next request reflects it
    instead of serving a stale cached list for up to RECS_CACHE_TTL_SECONDS."""
    try:
        redis = await get_redis()
        async for key in redis.scan_iter(match=f"recs:{user_id}:*"):
            await redis.delete(key)
    except Exception:
        pass


async def record_dish_interaction(user_id: str, dish_name: str, action: str):
    """
    Increments a per-dish weighted counter on click/order. This is what
    reorder_boost() reads (alongside meal-log top_dishes) so a specific
    dish you keep engaging with in the recommendation UI gets reinforced
    individually, not just its cuisine bucket. `skip` is intentionally
    not handled here — a soft negative skip signal already exists at the
    cuisine level via feedback_update_worker's cuisine_affinity nudge;
    doing it again per-dish here would double-count the same weak signal.
    """
    weight = DISH_INTERACTION_WEIGHTS.get(action)
    if not weight:
        return
    try:
        redis = await get_redis()
        key = dish_interactions_key(user_id)
        await redis.hincrbyfloat(key, dish_name, weight)
        await redis.expire(key, DISH_INTERACTION_TTL_SECONDS)
    except Exception:
        pass


async def get_dish_interactions(user_id: str) -> dict:
    try:
        redis = await get_redis()
        raw = await redis.hgetall(dish_interactions_key(user_id))
        return {k: float(v) for k, v in raw.items()} if raw else {}
    except Exception:
        return {}
