import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class UserHealthProfile(Base):
    __tablename__ = "user_health_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Health conditions declared by user
    # e.g. ["prediabetes", "hypertension", "lactose_intolerance", "pcos"]
    declared_conditions: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)

    # Hard dietary restrictions
    # e.g. ["vegetarian", "vegan", "jain", "no_onion_garlic", "gluten_free"]
    dietary_restrictions: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)

    # Nutritional targets
    # e.g. {"target_protein_g": 80, "target_fiber_g": 25, "max_sugar_g": 30, "max_calories": 2000}
    nutritional_goals: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Hard allergens — never show dishes with these
    # e.g. ["peanuts", "shellfish", "tree_nuts", "soy"]
    allergies: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)

    # Wearable devices connected
    # e.g. {"apple_health": true, "google_fit": false, "cgm_brand": "libre"}
    wearable_integrations: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Cuisine preferences for Bangalore context
    # e.g. {"loved": ["south_indian", "north_indian"], "disliked": ["chinese"]}
    cuisine_preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Budget preferences
    # e.g. {"weekday_max": 300, "weekend_max": 600, "preferred_range": [150, 400]}
    budget_preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Activity level affects caloric needs
    # sedentary / lightly_active / moderately_active / very_active
    activity_level: Mapped[str] = mapped_column(Text, default="moderately_active", nullable=False)

    # Basic physical stats for caloric calculations
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=True)
    height_cm: Mapped[float] = mapped_column(Float, nullable=True)
    gender: Mapped[str] = mapped_column(Text, nullable=True)  # male/female/other

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # ── Added: real signal for previously-hardcoded ranker/occasion features ──
    # These were constants in recommendation/app/routers/recommend.py
    # (_build_user) and ranker.py (detect_occasion) for every user. Now
    # collected at onboarding so the trained models see real per-user
    # signal instead of the same value for everyone.

    # Ranker categorical feature "income_tier" — self-reported, no honest
    # way to infer this from behavior. NULL = not yet provided; treated as
    # "unknown" downstream, never silently defaulted to "medium".
    income_tier: Mapped[str] = mapped_column(Text, nullable=True)  # low / medium / high

    # Ranker categorical feature "region" — derived once from the state the
    # user selects at onboarding (see _state_to_region in recommend.py),
    # stored directly rather than recomputed from birthplace each request.
    region: Mapped[str] = mapped_column(Text, nullable=True)  # north / south / east / west

    # Occasion classifier categorical features. Same reasoning: no honest
    # proxy exists without asking, so these stay NULL until the user sets
    # them (Profile page) rather than being faked as a fixed encoded value
    # (the old code sent literal 0/2/0/0/0 for every user, every request).
    occupation: Mapped[str] = mapped_column(Text, nullable=True)
    living_situation: Mapped[str] = mapped_column(Text, nullable=True)
    stress_level: Mapped[str] = mapped_column(Text, nullable=True)
    is_wfh: Mapped[bool] = mapped_column(Boolean, nullable=True)


class FoodGraph(Base):
    """
    Pre-aggregated food intelligence per user.
    Updated async by Kafka worker when food events are enriched.
    Cached in Redis. Source of truth for recommendation engine.
    """
    __tablename__ = "food_graphs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    # Rolling nutritional windows
    # {"protein_g": 45.2, "carbs_g": 180.3, "fat_g": 32.1, "fiber_g": 8.4, "calories": 1240}
    last_24h: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    last_7d: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    last_30d: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Nutritional gaps detected
    # [{"nutrient": "fiber_g", "target": 25, "actual_avg": 8.4, "deficit_pct": 0.66, "consecutive_days": 5}]
    nutritional_gaps: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)

    # Cuisine affinity scores learned from behavior
    # {"south_indian": 0.72, "north_indian": 0.45, "chinese": 0.12, "biryani": 0.88}
    cuisine_affinity: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Meal timing patterns
    # {"breakfast_avg_hour": 8.5, "lunch_avg_hour": 13.2, "dinner_avg_hour": 20.1}
    meal_timing_patterns: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Top dishes ordered in last 30 days with counts
    # [{"dish": "biryani", "count": 8, "last_ordered": "2024-01-10"}, ...]
    top_dishes: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)

    # Detected eating patterns
    # {"skips_breakfast": true, "heavy_dinner": true, "consistent_lunch": false}
    detected_patterns: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Total meals logged (enrichment_status = 'done', counted toward graph)
    total_meals_logged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Meals logged in the same 30d window that are still enriching
    # (enrichment_status in 'pending'/'processing'). Lets the frontend show
    # "N meals still processing" instead of looking stale right after a log.
    total_meals_pending: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Last time graph was recomputed
    last_computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
