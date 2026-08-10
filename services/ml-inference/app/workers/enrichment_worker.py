"""
Enrichment Worker — Core ML Inference Pipeline
Redis Streams consumer on food.events.raw (was Kafka)

Flow for each event:
  1. Consume message from food.events.raw
  2. Mark food_event.enrichment_status = "processing"
  3. Extract dish name from raw_input using Food NER
  4. Try KB lookup (fuzzy match)
     a. Hit  → use KB nutrition, confidence ~0.8-1.0
     b. Miss → use ingredient estimator, confidence ~0.4-0.5
  5. Write to food_event_nutrition table
  6. Update food_event.enrichment_status = "done"
  7. Publish to food.events.enriched → triggers graph recompute

On any failure:
  - Mark enrichment_status = "failed"
  - Log error with full context
  - Continue to next message (don't crash the worker)
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone

import structlog
from redis.asyncio import Redis
from sqlalchemy import select, update

from app.core.config import get_settings
from app.core.database import NeonSession, LocalSession
from app.core.metrics import metrics, Timer
from app.core.redis_streams import consume_loop, emit as redis_emit
from app.models.nutrition import FoodEvent, FoodEventNutrition
from app.pipeline.food_ner import food_ner
from app.pipeline.nutrition_lookup import nutrition_lookup
from app.pipeline.nutrition_estimator import nutrition_estimator

log = structlog.get_logger()
settings = get_settings()


def utcnow():
    return datetime.now(timezone.utc)


# ── Event processing ──────────────────────────────────────────

async def process_event(event_id: str, user_id: str, redis: Redis):
    """
    Full enrichment pipeline for one food event.
    Reads event from DB, enriches, writes results back.
    """
    async with NeonSession() as neon_db:
        # ── Fetch the event ───────────────────────────────────
        result = await neon_db.execute(
            select(FoodEvent).where(FoodEvent.id == uuid.UUID(event_id))
        )
        event = result.scalar_one_or_none()

        if not event:
            log.error("enrichment.event_not_found", event_id=event_id)
            return

        if event.enrichment_status == "done":
            log.info("enrichment.already_done", event_id=event_id)
            return

        # ── Mark as processing ────────────────────────────────
        await neon_db.execute(
            update(FoodEvent)
            .where(FoodEvent.id == event.id)
            .values(enrichment_status="processing")
        )
        await neon_db.commit()

        with Timer() as total_timer:
            try:
                nutrition_data = await _run_pipeline(event)
            except Exception as e:
                log.error("enrichment.pipeline_failed", event_id=event_id, error=str(e))
                await neon_db.execute(
                    update(FoodEvent)
                    .where(FoodEvent.id == event.id)
                    .values(enrichment_status="failed")
                )
                await neon_db.commit()
                metrics.total_events_failed += 1
                return

        metrics.enrichment_latency.record(total_timer.elapsed_ms)

        # ── Write nutrition result ────────────────────────────
        # Check if nutrition record already exists (idempotency)
        existing = await neon_db.execute(
            select(FoodEventNutrition).where(FoodEventNutrition.event_id == event.id)
        )
        if not existing.scalar_one_or_none():
            neon_db.add(FoodEventNutrition(
                event_id=event.id,
                dish_name=nutrition_data["dish_name"],
                estimated_nutrition=nutrition_data["nutrition"],
                confidence_score=nutrition_data["confidence"],
                model_version=nutrition_data["model_version"],
                ingredients_inferred=nutrition_data.get("ingredients", []),
                cuisine_type=nutrition_data.get("cuisine_type"),
                portion_size_estimate=nutrition_data.get("portion_size"),
            ))

        # ── Mark as done ──────────────────────────────────────
        await neon_db.execute(
            update(FoodEvent)
            .where(FoodEvent.id == event.id)
            .values(
                enrichment_status="done",
                enriched_at=utcnow(),
            )
        )
        await neon_db.commit()

        # ── Publish to food.events.enriched ───────────────────
        enriched_msg = {
            "event_id": event_id,
            "user_id": user_id,
            "dish_name": nutrition_data["dish_name"],
            "enriched_at": utcnow().isoformat(),
        }
        await redis_emit(redis, "food.events.enriched", enriched_msg)

        metrics.total_events_processed += 1
        log.info(
            "enrichment.done",
            event_id=event_id,
            dish=nutrition_data["dish_name"],
            confidence=nutrition_data["confidence"],
            model=nutrition_data["model_version"],
            latency_ms=total_timer.elapsed_ms,
        )


async def _run_pipeline(event: FoodEvent) -> dict:
    """
    Core enrichment logic. Returns nutrition dict.
    """
    raw_input = event.raw_input or {}
    event_type = event.event_type

    # ── Step 1: Get text description ─────────────────────────
    if event_type == "manual_log":
        description = raw_input.get("description", "")
    elif event_type == "order":
        # Build description from order items
        items = raw_input.get("items", [])
        description = ", ".join(
            item.get("name", "") for item in items if item.get("name")
        )
    elif event_type == "import":
        items = raw_input.get("items", [])
        description = ", ".join(
            item.get("name", "") for item in items if item.get("name")
        )
    elif event_type == "photo_log":
        # Photo events are handled by vision worker separately
        # If we get here it means vision worker hasn't processed it yet
        description = raw_input.get("description", "food photo")
    elif event_type == "barcode_scan":
        description = raw_input.get("product_name", raw_input.get("description", ""))
    else:
        description = raw_input.get("description", str(raw_input))

    if not description.strip():
        description = "unknown food"

    # ── Step 2: NER — extract dish name ──────────────────────
    dish_name, ner_confidence = food_ner.top_dish(description)

    log.debug("enrichment.ner_result", description=description[:60], dish=dish_name, conf=ner_confidence)

    # ── Step 3: KB Lookup ─────────────────────────────────────
    lookup_result = nutrition_lookup.lookup(dish_name)

    if lookup_result:
        # ── KB Hit ────────────────────────────────────────────
        nutrition = dict(lookup_result.nutrition)

        # Add GI/GL if present in KB
        if lookup_result.glycemic_index:
            nutrition["glycemic_index"] = lookup_result.glycemic_index
        if lookup_result.glycemic_load:
            nutrition["glycemic_load"] = lookup_result.glycemic_load

        return {
            "dish_name": lookup_result.dish_name,
            "nutrition": nutrition,
            "confidence": lookup_result.confidence,
            "model_version": f"kb_{lookup_result.matched_on}_v1",
            "ingredients": lookup_result.ingredients,
            "cuisine_type": lookup_result.cuisine_type,
            "portion_size": f"{lookup_result.serving_size_g}g" if lookup_result.serving_size_g else None,
        }

    # ── Step 4: Ingredient Estimator (fallback) ───────────────
    async with LocalSession() as local_db:
        est_result = await nutrition_estimator.estimate(dish_name, local_db)

    return {
        "dish_name": est_result.dish_name,
        "nutrition": est_result.estimated_nutrition,
        "confidence": est_result.confidence,
        "model_version": est_result.model_version,
        "ingredients": est_result.ingredients_used,
        "cuisine_type": None,
        "portion_size": "250g",  # default serving
    }


# ── Worker loop ───────────────────────────────────────────────

# Backoff schedule for reconnect attempts after a connection-level failure.
# Previously NONE of this was caught — only per-message failures inside
# the loop were wrapped in try/except, so any connection-level exception
# propagated straight out of run_enrichment_worker(), silently killing the
# asyncio task. main.py's health check would then report "stopped"
# forever, with the actual exception never logged anywhere — nothing ever
# calls task.exception() on a fire-and-forget asyncio.create_task().
_RECONNECT_BACKOFF_SECONDS = [2, 5, 10, 20, 30]


async def run_enrichment_worker():
    """
    Main consumer loop — Redis Streams version.
    Consumes from food.events.raw, processes each event.

    Retries the whole connect-and-consume cycle on any connection-level
    failure (not just per-message ones, which were already handled) with
    exponential backoff, and logs the real exception every time instead of
    dying silently. asyncio.CancelledError (graceful shutdown via
    main.py's task.cancel()) is re-raised immediately, not retried.
    """
    attempt = 0

    while True:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)

        try:
            log.info("enrichment_worker.starting", redis=settings.redis_url, attempt=attempt + 1)

            # Load KB into memory before starting consumption
            async with LocalSession() as local_db:
                await nutrition_lookup.load(local_db)

            # Load spaCy model
            food_ner.load()

            log.info("enrichment_worker.ready", kb_entries=nutrition_lookup.entry_count)
            attempt = 0  # reset backoff once we're actually connected and consuming

            async def handle_message(data: dict, key):
                event_id = data.get("event_id")
                user_id = data.get("user_id")

                if not event_id or not user_id:
                    log.warning("enrichment_worker.missing_fields", data=data)
                    return

                log.info("enrichment_worker.received", event_id=event_id, user_id=user_id)

                try:
                    await process_event(event_id, user_id, redis)
                except Exception as e:
                    log.error(
                        "enrichment_worker.unhandled_error",
                        event_id=event_id,
                        error=str(e),
                        exc_info=True,
                    )

                # Log metrics summary every 100 events
                if metrics.total_events_processed % 100 == 0 and metrics.total_events_processed > 0:
                    metrics.log_summary()

            await consume_loop(
                redis,
                stream="food.events.raw",
                group=settings.kafka_consumer_group_enrichment,
                consumer_name="enrichment-worker-1",
                handler=handle_message,
            )

        except asyncio.CancelledError:
            # Graceful shutdown (main.py cancels this task) — stop cleanly,
            # do NOT treat this as a connection failure to retry.
            raise

        except Exception as e:
            # This is the exact class of failure that previously killed the
            # worker silently — now it's actually logged with the real
            # cause, and the worker retries instead of staying "stopped"
            # forever.
            wait_s = _RECONNECT_BACKOFF_SECONDS[min(attempt, len(_RECONNECT_BACKOFF_SECONDS) - 1)]
            log.error(
                "enrichment_worker.connection_failed",
                error=str(e),
                exc_info=True,
                retry_in_seconds=wait_s,
                attempt=attempt + 1,
            )
            attempt += 1
            await asyncio.sleep(wait_s)
            continue

        finally:
            await redis.close()
            log.info("enrichment_worker.stopped")


if __name__ == "__main__":
    asyncio.run(run_enrichment_worker())