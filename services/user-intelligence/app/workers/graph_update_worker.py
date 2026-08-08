"""
Food Graph Update Worker
Kafka consumer on food.events.enriched topic.
Triggers food graph recompute when new enriched events arrive.
Run standalone: python -m app.workers.graph_update_worker
"""
import asyncio
import json
import structlog
from uuid import UUID

from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import NeonSession
from app.core.redis import get_redis
from app.workers.graph_computer import compute_food_graph

log = structlog.get_logger()
settings = get_settings()


async def process_enriched_event(user_id: UUID):
    """Recompute food graph for user and invalidate cache."""
    async with NeonSession() as db:
        try:
            # Invalidate cache first
            redis = await get_redis()
            await redis.delete(f"foodgraph:{user_id}")
            await redis.delete(f"insights:{user_id}")

            # Recompute
            graph = await compute_food_graph(user_id, db)
            if graph:
                log.info("food_graph.updated", user_id=str(user_id), meals=graph.total_meals_logged)
            else:
                log.info("food_graph.no_data", user_id=str(user_id))
        except Exception as e:
            log.error("food_graph.update_failed", user_id=str(user_id), error=str(e))


async def run_worker():
    log.info("graph_update_worker.starting", kafka=settings.kafka_bootstrap_servers)

    consumer = AIOKafkaConsumer(
        "food.events.enriched",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="graph-update-workers",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )

    await consumer.start()
    log.info("graph_update_worker.ready")

    try:
        async for message in consumer:
            data = message.value
            user_id_str = data.get("user_id")
            event_id = data.get("event_id")

            if not user_id_str:
                log.warning("graph_update_worker.missing_user_id", data=data)
                continue

            log.info("graph_update_worker.processing", event_id=event_id, user_id=user_id_str)

            try:
                user_id = UUID(user_id_str)
                await process_enriched_event(user_id)
            except ValueError:
                log.error("graph_update_worker.invalid_uuid", user_id=user_id_str)
            except Exception as e:
                log.error("graph_update_worker.failed", event_id=event_id, error=str(e))

    finally:
        await consumer.stop()
        log.info("graph_update_worker.stopped")


if __name__ == "__main__":
    asyncio.run(run_worker())

