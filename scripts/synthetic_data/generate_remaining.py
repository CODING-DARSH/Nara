"""
NARA Synthetic Data Generator — Remaining CSV Generators
Generates:
  - user_weekly_context.csv
  - interactions.csv
  - life_events.csv
  - fast_days.csv
  - skip_events.csv
  - reorder_events.csv
  - health_outcomes.csv
  - social_eating_context.csv
"""
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, date
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from constants import (
    MONTH_TO_SEASON, FESTIVALS, LIFE_EVENT_TYPES,
    FASTING_SCHEDULES, DISH_GI_SCORES, DEFAULT_GI,
    get_month_position_multiplier,
    compute_compliance_improvement,
)
from constants import get_fasting_foods
random.seed(42)
np.random.seed(42)


# ════════════════════════════════════════════════════════════
# 1. USER WEEKLY CONTEXT
# ════════════════════════════════════════════════════════════
def weighted_choice_dict(d: dict) -> str:
    if not d:
        return "steamed rice"
    keys = list(d.keys())
    weights = [max(0.01, v) for v in d.values()]
    total = sum(weights)
    weights = [w / total for w in weights]
    return np.random.choice(keys, p=weights)

def generate_weekly_context_csv(users_csv: str = "data/users.csv",
                                  meal_logs_csv: str = "data/meal_logs.csv",
                                  output_path: str = "data/user_weekly_context.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print("Generating user_weekly_context.csv...")

    users_df = pd.read_csv(users_csv)
    meals_df = pd.read_csv(meal_logs_csv, parse_dates=["occurred_at"])

    # Add week number
    meals_df["week"] = meals_df["occurred_at"].dt.isocalendar().week
    meals_df["year"] = meals_df["occurred_at"].dt.year
    meals_df["week_start"] = meals_df["occurred_at"].dt.to_period("W").dt.start_time

    records = []
    user_meal_groups = meals_df.groupby("user_id")

    for _, user in users_df.iterrows():
        uid = user["user_id"]
        if uid not in user_meal_groups.groups:
            continue

        user_meals = user_meal_groups.get_group(uid)
        week_groups = user_meals.groupby(["year", "week"])

        for (year, week), week_meals in week_groups:
            week_start = week_meals["week_start"].min()
            month = week_start.month if hasattr(week_start, 'month') else 1

            # Festival in this week
            festivals_this_week = []
            for d in range(7):
                dt = (week_start + timedelta(days=d)).date() if hasattr(week_start, 'date') else date.today()
                for festival in FESTIVALS:
                    if festival["month"] == month and (d + week_start.day if hasattr(week_start, 'day') else 1) in festival["days"]:
                        festivals_this_week.append(festival["name"])

            n_meals = len(week_meals)
            n_ordered = week_meals["ordered_delivery"].sum() if "ordered_delivery" in week_meals.columns else 0
            n_cooked = week_meals["cooking_at_home"].sum() if "cooking_at_home" in week_meals.columns else 0
            avg_cal = week_meals["estimated_calories"].mean() if "estimated_calories" in week_meals.columns else 250
            avg_gi = week_meals["gi_score"].mean() if "gi_score" in week_meals.columns else 55
            avg_protein = week_meals["estimated_protein_g"].mean() if "estimated_protein_g" in week_meals.columns else 15
            avg_carbs = week_meals["estimated_carbs_g"].mean() if "estimated_carbs_g" in week_meals.columns else 45
            avg_fat = week_meals["estimated_fat_g"].mean() if "estimated_fat_g" in week_meals.columns else 12
            avg_fiber = week_meals["estimated_fiber_g"].mean() if "estimated_fiber_g" in week_meals.columns else 5
            compliance_rate = week_meals["health_compliant"].mean() if "health_compliant" in week_meals.columns else 0.7
            stress_mode = week_meals["stress_level"].mode()[0] if "stress_level" in week_meals.columns and len(week_meals) > 0 else "medium"
            social_mode = week_meals["social_context"].mode()[0] if "social_context" in week_meals.columns and len(week_meals) > 0 else "alone"

            # Nutritional gaps (simplified)
            protein_gap = max(0, 60 - avg_protein * 3)   # assuming 3 meals
            carb_gap = max(0, 250 - avg_carbs * 3)
            fat_gap = max(0, 55 - avg_fat * 3)
            fiber_gap = max(0, 30 - avg_fiber * 3)

            records.append({
                "user_id":                  uid,
                "week_number":              week,
                "year":                     year,
                "week_start_date":          str(week_start)[:10],
                "avg_stress_level":         stress_mode,
                "dominant_social_context":  social_mode,
                "budget_state":             get_month_position_multiplier(week_start.day if hasattr(week_start, 'day') else 15),
                "health_compliance_rate":   round(float(compliance_rate), 3),
                "meals_logged":             n_meals,
                "meals_ordered":            int(n_ordered),
                "meals_cooked":             int(n_cooked),
                "avg_calories":             round(float(avg_cal), 1),
                "avg_gi":                   round(float(avg_gi), 1),
                "avg_protein_g":            round(float(avg_protein), 1),
                "avg_carbs_g":              round(float(avg_carbs), 1),
                "avg_fat_g":                round(float(avg_fat), 1),
                "avg_fiber_g":              round(float(avg_fiber), 1),
                "protein_gap_g":            round(float(protein_gap), 1),
                "carb_gap_g":               round(float(carb_gap), 1),
                "fat_gap_g":                round(float(fat_gap), 1),
                "fiber_gap_g":              round(float(fiber_gap), 1),
                "life_event_active":        False,
                "life_event_type":          "",
                "season":                   MONTH_TO_SEASON.get(month, "summer"),
                "festivals_in_week":        "|".join(set(festivals_this_week)),
            })

    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    print(f"  Done. {len(df):,} weekly context rows → {output_path}")
    return df


# ════════════════════════════════════════════════════════════
# 2. INTERACTIONS
# ════════════════════════════════════════════════════════════

ALL_DISHES = [
    "idli", "dosa", "masala dosa", "uttapam", "upma", "pongal", "curd rice",
    "sambar", "rasam", "chicken biryani", "mutton biryani", "veg biryani",
    "dal makhani", "dal tadka", "butter chicken", "chicken curry", "chicken tikka",
    "palak paneer", "paneer tikka masala", "chole", "rajma", "aloo gobi",
    "roti", "naan", "paratha", "aloo paratha", "puri", "bhatura",
    "pav bhaji", "vada pav", "samosa", "pani puri", "bhel puri",
    "poha", "dhokla", "thepla", "sabudana khichdi",
    "gulab jamun", "kheer", "jalebi", "ladoo", "barfi",
    "masala chai", "filter coffee", "lassi", "buttermilk",
    "steamed rice", "khichdi", "egg curry", "anda bhurji",
    "machher jhol", "aloo posto", "luchi", "rasgulla",
    "dal baati churma", "laal maas", "misal pav", "puran poli",
]


def simulate_interaction(user: dict, dish: str, rank: int,
                          context_time: int, context_day: int,
                          context_season: str, context_stress: str,
                          context_budget: float) -> dict:
    """Simulate realistic click/order behaviour"""
    is_vegetarian = user.get("is_vegetarian", False)
    conditions = [c.strip() for c in str(user.get("conditions", "")).split("|") if c.strip()]
    health_literacy = float(user.get("health_literacy", 0.5))
    income_tier = user.get("income_tier", "medium")

    non_veg = ["chicken biryani", "mutton biryani", "butter chicken", "chicken curry",
               "chicken tikka", "mutton curry", "laal maas", "machher jhol",
               "egg curry", "anda bhurji", "luchi"]

    # Base click probability
    click_prob = max(0.05, 0.45 - rank * 0.04)

    # Vegetarian filter
    if is_vegetarian and dish in non_veg:
        click_prob = 0.01

    # Health condition filter
    gi = DISH_GI_SCORES.get(dish, DEFAULT_GI)
    if ("type2_diabetes" in conditions or "prediabetes" in conditions) and gi > 70:
        click_prob *= (1 - health_literacy * 0.7)

    # Budget filter
    expensive_dishes = ["chicken biryani", "mutton biryani", "butter chicken",
                        "dal baati churma", "chicken tikka"]
    if dish in expensive_dishes and income_tier == "low" and context_budget < 0.85:
        click_prob *= 0.4

    # Time of day relevance
    breakfast_dishes = ["idli", "dosa", "upma", "poha", "masala chai", "filter coffee", "pongal"]
    dinner_dishes = ["chicken biryani", "mutton biryani", "dal makhani", "butter chicken", "roti", "naan"]
    snack_dishes = ["samosa", "pani puri", "bhel puri", "masala chai", "lassi"]

    if context_time < 10 and dish in dinner_dishes:
        click_prob *= 0.3
    elif context_time >= 18 and dish in breakfast_dishes:
        click_prob *= 0.4
    elif 14 <= context_time <= 17 and dish in snack_dishes:
        click_prob *= 1.4

    # Weekend effect
    if context_day >= 5:
        if dish in ["chicken biryani", "mutton biryani", "dal baati churma"]:
            click_prob *= 1.3

    
    clicked = random.random() < click_prob
    order_prob = 0.0
    if clicked:
        order_prob = 0.35 - rank * 0.03
        if context_budget < 0.75:
            order_prob *= 0.6
        if context_stress in ["high", "extreme"]:
            order_prob *= 1.2

    ordered = clicked and random.random() < order_prob
    if ordered:
        session_duration = random.randint(90, 300)   # ordered → long session
    elif clicked:
        session_duration = random.randint(20, 120)   # clicked → medium
    else:
        session_duration = random.randint(1, 15)   

    # Order probability given click


    return {
        "action":           "order" if ordered else ("click" if clicked else "skip"),
        "session_duration": session_duration,
        "final_ordered":    ordered,
    }


def generate_interactions_csv(users_csv: str = "data/users.csv",
                                output_path: str = "data/interactions.csv",
                                n_interactions: int = 1000000):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print(f"Generating {n_interactions:,} interactions...")

    users_df = pd.read_csv(users_csv)
    users = users_df.to_dict("records")
    seasons = ["summer", "monsoon", "winter", "autumn"]
    stress_levels = ["none", "low", "medium", "high"]

    records = []
    chunk_size = 50000

    for i in range(n_interactions):
        user = random.choice(users)

        # Context
        dt = date.today() - timedelta(days=random.randint(0, 365))
        context_time = random.randint(7, 23)
        context_day = dt.weekday()
        context_season = MONTH_TO_SEASON.get(dt.month, "summer")
        context_stress = random.choice(stress_levels)
        context_budget = get_month_position_multiplier(dt.day)

        # Recommendation set (5-10 dishes shown)
        n_shown = random.randint(5, 10)
        shown_dishes = random.sample(ALL_DISHES, min(n_shown, len(ALL_DISHES)))

        for rank, dish in enumerate(shown_dishes):
            interaction = simulate_interaction(
                user, dish, rank, context_time, context_day,
                context_season, context_stress, context_budget
            )

            records.append({
                "interaction_id":       f"INT{i:08d}R{rank}",
                "user_id":              user["user_id"],
                "dish_name":            dish,
                "cuisine_type":         "mixed",
                "timestamp":            datetime(dt.year, dt.month, dt.day, context_time, random.randint(0, 59)).strftime("%Y-%m-%d %H:%M:%S"),
                "context_time_of_day":  context_time,
                "context_day":          context_day,
                "context_season":       context_season,
                "context_stress":       context_stress,
                "context_budget":       context_budget,
                "action":               interaction["action"],
                "session_duration_sec": interaction["session_duration"],
                "recommendation_rank":  rank,
                "was_top3":             rank < 3,
                "user_health_match":    round(random.uniform(0.3, 1.0), 2),
                "price_match_score":    round(random.uniform(0.3, 1.0), 2),
                "cuisine_affinity":     round(random.uniform(0.2, 1.0), 2),
                "final_ordered":        interaction["final_ordered"],
            })

        if (i + 1) % chunk_size == 0:
            df = pd.DataFrame(records[-chunk_size * n_shown:])
            mode = 'w' if i + 1 == chunk_size else 'a'
            header = i + 1 == chunk_size
            df.to_csv(output_path, index=False, mode=mode, header=header)
            print(f"  {i+1:,}/{n_interactions:,} sessions written")

    # Write remaining
    remaining_start = (n_interactions // chunk_size) * chunk_size * n_shown
    df = pd.DataFrame(records[remaining_start:])
    df.to_csv(output_path, index=False, mode='a', header=False)
    print(f"  Done → {output_path}")


# ════════════════════════════════════════════════════════════
# 3. LIFE EVENTS
# ════════════════════════════════════════════════════════════

def generate_life_events_csv(users_csv: str = "data/users.csv",
                               output_path: str = "data/life_events.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print("Generating life_events.csv...")

    users_df = pd.read_csv(users_csv)
    records = []
    event_id = 1

    for _, user in users_df.iterrows():
        age = int(user.get("age", 30))
        gender = user.get("gender", "male")
        occupation = user.get("occupation", "office_worker")
        conditions = str(user.get("conditions", "")).split("|")

        for event_type, props in LIFE_EVENT_TYPES.items():
            if props.get("gender_restricted") and props["gender_restricted"] != gender:
                continue

            # Probability varies by user profile
            base_prob = props["probability_per_year"]

            # Adjust probabilities
            if event_type == "health_diagnosis" and len([c for c in conditions if c]) > 1:
                base_prob *= 1.5
            if event_type == "started_gym" and age < 35:
                base_prob *= 1.4
            if event_type == "city_relocation" and occupation == "software_engineer":
                base_prob *= 1.8
            if event_type == "marriage" and 24 <= age <= 35:
                base_prob *= 1.5
            if event_type == "pregnancy" and gender == "female" and 22 <= age <= 38:
                base_prob *= 1.8

            if random.random() < base_prob:
                days_ago = random.randint(30, 365)
                event_date = date.today() - timedelta(days=days_ago)
                transition_range = props["transition_weeks"]
                transition_weeks = random.randint(transition_range[0], transition_range[1])

                # Event details
                detail = ""
                city_from, city_to = "", ""
                triggered_condition = ""

                if event_type == "health_diagnosis":
                    new_conditions = ["type2_diabetes", "hypertension", "high_cholesterol", "pcos", "thyroid"]
                    existing = [c for c in conditions if c]
                    available = [c for c in new_conditions if c not in existing]
                    triggered_condition = random.choice(available) if available else "prediabetes"
                    detail = f"Diagnosed with {triggered_condition}"
                    compliance = round(random.uniform(0.3, 0.9), 2)
                elif event_type == "city_relocation":
                    metros = ["Mumbai", "Bangalore", "Delhi", "Hyderabad", "Chennai", "Pune"]
                    city_from = user.get("birthplace_city", "Patna")
                    city_to = random.choice([c for c in metros if c != city_from])
                    detail = f"Moved from {city_from} to {city_to}"
                    compliance = round(random.uniform(0.4, 0.8), 2)
                elif event_type == "started_gym":
                    detail = "Started gym/fitness routine"
                    compliance = round(random.uniform(0.5, 0.95), 2)
                elif event_type == "marriage":
                    detail = "Got married"
                    compliance = round(random.uniform(0.5, 0.9), 2)
                elif event_type == "financial_stress":
                    detail = "Financial stress period"
                    compliance = round(random.uniform(0.3, 0.7), 2)
                else:
                    detail = event_type.replace("_", " ").title()
                    compliance = round(random.uniform(0.4, 0.8), 2)

                records.append({
                    "event_id":             f"LE{event_id:07d}",
                    "user_id":              user["user_id"],
                    "event_type":           event_type,
                    "event_date":           str(event_date),
                    "event_detail":         detail,
                    "transition_weeks":     transition_weeks,
                    "compliance_level":     compliance,
                    "diet_change_direction":props.get("diet_impact", "moderate"),
                    "triggered_condition":  triggered_condition,
                    "city_moved_from":      city_from,
                    "city_moved_to":        city_to,
                })
                event_id += 1

    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    print(f"  Done. {len(df):,} life events → {output_path}")
    return df


# ════════════════════════════════════════════════════════════
# 4. FAST DAYS
# ════════════════════════════════════════════════════════════

def generate_fast_days_csv(users_csv: str = "data/users.csv",
                             output_path: str = "data/fast_days.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print("Generating fast_days.csv...")

    users_df = pd.read_csv(users_csv)
    records = []
    fast_id = 1

    end_date = date.today()
    start_date = end_date - timedelta(days=365)

    for _, user in users_df.iterrows():
        religion = user.get("religion", "hindu")
        observance = float(user.get("observance_level", 0.4))

        if religion not in FASTING_SCHEDULES:
            continue

        current = start_date
        while current <= end_date:
            day_of_week = current.weekday()
            month = current.month
            day = current.day

            fast_occurred = False
            fast_type = None
            allowed_foods = []
            is_complete_fast = False

            if religion == "hindu":
                # Monday fast
                if day_of_week == 0 and random.random() < 0.18 * observance:
                    fast_occurred = True
                    fast_type = "monday_fast"
                    allowed_foods = ["fruits", "milk", "dahi"]
                    is_complete_fast = random.random() < 0.3

                # Ekadashi (approx 11th and 26th)
                elif day in [11, 26] and random.random() < 0.30 * observance:
                    fast_occurred = True
                    fast_type = "ekadashi"
                    allowed_foods = ["fruits", "sabudana", "milk", "dahi"]
                    is_complete_fast = random.random() < 0.25

                # Navratri (Oct 3-12 approx)
                elif month == 10 and 3 <= day <= 12 and random.random() < 0.45 * observance:
                    fast_occurred = True
                    fast_type = "navratri"
                    allowed_foods = ["sabudana", "kuttu", "fruits", "milk", "dahi", "sendha namak"]
                    is_complete_fast = False

            elif religion == "muslim":
                # Ramadan (simplified: March 12 - April 11)
                if (month == 3 and day >= 12) or (month == 4 and day <= 11):
                    if random.random() < 0.92 * observance:
                        fast_occurred = True
                        fast_type = "ramadan"
                        allowed_foods = ["sehri_before_dawn", "iftar_after_sunset"]
                        is_complete_fast = True

            elif religion == "jain":
                # Paryushan (Aug 31 - Sep 7 approx)
                if month == 8 and day >= 31 or month == 9 and day <= 7:
                    if random.random() < 0.65 * observance:
                        fast_occurred = True
                        fast_type = "paryushan"
                        allowed_foods = ["limited_jain_no_grains"]
                        is_complete_fast = random.random() < 0.4

                # Monthly fast
                elif day == 14 and random.random() < 0.40 * observance:
                    fast_occurred = True
                    fast_type = "jain_monthly"
                    allowed_foods = ["fruits", "milk", "limited"]
                    is_complete_fast = False

            if fast_occurred:
                pre_fast_pool = get_fasting_foods(religion, "during")
                pre_fast_meal = weighted_choice_dict(pre_fast_pool)
                post_fast_pool = get_fasting_foods(religion, "post_fast")
                post_fast_meal = random.choice(post_fast_pool)

                records.append({
                    "fast_id":          f"FD{fast_id:08d}",
                    "user_id":          user["user_id"],
                    "date":             str(current),
                    "fast_type":        fast_type,
                    "religion":         religion,
                    "observance_level": observance,
                    "complete_fast":    is_complete_fast,
                    "allowed_foods":    "|".join(allowed_foods),
                    "pre_fast_meal":    pre_fast_meal,
                    "post_fast_meal":   post_fast_meal,
                    "calorie_impact":   round(random.uniform(-0.6, -0.2) if is_complete_fast else random.uniform(-0.3, -0.1), 2),
                })
                fast_id += 1

            current += timedelta(days=1)

    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    print(f"  Done. {len(df):,} fast days → {output_path}")
    return df


# ════════════════════════════════════════════════════════════
# 5. SKIP EVENTS
# ════════════════════════════════════════════════════════════

def generate_skip_events_csv(users_csv: str = "data/users.csv",
                               meal_logs_csv: str = "data/meal_logs.csv",
                               output_path: str = "data/skip_events.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print("Generating skip_events.csv...")

    users_df = pd.read_csv(users_csv)
    meals_df = pd.read_csv(meal_logs_csv, parse_dates=["occurred_at"])

    skip_reasons = {
        "breakfast": ["running_late", "not_hungry", "meeting", "fasting", "forgot"],
        "lunch":     ["busy_at_work", "meeting", "not_hungry", "diet", "no_food_available"],
        "dinner":    ["tired", "not_hungry", "fasting", "ill"],
    }

    records = []
    skip_id = 1

    for _, user in users_df.iterrows():
        uid = user["user_id"]
        occupation = user.get("occupation", "office_worker")
        user_meals = meals_df[meals_df["user_id"] == uid]
        if len(user_meals) == 0:
            continue

        # Generate skip events based on skip probabilities
        user_meals_sorted = user_meals.sort_values("occurred_at")
        dates_with_meals = user_meals_sorted["occurred_at"].dt.date.unique()

        for dt in dates_with_meals:
            day_meals = user_meals_sorted[user_meals_sorted["occurred_at"].dt.date == dt]
            occasions_logged = day_meals["meal_occasion"].tolist()

            for occasion in ["breakfast", "lunch", "dinner"]:
                if occasion not in occasions_logged:
                    # This was a skip
                    skip_prob_map = {
                        "breakfast": 0.20, "lunch": 0.08, "dinner": 0.03
                    }
                    if random.random() < skip_prob_map.get(occasion, 0.10):
                        reason = random.choice(skip_reasons.get(occasion, ["unknown"]))
                        compensatory = occasion == "breakfast" and "lunch" in occasions_logged

                        if compensatory:
                            comp_meals = day_meals[day_meals["meal_occasion"] == "lunch"]
                            comp_calories = comp_meals["estimated_calories"].sum() if len(comp_meals) > 0 else 0
                            normal_calories = 350
                            cal_increase = round((comp_calories - normal_calories) / normal_calories, 2) if normal_calories > 0 else 0
                        else:
                            cal_increase = 0

                        records.append({
                            "skip_id":                      f"SK{skip_id:08d}",
                            "user_id":                      uid,
                            "skipped_meal_occasion":        occasion,
                            "skip_date":                    str(dt),
                            "skip_reason":                  reason,
                            "compensatory_meal_occurred":   compensatory,
                            "compensatory_meal_occasion":   "lunch" if compensatory else "",
                            "compensatory_calorie_increase":cal_increase,
                        })
                        skip_id += 1

    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    print(f"  Done. {len(df):,} skip events → {output_path}")
    return df


# ════════════════════════════════════════════════════════════
# 6. REORDER EVENTS
# ════════════════════════════════════════════════════════════

def generate_reorder_events_csv(meal_logs_csv: str = "data/meal_logs.csv",
                                  output_path: str = "data/reorder_events.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print("Generating reorder_events.csv...")

    meals_df = pd.read_csv(meal_logs_csv, parse_dates=["occurred_at"])
    ordered_meals = meals_df[meals_df["ordered_delivery"] == True] if "ordered_delivery" in meals_df.columns else meals_df

    records = []
    reorder_id = 1

    for uid, user_meals in ordered_meals.groupby("user_id"):
        user_meals_sorted = user_meals.sort_values("occurred_at")

        dish_first_order = {}
        dish_order_count = {}

        for _, meal in user_meals_sorted.iterrows():
            dish = meal["dish_name"]
            occurred = meal["occurred_at"]

            if dish not in dish_first_order:
                dish_first_order[dish] = occurred
                dish_order_count[dish] = 1
            else:
                dish_order_count[dish] += 1
                days_between = (occurred - dish_first_order[dish]).days
                total_orders = dish_order_count[dish]

                # Simulate rating proxy
                rating_proxy = round(random.uniform(3.0, 5.0), 1)
                if total_orders > 5:
                    rating_proxy = round(min(5.0, rating_proxy + 0.3), 1)

                # Reorder probability (was it actually reordered again?)
                reorder_again_prob = min(0.9, 0.3 + total_orders * 0.08)
                reorder_trigger = random.choice(["habit", "craving", "convenience", "festival", "stress"])

                records.append({
                    "reorder_id":           f"RO{reorder_id:08d}",
                    "user_id":              uid,
                    "dish_name":            dish,
                    "first_order_date":     str(dish_first_order[dish].date()),
                    "reorder_date":         str(occurred.date()),
                    "days_between":         days_between,
                    "total_orders_dish":    total_orders,
                    "last_rating_proxy":    rating_proxy,
                    "reordered_yes_no":     random.random() < reorder_again_prob,
                    "trigger_type":         reorder_trigger,
                })
                reorder_id += 1

    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    print(f"  Done. {len(df):,} reorder events → {output_path}")
    return df


# ════════════════════════════════════════════════════════════
# 7. HEALTH OUTCOMES
# ════════════════════════════════════════════════════════════

def generate_health_outcomes_csv(users_csv: str = "data/users.csv",
                                   meal_logs_csv: str = "data/meal_logs.csv",
                                   output_path: str = "data/health_outcomes.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print("Generating health_outcomes.csv...")

    users_df = pd.read_csv(users_csv)
    meals_df = pd.read_csv(meal_logs_csv, parse_dates=["occurred_at"])
    meals_df["quarter"] = meals_df["occurred_at"].dt.quarter
    meals_df["year"] = meals_df["occurred_at"].dt.year

    records = []
    outcome_id = 1

    for _, user in users_df.iterrows():
        uid = user["user_id"]
        conditions = str(user.get("conditions", "")).split("|")
        bmi = float(user.get("bmi", 23.0))
        health_literacy = float(user.get("health_literacy", 0.5))

        user_meals = meals_df[meals_df["user_id"] == uid]
        if len(user_meals) == 0:
            continue
        prev_compliance_by_user = {}
        for (year, quarter), q_meals in user_meals.groupby(["year", "quarter"]):
            avg_cal = q_meals["estimated_calories"].mean() if "estimated_calories" in q_meals.columns else 300
            avg_gi = q_meals["gi_score"].mean() if "gi_score" in q_meals.columns else 55
            avg_protein = q_meals["estimated_protein_g"].mean() if "estimated_protein_g" in q_meals.columns else 15
            avg_fiber = q_meals["estimated_fiber_g"].mean() if "estimated_fiber_g" in q_meals.columns else 5
            avg_sodium = random.uniform(800, 2200)
            compliance = q_meals["health_compliant"].mean() if "health_compliant" in q_meals.columns else 0.6
            uid = user["user_id"]
            prev = prev_compliance_by_user.get(uid, None)
            compliance_improvement = compute_compliance_improvement(float(compliance), prev)
            prev_compliance_by_user[uid] = float(compliance)

            # BMI change based on caloric intake
            from constants import compute_bmi_change
            n_meals = len(q_meals)
            quarter_days = 90
            meals_per_day = n_meals / quarter_days
            bmi_change = compute_bmi_change(
            avg_calories_per_meal=float(avg_cal),
            meals_per_day=meals_per_day,
            height_cm=float(user.get("height_cm", 165)),
            fitness_goal=str(user.get("fitness_goal", "maintain")),
            activity_level=str(user.get("activity_level", "lightly_active")),
            quarter_days=quarter_days,
            )
            bmi = round(max(14.0, min(50.0, bmi + bmi_change)), 1)
            # Condition severity change
            severity_change = 0.0
            if "type2_diabetes" in conditions:
                if avg_gi < 50 and compliance > 0.7:
                    severity_change = round(random.uniform(-0.2, 0.0), 2)
                else:
                    severity_change = round(random.uniform(0.0, 0.15), 2)

            # Nutritional gap score
            gap_score = 0
            if avg_protein < 15:
                gap_score += 2
            if avg_fiber < 5:
                gap_score += 1
            if avg_gi > 65:
                gap_score += 2

            health_trend = "improving" if severity_change < 0 and compliance > 0.65 else \
                          "stable" if abs(severity_change) < 0.05 else "declining"

            records.append({
                "outcome_id":               f"HO{outcome_id:08d}",
                "user_id":                  uid,
                "quarter":                  quarter,
                "year":                     year,
                "avg_daily_calories":       round(float(avg_cal), 1),
                "avg_gi":                   round(float(avg_gi), 1),
                "avg_protein_g":            round(float(avg_protein), 1),
                "avg_fiber_g":              round(float(avg_fiber), 1),
                "avg_sodium_mg":            round(float(avg_sodium), 1),
                "bmi_change":               bmi_change,
                "current_bmi":              bmi,
                "condition_severity_change":severity_change,
                "nutritional_gap_score":    gap_score,
                "health_trend":             health_trend,
                "compliance_rate":          round(float(compliance), 3),
                "compliance_improvement": compliance_improvement,
            })
            outcome_id += 1

    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    print(f"  Done. {len(df):,} health outcomes → {output_path}")
    return df


# ════════════════════════════════════════════════════════════
# 8. SOCIAL EATING CONTEXT
# ════════════════════════════════════════════════════════════

def generate_social_context_csv(meal_logs_csv="data/meal_logs.csv",
                                  users_csv="data/users.csv",
                                  output_path="data/social_eating_context.csv"):
    users_df = pd.read_csv(users_csv, usecols=["user_id","living_situation"])
    living_map = dict(zip(users_df["user_id"], users_df["living_situation"]))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    print("Generating social_eating_context.csv...")

    meals_df = pd.read_csv(meal_logs_csv)
    records = []

    group_sizes = {
        "alone": 1, "with_family": random.randint(2, 6),
        "with_colleagues": random.randint(2, 8),
        "with_friends": random.randint(2, 6),
        "at_restaurant": random.randint(2, 8),
        "with_spouse": 2,
    }

    relationship_types = {
        "alone": "self", "with_family": "family",
        "with_colleagues": "professional", "with_friends": "social",
        "at_restaurant": "social", "with_spouse": "intimate",
    }

    location_types = {
        "alone": ["home", "office_desk", "hostel"],
        "with_family": ["home", "family_restaurant"],
        "with_colleagues": ["office_canteen", "nearby_restaurant"],
        "with_friends": ["restaurant", "street_food", "cafe"],
        "at_restaurant": ["restaurant", "fine_dining", "dhaba"],
        "with_spouse": ["home", "restaurant"],
    }

    duration_map = {
        "alone": (10, 25), "with_family": (20, 45),
        "with_colleagues": (20, 40), "with_friends": (30, 90),
        "at_restaurant": (45, 120), "with_spouse": (20, 50),
    }

    budget_multipliers = {
        "alone": 0.90, "with_family": 1.00, "with_colleagues": 0.95,
        "with_friends": 1.20, "at_restaurant": 1.40, "with_spouse": 1.15,
    }

    chunk_size = 100000
    for i, (_, meal) in enumerate(meals_df.iterrows()):
        social = meal.get("social_context", "alone")
        uid = meal.get("user_id", "")
        living = living_map.get(uid, "with_family")
        if social == "alone":
            if living in ["hostel_pg"]:
                loc_options = ["hostel", "home", "office_desk"]
            elif living in ["with_roommates"]:
                loc_options = ["home", "office_desk", "nearby_restaurant"]
            else:
                loc_options = ["home", "office_desk"]
        else:
            loc_options = location_types.get(social, ["home"])
        group_size = group_sizes.get(social, 1)
        if callable(group_size):
            group_size = group_size()
        elif isinstance(group_size, int):
            pass
        else:
            group_size = 1

        # Recalculate group size with randomness
        if social == "with_family":
            group_size = random.randint(2, 6)
        elif social == "with_colleagues":
            group_size = random.randint(2, 8)
        elif social == "with_friends":
            group_size = random.randint(2, 6)

        loc_options = location_types.get(social, ["home"])
        duration_range = duration_map.get(social, (15, 30))

        records.append({
            "meal_id":              meal.get("meal_id", f"ML{i:08d}"),
            "user_id":              meal.get("user_id", ""),
            "social_context":       social,
            "group_size":           group_size,
            "relationship_type":    relationship_types.get(social, "self"),
            "location_type":        random.choice(loc_options),
            "meal_duration_min":    random.randint(duration_range[0], duration_range[1]),
            "budget_multiplier":    budget_multipliers.get(social, 1.0),
            "variety_score":        round(random.uniform(0.2, 1.0) if social != "alone" else random.uniform(0.1, 0.5), 2),
            "outside_comfort_zone": random.random() < (0.25 if social in ["with_friends", "at_restaurant"] else 0.08),
            "influenced_by_group":  social not in ["alone"] and random.random() < 0.45,
        })

        if (i + 1) % chunk_size == 0:
            df = pd.DataFrame(records[-chunk_size:])
            mode = 'w' if i + 1 == chunk_size else 'a'
            header = i + 1 == chunk_size
            df.to_csv(output_path, index=False, mode=mode, header=header)
            print(f"  {i+1:,} social context rows written")

    # Write remaining
    df = pd.DataFrame(records[-(len(records) % chunk_size or chunk_size):])
    df.to_csv(output_path, index=False, mode='a', header=False)
    print(f"  Done → {output_path}")


# ════════════════════════════════════════════════════════════
# RUN ALL
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--weekly", action="store_true")
    parser.add_argument("--interactions", action="store_true")
    parser.add_argument("--life_events", action="store_true")
    parser.add_argument("--fast_days", action="store_true")
    parser.add_argument("--skip_events", action="store_true")
    parser.add_argument("--reorders", action="store_true")
    parser.add_argument("--health_outcomes", action="store_true")
    parser.add_argument("--social", action="store_true")
    args = parser.parse_args()

    if args.all or args.weekly:
        generate_weekly_context_csv()
    if args.all or args.interactions:
        generate_interactions_csv()
    if args.all or args.life_events:
        generate_life_events_csv()
    if args.all or args.fast_days:
        generate_fast_days_csv()
    if args.all or args.skip_events:
        generate_skip_events_csv()
    if args.all or args.reorders:
        generate_reorder_events_csv()
    if args.all or args.health_outcomes:
        generate_health_outcomes_csv()
    if args.all or args.social:
        generate_social_context_csv()