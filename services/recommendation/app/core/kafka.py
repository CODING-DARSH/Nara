"""
NARA — Recommendation Service Kafka Producer

The `recommendation.feedback` topic was created by kafka-init in
docker-compose but nothing in this service ever produced to it — every
impression, click, skip, and order the recommendation pipeline generated
went nowhere, so the models could never be retrained on their own live
outcomes. This wires up a real producer.

Two event types are published:
  - "impression": every dish list actually returned to a user (fire-and-forget,
    called from the recommend router after get_recommendations()).
  - "feedback": explicit user action on a specific dish (skip/click/order),
    submitted via POST /v1/recommend/feedback.
"""
import json
import time
import structlog
from aiokafka import AIOKafkaProducer
from app.core.config import get_settings

log = structlog.get_logger()
settings = get_settings()

FEEDBACK_TOPIC = "recommendation.feedback"

_producer: AIOKafkaProducer | None = None


async def start_kafka_producer():
    global _producer
    if _producer is not None:
        return
    _producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await _producer.start()
    log.info("kafka_producer.started", topic=FEEDBACK_TOPIC)


async def stop_kafka_producer():
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None
        log.info("kafka_producer.stopped")


async def publish_feedback_event(event: dict):
    """
    Fire-and-forget publish. A feedback-loop event failing to send should
    never fail the user-facing request — log and move on.
    """
    global _producer
    if _producer is None:
        log.warning("kafka_producer.not_started", event_type=event.get("event_type"))
        return
    event.setdefault("emitted_at", time.time())
    try:
        await _producer.send_and_wait(FEEDBACK_TOPIC, value=event)
    except Exception as e:
        log.warning("kafka_producer.publish_failed", error=str(e), event_type=event.get("event_type"))
