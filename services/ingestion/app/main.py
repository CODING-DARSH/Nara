import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.kafka import close_producer
from app.routers.meals import router as meals_router
from app.routers.import_orders import router as import_router

settings = get_settings()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("nara.ingestion.startup", environment=settings.environment)
    yield
    await close_producer()
    log.info("nara.ingestion.shutdown")


app = FastAPI(
    title="NARA Ingestion Service",
    version="0.1.0",
    description="Meal logging — text, photo, barcode, and order import",
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


app.include_router(meals_router)
app.include_router(import_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "nara-ingestion"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

