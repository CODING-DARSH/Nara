"""
NARA — Recommendation Pipeline (FIXED)
Fixes applied:
  1. LightGBM feature vector now exactly matches the 33 features used at
     training time (17 numerical + 5 categorical + 2 binary + 9 condition flags),
     in the same order, with the same label-encoding scheme. This was the
     cause of "[LightGBM] [Fatal] number of features ... not the same".
  2. Occasion filtering is now strict when explicitly requested by the user
     (tabs in the UI) — no silent fallback to the full unfiltered list.
  3. Reorder model wired in as a real signal (frequency + recency boost).
"""
import logging
import random
from datetime import datetime
import numpy as np
import pandas as pd

from app.core.model_loader import model_store

log = logging.getLogger("nara.recommendation.pipeline")

# ── Dish pool from nutrition KB ───────────────────────────────
DISH_CANDIDATES = []


def set_dish_candidates(dishes: list):
    global DISH_CANDIDATES
    DISH_CANDIDATES = dishes
    log.info(f"Dish candidates loaded: {len(DISH_CANDIDATES)}")


# ════════════════════════════════════════════════════════════
# FIX 1 — Feature vector exactly matching training (33 features)
# ════════════════════════════════════════════════════════════
# Order MUST match config.RANKER_FEATURES:
#   numerical(17) + categorical(5) + binary(2) + condition_flags(9) = 33

RANKER_NUMERICAL = [
    "context_time_of_day", "context_day", "context_budget",
    "recommendation_rank", "cuisine_affinity", "price_match_score",
    "user_health_match", "age", "health_literacy", "habit_strength",
    "bmi", "gi_score", "calories_kcal", "protein_g", "carbs_g",
    "fat_g", "fiber_g",
]
RANKER_CATEGORICAL = [
    "context_season", "context_stress", "income_tier", "region", "cuisine_type",
]
RANKER_BINARY = ["is_vegetarian", "was_top3"]
RANKER_CONDITION_FLAGS = [
    "has_diabetes", "has_prediabetes", "has_hypertension", "has_obesity",
    "has_pcos", "has_high_cholesterol", "has_thyroid", "has_ibs", "has_anemia",
]
CONDITION_FLAG_MAP = {
    "has_diabetes":         "type2_diabetes",
    "has_prediabetes":      "prediabetes",
    "has_hypertension":     "hypertension",
    "has_obesity":          "obesity",
    "has_pcos":             "pcos",
    "has_high_cholesterol": "high_cholesterol",
    "has_thyroid":          "thyroid",
    "has_ibs":              "ibs",
    "has_anemia":           "anemia",
}

# CONFIRMED against real services/ml-training/models/encoders.joblib
# (FeatureEncoder.label_encoders), via inspect_encoders.py output:
#   context_season: ['autumn','monsoon','monsoon_end','monsoon_onset','summer','summer_onset','winter','winter_onset']
#   context_stress: ['high','low','medium','none']            <- no "extreme"
#   income_tier:    ['high','low','medium']
#   region:         ['east','north','northeast','south','west'] <- has "northeast"
# Two real mistakes fixed from the previous guess:
#   1. region was missing "northeast" entirely.
#   2. stress was guessed with 5 classes including "extreme", which the
#      real trained encoder does NOT have (only 4 classes). Any "extreme"
#      value sent at inference would have silently landed in the unknown
#      bucket instead of erroring — fixed to match the real 4 classes.
_SEASON_CLASSES  = sorted(["autumn", "monsoon", "monsoon_end", "monsoon_onset",
                           "summer", "summer_onset", "winter", "winter_onset"])
_STRESS_CLASSES  = sorted(["high", "low", "medium", "none"])
_INCOME_CLASSES  = sorted(["high", "low", "medium"])
_REGION_CLASSES  = sorted(["east", "north", "northeast", "south", "west"])

# NOT CONFIRMED — could not be verified against a real file. Investigated
# why: only recommendation_ranker/train_logistic.py ever calls
# encoder.save(...) on its FeatureEncoder (services/ml-training/utils.py
# FeatureEncoder.save). meal_occasion_classifier/*.py and
# health_scorer/*.py each fit their OWN local FeatureEncoder during
# training but never save it — so the encodings they used for
# occupation/living_situation/month_position/meal_occasion/activity_level
# only ever existed in-memory during that training run and are not
# recoverable from any file that currently exists. The only way to get the
# real classes is to add `encoder.save(...)` to those scripts and re-run
# them. Until then, these stay best-effort placeholders.
_CUISINE_CLASSES = sorted([
    "south_indian", "north_indian", "biryani", "street_food", "gujarati",
    "maharashtrian", "bengali", "rajasthani", "dessert", "beverage",
    "staple", "goan",
])
# health_scorer's categorical "activity_level" — mirrors schemas.VALID_ACTIVITY
# in user-intelligence (sedentary/lightly_active/moderately_active/very_active).
_ACTIVITY_CLASSES = sorted(["lightly_active", "moderately_active", "sedentary", "very_active"])
# health_scorer's categorical "meal_occasion" — same 5 classes the occasion
# classifier predicts/consumes.
_OCCASION_CLASSES = sorted(["breakfast", "dinner", "late_night", "lunch", "snack"])

# TODO(darsh): occasion classifier's month_position/occupation/
# living_situation categoricals — UNVERIFIABLE from any existing file, see
# note above. Re-run meal_occasion_classifier/train_xgboost.py with
# `encoder.save(MODEL_PATHS["occasion_encoders"])` added (and a matching
# new MODEL_PATHS entry) if you want the real values instead of these
# placeholder guesses.
_MONTH_POSITION_CLASSES    = sorted(["early", "mid", "late"])
_OCCUPATION_CLASSES        = sorted(["student", "salaried", "self_employed", "homemaker", "unemployed", "retired", "unknown"])
_LIVING_SITUATION_CLASSES  = sorted(["alone", "with_family", "with_roommates", "with_partner", "unknown"])
# reorder_prediction's "trigger_type" categorical — same unverifiable-encoder
# situation as above (train_random_forest.py/train_logistic.py never call
# encoder.save()). Best-effort placeholder matching the 5 classes named in
# config.py's REORDER_FEATURES comment.
_TRIGGER_TYPE_CLASSES      = sorted(["convenience", "craving", "festival", "habit", "stress"])


def _label_encode(value: str, classes: list) -> float:
    """Mirror LabelEncoder behaviour: unseen value maps to len(classes) ('unknown' bucket)."""
    try:
        return float(classes.index(value))
    except ValueError:
        return float(len(classes))


def build_feature_vector(user: dict, dish: dict,
                          context: dict, rank: int) -> np.ndarray:
    """
    Build the EXACT 33-feature vector the LightGBM/XGBoost rankers were
    trained on. Any change here must mirror config.RANKER_FEATURES.
    """
    hour   = context.get("hour", 13)
    day    = context.get("day_of_week", 0)
    budget = context.get("budget_multiplier", 1.0)
    season = context.get("season", "summer")
    stress = context.get("stress_level", "medium")

    conditions = user.get("conditions", [])
    if isinstance(conditions, str):
        conditions = [c for c in conditions.split("|") if c]

    numerical = [
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
    ]

    categorical = [
        _label_encode(season, _SEASON_CLASSES),
        _label_encode(stress, _STRESS_CLASSES),
        _label_encode(user.get("income_tier", "medium"), _INCOME_CLASSES),
        _label_encode(user.get("region", "north"), _REGION_CLASSES),
        _label_encode(dish.get("cuisine_type", "north_indian"), _CUISINE_CLASSES),
    ]

    binary = [
        float(1 if user.get("is_vegetarian") else 0),
        float(1 if rank < 3 else 0),
    ]

    condition_flags = [
        float(1 if CONDITION_FLAG_MAP[flag] in conditions else 0)
        for flag in RANKER_CONDITION_FLAGS
    ]

    features = numerical + categorical + binary + condition_flags
    if len(features) != 33:
        log.error(f"Feature count mismatch: got {len(features)}, expected 33")
    return np.array(features, dtype=np.float32)


# ── Health rule-based scorer (fallback) ───────────────────────
def rule_health_score(dish: dict, conditions: list) -> float:
    gi       = dish.get("glycemic_index", 55) or 55
    calories = dish.get("calories_kcal", 300) or 300

    score = 1.0
    if "type2_diabetes" in conditions or "prediabetes" in conditions:
        if gi > 70:
            score *= 0.2
        elif gi > 55:
            score *= 0.7
    if "hypertension" in conditions and calories > 500:
        score *= 0.6
    if "obesity" in conditions and calories > 600:
        score *= 0.5
    if "pcos" in conditions and gi > 65:
        score *= 0.4
    return round(score, 3)


# ── Occasion detection (fallback) ─────────────────────────────
def rule_detect_occasion(hour: int) -> str:
    if 5 <= hour < 10:
        return "breakfast"
    elif 10 <= hour < 15:
        return "lunch"
    elif 15 <= hour < 18:
        return "snack"
    elif 18 <= hour < 23:
        return "dinner"
    return "late_night"


# ════════════════════════════════════════════════════════════
# FIX 1 — Dish-level occasion filtering (replaces broken cuisine-level filter)
# ════════════════════════════════════════════════════════════
# OLD APPROACH (removed): filtered by cuisine_type (south_indian,
# north_indian...) which is far too coarse — masala dosa and chicken
# biryani are both "tagged" similarly at cuisine level, so they kept
# showing up across breakfast/lunch/dinner identically.
#
# NEW APPROACH: every dish row carries occasion_tags (JSONB list) from
# nutrition_kb, backfilled by scripts/migrate_occasion_tags.py with real
# per-dish appropriateness (idli -> breakfast/snack, biryani -> lunch/
# dinner, gulab jamun -> dessert/snack, etc). Filtering now checks
# membership in that list directly.

# Fallback cuisine map ONLY used for dishes that somehow have no
# occasion_tags at all (e.g. KB rows added after a migration was skipped).
_FALLBACK_CUISINE_OCCASION = {
    "south_indian": ["breakfast", "lunch", "dinner", "snack"],
    "north_indian": ["lunch", "dinner"],
    "biryani":      ["lunch", "dinner"],
    "street_food":  ["snack"],
    "gujarati":     ["breakfast", "lunch", "dinner", "snack"],
    "maharashtrian":["breakfast", "lunch", "dinner", "snack"],
    "bengali":      ["lunch", "dinner"],
    "rajasthani":   ["lunch", "dinner"],
    "dessert":      ["dessert", "snack"],
    "beverage":     ["breakfast", "snack"],
    "staple":       ["breakfast", "lunch", "dinner", "snack"],
    "goan":         ["lunch", "dinner"],
}


def _dish_occasion_tags(dish: dict) -> list:
    tags = dish.get("occasion_tags")
    if tags:
        return tags
    # Fallback only when KB row truly has no tags (migration not run yet)
    cuisine = dish.get("cuisine_type", "")
    return _FALLBACK_CUISINE_OCCASION.get(cuisine, ["lunch", "dinner"])


def filter_by_occasion(dishes: list, occasion: str, strict: bool = False) -> list:
    """
    strict=True  -> always return the filtered list (even if empty),
                    used when the user explicitly picked a tab in the UI.
    strict=False -> falls back to the unfiltered list only if the filter
                    produced zero results (used for the implicit/auto path).

    Filtering is now done against each dish's REAL occasion_tags, not a
    coarse cuisine category — this is the actual fix for dishes repeating
    identically across breakfast/lunch/dinner/snack.
    """
    if not occasion:
        return dishes
    filtered = [d for d in dishes if occasion in _dish_occasion_tags(d)]
    if strict:
        return filtered
    return filtered if filtered else dishes


def filter_by_dietary(dishes: list, restrictions: list, is_veg: bool) -> list:
    if not restrictions and not is_veg:
        return dishes

    result = []
    for dish in dishes:
        allergens = dish.get("allergens", [])
        if isinstance(allergens, str):
            allergens = allergens.split("|") if allergens else []

        if is_veg and not dish.get("is_veg", True):
            continue

        skip = False
        if "no_dairy" in restrictions and "milk" in allergens:
            skip = True
        if "no_gluten" in restrictions and "gluten" in allergens:
            skip = True
        if "halal" in restrictions and dish.get("cuisine_type") == "goan":
            skip = True

        if not skip:
            result.append(dish)

    return result if result else dishes


# ════════════════════════════════════════════════════════════
# Scoring — ranker, health, occasion detection, reorder boost
# ════════════════════════════════════════════════════════════

def score_dish(user: dict, dish: dict, context: dict, rank: int) -> tuple[float, dict]:
    """
    Ensemble ranker score for a single dish.
    Returns (combined_score, per_model_breakdown) — breakdown is logged
    per-request so weights can be tuned from real production data.
    Falls back to rule-based if no ranker variants loaded.
    """
    features = build_feature_vector(user, dish, context, rank)

    if model_store.rankers:
        score, breakdown = model_store.ensemble_ranker_score(features)
        if score > 0 or breakdown:
            return score, breakdown

    # Rule-based fallback
    conditions    = user.get("conditions", [])
    if isinstance(conditions, str):
        conditions = conditions.split("|") if conditions else []
    health_score  = rule_health_score(dish, conditions)
    cuisine_score = user.get("cuisine_affinity_score", 0.5)
    recency_bonus = 0.1 if dish.get("dish_name") in user.get("top_dishes", []) else 0.0
    score = round((health_score * 0.4 + cuisine_score * 0.4 + recency_bonus + 0.1), 4)
    return score, {"rules": score}


def health_score_dish(user: dict, dish: dict, context: dict | None = None) -> dict:
    """
    Ensemble health compliance score for a dish.
    Combines xgb + rf variants weighted by AUC.
    Falls back to rule-based if no models loaded.
    """
    context = context or {}
    conditions = user.get("conditions", [])
    if isinstance(conditions, str):
        conditions = conditions.split("|") if conditions else []

    gi       = dish.get("glycemic_index", 55) or 55
    calories = dish.get("calories_kcal", 300) or 300

    meal_occasion = context.get("occasion") or "lunch"
    season        = context.get("season", "summer")
    activity      = user.get("activity_level", "moderately_active")
    is_veg        = 1.0 if user.get("is_vegetarian") else 0.0

    features = np.array([[
        float(gi), float(calories),
        float(dish.get("protein_g", 10) or 10),
        float(dish.get("carbs_g", 35) or 35),
        float(dish.get("fat_g", 8) or 8),
        float(dish.get("fiber_g", 3) or 3),
        1.0,
        float(user.get("age", 30)),
        float(user.get("bmi", 23.0)),
        float(user.get("health_literacy", 0.5)),
        _label_encode(meal_occasion, _OCCASION_CLASSES),
        _label_encode(season, _SEASON_CLASSES),
        _label_encode(context.get("stress_level", "medium"), _STRESS_CLASSES),
        _label_encode(activity, _ACTIVITY_CLASSES),
        0,  # is_festival_day — no calendar source
        0,  # is_fast_day — no calendar source
        is_veg,
        int("type2_diabetes" in conditions),
        int("prediabetes" in conditions),
        int("hypertension" in conditions),
        int("obesity" in conditions),
        int("pcos" in conditions),
        int("high_cholesterol" in conditions),
    ]], dtype=np.float32)

    confidence = None
    breakdown  = {}

    if model_store.health_scorers:
        combined, breakdown = model_store.ensemble_health_score(features)
        if combined is not None:
            confidence = combined

    if confidence is None:
        confidence = rule_health_score(dish, conditions)

    compliant = confidence >= 0.5

    reasons = []
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
        "breakdown":   breakdown,
    }


def detect_occasion(context: dict, user: dict | None = None, debug_out: dict | None = None) -> str:
    """
    Ensemble occasion detection — combines xgb + rf + dt via weighted vote.
    Falls back to rule-based if no models loaded.
    """
    user = user or {}
    hour         = context.get("hour", datetime.now().hour)
    is_weekend   = context.get("is_weekend", False)
    day_of_month = context.get("day_of_month") or datetime.now().day

    if model_store.occasion_models:
        try:
            season = context.get("season", "summer")
            if day_of_month <= 10:
                month_position = "early"
            elif day_of_month <= 20:
                month_position = "mid"
            else:
                month_position = "late"

            features = np.array([[
                float(hour),
                float(context.get("day_of_week", 0)),
                float(context.get("month", 1)),
                float(context.get("budget_multiplier", 1.0)),
                float(context.get("commute_minutes", 45)),
                float(user.get("age", 30)),
                _label_encode(season, _SEASON_CLASSES),
                _label_encode(user.get("stress_level") or "unknown", _STRESS_CLASSES),
                _label_encode(month_position, _MONTH_POSITION_CLASSES),
                _label_encode(user.get("occupation") or "unknown", _OCCUPATION_CLASSES),
                _label_encode(user.get("living_situation") or "unknown", _LIVING_SITUATION_CLASSES),
                float(1 if is_weekend else 0),
                0,  # cooking_at_home
                0,  # ordered_delivery
                0,  # is_festival_day
                0,  # is_fast_day
                float(1 if user.get("is_wfh") else 0),
            ]], dtype=np.float32)

            # Real alphabetical class mapping confirmed from training logs:
            # Classes: ['breakfast', 'dinner', 'late_night', 'lunch', 'snack']
            OCCASION_MAP = {0: "breakfast", 1: "dinner", 2: "late_night", 3: "lunch", 4: "snack"}

            pred_idx, breakdown = model_store.ensemble_occasion_predict(features)
            if debug_out is not None:
                debug_out["occasion_detection"] = {"predicted_idx": pred_idx, "standalone": breakdown}
            if pred_idx is not None:
                return OCCASION_MAP.get(pred_idx, "lunch")
        except Exception as e:
            log.debug(f"Ensemble occasion failed: {e}")

    return rule_detect_occasion(hour)


# ════════════════════════════════════════════════════════════
# FIX 3 — Reorder model wired in as a real signal
# ════════════════════════════════════════════════════════════

def reorder_boost(user: dict, dish: dict, food_graph: dict, dish_interactions: dict | None = None,
                   debug_out: dict | None = None) -> float:
    """
    Ensemble reorder boost (rf + logistic, AUC-weighted).

    Combines two independent repeat-preference signals:
      - `food_graph.top_dishes` — from actually logging a meal (LogMeal.jsx
        -> food.events.enriched). Strong signal: you really ate this.
      - `dish_interactions` — from clicking/ordering a recommendation card
        (tracked in Redis by the /feedback endpoint, see core/redis.py).
        Weaker signal (a click doesn't guarantee you ate it), but this was
        previously not read AT ALL for per-dish reinforcement — only
        cuisine_affinity moved from in-app behavior, so a specific dish you
        keep engaging with never individually became more likely to
        resurface. This is what closes that gap.

    Returns 0.0 if the dish has no signal from either source — running
    reorder models on pure noise produces noise, not signal.
    """
    top_dishes = food_graph.get("top_dishes", []) if food_graph else []
    dish_interactions = dish_interactions or {}

    dish_name = dish.get("dish_name", "")
    logged_match  = next((d for d in top_dishes if d.get("dish") == dish_name), None)
    logged_count  = float(logged_match.get("count", 0)) if logged_match else 0.0
    click_weight  = float(dish_interactions.get(dish_name, 0.0))

    total_orders = logged_count + click_weight
    if total_orders <= 0:
        return 0.0

    # Combined ranking across both signals — union of every dish with
    # either kind of signal, ranked by combined weight. Used below as a
    # days_between proxy (no real per-dish order timestamps exist yet),
    # so it needs to reflect TRUE relative frequency across both sources,
    # not just meal-log order.
    combined_weights: dict[str, float] = {}
    for d in top_dishes:
        name = d.get("dish")
        if name:
            combined_weights[name] = combined_weights.get(name, 0.0) + float(d.get("count", 0))
    for name, w in dish_interactions.items():
        combined_weights[name] = combined_weights.get(name, 0.0) + w
    top_dish_names = sorted(combined_weights, key=lambda n: combined_weights[n], reverse=True)

    if not model_store.reorder_models:
        # Fallback heuristic: frequency-based, capped
        return round(min(0.10, 0.02 * total_orders), 4)

    try:
        dish_rank    = top_dish_names.index(dish_name) if dish_name in top_dish_names else 10
        days_between = max(1, 7 - dish_rank)  # proxy: no real per-dish order timestamps tracked yet

        now = datetime.now()
        day_of_month = now.day
        if day_of_month <= 10:
            month_position = "early"
        elif day_of_month <= 20:
            month_position = "mid"
        else:
            month_position = "late"

        # FIX: previous vector was built as a hardcoded positional list that
        # didn't match REORDER_FEATURES training order at all (fields
        # swapped, bmi/dish_rank injected as if trained — they never were).
        # Build a name-keyed dict instead and let model_store order it per
        # model using each model's own saved feature_cols.
        raw = {
            # numerical
            "days_between":            float(days_between),
            "total_orders_dish":       float(total_orders),
            "last_rating_proxy":       0.0,  # no rating data collected yet
            "habit_strength":          float(user.get("habit_strength", 0.3)),
            "health_literacy":         float(user.get("health_literacy", 0.5)),
            "age":                     float(user.get("age", 30)),
            "order_frequency_weekly":  0.0,  # no real order-frequency tracking yet
            # categorical (label-encoded, same scheme as elsewhere in this file)
            "trigger_type":  _label_encode("habit", _TRIGGER_TYPE_CLASSES),  # best-effort: a reorder is, by definition, a repeat/habit signal
            "income_tier":   _label_encode(user.get("income_tier") or "unknown", _INCOME_CLASSES),
            "occupation":    _label_encode(user.get("occupation") or "unknown", _OCCUPATION_CLASSES),
            "stress_profile":_label_encode(user.get("stress_level") or "unknown", _STRESS_CLASSES),
            "season":        _label_encode(_get_season(now.month), _SEASON_CLASSES),
            "month_position":_label_encode(month_position, _MONTH_POSITION_CLASSES),
            # binary
            "is_vegetarian": float(1 if user.get("is_vegetarian") else 0),
        }

        reorder_prob, reorder_breakdown = model_store.ensemble_reorder_score(raw)
        if debug_out is not None:
            debug_out["reorder"] = {"ensemble_prob": reorder_prob, "standalone": reorder_breakdown}
        return round(min(reorder_prob * 0.12, 0.12), 4)

    except Exception as e:
        log.debug(f"Ensemble reorder failed: {e}")
        return round(min(0.10, 0.02 * total_orders), 4)


# ════════════════════════════════════════════════════════════
# Main recommendation function
# ════════════════════════════════════════════════════════════

# FIX: region was only ever fed as a numeric feature into the trained
# ranker's feature vector — it influenced the model's learned score, but
# nothing anywhere actually surfaced region-typical cuisines for a user.
# A brand-new West-region user with zero meal history would never see
# Gujarati/Maharashtrian dishes ranked any higher than anyone else's,
# since cuisine_affinity_score (below) came purely from food_graph's
# behavioral data — which is empty for a new user by definition. This
# real mapping gives every user, even a day-one signup with zero history,
# an honest regional cuisine prior instead of waiting for behavior data
# that doesn't exist yet. Values match the real cuisine_type strings in
# _CUISINE_CLASSES above, not invented categories.
REGION_CUISINE_AFFINITY = {
    "west":      {"gujarati": 0.7, "maharashtrian": 0.7, "north_indian": 0.4},
    "north":     {"north_indian": 0.7, "rajasthani": 0.5, "street_food": 0.4},
    "south":     {"south_indian": 0.7, "biryani": 0.4},
    "east":      {"bengali": 0.7, "street_food": 0.4},
    "northeast": {"street_food": 0.4},  # no dedicated northeastern cuisine_type exists in the KB yet
}

# Candidate generation — the retrieval stage that was missing entirely.
# Previously every request ran the full ensemble ranker (LightGBM/XGBoost/
# health-scorer/reorder-boost, all real model inference) over the ENTIRE
# filtered dish pool, however large nutrition_kb grows. This narrows that
# pool to a bounded size using cheap arithmetic (no model inference) before
# the expensive per-dish ensemble loop runs — the standard two-stage
# retrieval-then-rank split, just without the embedding/ANN machinery that
# isn't warranted at this catalog size (see conversation notes: heuristic
# retrieval now, embeddings only if free-text search or a much larger
# catalog make structured filtering insufficient later).
MAX_CANDIDATES_PER_REQUEST = 250
MIN_CANDIDATES_PER_CUISINE = 5  # floor so a low-affinity cuisine isn't fully
                                  # starved — keeps room for genuine
                                  # discovery and for _diversify() downstream


def _cuisine_affinity_score(cuisine: str, region: str | None, cuisine_affinity: dict) -> float:
    """
    Same blend formula the main scoring loop uses for cuisine_affinity_score
    (0.75 behavioral + 0.25 region prior, region-only fallback, 0.3 default)
    — kept identical on purpose so retrieval and ranking agree on what
    "relevant" means instead of being two different worldviews.
    """
    region_affinity = REGION_CUISINE_AFFINITY.get(region, {}).get(cuisine, 0.0)
    behavioral = cuisine_affinity.get(cuisine)
    if behavioral is not None:
        return round(0.75 * behavioral + 0.25 * region_affinity, 3)
    return region_affinity if region_affinity else 0.3


def generate_candidates(
    dishes: list,
    region: str | None,
    cuisine_affinity: dict,
    max_candidates: int = MAX_CANDIDATES_PER_REQUEST,
) -> list:
    """
    Narrows an already hard-filtered dish pool (post occasion/dietary
    filters) down to a bounded candidate set using a proportional,
    multi-bucket retrieval: bucket dishes by cuisine_type, score each
    bucket once via the same affinity blend the ranker trusts, then fill
    the candidate budget proportionally to that score — NOT a hard
    top-cuisines-only cutoff, which would starve low-affinity cuisines
    entirely and kill discovery/diversity before the ranker even runs.

    Every cuisine bucket present in the pool gets at least
    MIN_CANDIDATES_PER_CUISINE slots (or its full size, if smaller) before
    proportional fill uses the rest of the budget — this is what keeps a
    user's dominant cuisine from crowding out everything else the way a
    plain `ORDER BY affinity_score LIMIT n` would.

    No-op (returns the pool unchanged) if it's already <= max_candidates —
    this stage exists to bound cost at scale, not to shrink small pools
    for no reason.
    """
    if len(dishes) <= max_candidates:
        return dishes

    buckets: dict[str, list] = {}
    for d in dishes:
        buckets.setdefault(d.get("cuisine_type", "north_indian"), []).append(d)

    scores = {c: _cuisine_affinity_score(c, region, cuisine_affinity) for c in buckets}
    ranked_cuisines = sorted(buckets, key=lambda c: scores[c], reverse=True)

    # Shuffle within each bucket so repeated requests in the same session
    # don't always surface the same subset of a cuisine — real per-dish
    # variety, not just cross-cuisine variety.
    for c in ranked_cuisines:
        random.shuffle(buckets[c])

    selected = []
    remaining_budget = max_candidates

    # Pass 1: guaranteed floor per cuisine (protects low-affinity cuisines
    # from being fully excluded).
    floor_taken = {}
    for c in ranked_cuisines:
        take = min(MIN_CANDIDATES_PER_CUISINE, len(buckets[c]), remaining_budget)
        floor_taken[c] = take
        selected.extend(buckets[c][:take])
        remaining_budget -= take
        if remaining_budget <= 0:
            break

    # Pass 2: proportional fill of whatever budget remains, weighted by
    # each cuisine's affinity score — this is what actually concentrates
    # the pool toward what the user likes, on top of the floor from pass 1.
    if remaining_budget > 0:
        total_score = sum(max(scores[c], 0.05) for c in ranked_cuisines) or 1.0
        for c in ranked_cuisines:
            if remaining_budget <= 0:
                break
            leftover = buckets[c][floor_taken.get(c, 0):]
            if not leftover:
                continue
            quota = max(0, round(max_candidates * (max(scores[c], 0.05) / total_score)))
            take = min(quota, len(leftover), remaining_budget)
            selected.extend(leftover[:take])
            remaining_budget -= take

    return selected[:max_candidates]


def get_recommendations(
    user: dict,
    context: dict,
    food_graph: dict,
    n: int = 10,
    occasion_explicit: bool = False,
    recently_shown: set | None = None,
    dish_interactions: dict | None = None,
    debug: bool = False,
) -> list:
    """
    Main recommendation function with ensemble scoring + cold-start blend.

    Cold-start blend logic:
      blend_weight = min(1.0, total_meals_logged / 10)
      final_score  = (1 - blend_weight) * cold_start_score
                   + blend_weight       * ensemble_score

      At 0 meals  → pure cold-start (demographic/regional priors)
      At 10+ meals → pure ensemble (fully personalized)
      Between 1-9  → smooth linear blend, cold-start fades as real data grows
    """
    if not DISH_CANDIDATES:
        log.warning("No dish candidates loaded")
        return []

    occasion_debug = {}
    occasion = context.get("occasion") or detect_occasion(context, user, debug_out=occasion_debug if debug else None)
    context["occasion"] = occasion

    conditions = user.get("conditions", [])
    if isinstance(conditions, str):
        conditions = [c for c in conditions.split("|") if c]

    restrictions = user.get("dietary_restrictions", [])
    if isinstance(restrictions, str):
        restrictions = [r for r in restrictions.split("|") if r]

    is_veg = bool(user.get("is_vegetarian", False))

    total_meals    = int((food_graph or {}).get("total_meals_logged", 0))
    top_dishes     = [d.get("dish") for d in (food_graph or {}).get("top_dishes", [])]
    cuisine_affinity = (food_graph or {}).get("cuisine_affinity", {})

    # Cold-start blend weight: 0.0 = pure cold-start, 1.0 = pure ensemble
    blend_weight = min(1.0, total_meals / 10.0)
    use_cold_start = blend_weight < 1.0 and model_store.cold_start_models

    user["top_dishes"] = top_dishes
    user["conditions"] = conditions

    candidates = list(DISH_CANDIDATES)
    candidates = filter_by_occasion(candidates, occasion, strict=occasion_explicit)
    candidates = filter_by_dietary(candidates, restrictions, is_veg)

    # Candidate generation (retrieval stage) — narrows the hard-filtered
    # pool to a bounded, affinity-weighted set BEFORE the expensive
    # ensemble ranker runs on it. Previously every request ran full model
    # inference over the entire filtered pool regardless of its size.
    candidates = generate_candidates(candidates, user.get("region"), cuisine_affinity)

    # Build cold-start raw feature map once if we need it (same for all dishes)
    # FIX: previously built a hardcoded 32-value vector unrelated to
    # COLD_START_FEATURES (injected region/hour/day_of_week/month/etc, none
    # of which the cold-start models were trained on, and was missing
    # health_literacy/habit_strength/religion/gender/birthplace_state/
    # is_jain/is_halal/observance_level entirely). Build a name-keyed dict
    # matching the real training schema instead, and let model_store order
    # it per-model from each model's own saved feature_cols.
    predicted_cuisine = None
    cold_breakdown = {}
    if use_cold_start:
        try:
            restr_list = [r.strip() for r in (user.get("dietary_restrictions") or "").split("|") if r.strip()] \
                         if isinstance(user.get("dietary_restrictions"), str) else (user.get("dietary_restrictions") or [])

            cold_raw = {
                # numerical
                "age":                    float(user.get("age", 28)),
                "health_literacy":        float(user.get("health_literacy", 0.5)),
                "habit_strength":         float(user.get("habit_strength", 0.3)),
                "bmi":                    float(user.get("bmi", 23.0)),
                "observance_level":       0.0,  # no religious-observance signal collected yet
                "order_frequency_weekly": 0.0,  # no real order-frequency tracking yet
                # categorical (label-encoded)
                "birthplace_state": _label_encode("unknown", []),  # not collected at profile level yet
                "current_state":    _label_encode(user.get("region") or "unknown", _REGION_CLASSES),
                "religion":         _label_encode("unknown", []),  # not collected — see dietary flags below for halal/jain proxies
                "gender":           _label_encode("unknown", []),  # not collected
                "occupation":       _label_encode(user.get("occupation") or "unknown", _OCCUPATION_CLASSES),
                "income_tier":      _label_encode(user.get("income_tier") or "unknown", _INCOME_CLASSES),
                "living_situation": _label_encode(user.get("living_situation") or "unknown", _LIVING_SITUATION_CLASSES),
                "activity_level":   _label_encode(user.get("activity_level") or "unknown", _ACTIVITY_CLASSES),
                # binary
                "is_vegetarian": float(1 if user.get("is_vegetarian") else 0),
                "is_jain":       float(1 if "jain" in restr_list else 0),
                "is_halal":      float(1 if "halal" in restr_list else 0),
                # condition flags (multi_hot "conditions" expanded)
                "has_diabetes":         float(int("type2_diabetes" in conditions)),
                "has_prediabetes":      float(int("prediabetes" in conditions)),
                "has_hypertension":     float(int("hypertension" in conditions)),
                "has_obesity":          float(int("obesity" in conditions)),
                "has_pcos":             float(int("pcos" in conditions)),
                "has_high_cholesterol": float(int("high_cholesterol" in conditions)),
                "has_thyroid":          float(int("thyroid" in conditions)),
                "has_ibs":              float(int("ibs" in conditions)),
                "has_anemia":           float(int("anemia" in conditions)),
                # dietary_restrictions (multi_hot expanded, matches
                # ml-training/cold_start's restr_<flag> naming)
                "restr_vegetarian": float(1 if "vegetarian" in restr_list else 0),
                "restr_low_gi":     float(1 if "low_gi" in restr_list else 0),
                "restr_low_sodium": float(1 if "low_sodium" in restr_list else 0),
                "restr_no_dairy":   float(1 if "no_dairy" in restr_list else 0),
                "restr_no_gluten":  float(1 if "no_gluten" in restr_list else 0),
                "restr_halal":      float(1 if "halal" in restr_list else 0),
                "restr_jain":       float(1 if "jain" in restr_list else 0),
                "restr_no_beef":    float(1 if "no_beef" in restr_list else 0),
            }

            predicted_cuisine, cold_breakdown = model_store.ensemble_cold_start_predict(cold_raw)
            if predicted_cuisine:
                log.debug(f"cold_start predicted cuisine={predicted_cuisine}, "
                          f"blend_weight={blend_weight:.2f}")
        except Exception as e:
            log.debug(f"Cold-start feature build failed: {e}")
    else:
        cold_breakdown = {}

    scored = []
    for rank, dish in enumerate(candidates):
        cuisine = dish.get("cuisine_type", "north_indian")

        # Region-behavioral cuisine affinity blend — same helper
        # generate_candidates() used for retrieval, kept identical so
        # retrieval and ranking never disagree on what "relevant" means.
        region = user.get("region")
        user["cuisine_affinity_score"] = _cuisine_affinity_score(cuisine, region, cuisine_affinity)

        # Health ensemble — computed first, feeds into ranker feature vector
        health_info = health_score_dish(user, dish, context)
        user["health_match_score"] = health_info["confidence"]

        # Price match — real when dish has a price (restaurant menu endpoint)
        dish_price   = dish.get("price")
        budget_prefs = user.get("budget_preferences") or {}
        if dish_price is not None:
            budget_midpoint = float(
                budget_prefs.get("preferred_range")
                or user.get("avg_cost_for_two", 400) / 2
                or 200
            )
            raw = 1.0 - abs(dish_price - budget_midpoint) / max(budget_midpoint, 1)
            user["price_match_score"] = round(max(0.0, min(1.0, raw)), 3)
        elif budget_prefs.get("preferred_range"):
            user["price_match_score"] = 0.6
        else:
            user["price_match_score"] = 0.5

        # Ensemble ranker score (now returns tuple)
        ensemble_score, ranker_breakdown = score_dish(user, dish, context, rank)

        # Cold-start blend
        if use_cold_start and predicted_cuisine is not None:
            # FIX: the ensemble cold-start prediction (KNN + MLP) was computed
            # every request but never read — cold_signal reused the region
            # prior instead, so the trained cold-start models had zero actual
            # effect on ranking. Now: dishes matching the model's predicted
            # cuisine get a real boost; others fall back to the region prior
            # so the signal still degrades gracefully off-prediction.
            if cuisine == predicted_cuisine:
                cold_signal = max(0.8, user.get("cuisine_affinity_score", 0.3))
            else:
                cold_signal = user.get("cuisine_affinity_score", 0.3)
            blended_score = (1 - blend_weight) * cold_signal + blend_weight * ensemble_score
        else:
            blended_score = ensemble_score

        reorder_debug = {}
        boost = reorder_boost(user, dish, food_graph or {}, dish_interactions,
                               debug_out=reorder_debug if debug else None)
        final_score = round(blended_score + boost, 4)

        # Anti-repeat: dishes shown to this user very recently (tracked via
        # Redis by the router) get a mild penalty rather than being
        # excluded outright — keeps the same dish from dominating every
        # single request in a session while still allowing a genuine repeat
        # favorite to surface if nothing else scores close to it.
        if recently_shown and dish.get("dish_name") in recently_shown:
            final_score = round(final_score * 0.85, 4)

        scored.append({
            "dish_name":         dish.get("dish_name"),
            "cuisine_type":      dish.get("cuisine_type"),
            "score":             final_score,
            "reorder_boost":     boost,
            "health_compliant":  health_info["compliant"],
            "health_confidence": health_info["confidence"],
            "health_reasons":    health_info["reasons"],
            "nutrition": {
                "calories":  dish.get("calories_kcal"),
                "protein_g": dish.get("protein_g"),
                "carbs_g":   dish.get("carbs_g"),
                "fat_g":     dish.get("fat_g"),
                "fiber_g":   dish.get("fiber_g"),
                "gi":        dish.get("glycemic_index"),
            },
            "price":     dish.get("price"),
            "is_veg":    dish.get("is_veg"),
            "allergens": dish.get("allergens", []),
            "occasion":  occasion,
            # Per-request model breakdown. ranker/health breakdown were
            # already attached unconditionally before this change — reorder/
            # cold_start/occasion_detection are new, gated behind debug=True
            # so a normal (non-debug) response doesn't carry breakdown data
            # nobody asked for.
            "_models": {
                "ranker":       ranker_breakdown,
                "health":       health_info.get("breakdown", {}),
                "blend_weight": round(blend_weight, 2),
                **({
                    "reorder":            reorder_debug.get("reorder", {}),
                    "cold_start":         cold_breakdown,
                    "cold_start_predicted_cuisine": predicted_cuisine,
                    "occasion_detection": occasion_debug,
                } if debug else {}),
            },
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    # Diversity pass: avoid returning near-duplicate cuisine clusters in
    # the top N every single call (e.g. 5 different rice dishes back to
    # back). Greedily pick highest scoring dish per cuisine first, then
    # backfill remaining slots by score.
    diversified = _diversify(scored, n)
    return diversified


def _diversify(scored: list, n: int, max_per_cuisine: int = 2) -> list:
    """
    Greedy diversity selection: cap how many dishes from the same cuisine
    can appear in the final list, so recommendations don't feel like the
    same 2-3 dishes reshuffled every time you ask.
    """
    result = []
    cuisine_counts = {}

    for item in scored:
        if len(result) >= n:
            break
        cuisine = item.get("cuisine_type", "unknown")
        count   = cuisine_counts.get(cuisine, 0)
        if count < max_per_cuisine:
            result.append(item)
            cuisine_counts[cuisine] = count + 1

    # Backfill if diversity cap left us short (small candidate pools)
    if len(result) < n:
        remaining = [s for s in scored if s not in result]
        result.extend(remaining[: n - len(result)])

    return result
