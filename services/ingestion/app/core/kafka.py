"""
NARA — Ingestion Service "Kafka" replacement (now Redis Streams)
Save as: services/ingestion/app/core/kafka.py
(keep the filename — every caller does `from app.core.kafka import emit`)
"""
import structlog
from redis.asyncio import Redis
from app.core.config import get_settings
from app.core.redis_streams import emit as _emit

settings = get_settings()
log = structlog.get_logger()

_redis: Redis | None = None


async def get_producer() -> Redis:
    """Kept the same function name/shape as the old get_producer() so
    nothing calling it needs to change — it just returns a Redis client
    instead of an AIOKafkaProducer now."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
        log.info("redis_stream.producer.started")
    return _redis


async def close_producer():
    global _redis
    if _redis:
        await _redis.close()
        _redis = None


async def emit(topic: str, payload: dict, key: str = None):
    """Same signature as before: emit(topic, payload, key)."""
    redis = await get_producer()
    await _emit(redis, topic, payload, key)