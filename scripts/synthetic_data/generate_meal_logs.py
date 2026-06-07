"""
NARA Synthetic Data Generator — Meal Log Generator
Generates meal_logs.csv with ~2.5M rows
Every meal has a causal story: why this dish, why now, why this portion
"""
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, date
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from constants import (
    REGIONAL_CUISINE_AFFINITY, CUISINE_DISH_POOLS, MEAL_TIMING,
    MONTH_TO_SEASON, FESTIVALS, FASTING_SCHEDULES, CITY_WEATHER,
    SOCIAL_CONTEXT_BY_DAY, SKIP_PROBABILITY, COMFORT_FOODS,
    STRESS_COMFORT_FOOD_MULTIPLIER, PORTION_MULTIPLIERS,
    DISH_GI_SCORES, DEFAULT_GI, LIVING_SITUATIONS,
    get_month_position_multiplier,
)
from constants import get_fasting_foods
random.seed(42)
np.random.seed(42)

# ── Nutrition lookup (simplified from KB) ─────────────────────
# Per serving nutrition for dishes — simplified for generation
DISH_NUTRITION = {
    "idli":                 {"calories_kcal": 156, "protein_g": 4.1, "carbs_g": 33.6, "fat_g": 0.6, "fiber_g": 1.8},
    "dosa":                 {"calories_kcal": 168, "protein_g": 3.9, "carbs_g": 33.0, "fat_g": 2.5, "fiber_g": 1.2},
    "masala dosa":          {"calories_kcal": 350, "protein_g": 8.4, "carbs_g": 64.0, "fat_g": 7.6, "fiber_g": 4.2},
    "rava dosa":            {"calories_kcal": 216, "protein_g": 5.8, "carbs_g": 39.0, "fat_g": 5.0, "fiber_g": 1.8},
    "uttapam":              {"calories_kcal": 218, "protein_g": 7.2, "carbs_g": 39.0, "fat_g": 4.2, "fiber_g": 3.8},
    "medu vada":            {"calories_kcal": 168, "protein_g": 7.5, "carbs_g": 19.2, "fat_g": 6.6, "fiber_g": 1.9},
    "upma":                 {"calories_kcal": 290, "protein_g": 8.4, "carbs_g": 53.0, "fat_g": 6.4, "fiber_g": 3.6},
    "pongal":               {"calories_kcal": 304, "protein_g": 10.4, "carbs_g": 53.6, "fat_g": 7.0, "fiber_g": 3.0},
    "curd rice":            {"calories_kcal": 295, "protein_g": 9.5, "carbs_g": 51.3, "fat_g": 5.5, "fiber_g": 1.3},
    "sambar":               {"calories_kcal": 104, "protein_g": 6.2, "carbs_g": 16.4, "fat_g": 1.6, "fiber_g": 5.6},
    "rasam":                {"calories_kcal": 56,  "protein_g": 2.4, "carbs_g": 9.6, "fat_g": 1.0, "fiber_g": 1.6},
    "lemon rice":           {"calories_kcal": 296, "protein_g": 5.6, "carbs_g": 57.0, "fat_g": 6.4, "fiber_g": 2.0},
    "tamarind rice":        {"calories_kcal": 310, "protein_g": 5.0, "carbs_g": 58.0, "fat_g": 7.6, "fiber_g": 3.0},
    "bisibelebath":         {"calories_kcal": 370, "protein_g": 13.8, "carbs_g": 61.3, "fat_g": 8.0, "fiber_g": 7.5},
    "appam":                {"calories_kcal": 126, "protein_g": 2.6, "carbs_g": 24.4, "fat_g": 2.2, "fiber_g": 0.6},
    "puttu":                {"calories_kcal": 222, "protein_g": 4.2, "carbs_g": 48.8, "fat_g": 1.8, "fiber_g": 1.5},
    "kerala fish curry":    {"calories_kcal": 250, "protein_g": 29.0, "carbs_g": 9.0, "fat_g": 11.6, "fiber_g": 2.4},
    "avial":                {"calories_kcal": 196, "protein_g": 5.0, "carbs_g": 21.0, "fat_g": 11.0, "fiber_g": 7.0},
    "parotta":              {"calories_kcal": 262, "protein_g": 6.0, "carbs_g": 41.6, "fat_g": 8.4, "fiber_g": 1.6},
    "chicken biryani":      {"calories_kcal": 648, "protein_g": 36.8, "carbs_g": 85.8, "fat_g": 18.2, "fiber_g": 4.2},
    "mutton biryani":       {"calories_kcal": 693, "protein_g": 40.3, "carbs_g": 82.3, "fat_g": 24.5, "fiber_g": 4.2},
    "veg biryani":          {"calories_kcal": 486, "protein_g": 12.6, "carbs_g": 85.5, "fat_g": 11.4, "fiber_g": 7.5},
    "egg biryani":          {"calories_kcal": 525, "protein_g": 25.5, "carbs_g": 72.0, "fat_g": 16.5, "fiber_g": 3.6},
    "dal makhani":          {"calories_kcal": 338, "protein_g": 17.0, "carbs_g": 41.3, "fat_g": 12.0, "fiber_g": 10.5},
    "dal tadka":            {"calories_kcal": 238, "protein_g": 14.5, "carbs_g": 33.8, "fat_g": 5.5, "fiber_g": 8.8},
    "moong dal":            {"calories_kcal": 213, "protein_g": 13.8, "carbs_g": 30.0, "fat_g": 3.8, "fiber_g": 7.5},
    "butter chicken":       {"calories_kcal": 413, "protein_g": 36.3, "carbs_g": 21.3, "fat_g": 20.5, "fiber_g": 3.0},
    "chicken curry":        {"calories_kcal": 370, "protein_g": 38.8, "carbs_g": 13.8, "fat_g": 19.5, "fiber_g": 3.8},
    "chicken tikka":        {"calories_kcal": 370, "protein_g": 45.0, "carbs_g": 9.0, "fat_g": 17.0, "fiber_g": 1.6},
    "tandoori chicken":     {"calories_kcal": 585, "protein_g": 73.5, "carbs_g": 10.5, "fat_g": 28.5, "fiber_g": 1.5},
    "mutton curry":         {"calories_kcal": 463, "protein_g": 46.3, "carbs_g": 12.5, "fat_g": 26.3, "fiber_g": 3.0},
    "rogan josh":           {"calories_kcal": 488, "protein_g": 45.0, "carbs_g": 16.3, "fat_g": 28.8, "fiber_g": 3.8},
    "palak paneer":         {"calories_kcal": 355, "protein_g": 18.8, "carbs_g": 20.5, "fat_g": 22.0, "fiber_g": 7.0},
    "paneer tikka masala":  {"calories_kcal": 445, "protein_g": 23.0, "carbs_g": 26.3, "fat_g": 28.0, "fiber_g": 4.5},
    "chole":                {"calories_kcal": 320, "protein_g": 18.0, "carbs_g": 46.3, "fat_g": 7.0, "fiber_g": 13.8},
    "rajma":                {"calories_kcal": 295, "protein_g": 17.0, "carbs_g": 43.0, "fat_g": 5.5, "fiber_g": 14.5},
    "aloo gobi":            {"calories_kcal": 176, "protein_g": 5.0, "carbs_g": 29.0, "fat_g": 5.6, "fiber_g": 6.4},
    "roti":                 {"calories_kcal": 119, "protein_g": 3.8, "carbs_g": 22.8, "fat_g": 1.5, "fiber_g": 1.8},
    "naan":                 {"calories_kcal": 248, "protein_g": 7.2, "carbs_g": 44.0, "fat_g": 4.6, "fiber_g": 1.8},
    "paratha":              {"calories_kcal": 261, "protein_g": 6.6, "carbs_g": 42.0, "fat_g": 7.6, "fiber_g": 3.0},
    "aloo paratha":         {"calories_kcal": 342, "protein_g": 8.2, "carbs_g": 54.6, "fat_g": 10.2, "fiber_g": 4.2},
    "puri":                 {"calories_kcal": 215, "protein_g": 5.1, "carbs_g": 31.2, "fat_g": 8.1, "fiber_g": 1.5},
    "bhatura":              {"calories_kcal": 308, "protein_g": 7.2, "carbs_g": 44.4, "fat_g": 12.4, "fiber_g": 1.6},
    "pav bhaji":            {"calories_kcal": 380, "protein_g": 10.5, "carbs_g": 56.3, "fat_g": 13.8, "fiber_g": 9.5},
    "vada pav":             {"calories_kcal": 322, "protein_g": 8.6, "carbs_g": 51.0, "fat_g": 9.4, "fiber_g": 3.4},
    "misal pav":            {"calories_kcal": 474, "protein_g": 22.5, "carbs_g": 67.5, "fat_g": 13.5, "fiber_g": 16.5},
    "samosa":               {"calories_kcal": 228, "protein_g": 4.6, "carbs_g": 28.4, "fat_g": 10.8, "fiber_g": 2.6},
    "pani puri":            {"calories_kcal": 198, "protein_g": 4.5, "carbs_g": 35.5, "fat_g": 5.2, "fiber_g": 3.5},
    "bhel puri":            {"calories_kcal": 278, "protein_g": 7.8, "carbs_g": 48.8, "fat_g": 7.2, "fiber_g": 6.3},
    "aloo tikki":           {"calories_kcal": 195, "protein_g": 4.0, "carbs_g": 30.5, "fat_g": 6.5, "fiber_g": 2.8},
    "chole bhature":        {"calories_kcal": 735, "protein_g": 23.4, "carbs_g": 109.5, "fat_g": 25.5, "fiber_g": 12.6},
    "poha":                 {"calories_kcal": 316, "protein_g": 6.4, "carbs_g": 65.0, "fat_g": 5.6, "fiber_g": 3.6},
    "dhokla":               {"calories_kcal": 218, "protein_g": 9.8, "carbs_g": 33.8, "fat_g": 4.8, "fiber_g": 4.2},
    "thepla":               {"calories_kcal": 171, "protein_g": 5.7, "carbs_g": 25.5, "fat_g": 5.1, "fiber_g": 3.3},
    "sabudana khichdi":     {"calories_kcal": 370, "protein_g": 7.0, "carbs_g": 71.0, "fat_g": 9.0, "fiber_g": 2.0},
    "dal baati churma":     {"calories_kcal": 1140, "protein_g": 38.0, "carbs_g": 170.0, "fat_g": 38.0, "fiber_g": 18.0},
    "machher jhol":         {"calories_kcal": 295, "protein_g": 33.8, "carbs_g": 11.3, "fat_g": 13.8, "fiber_g": 3.0},
    "aloo posto":           {"calories_kcal": 230, "protein_g": 5.6, "carbs_g": 31.0, "fat_g": 11.0, "fiber_g": 5.0},
    "luchi":                {"calories_kcal": 221, "protein_g": 5.1, "carbs_g": 31.5, "fat_g": 9.0, "fiber_g": 0.9},
    "rasgulla":             {"calories_kcal": 186, "protein_g": 4.5, "carbs_g": 35.5, "fat_g": 3.8, "fiber_g": 0.0},
    "gulab jamun":          {"calories_kcal": 211, "protein_g": 3.5, "carbs_g": 31.5, "fat_g": 8.1, "fiber_g": 0.3},
    "kheer":                {"calories_kcal": 222, "protein_g": 6.3, "carbs_g": 33.8, "fat_g": 7.2, "fiber_g": 0.5},
    "jalebi":               {"calories_kcal": 304, "protein_g": 3.4, "carbs_g": 52.4, "fat_g": 9.2, "fiber_g": 0.6},
    "halwa":                {"calories_kcal": 443, "protein_g": 6.8, "carbs_g": 68.3, "fat_g": 15.8, "fiber_g": 1.8},
    "ladoo":                {"calories_kcal": 170, "protein_g": 3.4, "carbs_g": 23.4, "fat_g": 7.4, "fiber_g": 1.0},
    "masala chai":          {"calories_kcal": 84, "protein_g": 3.6, "carbs_g": 13.0, "fat_g": 2.4, "fiber_g": 0.0},
    "filter coffee":        {"calories_kcal": 57, "protein_g": 2.3, "carbs_g": 7.8, "fat_g": 1.8, "fiber_g": 0.0},
    "lassi":                {"calories_kcal": 180, "protein_g": 8.8, "carbs_g": 24.5, "fat_g": 5.5, "fiber_g": 0.0},
    "buttermilk":           {"calories_kcal": 56, "protein_g": 3.6, "carbs_g": 7.0, "fat_g": 1.6, "fiber_g": 0.0},
    "steamed rice":         {"calories_kcal": 260, "protein_g": 5.4, "carbs_g": 56.4, "fat_g": 0.6, "fiber_g": 0.8},
    "khichdi":              {"calories_kcal": 295, "protein_g": 13.0, "carbs_g": 51.3, "fat_g": 5.5, "fiber_g": 7.0},
    "egg curry":            {"calories_kcal": 290, "protein_g": 19.0, "carbs_g": 13.0, "fat_g": 18.0, "fiber_g": 2.4},
    "anda bhurji":          {"calories_kcal": 263, "protein_g": 17.3, "carbs_g": 6.8, "fat_g": 18.8, "fiber_g": 1.2},
    "dahi":                 {"calories_kcal": 92, "protein_g": 5.3, "carbs_g": 7.1, "fat_g": 5.0, "fiber_g": 0.0},
    "raita":                {"calories_kcal": 52, "protein_g": 2.8, "carbs_g": 5.5, "fat_g": 2.2, "fiber_g": 0.5},
    "coconut water":        {"calories_kcal": 57, "protein_g": 2.1, "carbs_g": 11.1, "fat_g": 0.6, "fiber_g": 3.3},
    "nimbu pani":           {"calories_kcal": 55, "protein_g": 0.5, "carbs_g": 13.8, "fat_g": 0.0, "fiber_g": 0.0},
    "pulao":                {"calories_kcal": 388, "protein_g": 8.8, "carbs_g": 70.0, "fat_g": 8.0, "fiber_g": 4.5},
    "jeera rice":           {"calories_kcal": 296, "protein_g": 5.6, "carbs_g": 57.0, "fat_g": 5.6, "fiber_g": 1.0},
}

DEFAULT_NUTRITION = {"calories_kcal": 250, "protein_g": 8.0, "carbs_g": 35.0, "fat_g": 8.0, "fiber_g": 3.0}


def get_festival_on_date(dt: date, religion: str, region: str) -> tuple:
    """Returns (festival_name, food_impact_dict) or (None, {})"""
    for festival in FESTIVALS:
        if festival["month"] != dt.month:
            continue
        if dt.day not in festival["days"]:
            continue
        # Check religion match
        rel_match = "all" in festival["religions"] or religion in festival["religions"]
        # Check region match
        reg_match = "all" in festival["region"] or region in festival["region"]
        if rel_match and reg_match:
            return festival["name"], festival.get("food_impact", {})
    return None, {}


def get_daily_stress(base_stress: str, day_of_week: int, month_day: int,
                      is_exam_period: bool = False) -> str:
    """Compute stress level for a specific day"""
    stress_levels = ["none", "low", "medium", "high", "extreme"]
    base_idx = {"low": 1, "medium": 2, "high": 3}.get(base_stress, 2)

    # Monday higher stress
    if day_of_week == 0:
        base_idx = min(4, base_idx + 1)
    # Friday lower stress
    elif day_of_week == 4:
        base_idx = max(0, base_idx - 1)
    # Weekend lower stress
    elif day_of_week in [5, 6]:
        base_idx = max(0, base_idx - 1)

    # Month end stress
    if month_day >= 28:
        base_idx = min(4, base_idx + 1)

    # Exam period
    if is_exam_period:
        base_idx = min(4, base_idx + 2)

    # Add randomness
    base_idx = max(0, min(4, base_idx + random.randint(-1, 1)))
    return stress_levels[base_idx]


def select_dish(user: dict, occasion: str, dt: date, stress_level: str,
                social_context: str, is_fast: bool,
                festival_name: str, food_impact: dict,
                last_meals: list, dish_freq=None) -> tuple:
    """
    Select a dish based on all context.
    Returns (dish_name, cuisine_type, is_health_compliant)
    """
    region = str(user.get("region", "north"))
    religion = str(user.get("religion", "hindu"))
    is_vegetarian = str(user.get("is_vegetarian", "False")).lower() in ("true", "1", "yes")
    conditions = [c.strip() for c in str(user.get("conditions", "")).split("|") if c.strip()]
    health_literacy = float(user.get("health_literacy", 0.5))
    habit_strength = float(user.get("habit_strength", 0.6))
    dietary_restrictions = [r.strip() for r in str(user.get("dietary_restrictions", "")).split("|") if r.strip()]

    # ── Fasting overrides everything ─────────────────────────
    # NEW — replace with this
    if is_fast:
        from constants import get_fasting_foods
        fasting_dishes = get_fasting_foods(religion, "during")
        dish = weighted_choice_dict(fasting_dishes)
        return dish, "staple", True

    # ── Festival food boost ───────────────────────────────────
    if festival_name and food_impact and random.random() < 0.55:
        boosted = list(food_impact.keys())
        festival_dish_map = {
            "sweet_pongal": "sweet pongal", "biryani": "chicken biryani",
            "sweets": "ladoo", "ladoo": "ladoo", "barfi": "barfi",
            "kaju_katli": "kaju katli", "modak": "ukdiche modak",
            "sabudana": "sabudana khichdi", "fasting_foods": "sabudana khichdi",
            "thandai": "thandai", "shrikhand": "shrikhand",
            "til_sweets": "ladoo", "khichdi": "khichdi",
            "payasam": "payasam", "fish": "machher jhol",
            "mutton": "mutton curry",
        }
        for b in boosted:
            if b in festival_dish_map:
                if is_vegetarian and festival_dish_map[b] in ["chicken biryani", "mutton curry", "machher jhol"]:
                    continue
                return festival_dish_map[b], "dessert", True

    # ── Stress → comfort food ─────────────────────────────────
    stress_multiplier = STRESS_COMFORT_FOOD_MULTIPLIER.get(stress_level, 1.0)
    if stress_multiplier > 1.3 and random.random() < (stress_multiplier - 1.0) * 0.5:
        comfort_pool = COMFORT_FOODS.get(region, ["khichdi", "dal tadka"])
        if is_vegetarian:
            comfort_pool = [d for d in comfort_pool if d not in ["chicken biryani", "mutton curry"]]
        if comfort_pool:
            return random.choice(comfort_pool), "comfort", False

    # ── Habit repetition ──────────────────────────────────────
    if last_meals and dish_freq and random.random() < habit_strength * 0.5:
        candidates = {d: dish_freq[d] for d in set(last_meals) if d in dish_freq}
        if candidates:
            total = sum(candidates.values())
            weights = [candidates[d] / total for d in candidates]
            chosen = np.random.choice(list(candidates.keys()), p=weights)
            cuisine = get_dish_cuisine(chosen)
            return chosen, cuisine, check_health_compliance(chosen, conditions, health_literacy)

    # ── Occasion-based filtering ──────────────────────────────
    occasion_cuisine_prefs = {
        "breakfast": ["south_indian", "north_indian", "staple", "beverage"],
        "lunch":     ["south_indian", "north_indian", "biryani", "gujarati", "maharashtrian", "bengali", "staple"],
        "snack":     ["street_food", "south_indian", "beverage", "dessert"],
        "dinner":    ["north_indian", "south_indian", "biryani", "bengali", "rajasthani", "staple"],
        "late_night":["street_food", "staple", "north_indian"],
    }
    preferred_cuisines = occasion_cuisine_prefs.get(occasion, ["north_indian", "staple"])

    # Add regional cuisine preference
    from constants import REGIONAL_CUISINE_AFFINITY_BY_STATE
    birthplace_state = str(user.get("birthplace_state", ""))
    region_affinities = (
    REGIONAL_CUISINE_AFFINITY_BY_STATE.get(birthplace_state)
    or REGIONAL_CUISINE_AFFINITY.get(region, {})
    )
    cuisine_weights = {}
    for cuisine in preferred_cuisines:
        affinity = region_affinities.get(cuisine, (0.5, 0.3))
        if isinstance(affinity, tuple):
            weight = max(0.1, np.random.normal(affinity[0], affinity[1]))
        else:
            weight = affinity
        cuisine_weights[cuisine] = weight

    # Select cuisine
    if not cuisine_weights:
        cuisine_weights = {"north_indian": 1.0}
    selected_cuisine = weighted_choice_dict(cuisine_weights)

    # Get dish pool for cuisine
    dish_pool = CUISINE_DISH_POOLS.get(selected_cuisine, [])

    # Filter by dietary restrictions
    restricted_dishes = get_restricted_dishes(dietary_restrictions, is_vegetarian, religion)
    dish_pool = [d for d in dish_pool if d not in restricted_dishes]

    if not dish_pool:
        dish_pool = ["steamed rice", "roti", "dal tadka"]

    # Health-aware selection
    if conditions:
        compliant = [d for d in dish_pool if check_health_compliance(d, conditions, health_literacy)]
        non_compliant = [d for d in dish_pool if d not in compliant]

        if not compliant:
            dish = random.choice(dish_pool)
        elif not non_compliant:
            dish = random.choice(compliant)
        else:
            # Scale directly with literacy — 0.3 literacy = 30% chance compliant
            # 0.9 literacy = 90% chance compliant
            # This creates the positive correlation the validator checks
            effective_prob = max(0.2, health_literacy)  # minimum 20% even for lowest literacy
            if random.random() < effective_prob:
                dish = random.choice(compliant)
            else:
                dish = random.choice(non_compliant)
    else:
        dish = random.choice(dish_pool)

    is_compliant = check_health_compliance(dish, conditions, health_literacy)
    return dish, selected_cuisine, is_compliant


def get_restricted_dishes(restrictions: list, is_vegetarian: bool, religion: str) -> list:
    restricted = []

    # ── Non-veg filter ────────────────────────────────────────
    non_veg_dishes = [
        "chicken biryani", "mutton biryani", "egg biryani", "prawn biryani",
        "butter chicken", "chicken curry", "chicken tikka", "tandoori chicken",
        "chicken korma", "chicken do pyaza", "mutton curry", "rogan josh",
        "keema", "gongura mutton", "laal maas", "kerala fish curry",
        "machher jhol", "shorshe ilish", "chingri malai curry",
        "goan fish curry", "vindaloo", "kottu roti", "kathi roll",
        "egg curry", "anda bhurji", "egg", "chicken",
    ]
    if is_vegetarian:
        restricted.extend(non_veg_dishes)

    # ── Dairy filter ──────────────────────────────────────────
    if "no_dairy" in restrictions:
        restricted.extend([
            "kheer", "rasmalai", "kulfi", "shrikhand", "rabdi",
            "lassi", "masala chai", "dahi", "raita", "filter coffee",
            "paneer tikka masala", "palak paneer", "shahi paneer",
            "kadai paneer", "matar paneer", "malai kofta",
            "mishti doi", "buttermilk", "dahi puri",
        ])

    # ── Gluten filter ─────────────────────────────────────────
    if "no_gluten" in restrictions:
        restricted.extend([
            "naan", "bhatura", "paratha", "aloo paratha", "gobi paratha",
            "paneer paratha", "missi roti", "puri", "samosa", "upma",
            "roti", "thepla", "kathi roll", "vada pav", "pav bhaji",
            "misal pav", "dal baati churma",
        ])

    # ── Jain / no_onion_garlic filter ─────────────────────────
    if "no_onion_garlic" in restrictions or "jain" in restrictions:
        restricted.extend([
            "butter chicken", "chicken curry", "dal makhani", "chole",
            "rajma", "palak paneer", "paneer tikka masala", "pav bhaji",
            "keema", "laal maas", "gongura mutton", "rogan josh",
            "aloo gobi", "bhindi masala", "baingan bharta",
        ])

    # ── No root vegetables (Jain) ─────────────────────────────
    if "no_root_vegetables" in restrictions:
        restricted.extend([
            "aloo paratha", "aloo gobi", "aloo posto", "aloo matar",
            "aloo tikki", "vada pav", "samosa", "chole bhature",
        ])

    # ── No beef ───────────────────────────────────────────────
    if "no_beef" in restrictions:
        restricted.extend(["beef curry", "beef biryani"])

    # ── Halal / Muslim ────────────────────────────────────────
    if religion == "muslim":
        restricted.extend(["vindaloo"])  # pork-based

    # ── Low GI (diabetes) ─────────────────────────────────────
    if "low_gi" in restrictions:
        restricted.extend([
            "steamed rice", "naan", "puri", "bhatura", "jalebi",
            "gulab jamun", "kheer", "sabudana khichdi", "poha",
        ])

    # ── Low sodium (hypertension) ─────────────────────────────
    if "low_sodium" in restrictions:
        restricted.extend([
            "dal makhani", "butter chicken", "chole",
            "pav bhaji", "samosa", "bhel puri", "vada pav",
        ])

    return list(set(restricted))  # deduplicate


def check_health_compliance(dish: str, conditions: list, health_literacy: float) -> bool:
    """Check if dish is appropriate for user's health conditions"""
    if not conditions or conditions == ['']:
        return True

    gi = DISH_GI_SCORES.get(dish, DEFAULT_GI)
    nutrition = DISH_NUTRITION.get(dish, DEFAULT_NUTRITION)

    if "type2_diabetes" in conditions or "prediabetes" in conditions:
        if gi > 70:
            return False

    if "hypertension" in conditions:
        sodium = nutrition.get("sodium_mg", 400)
        if sodium > 800:
            return False

    if "obesity" in conditions:
        calories = nutrition.get("calories_kcal", 300)
        if calories > 600 and health_literacy > 0.5:
            return False

    return True


def get_dish_cuisine(dish: str) -> str:
    for cuisine, dishes in CUISINE_DISH_POOLS.items():
        if dish in dishes:
            return cuisine
    return "north_indian"


def weighted_choice_dict(d: dict) -> str:
    if not d:
        return "steamed rice"
    keys = list(d.keys())
    weights = [max(0.01, v) for v in d.values()]
    total = sum(weights)
    weights = [w / total for w in weights]
    return np.random.choice(keys, p=weights)


def get_meal_occasions_for_day(user: dict, dt: date, is_fast: bool) -> list:
    """Determine which meals user has on a given day"""
    occupation = user.get("occupation", "office_worker")
    is_weekend = dt.weekday() >= 5
    occasions = []

    # Breakfast
    skip_prob = SKIP_PROBABILITY["breakfast"].get(occupation, 0.18)
    if is_weekend:
        skip_prob *= 0.5  # less likely to skip on weekend
    if not is_fast and random.random() > skip_prob:
        occasions.append("breakfast")
    elif is_fast:
        # On fast days, might have limited breakfast
        if random.random() < 0.4:
            occasions.append("breakfast")

    # Lunch
    skip_prob_lunch = SKIP_PROBABILITY["lunch"].get(occupation, 0.08)
    if random.random() > skip_prob_lunch:
        occasions.append("lunch")

    # Snack
    snack_prob = 0.55 if is_weekend else 0.45
    if occupation == "student":
        snack_prob = 0.65
    if random.random() < snack_prob:
        occasions.append("snack")

    # Dinner
    skip_prob_dinner = SKIP_PROBABILITY["dinner"].get("default", 0.03)
    if random.random() > skip_prob_dinner:
        occasions.append("dinner")

    # Late night (students, young metro)
    late_night_prob = 0.0
    if occupation == "student":
        late_night_prob = 0.20
    elif user.get("current_city_tier") == 1 and user.get("age", 30) < 32:
        late_night_prob = 0.12
    if random.random() < late_night_prob:
        occasions.append("late_night")

    return occasions


def generate_meal_timestamp(user: dict, dt: date, occasion: str) -> datetime:
    """Generate realistic timestamp for a meal"""
    region = user.get("region", "north")
    timing = MEAL_TIMING.get(region, MEAL_TIMING["north"])
    mean_hour, std = timing.get(occasion, (13.0, 0.8))

    # Weekend meals are later
    if dt.weekday() >= 5:
        mean_hour += 0.5

    # Late night special
    if occasion == "late_night":
        mean_hour = 22.5
        std = 0.8

    OCCASION_HOUR_FLOOR = {
    "breakfast":  5.0,
    "lunch":     11.5,
    "snack":     14.0,
    "dinner":    18.0,
    "late_night":21.5,
    }
    
    OCCASION_STD = {
        "breakfast":  0.5,   # was 0.8-1.0, tighter to prevent 10am breakfast
        "lunch":      0.5,   # was 0.7-0.8
        "snack":      0.7,
        "dinner":     0.5,   # was 0.8-1.0, tighter to prevent 5pm dinner
        "late_night": 0.5,
    }

    hour = np.random.normal(mean_hour, std)
    floor = OCCASION_HOUR_FLOOR.get(occasion, 5.0)
    hour = max(floor, min(23.5, hour))
    minutes = random.randint(0, 59)
    seconds = random.randint(0, 59)
    return datetime(dt.year, dt.month, dt.day, int(hour), minutes, seconds)


def compute_portion_multiplier(social_context: str, stress_level: str,
                                is_post_skip: bool, occasion: str,
                                is_festival: bool) -> float:
    """Compute realistic portion size multiplier"""
    multiplier = 1.0

    if social_context == "alone" and stress_level in ["high", "extreme"]:
        multiplier *= PORTION_MULTIPLIERS["alone_stressed"]
    elif social_context == "alone":
        multiplier *= PORTION_MULTIPLIERS["alone_weekday"]
    elif social_context in ["with_colleagues"]:
        multiplier *= PORTION_MULTIPLIERS["with_colleagues"]
    elif social_context in ["with_friends", "at_restaurant"]:
        multiplier *= PORTION_MULTIPLIERS["with_friends"]

    if is_post_skip:
        multiplier *= PORTION_MULTIPLIERS["post_skip"]

    if is_festival:
        multiplier *= PORTION_MULTIPLIERS["festival"]

    if occasion == "late_night":
        multiplier *= PORTION_MULTIPLIERS["late_night"]

    return round(max(0.5, min(2.5, multiplier + np.random.normal(0, 0.1))), 2)


def generate_meal_logs_for_user(user: dict, start_date: date,
                                 end_date: date) -> list:
    """Generate all meal logs for a single user over their active period"""
    meals = []
    last_dishes = []
    dish_freq = {}
    current_date = start_date
    meal_id_counter = 0

    # User-level fasting schedule
    religion = user.get("religion", "hindu")
    observance = float(user.get("observance_level", 0.4))
    is_vegetarian = str(user.get("is_vegetarian", "False")).lower() in ("true", "1", "yes")
    conditions = [c.strip() for c in str(user.get("conditions", "")).split("|") if c.strip()]
    dietary_restrictions = [r.strip() for r in str(user.get("dietary_restrictions", "")).split("|") if r.strip()]
    
    while current_date <= end_date:
        month = current_date.month
        day = current_date.day
        day_of_week = current_date.weekday()
        season = MONTH_TO_SEASON.get(month, "summer")
        is_weekend = day_of_week >= 5

        # Check festival
        festival_name, food_impact = get_festival_on_date(
            current_date, religion, user.get("region", "north")
        )

        # Check fasting
        is_fast = False
        fast_type = None
        if religion in FASTING_SCHEDULES:
            fasting = FASTING_SCHEDULES[religion]
            # Monday fast for Hindus
            if religion == "hindu" and day_of_week == 0:
                if random.random() < fasting.get("monday_fast", {}).get("probability", 0.18) * observance:
                    is_fast = True
                    fast_type = "monday_fast"
            # Ekadashi (11th and 26th of month approx)
            if religion == "hindu" and day in [11, 26]:
                if random.random() < 0.25 * observance:
                    is_fast = True
                    fast_type = "ekadashi"

        # Daily stress
        is_exam = (user.get("occupation") == "student" and month in [3, 4, 10, 11])
        stress_level = get_daily_stress(
            user.get("stress_profile", "medium"),
            day_of_week, day, is_exam
        )

        # Budget state
        budget_multiplier = get_month_position_multiplier(day)

        # Get occasions for today
        occasions = get_meal_occasions_for_day(user, current_date, is_fast)

        prev_occasion_skipped = False
        for i, occasion in enumerate(["breakfast", "lunch", "snack", "dinner", "late_night"]):
            if occasion not in occasions:
                prev_occasion_skipped = True
                continue

            # Social context
            day_type = "weekend" if is_weekend else "weekday"
            social_dist = SOCIAL_CONTEXT_BY_DAY.get(day_type, {}).get(occasion, {"alone": 0.7, "with_family": 0.3})
            social_context = weighted_choice_dict(social_dist)

            # Select dish
            dish, cuisine_type, is_compliant = select_dish(
                user, occasion, current_date, stress_level,
                social_context, is_fast, festival_name, food_impact,
                last_dishes[-3:] if last_dishes else []
            )

            # Timestamp
            timestamp = generate_meal_timestamp(user, current_date, occasion)

            # Portion multiplier
            portion_mult = compute_portion_multiplier(
                social_context, stress_level,
                prev_occasion_skipped,
                occasion, bool(festival_name)
            )

            # Nutrition
            base_nutrition = DISH_NUTRITION.get(dish, DEFAULT_NUTRITION)
            gi = DISH_GI_SCORES.get(dish, DEFAULT_GI)

            # Cooking vs ordering
            living_probs = LIVING_SITUATIONS.get(user.get("living_situation", "with_family"), {})
            cook_prob = living_probs.get("cooking_prob", 0.5)
            # Cooking skill modifies probability
            cook_prob *= float(user.get("cooking_skill", 0.5))
            # Budget state affects ordering
            if budget_multiplier < 0.8:
                cook_prob = min(0.95, cook_prob * 1.3)
            ordered_delivery = random.random() > cook_prob
            cooking_at_home = not ordered_delivery

            # Weather
            city_weather = CITY_WEATHER.get(user.get("current_city", "default"), CITY_WEATHER["default"])
            weather_info = city_weather.get(month, (28, "dry"))
            weather_condition = weather_info[1] if isinstance(weather_info, tuple) else "dry"

            # Repeat meal check
            is_repeat = dish in last_dishes
            days_since_last = 0
            if is_repeat and dish in last_dishes:
                idx = len(last_dishes) - 1 - last_dishes[::-1].index(dish)
                days_since_last = len(last_dishes) - idx
            base = float(user.get("health_literacy", 0.5)) * (1.0 if is_compliant else 0.3) 
            noise = np.random.normal(0, 0.05)
            meal_record = {
                "meal_id":              f"ML{user['user_id']}{meal_id_counter:04d}",
                "user_id":              user["user_id"],
                "dish_name":            dish,
                "cuisine_type":         cuisine_type,
                "occurred_at":          timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "meal_occasion":        occasion,
                "day_of_week":          day_of_week,
                "month":                month,
                "season":               season,
                "is_weekend":           is_weekend,
                "is_festival_day":      bool(festival_name),
                "festival_name":        festival_name or "",
                "is_fast_day":          is_fast,
                "fast_type":            fast_type or "",
                "social_context":       social_context,
                "eating_alone":         social_context == "alone",
                "stress_level":         stress_level,
                "hunger_level":         "high" if prev_occasion_skipped else "normal",
                "budget_availability":  budget_multiplier,
                "month_position":       "early" if day <= 10 else "mid" if day <= 20 else "late",
                "cooking_at_home":      cooking_at_home,
                "ordered_delivery":     ordered_delivery,
                "portion_multiplier":   portion_mult,
                "estimated_calories":   round(base_nutrition["calories_kcal"] * portion_mult, 1),
                "estimated_protein_g":  round(base_nutrition["protein_g"] * portion_mult, 1),
                "estimated_carbs_g":    round(base_nutrition["carbs_g"] * portion_mult, 1),
                "estimated_fat_g":      round(base_nutrition["fat_g"] * portion_mult, 1),
                "estimated_fiber_g":    round(base_nutrition["fiber_g"] * portion_mult, 1),
                "gi_score":             gi,
                "weather_condition":    weather_condition,
                "health_compliant":     is_compliant,
                "repeat_meal":          is_repeat,
                "days_since_last_same": days_since_last,
                "life_event_phase":     "normal",
                "compliance_score": round(float(np.clip(base + noise, 0.0, 1.0)), 2),
            }

            meals.append(meal_record)
            dish_freq[dish] = dish_freq.get(dish, 0) + 1
            last_dishes.append(dish)
            if len(last_dishes) > 20:
                last_dishes.pop(0)

            prev_occasion_skipped = False
            meal_id_counter += 1

        current_date += timedelta(days=1)

    return meals


def generate_meal_logs_csv(users_csv: str = "data/users.csv",
                            output_path: str = "data/meal_logs.csv",
                            days_of_history: int = 365,
                            chunk_size: int = 1000):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"Loading users from {users_csv}...")
    users_df = pd.read_csv(users_csv)
    n_users = len(users_df)
    print(f"Generating meal logs for {n_users:,} users over {days_of_history} days...")

    end_date = date.today()
    start_date = end_date - timedelta(days=days_of_history)

    total_meals = 0
    first_write = True

    for chunk_start in range(0, n_users, chunk_size):
        chunk_end = min(chunk_start + chunk_size, n_users)
        chunk_users = users_df.iloc[chunk_start:chunk_end]
        chunk_meals = []

        for _, user in chunk_users.iterrows():
            user_dict = user.to_dict()
            # Users have varying history length based on signup date
            created_at = pd.to_datetime(user_dict.get("created_at", str(start_date))).date()
            user_start = max(start_date, created_at)
            meals = generate_meal_logs_for_user(user_dict, user_start, end_date)
            chunk_meals.extend(meals)

        df_chunk = pd.DataFrame(chunk_meals)

        if first_write:
            df_chunk.to_csv(output_path, index=False, mode='w')
            first_write = False
        else:
            df_chunk.to_csv(output_path, index=False, mode='a', header=False)

        total_meals += len(chunk_meals)
        pct = chunk_end / n_users * 100
        print(f"  Users {chunk_start+1:,}-{chunk_end:,} done | Meals so far: {total_meals:,} ({pct:.1f}%)")

    print(f"\nDone. {total_meals:,} meal logs written to {output_path}")
    return total_meals


if __name__ == "__main__":
    generate_meal_logs_csv(
        users_csv="data/users.csv",
        output_path="data/meal_logs.csv",
        days_of_history=365,
    )