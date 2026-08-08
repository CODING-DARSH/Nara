"""
ML Inference Service — ORM Models
Two databases, two sets of models.

NeonModels  : FoodEvent, FoodEventNutrition   (user data on Neon)
LocalModels : NutritionKB                      (reference data on local Postgres)
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Text, Float, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase


def utcnow():
    return datetime.now(timezone.utc)


# ── Base classes (one per DB so metadata stays separate) ──────

class NeonBase(DeclarativeBase):
    pass


class LocalBase(DeclarativeBase):
    pass


# ── Neon: food_events ─────────────────────────────────────────

class FoodEvent(NeonBase):
    __tablename__ = "food_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_ref: Mapped[dict] = mapped_column(JSONB, nullable=True)
    raw_input: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    meal_context: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    enrichment_status: Mapped[str] = mapped_column(Text, default="pending", nullable=False)
    enriched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Neon: food_event_nutrition ────────────────────────────────

class FoodEventNutrition(NeonBase):
    __tablename__ = "food_event_nutrition"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)

    dish_name: Mapped[str] = mapped_column(Text, nullable=False)

    # Full macro profile: {calories, protein_g, carbs_g, fat_g, fiber_g, sugar_g,
    #                       sodium_mg, cholesterol_mg, glycemic_index, glycemic_load}
    estimated_nutrition: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # 1.0 = exact KB match, 0.8 = fuzzy match, 0.5 = ingredient estimation, 0.3 = vision fallback
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # e.g. "kb_exact_v1", "kb_fuzzy_v1", "ingredient_estimator_v1", "vision_claude_v1"
    model_version: Mapped[str] = mapped_column(Text, nullable=True)

    # Ingredients used if fallback estimator was triggered
    ingredients_inferred: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    cuisine_type: Mapped[str] = mapped_column(Text, nullable=True)
    portion_size_estimate: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Local: nutrition_kb ───────────────────────────────────────

class NutritionKB(LocalBase):
    __tablename__ = "nutrition_kb"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    dish_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    # ["chicken biriyani", "hyderabadi biryani", "biryani rice", ...]
    aliases: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    cuisine_type: Mapped[str] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=True)

    # {"calories": 250, "protein_g": 12.0, "carbs_g": 35.0, ...}
    per_100g: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    per_serving: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    serving_size_g: Mapped[float] = mapped_column(Float, nullable=True)

    # ["rice", "chicken", "spices", ...]  used by estimator fallback
    ingredients: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    allergens: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    is_veg: Mapped[bool] = mapped_column(Boolean, nullable=True)
    glycemic_index: Mapped[float] = mapped_column(Float, nullable=True)
    glycemic_load: Mapped[float] = mapped_column(Float, nullable=True)

    # How trustworthy is this entry: 1.0 = verified, 0.7 = estimated
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
