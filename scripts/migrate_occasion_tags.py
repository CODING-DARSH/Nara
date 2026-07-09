"""
NARA — Migration: Dish-level occasion tagging (FIX 1)
─────────────────────────────────────────────────────────────
PROBLEM:
  Recommendations repeated the same dishes across breakfast/lunch/dinner
  because filtering was done at CUISINE level (south_indian, north_indian...)
  which is far too coarse — masala dosa and biryani are both "south_indian"
  category but obviously not interchangeable by meal time.

FIX:
  Add occasion_tags JSONB column to nutrition_kb. Each dish gets tagged
  with which occasions it's actually appropriate for, e.g.:
    idli            -> ["breakfast", "snack"]
    chicken biryani -> ["lunch", "dinner"]
    masala chai     -> ["breakfast", "snack"]
    gulab jamun      -> ["dessert", "snack"]   (never primary meal)

Run:
  python scripts/migrate_occasion_tags.py
"""
import json
import psycopg2

LOCAL_DB = "postgresql://nara:nara_secret@127.0.0.1:5433/nara_data"

# Every dish currently in the 176-dish KB, tagged by real-world eating
# pattern (not by cuisine label). A dish can have multiple tags.
OCCASION_TAGS = {
    # ── Breakfast-primary ──────────────────────────────────────
    "idli": ["breakfast", "snack"],
    "dosa": ["breakfast", "snack"],
    "masala dosa": ["breakfast", "lunch"],
    "rava dosa": ["breakfast", "snack"],
    "set dosa": ["breakfast"],
    "neer dosa": ["breakfast"],
    "pesarattu": ["breakfast"],
    "uttapam": ["breakfast", "snack"],
    "adai": ["breakfast"],
    "rava idli": ["breakfast", "snack"],
    "kanchipuram idli": ["breakfast"],
    "mini idli": ["breakfast", "snack"],
    "medu vada": ["breakfast", "snack"],
    "masala vada": ["snack"],
    "punugulu": ["snack"],
    "upma": ["breakfast"],
    "vegetable upma": ["breakfast"],
    "poha upma": ["breakfast"],
    "poha": ["breakfast"],
    "pongal": ["breakfast"],
    "sweet pongal": ["breakfast", "dessert"],
    "appam": ["breakfast", "dinner"],
    "puttu": ["breakfast"],
    "dhokla": ["breakfast", "snack"],
    "thepla": ["breakfast", "snack"],
    "handvo": ["breakfast", "snack"],
    "khandvi": ["snack"],

    # ── Lunch / Dinner mains ───────────────────────────────────
    "sambar": ["lunch", "dinner"],
    "rasam": ["lunch", "dinner"],
    "curd rice": ["lunch", "dinner"],
    "lemon rice": ["lunch"],
    "tamarind rice": ["lunch"],
    "coconut rice": ["lunch"],
    "tomato rice": ["lunch"],
    "bisibelebath": ["lunch", "dinner"],
    "vangi bath": ["lunch"],
    "avial": ["lunch", "dinner"],
    "kerala fish curry": ["lunch", "dinner"],
    "olan": ["lunch", "dinner"],
    "thoran": ["lunch", "dinner"],
    "sadya": ["lunch"],
    "gongura mutton": ["lunch", "dinner"],
    "gutti vankaya": ["lunch", "dinner"],
    "parotta": ["lunch", "dinner"],
    "kottu roti": ["lunch", "dinner"],
    "murukku": ["snack"],
    "coconut chutney": ["breakfast", "lunch"],
    "tomato chutney": ["breakfast", "lunch"],

    "chicken biryani": ["lunch", "dinner"],
    "mutton biryani": ["lunch", "dinner"],
    "veg biryani": ["lunch", "dinner"],
    "egg biryani": ["lunch", "dinner"],
    "prawn biryani": ["lunch", "dinner"],
    "pulao": ["lunch", "dinner"],
    "jeera rice": ["lunch", "dinner"],

    "dal makhani": ["lunch", "dinner"],
    "dal tadka": ["lunch", "dinner"],
    "moong dal": ["lunch", "dinner"],
    "chana dal": ["lunch", "dinner"],
    "masoor dal": ["lunch", "dinner"],
    "palak paneer": ["lunch", "dinner"],
    "paneer tikka masala": ["lunch", "dinner"],
    "shahi paneer": ["lunch", "dinner"],
    "kadai paneer": ["lunch", "dinner"],
    "paneer bhurji": ["breakfast", "lunch", "dinner"],
    "matar paneer": ["lunch", "dinner"],
    "butter chicken": ["lunch", "dinner"],
    "chicken curry": ["lunch", "dinner"],
    "chicken tikka": ["snack", "dinner"],
    "tandoori chicken": ["dinner"],
    "chicken korma": ["lunch", "dinner"],
    "chicken do pyaza": ["lunch", "dinner"],
    "mutton curry": ["lunch", "dinner"],
    "rogan josh": ["lunch", "dinner"],
    "keema": ["lunch", "dinner"],
    "aloo gobi": ["lunch", "dinner"],
    "chole": ["lunch", "dinner"],
    "rajma": ["lunch", "dinner"],
    "malai kofta": ["lunch", "dinner"],
    "kadhi": ["lunch", "dinner"],
    "baingan bharta": ["lunch", "dinner"],
    "aloo matar": ["lunch", "dinner"],
    "bhindi masala": ["lunch", "dinner"],
    "aloo palak": ["lunch", "dinner"],
    "shahi korma": ["lunch", "dinner"],

    "roti": ["lunch", "dinner"],
    "naan": ["lunch", "dinner"],
    "paratha": ["breakfast", "lunch", "dinner"],
    "aloo paratha": ["breakfast"],
    "gobi paratha": ["breakfast"],
    "paneer paratha": ["breakfast"],
    "puri": ["breakfast", "lunch"],
    "bhatura": ["breakfast", "lunch"],
    "missi roti": ["lunch", "dinner"],

    # ── Gujarati / Maharashtrian / Rajasthani mains ────────────
    "undhiyu": ["lunch", "dinner"],
    "dal dhokli": ["lunch", "dinner"],
    "gujarati kadhi": ["lunch", "dinner"],
    "sev tameta": ["lunch", "dinner"],
    "rotlo": ["lunch", "dinner"],
    "sukhdi": ["dessert", "snack"],
    "misal pav": ["breakfast", "lunch"],
    "puran poli": ["lunch", "dessert"],
    "bharli vangi": ["lunch", "dinner"],
    "ukdiche modak": ["dessert", "snack"],
    "sabudana khichdi": ["breakfast", "snack"],
    "thalipeeth": ["breakfast"],
    "dal baati churma": ["lunch", "dinner"],
    "laal maas": ["lunch", "dinner"],
    "gatte ki sabzi": ["lunch", "dinner"],
    "ker sangri": ["lunch", "dinner"],
    "bajra khichdi": ["lunch", "dinner"],
    "rabdi": ["dessert"],

    # ── Goan ────────────────────────────────────────────────────
    "goan fish curry": ["lunch", "dinner"],
    "vindaloo": ["lunch", "dinner"],
    "bebinca": ["dessert"],

    # ── Bengali ─────────────────────────────────────────────────
    "machher jhol": ["lunch", "dinner"],
    "shorshe ilish": ["lunch", "dinner"],
    "aloo posto": ["lunch", "dinner"],
    "chingri malai curry": ["lunch", "dinner"],
    "luchi": ["breakfast", "lunch"],
    "mishti doi": ["dessert"],
    "rasgulla": ["dessert"],
    "sandesh": ["dessert"],
    "dal pakhala": ["lunch", "dinner"],
    "dalma": ["lunch", "dinner"],

    # ── Staples ─────────────────────────────────────────────────
    "steamed rice": ["lunch", "dinner"],
    "brown rice": ["lunch", "dinner"],
    "khichdi": ["lunch", "dinner", "breakfast"],
    "paneer": ["lunch", "dinner"],
    "egg": ["breakfast", "lunch", "dinner"],
    "chicken": ["lunch", "dinner"],
    "egg curry": ["breakfast", "lunch", "dinner"],
    "anda bhurji": ["breakfast"],
    "dahi": ["breakfast", "lunch", "dinner", "snack"],
    "raita": ["lunch", "dinner"],
    "mango pickle": ["lunch", "dinner"],
    "papadum": ["lunch", "dinner"],

    # ── Street food (snack-primary) ────────────────────────────
    "samosa": ["snack"],
    "pani puri": ["snack"],
    "bhel puri": ["snack"],
    "sev puri": ["snack"],
    "dahi puri": ["snack"],
    "aloo tikki": ["snack"],
    "dabeli": ["snack"],
    "chole bhature": ["breakfast", "lunch"],
    "kathi roll": ["lunch", "dinner", "snack"],
    "chaat": ["snack"],
    "vada pav": ["breakfast", "snack"],
    "pav bhaji": ["lunch", "dinner", "snack"],

    # ── Desserts (never primary, snack/dessert only) ───────────
    "gulab jamun": ["dessert", "snack"],
    "kheer": ["dessert"],
    "jalebi": ["breakfast", "dessert", "snack"],
    "halwa": ["dessert", "snack"],
    "gajar halwa": ["dessert", "snack"],
    "ladoo": ["dessert", "snack"],
    "barfi": ["dessert", "snack"],
    "kaju katli": ["dessert", "snack"],
    "rasmalai": ["dessert"],
    "kulfi": ["dessert", "snack"],
    "shrikhand": ["dessert"],
    "payasam": ["dessert"],

    # ── Beverages (any time, but skew breakfast/snack) ─────────
    "masala chai": ["breakfast", "snack"],
    "filter coffee": ["breakfast", "snack"],
    "lassi": ["breakfast", "snack"],
    "buttermilk": ["lunch", "dinner", "snack"],
    "nimbu pani": ["snack"],
    "aam panna": ["snack"],
    "jaljeera": ["snack"],
    "thandai": ["snack"],
    "coconut water": ["breakfast", "snack"],
    "sugarcane juice": ["snack"],
    "rooh afza": ["snack"],
}

# Late night gets derived automatically: only light/snack-tagged dishes
# qualify, never heavy lunch/dinner-only mains.
LATE_NIGHT_ELIGIBLE_TAGS = {"snack", "beverage", "staple"}


def derive_late_night(tags: list) -> bool:
    return any(t in LATE_NIGHT_ELIGIBLE_TAGS for t in tags) or "snack" in tags


def migrate():
    conn = psycopg2.connect(LOCAL_DB)
    cur = conn.cursor()

    print("Step 1: Adding occasion_tags column if missing...")
    cur.execute("""
        ALTER TABLE nutrition_kb
        ADD COLUMN IF NOT EXISTS occasion_tags JSONB NOT NULL DEFAULT '[]';
    """)
    conn.commit()

    print(f"Step 2: Backfilling occasion tags for {len(OCCASION_TAGS)} dishes...\n")
    updated, skipped = 0, 0

    for dish_name, tags in OCCASION_TAGS.items():
        final_tags = list(tags)
        if derive_late_night(tags) and "late_night" not in final_tags:
            final_tags.append("late_night")

        cur.execute(
            "UPDATE nutrition_kb SET occasion_tags = %s WHERE dish_name = %s",
            (json.dumps(final_tags), dish_name),
        )
        if cur.rowcount > 0:
            updated += 1
            print(f"  ✓ {dish_name:<35} -> {final_tags}")
        else:
            skipped += 1
            print(f"  - {dish_name:<35} (not found in KB, skipped)")

    conn.commit()

    print("\nStep 3: Catching any dishes left untagged (default = lunch+dinner)...")
    cur.execute("""
        UPDATE nutrition_kb
        SET occasion_tags = '["lunch", "dinner"]'::jsonb
        WHERE occasion_tags = '[]'::jsonb
    """)
    fallback_count = cur.rowcount
    conn.commit()

    cur.close()
    conn.close()

    print(f"\nDone.")
    print(f"  Tagged explicitly : {updated}")
    print(f"  Not found in KB   : {skipped}")
    print(f"  Fallback tagged   : {fallback_count}")
    print(f"\nVerify:")
    print(f"  SELECT dish_name, occasion_tags FROM nutrition_kb LIMIT 10;")
    print(f"  SELECT occasion_tags, COUNT(*) FROM nutrition_kb GROUP BY occasion_tags;")


if __name__ == "__main__":
    migrate()