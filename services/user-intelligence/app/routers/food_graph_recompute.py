"""
NARA — Food Graph Refresh Fix Notes
─────────────────────────────────────────────────────────────
ROOT CAUSE (why food graph doesn't update after logging a meal):

The pipeline is:
  ingestion (8003) --POST /v1/meals/log--> food_events row (pending)
                    --kafka: food.events.raw-->
  ml-inference (8004) consumes --> enriches --> food_event_nutrition row
                    --kafka: food.events.enriched-->
  user-intelligence (8002) graph_update_worker.py consumes
                    --> recompute_food_graph() --> writes food_graphs row
                    --> invalidates Redis key foodgraph:{user_id}

This chain works (you saw it work in earlier testing — "food graph updated
with biryani"). The NEW symptom ("food graph isn't getting fetched newly
logged also") is most likely ONE of these three:

1. Redis cache not invalidated for THIS request's cache key.
   GET /v1/food-graph in user-intelligence likely does:
       cached = redis.get(f"foodgraph:{user_id}")
       if cached: return cached
   If the invalidation key format in graph_update_worker.py doesn't EXACTLY
   match the read path's key format, the UI keeps getting stale cached data
   even though the DB row is correct. This is the single most common cause
   of "logged a meal but graph didn't change."

2. Race condition: enrichment worker pipeline takes 100-300ms typically,
   but with model loading + Kafka overhead the full round trip
   (raw -> enriched -> graph recompute -> cache invalidate) can take
   1-3 seconds. If the frontend re-fetches food graph IMMEDIATELY after
   the 202 response from /meals/log, it's fetching before the graph
   worker has even run yet.

3. graph_update_worker.py container/process not running at all inside
   user-intelligence-service (it's meant to run as a background task
   alongside the FastAPI app, similar to how ml-inference runs its
   Kafka consumers in main.py's lifespan).

WHAT THIS FILE PROVIDES AS A FIX:
  - A manual /v1/food-graph/recompute endpoint (safety net): forces an
    immediate recompute + cache bust for the current user, bypassing
    Kafka entirely. The frontend calls this right after a meal log
    instead of just re-GETting /v1/food-graph, guaranteeing fresh data
    without needing to wait on Kafka timing.
  - This belongs in user-intelligence service at:
        app/routers/food_graph.py  (add this route to the existing router)
    or as a new file app/routers/food_graph_recompute.py included in main.py.

INTEGRATION STEPS (apply in services/user-intelligence):

1. Add this router function to your existing food_graph.py router
   (or create food_graph_recompute.py and include_router it in main.py).

2. Confirm graph_update_worker.py actually deletes the SAME redis key
   that health_profile/food_graph router reads. Both must use:
       f"foodgraph:{user_id}"
   identically — check both files side by side.

3. Confirm graph_update_worker() is started in user-intelligence's
   app/main.py lifespan, e.g.:
       asyncio.create_task(run_worker())
   The same pattern ml-inference/app/main.py already uses for its
   enrichment_worker and vision_worker.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer

from app.core.database import NeonSession
from app.core.redis import get_redis
from app.dependencies.auth import get_current_user  # adjust import to your actual path
from app.workers.graph_computer import compute_food_graph

log    = logging.getLogger("nara.user_intelligence.food_graph_recompute")
router = APIRouter(prefix="/v1/food-graph", tags=["food-graph"])
bearer = HTTPBearer()


@router.post("/recompute")
async def recompute_food_graph_now(current_user: dict = Depends(get_current_user)):
    """
    Safety-net endpoint: forces an immediate, synchronous food graph
    recompute for the current user and busts the Redis cache, bypassing
    the Kafka pipeline's timing entirely.

    Frontend should call this RIGHT AFTER a successful meal log POST,
    then re-fetch GET /v1/food-graph — guaranteed fresh data instead of
    racing the async enrichment pipeline.
    """
    user_id = current_user["user_id"]

    redis = await get_redis()
    await redis.delete(f"foodgraph:{user_id}")
    await redis.delete(f"insights:{user_id}")

    async with NeonSession() as db:
        graph = await compute_food_graph(UUID(user_id), db)

    if graph is None:
        log.info("food_graph.recompute.no_data", extra={"user_id": user_id})
        return {"recomputed": False, "message": "No meal data yet"}

    log.info("food_graph.recompute.done", extra={
        "user_id": user_id, "meals": graph.total_meals_logged,
    })
    return {
        "recomputed":       True,
        "total_meals_logged": graph.total_meals_logged,
        "last_computed_at":   str(graph.last_computed_at),
    }