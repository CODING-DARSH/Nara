import asyncio
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.redis import close_redis
from app.routers.health_profile import router as health_router
from app.routers.food_graph import router as graph_router
from app.workers.graph_update_worker import run_worker as run_graph_update_worker

settings = get_settings()
log = structlog.get_logger()

# Worker task handle (for clean shutdown)
_worker_tasks: dict[str, asyncio.Task] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("nara.user-intelligence.startup", environment=settings.environment)

    # Start the Kafka consumer that recomputes the food graph whenever
    # ml-inference publishes to food.events.enriched. Previously this
    # only ran if you launched graph_update_worker.py as its own process
    # (`python -m app.workers.graph_update_worker`), which the Dockerfile
    # never did — so the food graph never updated automatically after a
    # meal was logged. This mirrors how ml-inference starts its own
    # Kafka consumers in main.py's lifespan.
    _worker_tasks["graph_update"] = asyncio.create_task(
        run_graph_update_worker(),
        name="graph_update_worker",
    )
    log.info("nara.user-intelligence.workers_started")

    yield

    log.info("nara.user-intelligence.shutting_down")
    for name, task in _worker_tasks.items():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            log.info("nara.user-intelligence.worker_stopped", worker=name)

    await close_redis()
    log.info("nara.user-intelligence.shutdown")


app = FastAPI(
    title="NARA User Intelligence Service",
    version="0.1.0",
    description="Health profiles, food graph, and nutritional intelligence",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    log.info("http.request", method=request.method, path=request.url.path, status=response.status_code)
    return response


app.include_router(health_router)
app.include_router(graph_router)


@app.get("/health")
async def health():
    worker_status = {
        name: "running" if not task.done() else "stopped"
        for name, task in _worker_tasks.items()
    }
    return {
        "status": "ok",
        "service": "nara-user-intelligence",
        "workers": worker_status,
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})