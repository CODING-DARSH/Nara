"""
NARA — Recommendation Pipeline
Takes user context + food graph → returns ranked dish recommendations
"""
import logging
from datetime import datetime
from typing import Optional
import numpy as np
import pandas as pd

from app.core.model_loader import model_store

log = logging.getLogger("nara.recommendation.pipeline")

# ── Dish pool from nutrition KB ───────────────────────────────
# Loaded at startup from DB, used as candidate pool
DISH_CANDIDATES = []


def set_dish_candidates(dishes: list):
    global DISH_CANDIDATES
    DISH_CANDIDATES = dishes
    log.info(f"Dish candidates loaded: {len(DISH_CANDIDATES)}")


# ── Health rule-based scorer (fallback) ───────────────────────
def rule_health_score(dish: dict, conditions: list) -> float:
    gi = dish.get("glycemic_index", 55) or 55
    calories = dish.get("calories_kcal", 300) or 300

    score = 1.0
    if "type2_diabetes" in conditions or "prediabetes" in conditions:
        if gi > 70:
            score *= 0.2
        elif gi > 55:
            score *= 0.7
    if "hypertension" in conditions:
        if calories > 500:
            score *= 0.6
    if "obesity" in conditions:
        if calories > 600:
            score *= 0.5
    if "pcos" in conditions:
        if gi > 65:
            score *= 0.4
    return round(score, 3)


# ── Occasion detection (fallback) ─────────────────────────────
def rule_detect_occasion(hour: int, is_weekend: bool) -> str:
    if 5 <= hour < 10:
        return "breakfast"
    elif 10 <= hour < 15:
        return "lunch"
    elif 15 <= hour < 18:
        return "snack"
    elif 18 <= hour < 23:
        return "dinner"
    else:
        return "late_night"


# ── Occasion filter ───────────────────────────────────────────
OCCASION_CUISINE_FILTER = {
    "breakfast": ["south_indian", "north_indian", "staple", "beverage", "maharashtrian", "gujarati"],
    "lunch":     ["south_indian", "north_indian", "biryani", "gujarati", "maharashtrian", "bengali", "staple", "rajasthani"],
    "snack":     ["street_food", "south_indian", "beverage", "gujarati", "staple"],
    "dinner":    ["north_indian", "south_indian", "biryani", "bengali", "rajasthani", "staple", "goan"],
    "late_night":["street_food", "staple", "north_indian", "beverage"],
}


def filter_by_occasion(dishes: list, occasion: str) -> list:
    allowed = OCCASION_CUISINE_FILTER.get(occasion, [])
    if not allowed:
        return dishes
    filtered = [d for d in dishes if d.get("cuisine_type") in allowed]
    return filtered if filtered else dishes


def filter_by_dietary(dishes: list, restrictions: list, is_veg: bool) -> list:
    if not restrictions and not is_veg:
        return dishes

    result = []
    for dish in dishes:
        allergens = dish.get("allergens", [])
        if isinstance(allergens, str):
            allergens = allergens.split("|") if allergens else []

        skip = False

        # Vegetarian filter
        if is_veg and not dish.get("is_veg", True):
            continue

        # Restriction filters
        if "no_dairy" in restrictions and "milk" in allergens:
            skip = True
        if "no_gluten" in restrictions and "gluten" in allergens:
            skip = True
        if "halal" in restrictions and dish.get("cuisine_type") == "goan":
            skip = True  # pork-based dishes

        if not skip:
            result.append(dish)

    return result if result else dishes


# ── Main recommendation function ──────────────────────────────

def build_feature_vector(user: dict, dish: dict,
                          context: dict, rank: int) -> np.ndarray:
    """Build feature vector for ranker model."""
    hour    = context.get("hour", 13)
    day     = context.get("day_of_week", 0)
    budget  = context.get("budget_multiplier", 1.0)
    season  = context.get("season", "summer")
    stress  = context.get("stress_level", "medium")

    season_map = {"winter": 0, "summer": 1, "monsoon": 2, "autumn": 3,
                  "winter_onset": 0, "summer_onset": 1, "monsoon_onset": 2, "monsoon_end": 2}
    stress_map = {"none": 0, "low": 1, "medium": 2, "high": 3, "extreme": 4}
    income_map = {"low": 0, "medium": 1, "high": 2}
    region_map = {"south": 0, "north": 1, "west": 2, "east": 3, "northeast": 4}
    cuisine_map = {"south_indian": 0, "north_indian": 1, "biryani": 2,
                   "street_food": 3, "gujarati": 4, "maharashtrian": 5,
                   "bengali": 6, "rajasthani": 7, "dessert": 8,
                   "beverage": 9, "staple": 10, "goan": 11}

    features = [
        float(hour),
        float(day),
        float(budget),
        float(rank),
        float(user.get("cuisine_affinity_score", 0.5)),
        float(user.get("price_match_score", 0.5)),
        float(user.get("health_match_score", 0.5)),
        float(user.get("age", 30)),
        float(user.get("health_literacy", 0.5)),
        float(user.get("habit_strength", 0.6)),
        float(user.get("bmi", 23.0)),
        float(dish.get("glycemic_index", 55) or 55),
        float(dish.get("calories_kcal", 300) or 300),
        float(dish.get("protein_g", 10) or 10),
        float(dish.get("carbs_g", 35) or 35),
        float(dish.get("fat_g", 8) or 8),
        float(dish.get("fiber_g", 3) or 3),
        float(season_map.get(season, 1)),
        float(stress_map.get(stress, 2)),
        float(income_map.get(user.get("income_tier", "medium"), 1)),
        float(region_map.get(user.get("region", "north"), 1)),
        float(cuisine_map.get(dish.get("cuisine_type", "north_indian"), 1)),
        float(1 if user.get("is_vegetarian") else 0),
        float(1 if rank < 3 else 0),
    ]
    return np.array(features, dtype=np.float32)


def score_dish(user: dict, dish: dict,
               context: dict, rank: int) -> float:
    """Score a single dish for a user."""
    features = build_feature_vector(user, dish, context, rank)

    # Try trained ranker
    if model_store.ranker is not None and model_store.ranker_type != "rules":
        try:
            if model_store.ranker_type == "lgbm":
                probs = model_store.ranker.predict(features.reshape(1, -1))
                if probs.ndim == 2:
                    score = probs[0][2]  # order probability
                else:
                    score = float(probs[0])
            else:
                probs = model_store.ranker.predict_proba(features.reshape(1, -1))
                score = float(probs[0][2]) if probs.shape[1] > 2 else float(probs[0][1])
            return round(score, 4)
        except Exception as e:
            log.debug(f"Ranker inference failed: {e}, using rules")

    # Rule-based fallback score
    conditions = user.get("conditions", [])
    if isinstance(conditions, str):
        conditions = conditions.split("|") if conditions else []

    health_score  = rule_health_score(dish, conditions)
    cuisine_score = user.get("cuisine_affinity_score", 0.5)
    recency_bonus = 0.1 if dish.get("dish_name") in user.get("top_dishes", []) else 0.0

    return round((health_score * 0.4 + cuisine_score * 0.4 + recency_bonus + 0.1), 4)


def health_score_dish(user: dict, dish: dict) -> dict:
    """Score a dish for health compliance."""
    conditions = user.get("conditions", [])
    if isinstance(conditions, str):
        conditions = conditions.split("|") if conditions else []

    if model_store.health_scorer is not None and model_store.health_type != "rules":
        try:
            gi       = dish.get("glycemic_index", 55) or 55
            calories = dish.get("calories_kcal", 300) or 300
            features = np.array([[
                float(gi), float(calories),
                float(dish.get("protein_g", 10) or 10),
                float(dish.get("carbs_g", 35) or 35),
                float(dish.get("fat_g", 8) or 8),
                float(dish.get("fiber_g", 3) or 3),
                1.0,  # portion_multiplier
                float(user.get("age", 30)),
                float(user.get("bmi", 23.0)),
                float(user.get("health_literacy", 0.5)),
                0, 0, 0, 0,  # occasion, season, stress, activity (encoded)
                0, 0, 0,     # is_festival, is_fast, is_veg
                int("type2_diabetes" in conditions),
                int("prediabetes" in conditions),
                int("hypertension" in conditions),
                int("obesity" in conditions),
                int("pcos" in conditions),
                int("high_cholesterol" in conditions),
            ]], dtype=np.float32)

            prob = model_store.health_scorer.predict_proba(features)[0]
            compliant = bool(np.argmax(prob) == 1)
            confidence = float(prob[1])
        except Exception:
            compliant  = rule_health_score(dish, conditions) > 0.5
            confidence = rule_health_score(dish, conditions)
    else:
        score     = rule_health_score(dish, conditions)
        compliant = score > 0.5
        confidence= score

    # Build human readable reasons
    reasons = []
    gi = dish.get("glycemic_index", 55) or 55
    if "type2_diabetes" in conditions and gi > 70:
        reasons.append(f"High GI ({gi}) — not ideal for diabetes")
    if "pcos" in conditions and gi > 65:
        reasons.append(f"High GI ({gi}) — PCOS needs low GI")
    if "hypertension" in conditions and (dish.get("calories_kcal", 0) or 0) > 500:
        reasons.append("High calorie meal — monitor sodium intake")

    return {
        "compliant":   compliant,
        "confidence":  round(confidence, 3),
        "reasons":     reasons,
    }


def detect_occasion(context: dict) -> str:
    """Detect meal occasion from context."""
    hour       = context.get("hour", datetime.now().hour)
    is_weekend = context.get("is_weekend", False)

    if model_store.occasion is not None and model_store.occasion_type != "rules":
        try:
            features = np.array([[
                float(hour), float(context.get("day_of_week", 0)),
                float(context.get("month", 1)),
                float(context.get("budget_multiplier", 1.0)),
                float(context.get("commute_minutes", 45)),
                float(context.get("age", 30)),
                0, 2, 0,  # season, stress, month_position (encoded)
                0, 0,     # occupation, living_situation
                float(1 if is_weekend else 0),
                0, 0, 0, 0, 0,  # binary flags
            ]], dtype=np.float32)

            pred = model_store.occasion.predict(features)
            occasion_map = {0: "breakfast", 1: "lunch", 2: "snack",
                           3: "dinner", 4: "late_night"}
            return occasion_map.get(int(pred[0]), "lunch")
        except Exception:
            pass

    return rule_detect_occasion(hour, is_weekend)


def get_recommendations(
    user: dict,
    context: dict,
    food_graph: dict,
    n: int = 10,
) -> list:
    """
    Main recommendation function.
    Returns ranked list of dish recommendations.
    """
    if not DISH_CANDIDATES:
        log.warning("No dish candidates loaded")
        return []

    # Detect occasion
    occasion = context.get("occasion") or detect_occasion(context)
    context["occasion"] = occasion

    # Get user attributes
    conditions = user.get("conditions", [])
    if isinstance(conditions, str):
        conditions = [c for c in conditions.split("|") if c]

    restrictions = user.get("dietary_restrictions", [])
    if isinstance(restrictions, str):
        restrictions = [r for r in restrictions.split("|") if r]

    is_veg = bool(user.get("is_vegetarian", False))

    # Get top dishes from food graph for affinity
    top_dishes    = [d.get("dish") for d in food_graph.get("top_dishes", [])]
    cuisine_affinity = food_graph.get("cuisine_affinity", {})

    # Enrich user with food graph data
    user["top_dishes"] = top_dishes
    user["conditions"] = conditions

    # Filter candidates
    candidates = list(DISH_CANDIDATES)
    candidates = filter_by_occasion(candidates, occasion)
    candidates = filter_by_dietary(candidates, restrictions, is_veg)

    # Score each candidate
    scored = []
    for rank, dish in enumerate(candidates):
        cuisine = dish.get("cuisine_type", "north_indian")
        user["cuisine_affinity_score"] = cuisine_affinity.get(cuisine, 0.3)
        user["price_match_score"] = 0.7  # TODO: use actual budget
        user["health_match_score"] = 0.6

        score        = score_dish(user, dish, context, rank)
        health_info  = health_score_dish(user, dish)

        # Boost frequently eaten dishes slightly
        reorder_boost = 0.05 if dish.get("dish_name") in top_dishes else 0.0

        final_score = round(score + reorder_boost, 4)

        scored.append({
            "dish_name":       dish.get("dish_name"),
            "cuisine_type":    dish.get("cuisine_type"),
            "score":           final_score,
            "health_compliant":health_info["compliant"],
            "health_confidence":health_info["confidence"],
            "health_reasons":  health_info["reasons"],
            "nutrition": {
                "calories":   dish.get("calories_kcal"),
                "protein_g":  dish.get("protein_g"),
                "carbs_g":    dish.get("carbs_g"),
                "fat_g":      dish.get("fat_g"),
                "fiber_g":    dish.get("fiber_g"),
                "gi":         dish.get("glycemic_index"),
            },
            "is_veg":         dish.get("is_veg"),
            "allergens":      dish.get("allergens", []),
            "occasion":       occasion,
        })

    # Sort by score
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:n]