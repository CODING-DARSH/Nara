"""
NARA — Recommendation Service Config
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "recommendation"
    environment: str = "development"

    # ── Databases ─────────────────────────────────────────────
    neon_database_url: str = "postgresql+asyncpg://neondb_owner:npg_VUpS27YXsGKQ@ep-orange-lake-aoafbm87.c-2.ap-southeast-1.aws.neon.tech/neondb?ssl=require"
    local_database_url: str = "postgresql+asyncpg://nara:nara_secret@postgres:5432/nara_data"

    # ── Services ──────────────────────────────────────────────
    user_intelligence_url: str = "http://user-intelligence-service:8002"
    ml_inference_url: str = "http://ml-inference-service:8004"

    # ── Kafka ─────────────────────────────────────────────────
    kafka_bootstrap_servers: str = "kafka:9092"

    # ── Redis ─────────────────────────────────────────────────
    redis_url: str = "redis://:nara_redis_secret@redis:6379/1"

    # ── JWT ───────────────────────────────────────────────────
    jwt_secret_key: str = "super_secret_jwt_key_change_in_production"
    jwt_algorithm: str = "HS256"

    # ── Models dir ────────────────────────────────────────────
    models_dir: str = os.environ.get(
        "MODELS_DIR",
        "/app/models"
    )

    # ── Active models (change here to swap models) ────────────
    active_ranker: str = "lgbm"          # lgbm / xgboost / logistic
    active_cold_start: str = "wide_deep" # wide_deep / mlp / knn
    active_health_scorer: str = "xgb"   # xgb / rf / rules
    active_occasion: str = "xgb"        # xgb / rf / dt
    active_reorder: str = "xgb"         # xgb / rf / logistic

    # ── Recommendation settings ───────────────────────────────
    max_recommendations: int = 10
    min_confidence_score: float = 0.3
    location_radius_km: float = 5.0

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()