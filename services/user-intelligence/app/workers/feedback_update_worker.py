"""
Feedback Update Worker
Redis Streams consumer on recommendation.feedback stream (was Kafka).

This is the missing half of the feedback loop: the recommendation service
was publishing impression/click/order/skip events, but nothing consumed
them — cuisine_affinity only ever moved when a meal was explicitly logged
(see graph_update_worker.py / food.events.enriched). Browsing and ordering
behavior in the recommendation UI had zero effect on future rankings.

This worker turns "feedback" events (explicit skip/click/order on a shown
dish) into a real, bounded nudge on FoodGraph.cuisine_affinity, using an
exponential-moving-average update rather than a full recompute — full
recomputes are meal-log-driven (compute_food_graph reads food_events) and
have no concept of "shown but not eaten" signal at all.

"impression" events are intentionally NOT used to move affinity — being
shown a dish is not a preference signal, only acting on it is. Impressions
are logged for future joint analysis (impression -> click -> order funnels)
but aren't handled here yet; add a dedicated impression-store consumer if
that's needed later.

Run standalone: python -m app.workers.feedback_update_worker
"""
import asyncio
import structlog
from uuid import UUID

from redis.asyncio import Redis
import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.database import NeonSession
from app.core.redis import get_redis
from app.core.redis_streams import consume_loop
from app.models.intelligence import FoodGraph
from sqlalchemy import select

log = structlog.get_logger()
settings = get_settings()

# Learning-rate style weights per action — order is the strongest signal
# (you actually ate it), click is weaker (you were interested enough to
# open it, didn't necessarily eat it), skip is a small negative nudge
# (shown, ignored — a soft signal something isn't a great fit right now,
# not a strong one, since "skip" also just means "wasn't in the mood").
#
# affinity_new = affinity_old * (1 - alpha) + target * alpha
# clamped to [0, 1] to match the existing 0-1 cuisine_affinity scale
# (see FoodGraph.cuisine_affinity docstring: south_indian: 0.72, etc.)
ACTION_WEIGHTS = {
    "order": {"alpha": 0.20, "target": 1.0},
    "click": {"alpha": 0.07, "target": 0.8},
    "skip":  {"alpha": 0.04, "target": 0.0},
}

FEEDBACK_STREAM = "recommendation.feedback"
CONSUMER_GROUP = "feedback-update-workers"

_RECONNECT_BACKOFF_SECONDS = [2, 5, 10, 20, 30]

# Recommendation service caches scored recs on a *different* Redis DB index
# (db 1) than user-intelligence (db 0) — same server/credentials, separate
# namespace. Without also invalidating there, a click/order wouldn't be
# reflected in recommendations for up to RECS_CACHE_TTL_SECONDS (10 min).
# Building a full second Redis client just for this one cross-service
# invalidation; if this pattern grows, it should become a shared cache
# util instead of living in two services.
async def _invalidate_recs_cache(user_id: str):
    """
    Invalidates recommendation-service's scored-recs cache so a click/
    order is reflected on the next request instead of waiting for TTL.

    Previously this connected to a *different* Redis DB index (db 1)
    than user-intelligence's own cache (db 0) — a leftover from when
    each service ran its own local Redis container with per-service DB
    splitting. Now that everything shares one Upstash REDIS_URL (no
    local per-service DB index), both caches live in the same logical
    Redis instance — reuse the same client/URL directly.
    """
    try:
        client = aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        async for key in client.scan_iter(match=f"recs:{user_id}:*"):
            await client.delete(key)
        await client.aclose()
    except Exception as e:
        log.debug("feedback_worker.recs_cache_invalidate_failed", error=str(e))


async def apply_feedback(user_id: UUID, cuisine_type: str, action: str):
    weights = ACTION_WEIGHTS.get(action)
    if not weights or not cuisine_type:
        return

    async with NeonSession() as db:
        result = await db.execute(select(FoodGraph).where(FoodGraph.user_id == user_id))
        graph = result.scalar_one_or_none()
        if graph is None:
            # No food graph yet (brand new user) — nothing to nudge until
            # compute_food_graph creates one from a real logged meal.
            log.debug("feedback_worker.no_food_graph", user_id=str(user_id))
            return

        affinity = dict(graph.cuisine_affinity or {})
        old = affinity.get(cuisine_type, 0.3)  # 0.3 matches ranker.py's own
                                                 # cold-start default, so a
                                                 # cuisine with no prior
                                                 # signal starts from the
                                                 # same baseline the ranker
                                                 # already assumes.
        alpha, target = weights["alpha"], weights["target"]
        new = old * (1 - alpha) + target * alpha
        affinity[cuisine_type] = round(max(0.0, min(1.0, new)), 3)

        graph.cuisine_affinity = affinity
        await db.commit()

        log.info("feedback_worker.affinity_updated",
                  user_id=str(user_id), cuisine=cuisine_type, action=action,
                  old=old, new=affinity[cuisine_type])

    # Invalidate both caches: user-intelligence's own food-graph cache (so
    # the next /food-graph read reflects it) and recommendation's scored-
    # recs cache (so the next /v1/recommend/ call re-ranks with it instead
    # of serving a stale cached list).
    redis = await get_redis()
    await redis.delete(f"foodgraph:{user_id}")
    await redis.delete(f"insights:{user_id}")
    await _invalidate_recs_cache(str(user_id))


async def run_worker():
    """
    Same retry/backoff shape used across all workers now — connect,
    consume, and on any connection-level failure back off and retry
    rather than letting the whole worker task die silently.
    """
    attempt = 0

    while True:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)

        try:
            log.info("feedback_update_worker.starting", redis=settings.redis_url, attempt=attempt + 1)
            attempt = 0

            async def handle_message(data: dict, key):
                event_type = data.get("event_type")

                # Only explicit actions move affinity — see module
                # docstring for why impressions are intentionally skipped.
                if event_type != "feedback":
                    return

                user_id_str  = data.get("user_id")
                cuisine_type = data.get("cuisine_type")
                action       = data.get("action")

                if not user_id_str or not action:
                    log.warning("feedback_update_worker.malformed_event", data=data)
                    return

                if not cuisine_type:
                    log.debug("feedback_update_worker.missing_cuisine_type",
                              dish_name=data.get("dish_name"), action=action)
                    return

                try:
                    user_id = UUID(user_id_str)
                    await apply_feedback(user_id, cuisine_type, action)
                except ValueError:
                    log.error("feedback_update_worker.invalid_uuid", user_id=user_id_str)

            await consume_loop(
                redis,
                stream=FEEDBACK_STREAM,
                group=CONSUMER_GROUP,
                consumer_name="feedback-worker-1",
                handler=handle_message,
            )

        except asyncio.CancelledError:
            raise

        except Exception as e:
            wait_s = _RECONNECT_BACKOFF_SECONDS[min(attempt, len(_RECONNECT_BACKOFF_SECONDS) - 1)]
            log.error("feedback_update_worker.connection_failed",
                      error=str(e), exc_info=True, retry_in_seconds=wait_s, attempt=attempt + 1)
            attempt += 1
            await asyncio.sleep(wait_s)
            continue


if __name__ == "__main__":
    asyncio.run(run_worker())