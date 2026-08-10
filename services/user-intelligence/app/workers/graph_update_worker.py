"""
Food Graph Update Worker
Redis Streams consumer on food.events.enriched stream (was Kafka).
Triggers food graph recompute when new enriched events arrive.
Run standalone: python -m app.workers.graph_update_worker
"""
import asyncio
import structlog
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.database import NeonSession
from app.core.redis import get_redis
from app.core.redis_streams import consume_loop
from app.workers.graph_computer import compute_food_graph

log = structlog.get_logger()
settings = get_settings()

ENRICHED_STREAM = "food.events.enriched"
CONSUMER_GROUP = "graph-update-workers"

_RECONNECT_BACKOFF_SECONDS = [2, 5, 10, 20, 30]


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
    attempt = 0

    while True:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)

        try:
            log.info("graph_update_worker.starting", redis=settings.redis_url, attempt=attempt + 1)
            attempt = 0

            async def handle_message(data: dict, key):
                user_id_str = data.get("user_id")
                event_id = data.get("event_id")

                if not user_id_str:
                    log.warning("graph_update_worker.missing_user_id", data=data)
                    return

                log.info("graph_update_worker.processing", event_id=event_id, user_id=user_id_str)

                try:
                    user_id = UUID(user_id_str)
                    await process_enriched_event(user_id)
                except ValueError:
                    log.error("graph_update_worker.invalid_uuid", user_id=user_id_str)

            await consume_loop(
                redis,
                stream=ENRICHED_STREAM,
                group=CONSUMER_GROUP,
                consumer_name="graph-worker-1",
                handler=handle_message,
            )

        except asyncio.CancelledError:
            raise

        except Exception as e:
            wait_s = _RECONNECT_BACKOFF_SECONDS[min(attempt, len(_RECONNECT_BACKOFF_SECONDS) - 1)]
            log.error("graph_update_worker.connection_failed",
                      error=str(e), exc_info=True, retry_in_seconds=wait_s, attempt=attempt + 1)
            attempt += 1
            await asyncio.sleep(wait_s)
            continue


if __name__ == "__main__":
    asyncio.run(run_worker())