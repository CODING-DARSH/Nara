import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.redis import close_redis
from app.routers.health_profile import router as health_router
from app.routers.food_graph import router as graph_router

settings = get_settings()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("nara.user-intelligence.startup", environment=settings.environment)
    yield
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
    return {"status": "ok", "service": "nara-user-intelligence"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
