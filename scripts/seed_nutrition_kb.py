"""
NARA Nutrition Knowledge Base Seeder
Pulls from USDA FoodData Central API — free, no billing required.

Setup:
    pip install psycopg2-binary requests
    Get free API key: https://fdc.nal.usda.gov/api-key-signup.html

Run:
    set USDA_API_KEY=your_key_here   (Windows)
    python scripts/seed_nutrition_kb.py
"""
import os
import json
import time
import psycopg2
import requests
from datetime import datetime

USDA_API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")
LOCAL_DB = "postgresql://neondb_owner:npg_GyEfuO9tA7DN@ep-cool-snow-az48g4au-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

# ── Comprehensive Indian dish list for Bangalore context ──────
DISHES = [
    # South Indian (most popular in Bangalore)
    "idli", "dosa", "masala dosa", "rava dosa", "uttapam", "vada",
    "sambar", "rasam", "coconut chutney", "upma", "pongal", "bisibelebath",
    "curd rice", "lemon rice", "tamarind rice", "pesarattu", "appam",
    "puttu", "avial", "olan", "kootu", "thoran", "payasam",

    # North Indian
    "biryani", "dal makhani", "butter chicken", "palak paneer",
    "chole bhature", "roti", "naan", "paratha", "aloo paratha",
    "rajma", "kadhi", "dal tadka", "aloo gobi", "paneer tikka",
    "malai kofta", "korma", "pulao", "khichdi",

    # Street food
    "pav bhaji", "vada pav", "misal pav", "pani puri", "bhel puri",
    "sev puri", "dahi puri", "kachori", "samosa", "aloo tikki",

    # Bangalore specific
    "MTR masala dosa", "Vidyarthi Bhavan benne dosa", "akki roti",
    "ragi mudde", "neer dosa", "mangalorean fish curry",
    "coorg pandi curry", "mysore masala dosa", "rava idli",

    # Beverages
    "masala chai", "filter coffee", "lassi", "chaas", "nimbu pani",
    "sugarcane juice",

    # Desserts
    "gulab jamun", "rasgulla", "kheer", "halwa", "ladoo",
    "barfi", "jalebi", "shrikhand", "kulfi",

    # Packaged / common
    "white rice", "brown rice", "wheat roti", "whole wheat bread",
    "paneer", "tofu", "eggs", "chicken breast", "dal",
    "moong dal", "chana dal", "urad dal", "toor dal",
]


def fetch_usda(dish: str) -> list:
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    try:
        resp = requests.get(url, params={
            "api_key": USDA_API_KEY,
            "query": dish,
            "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"],
            "pageSize": 3,
        }, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("foods", [])
        elif resp.status_code == 429:
            print("  Rate limited. Waiting 60s...")
            time.sleep(60)
            return fetch_usda(dish)
    except Exception as e:
        print(f"  Error: {e}")
    return []


def extract_nutrients(food: dict) -> dict:
    nutrient_map = {
        "Energy": "calories_kcal",
        "Protein": "protein_g",
        "Total lipid (fat)": "fat_g",
        "Carbohydrate, by difference": "carbs_g",
        "Fiber, total dietary": "fiber_g",
        "Sugars, total including NLEA": "sugar_g",
        "Sodium, Na": "sodium_mg",
        "Cholesterol": "cholesterol_mg",
        "Fatty acids, total saturated": "saturated_fat_g",
        "Iron, Fe": "iron_mg",
        "Calcium, Ca": "calcium_mg",
        "Vitamin C, total ascorbic acid": "vitamin_c_mg",
    }
    result = {}
    for n in food.get("foodNutrients", []):
        name = n.get("nutrientName", "")
        if name in nutrient_map:
            result[nutrient_map[name]] = round(n.get("value", 0), 2)
    return result


def estimate_glycemic_index(dish: str, nutrition: dict) -> float:
    """
    Rough GI estimate based on dish type and carb profile.
    Will be replaced by proper GI database in Sprint 4.
    """
    dish_lower = dish.lower()
    carbs = nutrition.get("carbs_g", 0)
    fiber = nutrition.get("fiber_g", 0)

    # High GI foods
    if any(w in dish_lower for w in ["rice", "biryani", "puri", "maida", "jalebi"]):
        return 70.0
    # Medium GI
    if any(w in dish_lower for w in ["roti", "paratha", "dosa", "idli", "upma"]):
        return 55.0
    # Low GI
    if any(w in dish_lower for w in ["dal", "chana", "rajma", "moong", "lentil"]):
        return 30.0
    # Default: estimate from carb:fiber ratio
    if fiber > 0 and carbs > 0:
        return max(20, min(90, (carbs / (fiber + 1)) * 10))
    return 50.0


def seed():
    conn = psycopg2.connect(LOCAL_DB)
    cur = conn.cursor()
    seeded = 0
    skipped = 0

    print(f"Starting nutrition KB seeding. {len(DISHES)} dishes to process.")
    print(f"Using USDA API key: {'DEMO_KEY (limited)' if USDA_API_KEY == 'DEMO_KEY' else 'Custom key'}\n")

    for i, dish in enumerate(DISHES):
        print(f"[{i+1}/{len(DISHES)}] {dish}...")

        # Check if already exists
        cur.execute("SELECT id FROM nutrition_kb WHERE dish_name = %s", (dish,))
        if cur.fetchone():
            print(f"  Already in KB, skipping.")
            skipped += 1
            continue

        foods = fetch_usda(dish)
        if not foods:
            # Insert with empty nutrition so we know we tried
            cur.execute("""
                INSERT INTO nutrition_kb (dish_name, source, per_100g, confidence)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (dish, "usda_not_found", json.dumps({}), 0.0))
            conn.commit()
            print(f"  Not found in USDA.")
            continue

        food = foods[0]
        nutrition = extract_nutrients(food)
        gi = estimate_glycemic_index(dish, nutrition)
        gl = round(gi * nutrition.get("carbs_g", 0) / 100, 1) if nutrition.get("carbs_g") else 0

        cur.execute("""
            INSERT INTO nutrition_kb
                (dish_name, source, per_100g, confidence, glycemic_index, glycemic_load, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            dish,
            "usda",
            json.dumps(nutrition),
            0.8,
            gi,
            gl,
            datetime.now(),
        ))
        conn.commit()
        seeded += 1
        print(f"  Saved: cal={nutrition.get('calories_kcal',0)} prot={nutrition.get('protein_g',0)}g carbs={nutrition.get('carbs_g',0)}g")

        time.sleep(0.3)  # respect rate limits

    cur.close()
    conn.close()
    print(f"\n✓ Done. Seeded: {seeded}, Skipped (exists): {skipped}, Total: {len(DISHES)}")


if __name__ == "__main__":
    seed()

