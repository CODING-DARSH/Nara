from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "NARA Ingestion Service"
    environment: str = "development"
    debug: bool = False

    # Neon DB
    database_url: str

    # Redis
    redis_url: str

    # Kafka
    kafka_bootstrap_servers: str = "localhost:29092"

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_secure: bool = False
    photo_bucket: str = "nara-food-photos-raw"
    photo_processed_bucket: str = "nara-food-photos-processed"

    # Upload limits
    max_photo_size_mb: int = 10
    allowed_photo_types: list = ["image/jpeg", "image/png", "image/webp"]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()



