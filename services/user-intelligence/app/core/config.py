from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "NARA User Intelligence Service"
    environment: str = "development"
    debug: bool = False

    # Neon DB — user/health data
    database_url: str = "postgresql+asyncpg://nara:nara_secret@localhost:5432/nara"

    # Local DB — food graph aggregates (heavy data)
    local_database_url: str = "postgresql+asyncpg://nara:nara_secret@localhost:5432/nara_data"

    # Redis
    redis_url: str = "redis://:nara_redis_secret@localhost:6379/0"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:29092"

    # JWT — same secret as auth service for token validation
    jwt_secret_key: str = "change_me_in_production"
    jwt_algorithm: str = "HS256"

    # Food graph cache TTL seconds
    food_graph_cache_ttl: int = 900       # 15 minutes
    gap_cache_ttl: int = 300              # 5 minutes

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
