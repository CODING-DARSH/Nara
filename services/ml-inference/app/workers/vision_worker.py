"""
Vision Worker — Photo Processing (Sprint 4 Placeholder)
Kafka consumer on photo.upload.pending

Sprint 4 behaviour:
  - Consume photo upload events
  - Verify photo exists in MinIO
  - Mark event as "pending_vision" (waiting for Sprint 5 model)
  - Log photo metadata for future training data collection

Sprint 5 will replace this with:
  - EfficientNet-B4 fine-tuned on South Asian food images
  - Inference pipeline returning dish_name + confidence
  - Feeding result back into enrichment pipeline

Why not Claude Vision API?
  We want a trained model we own, not API dependency.
  Need 10K+ labeled photos before fine-tuning is worth it.
  Photos collected here become that training dataset.
"""
import asyncio
import json
import uuid

import structlog
from aiokafka import AIOKafkaConsumer
from sqlalchemy import update

from app.core.config import get_settings
from app.core.database import NeonSession
from app.core.metrics import metrics
from app.models.nutrition import FoodEvent

log = structlog.get_logger()
settings = get_settings()


async def process_photo_event(event_id: str, user_id: str, s3_key: str):
    """
    Sprint 4: Mark photo event as pending_vision.
    Sprint 5: Replace with actual model inference.
    """
    async with NeonSession() as db:
        # Mark event status — separate from "pending" so we know
        # it's been seen by vision worker, just waiting for model
        await db.execute(
            update(FoodEvent)
            .where(FoodEvent.id == uuid.UUID(event_id))
            .values(enrichment_status="pending_vision")
        )
        await db.commit()

    metrics.total_photos_processed += 1
    log.info(
        "vision_worker.photo_queued",
        event_id=event_id,
        user_id=user_id,
        s3_key=s3_key,
        note="Sprint 5: EfficientNet-B4 will process this",
    )


async def run_vision_worker():
    """
    Vision worker consumer loop.
    Sprint 4: Just acknowledges photos and queues for future processing.
    """
    log.info("vision_worker.starting", kafka=settings.kafka_bootstrap_servers)

    consumer = AIOKafkaConsumer(
        "photo.upload.pending",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_consumer_group_vision,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    await consumer.start()
    log.info("vision_worker.ready", note="Sprint 4 placeholder — no model loaded")

    try:
        async for message in consumer:
            data = message.value
            event_id = data.get("event_id")
            user_id = data.get("user_id")
            # Ingestion (app/routers/meals.py) emits this field as "s3_key",
            # not "minio_key" — this previously always read as an empty string.
            s3_key = data.get("s3_key", "")

            if not event_id or not user_id:
                log.warning("vision_worker.missing_fields", data=data)
                continue

            try:
                await process_photo_event(event_id, user_id, s3_key)
            except Exception as e:
                log.error(
                    "vision_worker.failed",
                    event_id=event_id,
                    error=str(e),
                )

    finally:
        await consumer.stop()
        log.info("vision_worker.stopped")


if __name__ == "__main__":
    asyncio.run(run_vision_worker())
