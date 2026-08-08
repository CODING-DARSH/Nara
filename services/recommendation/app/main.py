"""
NARA — Recommendation Service
Port 8005
"""
from contextlib import asynccontextmanager
import logging
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import check_connections
from app.core.model_loader import model_store
from app.core.kafka import start_kafka_producer, stop_kafka_producer
from app.core.redis import close_redis
from app.routers.recommend import router as recommend_router
from app.routers.orders import router as orders_router

log      = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("recommendation_service.starting")
    model_store.load_all(settings.models_dir)
    # Feedback loop: recommendation.feedback topic existed in kafka-init but
    # nothing produced to it — this is the producer for impression/feedback
    # events (see app/core/kafka.py and the /v1/recommend/feedback endpoint).
    await start_kafka_producer()
    log.info("recommendation_service.ready", models=model_store.status())
    yield
    log.info("recommendation_service.stopping")
    await stop_kafka_producer()
    await close_redis()


app = FastAPI(
    title="NARA Recommendation Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommend_router)
app.include_router(orders_router)


@app.get("/health")
async def health():
    db = await check_connections()
    return {
        "status":  "healthy" if all(v == "ok" for v in db.values()) else "degraded",
        "service": "recommendation",
        "databases": db,
        "models":  model_store.status(),
    }
