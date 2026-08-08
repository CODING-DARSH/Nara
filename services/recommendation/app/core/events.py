"""
NARA — Raw Event Logging

Writes every impression/click/skip/order to recommendation_events in Neon
(see app/migrations/004_recommendation_events.sql for the full schema and
reasoning). This is intentionally separate from:
  - core/kafka.py's publish_feedback_event — that's for ASYNC processing
    (the user-intelligence consumer nudging cuisine_affinity). This module
    is for DURABLE STORAGE of the raw event itself, regardless of whether
    anything needs to react to it.
  - core/redis.record_dish_interaction — that's a live, TTL-bound
    aggregate the ranker reads on every request. This module is the
    permanent record underneath it.

All three can fire for the same user action — they serve different
purposes and none of them replaces another.

Logging failures here MUST NEVER break the user-facing request — same
"best-effort" contract as the Redis/Kafka helpers.
"""
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import text

from app.core.database import NeonSession

log = logging.getLogger("nara.recommendation.events")

VALID_EVENT_TYPES = {"impression", "click", "skip", "order"}


async def log_event(
    user_id: str,
    event_type: str,
    dish_name: str,
    cuisine_type: Optional[str] = None,
    restaurant_id: Optional[str] = None,
    occasion: Optional[str] = None,
    rank: Optional[int] = None,
    score: Optional[float] = None,
    session_id: Optional[str] = None,
    model_variant: str = "production",
):
    if event_type not in VALID_EVENT_TYPES:
        log.warning(f"events.invalid_event_type event_type={event_type}")
        return
    try:
        async with NeonSession() as db:
            await db.execute(
                text("""
                    INSERT INTO recommendation_events
                        (user_id, event_type, dish_name, cuisine_type, restaurant_id,
                         occasion, rank, score, session_id, model_variant)
                    VALUES
                        (:user_id, :event_type, :dish_name, :cuisine_type, :restaurant_id,
                         :occasion, :rank, :score, :session_id, :model_variant)
                """),
                {
                    "user_id":       user_id,
                    "event_type":    event_type,
                    "dish_name":     dish_name,
                    "cuisine_type":  cuisine_type,
                    "restaurant_id": restaurant_id,
                    "occasion":      occasion,
                    "rank":          rank,
                    "score":         score,
                    "session_id":    session_id,
                    "model_variant": model_variant,
                },
            )
            await db.commit()
    except Exception as e:
        # Best-effort — never break the user-facing request over a
        # logging failure. Loud enough to notice in logs, not loud enough
        # to matter to the response.
        log.warning(f"events.log_failed event_type={event_type} dish_name={dish_name} error={e}")


async def log_events_bulk(events: list[dict]):
    """
    Log multiple events in one transaction — used for impressions, where
    a single recommendation request produces N rows (one per dish shown)
    that all belong together. Cheaper than N separate log_event() calls,
    and means a partial failure doesn't leave half a shown-list logged.
    """
    if not events:
        return
    try:
        async with NeonSession() as db:
            for e in events:
                if e.get("event_type") not in VALID_EVENT_TYPES:
                    continue
                await db.execute(
                    text("""
                        INSERT INTO recommendation_events
                            (user_id, event_type, dish_name, cuisine_type, restaurant_id,
                             occasion, rank, score, session_id, model_variant)
                        VALUES
                            (:user_id, :event_type, :dish_name, :cuisine_type, :restaurant_id,
                             :occasion, :rank, :score, :session_id, :model_variant)
                    """),
                    {
                        "user_id":       e.get("user_id"),
                        "event_type":    e.get("event_type"),
                        "dish_name":     e.get("dish_name"),
                        "cuisine_type":  e.get("cuisine_type"),
                        "restaurant_id": e.get("restaurant_id"),
                        "occasion":      e.get("occasion"),
                        "rank":          e.get("rank"),
                        "score":         e.get("score"),
                        "session_id":    e.get("session_id"),
                        "model_variant": e.get("model_variant", "production"),
                    },
                )
            await db.commit()
    except Exception as e:
        log.warning(f"events.log_bulk_failed count={len(events)} error={e}")
