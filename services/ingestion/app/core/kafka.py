import json
import structlog
from aiokafka import AIOKafkaProducer
from app.core.config import get_settings

settings = get_settings()
log = structlog.get_logger()

_producer = None


async def get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await _producer.start()
        log.info("kafka.producer.started")
    return _producer


async def close_producer():
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None


async def emit(topic: str, payload: dict, key: str = None):
    """Emit a message to a Kafka topic."""
    producer = await get_producer()
    key_bytes = key.encode("utf-8") if key else None
    await producer.send_and_wait(topic, value=payload, key=key_bytes)
    log.info("kafka.emitted", topic=topic, key=key)

