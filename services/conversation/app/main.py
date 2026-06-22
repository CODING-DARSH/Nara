"""
NARA — Conversation Service
Port 8006
"""
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.agents.intent import load_classifier
from app.agents.ner import load_ner
from app.routers.chat import router as chat_router

log      = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("conversation_service.starting")
    load_classifier()
    load_ner()
    log.info("conversation_service.ready")
    yield
    log.info("conversation_service.stopping")


app = FastAPI(
    title="NARA Conversation Service",
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

app.include_router(chat_router)


@app.get("/health")
async def health():
    return {
        "status":  "healthy",
        "service": "conversation",
        "models": {
            "intent": settings.intent_model,
            "ner":    settings.ner_model,
            "response": settings.response_model,
        }
    }