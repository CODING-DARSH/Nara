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
    neon_database_url: str
    local_database_url: str
    # ── Services ──────────────────────────────────────────────
    user_intelligence_url: str = "http://user-intelligence-service:8002"
    ml_inference_url: str = "http://ml-inference-service:8004"


    # ── Redis ─────────────────────────────────────────────────
    redis_url: str

    # ── JWT ───────────────────────────────────────────────────
    jwt_secret_key: str
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

