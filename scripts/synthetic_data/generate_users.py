"""
NARA Synthetic Data Generator — User Generator
Generates users.csv with 50,000 synthetic Indian users
Hierarchical sampling from real distributions in constants.py
"""
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from constants import (
    STATE_POPULATION_WEIGHTS, STATE_REGION, STATE_CITIES,
    STATE_RELIGION_DIST, STATE_MOTHER_TONGUE, AGE_DISTRIBUTION,
    GENDER_DISTRIBUTION, STATE_URBAN_RATIO, OCCUPATION_TYPES,
    OCCUPATION_BY_AGE, INCOME_TIERS, LIVING_SITUATIONS,
    LIVING_BY_AGE_OCCUPATION, CONDITION_PREVALENCE_BY_AGE_GENDER,
    RELIGION_DIETARY_CONSTRAINTS, PERSONAS,
)
from constants import get_fasting_foods
random.seed(42)
np.random.seed(42)


def weighted_choice(choices: dict) -> str:
    keys = list(choices.keys())
    weights = list(choices.values())
    total = sum(weights)
    weights = [w / total for w in weights]
    return keys[np.random.choice(len(keys), p=weights)]


def get_age_bucket(age: int) -> tuple:
    for bucket in AGE_DISTRIBUTION.keys():
        if bucket[0] <= age <= bucket[1]:
            return bucket
    return (26, 35)


def sample_age() -> int:
    bucket = weighted_choice(AGE_DISTRIBUTION)
    return random.randint(bucket[0], bucket[1])


def sample_birthplace() -> tuple:
    state = weighted_choice(STATE_POPULATION_WEIGHTS)
    cities = STATE_CITIES.get(state, [("Unknown", 3)])
    city, tier = random.choice(cities)
    return state, city, tier


def sample_current_location(birthplace_state: str, age: int, occupation: str) -> tuple:
    # Migration probability increases with education/income occupation
    migration_prob = {
        "software_engineer": 0.55,
        "office_worker": 0.25,
        "student": 0.35,
        "homemaker": 0.10,
        "business_owner": 0.20,
        "field_worker": 0.08,
        "healthcare_worker": 0.20,
        "teacher": 0.12,
        "driver": 0.15,
        "daily_wage_worker": 0.12,
        "retired": 0.05,
        "freelancer": 0.30,
    }
    migrated = random.random() < migration_prob.get(occupation, 0.15)
    if migrated:
        # Move to metro cities with higher probability
        metro_states = ["Maharashtra", "Karnataka", "Delhi", "Tamil Nadu",
                       "Telangana", "Gujarat", "West Bengal"]
        current_state = random.choice(metro_states)
    else:
        current_state = birthplace_state

    cities = STATE_CITIES.get(current_state, [("Unknown", 3)])
    # Migrants prefer tier 1 cities
    if migrated:
        tier1 = [(c, t) for c, t in cities if t == 1]
        if tier1:
            city, tier = random.choice(tier1)
        else:
            city, tier = random.choice(cities)
    else:
        city, tier = random.choice(cities)

    return current_state, city, tier


def sample_religion(state: str) -> str:
    dist = STATE_RELIGION_DIST.get(state, {"hindu": 0.80, "muslim": 0.14, "christian": 0.04, "other": 0.02})
    return weighted_choice(dist)


def sample_occupation(age: int) -> str:
    bucket = get_age_bucket(age)
    dist = OCCUPATION_BY_AGE.get(bucket, OCCUPATION_BY_AGE[(26, 35)])
    return weighted_choice(dist)


def sample_health_conditions(age: int, gender: str, religion: str, region: str) -> list:
    conditions = []
    bucket = get_age_bucket(age)
    g = gender if gender in ["male", "female"] else "male"

    # South India has higher diabetes prevalence
    diabetes_multiplier = 1.3 if region == "south" else 1.0
    # North India higher hypertension
    hypertension_multiplier = 1.2 if region == "north" else 1.0

    for condition, age_gender_dist in CONDITION_PREVALENCE_BY_AGE_GENDER.items():
        if bucket not in age_gender_dist:
            continue
        base_prob = age_gender_dist[bucket].get(g, 0.0)

        if condition == "type2_diabetes":
            base_prob *= diabetes_multiplier
        elif condition == "hypertension":
            base_prob *= hypertension_multiplier

        # Jains have lower diabetes due to vegetarian diet
        if religion == "jain" and condition in ["type2_diabetes", "obesity"]:
            base_prob *= 0.75

        if random.random() < base_prob:
            conditions.append(condition)

    # Realistic co-morbidity: diabetes + hypertension often together
    if "type2_diabetes" in conditions and random.random() < 0.45:
        if "hypertension" not in conditions:
            conditions.append("hypertension")

    # Obesity + diabetes correlation
    if "obesity" in conditions:
        if (
        "type2_diabetes" not in conditions
        and random.random() < 0.30
        ):
            conditions.append("type2_diabetes")
        elif (
        "prediabetes" not in conditions
        and random.random() < 0.50
        ):
            conditions.append("prediabetes")

    return conditions


def sample_dietary_restrictions(religion: str, conditions: list, is_vegetarian: bool) -> list:
    restrictions = []
    religion_constraints = RELIGION_DIETARY_CONSTRAINTS.get(religion, {})

    if is_vegetarian:
        restrictions.append("vegetarian")

    if religion == "jain":
        if random.random() < religion_constraints.get("no_root_vegetables_prob", 0.75):
            restrictions.append("no_root_vegetables")
        if random.random() < religion_constraints.get("no_onion_garlic_prob", 0.85):
            restrictions.append("no_onion_garlic")
        restrictions.append("jain")

    if religion == "muslim":
        restrictions.append("halal")

    if religion == "hindu":
        if random.random() < religion_constraints.get("no_beef_prob", 0.82):
            restrictions.append("no_beef")

    # Health condition based restrictions
    if "lactose_intolerance" in conditions:
        restrictions.append("no_dairy")
    if "gluten_intolerance" in conditions:
        restrictions.append("no_gluten")
    if "hypertension" in conditions and random.random() < 0.55:
        restrictions.append("low_sodium")
    if "type2_diabetes" in conditions and random.random() < 0.65:
        restrictions.append("low_gi")
    if "ibs" in conditions and random.random() < 0.50:
        restrictions.append("low_fiber_trigger")

    return list(set(restrictions))


def sample_bmi(age: int, gender: str, conditions: list, region: str) -> float:
    # Base BMI by age and gender (NFHS-5 data)
    base_means = {
        "male":   {(18,25): 21.5, (26,35): 23.2, (36,45): 24.8, (46,55): 25.2, (56,65): 25.0, (66,80): 24.2},
        "female": {(18,25): 21.8, (26,35): 23.8, (36,45): 25.5, (46,55): 26.2, (56,65): 25.8, (66,80): 24.5},
    }
    bucket = get_age_bucket(age)
    g = gender if gender in ["male", "female"] else "male"
    base_mean = base_means[g].get(bucket, 23.0)

    # Urban adds ~0.8 BMI on average
    if region in ["south", "west"]:
        base_mean += 0.5

    # Obesity condition → higher BMI
    if "obesity" in conditions:
        base_mean = max(base_mean, 30.0) + random.uniform(0, 5)
    
    bmi = np.random.normal(base_mean, 2.5)
    return round(max(15.0, min(45.0, bmi)), 1)


def sample_cooking_skill(occupation: str, living_situation: str,
                          age: int, gender: str) -> float:
    base_skills = {
        "homemaker": 0.90, "retired": 0.75, "teacher": 0.65,
        "office_worker": 0.55, "healthcare_worker": 0.55,
        "software_engineer": 0.45, "freelancer": 0.50,
        "business_owner": 0.55, "field_worker": 0.40,
        "student": 0.25, "driver": 0.35, "daily_wage_worker": 0.50,
    }
    skill = base_skills.get(occupation, 0.50)

    # Living alone reduces cooking skill slightly
    if living_situation in ["alone", "hostel_pg"]:
        skill *= 0.75
    elif living_situation == "with_family":
        skill *= 1.10

    # Older people tend to cook more
    if age > 45:
        skill = min(0.95, skill * 1.15)

    # Women historically cook more in India (realistic not prescriptive)
    if gender == "female":
        skill = min(0.95, skill * 1.12)

    return round(min(0.98, max(0.05, skill + np.random.normal(0, 0.08))), 2)


def sample_health_literacy(occupation: str, age: int,
                            city_tier: int, conditions: list) -> float:
    base = {
        "software_engineer": 0.72, "healthcare_worker": 0.88,
        "teacher": 0.68, "office_worker": 0.58, "freelancer": 0.62,
        "business_owner": 0.55, "homemaker": 0.50, "student": 0.55,
        "field_worker": 0.28, "driver": 0.30, "daily_wage_worker": 0.25,
        "retired": 0.48,
    }
    literacy = base.get(occupation, 0.50)

    # City tier effect
    if city_tier == 1:
        literacy += 0.10
    elif city_tier == 3:
        literacy -= 0.12

    # Having a health condition increases awareness
    if len(conditions) > 0:
        literacy = min(0.95, literacy + 0.10)
    if "type2_diabetes" in conditions:
        literacy = min(0.95, literacy + 0.08)

    # Younger people more health aware (millennial/gen-z effect)
    if 18 <= age <= 35:
        literacy += 0.05

    return round(min(0.98, max(0.05, literacy + np.random.normal(0, 0.06))), 2)


def generate_user(user_id: int, persona_name: str = None) -> dict:
    # ── Persona assignment ────────────────────────────────────
    if persona_name is None:
        # 60% follow a persona, 40% are fully random
        if random.random() < 0.60:
            persona_name = random.choice(list(PERSONAS.keys()))
        
    persona = PERSONAS.get(persona_name, {}) if persona_name else {}

    # ── Step 1: Birthplace ────────────────────────────────────
    birthplace_state, birthplace_city, birthplace_tier = sample_birthplace()
    region = STATE_REGION.get(birthplace_state, "north")

    # ── Step 2: Age and Gender ────────────────────────────────
    if persona:
        age_range = persona.get("age_range", (18, 65))
        age = random.randint(age_range[0], age_range[1])
    else:
        age = sample_age()

    forced_gender = persona.get("forced_gender")
    if forced_gender:
        gender = forced_gender
    else:
        gender = weighted_choice(GENDER_DISTRIBUTION)

    # ── Step 3: Religion ──────────────────────────────────────
    forced_religion = persona.get("forced_religion")
    if forced_religion:
        religion = forced_religion
    else:
        religion = sample_religion(birthplace_state)

    # ── Step 4: Occupation ────────────────────────────────────
    if persona:
        occupation = persona.get("occupation", sample_occupation(age))
    else:
        occupation = sample_occupation(age)

    # ── Step 5: Current location ──────────────────────────────
    current_state, current_city, current_city_tier = sample_current_location(
        birthplace_state, age, occupation
    )

    # ── Step 6: Income tier ───────────────────────────────────
    if persona:
        income_tier = persona.get("income_tier", "medium")
    else:
        occ_info = OCCUPATION_TYPES.get(occupation, {})
        income_tier = occ_info.get("income_tier", "medium")
        # Add some variance
        if random.random() < 0.15:
            income_tier = random.choice(["low", "medium", "high"])

    # ── Step 7: Living situation ──────────────────────────────
    living_dist = LIVING_BY_AGE_OCCUPATION.get(
        occupation,
        {"with_family": 0.50, "alone": 0.25, "with_spouse": 0.25}
    )
    living_situation = weighted_choice(living_dist)

    # ── Step 8: Family size ───────────────────────────────────
    family_size_map = {
        "alone": 1, "hostel_pg": 1,
        "with_spouse": random.randint(2, 4),
        "with_family": random.randint(3, 7),
        "with_roommates": random.randint(2, 4),
    }
    family_size = family_size_map.get(living_situation, 2)

    # ── Step 9: Health conditions ─────────────────────────────
    forced_conditions = persona.get("forced_conditions", [])
    conditions = sample_health_conditions(age, gender, religion, region)
    for fc in forced_conditions:
        if fc not in conditions:
            conditions.append(fc)

    # ── Step 10: Vegetarian status ────────────────────────────
    religion_constraints = RELIGION_DIETARY_CONSTRAINTS.get(religion, {})
    is_vegetarian = random.random() < religion_constraints.get("vegetarian_prob", 0.28)

    # ── Step 11: Dietary restrictions ────────────────────────
    dietary_restrictions = sample_dietary_restrictions(religion, conditions, is_vegetarian)

    # ── Step 12: Physical stats ───────────────────────────────  bmi logic fix with hard constraints
    bmi = sample_bmi(age, gender, conditions, region)
    if bmi >= 35:
        if "type2_diabetes" not in conditions and random.random() < 0.40:
            conditions.append("type2_diabetes")
        if "hypertension" not in conditions and random.random() < 0.45:
            conditions.append("hypertension")
        if "high_cholesterol" not in conditions and random.random() < 0.35:
            conditions.append("high_cholesterol")
    elif bmi >= 30:
        if "type2_diabetes" not in conditions and random.random() < 0.25:
            conditions.append("type2_diabetes") 

        if "hypertension" not in conditions and random.random() < 0.30:
            conditions.append("hypertension")

        if "high_cholesterol" not in conditions and random.random() < 0.20:
            conditions.append("high_cholesterol")
    elif bmi >= 27:
        if "prediabetes" not in conditions and random.random() < 0.20:
            conditions.append("prediabetes")
    height_cm = round(np.random.normal(
        165 if gender == "female" else 172,
        6.5 if gender == "female" else 7.0
    ), 1)
    weight_kg = round(bmi * (height_cm / 100) ** 2, 1)

    # ── Step 13: Cooking skill ────────────────────────────────
    cooking_skill = sample_cooking_skill(occupation, living_situation, age, gender)

    # ── Step 14: Health literacy ──────────────────────────────
    health_literacy = sample_health_literacy(occupation, age, current_city_tier, conditions)

    # ── Step 15: Personality traits ───────────────────────────
    if persona:
        habit_strength = persona.get("habit_strength", 0.60) + np.random.normal(0, 0.08)
        stress_profile = persona.get("stress_profile", "medium")
        trend_susceptibility = persona.get("trend_susceptibility", 0.35) + np.random.normal(0, 0.08)
    else:
        habit_strength = round(np.random.beta(4, 2), 2)  # skewed toward habit
        stress_profiles = ["low", "medium", "high"]
        occ_stress = OCCUPATION_TYPES.get(occupation, {}).get("stress", "medium")
        stress_probs = {"low": [0.5, 0.3, 0.2], "medium": [0.2, 0.5, 0.3], "high": [0.1, 0.3, 0.6]}
        stress_profile = np.random.choice(stress_profiles, p=stress_probs[occ_stress])
        trend_susceptibility = round(np.random.beta(2, 3) if age > 35 else np.random.beta(3, 2), 2)

    habit_strength = round(min(0.98, max(0.10, habit_strength)), 2)
    trend_susceptibility = round(min(0.98, max(0.02, trend_susceptibility)), 2)

    # ── Step 16: Commute and WFH ──────────────────────────────
    occ_info = OCCUPATION_TYPES.get(occupation, {"commute": (30, 60), "wfh_prob": 0.2})
    commute_range = occ_info.get("commute", (30, 60))
    commute_minutes = random.randint(commute_range[0], commute_range[1])
    wfh_prob = occ_info.get("wfh_prob", 0.2)
    is_wfh = random.random() < wfh_prob

    # ── Step 17: Order frequency ──────────────────────────────
    if persona:
        base_order_freq = persona.get("order_frequency_weekly", 2.5)
    else:
        living_order = LIVING_SITUATIONS.get(living_situation, {})
        base_order_freq = living_order.get("order_prob", 0.3) * 7
    order_frequency_weekly = round(
        max(0.1, base_order_freq + np.random.normal(0, 0.8)), 1
    )

    # ── Step 18: Fitness goal ─────────────────────────────────
    fitness_goals = ["lose_weight", "maintain", "gain_muscle", "manage_condition", "general_health"]
    if "obesity" in conditions or "type2_diabetes" in conditions:
        fitness_goal = np.random.choice(["lose_weight", "manage_condition"], p=[0.5, 0.5])
    elif age < 30 and gender == "male":
        fitness_goal = np.random.choice(fitness_goals, p=[0.15, 0.25, 0.40, 0.05, 0.15])
    else:
        fitness_goal = np.random.choice(fitness_goals, p=[0.30, 0.30, 0.15, 0.10, 0.15])

    # ── Step 19: Activity level ───────────────────────────────
    activity_levels = ["sedentary", "lightly_active", "moderately_active", "very_active"]
    if occupation in ["field_worker", "daily_wage_worker", "driver"]:
        activity = np.random.choice(activity_levels, p=[0.05, 0.15, 0.40, 0.40])
    elif occupation in ["software_engineer", "office_worker", "retired"]:
        activity = np.random.choice(activity_levels, p=[0.35, 0.40, 0.18, 0.07])
    else:
        activity = np.random.choice(activity_levels, p=[0.20, 0.35, 0.30, 0.15])

    # ── Step 20: Sleep hours ──────────────────────────────────
    stress_sleep = {"low": (7.5, 0.8), "medium": (6.8, 0.9), "high": (6.0, 1.0), "extreme": (5.5, 1.2)}
    sleep_mean, sleep_std = stress_sleep.get(stress_profile, (7.0, 0.9))
    sleep_hours = round(min(10, max(4, np.random.normal(sleep_mean, sleep_std))), 1)

    # ── Step 21: Payment date ─────────────────────────────────
    payment_dates = [1, 5, 7, 10, 15, 25, 30]
    payment_date = random.choice(payment_dates)

    # ── Step 22: Mother tongue ────────────────────────────────
    tongues = STATE_MOTHER_TONGUE.get(birthplace_state, ["Hindi"])
    mother_tongue = random.choice(tongues)

    # ── Step 23: Allergies ────────────────────────────────────
    common_allergens = ["peanuts", "shellfish", "tree_nuts", "eggs", "fish", "milk", "gluten", "mustard"]
    allergen_probs = [0.05, 0.03, 0.04, 0.02, 0.03, 0.04, 0.02, 0.02]
    allergies = [a for a, p in zip(common_allergens, allergen_probs) if random.random() < p]
    # Remove allergens already covered by intolerances
    if "lactose_intolerance" in conditions and "milk" not in allergies:
        pass  # covered by restriction

    # ── Step 24: Nutritional goals ────────────────────────────
    nutritional_goals = {}
    if fitness_goal == "gain_muscle":
        nutritional_goals["protein_g_daily"] = random.randint(120, 180)
    elif fitness_goal == "lose_weight":
        nutritional_goals["calories_daily"] = random.randint(1500, 1800)
    elif fitness_goal == "manage_condition":
        if "type2_diabetes" in conditions:
            nutritional_goals["gi_max"] = 55
            nutritional_goals["carbs_g_daily"] = random.randint(150, 200)
        if "hypertension" in conditions:
            nutritional_goals["sodium_mg_daily"] = random.randint(1500, 2000)

    # ── Step 25: Cuisine preferences ─────────────────────────
    region_affinity = {
        "south": {"south_indian": 0.75, "biryani": 0.55, "north_indian": 0.35},
        "north": {"north_indian": 0.75, "street_food": 0.65, "biryani": 0.50},
        "west":  {"gujarati": 0.60, "maharashtrian": 0.55, "north_indian": 0.45},
        "east":  {"bengali": 0.70, "north_indian": 0.40, "biryani": 0.45},
        "northeast": {"northeast": 0.70, "chinese": 0.55},
    }
    cuisine_prefs = region_affinity.get(region, {"north_indian": 0.60})
    # Add variance
    cuisine_prefs = {k: round(min(1.0, v + np.random.normal(0, 0.1)), 2)
                    for k, v in cuisine_prefs.items()}

    # ── Step 26: Created at (registration date) ───────────────
    days_ago = random.randint(30, 730)
    created_at = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

    return {
        "user_id":                  f"SU{user_id:06d}",
        "age":                      age,
        "gender":                   gender,
        "birthplace_state":         birthplace_state,
        "birthplace_city":          birthplace_city,
        "birthplace_tier":          birthplace_tier,
        "current_state":            current_state,
        "current_city":             current_city,
        "current_city_tier":        current_city_tier,
        "region":                   region,
        "religion":                 religion,
        "observance_level":         round(np.random.beta(2, 3), 2),
        "mother_tongue":            mother_tongue,
        "occupation":               occupation,
        "income_tier":              income_tier,
        "payment_date":             payment_date,
        "living_situation":         living_situation,
        "family_size":              family_size,
        "cooking_skill":            cooking_skill,
        "commute_minutes":          commute_minutes,
        "is_wfh":                   is_wfh,
        "stress_profile":           stress_profile,
        "health_literacy":          health_literacy,
        "habit_strength":           habit_strength,
        "trend_susceptibility":     trend_susceptibility,
        "is_vegetarian":            is_vegetarian,
        "is_vegan":                 is_vegetarian and random.random() < 0.05,
        "is_jain":                  religion == "jain",
        "is_halal":                 religion == "muslim",
        "dietary_restrictions":     "|".join(dietary_restrictions),
        "conditions":               "|".join(conditions),
        "family_history":           "|".join(random.sample(
                                        ["diabetes", "hypertension", "heart_disease", "cancer", "none"],
                                        k=random.randint(0, 2)
                                    )),
        "allergies":                "|".join(allergies),
        "bmi":                      bmi,
        "weight_kg":                weight_kg,
        "height_cm":                height_cm,
        "activity_level":           activity,
        "sleep_hours":              sleep_hours,
        "fitness_goal":             fitness_goal,
        "nutritional_goals":        str(nutritional_goals),
        "cuisine_preferences":      str(cuisine_prefs),
        "order_frequency_weekly":   order_frequency_weekly,
        "persona_type":             persona_name or "random",
        "created_at":               created_at,
    }


def generate_users_csv(n_users: int = 50000, output_path: str = "data/users.csv",
                        chunk_size: int = 5000):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Persona distribution — ensures diversity
    persona_names = list(PERSONAS.keys())
    persona_assigned = []
    # 60% get a persona, distributed evenly across 12 personas
    for i in range(n_users):
        if random.random() < 0.60:
            persona_assigned.append(persona_names[i % len(persona_names)])
        else:
            persona_assigned.append(None)
    random.shuffle(persona_assigned)

    print(f"Generating {n_users:,} synthetic users...")
    print(f"Output: {output_path}")

    all_users = []
    for i in range(n_users):
        user = generate_user(i + 1, persona_assigned[i])
        all_users.append(user)

        if (i + 1) % chunk_size == 0:
            pct = (i + 1) / n_users * 100
            print(f"  {i+1:,}/{n_users:,} users generated ({pct:.0f}%)")

            # Write in chunks to avoid memory issues
            if i + 1 == chunk_size:
                df = pd.DataFrame(all_users)
                df.to_csv(output_path, index=False, mode='w')
            else:
                df = pd.DataFrame(all_users[-chunk_size:])
                df.to_csv(output_path, index=False, mode='a', header=False)
            all_users = all_users[-chunk_size:]  # keep only last chunk in memory

    # Write remaining
    remaining = all_users[-(n_users % chunk_size or chunk_size):]
    if remaining:
        df = pd.DataFrame(remaining)
        df.to_csv(output_path, index=False,
                  mode='a' if n_users > chunk_size else 'w',
                  header=n_users <= chunk_size)

    print(f"\nDone. {n_users:,} users written to {output_path}")

    # Print distribution summary
    df_full = pd.read_csv(output_path)
    print(f"\nDistribution Summary:")
    print(f"  Gender:      {df_full['gender'].value_counts().to_dict()}")
    print(f"  Income tier: {df_full['income_tier'].value_counts().to_dict()}")
    print(f"  Region:      {df_full['region'].value_counts().to_dict()}")
    print(f"  Religion:    {df_full['religion'].value_counts().to_dict()}")
    print(f"  Vegetarian:  {df_full['is_vegetarian'].sum():,} ({df_full['is_vegetarian'].mean()*100:.1f}%)")
    print(f"  Avg age:     {df_full['age'].mean():.1f}")
    print(f"  Avg BMI:     {df_full['bmi'].mean():.1f}")
    conditions_flat = df_full['conditions'].dropna().str.split('|').explode()
    print(f"  Top conditions: {conditions_flat.value_counts().head(5).to_dict()}")

    return df_full


if __name__ == "__main__":
    generate_users_csv(n_users=50000, output_path="data/users.csv")