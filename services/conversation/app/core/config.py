"""
NARA — Conversation Service Config
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "conversation"
    environment:  str = "development"

    neon_database_url: str

    jwt_secret_key: str
    jwt_algorithm:  str = "HS256"

    user_intelligence_url:  str = "http://user-intelligence-service:8002"
    recommendation_url:     str = "http://recommendation-service:8005"
    ml_inference_url:       str = "http://ml-inference-service:8004"

    # ── NLP Models ────────────────────────────────────────────
    # Intent classifier — swap path here when fine-tuned
    intent_model: str = "distilbert-base-uncased"
    # NER model — swap path here when fine-tuned
    ner_model:    str = "en_core_web_sm"
    # Response model — swap here when Flan-T5 fine-tuned
    response_model: str = "template"  # template / flan-t5

    # ── Intent classes ────────────────────────────────────────
    intent_labels: list = [
        "get_recommendation",
        "log_meal",
        "ask_nutrition",
        "check_food_graph",
        "set_preference",
        "order_food",
        "general_chat",
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()

