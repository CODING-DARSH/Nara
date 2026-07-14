"""
ML Inference Service — Configuration
All settings from environment variables with sane dev defaults.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Service ───────────────────────────────────────────────
    service_name: str = "ml-inference"
    environment: str = "development"
    log_level: str = "INFO"

    # ── Databases ─────────────────────────────────────────────
    # Neon (user data — food_events, food_event_nutrition)
    neon_database_url: str = "postgresql+asyncpg://nara:nara_secret@localhost:5433/nara"

    # Local Postgres (nutrition_kb, restaurants)
    local_database_url: str = "postgresql+asyncpg://nara:nara_secret@postgres:5432/nara_data"

    # ── Kafka ─────────────────────────────────────────────────
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_consumer_group_enrichment: str = "ml-enrichment-workers"
    kafka_consumer_group_vision: str = "ml-vision-workers"

    # ── Claude Vision API ─────────────────────────────────────
    anthropic_api_key: str = ""
    vision_model: str = "claude-opus-4-5-20251101"
    vision_confidence_threshold: float = 0.4   # below this → flag for review

    # ── MinIO ─────────────────────────────────────────────────
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "nara_minio"
    minio_secret_key: str = "nara_minio_secret"
    minio_secure: bool = False
    minio_bucket_raw: str = "nara-food-photos-raw"

    # ── NER ───────────────────────────────────────────────────
    spacy_model: str = "en_core_web_sm"

    # ── Fuzzy Matching ────────────────────────────────────────
    # Minimum score (0-100) for a fuzzy match to be accepted
    fuzzy_match_threshold: int = 80

    # ── Metrics ───────────────────────────────────────────────
    # How many recent latency samples to keep in memory for reporting
    metrics_window_size: int = 1000

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()