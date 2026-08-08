from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, field_validator


# ── Health Profile ─────────────────────────────────────────────

VALID_CONDITIONS = {
    "prediabetes", "type2_diabetes", "type1_diabetes",
    "hypertension", "high_cholesterol", "obesity",
    "lactose_intolerance", "gluten_intolerance", "celiac",
    "pcos", "thyroid", "ibs", "gerd", "fatty_liver",
    "anemia", "osteoporosis", "kidney_disease"
}

VALID_RESTRICTIONS = {
    "vegetarian", "vegan", "jain", "eggetarian",
    "no_onion_garlic", "gluten_free", "dairy_free",
    "keto", "low_carb", "low_sodium", "low_fat", "halal"
}

VALID_ALLERGENS = {
    "peanuts", "tree_nuts", "shellfish", "fish",
    "eggs", "milk", "soy", "wheat", "sesame"
}

VALID_ACTIVITY = {"sedentary", "lightly_active", "moderately_active", "very_active"}

# ── Added: validation for previously-hardcoded ranker/occasion features ──

# CONFIRMED against real services/ml-training/models/encoders.joblib via
# inspect_encoders.py. Two corrections from the earlier placeholder guess:
#   - region needed "northeast" added (real encoder has 5 classes, not 4)
#   - stress_level needed "extreme" removed (real encoder has 4 classes:
#     high/low/medium/none — no "extreme")
VALID_INCOME_TIERS = {"low", "medium", "high"}

VALID_REGIONS = {"north", "south", "east", "west", "northeast"}

# TODO(darsh): these two are still placeholder enums — UNVERIFIABLE from
# any existing file. meal_occasion_classifier/*.py fits its own FeatureEncoder
# during training but never calls .save() on it (only
# recommendation_ranker/train_logistic.py does, and only for the ranker's
# own encoder — confirmed via inspect_encoders.py + reading the training
# scripts directly). The occasion classifier's real occupation/
# living_situation classes only existed in-memory during that training run
# and aren't recoverable without adding encoder.save(...) and re-running it.
VALID_OCCUPATIONS = {
    "student", "salaried", "self_employed", "homemaker", "unemployed", "retired",
}
VALID_LIVING_SITUATIONS = {
    "alone", "with_family", "with_roommates", "with_partner",
}
# CONFIRMED — matches the ranker's real context_stress encoder exactly.
VALID_STRESS_LEVELS = {"none", "low", "medium", "high"}


class HealthProfileCreate(BaseModel):
    declared_conditions: list[str] = []
    dietary_restrictions: list[str] = []
    nutritional_goals: dict = {}
    allergies: list[str] = []
    cuisine_preferences: dict = {}
    budget_preferences: dict = {}
    activity_level: str = "moderately_active"
    age: Optional[int] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    gender: Optional[str] = None

    # Added — see model comments in models/intelligence.py for why these
    # exist: they replace hardcoded constants previously sent to the
    # ranker and occasion-classifier models for every single user.
    income_tier: Optional[str] = None
    region: Optional[str] = None
    occupation: Optional[str] = None
    living_situation: Optional[str] = None
    stress_level: Optional[str] = None
    is_wfh: Optional[bool] = None

    @field_validator("declared_conditions")
    @classmethod
    def validate_conditions(cls, v):
        invalid = set(v) - VALID_CONDITIONS
        if invalid:
            raise ValueError(f"Unknown conditions: {invalid}. Valid: {VALID_CONDITIONS}")
        return v

    @field_validator("dietary_restrictions")
    @classmethod
    def validate_restrictions(cls, v):
        invalid = set(v) - VALID_RESTRICTIONS
        if invalid:
            raise ValueError(f"Unknown restrictions: {invalid}. Valid: {VALID_RESTRICTIONS}")
        return v

    @field_validator("allergies")
    @classmethod
    def validate_allergies(cls, v):
        invalid = set(v) - VALID_ALLERGENS
        if invalid:
            raise ValueError(f"Unknown allergens: {invalid}. Valid: {VALID_ALLERGENS}")
        return v

    @field_validator("activity_level")
    @classmethod
    def validate_activity(cls, v):
        if v not in VALID_ACTIVITY:
            raise ValueError(f"activity_level must be one of: {VALID_ACTIVITY}")
        return v

    @field_validator("income_tier")
    @classmethod
    def validate_income_tier(cls, v):
        if v is not None and v not in VALID_INCOME_TIERS:
            raise ValueError(f"income_tier must be one of: {VALID_INCOME_TIERS}")
        return v

    @field_validator("region")
    @classmethod
    def validate_region(cls, v):
        if v is not None and v not in VALID_REGIONS:
            raise ValueError(f"region must be one of: {VALID_REGIONS}")
        return v

    @field_validator("occupation")
    @classmethod
    def validate_occupation(cls, v):
        if v is not None and v not in VALID_OCCUPATIONS:
            raise ValueError(f"occupation must be one of: {VALID_OCCUPATIONS}")
        return v

    @field_validator("living_situation")
    @classmethod
    def validate_living_situation(cls, v):
        if v is not None and v not in VALID_LIVING_SITUATIONS:
            raise ValueError(f"living_situation must be one of: {VALID_LIVING_SITUATIONS}")
        return v

    @field_validator("stress_level")
    @classmethod
    def validate_stress_level(cls, v):
        if v is not None and v not in VALID_STRESS_LEVELS:
            raise ValueError(f"stress_level must be one of: {VALID_STRESS_LEVELS}")
        return v

    @field_validator("nutritional_goals")
    @classmethod
    def validate_goals(cls, v):
        valid_keys = {
            "target_protein_g", "target_fiber_g", "target_carbs_g",
            "target_fat_g", "max_calories", "max_sugar_g",
            "max_sodium_mg", "min_calories"
        }
        invalid = set(v.keys()) - valid_keys
        if invalid:
            raise ValueError(f"Unknown goal keys: {invalid}. Valid: {valid_keys}")
        return v


class HealthProfileUpdate(HealthProfileCreate):
    pass


class HealthProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    version: int
    declared_conditions: list
    dietary_restrictions: list
    nutritional_goals: dict
    allergies: list
    cuisine_preferences: dict
    budget_preferences: dict
    activity_level: str
    age: Optional[int]
    weight_kg: Optional[float]
    height_cm: Optional[float]
    gender: Optional[str]
    income_tier: Optional[str]
    region: Optional[str]
    occupation: Optional[str]
    living_situation: Optional[str]
    stress_level: Optional[str]
    is_wfh: Optional[bool]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Food Graph ─────────────────────────────────────────────────

class NutritionalGap(BaseModel):
    nutrient: str
    target: float
    actual_avg: float
    deficit_pct: float
    consecutive_days: int
    severity: str  # low / medium / high


class FoodGraphResponse(BaseModel):
    user_id: UUID
    last_24h: dict
    last_7d: dict
    last_30d: dict
    nutritional_gaps: list
    cuisine_affinity: dict
    meal_timing_patterns: dict
    top_dishes: list
    detected_patterns: dict
    total_meals_logged: int
    total_meals_pending: int
    last_computed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Insights ───────────────────────────────────────────────────

class InsightResponse(BaseModel):
    gaps: list[NutritionalGap]
    summary: str
    recommendations_hint: list[str]  # plain-english hints fed to recommendation engine


# ── Generic ────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
