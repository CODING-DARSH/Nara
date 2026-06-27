"""
ML Inference Service — Entry Point
FastAPI app with:
  - /health    : DB connectivity + worker status
  - /metrics   : latency, hit rates, confidence scores (baseline for Sprint 5 comparison)
  - /kb/stats  : nutrition KB coverage stats

Both Kafka workers run as asyncio background tasks.
"""
import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import check_db_connections, LocalSession
from app.core.metrics import metrics
from app.pipeline.food_ner import food_ner
from app.pipeline.nutrition_lookup import nutrition_lookup
from app.workers.enrichment_worker import run_enrichment_worker
from app.workers.vision_worker import run_vision_worker

log = structlog.get_logger()
settings = get_settings()

# ── Worker task handles (for health checks) ───────────────────
_worker_tasks: dict[str, asyncio.Task] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load models + KB, start workers. Shutdown: cancel workers."""
    log.info("ml_inference.starting")

    # Load spaCy model
    food_ner.load()

    # Load nutrition KB into memory
    async with LocalSession() as db:
        await nutrition_lookup.load(db)

    log.info(
        "ml_inference.models_loaded",
        kb_entries=nutrition_lookup.entry_count,
        spacy_model=settings.spacy_model,
    )

    # Start Kafka workers as background tasks
    _worker_tasks["enrichment"] = asyncio.create_task(
        run_enrichment_worker(),
        name="enrichment_worker",
    )
    _worker_tasks["vision"] = asyncio.create_task(
        run_vision_worker(),
        name="vision_worker",
    )

    log.info("ml_inference.workers_started")
    yield

    # Shutdown
    log.info("ml_inference.shutting_down")
    for name, task in _worker_tasks.items():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            log.info(f"ml_inference.worker_stopped", worker=name)


app = FastAPI(
    title="NARA ML Inference Service",
    version="0.1.0",
    description="Food enrichment pipeline — NER, KB lookup, ingredient estimation",
    lifespan=lifespan,
)


# ── Health ────────────────────────────────────────────────────

@app.get("/health")
async def health():
    db_status = await check_db_connections()

    worker_status = {
        name: "running" if not task.done() else "stopped"
        for name, task in _worker_tasks.items()
    }

    all_healthy = (
        all(v == "ok" for v in db_status.values())
        and all(v == "running" for v in worker_status.values())
        and nutrition_lookup.is_loaded
    )

    return JSONResponse(
        status_code=200 if all_healthy else 503,
        content={
            "status": "healthy" if all_healthy else "degraded",
            "service": "ml-inference",
            "databases": db_status,
            "workers": worker_status,
            "kb_loaded": nutrition_lookup.is_loaded,
            "kb_entries": nutrition_lookup.entry_count,
        },
    )

@app.get("/debug/workers")
async def debug_workers():
    result = {}

    for name, task in _worker_tasks.items():
        result[name] = {
            "done": task.done(),
            "cancelled": task.cancelled(),
            "exception": str(task.exception()) if task.done() else None,
        }

    return result
# ── Metrics ───────────────────────────────────────────────────

@app.get("/metrics")
async def get_metrics():
    """
    Sprint 4 baseline metrics.
    Compare these numbers against Sprint 5 model performance.

    Key metrics to watch:
      - kb_hit.rate        : target > 0.6 with 500+ dishes
      - enrichment_e2e.p95 : target < 200ms
      - ner.p95            : target < 50ms
      - ner_confidence.mean: target > 0.7
    """
    return metrics.summary()


# ── KB Stats ──────────────────────────────────────────────────

@app.get("/kb/stats")
async def kb_stats():
    """
    Nutrition KB coverage stats.
    Use this to track progress toward 500+ dish target for Sprint 5.
    """
    return {
        "total_entries": nutrition_lookup.entry_count,
        "target_for_sprint5": 500,
        "coverage_percent": round(
            (nutrition_lookup.entry_count / 500) * 100, 1
        ),
        "kb_loaded": nutrition_lookup.is_loaded,
        "note": (
            "KB hit rate will be low (~20-30%) until 500+ dishes are seeded. "
            "Run seed scripts to improve coverage before Sprint 5."
        ),
    }


# ── NER test endpoint (dev only) ──────────────────────────────

@app.post("/debug/ner")
async def test_ner(body: dict):
    """
    Dev endpoint to test NER extraction.
    POST {"text": "had idli and sambar for breakfast"}
    """
    text = body.get("text", "")
    if not text:
        return {"error": "text field required"}

    candidates = food_ner.extract(text)
    return {
        "input": text,
        "candidates": [
            {"name": c.name, "confidence": c.confidence, "source": c.source}
            for c in candidates
        ],
    }


# ── Lookup test endpoint (dev only) ──────────────────────────

@app.post("/debug/lookup")
async def test_lookup(body: dict):
    """
    Dev endpoint to test KB fuzzy lookup.
    POST {"dish": "chicken biriyani"}
    """
    dish = body.get("dish", "")
    if not dish:
        return {"error": "dish field required"}

    result = nutrition_lookup.lookup(dish)
    if result:
        return {
            "found": True,
            "dish_name": result.dish_name,
            "matched_on": result.matched_on,
            "confidence": result.confidence,
            "cuisine_type": result.cuisine_type,
            "nutrition": result.nutrition,
        }
    return {"found": False, "dish": dish, "note": "Will use ingredient estimator"}