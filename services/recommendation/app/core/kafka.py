"""
NARA — Recommendation Service "Kafka" replacement (now Redis Streams)
Save as: services/recommendation/app/core/kafka.py
(keep filename/imports the same — routers/recommend.py and
routers/orders.py both do `from app.core.kafka import publish_feedback_event`)
"""
import time
import structlog
from redis.asyncio import Redis
from app.core.config import get_settings
from app.core.redis_streams import emit as _emit

log = structlog.get_logger()
settings = get_settings()

FEEDBACK_STREAM = "recommendation.feedback"

_redis: Redis | None = None


async def start_kafka_producer():
    """Name kept for zero-change call sites in main.py's startup hook."""
    global _redis
    if _redis is not None:
        return
    _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    log.info("redis_stream.producer.started", stream=FEEDBACK_STREAM)


async def stop_kafka_producer():
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
        log.info("redis_stream.producer.stopped")


async def publish_feedback_event(event: dict):
    """
    Same fire-and-forget contract as before: never raise into the
    caller, a feedback event failing to send should never fail the
    user-facing request.
    """
    global _redis
    if _redis is None:
        log.warning("redis_stream.producer.not_started", event_type=event.get("event_type"))
        return
    event.setdefault("emitted_at", time.time())
    try:
        await _emit(_redis, FEEDBACK_STREAM, event)
    except Exception as e:
        log.warning("redis_stream.publish_failed", error=str(e), event_type=event.get("event_type"))