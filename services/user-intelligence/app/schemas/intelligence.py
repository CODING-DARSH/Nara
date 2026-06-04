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
