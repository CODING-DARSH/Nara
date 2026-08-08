"""
Feedback Update Worker
Kafka consumer on recommendation.feedback topic.

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
import json
import structlog
from uuid import UUID

from aiokafka import AIOKafkaConsumer
import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.database import NeonSession
from app.core.redis import get_redis
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

FEEDBACK_TOPIC = "recommendation.feedback"

# Recommendation service caches scored recs on a *different* Redis DB index
# (db 1) than user-intelligence (db 0) — same server/credentials, separate
# namespace. Without also invalidating there, a click/order wouldn't be
# reflected in recommendations for up to RECS_CACHE_TTL_SECONDS (10 min).
# Building a full second Redis client just for this one cross-service
# invalidation; if this pattern grows, it should become a shared cache
# util instead of living in two services.
def _recs_cache_redis_url() -> str:
    base = settings.redis_url.rsplit("/", 1)[0]
    return f"{base}/1"


async def _invalidate_recs_cache(user_id: str):
    try:
        client = aioredis.from_url(_recs_cache_redis_url(), encoding="utf-8", decode_responses=True)
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
    log.info("feedback_update_worker.starting", kafka=settings.kafka_bootstrap_servers)

    consumer = AIOKafkaConsumer(
        FEEDBACK_TOPIC,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="feedback-update-workers",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    await consumer.start()
    log.info("feedback_update_worker.ready")

    try:
        async for message in consumer:
            data = message.value
            event_type = data.get("event_type")

            # Only explicit actions move affinity — see module docstring
            # for why impressions are intentionally skipped here.
            if event_type != "feedback":
                continue

            user_id_str  = data.get("user_id")
            cuisine_type = data.get("cuisine_type")
            action       = data.get("action")

            if not user_id_str or not action:
                log.warning("feedback_update_worker.malformed_event", data=data)
                continue

            if not cuisine_type:
                # Recommendation router only knows cuisine_type if the
                # frontend passed it back (it has it — every rec/dish
                # object already carries cuisine_type). If it's missing,
                # this is an older client or a bug in the caller; log and
                # skip rather than guessing.
                log.debug("feedback_update_worker.missing_cuisine_type",
                          dish_name=data.get("dish_name"), action=action)
                continue

            try:
                user_id = UUID(user_id_str)
                await apply_feedback(user_id, cuisine_type, action)
            except ValueError:
                log.error("feedback_update_worker.invalid_uuid", user_id=user_id_str)
            except Exception as e:
                log.error("feedback_update_worker.failed", error=str(e), data=data)

    finally:
        await consumer.stop()
        log.info("feedback_update_worker.stopped")


if __name__ == "__main__":
    asyncio.run(run_worker())
