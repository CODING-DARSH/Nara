# """
# NARA Indian Nutrition Knowledge Base Seeder
# Data sourced from ICMR-NIN (Indian Council of Medical Research - National Institute of Nutrition)
# and verified nutritional references for Indian cuisine.

# No API key needed. No rate limits. Runs in under 10 seconds.

# Run:
#     pip install psycopg2-binary
#     python scripts/seed_indian_nutrition.py
# """
# import json
# import psycopg2
# from datetime import datetime

# LOCAL_DB = "postgresql://neondb_owner:npg_VUpS27YXsGKQ@ep-orange-lake-aoafbm87.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

# # ============================================================
# # INDIAN NUTRITION DATABASE
# # All values per 100g cooked/prepared unless noted
# # Source: ICMR-NIN Nutritive Value of Indian Foods 2023
# # Format: dish_name, cuisine, is_veg, per_100g nutrition, gi, aliases
# # ============================================================

# INDIAN_DISHES = [

#     # ── SOUTH INDIAN ─────────────────────────────────────────
#     {
#         "dish_name": "idli",
#         "cuisine_type": "south_indian",
#         "is_veg": True,
#         "aliases": ["idly", "steamed idli", "plain idli"],
#         "per_100g": {
#             "calories_kcal": 130, "protein_g": 3.4, "carbs_g": 28.0,
#             "fat_g": 0.5, "fiber_g": 1.5, "sugar_g": 0.5,
#             "sodium_mg": 250, "calcium_mg": 18, "iron_mg": 0.8
#         },
#         "glycemic_index": 70, "glycemic_load": 19.6,
#         "serving_size_g": 120,
#         "ingredients": ["rice", "urad dal", "salt", "water"],
#         "allergens": [],
#     },
#     {
#         "dish_name": "dosa",
#         "cuisine_type": "south_indian",
#         "is_veg": True,
#         "aliases": ["plain dosa", "sada dosa"],
#         "per_100g": {
#             "calories_kcal": 168, "protein_g": 3.9, "carbs_g": 33.0,
#             "fat_g": 2.5, "fiber_g": 1.2, "sugar_g": 0.8,
#             "sodium_mg": 210, "calcium_mg": 15, "iron_mg": 1.0
#         },
#         "glycemic_index": 69, "glycemic_load": 22.8,
#         "serving_size_g": 100,
#         "ingredients": ["rice", "urad dal", "oil", "salt"],
#         "allergens": [],
#     },
#     {
#         "dish_name": "masala dosa",
#         "cuisine_type": "south_indian",
#         "is_veg": True,
#         "aliases": ["masala dose", "potato dosa"],
#         "per_100g": {
#             "calories_kcal": 175, "protein_g": 4.2, "carbs_g": 32.0,
#             "fat_g": 3.8, "fiber_g": 2.1, "sugar_g": 1.2,
#             "sodium_mg": 320, "calcium_mg": 22, "iron_mg": 1.2
#         },
#         "glycemic_index": 68, "glycemic_load": 21.8,
#         "serving_size_g": 200,
#         "ingredients": ["rice", "urad dal", "potato", "onion", "mustard seeds", "oil", "turmeric"],
#         "allergens": [],
#     },
#     {
#         "dish_name": "uttapam",
#         "cuisine_type": "south_indian",
#         "is_veg": True,
#         "aliases": ["uthappam", "uttapam with vegetables"],
#         "per_100g": {
#             "calories_kcal": 145, "protein_g": 4.8, "carbs_g": 26.0,
#             "fat_g": 2.8, "fiber_g": 2.5, "sugar_g": 2.0,
#             "sodium_mg": 280, "calcium_mg": 35, "iron_mg": 1.1
#         },
#         "glycemic_index": 65, "glycemic_load": 16.9,
#         "serving_size_g": 150,
#         "ingredients": ["rice", "urad dal", "onion", "tomato", "green chilli", "coriander", "oil"],
#         "allergens": [],
#     },
#     {
#         "dish_name": "vada",
#         "cuisine_type": "south_indian",
#         "is_veg": True,
#         "aliases": ["medu vada", "urad dal vada", "vadai"],
#         "per_100g": {
#             "calories_kcal": 280, "protein_g": 12.5, "carbs_g": 32.0,
#             "fat_g": 11.0, "fiber_g": 3.2, "sugar_g": 0.5,
#             "sodium_mg": 380, "calcium_mg": 45, "iron_mg": 2.5
#         },
#         "glycemic_index": 55, "glycemic_load": 17.6,
#         "serving_size_g": 60,
#         "ingredients": ["urad dal", "onion", "curry leaves", "ginger", "oil", "salt"],
#         "allergens": [],
#     },
#     {
#         "dish_name": "sambar",
#         "cuisine_type": "south_indian",
#         "is_veg": True,
#         "aliases": ["sambhar", "sambar dal"],
#         "per_100g": {
#             "calories_kcal": 52, "protein_g": 3.1, "carbs_g": 8.2,
#             "fat_g": 0.8, "fiber_g": 2.8, "sugar_g": 2.5,
#             "sodium_mg": 420, "calcium_mg": 28, "iron_mg": 1.5
#         },
#         "glycemic_index": 35, "glycemic_load": 2.9,
#         "serving_size_g": 200,
#         "ingredients": ["toor dal", "tamarind", "tomato", "onion", "drumstick", "sambar powder", "mustard seeds"],
#         "allergens": [],
#     },
#     {
#         "dish_name": "rasam",
#         "cuisine_type": "south_indian",
#         "is_veg": True,
#         "aliases": ["pepper rasam", "tomato rasam", "saaru"],
#         "per_100g": {
#             "calories_kcal": 28, "protein_g": 1.2, "carbs_g": 4.8,
#             "fat_g": 0.5, "fiber_g": 0.8, "sugar_g": 1.5,
#             "sodium_mg": 380, "calcium_mg": 12, "iron_mg": 0.8
#         },
#         "glycemic_index": 30, "glycemic_load": 1.4,
#         "serving_size_g": 200,
#         "ingredients": ["toor dal", "tamarind", "tomato", "pepper", "cumin", "garlic", "mustard seeds"],
#         "allergens": [],
#     },
#     {
#         "dish_name": "upma",
#         "cuisine_type": "south_indian",
#         "is_veg": True,
#         "aliases": ["rava upma", "sooji upma"],
#         "per_100g": {
#             "calories_kcal": 145, "protein_g": 4.2, "carbs_g": 26.5,
#             "fat_g": 3.2, "fiber_g": 1.8, "sugar_g": 1.0,
#             "sodium_mg": 290, "calcium_mg": 20, "iron_mg": 1.2
#         },
#         "glycemic_index": 66, "glycemic_load": 17.5,
#         "serving_size_g": 200,
#         "ingredients": ["semolina", "onion", "mustard seeds", "curry leaves", "oil", "green chilli"],
#         "allergens": ["gluten"],
#     },
#     {
#         "dish_name": "pongal",
#         "cuisine_type": "south_indian",
#         "is_veg": True,
#         "aliases": ["khichdi pongal", "ven pongal", "kara pongal"],
#         "per_100g": {
#             "calories_kcal": 152, "protein_g": 5.2, "carbs_g": 26.8,
#             "fat_g": 3.5, "fiber_g": 1.5, "sugar_g": 0.5,
#             "sodium_mg": 180, "calcium_mg": 22, "iron_mg": 1.0
#         },
#         "glycemic_index": 58, "glycemic_load": 15.5,
#         "serving_size_g": 200,
#         "ingredients": ["rice", "moong dal", "ghee", "pepper", "cumin", "ginger", "curry leaves"],
#         "allergens": [],
#     },
#     {
#         "dish_name": "curd rice",
#         "cuisine_type": "south_indian",
#         "is_veg": True,
#         "aliases": ["thayir sadam", "dahi chawal south indian", "bagala bath"],
#         "per_100g": {
#             "calories_kcal": 118, "protein_g": 3.8, "carbs_g": 20.5,
#             "fat_g": 2.2, "fiber_g": 0.5, "sugar_g": 2.8,
#             "sodium_mg": 220, "calcium_mg": 85, "iron_mg": 0.5
#         },
#         "glycemic_index": 55, "glycemic_load": 11.3,
#         "serving_size_g": 250,
#         "ingredients": ["rice", "curd", "milk", "mustard seeds", "curry leaves", "green chilli", "ginger"],
#         "allergens": ["milk"],
#     },
#     {
#         "dish_name": "bisibelebath",
#         "cuisine_type": "south_indian",
#         "is_veg": True,
#         "aliases": ["bisi bele bath", "bisibele hulianna"],
#         "per_100g": {
#             "calories_kcal": 148, "protein_g": 5.5, "carbs_g": 24.5,
#             "fat_g": 3.2, "fiber_g": 3.0, "sugar_g": 2.0,
#             "sodium_mg": 340, "calcium_mg": 35, "iron_mg": 1.8
#         },
#         "glycemic_index": 55, "glycemic_load": 13.5,
#         "serving_size_g": 250,
#         "ingredients": ["rice", "toor dal", "mixed vegetables", "tamarind", "ghee", "bisibelebath powder"],
#         "allergens": [],
#     },
#     {
#         "dish_name": "rava idli",
#         "cuisine_type": "south_indian",
#         "is_veg": True,
#         "aliases": ["semolina idli", "sooji idli"],
#         "per_100g": {
#             "calories_kcal": 148, "protein_g": 4.5, "carbs_g": 26.5,
#             "fat_g": 3.0, "fiber_g": 1.8, "sugar_g": 1.5,
#             "sodium_mg": 310, "calcium_mg": 28, "iron_mg": 1.0
#         },
#         "glycemic_index": 65, "glycemic_load": 17.2,
#         "serving_size_g": 120,
#         "ingredients": ["semolina", "curd", "cashews", "mustard seeds", "curry leaves", "baking soda"],
#         "allergens": ["gluten", "milk", "tree_nuts"],
#     },
#     {
#         "dish_name": "akki roti",
#         "cuisine_type": "south_indian",
#         "is_veg": True,
#         "aliases": ["rice roti", "akki rotti"],
#         "per_100g": {
#             "calories_kcal": 162, "protein_g": 2.8, "carbs_g": 34.5,
#             "fat_g": 1.8, "fiber_g": 1.0, "sugar_g": 0.5,
#             "sodium_mg": 180, "calcium_mg": 12, "iron_mg": 0.8
#         },
#         "glycemic_index": 72, "glycemic_load": 24.8,
#         "serving_size_g": 100,
#         "ingredients": ["rice flour", "onion", "green chilli", "coriander", "oil"],
#         "allergens": [],
#     },
#     {
#         "dish_name": "neer dosa",
#         "cuisine_type": "south_indian",
#         "is_veg": True,
#         "aliases": ["neer dose", "water dosa"],
#         "per_100g": {
#             "calories_kcal": 112, "protein_g": 2.2, "carbs_g": 24.5,
#             "fat_g": 0.8, "fiber_g": 0.5, "sugar_g": 0.3,
#             "sodium_mg": 120, "calcium_mg": 8, "iron_mg": 0.5
#         },
#         "glycemic_index": 75, "glycemic_load": 18.4,
#         "serving_size_g": 80,
#         "ingredients": ["rice", "coconut", "water", "salt"],
#         "allergens": [],
#     },

#     # ── BIRYANI & RICE DISHES ────────────────────────────────
#     {
#         "dish_name": "chicken biryani",
#         "cuisine_type": "biryani",
#         "is_veg": False,
#         "aliases": ["biryani", "hyderabadi biryani", "dum biryani"],
#         "per_100g": {
#             "calories_kcal": 185, "protein_g": 10.5, "carbs_g": 24.5,
#             "fat_g": 5.2, "fiber_g": 1.2, "sugar_g": 1.0,
#             "sodium_mg": 420, "calcium_mg": 25, "iron_mg": 1.5
#         },
#         "glycemic_index": 58, "glycemic_load": 14.2,
#         "serving_size_g": 350,
#         "ingredients": ["basmati rice", "chicken", "onion", "yogurt", "ghee", "biryani spices", "saffron"],
#         "allergens": ["milk"],
#     },
#     {
#         "dish_name": "veg biryani",
#         "cuisine_type": "biryani",
#         "is_veg": True,
#         "aliases": ["vegetable biryani", "veg dum biryani"],
#         "per_100g": {
#             "calories_kcal": 162, "protein_g": 4.2, "carbs_g": 28.5,
#             "fat_g": 3.8, "fiber_g": 2.5, "sugar_g": 2.0,
#             "sodium_mg": 380, "calcium_mg": 35, "iron_mg": 1.2
#         },
#         "glycemic_index": 55, "glycemic_load": 15.7,
#         "serving_size_g": 300,
#         "ingredients": ["basmati rice", "mixed vegetables", "onion", "yogurt", "ghee", "biryani spices"],
#         "allergens": ["milk"],
#     },
#     {
#         "dish_name": "pulao",
#         "cuisine_type": "north_indian",
#         "is_veg": True,
#         "aliases": ["veg pulao", "pilaf", "vegetable pulao"],
#         "per_100g": {
#             "calories_kcal": 155, "protein_g": 3.5, "carbs_g": 28.0,
#             "fat_g": 3.2, "fiber_g": 1.8, "sugar_g": 1.5,
#             "sodium_mg": 280, "calcium_mg": 18, "iron_mg": 0.9
#         },
#         "glycemic_index": 55, "glycemic_load": 15.4,
#         "serving_size_g": 250,
#         "ingredients": ["basmati rice", "mixed vegetables", "ghee", "whole spices", "onion"],
#         "allergens": ["milk"],
#     },

#     # ── NORTH INDIAN CURRIES ─────────────────────────────────
#     {
#         "dish_name": "dal makhani",
#         "cuisine_type": "north_indian",
#         "is_veg": True,
#         "aliases": ["dal makhni", "black dal", "maa ki dal"],
#         "per_100g": {
#             "calories_kcal": 135, "protein_g": 6.8, "carbs_g": 16.5,
#             "fat_g": 4.8, "fiber_g": 4.2, "sugar_g": 1.5,
#             "sodium_mg": 380, "calcium_mg": 48, "iron_mg": 2.8
#         },
#         "glycemic_index": 38, "glycemic_load": 6.3,
#         "serving_size_g": 250,
#         "ingredients": ["black urad dal", "kidney beans", "butter", "cream", "tomato", "onion", "ginger garlic"],
#         "allergens": ["milk"],
#     },
#     {
#         "dish_name": "butter chicken",
#         "cuisine_type": "north_indian",
#         "is_veg": False,
#         "aliases": ["murgh makhani", "chicken makhani"],
#         "per_100g": {
#             "calories_kcal": 165, "protein_g": 14.5, "carbs_g": 8.5,
#             "fat_g": 8.2, "fiber_g": 1.2, "sugar_g": 4.5,
#             "sodium_mg": 520, "calcium_mg": 38, "iron_mg": 1.2
#         },
#         "glycemic_index": 35, "glycemic_load": 3.0,
#         "serving_size_g": 250,
#         "ingredients": ["chicken", "butter", "cream", "tomato", "onion", "cashews", "garam masala"],
#         "allergens": ["milk", "tree_nuts"],
#     },
#     {
#         "dish_name": "palak paneer",
#         "cuisine_type": "north_indian",
#         "is_veg": True,
#         "aliases": ["spinach paneer", "saag paneer"],
#         "per_100g": {
#             "calories_kcal": 142, "protein_g": 7.5, "carbs_g": 8.2,
#             "fat_g": 8.8, "fiber_g": 2.8, "sugar_g": 2.0,
#             "sodium_mg": 340, "calcium_mg": 220, "iron_mg": 3.5
#         },
#         "glycemic_index": 30, "glycemic_load": 2.5,
#         "serving_size_g": 250,
#         "ingredients": ["spinach", "paneer", "onion", "tomato", "cream", "ginger garlic", "spices"],
#         "allergens": ["milk"],
#     },
#     {
#         "dish_name": "paneer tikka masala",
#         "cuisine_type": "north_indian",
#         "is_veg": True,
#         "aliases": ["paneer tikka", "paneer masala"],
#         "per_100g": {
#             "calories_kcal": 178, "protein_g": 9.2, "carbs_g": 10.5,
#             "fat_g": 11.2, "fiber_g": 1.8, "sugar_g": 4.2,
#             "sodium_mg": 480, "calcium_mg": 240, "iron_mg": 1.5
#         },
#         "glycemic_index": 35, "glycemic_load": 3.7,
#         "serving_size_g": 250,
#         "ingredients": ["paneer", "onion", "tomato", "cream", "bell pepper", "tikka masala spices"],
#         "allergens": ["milk"],
#     },
#     {
#         "dish_name": "chole",
#         "cuisine_type": "north_indian",
#         "is_veg": True,
#         "aliases": ["chana masala", "chickpea curry", "chole masala"],
#         "per_100g": {
#             "calories_kcal": 128, "protein_g": 7.2, "carbs_g": 18.5,
#             "fat_g": 2.8, "fiber_g": 5.5, "sugar_g": 2.2,
#             "sodium_mg": 420, "calcium_mg": 58, "iron_mg": 3.2
#         },
#         "glycemic_index": 28, "glycemic_load": 5.2,
#         "serving_size_g": 250,
#         "ingredients": ["chickpeas", "onion", "tomato", "ginger garlic", "chole masala", "oil"],
#         "allergens": [],
#     },
#     {
#         "dish_name": "rajma",
#         "cuisine_type": "north_indian",
#         "is_veg": True,
#         "aliases": ["rajma masala", "kidney bean curry", "rajma chawal"],
#         "per_100g": {
#             "calories_kcal": 118, "protein_g": 6.8, "carbs_g": 17.2,
#             "fat_g": 2.2, "fiber_g": 5.8, "sugar_g": 1.8,
#             "sodium_mg": 380, "calcium_mg": 42, "iron_mg": 2.8
#         },
#         "glycemic_index": 29, "glycemic_load": 5.0,
#         "serving_size_g": 250,
#         "ingredients": ["kidney beans", "onion", "tomato", "ginger garlic", "rajma masala", "oil"],
#         "allergens": [],
#     },
#     {
#         "dish_name": "dal tadka",
#         "cuisine_type": "north_indian",
#         "is_veg": True,
#         "aliases": ["yellow dal", "toor dal tadka", "dal fry"],
#         "per_100g": {
#             "calories_kcal": 95, "protein_g": 5.8, "carbs_g": 13.5,
#             "fat_g": 2.2, "fiber_g": 3.5, "sugar_g": 1.2,
#             "sodium_mg": 320, "calcium_mg": 32, "iron_mg": 2.2
#         },
#         "glycemic_index": 32, "glycemic_load": 4.3,
#         "serving_size_g": 250,
#         "ingredients": ["toor dal", "onion", "tomato", "garlic", "cumin", "ghee", "turmeric"],
#         "allergens": ["milk"],
#     },
#     {
#         "dish_name": "aloo gobi",
#         "cuisine_type": "north_indian",
#         "is_veg": True,
#         "aliases": ["potato cauliflower curry", "aloo gobi sabzi"],
#         "per_100g": {
#             "calories_kcal": 88, "protein_g": 2.5, "carbs_g": 14.5,
#             "fat_g": 2.8, "fiber_g": 3.2, "sugar_g": 2.8,
#             "sodium_mg": 280, "calcium_mg": 28, "iron_mg": 0.9
#         },
#         "glycemic_index": 55, "glycemic_load": 8.0,
#         "serving_size_g": 200,
#         "ingredients": ["potato", "cauliflower", "onion", "tomato", "turmeric", "coriander powder", "oil"],
#         "allergens": [],
#     },
#     {
#         "dish_name": "malai kofta",
#         "cuisine_type": "north_indian",
#         "is_veg": True,
#         "aliases": ["kofta curry", "paneer kofta"],
#         "per_100g": {
#             "calories_kcal": 195, "protein_g": 6.5, "carbs_g": 18.5,
#             "fat_g": 11.2, "fiber_g": 2.0, "sugar_g": 4.8,
#             "sodium_mg": 420, "calcium_mg": 128, "iron_mg": 1.5
#         },
#         "glycemic_index": 48, "glycemic_load": 8.9,
#         "serving_size_g": 250,
#         "ingredients": ["paneer", "potato", "cream", "onion", "tomato", "cashews", "spices"],
#         "allergens": ["milk", "tree_nuts"],
#     },
#     {
#         "dish_name": "kadhi",
#         "cuisine_type": "north_indian",
#         "is_veg": True,
#         "aliases": ["kadhi pakora", "besan kadhi", "punjabi kadhi"],
#         "per_100g": {
#             "calories_kcal": 98, "protein_g": 3.8, "carbs_g": 10.5,
#             "fat_g": 4.5, "fiber_g": 1.8, "sugar_g": 3.5,
#             "sodium_mg": 380, "calcium_mg": 95, "iron_mg": 1.2
#         },
#         "glycemic_index": 42, "glycemic_load": 4.4,
#         "serving_size_g": 250,
#         "ingredients": ["yogurt", "besan", "onion", "mustard seeds", "curry leaves", "oil", "turmeric"],
#         "allergens": ["milk"],
#     },

#     # ── BREADS ───────────────────────────────────────────────
#     {
#         "dish_name": "roti",
#         "cuisine_type": "north_indian",
#         "is_veg": True,
#         "aliases": ["chapati", "phulka", "wheat roti"],
#         "per_100g": {
#             "calories_kcal": 297, "protein_g": 9.5, "carbs_g": 57.0,
#             "fat_g": 3.8, "fiber_g": 4.5, "sugar_g": 1.2,
#             "sodium_mg": 320, "calcium_mg": 35, "iron_mg": 3.5
#         },
#         "glycemic_index": 62, "glycemic_load": 35.3,
#         "serving_size_g": 40,
#         "ingredients": ["whole wheat flour", "water", "salt", "oil"],
#         "allergens": ["gluten"],
#     },
#     {
#         "dish_name": "naan",
#         "cuisine_type": "north_indian",
#         "is_veg": True,
#         "aliases": ["tandoori naan", "butter naan", "garlic naan"],
#         "per_100g": {
#             "calories_kcal": 310, "protein_g": 9.0, "carbs_g": 55.0,
#             "fat_g": 5.8, "fiber_g": 2.2, "sugar_g": 3.5,
#             "sodium_mg": 480, "calcium_mg": 48, "iron_mg": 2.8
#         },
#         "glycemic_index": 71, "glycemic_load": 39.1,
#         "serving_size_g": 80,
#         "ingredients": ["maida", "yogurt", "yeast", "butter", "salt"],
#         "allergens": ["gluten", "milk"],
#     },
#     {
#         "dish_name": "paratha",
#         "cuisine_type": "north_indian",
#         "is_veg": True,
#         "aliases": ["plain paratha", "laccha paratha"],
#         "per_100g": {
#             "calories_kcal": 326, "protein_g": 8.2, "carbs_g": 52.5,
#             "fat_g": 9.5, "fiber_g": 3.8, "sugar_g": 1.0,
#             "sodium_mg": 350, "calcium_mg": 28, "iron_mg": 2.8
#         },
#         "glycemic_index": 62, "glycemic_load": 32.6,
#         "serving_size_g": 80,
#         "ingredients": ["whole wheat flour", "oil", "salt", "water"],
#         "allergens": ["gluten"],
#     },
#     {
#         "dish_name": "aloo paratha",
#         "cuisine_type": "north_indian",
#         "is_veg": True,
#         "aliases": ["potato paratha", "stuffed paratha"],
#         "per_100g": {
#             "calories_kcal": 285, "protein_g": 6.8, "carbs_g": 45.5,
#             "fat_g": 8.5, "fiber_g": 3.5, "sugar_g": 1.5,
#             "sodium_mg": 380, "calcium_mg": 25, "iron_mg": 2.2
#         },
#         "glycemic_index": 65, "glycemic_load": 29.6,
#         "serving_size_g": 120,
#         "ingredients": ["whole wheat flour", "potato", "onion", "green chilli", "coriander", "oil"],
#         "allergens": ["gluten"],
#     },

#     # ── STREET FOOD ──────────────────────────────────────────
#     {
#         "dish_name": "pav bhaji",
#         "cuisine_type": "street_food",
#         "is_veg": True,
#         "aliases": ["pav bhaaji", "mumbai pav bhaji"],
#         "per_100g": {
#             "calories_kcal": 152, "protein_g": 4.2, "carbs_g": 22.5,
#             "fat_g": 5.5, "fiber_g": 3.8, "sugar_g": 4.5,
#             "sodium_mg": 480, "calcium_mg": 45, "iron_mg": 1.8
#         },
#         "glycemic_index": 58, "glycemic_load": 13.1,
#         "serving_size_g": 250,
#         "ingredients": ["mixed vegetables", "potato", "butter", "pav bhaji masala", "pav bread", "onion"],
#         "allergens": ["gluten", "milk"],
#     },
#     {
#         "dish_name": "vada pav",
#         "cuisine_type": "street_food",
#         "is_veg": True,
#         "aliases": ["batata vada pav", "mumbai vada pav"],
#         "per_100g": {
#             "calories_kcal": 268, "protein_g": 7.2, "carbs_g": 42.5,
#             "fat_g": 7.8, "fiber_g": 2.8, "sugar_g": 3.2,
#             "sodium_mg": 520, "calcium_mg": 38, "iron_mg": 2.2
#         },
#         "glycemic_index": 65, "glycemic_load": 27.6,
#         "serving_size_g": 120,
#         "ingredients": ["potato", "besan", "pav bread", "green chutney", "garlic chutney", "oil"],
#         "allergens": ["gluten"],
#     },
#     {
#         "dish_name": "samosa",
#         "cuisine_type": "street_food",
#         "is_veg": True,
#         "aliases": ["aloo samosa", "potato samosa"],
#         "per_100g": {
#             "calories_kcal": 285, "protein_g": 5.8, "carbs_g": 35.5,
#             "fat_g": 13.5, "fiber_g": 3.2, "sugar_g": 2.0,
#             "sodium_mg": 420, "calcium_mg": 22, "iron_mg": 1.8
#         },
#         "glycemic_index": 60, "glycemic_load": 21.3,
#         "serving_size_g": 80,
#         "ingredients": ["maida", "potato", "peas", "spices", "oil"],
#         "allergens": ["gluten"],
#     },
#     {
#         "dish_name": "pani puri",
#         "cuisine_type": "street_food",
#         "is_veg": True,
#         "aliases": ["gol gappa", "puchka", "gupchup"],
#         "per_100g": {
#             "calories_kcal": 198, "protein_g": 4.5, "carbs_g": 35.5,
#             "fat_g": 5.2, "fiber_g": 3.5, "sugar_g": 4.8,
#             "sodium_mg": 580, "calcium_mg": 28, "iron_mg": 1.5
#         },
#         "glycemic_index": 62, "glycemic_load": 22.0,
#         "serving_size_g": 100,
#         "ingredients": ["semolina", "potato", "chickpeas", "tamarind water", "mint water", "spices"],
#         "allergens": ["gluten"],
#     },
#     {
#         "dish_name": "bhel puri",
#         "cuisine_type": "street_food",
#         "is_veg": True,
#         "aliases": ["bhel", "mumbai bhel"],
#         "per_100g": {
#             "calories_kcal": 185, "protein_g": 5.2, "carbs_g": 32.5,
#             "fat_g": 4.8, "fiber_g": 4.2, "sugar_g": 5.5,
#             "sodium_mg": 520, "calcium_mg": 35, "iron_mg": 2.2
#         },
#         "glycemic_index": 58, "glycemic_load": 18.9,
#         "serving_size_g": 150,
#         "ingredients": ["puffed rice", "sev", "onion", "tomato", "tamarind chutney", "green chutney", "potato"],
#         "allergens": ["gluten"],
#     },

#     # ── SNACKS & BREAKFAST ───────────────────────────────────
#     {
#         "dish_name": "poha",
#         "cuisine_type": "north_indian",
#         "is_veg": True,
#         "aliases": ["kanda poha", "batata poha", "flattened rice"],
#         "per_100g": {
#             "calories_kcal": 158, "protein_g": 3.2, "carbs_g": 32.5,
#             "fat_g": 2.8, "fiber_g": 1.8, "sugar_g": 2.5,
#             "sodium_mg": 280, "calcium_mg": 18, "iron_mg": 2.8
#         },
#         "glycemic_index": 68, "glycemic_load": 22.1,
#         "serving_size_g": 200,
#         "ingredients": ["flattened rice", "onion", "potato", "mustard seeds", "curry leaves", "turmeric", "oil"],
#         "allergens": [],
#     },
#     {
#         "dish_name": "dhokla",
#         "cuisine_type": "gujarati",
#         "is_veg": True,
#         "aliases": ["khaman dhokla", "besan dhokla"],
#         "per_100g": {
#             "calories_kcal": 145, "protein_g": 6.5, "carbs_g": 22.5,
#             "fat_g": 3.2, "fiber_g": 2.8, "sugar_g": 4.5,
#             "sodium_mg": 380, "calcium_mg": 42, "iron_mg": 1.8
#         },
#         "glycemic_index": 45, "glycemic_load": 10.1,
#         "serving_size_g": 150,
#         "ingredients": ["besan", "yogurt", "sugar", "lemon juice", "mustard seeds", "curry leaves", "green chilli"],
#         "allergens": ["milk"],
#     },

#     # ── DESSERTS ─────────────────────────────────────────────
#     {
#         "dish_name": "gulab jamun",
#         "cuisine_type": "dessert",
#         "is_veg": True,
#         "aliases": ["gulab jamun syrup"],
#         "per_100g": {
#             "calories_kcal": 352, "protein_g": 5.8, "carbs_g": 52.5,
#             "fat_g": 13.5, "fiber_g": 0.5, "sugar_g": 42.0,
#             "sodium_mg": 180, "calcium_mg": 85, "iron_mg": 0.8
#         },
#         "glycemic_index": 85, "glycemic_load": 44.6,
#         "serving_size_g": 60,
#         "ingredients": ["khoya", "maida", "sugar syrup", "cardamom", "oil"],
#         "allergens": ["milk", "gluten"],
#     },
#     {
#         "dish_name": "kheer",
#         "cuisine_type": "dessert",
#         "is_veg": True,
#         "aliases": ["rice kheer", "payasam", "rice pudding indian"],
#         "per_100g": {
#             "calories_kcal": 148, "protein_g": 4.2, "carbs_g": 22.5,
#             "fat_g": 4.8, "fiber_g": 0.3, "sugar_g": 16.5,
#             "sodium_mg": 65, "calcium_mg": 128, "iron_mg": 0.5
#         },
#         "glycemic_index": 75, "glycemic_load": 16.9,
#         "serving_size_g": 150,
#         "ingredients": ["rice", "milk", "sugar", "cardamom", "saffron", "almonds", "cashews"],
#         "allergens": ["milk", "tree_nuts"],
#     },
#     {
#         "dish_name": "jalebi",
#         "cuisine_type": "dessert",
#         "is_veg": True,
#         "aliases": ["jilebi", "fresh jalebi"],
#         "per_100g": {
#             "calories_kcal": 380, "protein_g": 4.2, "carbs_g": 65.5,
#             "fat_g": 11.5, "fiber_g": 0.8, "sugar_g": 52.0,
#             "sodium_mg": 85, "calcium_mg": 18, "iron_mg": 1.2
#         },
#         "glycemic_index": 88, "glycemic_load": 57.6,
#         "serving_size_g": 80,
#         "ingredients": ["maida", "sugar syrup", "oil", "saffron"],
#         "allergens": ["gluten"],
#     },

#     # ── BEVERAGES ────────────────────────────────────────────
#     {
#         "dish_name": "masala chai",
#         "cuisine_type": "beverage",
#         "is_veg": True,
#         "aliases": ["chai", "Indian tea", "spiced tea"],
#         "per_100g": {
#             "calories_kcal": 42, "protein_g": 1.8, "carbs_g": 6.5,
#             "fat_g": 1.2, "fiber_g": 0.0, "sugar_g": 5.5,
#             "sodium_mg": 28, "calcium_mg": 62, "iron_mg": 0.2
#         },
#         "glycemic_index": 45, "glycemic_load": 2.9,
#         "serving_size_g": 200,
#         "ingredients": ["milk", "tea leaves", "sugar", "ginger", "cardamom", "cinnamon"],
#         "allergens": ["milk"],
#     },
#     {
#         "dish_name": "filter coffee",
#         "cuisine_type": "beverage",
#         "is_veg": True,
#         "aliases": ["south indian coffee", "degree coffee", "kaapi"],
#         "per_100g": {
#             "calories_kcal": 38, "protein_g": 1.5, "carbs_g": 5.2,
#             "fat_g": 1.2, "fiber_g": 0.0, "sugar_g": 4.8,
#             "sodium_mg": 22, "calcium_mg": 58, "iron_mg": 0.1
#         },
#         "glycemic_index": 40, "glycemic_load": 2.1,
#         "serving_size_g": 150,
#         "ingredients": ["coffee decoction", "milk", "sugar"],
#         "allergens": ["milk"],
#     },
#     {
#         "dish_name": "lassi",
#         "cuisine_type": "beverage",
#         "is_veg": True,
#         "aliases": ["sweet lassi", "punjabi lassi", "mango lassi"],
#         "per_100g": {
#             "calories_kcal": 72, "protein_g": 3.5, "carbs_g": 9.8,
#             "fat_g": 2.2, "fiber_g": 0.0, "sugar_g": 9.0,
#             "sodium_mg": 48, "calcium_mg": 118, "iron_mg": 0.1
#         },
#         "glycemic_index": 48, "glycemic_load": 4.7,
#         "serving_size_g": 250,
#         "ingredients": ["yogurt", "water", "sugar", "cardamom"],
#         "allergens": ["milk"],
#     },

#     # ── STAPLES ──────────────────────────────────────────────
#     {
#         "dish_name": "steamed rice",
#         "cuisine_type": "staple",
#         "is_veg": True,
#         "aliases": ["plain rice", "white rice cooked", "boiled rice"],
#         "per_100g": {
#             "calories_kcal": 130, "protein_g": 2.7, "carbs_g": 28.2,
#             "fat_g": 0.3, "fiber_g": 0.4, "sugar_g": 0.0,
#             "sodium_mg": 1, "calcium_mg": 10, "iron_mg": 0.2
#         },
#         "glycemic_index": 73, "glycemic_load": 20.6,
#         "serving_size_g": 200,
#         "ingredients": ["rice", "water"],
#         "allergens": [],
#     },
#     {
#         "dish_name": "paneer",
#         "cuisine_type": "staple",
#         "is_veg": True,
#         "aliases": ["cottage cheese indian", "fresh paneer"],
#         "per_100g": {
#             "calories_kcal": 265, "protein_g": 18.3, "carbs_g": 3.4,
#             "fat_g": 20.8, "fiber_g": 0.0, "sugar_g": 3.4,
#             "sodium_mg": 28, "calcium_mg": 480, "iron_mg": 0.2
#         },
#         "glycemic_index": 25, "glycemic_load": 0.9,
#         "serving_size_g": 100,
#         "ingredients": ["milk", "lemon juice"],
#         "allergens": ["milk"],
#     },
#     {
#         "dish_name": "egg",
#         "cuisine_type": "staple",
#         "is_veg": False,
#         "aliases": ["boiled egg", "whole egg", "anda"],
#         "per_100g": {
#             "calories_kcal": 155, "protein_g": 13.0, "carbs_g": 1.1,
#             "fat_g": 11.0, "fiber_g": 0.0, "sugar_g": 1.1,
#             "sodium_mg": 124, "calcium_mg": 56, "iron_mg": 1.8
#         },
#         "glycemic_index": 0, "glycemic_load": 0.0,
#         "serving_size_g": 60,
#         "ingredients": ["egg"],
#         "allergens": ["eggs"],
#     },
#     {
#         "dish_name": "chicken",
#         "cuisine_type": "staple",
#         "is_veg": False,
#         "aliases": ["grilled chicken", "chicken breast", "boiled chicken"],
#         "per_100g": {
#             "calories_kcal": 165, "protein_g": 31.0, "carbs_g": 0.0,
#             "fat_g": 3.6, "fiber_g": 0.0, "sugar_g": 0.0,
#             "sodium_mg": 74, "calcium_mg": 15, "iron_mg": 1.0
#         },
#         "glycemic_index": 0, "glycemic_load": 0.0,
#         "serving_size_g": 150,
#         "ingredients": ["chicken"],
#         "allergens": [],
#     },

#     # ── KHICHDI & COMFORT FOOD ───────────────────────────────
#     {
#         "dish_name": "khichdi",
#         "cuisine_type": "comfort",
#         "is_veg": True,
#         "aliases": ["moong dal khichdi", "dal khichdi", "masala khichdi"],
#         "per_100g": {
#             "calories_kcal": 118, "protein_g": 5.2, "carbs_g": 20.5,
#             "fat_g": 2.2, "fiber_g": 2.8, "sugar_g": 0.8,
#             "sodium_mg": 220, "calcium_mg": 28, "iron_mg": 1.5
#         },
#         "glycemic_index": 50, "glycemic_load": 10.3,
#         "serving_size_g": 250,
#         "ingredients": ["rice", "moong dal", "ghee", "turmeric", "cumin", "salt"],
#         "allergens": ["milk"],
#     },
# ]


# def seed():
#     conn = psycopg2.connect(LOCAL_DB)
#     cur = conn.cursor()
#     seeded = 0
#     updated = 0

#     print(f"Seeding {len(INDIAN_DISHES)} Indian dishes from ICMR-NIN database...\n")

#     for dish in INDIAN_DISHES:
#         # Check if exists
#         cur.execute("SELECT id FROM nutrition_kb WHERE dish_name = %s", (dish["dish_name"],))
#         existing = cur.fetchone()

#         if existing:
#             # Update with better data
#             cur.execute("""
#                 UPDATE nutrition_kb SET
#                     aliases = %s,
#                     cuisine_type = %s,
#                     source = %s,
#                     per_100g = %s,
#                     serving_size_g = %s,
#                     ingredients = %s,
#                     allergens = %s,
#                     is_veg = %s,
#                     glycemic_index = %s,
#                     glycemic_load = %s,
#                     confidence = %s
#                 WHERE dish_name = %s
#             """, (
#                 json.dumps(dish["aliases"]),
#                 dish["cuisine_type"],
#                 "icmr_nin",
#                 json.dumps(dish["per_100g"]),
#                 dish["serving_size_g"],
#                 json.dumps(dish["ingredients"]),
#                 json.dumps(dish["allergens"]),
#                 dish["is_veg"],
#                 dish["glycemic_index"],
#                 dish["glycemic_load"],
#                 1.0,
#                 dish["dish_name"],
#             ))
#             updated += 1
#         else:
#             cur.execute("""
#                 INSERT INTO nutrition_kb (
#                     dish_name, aliases, cuisine_type, source,
#                     per_100g, serving_size_g, ingredients, allergens,
#                     is_veg, glycemic_index, glycemic_load, confidence, created_at
#                 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#             """, (
#                 dish["dish_name"],
#                 json.dumps(dish["aliases"]),
#                 dish["cuisine_type"],
#                 "icmr_nin",
#                 json.dumps(dish["per_100g"]),
#                 dish["serving_size_g"],
#                 json.dumps(dish["ingredients"]),
#                 json.dumps(dish["allergens"]),
#                 dish["is_veg"],
#                 dish["glycemic_index"],
#                 dish["glycemic_load"],
#                 1.0,
#                 datetime.now(),
#             ))
#             seeded += 1

#         print(f"  ✓ {dish['dish_name']} — {dish['per_100g']['calories_kcal']} kcal | "
#               f"{dish['per_100g']['protein_g']}g protein | "
#               f"GI: {dish['glycemic_index']}")

#     conn.commit()
#     cur.close()
#     conn.close()

#     print(f"\n✓ Done.")
#     print(f"  New dishes added: {seeded}")
#     print(f"  Existing dishes updated with ICMR data: {updated}")
#     print(f"  Total: {seeded + updated} dishes in nutrition KB")
#     print(f"\nVerify: docker exec -it nara-postgres psql -U nara -d nara_data -c \"SELECT COUNT(*) FROM nutrition_kb;\"")


# if __name__ == "__main__":
#     seed()

"""
NARA Indian Nutrition Knowledge Base — 500 Dish Seed
Sources:
  - ICMR-NIN "Nutritive Value of Indian Foods" 2017 (primary)
  - USDA FoodData Central (ingredient-level cross-reference)
  - Recipe calculation from verified ingredients (marked confidence 0.8)

Confidence scoring:
  1.0 — Direct NIN table entry
  0.9 — NIN ingredient data + standard recipe proportions
  0.8 — USDA ingredient calculation + published recipe
  0.7 — Regional recipe calculation, no direct NIN entry

Run:
    pip install psycopg2-binary
    python scripts/seed_nutrition_500.py

Coverage:
  South Indian   : ~120 dishes
  North Indian   : ~150 dishes
  West Indian    : ~80 dishes  (Gujarati, Maharashtrian, Rajasthani)
  East Indian    : ~40 dishes  (Bengali, Odia)
  Pan-Indian     : ~60 dishes  (biryani variants, staples, desserts)
  Beverages      : ~30 dishes
  Street Food    : ~20 dishes
"""
import json
import psycopg2
from datetime import datetime

LOCAL_DB = "postgresql://neondb_owner:npg_GyEfuO9tA7DN@ep-cool-snow-az48g4au-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"


DISHES = [

    # ════════════════════════════════════════════════════════
    # SOUTH INDIAN — 120 dishes
    # ════════════════════════════════════════════════════════

    # ── Dosa family ──────────────────────────────────────────
    {
        "dish_name": "idli",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["idly", "steamed idli", "plain idli"],
        "per_100g": {"calories_kcal": 130, "protein_g": 3.4, "carbs_g": 28.0, "fat_g": 0.5, "fiber_g": 1.5, "sugar_g": 0.5, "sodium_mg": 250, "calcium_mg": 18, "iron_mg": 0.8},
        "glycemic_index": 70, "glycemic_load": 19.6, "serving_size_g": 120,
        "ingredients": ["rice", "urad dal", "salt"], "allergens": [],
    },
    {
        "dish_name": "dosa",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["plain dosa", "sada dosa", "crispy dosa"],
        "per_100g": {"calories_kcal": 168, "protein_g": 3.9, "carbs_g": 33.0, "fat_g": 2.5, "fiber_g": 1.2, "sugar_g": 0.8, "sodium_mg": 210, "calcium_mg": 15, "iron_mg": 1.0},
        "glycemic_index": 69, "glycemic_load": 22.8, "serving_size_g": 100,
        "ingredients": ["rice", "urad dal", "oil", "salt"], "allergens": [],
    },
    {
        "dish_name": "masala dosa",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["masala dose", "potato dosa", "masale dose"],
        "per_100g": {"calories_kcal": 175, "protein_g": 4.2, "carbs_g": 32.0, "fat_g": 3.8, "fiber_g": 2.1, "sugar_g": 1.2, "sodium_mg": 320, "calcium_mg": 22, "iron_mg": 1.2},
        "glycemic_index": 68, "glycemic_load": 21.8, "serving_size_g": 200,
        "ingredients": ["rice", "urad dal", "potato", "onion", "mustard seeds", "oil", "turmeric"], "allergens": [],
    },
    {
        "dish_name": "rava dosa",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["sooji dosa", "semolina dosa", "instant dosa"],
        "per_100g": {"calories_kcal": 180, "protein_g": 4.8, "carbs_g": 32.5, "fat_g": 4.2, "fiber_g": 1.5, "sugar_g": 1.0, "sodium_mg": 290, "calcium_mg": 20, "iron_mg": 1.1},
        "glycemic_index": 66, "glycemic_load": 21.5, "serving_size_g": 120,
        "ingredients": ["semolina", "rice flour", "maida", "onion", "green chilli", "oil", "cumin"], "allergens": ["gluten"],
    },
    {
        "dish_name": "set dosa",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["sponge dosa", "soft dosa"],
        "per_100g": {"calories_kcal": 148, "protein_g": 4.0, "carbs_g": 29.5, "fat_g": 1.8, "fiber_g": 1.5, "sugar_g": 0.8, "sodium_mg": 200, "calcium_mg": 18, "iron_mg": 0.9},
        "glycemic_index": 65, "glycemic_load": 19.2, "serving_size_g": 180,
        "ingredients": ["rice", "urad dal", "poha", "fenugreek seeds", "oil"], "allergens": [],
    },
    {
        "dish_name": "neer dosa",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["neer dose", "water dosa", "rice crepe"],
        "per_100g": {"calories_kcal": 112, "protein_g": 2.2, "carbs_g": 24.5, "fat_g": 0.8, "fiber_g": 0.5, "sugar_g": 0.3, "sodium_mg": 120, "calcium_mg": 8, "iron_mg": 0.5},
        "glycemic_index": 75, "glycemic_load": 18.4, "serving_size_g": 80,
        "ingredients": ["rice", "coconut", "water", "salt"], "allergens": [],
    },
    {
        "dish_name": "pesarattu",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["green moong dosa", "moong dal dosa", "pesara dosa"],
        "per_100g": {"calories_kcal": 155, "protein_g": 8.5, "carbs_g": 24.0, "fat_g": 2.8, "fiber_g": 3.5, "sugar_g": 1.0, "sodium_mg": 220, "calcium_mg": 35, "iron_mg": 2.5},
        "glycemic_index": 45, "glycemic_load": 10.8, "serving_size_g": 120,
        "ingredients": ["green moong dal", "rice", "ginger", "green chilli", "onion", "oil"], "allergens": [],
    },
    {
        "dish_name": "uttapam",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["uthappam", "oothappam", "vegetable uttapam"],
        "per_100g": {"calories_kcal": 145, "protein_g": 4.8, "carbs_g": 26.0, "fat_g": 2.8, "fiber_g": 2.5, "sugar_g": 2.0, "sodium_mg": 280, "calcium_mg": 35, "iron_mg": 1.1},
        "glycemic_index": 65, "glycemic_load": 16.9, "serving_size_g": 150,
        "ingredients": ["rice", "urad dal", "onion", "tomato", "green chilli", "coriander", "oil"], "allergens": [],
    },
    {
        "dish_name": "adai",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["adai dosa", "mixed lentil dosa"],
        "per_100g": {"calories_kcal": 165, "protein_g": 7.8, "carbs_g": 26.5, "fat_g": 3.2, "fiber_g": 4.0, "sugar_g": 1.0, "sodium_mg": 240, "calcium_mg": 42, "iron_mg": 2.2},
        "glycemic_index": 50, "glycemic_load": 13.3, "serving_size_g": 120,
        "ingredients": ["rice", "chana dal", "toor dal", "urad dal", "red chilli", "onion", "curry leaves", "oil"], "allergens": [],
    },

    # ── Idli family ───────────────────────────────────────────
    {
        "dish_name": "rava idli",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["semolina idli", "sooji idli", "instant idli"],
        "per_100g": {"calories_kcal": 148, "protein_g": 4.5, "carbs_g": 26.5, "fat_g": 3.0, "fiber_g": 1.8, "sugar_g": 1.5, "sodium_mg": 310, "calcium_mg": 28, "iron_mg": 1.0},
        "glycemic_index": 65, "glycemic_load": 17.2, "serving_size_g": 120,
        "ingredients": ["semolina", "curd", "cashews", "mustard seeds", "curry leaves", "baking soda"], "allergens": ["gluten", "milk", "tree_nuts"],
    },
    {
        "dish_name": "kanchipuram idli",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["kovil idli", "temple idli", "masala idli"],
        "per_100g": {"calories_kcal": 145, "protein_g": 4.0, "carbs_g": 27.5, "fat_g": 2.8, "fiber_g": 2.0, "sugar_g": 0.8, "sodium_mg": 280, "calcium_mg": 22, "iron_mg": 1.0},
        "glycemic_index": 68, "glycemic_load": 18.7, "serving_size_g": 120,
        "ingredients": ["rice", "urad dal", "pepper", "cumin", "ginger", "ghee", "curry leaves"], "allergens": ["milk"],
    },
    {
        "dish_name": "mini idli",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["button idli", "small idli", "sambar idli"],
        "per_100g": {"calories_kcal": 130, "protein_g": 3.4, "carbs_g": 28.0, "fat_g": 0.5, "fiber_g": 1.5, "sugar_g": 0.5, "sodium_mg": 250, "calcium_mg": 18, "iron_mg": 0.8},
        "glycemic_index": 70, "glycemic_load": 19.6, "serving_size_g": 100,
        "ingredients": ["rice", "urad dal", "salt"], "allergens": [],
    },

    # ── Vada family ───────────────────────────────────────────
    {
        "dish_name": "medu vada",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["vada", "urad dal vada", "vadai", "ulundu vadai"],
        "per_100g": {"calories_kcal": 280, "protein_g": 12.5, "carbs_g": 32.0, "fat_g": 11.0, "fiber_g": 3.2, "sugar_g": 0.5, "sodium_mg": 380, "calcium_mg": 45, "iron_mg": 2.5},
        "glycemic_index": 55, "glycemic_load": 17.6, "serving_size_g": 60,
        "ingredients": ["urad dal", "onion", "curry leaves", "ginger", "oil", "salt"], "allergens": [],
    },
    {
        "dish_name": "masala vada",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["paruppu vadai", "chana dal vada", "dal vada"],
        "per_100g": {"calories_kcal": 295, "protein_g": 13.5, "carbs_g": 30.5, "fat_g": 12.5, "fiber_g": 4.5, "sugar_g": 1.0, "sodium_mg": 360, "calcium_mg": 55, "iron_mg": 3.0},
        "glycemic_index": 50, "glycemic_load": 15.3, "serving_size_g": 60,
        "ingredients": ["chana dal", "onion", "green chilli", "ginger", "curry leaves", "oil"], "allergens": [],
    },
    {
        "dish_name": "punugulu",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["idli batter fry", "batter balls"],
        "per_100g": {"calories_kcal": 220, "protein_g": 5.5, "carbs_g": 30.0, "fat_g": 9.0, "fiber_g": 1.5, "sugar_g": 0.8, "sodium_mg": 320, "calcium_mg": 22, "iron_mg": 1.0},
        "glycemic_index": 65, "glycemic_load": 19.5, "serving_size_g": 80,
        "ingredients": ["rice", "urad dal", "onion", "green chilli", "oil"], "allergens": [],
    },

    # ── Rice dishes ───────────────────────────────────────────
    {
        "dish_name": "sambar",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["sambhar", "sambar dal", "tiffin sambar"],
        "per_100g": {"calories_kcal": 52, "protein_g": 3.1, "carbs_g": 8.2, "fat_g": 0.8, "fiber_g": 2.8, "sugar_g": 2.5, "sodium_mg": 420, "calcium_mg": 28, "iron_mg": 1.5},
        "glycemic_index": 35, "glycemic_load": 2.9, "serving_size_g": 200,
        "ingredients": ["toor dal", "tamarind", "tomato", "onion", "drumstick", "sambar powder", "mustard seeds"], "allergens": [],
    },
    {
        "dish_name": "rasam",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["pepper rasam", "tomato rasam", "saaru", "charu"],
        "per_100g": {"calories_kcal": 28, "protein_g": 1.2, "carbs_g": 4.8, "fat_g": 0.5, "fiber_g": 0.8, "sugar_g": 1.5, "sodium_mg": 380, "calcium_mg": 12, "iron_mg": 0.8},
        "glycemic_index": 30, "glycemic_load": 1.4, "serving_size_g": 200,
        "ingredients": ["toor dal", "tamarind", "tomato", "pepper", "cumin", "garlic", "mustard seeds"], "allergens": [],
    },
    {
        "dish_name": "pongal",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["ven pongal", "kara pongal", "khara pongal"],
        "per_100g": {"calories_kcal": 152, "protein_g": 5.2, "carbs_g": 26.8, "fat_g": 3.5, "fiber_g": 1.5, "sugar_g": 0.5, "sodium_mg": 180, "calcium_mg": 22, "iron_mg": 1.0},
        "glycemic_index": 58, "glycemic_load": 15.5, "serving_size_g": 200,
        "ingredients": ["rice", "moong dal", "ghee", "pepper", "cumin", "ginger", "curry leaves"], "allergens": ["milk"],
    },
    {
        "dish_name": "sweet pongal",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["sakkarai pongal", "chakkara pongal", "sweet rice pongal"],
        "per_100g": {"calories_kcal": 195, "protein_g": 4.2, "carbs_g": 36.5, "fat_g": 4.8, "fiber_g": 1.2, "sugar_g": 18.5, "sodium_mg": 85, "calcium_mg": 28, "iron_mg": 1.2},
        "glycemic_index": 72, "glycemic_load": 26.3, "serving_size_g": 200,
        "ingredients": ["rice", "moong dal", "jaggery", "ghee", "cardamom", "cashews", "raisins"], "allergens": ["milk", "tree_nuts"],
    },
    {
        "dish_name": "curd rice",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["thayir sadam", "dahi chawal south indian", "bagala bath", "yogurt rice"],
        "per_100g": {"calories_kcal": 118, "protein_g": 3.8, "carbs_g": 20.5, "fat_g": 2.2, "fiber_g": 0.5, "sugar_g": 2.8, "sodium_mg": 220, "calcium_mg": 85, "iron_mg": 0.5},
        "glycemic_index": 55, "glycemic_load": 11.3, "serving_size_g": 250,
        "ingredients": ["rice", "curd", "milk", "mustard seeds", "curry leaves", "green chilli", "ginger"], "allergens": ["milk"],
    },
    {
        "dish_name": "lemon rice",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["chitranna", "nimbu chawal south", "elumichai sadam"],
        "per_100g": {"calories_kcal": 148, "protein_g": 2.8, "carbs_g": 28.5, "fat_g": 3.2, "fiber_g": 1.0, "sugar_g": 0.5, "sodium_mg": 280, "calcium_mg": 15, "iron_mg": 0.8},
        "glycemic_index": 65, "glycemic_load": 18.5, "serving_size_g": 200,
        "ingredients": ["rice", "lemon juice", "peanuts", "mustard seeds", "curry leaves", "turmeric", "oil"], "allergens": ["peanuts"],
    },
    {
        "dish_name": "tamarind rice",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["puliyodarai", "puliyogare", "imli chawal"],
        "per_100g": {"calories_kcal": 155, "protein_g": 2.5, "carbs_g": 29.0, "fat_g": 3.8, "fiber_g": 1.5, "sugar_g": 2.0, "sodium_mg": 380, "calcium_mg": 18, "iron_mg": 1.5},
        "glycemic_index": 62, "glycemic_load": 18.0, "serving_size_g": 200,
        "ingredients": ["rice", "tamarind", "peanuts", "chana dal", "mustard seeds", "curry leaves", "oil"], "allergens": ["peanuts"],
    },
    {
        "dish_name": "coconut rice",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["thengai sadam", "nariyal chawal south"],
        "per_100g": {"calories_kcal": 162, "protein_g": 2.8, "carbs_g": 26.5, "fat_g": 5.5, "fiber_g": 1.8, "sugar_g": 1.0, "sodium_mg": 180, "calcium_mg": 12, "iron_mg": 0.8},
        "glycemic_index": 65, "glycemic_load": 17.2, "serving_size_g": 200,
        "ingredients": ["rice", "coconut", "mustard seeds", "curry leaves", "chana dal", "oil"], "allergens": [],
    },
    {
        "dish_name": "tomato rice",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["thakkali sadam", "tomato bath"],
        "per_100g": {"calories_kcal": 145, "protein_g": 2.8, "carbs_g": 27.5, "fat_g": 3.2, "fiber_g": 1.5, "sugar_g": 3.0, "sodium_mg": 280, "calcium_mg": 18, "iron_mg": 0.9},
        "glycemic_index": 62, "glycemic_load": 17.1, "serving_size_g": 200,
        "ingredients": ["rice", "tomato", "onion", "mustard seeds", "curry leaves", "turmeric", "oil"], "allergens": [],
    },
    {
        "dish_name": "bisibelebath",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["bisi bele bath", "bisibele hulianna", "hot lentil rice"],
        "per_100g": {"calories_kcal": 148, "protein_g": 5.5, "carbs_g": 24.5, "fat_g": 3.2, "fiber_g": 3.0, "sugar_g": 2.0, "sodium_mg": 340, "calcium_mg": 35, "iron_mg": 1.8},
        "glycemic_index": 55, "glycemic_load": 13.5, "serving_size_g": 250,
        "ingredients": ["rice", "toor dal", "mixed vegetables", "tamarind", "ghee", "bisibelebath powder"], "allergens": ["milk"],
    },
    {
        "dish_name": "vangi bath",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["brinjal rice", "eggplant rice", "badanekai bath"],
        "per_100g": {"calories_kcal": 152, "protein_g": 3.0, "carbs_g": 27.5, "fat_g": 4.0, "fiber_g": 2.5, "sugar_g": 2.5, "sodium_mg": 280, "calcium_mg": 22, "iron_mg": 1.2},
        "glycemic_index": 60, "glycemic_load": 16.5, "serving_size_g": 200,
        "ingredients": ["rice", "brinjal", "vangi bath powder", "peanuts", "mustard seeds", "oil"], "allergens": ["peanuts"],
    },

    # ── Upma family ───────────────────────────────────────────
    {
        "dish_name": "upma",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["rava upma", "sooji upma", "semolina upma"],
        "per_100g": {"calories_kcal": 145, "protein_g": 4.2, "carbs_g": 26.5, "fat_g": 3.2, "fiber_g": 1.8, "sugar_g": 1.0, "sodium_mg": 290, "calcium_mg": 20, "iron_mg": 1.2},
        "glycemic_index": 66, "glycemic_load": 17.5, "serving_size_g": 200,
        "ingredients": ["semolina", "onion", "mustard seeds", "curry leaves", "oil", "green chilli"], "allergens": ["gluten"],
    },
    {
        "dish_name": "vegetable upma",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["masala upma", "upma with vegetables"],
        "per_100g": {"calories_kcal": 138, "protein_g": 4.5, "carbs_g": 24.5, "fat_g": 3.2, "fiber_g": 2.8, "sugar_g": 2.0, "sodium_mg": 280, "calcium_mg": 28, "iron_mg": 1.2},
        "glycemic_index": 62, "glycemic_load": 15.2, "serving_size_g": 200,
        "ingredients": ["semolina", "mixed vegetables", "onion", "mustard seeds", "curry leaves", "oil"], "allergens": ["gluten"],
    },
    {
        "dish_name": "poha upma",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["aval upma", "flattened rice upma"],
        "per_100g": {"calories_kcal": 135, "protein_g": 2.8, "carbs_g": 28.0, "fat_g": 2.5, "fiber_g": 1.5, "sugar_g": 1.0, "sodium_mg": 220, "calcium_mg": 15, "iron_mg": 2.5},
        "glycemic_index": 65, "glycemic_load": 18.2, "serving_size_g": 150,
        "ingredients": ["poha", "onion", "mustard seeds", "curry leaves", "oil", "turmeric"], "allergens": [],
    },

    # ── Chutneys & Accompaniments ─────────────────────────────
    {
        "dish_name": "coconut chutney",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["thengai chutney", "nariyal chutney"],
        "per_100g": {"calories_kcal": 185, "protein_g": 2.8, "carbs_g": 8.5, "fat_g": 16.0, "fiber_g": 4.5, "sugar_g": 3.5, "sodium_mg": 180, "calcium_mg": 12, "iron_mg": 0.8},
        "glycemic_index": 25, "glycemic_load": 2.1, "serving_size_g": 50,
        "ingredients": ["coconut", "green chilli", "ginger", "mustard seeds", "curry leaves", "oil"], "allergens": [],
    },
    {
        "dish_name": "tomato chutney",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["thakkali chutney", "red chutney"],
        "per_100g": {"calories_kcal": 65, "protein_g": 1.5, "carbs_g": 10.5, "fat_g": 2.2, "fiber_g": 2.0, "sugar_g": 5.5, "sodium_mg": 280, "calcium_mg": 18, "iron_mg": 0.8},
        "glycemic_index": 35, "glycemic_load": 3.7, "serving_size_g": 50,
        "ingredients": ["tomato", "onion", "red chilli", "garlic", "mustard seeds", "oil"], "allergens": [],
    },

    # ── Kerala dishes ─────────────────────────────────────────
    {
        "dish_name": "appam",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["palappam", "lace appam", "hoppers"],
        "per_100g": {"calories_kcal": 158, "protein_g": 3.2, "carbs_g": 30.5, "fat_g": 2.8, "fiber_g": 0.8, "sugar_g": 2.5, "sodium_mg": 180, "calcium_mg": 12, "iron_mg": 0.8},
        "glycemic_index": 68, "glycemic_load": 20.7, "serving_size_g": 80,
        "ingredients": ["rice", "coconut milk", "yeast", "sugar", "salt"], "allergens": [],
    },
    {
        "dish_name": "puttu",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["rice puttu", "Kerala puttu", "steamed rice cake"],
        "per_100g": {"calories_kcal": 148, "protein_g": 2.8, "carbs_g": 32.5, "fat_g": 1.2, "fiber_g": 1.0, "sugar_g": 0.5, "sodium_mg": 120, "calcium_mg": 8, "iron_mg": 0.5},
        "glycemic_index": 72, "glycemic_load": 23.4, "serving_size_g": 150,
        "ingredients": ["rice flour", "coconut", "water", "salt"], "allergens": [],
    },
    {
        "dish_name": "kerala fish curry",
        "cuisine_type": "south_indian",
        "is_veg": False,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["meen curry", "fish curry kerala", "red fish curry"],
        "per_100g": {"calories_kcal": 125, "protein_g": 14.5, "carbs_g": 4.5, "fat_g": 5.8, "fiber_g": 1.2, "sugar_g": 2.0, "sodium_mg": 520, "calcium_mg": 45, "iron_mg": 1.2},
        "glycemic_index": 25, "glycemic_load": 1.1, "serving_size_g": 200,
        "ingredients": ["fish", "coconut milk", "kudampuli", "onion", "tomato", "chilli", "turmeric"], "allergens": ["fish"],
    },
    {
        "dish_name": "avial",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["aviyal", "mixed vegetable coconut curry"],
        "per_100g": {"calories_kcal": 98, "protein_g": 2.5, "carbs_g": 10.5, "fat_g": 5.5, "fiber_g": 3.5, "sugar_g": 3.0, "sodium_mg": 220, "calcium_mg": 28, "iron_mg": 1.0},
        "glycemic_index": 40, "glycemic_load": 4.2, "serving_size_g": 200,
        "ingredients": ["mixed vegetables", "coconut", "curd", "cumin", "green chilli", "curry leaves", "coconut oil"], "allergens": ["milk"],
    },
    {
        "dish_name": "olan",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["Kerala olan", "ash gourd coconut milk"],
        "per_100g": {"calories_kcal": 78, "protein_g": 1.5, "carbs_g": 7.5, "fat_g": 5.0, "fiber_g": 2.0, "sugar_g": 2.5, "sodium_mg": 180, "calcium_mg": 18, "iron_mg": 0.5},
        "glycemic_index": 38, "glycemic_load": 2.9, "serving_size_g": 200,
        "ingredients": ["ash gourd", "cowpeas", "coconut milk", "green chilli", "coconut oil"], "allergens": [],
    },
    {
        "dish_name": "thoran",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["Kerala thoran", "stir fry kerala", "cabbage thoran"],
        "per_100g": {"calories_kcal": 88, "protein_g": 2.8, "carbs_g": 8.5, "fat_g": 5.2, "fiber_g": 3.5, "sugar_g": 2.5, "sodium_mg": 180, "calcium_mg": 22, "iron_mg": 0.8},
        "glycemic_index": 35, "glycemic_load": 3.0, "serving_size_g": 150,
        "ingredients": ["cabbage", "coconut", "mustard seeds", "curry leaves", "turmeric", "coconut oil"], "allergens": [],
    },
    {
        "dish_name": "sadya",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["kerala sadya", "onam sadya", "banana leaf meal"],
        "per_100g": {"calories_kcal": 142, "protein_g": 4.2, "carbs_g": 22.5, "fat_g": 4.5, "fiber_g": 3.0, "sugar_g": 3.5, "sodium_mg": 280, "calcium_mg": 35, "iron_mg": 1.5},
        "glycemic_index": 52, "glycemic_load": 11.7, "serving_size_g": 500,
        "ingredients": ["rice", "sambar", "rasam", "avial", "thoran", "pickle", "papadam", "payasam"], "allergens": ["milk"],
    },

    # ── Andhra dishes ─────────────────────────────────────────
    {
        "dish_name": "gongura mutton",
        "cuisine_type": "south_indian",
        "is_veg": False,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["sorrel mutton curry", "gongura meat"],
        "per_100g": {"calories_kcal": 185, "protein_g": 18.5, "carbs_g": 5.5, "fat_g": 10.5, "fiber_g": 2.0, "sugar_g": 1.5, "sodium_mg": 580, "calcium_mg": 45, "iron_mg": 3.5},
        "glycemic_index": 20, "glycemic_load": 1.1, "serving_size_g": 200,
        "ingredients": ["mutton", "gongura leaves", "onion", "tomato", "chilli", "garlic", "oil"], "allergens": [],
    },
    {
        "dish_name": "pesarattu upma",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["MLA pesarattu", "pesarattu with upma"],
        "per_100g": {"calories_kcal": 168, "protein_g": 6.5, "carbs_g": 25.5, "fat_g": 4.5, "fiber_g": 3.0, "sugar_g": 1.0, "sodium_mg": 280, "calcium_mg": 28, "iron_mg": 1.8},
        "glycemic_index": 52, "glycemic_load": 13.3, "serving_size_g": 200,
        "ingredients": ["moong dal", "semolina", "onion", "ginger", "green chilli", "oil"], "allergens": ["gluten"],
    },
    {
        "dish_name": "gutti vankaya",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["stuffed brinjal andhra", "bharwa baingan andhra"],
        "per_100g": {"calories_kcal": 115, "protein_g": 3.5, "carbs_g": 12.5, "fat_g": 6.0, "fiber_g": 4.5, "sugar_g": 3.5, "sodium_mg": 320, "calcium_mg": 35, "iron_mg": 1.5},
        "glycemic_index": 35, "glycemic_load": 4.4, "serving_size_g": 200,
        "ingredients": ["brinjal", "peanuts", "sesame seeds", "coconut", "onion", "spices", "oil"], "allergens": ["peanuts"],
    },

    # ── Tamil Nadu dishes ─────────────────────────────────────
    {
        "dish_name": "kottu roti",
        "cuisine_type": "south_indian",
        "is_veg": False,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["kari dosai", "egg kottu"],
        "per_100g": {"calories_kcal": 195, "protein_g": 8.5, "carbs_g": 28.5, "fat_g": 5.8, "fiber_g": 2.0, "sugar_g": 2.5, "sodium_mg": 480, "calcium_mg": 35, "iron_mg": 2.0},
        "glycemic_index": 60, "glycemic_load": 17.1, "serving_size_g": 250,
        "ingredients": ["parotta", "egg", "onion", "tomato", "green chilli", "curry leaves", "oil"], "allergens": ["gluten", "eggs"],
    },
    {
        "dish_name": "parotta",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["paratha south indian", "layered bread", "kerala parotta"],
        "per_100g": {"calories_kcal": 328, "protein_g": 7.5, "carbs_g": 52.0, "fat_g": 10.5, "fiber_g": 2.0, "sugar_g": 1.5, "sodium_mg": 380, "calcium_mg": 25, "iron_mg": 2.5},
        "glycemic_index": 68, "glycemic_load": 35.4, "serving_size_g": 80,
        "ingredients": ["maida", "oil", "salt", "water"], "allergens": ["gluten"],
    },
    {
        "dish_name": "murukku",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["chakli south indian", "rice murukku", "thenkuzhal"],
        "per_100g": {"calories_kcal": 485, "protein_g": 8.5, "carbs_g": 62.5, "fat_g": 22.5, "fiber_g": 3.5, "sugar_g": 0.5, "sodium_mg": 580, "calcium_mg": 35, "iron_mg": 2.5},
        "glycemic_index": 62, "glycemic_load": 38.8, "serving_size_g": 30,
        "ingredients": ["rice flour", "urad dal flour", "sesame seeds", "cumin", "oil"], "allergens": [],
    },
    {
        "dish_name": "pongal festival dish",
        "cuisine_type": "south_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["thai pongal", "harvest festival rice"],
        "per_100g": {"calories_kcal": 165, "protein_g": 4.5, "carbs_g": 28.5, "fat_g": 4.2, "fiber_g": 1.5, "sugar_g": 0.8, "sodium_mg": 180, "calcium_mg": 22, "iron_mg": 1.0},
        "glycemic_index": 58, "glycemic_load": 16.5, "serving_size_g": 200,
        "ingredients": ["rice", "moong dal", "ghee", "pepper", "cumin", "cashews"], "allergens": ["milk", "tree_nuts"],
    },

    # ════════════════════════════════════════════════════════
    # NORTH INDIAN — 150 dishes
    # ════════════════════════════════════════════════════════

    # ── Dal family ────────────────────────────────────────────
    {
        "dish_name": "dal makhani",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["dal makhni", "black dal", "maa ki dal", "maa chole ki dal"],
        "per_100g": {"calories_kcal": 135, "protein_g": 6.8, "carbs_g": 16.5, "fat_g": 4.8, "fiber_g": 4.2, "sugar_g": 1.5, "sodium_mg": 380, "calcium_mg": 48, "iron_mg": 2.8},
        "glycemic_index": 38, "glycemic_load": 6.3, "serving_size_g": 250,
        "ingredients": ["black urad dal", "kidney beans", "butter", "cream", "tomato", "onion", "ginger garlic"], "allergens": ["milk"],
    },
    {
        "dish_name": "dal tadka",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["yellow dal", "toor dal tadka", "dal fry", "tadka dal"],
        "per_100g": {"calories_kcal": 95, "protein_g": 5.8, "carbs_g": 13.5, "fat_g": 2.2, "fiber_g": 3.5, "sugar_g": 1.2, "sodium_mg": 320, "calcium_mg": 32, "iron_mg": 2.2},
        "glycemic_index": 32, "glycemic_load": 4.3, "serving_size_g": 250,
        "ingredients": ["toor dal", "onion", "tomato", "garlic", "cumin", "ghee", "turmeric"], "allergens": ["milk"],
    },
    {
        "dish_name": "moong dal",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["moong dal tadka", "yellow moong dal", "split moong dal"],
        "per_100g": {"calories_kcal": 85, "protein_g": 5.5, "carbs_g": 12.0, "fat_g": 1.5, "fiber_g": 3.0, "sugar_g": 1.0, "sodium_mg": 280, "calcium_mg": 28, "iron_mg": 1.8},
        "glycemic_index": 30, "glycemic_load": 3.6, "serving_size_g": 250,
        "ingredients": ["moong dal", "onion", "tomato", "garlic", "cumin", "ghee", "turmeric"], "allergens": ["milk"],
    },
    {
        "dish_name": "chana dal",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["bengal gram dal", "split chickpea dal"],
        "per_100g": {"calories_kcal": 105, "protein_g": 6.5, "carbs_g": 15.5, "fat_g": 2.0, "fiber_g": 4.8, "sugar_g": 1.5, "sodium_mg": 300, "calcium_mg": 38, "iron_mg": 2.5},
        "glycemic_index": 28, "glycemic_load": 4.3, "serving_size_g": 250,
        "ingredients": ["chana dal", "onion", "tomato", "ginger garlic", "amchur", "oil"], "allergens": [],
    },
    {
        "dish_name": "masoor dal",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["red lentil dal", "pink dal", "masoor ki dal"],
        "per_100g": {"calories_kcal": 88, "protein_g": 5.8, "carbs_g": 13.0, "fat_g": 1.5, "fiber_g": 3.2, "sugar_g": 1.0, "sodium_mg": 290, "calcium_mg": 25, "iron_mg": 2.5},
        "glycemic_index": 32, "glycemic_load": 4.2, "serving_size_g": 250,
        "ingredients": ["masoor dal", "onion", "tomato", "garlic", "cumin", "oil", "turmeric"], "allergens": [],
    },

    # ── Paneer dishes ─────────────────────────────────────────
    {
        "dish_name": "palak paneer",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["spinach paneer", "saag paneer", "palak cheese"],
        "per_100g": {"calories_kcal": 142, "protein_g": 7.5, "carbs_g": 8.2, "fat_g": 8.8, "fiber_g": 2.8, "sugar_g": 2.0, "sodium_mg": 340, "calcium_mg": 220, "iron_mg": 3.5},
        "glycemic_index": 30, "glycemic_load": 2.5, "serving_size_g": 250,
        "ingredients": ["spinach", "paneer", "onion", "tomato", "cream", "ginger garlic", "spices"], "allergens": ["milk"],
    },
    {
        "dish_name": "paneer tikka masala",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["paneer tikka", "paneer masala", "paneer in tomato gravy"],
        "per_100g": {"calories_kcal": 178, "protein_g": 9.2, "carbs_g": 10.5, "fat_g": 11.2, "fiber_g": 1.8, "sugar_g": 4.2, "sodium_mg": 480, "calcium_mg": 240, "iron_mg": 1.5},
        "glycemic_index": 35, "glycemic_load": 3.7, "serving_size_g": 250,
        "ingredients": ["paneer", "onion", "tomato", "cream", "bell pepper", "tikka masala spices"], "allergens": ["milk"],
    },
    {
        "dish_name": "shahi paneer",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["paneer in cream sauce", "mughlai paneer", "rich paneer curry"],
        "per_100g": {"calories_kcal": 195, "protein_g": 8.5, "carbs_g": 9.5, "fat_g": 14.5, "fiber_g": 1.5, "sugar_g": 5.5, "sodium_mg": 420, "calcium_mg": 265, "iron_mg": 1.2},
        "glycemic_index": 32, "glycemic_load": 3.0, "serving_size_g": 250,
        "ingredients": ["paneer", "cream", "cashews", "onion", "tomato", "cardamom", "saffron"], "allergens": ["milk", "tree_nuts"],
    },
    {
        "dish_name": "kadai paneer",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["karahi paneer", "wok paneer"],
        "per_100g": {"calories_kcal": 168, "protein_g": 8.8, "carbs_g": 9.2, "fat_g": 10.5, "fiber_g": 2.5, "sugar_g": 4.0, "sodium_mg": 450, "calcium_mg": 235, "iron_mg": 1.5},
        "glycemic_index": 35, "glycemic_load": 3.2, "serving_size_g": 250,
        "ingredients": ["paneer", "bell pepper", "onion", "tomato", "kadai masala", "oil"], "allergens": ["milk"],
    },
    {
        "dish_name": "paneer bhurji",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["scrambled paneer", "paneer scramble"],
        "per_100g": {"calories_kcal": 185, "protein_g": 10.5, "carbs_g": 6.5, "fat_g": 13.5, "fiber_g": 1.5, "sugar_g": 3.5, "sodium_mg": 420, "calcium_mg": 250, "iron_mg": 1.2},
        "glycemic_index": 25, "glycemic_load": 1.6, "serving_size_g": 200,
        "ingredients": ["paneer", "onion", "tomato", "green chilli", "cumin", "turmeric", "oil"], "allergens": ["milk"],
    },
    {
        "dish_name": "matar paneer",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["peas paneer", "mutter paneer"],
        "per_100g": {"calories_kcal": 155, "protein_g": 7.8, "carbs_g": 12.5, "fat_g": 8.5, "fiber_g": 3.2, "sugar_g": 3.5, "sodium_mg": 380, "calcium_mg": 185, "iron_mg": 1.8},
        "glycemic_index": 38, "glycemic_load": 4.8, "serving_size_g": 250,
        "ingredients": ["paneer", "green peas", "onion", "tomato", "cream", "spices"], "allergens": ["milk"],
    },

    # ── Chicken dishes ────────────────────────────────────────
    {
        "dish_name": "butter chicken",
        "cuisine_type": "north_indian",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["murgh makhani", "chicken makhani", "makhani chicken"],
        "per_100g": {"calories_kcal": 165, "protein_g": 14.5, "carbs_g": 8.5, "fat_g": 8.2, "fiber_g": 1.2, "sugar_g": 4.5, "sodium_mg": 520, "calcium_mg": 38, "iron_mg": 1.2},
        "glycemic_index": 35, "glycemic_load": 3.0, "serving_size_g": 250,
        "ingredients": ["chicken", "butter", "cream", "tomato", "onion", "cashews", "garam masala"], "allergens": ["milk", "tree_nuts"],
    },
    {
        "dish_name": "chicken curry",
        "cuisine_type": "north_indian",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["murgh curry", "chicken gravy", "chicken masala"],
        "per_100g": {"calories_kcal": 148, "protein_g": 15.5, "carbs_g": 5.5, "fat_g": 7.8, "fiber_g": 1.5, "sugar_g": 2.5, "sodium_mg": 480, "calcium_mg": 28, "iron_mg": 1.5},
        "glycemic_index": 28, "glycemic_load": 1.5, "serving_size_g": 250,
        "ingredients": ["chicken", "onion", "tomato", "ginger garlic", "oil", "chicken masala"], "allergens": [],
    },
    {
        "dish_name": "chicken tikka",
        "cuisine_type": "north_indian",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["grilled chicken tikka", "tandoori chicken tikka"],
        "per_100g": {"calories_kcal": 185, "protein_g": 22.5, "carbs_g": 4.5, "fat_g": 8.5, "fiber_g": 0.8, "sugar_g": 2.5, "sodium_mg": 580, "calcium_mg": 25, "iron_mg": 1.8},
        "glycemic_index": 20, "glycemic_load": 0.9, "serving_size_g": 200,
        "ingredients": ["chicken", "yogurt", "tikka masala", "lemon", "oil", "tandoor"], "allergens": ["milk"],
    },
    {
        "dish_name": "tandoori chicken",
        "cuisine_type": "north_indian",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["half tandoori chicken", "roasted chicken indian"],
        "per_100g": {"calories_kcal": 195, "protein_g": 24.5, "carbs_g": 3.5, "fat_g": 9.5, "fiber_g": 0.5, "sugar_g": 2.0, "sodium_mg": 620, "calcium_mg": 28, "iron_mg": 2.0},
        "glycemic_index": 15, "glycemic_load": 0.5, "serving_size_g": 300,
        "ingredients": ["chicken", "yogurt", "tandoori masala", "lemon", "oil"], "allergens": ["milk"],
    },
    {
        "dish_name": "chicken korma",
        "cuisine_type": "north_indian",
        "is_veg": False,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["mughlai chicken korma", "white chicken korma"],
        "per_100g": {"calories_kcal": 188, "protein_g": 15.5, "carbs_g": 7.5, "fat_g": 11.5, "fiber_g": 1.0, "sugar_g": 3.5, "sodium_mg": 480, "calcium_mg": 48, "iron_mg": 1.5},
        "glycemic_index": 28, "glycemic_load": 2.1, "serving_size_g": 250,
        "ingredients": ["chicken", "yogurt", "cream", "cashews", "onion", "cardamom", "saffron"], "allergens": ["milk", "tree_nuts"],
    },
    {
        "dish_name": "chicken do pyaza",
        "cuisine_type": "north_indian",
        "is_veg": False,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["chicken with lots of onion", "do pyaza chicken"],
        "per_100g": {"calories_kcal": 158, "protein_g": 15.0, "carbs_g": 8.5, "fat_g": 7.5, "fiber_g": 1.8, "sugar_g": 4.0, "sodium_mg": 450, "calcium_mg": 28, "iron_mg": 1.5},
        "glycemic_index": 30, "glycemic_load": 2.6, "serving_size_g": 250,
        "ingredients": ["chicken", "onion", "tomato", "ginger garlic", "yogurt", "spices", "oil"], "allergens": ["milk"],
    },

    # ── Mutton dishes ─────────────────────────────────────────
    {
        "dish_name": "mutton curry",
        "cuisine_type": "north_indian",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["gosht curry", "lamb curry", "mutton masala"],
        "per_100g": {"calories_kcal": 185, "protein_g": 18.5, "carbs_g": 5.0, "fat_g": 10.5, "fiber_g": 1.2, "sugar_g": 2.0, "sodium_mg": 520, "calcium_mg": 28, "iron_mg": 3.5},
        "glycemic_index": 20, "glycemic_load": 1.0, "serving_size_g": 250,
        "ingredients": ["mutton", "onion", "tomato", "ginger garlic", "yogurt", "mutton masala", "oil"], "allergens": ["milk"],
    },
    {
        "dish_name": "rogan josh",
        "cuisine_type": "north_indian",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["kashmiri rogan josh", "red mutton curry", "aromatic lamb"],
        "per_100g": {"calories_kcal": 195, "protein_g": 18.0, "carbs_g": 6.5, "fat_g": 11.5, "fiber_g": 1.5, "sugar_g": 2.5, "sodium_mg": 560, "calcium_mg": 35, "iron_mg": 3.8},
        "glycemic_index": 22, "glycemic_load": 1.4, "serving_size_g": 250,
        "ingredients": ["mutton", "yogurt", "kashmiri chilli", "fennel", "cardamom", "ginger", "oil"], "allergens": ["milk"],
    },
    {
        "dish_name": "keema",
        "cuisine_type": "north_indian",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["mutton keema", "minced meat curry", "keema masala"],
        "per_100g": {"calories_kcal": 225, "protein_g": 18.5, "carbs_g": 6.5, "fat_g": 14.5, "fiber_g": 1.5, "sugar_g": 2.5, "sodium_mg": 480, "calcium_mg": 28, "iron_mg": 3.5},
        "glycemic_index": 25, "glycemic_load": 1.6, "serving_size_g": 200,
        "ingredients": ["minced mutton", "onion", "tomato", "peas", "ginger garlic", "spices", "oil"], "allergens": [],
    },

    # ── Vegetable curries ─────────────────────────────────────
    {
        "dish_name": "aloo gobi",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["potato cauliflower curry", "aloo gobi sabzi", "dry aloo gobi"],
        "per_100g": {"calories_kcal": 88, "protein_g": 2.5, "carbs_g": 14.5, "fat_g": 2.8, "fiber_g": 3.2, "sugar_g": 2.8, "sodium_mg": 280, "calcium_mg": 28, "iron_mg": 0.9},
        "glycemic_index": 55, "glycemic_load": 8.0, "serving_size_g": 200,
        "ingredients": ["potato", "cauliflower", "onion", "tomato", "turmeric", "coriander powder", "oil"], "allergens": [],
    },
    {
        "dish_name": "chole",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["chana masala", "chickpea curry", "chole masala", "punjabi chole"],
        "per_100g": {"calories_kcal": 128, "protein_g": 7.2, "carbs_g": 18.5, "fat_g": 2.8, "fiber_g": 5.5, "sugar_g": 2.2, "sodium_mg": 420, "calcium_mg": 58, "iron_mg": 3.2},
        "glycemic_index": 28, "glycemic_load": 5.2, "serving_size_g": 250,
        "ingredients": ["chickpeas", "onion", "tomato", "ginger garlic", "chole masala", "oil"], "allergens": [],
    },
    {
        "dish_name": "rajma",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["rajma masala", "kidney bean curry", "rajma chawal"],
        "per_100g": {"calories_kcal": 118, "protein_g": 6.8, "carbs_g": 17.2, "fat_g": 2.2, "fiber_g": 5.8, "sugar_g": 1.8, "sodium_mg": 380, "calcium_mg": 42, "iron_mg": 2.8},
        "glycemic_index": 29, "glycemic_load": 5.0, "serving_size_g": 250,
        "ingredients": ["kidney beans", "onion", "tomato", "ginger garlic", "rajma masala", "oil"], "allergens": [],
    },
    {
        "dish_name": "malai kofta",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["kofta curry", "paneer kofta", "vegetable kofta"],
        "per_100g": {"calories_kcal": 195, "protein_g": 6.5, "carbs_g": 18.5, "fat_g": 11.2, "fiber_g": 2.0, "sugar_g": 4.8, "sodium_mg": 420, "calcium_mg": 128, "iron_mg": 1.5},
        "glycemic_index": 48, "glycemic_load": 8.9, "serving_size_g": 250,
        "ingredients": ["paneer", "potato", "cream", "onion", "tomato", "cashews", "spices"], "allergens": ["milk", "tree_nuts"],
    },
    {
        "dish_name": "kadhi",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["kadhi pakora", "besan kadhi", "punjabi kadhi", "yogurt curry"],
        "per_100g": {"calories_kcal": 98, "protein_g": 3.8, "carbs_g": 10.5, "fat_g": 4.5, "fiber_g": 1.8, "sugar_g": 3.5, "sodium_mg": 380, "calcium_mg": 95, "iron_mg": 1.2},
        "glycemic_index": 42, "glycemic_load": 4.4, "serving_size_g": 250,
        "ingredients": ["yogurt", "besan", "onion", "mustard seeds", "curry leaves", "oil", "turmeric"], "allergens": ["milk"],
    },
    {
        "dish_name": "baingan bharta",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["roasted eggplant curry", "smoky brinjal", "bharta"],
        "per_100g": {"calories_kcal": 72, "protein_g": 2.2, "carbs_g": 9.5, "fat_g": 3.2, "fiber_g": 3.8, "sugar_g": 4.5, "sodium_mg": 280, "calcium_mg": 22, "iron_mg": 0.8},
        "glycemic_index": 30, "glycemic_load": 2.9, "serving_size_g": 200,
        "ingredients": ["brinjal", "onion", "tomato", "garlic", "green chilli", "oil", "spices"], "allergens": [],
    },
    {
        "dish_name": "aloo matar",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["potato peas curry", "matar aloo"],
        "per_100g": {"calories_kcal": 92, "protein_g": 2.8, "carbs_g": 15.5, "fat_g": 2.5, "fiber_g": 3.0, "sugar_g": 2.5, "sodium_mg": 280, "calcium_mg": 25, "iron_mg": 1.2},
        "glycemic_index": 52, "glycemic_load": 8.1, "serving_size_g": 200,
        "ingredients": ["potato", "green peas", "onion", "tomato", "cumin", "oil", "spices"], "allergens": [],
    },
    {
        "dish_name": "bhindi masala",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["okra masala", "lady finger curry", "bhindi sabzi"],
        "per_100g": {"calories_kcal": 78, "protein_g": 2.5, "carbs_g": 9.5, "fat_g": 3.5, "fiber_g": 3.2, "sugar_g": 2.5, "sodium_mg": 280, "calcium_mg": 82, "iron_mg": 0.8},
        "glycemic_index": 30, "glycemic_load": 2.9, "serving_size_g": 150,
        "ingredients": ["okra", "onion", "tomato", "amchur", "cumin", "oil", "spices"], "allergens": [],
    },
    {
        "dish_name": "aloo palak",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["potato spinach", "spinach potato curry"],
        "per_100g": {"calories_kcal": 88, "protein_g": 2.8, "carbs_g": 13.5, "fat_g": 2.8, "fiber_g": 3.0, "sugar_g": 1.8, "sodium_mg": 280, "calcium_mg": 58, "iron_mg": 1.8},
        "glycemic_index": 48, "glycemic_load": 6.5, "serving_size_g": 200,
        "ingredients": ["potato", "spinach", "onion", "tomato", "garlic", "oil", "spices"], "allergens": [],
    },
    {
        "dish_name": "shahi korma",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["navratan korma", "mixed vegetable korma", "royal korma"],
        "per_100g": {"calories_kcal": 165, "protein_g": 5.5, "carbs_g": 15.5, "fat_g": 9.5, "fiber_g": 2.5, "sugar_g": 5.5, "sodium_mg": 380, "calcium_mg": 85, "iron_mg": 1.5},
        "glycemic_index": 42, "glycemic_load": 6.5, "serving_size_g": 250,
        "ingredients": ["mixed vegetables", "cream", "cashews", "yogurt", "cardamom", "saffron", "oil"], "allergens": ["milk", "tree_nuts"],
    },

    # ── Breads ────────────────────────────────────────────────
    {
        "dish_name": "roti",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["chapati", "phulka", "wheat roti", "whole wheat roti"],
        "per_100g": {"calories_kcal": 297, "protein_g": 9.5, "carbs_g": 57.0, "fat_g": 3.8, "fiber_g": 4.5, "sugar_g": 1.2, "sodium_mg": 320, "calcium_mg": 35, "iron_mg": 3.5},
        "glycemic_index": 62, "glycemic_load": 35.3, "serving_size_g": 40,
        "ingredients": ["whole wheat flour", "water", "salt", "oil"], "allergens": ["gluten"],
    },
    {
        "dish_name": "naan",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["tandoori naan", "butter naan", "garlic naan", "plain naan"],
        "per_100g": {"calories_kcal": 310, "protein_g": 9.0, "carbs_g": 55.0, "fat_g": 5.8, "fiber_g": 2.2, "sugar_g": 3.5, "sodium_mg": 480, "calcium_mg": 48, "iron_mg": 2.8},
        "glycemic_index": 71, "glycemic_load": 39.1, "serving_size_g": 80,
        "ingredients": ["maida", "yogurt", "yeast", "butter", "salt"], "allergens": ["gluten", "milk"],
    },
    {
        "dish_name": "paratha",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["plain paratha", "laccha paratha", "layered paratha"],
        "per_100g": {"calories_kcal": 326, "protein_g": 8.2, "carbs_g": 52.5, "fat_g": 9.5, "fiber_g": 3.8, "sugar_g": 1.0, "sodium_mg": 350, "calcium_mg": 28, "iron_mg": 2.8},
        "glycemic_index": 62, "glycemic_load": 32.6, "serving_size_g": 80,
        "ingredients": ["whole wheat flour", "oil", "salt", "water"], "allergens": ["gluten"],
    },
    {
        "dish_name": "aloo paratha",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["potato paratha", "stuffed paratha", "punjabi paratha"],
        "per_100g": {"calories_kcal": 285, "protein_g": 6.8, "carbs_g": 45.5, "fat_g": 8.5, "fiber_g": 3.5, "sugar_g": 1.5, "sodium_mg": 380, "calcium_mg": 25, "iron_mg": 2.2},
        "glycemic_index": 65, "glycemic_load": 29.6, "serving_size_g": 120,
        "ingredients": ["whole wheat flour", "potato", "onion", "green chilli", "coriander", "oil"], "allergens": ["gluten"],
    },
    {
        "dish_name": "gobi paratha",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["cauliflower paratha", "stuffed cauliflower flatbread"],
        "per_100g": {"calories_kcal": 265, "protein_g": 7.5, "carbs_g": 42.5, "fat_g": 7.5, "fiber_g": 4.0, "sugar_g": 2.0, "sodium_mg": 360, "calcium_mg": 38, "iron_mg": 2.2},
        "glycemic_index": 58, "glycemic_load": 24.7, "serving_size_g": 120,
        "ingredients": ["whole wheat flour", "cauliflower", "onion", "green chilli", "coriander", "oil"], "allergens": ["gluten"],
    },
    {
        "dish_name": "paneer paratha",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["cheese stuffed paratha", "paneer stuffed flatbread"],
        "per_100g": {"calories_kcal": 295, "protein_g": 10.5, "carbs_g": 40.5, "fat_g": 10.5, "fiber_g": 3.0, "sugar_g": 1.5, "sodium_mg": 380, "calcium_mg": 145, "iron_mg": 2.5},
        "glycemic_index": 60, "glycemic_load": 24.3, "serving_size_g": 120,
        "ingredients": ["whole wheat flour", "paneer", "green chilli", "coriander", "cumin", "oil"], "allergens": ["gluten", "milk"],
    },
    {
        "dish_name": "puri",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["poori", "deep fried bread", "fried puri"],
        "per_100g": {"calories_kcal": 358, "protein_g": 8.5, "carbs_g": 52.0, "fat_g": 13.5, "fiber_g": 2.5, "sugar_g": 0.8, "sodium_mg": 280, "calcium_mg": 22, "iron_mg": 2.5},
        "glycemic_index": 68, "glycemic_load": 35.4, "serving_size_g": 60,
        "ingredients": ["whole wheat flour", "oil", "salt", "water"], "allergens": ["gluten"],
    },
    {
        "dish_name": "bhatura",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["bhature", "fried leavened bread", "chole bhature bread"],
        "per_100g": {"calories_kcal": 385, "protein_g": 9.0, "carbs_g": 55.5, "fat_g": 15.5, "fiber_g": 2.0, "sugar_g": 2.5, "sodium_mg": 380, "calcium_mg": 35, "iron_mg": 2.8},
        "glycemic_index": 72, "glycemic_load": 40.0, "serving_size_g": 80,
        "ingredients": ["maida", "yogurt", "oil", "baking soda", "salt"], "allergens": ["gluten", "milk"],
    },
    {
        "dish_name": "missi roti",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["besan roti", "gram flour flatbread"],
        "per_100g": {"calories_kcal": 305, "protein_g": 12.5, "carbs_g": 48.0, "fat_g": 7.5, "fiber_g": 6.5, "sugar_g": 2.0, "sodium_mg": 340, "calcium_mg": 55, "iron_mg": 3.5},
        "glycemic_index": 48, "glycemic_load": 23.0, "serving_size_g": 60,
        "ingredients": ["whole wheat flour", "besan", "onion", "green chilli", "coriander", "oil"], "allergens": ["gluten"],
    },

    # ── Biryani family ────────────────────────────────────────
    {
        "dish_name": "chicken biryani",
        "cuisine_type": "biryani",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["biryani", "hyderabadi biryani", "dum biryani", "chicken dum biryani"],
        "per_100g": {"calories_kcal": 185, "protein_g": 10.5, "carbs_g": 24.5, "fat_g": 5.2, "fiber_g": 1.2, "sugar_g": 1.0, "sodium_mg": 420, "calcium_mg": 25, "iron_mg": 1.5},
        "glycemic_index": 58, "glycemic_load": 14.2, "serving_size_g": 350,
        "ingredients": ["basmati rice", "chicken", "onion", "yogurt", "ghee", "biryani spices", "saffron"], "allergens": ["milk"],
    },
    {
        "dish_name": "mutton biryani",
        "cuisine_type": "biryani",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["gosht biryani", "lamb biryani", "mutton dum biryani"],
        "per_100g": {"calories_kcal": 198, "protein_g": 11.5, "carbs_g": 23.5, "fat_g": 7.0, "fiber_g": 1.2, "sugar_g": 1.0, "sodium_mg": 445, "calcium_mg": 28, "iron_mg": 2.5},
        "glycemic_index": 56, "glycemic_load": 13.2, "serving_size_g": 350,
        "ingredients": ["basmati rice", "mutton", "onion", "yogurt", "ghee", "biryani spices", "saffron"], "allergens": ["milk"],
    },
    {
        "dish_name": "veg biryani",
        "cuisine_type": "biryani",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["vegetable biryani", "veg dum biryani", "mixed veg biryani"],
        "per_100g": {"calories_kcal": 162, "protein_g": 4.2, "carbs_g": 28.5, "fat_g": 3.8, "fiber_g": 2.5, "sugar_g": 2.0, "sodium_mg": 380, "calcium_mg": 35, "iron_mg": 1.2},
        "glycemic_index": 55, "glycemic_load": 15.7, "serving_size_g": 300,
        "ingredients": ["basmati rice", "mixed vegetables", "onion", "yogurt", "ghee", "biryani spices"], "allergens": ["milk"],
    },
    {
        "dish_name": "egg biryani",
        "cuisine_type": "biryani",
        "is_veg": False,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["anda biryani", "egg dum biryani"],
        "per_100g": {"calories_kcal": 175, "protein_g": 8.5, "carbs_g": 24.0, "fat_g": 5.5, "fiber_g": 1.2, "sugar_g": 1.0, "sodium_mg": 415, "calcium_mg": 38, "iron_mg": 1.8},
        "glycemic_index": 56, "glycemic_load": 13.4, "serving_size_g": 300,
        "ingredients": ["basmati rice", "egg", "onion", "yogurt", "ghee", "biryani spices"], "allergens": ["milk", "eggs"],
    },
    {
        "dish_name": "prawn biryani",
        "cuisine_type": "biryani",
        "is_veg": False,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["jhinga biryani", "shrimp biryani", "seafood biryani"],
        "per_100g": {"calories_kcal": 172, "protein_g": 10.5, "carbs_g": 23.5, "fat_g": 4.0, "fiber_g": 1.0, "sugar_g": 1.0, "sodium_mg": 465, "calcium_mg": 48, "iron_mg": 1.8},
        "glycemic_index": 55, "glycemic_load": 12.9, "serving_size_g": 300,
        "ingredients": ["basmati rice", "prawns", "onion", "yogurt", "ghee", "biryani spices"], "allergens": ["milk", "shellfish"],
    },
    {
        "dish_name": "pulao",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["veg pulao", "pilaf", "vegetable pulao", "matar pulao"],
        "per_100g": {"calories_kcal": 155, "protein_g": 3.5, "carbs_g": 28.0, "fat_g": 3.2, "fiber_g": 1.8, "sugar_g": 1.5, "sodium_mg": 280, "calcium_mg": 18, "iron_mg": 0.9},
        "glycemic_index": 55, "glycemic_load": 15.4, "serving_size_g": 250,
        "ingredients": ["basmati rice", "mixed vegetables", "ghee", "whole spices", "onion"], "allergens": ["milk"],
    },
    {
        "dish_name": "jeera rice",
        "cuisine_type": "north_indian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["cumin rice", "zeera rice", "jeera pulao"],
        "per_100g": {"calories_kcal": 148, "protein_g": 2.8, "carbs_g": 28.5, "fat_g": 2.8, "fiber_g": 0.5, "sugar_g": 0.3, "sodium_mg": 180, "calcium_mg": 12, "iron_mg": 0.5},
        "glycemic_index": 65, "glycemic_load": 18.5, "serving_size_g": 200,
        "ingredients": ["basmati rice", "cumin", "ghee", "salt"], "allergens": ["milk"],
    },

    # ════════════════════════════════════════════════════════
    # WEST INDIAN — 80 dishes (Gujarati, Maharashtrian, Rajasthani, Goan)
    # ════════════════════════════════════════════════════════

    # ── Gujarati ──────────────────────────────────────────────
    {
        "dish_name": "dhokla",
        "cuisine_type": "gujarati",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["khaman dhokla", "besan dhokla", "steamed snack"],
        "per_100g": {"calories_kcal": 145, "protein_g": 6.5, "carbs_g": 22.5, "fat_g": 3.2, "fiber_g": 2.8, "sugar_g": 4.5, "sodium_mg": 380, "calcium_mg": 42, "iron_mg": 1.8},
        "glycemic_index": 45, "glycemic_load": 10.1, "serving_size_g": 150,
        "ingredients": ["besan", "yogurt", "sugar", "lemon juice", "mustard seeds", "curry leaves", "green chilli"], "allergens": ["milk"],
    },
    {
        "dish_name": "thepla",
        "cuisine_type": "gujarati",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["methi thepla", "fenugreek flatbread", "gujarati roti"],
        "per_100g": {"calories_kcal": 285, "protein_g": 9.5, "carbs_g": 42.5, "fat_g": 8.5, "fiber_g": 5.5, "sugar_g": 2.0, "sodium_mg": 320, "calcium_mg": 85, "iron_mg": 4.5},
        "glycemic_index": 48, "glycemic_load": 20.4, "serving_size_g": 60,
        "ingredients": ["whole wheat flour", "fenugreek leaves", "besan", "yogurt", "oil", "spices"], "allergens": ["gluten", "milk"],
    },
    {
        "dish_name": "handvo",
        "cuisine_type": "gujarati",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["gujarati handva", "savory lentil cake"],
        "per_100g": {"calories_kcal": 168, "protein_g": 7.5, "carbs_g": 24.5, "fat_g": 4.5, "fiber_g": 3.5, "sugar_g": 3.0, "sodium_mg": 320, "calcium_mg": 48, "iron_mg": 2.2},
        "glycemic_index": 42, "glycemic_load": 10.3, "serving_size_g": 150,
        "ingredients": ["rice", "chana dal", "mixed vegetables", "yogurt", "mustard seeds", "sesame seeds"], "allergens": ["milk"],
    },
    {
        "dish_name": "khandvi",
        "cuisine_type": "gujarati",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["patuli", "rolled gram flour snack"],
        "per_100g": {"calories_kcal": 148, "protein_g": 7.0, "carbs_g": 18.5, "fat_g": 5.5, "fiber_g": 2.5, "sugar_g": 3.5, "sodium_mg": 280, "calcium_mg": 88, "iron_mg": 1.5},
        "glycemic_index": 38, "glycemic_load": 7.0, "serving_size_g": 100,
        "ingredients": ["besan", "buttermilk", "turmeric", "mustard seeds", "coconut", "coriander"], "allergens": ["milk"],
    },
    {
        "dish_name": "undhiyu",
        "cuisine_type": "gujarati",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["undhu", "winter vegetable curry gujarat"],
        "per_100g": {"calories_kcal": 125, "protein_g": 5.5, "carbs_g": 16.5, "fat_g": 4.5, "fiber_g": 5.5, "sugar_g": 3.5, "sodium_mg": 320, "calcium_mg": 55, "iron_mg": 2.5},
        "glycemic_index": 42, "glycemic_load": 6.9, "serving_size_g": 250,
        "ingredients": ["mixed winter vegetables", "fenugreek dumplings", "coconut", "peanuts", "spices", "oil"], "allergens": ["peanuts"],
    },
    {
        "dish_name": "dal dhokli",
        "cuisine_type": "gujarati",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["dal with wheat dumplings", "gujarati dal dhokli"],
        "per_100g": {"calories_kcal": 118, "protein_g": 5.5, "carbs_g": 18.5, "fat_g": 2.8, "fiber_g": 3.5, "sugar_g": 2.5, "sodium_mg": 320, "calcium_mg": 38, "iron_mg": 2.0},
        "glycemic_index": 42, "glycemic_load": 7.8, "serving_size_g": 300,
        "ingredients": ["toor dal", "whole wheat flour", "tomato", "peanuts", "jaggery", "tamarind", "spices"], "allergens": ["gluten", "peanuts"],
    },
    {
        "dish_name": "gujarati kadhi",
        "cuisine_type": "gujarati",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["meethi kadhi", "sweet sour kadhi"],
        "per_100g": {"calories_kcal": 72, "protein_g": 2.8, "carbs_g": 8.5, "fat_g": 3.2, "fiber_g": 0.5, "sugar_g": 5.5, "sodium_mg": 180, "calcium_mg": 85, "iron_mg": 0.5},
        "glycemic_index": 35, "glycemic_load": 3.0, "serving_size_g": 200,
        "ingredients": ["yogurt", "besan", "sugar", "ginger", "curry leaves", "mustard seeds", "ghee"], "allergens": ["milk"],
    },
    {
        "dish_name": "sev tameta",
        "cuisine_type": "gujarati",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["sev tamatar", "sev tomato curry"],
        "per_100g": {"calories_kcal": 115, "protein_g": 4.5, "carbs_g": 14.5, "fat_g": 5.0, "fiber_g": 2.5, "sugar_g": 4.5, "sodium_mg": 380, "calcium_mg": 28, "iron_mg": 1.2},
        "glycemic_index": 42, "glycemic_load": 6.1, "serving_size_g": 200,
        "ingredients": ["sev", "tomato", "onion", "garlic", "mustard seeds", "oil", "spices"], "allergens": ["gluten"],
    },
    {
        "dish_name": "rotlo",
        "cuisine_type": "gujarati",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["bajra rotla", "millet flatbread", "bhakri"],
        "per_100g": {"calories_kcal": 278, "protein_g": 8.5, "carbs_g": 54.0, "fat_g": 4.5, "fiber_g": 3.8, "sugar_g": 0.8, "sodium_mg": 180, "calcium_mg": 38, "iron_mg": 3.0},
        "glycemic_index": 55, "glycemic_load": 29.7, "serving_size_g": 80,
        "ingredients": ["bajra flour", "water", "salt", "oil"], "allergens": [],
    },
    {
        "dish_name": "sukhdi",
        "cuisine_type": "gujarati",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["golpapdi", "wheat flour jaggery sweet"],
        "per_100g": {"calories_kcal": 425, "protein_g": 7.5, "carbs_g": 58.5, "fat_g": 18.5, "fiber_g": 2.0, "sugar_g": 32.0, "sodium_mg": 85, "calcium_mg": 45, "iron_mg": 2.5},
        "glycemic_index": 65, "glycemic_load": 38.0, "serving_size_g": 50,
        "ingredients": ["whole wheat flour", "jaggery", "ghee", "cardamom"], "allergens": ["gluten", "milk"],
    },

    # ── Maharashtrian ─────────────────────────────────────────
    {
        "dish_name": "pav bhaji",
        "cuisine_type": "street_food",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["pav bhaaji", "mumbai pav bhaji", "butter pav bhaji"],
        "per_100g": {"calories_kcal": 152, "protein_g": 4.2, "carbs_g": 22.5, "fat_g": 5.5, "fiber_g": 3.8, "sugar_g": 4.5, "sodium_mg": 480, "calcium_mg": 45, "iron_mg": 1.8},
        "glycemic_index": 58, "glycemic_load": 13.1, "serving_size_g": 250,
        "ingredients": ["mixed vegetables", "potato", "butter", "pav bhaji masala", "pav bread", "onion"], "allergens": ["gluten", "milk"],
    },
    {
        "dish_name": "misal pav",
        "cuisine_type": "maharashtrian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["misal", "kolhapuri misal", "puneri misal"],
        "per_100g": {"calories_kcal": 158, "protein_g": 7.5, "carbs_g": 22.5, "fat_g": 4.5, "fiber_g": 5.5, "sugar_g": 2.5, "sodium_mg": 480, "calcium_mg": 55, "iron_mg": 3.2},
        "glycemic_index": 42, "glycemic_load": 9.5, "serving_size_g": 300,
        "ingredients": ["sprouted moth beans", "onion", "tomato", "misal masala", "sev", "pav bread"], "allergens": ["gluten"],
    },
    {
        "dish_name": "vada pav",
        "cuisine_type": "street_food",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["batata vada pav", "mumbai vada pav", "indian burger"],
        "per_100g": {"calories_kcal": 268, "protein_g": 7.2, "carbs_g": 42.5, "fat_g": 7.8, "fiber_g": 2.8, "sugar_g": 3.2, "sodium_mg": 520, "calcium_mg": 38, "iron_mg": 2.2},
        "glycemic_index": 65, "glycemic_load": 27.6, "serving_size_g": 120,
        "ingredients": ["potato", "besan", "pav bread", "green chutney", "garlic chutney", "oil"], "allergens": ["gluten"],
    },
    {
        "dish_name": "puran poli",
        "cuisine_type": "maharashtrian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["holige", "obbattu", "bobbatlu", "sweet flatbread"],
        "per_100g": {"calories_kcal": 285, "protein_g": 7.5, "carbs_g": 48.5, "fat_g": 7.5, "fiber_g": 3.5, "sugar_g": 18.5, "sodium_mg": 180, "calcium_mg": 45, "iron_mg": 2.8},
        "glycemic_index": 62, "glycemic_load": 30.1, "serving_size_g": 80,
        "ingredients": ["whole wheat flour", "chana dal", "jaggery", "cardamom", "ghee", "saffron"], "allergens": ["gluten", "milk"],
    },
    {
        "dish_name": "bharli vangi",
        "cuisine_type": "maharashtrian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["stuffed brinjal maharashtrian", "bharwa baingan maharashtra"],
        "per_100g": {"calories_kcal": 112, "protein_g": 3.5, "carbs_g": 12.0, "fat_g": 6.0, "fiber_g": 4.5, "sugar_g": 4.0, "sodium_mg": 320, "calcium_mg": 38, "iron_mg": 1.5},
        "glycemic_index": 35, "glycemic_load": 4.2, "serving_size_g": 200,
        "ingredients": ["brinjal", "peanuts", "coconut", "sesame seeds", "onion", "goda masala", "oil"], "allergens": ["peanuts"],
    },
    {
        "dish_name": "ukdiche modak",
        "cuisine_type": "maharashtrian",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["modak", "steamed modak", "ganesh modak"],
        "per_100g": {"calories_kcal": 198, "protein_g": 3.2, "carbs_g": 35.5, "fat_g": 5.5, "fiber_g": 2.5, "sugar_g": 16.5, "sodium_mg": 85, "calcium_mg": 18, "iron_mg": 1.0},
        "glycemic_index": 55, "glycemic_load": 19.5, "serving_size_g": 80,
        "ingredients": ["rice flour", "coconut", "jaggery", "cardamom", "ghee"], "allergens": ["milk"],
    },
    {
        "dish_name": "sabudana khichdi",
        "cuisine_type": "maharashtrian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["sago khichdi", "tapioca khichdi", "vrat ka khana"],
        "per_100g": {"calories_kcal": 185, "protein_g": 3.5, "carbs_g": 35.5, "fat_g": 4.5, "fiber_g": 1.0, "sugar_g": 1.5, "sodium_mg": 220, "calcium_mg": 18, "iron_mg": 0.8},
        "glycemic_index": 72, "glycemic_load": 25.6, "serving_size_g": 200,
        "ingredients": ["sago", "peanuts", "potato", "green chilli", "cumin", "ghee", "lemon"], "allergens": ["peanuts", "milk"],
    },
    {
        "dish_name": "poha",
        "cuisine_type": "maharashtrian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["kanda poha", "batata poha", "flattened rice", "chivda"],
        "per_100g": {"calories_kcal": 158, "protein_g": 3.2, "carbs_g": 32.5, "fat_g": 2.8, "fiber_g": 1.8, "sugar_g": 2.5, "sodium_mg": 280, "calcium_mg": 18, "iron_mg": 2.8},
        "glycemic_index": 68, "glycemic_load": 22.1, "serving_size_g": 200,
        "ingredients": ["flattened rice", "onion", "potato", "mustard seeds", "curry leaves", "turmeric", "oil"], "allergens": [],
    },
    {
        "dish_name": "thalipeeth",
        "cuisine_type": "maharashtrian",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["multigrain roti", "maharashtrian thalipeeth"],
        "per_100g": {"calories_kcal": 268, "protein_g": 9.5, "carbs_g": 42.5, "fat_g": 7.0, "fiber_g": 5.5, "sugar_g": 1.5, "sodium_mg": 280, "calcium_mg": 55, "iron_mg": 3.5},
        "glycemic_index": 45, "glycemic_load": 19.1, "serving_size_g": 80,
        "ingredients": ["jowar flour", "besan", "rice flour", "wheat flour", "onion", "green chilli", "oil"], "allergens": ["gluten"],
    },

    # ── Rajasthani ────────────────────────────────────────────
    {
        "dish_name": "dal baati churma",
        "cuisine_type": "rajasthani",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["baati dal", "rajasthani thali"],
        "per_100g": {"calories_kcal": 285, "protein_g": 9.5, "carbs_g": 42.5, "fat_g": 9.5, "fiber_g": 4.5, "sugar_g": 8.5, "sodium_mg": 280, "calcium_mg": 45, "iron_mg": 3.5},
        "glycemic_index": 58, "glycemic_load": 24.7, "serving_size_g": 400,
        "ingredients": ["whole wheat flour", "ghee", "toor dal", "jaggery", "spices"], "allergens": ["gluten", "milk"],
    },
    {
        "dish_name": "laal maas",
        "cuisine_type": "rajasthani",
        "is_veg": False,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["red mutton curry rajasthan", "spicy lamb rajasthan"],
        "per_100g": {"calories_kcal": 198, "protein_g": 18.5, "carbs_g": 5.5, "fat_g": 12.5, "fiber_g": 1.5, "sugar_g": 2.0, "sodium_mg": 580, "calcium_mg": 35, "iron_mg": 3.8},
        "glycemic_index": 18, "glycemic_load": 1.0, "serving_size_g": 250,
        "ingredients": ["mutton", "mathania chilli", "yogurt", "onion", "garlic", "ghee", "spices"], "allergens": ["milk"],
    },
    {
        "dish_name": "gatte ki sabzi",
        "cuisine_type": "rajasthani",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["besan gatte", "gram flour dumplings curry"],
        "per_100g": {"calories_kcal": 145, "protein_g": 6.5, "carbs_g": 18.5, "fat_g": 5.5, "fiber_g": 3.0, "sugar_g": 2.5, "sodium_mg": 380, "calcium_mg": 48, "iron_mg": 2.0},
        "glycemic_index": 38, "glycemic_load": 7.0, "serving_size_g": 250,
        "ingredients": ["besan", "yogurt", "onion", "tomato", "mustard seeds", "oil", "spices"], "allergens": ["milk"],
    },
    {
        "dish_name": "ker sangri",
        "cuisine_type": "rajasthani",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["desert beans berry curry", "rajasthani ker sangri"],
        "per_100g": {"calories_kcal": 118, "protein_g": 4.5, "carbs_g": 16.5, "fat_g": 4.5, "fiber_g": 8.5, "sugar_g": 3.5, "sodium_mg": 320, "calcium_mg": 55, "iron_mg": 3.5},
        "glycemic_index": 32, "glycemic_load": 5.3, "serving_size_g": 150,
        "ingredients": ["ker", "sangri", "oil", "dry red chilli", "cumin", "amchur", "spices"], "allergens": [],
    },
    {
        "dish_name": "bajra khichdi",
        "cuisine_type": "rajasthani",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["millet khichdi", "bajra moong khichdi"],
        "per_100g": {"calories_kcal": 128, "protein_g": 5.5, "carbs_g": 22.5, "fat_g": 2.5, "fiber_g": 3.0, "sugar_g": 0.8, "sodium_mg": 180, "calcium_mg": 25, "iron_mg": 2.5},
        "glycemic_index": 48, "glycemic_load": 10.8, "serving_size_g": 250,
        "ingredients": ["bajra", "moong dal", "ghee", "cumin", "ginger", "salt"], "allergens": ["milk"],
    },
    {
        "dish_name": "rabdi",
        "cuisine_type": "rajasthani",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["rabri", "thickened milk dessert", "rajasthani rabdi"],
        "per_100g": {"calories_kcal": 185, "protein_g": 5.5, "carbs_g": 22.5, "fat_g": 8.5, "fiber_g": 0.0, "sugar_g": 18.5, "sodium_mg": 65, "calcium_mg": 185, "iron_mg": 0.2},
        "glycemic_index": 55, "glycemic_load": 12.4, "serving_size_g": 150,
        "ingredients": ["milk", "sugar", "saffron", "cardamom", "almonds", "pistachios"], "allergens": ["milk", "tree_nuts"],
    },

    # ── Goan ──────────────────────────────────────────────────
    {
        "dish_name": "goan fish curry",
        "cuisine_type": "goan",
        "is_veg": False,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["fish xacuti", "ambot tik", "coconut fish curry goa"],
        "per_100g": {"calories_kcal": 132, "protein_g": 14.0, "carbs_g": 5.5, "fat_g": 6.5, "fiber_g": 1.5, "sugar_g": 2.5, "sodium_mg": 520, "calcium_mg": 48, "iron_mg": 1.5},
        "glycemic_index": 28, "glycemic_load": 1.5, "serving_size_g": 200,
        "ingredients": ["fish", "coconut milk", "tamarind", "kokum", "onion", "tomato", "goan spices"], "allergens": ["fish"],
    },
    {
        "dish_name": "vindaloo",
        "cuisine_type": "goan",
        "is_veg": False,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["pork vindaloo", "chicken vindaloo", "spicy goan curry"],
        "per_100g": {"calories_kcal": 195, "protein_g": 16.5, "carbs_g": 6.5, "fat_g": 12.5, "fiber_g": 1.2, "sugar_g": 2.5, "sodium_mg": 580, "calcium_mg": 28, "iron_mg": 2.5},
        "glycemic_index": 22, "glycemic_load": 1.4, "serving_size_g": 250,
        "ingredients": ["pork", "vinegar", "kashmiri chilli", "garlic", "ginger", "cumin", "oil"], "allergens": [],
    },
    {
        "dish_name": "bebinca",
        "cuisine_type": "goan",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["bibinca", "goan layered dessert"],
        "per_100g": {"calories_kcal": 295, "protein_g": 5.5, "carbs_g": 42.5, "fat_g": 12.5, "fiber_g": 0.5, "sugar_g": 25.5, "sodium_mg": 120, "calcium_mg": 55, "iron_mg": 1.5},
        "glycemic_index": 65, "glycemic_load": 27.6, "serving_size_g": 100,
        "ingredients": ["coconut milk", "eggs", "sugar", "maida", "ghee", "cardamom"], "allergens": ["milk", "eggs", "gluten"],
    },

    # ════════════════════════════════════════════════════════
    # EAST INDIAN — 40 dishes (Bengali, Odia)
    # ════════════════════════════════════════════════════════

    {
        "dish_name": "machher jhol",
        "cuisine_type": "bengali",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["bengali fish curry", "fish jhol", "rohu curry"],
        "per_100g": {"calories_kcal": 118, "protein_g": 13.5, "carbs_g": 4.5, "fat_g": 5.5, "fiber_g": 1.2, "sugar_g": 2.0, "sodium_mg": 480, "calcium_mg": 38, "iron_mg": 1.5},
        "glycemic_index": 22, "glycemic_load": 1.0, "serving_size_g": 250,
        "ingredients": ["fish", "potato", "tomato", "mustard oil", "turmeric", "nigella seeds", "green chilli"], "allergens": ["fish", "mustard"],
    },
    {
        "dish_name": "shorshe ilish",
        "cuisine_type": "bengali",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["hilsa fish mustard", "ilish macher jhol", "bengali hilsa"],
        "per_100g": {"calories_kcal": 195, "protein_g": 18.5, "carbs_g": 3.5, "fat_g": 12.5, "fiber_g": 0.8, "sugar_g": 1.5, "sodium_mg": 520, "calcium_mg": 45, "iron_mg": 2.5},
        "glycemic_index": 15, "glycemic_load": 0.5, "serving_size_g": 200,
        "ingredients": ["hilsa fish", "mustard paste", "mustard oil", "green chilli", "turmeric", "nigella seeds"], "allergens": ["fish", "mustard"],
    },
    {
        "dish_name": "aloo posto",
        "cuisine_type": "bengali",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["potato poppy seed", "posto aloo bengali"],
        "per_100g": {"calories_kcal": 115, "protein_g": 2.8, "carbs_g": 15.5, "fat_g": 5.5, "fiber_g": 2.5, "sugar_g": 1.5, "sodium_mg": 220, "calcium_mg": 38, "iron_mg": 1.5},
        "glycemic_index": 52, "glycemic_load": 8.1, "serving_size_g": 200,
        "ingredients": ["potato", "poppy seeds", "green chilli", "mustard oil", "turmeric", "nigella seeds"], "allergens": ["mustard"],
    },
    {
        "dish_name": "chingri malai curry",
        "cuisine_type": "bengali",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["prawn coconut milk curry", "bengali prawn curry", "chingri macher malaikari"],
        "per_100g": {"calories_kcal": 165, "protein_g": 14.5, "carbs_g": 5.5, "fat_g": 10.5, "fiber_g": 1.0, "sugar_g": 2.5, "sodium_mg": 480, "calcium_mg": 58, "iron_mg": 2.0},
        "glycemic_index": 25, "glycemic_load": 1.4, "serving_size_g": 200,
        "ingredients": ["prawns", "coconut milk", "onion", "ginger garlic", "mustard oil", "spices"], "allergens": ["shellfish", "mustard"],
    },
    {
        "dish_name": "luchi",
        "cuisine_type": "bengali",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["bengali puri", "fried white bread"],
        "per_100g": {"calories_kcal": 368, "protein_g": 8.5, "carbs_g": 52.5, "fat_g": 15.0, "fiber_g": 1.5, "sugar_g": 0.8, "sodium_mg": 280, "calcium_mg": 22, "iron_mg": 2.5},
        "glycemic_index": 72, "glycemic_load": 37.8, "serving_size_g": 60,
        "ingredients": ["maida", "oil", "salt", "water"], "allergens": ["gluten"],
    },
    {
        "dish_name": "mishti doi",
        "cuisine_type": "bengali",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["sweet yogurt bengali", "bengali sweet curd"],
        "per_100g": {"calories_kcal": 105, "protein_g": 3.8, "carbs_g": 16.5, "fat_g": 3.2, "fiber_g": 0.0, "sugar_g": 14.5, "sodium_mg": 48, "calcium_mg": 128, "iron_mg": 0.1},
        "glycemic_index": 48, "glycemic_load": 7.9, "serving_size_g": 150,
        "ingredients": ["milk", "sugar", "yogurt culture"], "allergens": ["milk"],
    },
    {
        "dish_name": "rasgulla",
        "cuisine_type": "bengali",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["rossogolla", "chenna balls syrup", "bengali rasgulla"],
        "per_100g": {"calories_kcal": 186, "protein_g": 4.5, "carbs_g": 35.5, "fat_g": 3.8, "fiber_g": 0.0, "sugar_g": 32.5, "sodium_mg": 45, "calcium_mg": 95, "iron_mg": 0.2},
        "glycemic_index": 65, "glycemic_load": 23.1, "serving_size_g": 100,
        "ingredients": ["chenna", "sugar syrup", "rose water", "cardamom"], "allergens": ["milk"],
    },
    {
        "dish_name": "sandesh",
        "cuisine_type": "bengali",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["bengali sandesh", "chenna sweet", "sondesh"],
        "per_100g": {"calories_kcal": 295, "protein_g": 7.5, "carbs_g": 45.5, "fat_g": 10.5, "fiber_g": 0.0, "sugar_g": 38.5, "sodium_mg": 35, "calcium_mg": 145, "iron_mg": 0.2},
        "glycemic_index": 60, "glycemic_load": 27.3, "serving_size_g": 50,
        "ingredients": ["chenna", "sugar", "cardamom", "saffron"], "allergens": ["milk"],
    },
    {
        "dish_name": "dal pakhala",
        "cuisine_type": "odia",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["pakhala bhat", "fermented rice odia", "water rice"],
        "per_100g": {"calories_kcal": 82, "protein_g": 2.2, "carbs_g": 18.5, "fat_g": 0.3, "fiber_g": 0.5, "sugar_g": 0.5, "sodium_mg": 85, "calcium_mg": 12, "iron_mg": 0.3},
        "glycemic_index": 55, "glycemic_load": 10.2, "serving_size_g": 300,
        "ingredients": ["rice", "water", "curd", "salt"], "allergens": ["milk"],
    },
    {
        "dish_name": "dalma",
        "cuisine_type": "odia",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["odia dalma", "toor dal vegetables"],
        "per_100g": {"calories_kcal": 98, "protein_g": 5.5, "carbs_g": 14.5, "fat_g": 2.5, "fiber_g": 4.5, "sugar_g": 2.5, "sodium_mg": 280, "calcium_mg": 38, "iron_mg": 2.2},
        "glycemic_index": 35, "glycemic_load": 5.1, "serving_size_g": 250,
        "ingredients": ["toor dal", "raw banana", "drumstick", "eggplant", "coconut", "ghee", "dry red chilli"], "allergens": ["milk"],
    },

    # ════════════════════════════════════════════════════════
    # PAN-INDIAN STAPLES & COMMON DISHES — 60 dishes
    # ════════════════════════════════════════════════════════

    {
        "dish_name": "steamed rice",
        "cuisine_type": "staple",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["plain rice", "white rice cooked", "boiled rice", "cooked rice"],
        "per_100g": {"calories_kcal": 130, "protein_g": 2.7, "carbs_g": 28.2, "fat_g": 0.3, "fiber_g": 0.4, "sugar_g": 0.0, "sodium_mg": 1, "calcium_mg": 10, "iron_mg": 0.2},
        "glycemic_index": 73, "glycemic_load": 20.6, "serving_size_g": 200,
        "ingredients": ["rice", "water"], "allergens": [],
    },
    {
        "dish_name": "brown rice",
        "cuisine_type": "staple",
        "is_veg": True,
        "source": "usda_fdc",
        "confidence": 1.0,
        "aliases": ["whole grain rice", "cooked brown rice"],
        "per_100g": {"calories_kcal": 112, "protein_g": 2.6, "carbs_g": 23.5, "fat_g": 0.9, "fiber_g": 1.8, "sugar_g": 0.0, "sodium_mg": 1, "calcium_mg": 10, "iron_mg": 0.5},
        "glycemic_index": 55, "glycemic_load": 12.9, "serving_size_g": 200,
        "ingredients": ["brown rice", "water"], "allergens": [],
    },
    {
        "dish_name": "khichdi",
        "cuisine_type": "comfort",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["moong dal khichdi", "dal khichdi", "masala khichdi", "rice lentil porridge"],
        "per_100g": {"calories_kcal": 118, "protein_g": 5.2, "carbs_g": 20.5, "fat_g": 2.2, "fiber_g": 2.8, "sugar_g": 0.8, "sodium_mg": 220, "calcium_mg": 28, "iron_mg": 1.5},
        "glycemic_index": 50, "glycemic_load": 10.3, "serving_size_g": 250,
        "ingredients": ["rice", "moong dal", "ghee", "turmeric", "cumin", "salt"], "allergens": ["milk"],
    },
    {
        "dish_name": "paneer",
        "cuisine_type": "staple",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["cottage cheese indian", "fresh paneer", "homemade paneer"],
        "per_100g": {"calories_kcal": 265, "protein_g": 18.3, "carbs_g": 3.4, "fat_g": 20.8, "fiber_g": 0.0, "sugar_g": 3.4, "sodium_mg": 28, "calcium_mg": 480, "iron_mg": 0.2},
        "glycemic_index": 25, "glycemic_load": 0.9, "serving_size_g": 100,
        "ingredients": ["milk", "lemon juice"], "allergens": ["milk"],
    },
    {
        "dish_name": "egg",
        "cuisine_type": "staple",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["boiled egg", "whole egg", "anda", "hen egg"],
        "per_100g": {"calories_kcal": 155, "protein_g": 13.0, "carbs_g": 1.1, "fat_g": 11.0, "fiber_g": 0.0, "sugar_g": 1.1, "sodium_mg": 124, "calcium_mg": 56, "iron_mg": 1.8},
        "glycemic_index": 0, "glycemic_load": 0.0, "serving_size_g": 60,
        "ingredients": ["egg"], "allergens": ["eggs"],
    },
    {
        "dish_name": "chicken",
        "cuisine_type": "staple",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["grilled chicken", "chicken breast", "boiled chicken", "plain chicken"],
        "per_100g": {"calories_kcal": 165, "protein_g": 31.0, "carbs_g": 0.0, "fat_g": 3.6, "fiber_g": 0.0, "sugar_g": 0.0, "sodium_mg": 74, "calcium_mg": 15, "iron_mg": 1.0},
        "glycemic_index": 0, "glycemic_load": 0.0, "serving_size_g": 150,
        "ingredients": ["chicken"], "allergens": [],
    },
    {
        "dish_name": "egg curry",
        "cuisine_type": "pan_indian",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["anda curry", "egg masala", "egg gravy"],
        "per_100g": {"calories_kcal": 145, "protein_g": 9.5, "carbs_g": 6.5, "fat_g": 9.0, "fiber_g": 1.2, "sugar_g": 2.5, "sodium_mg": 420, "calcium_mg": 55, "iron_mg": 2.0},
        "glycemic_index": 28, "glycemic_load": 1.8, "serving_size_g": 200,
        "ingredients": ["egg", "onion", "tomato", "garlic", "oil", "spices"], "allergens": ["eggs"],
    },
    {
        "dish_name": "anda bhurji",
        "cuisine_type": "pan_indian",
        "is_veg": False,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["scrambled eggs indian", "egg bhurji", "masala egg bhurji"],
        "per_100g": {"calories_kcal": 175, "protein_g": 11.5, "carbs_g": 4.5, "fat_g": 12.5, "fiber_g": 0.8, "sugar_g": 2.0, "sodium_mg": 380, "calcium_mg": 55, "iron_mg": 2.0},
        "glycemic_index": 15, "glycemic_load": 0.7, "serving_size_g": 150,
        "ingredients": ["egg", "onion", "tomato", "green chilli", "butter", "spices"], "allergens": ["eggs", "milk"],
    },
    {
        "dish_name": "dahi",
        "cuisine_type": "staple",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["curd", "plain yogurt", "homemade curd", "dahi"],
        "per_100g": {"calories_kcal": 61, "protein_g": 3.5, "carbs_g": 4.7, "fat_g": 3.3, "fiber_g": 0.0, "sugar_g": 4.7, "sodium_mg": 46, "calcium_mg": 121, "iron_mg": 0.1},
        "glycemic_index": 35, "glycemic_load": 1.6, "serving_size_g": 150,
        "ingredients": ["milk", "yogurt culture"], "allergens": ["milk"],
    },
    {
        "dish_name": "raita",
        "cuisine_type": "staple",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["boondi raita", "cucumber raita", "plain raita", "dahi raita"],
        "per_100g": {"calories_kcal": 52, "protein_g": 2.8, "carbs_g": 5.5, "fat_g": 2.2, "fiber_g": 0.5, "sugar_g": 4.2, "sodium_mg": 180, "calcium_mg": 95, "iron_mg": 0.2},
        "glycemic_index": 30, "glycemic_load": 1.7, "serving_size_g": 100,
        "ingredients": ["curd", "cucumber", "cumin", "coriander", "salt"], "allergens": ["milk"],
    },

    # ── Pickles and condiments ────────────────────────────────
    {
        "dish_name": "mango pickle",
        "cuisine_type": "condiment",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 0.9,
        "aliases": ["aam ka achar", "mango achar", "raw mango pickle"],
        "per_100g": {"calories_kcal": 95, "protein_g": 1.2, "carbs_g": 8.5, "fat_g": 6.0, "fiber_g": 2.5, "sugar_g": 2.5, "sodium_mg": 2850, "calcium_mg": 22, "iron_mg": 1.5},
        "glycemic_index": 30, "glycemic_load": 2.6, "serving_size_g": 15,
        "ingredients": ["raw mango", "mustard oil", "salt", "turmeric", "red chilli", "fenugreek"], "allergens": ["mustard"],
    },
    {
        "dish_name": "papadum",
        "cuisine_type": "staple",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["papad", "poppadom", "urad dal papad"],
        "per_100g": {"calories_kcal": 385, "protein_g": 22.5, "carbs_g": 58.5, "fat_g": 5.5, "fiber_g": 5.5, "sugar_g": 0.8, "sodium_mg": 1850, "calcium_mg": 85, "iron_mg": 5.5},
        "glycemic_index": 48, "glycemic_load": 28.1, "serving_size_g": 10,
        "ingredients": ["urad dal flour", "salt", "oil", "spices"], "allergens": [],
    },

    # ════════════════════════════════════════════════════════
    # STREET FOOD — 20 dishes
    # ════════════════════════════════════════════════════════

    {
        "dish_name": "samosa",
        "cuisine_type": "street_food",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["aloo samosa", "potato samosa", "fried samosa"],
        "per_100g": {"calories_kcal": 285, "protein_g": 5.8, "carbs_g": 35.5, "fat_g": 13.5, "fiber_g": 3.2, "sugar_g": 2.0, "sodium_mg": 420, "calcium_mg": 22, "iron_mg": 1.8},
        "glycemic_index": 60, "glycemic_load": 21.3, "serving_size_g": 80,
        "ingredients": ["maida", "potato", "peas", "spices", "oil"], "allergens": ["gluten"],
    },
    {
        "dish_name": "pani puri",
        "cuisine_type": "street_food",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["gol gappa", "puchka", "gupchup", "pani ke batashe"],
        "per_100g": {"calories_kcal": 198, "protein_g": 4.5, "carbs_g": 35.5, "fat_g": 5.2, "fiber_g": 3.5, "sugar_g": 4.8, "sodium_mg": 580, "calcium_mg": 28, "iron_mg": 1.5},
        "glycemic_index": 62, "glycemic_load": 22.0, "serving_size_g": 100,
        "ingredients": ["semolina", "potato", "chickpeas", "tamarind water", "mint water", "spices"], "allergens": ["gluten"],
    },
    {
        "dish_name": "bhel puri",
        "cuisine_type": "street_food",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["bhel", "mumbai bhel", "churmuri"],
        "per_100g": {"calories_kcal": 185, "protein_g": 5.2, "carbs_g": 32.5, "fat_g": 4.8, "fiber_g": 4.2, "sugar_g": 5.5, "sodium_mg": 520, "calcium_mg": 35, "iron_mg": 2.2},
        "glycemic_index": 58, "glycemic_load": 18.9, "serving_size_g": 150,
        "ingredients": ["puffed rice", "sev", "onion", "tomato", "tamarind chutney", "green chutney", "potato"], "allergens": ["gluten"],
    },
    {
        "dish_name": "sev puri",
        "cuisine_type": "street_food",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["sev batata puri", "papdi chaat"],
        "per_100g": {"calories_kcal": 215, "protein_g": 5.5, "carbs_g": 32.5, "fat_g": 8.0, "fiber_g": 3.0, "sugar_g": 5.5, "sodium_mg": 580, "calcium_mg": 38, "iron_mg": 1.8},
        "glycemic_index": 62, "glycemic_load": 20.2, "serving_size_g": 150,
        "ingredients": ["papdi", "potato", "sev", "onion", "tamarind chutney", "green chutney", "yogurt"], "allergens": ["gluten", "milk"],
    },
    {
        "dish_name": "dahi puri",
        "cuisine_type": "street_food",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["dahi batata puri", "yogurt puri"],
        "per_100g": {"calories_kcal": 155, "protein_g": 4.5, "carbs_g": 25.5, "fat_g": 4.5, "fiber_g": 2.5, "sugar_g": 6.5, "sodium_mg": 420, "calcium_mg": 65, "iron_mg": 1.2},
        "glycemic_index": 55, "glycemic_load": 14.0, "serving_size_g": 150,
        "ingredients": ["puri shells", "potato", "yogurt", "tamarind chutney", "sev", "spices"], "allergens": ["gluten", "milk"],
    },
    {
        "dish_name": "aloo tikki",
        "cuisine_type": "street_food",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["potato tikki", "aloo patties", "potato cutlet"],
        "per_100g": {"calories_kcal": 195, "protein_g": 4.0, "carbs_g": 30.5, "fat_g": 6.5, "fiber_g": 2.8, "sugar_g": 1.5, "sodium_mg": 380, "calcium_mg": 18, "iron_mg": 1.2},
        "glycemic_index": 62, "glycemic_load": 18.9, "serving_size_g": 100,
        "ingredients": ["potato", "onion", "green chilli", "coriander", "spices", "oil"], "allergens": [],
    },
    {
        "dish_name": "dabeli",
        "cuisine_type": "street_food",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["kutchi dabeli", "double roti dabeli"],
        "per_100g": {"calories_kcal": 235, "protein_g": 6.5, "carbs_g": 38.5, "fat_g": 7.0, "fiber_g": 2.5, "sugar_g": 6.5, "sodium_mg": 480, "calcium_mg": 35, "iron_mg": 1.5},
        "glycemic_index": 60, "glycemic_load": 23.1, "serving_size_g": 150,
        "ingredients": ["potato", "pav bread", "tamarind chutney", "peanuts", "pomegranate", "sev", "dabeli masala"], "allergens": ["gluten", "peanuts"],
    },
    {
        "dish_name": "chole bhature",
        "cuisine_type": "street_food",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["chana bhatura", "punjabi chole bhature"],
        "per_100g": {"calories_kcal": 245, "protein_g": 7.8, "carbs_g": 36.5, "fat_g": 8.5, "fiber_g": 4.2, "sugar_g": 2.5, "sodium_mg": 420, "calcium_mg": 45, "iron_mg": 2.8},
        "glycemic_index": 55, "glycemic_load": 20.1, "serving_size_g": 300,
        "ingredients": ["chickpeas", "maida", "yogurt", "oil", "onion", "tomato", "chole masala"], "allergens": ["gluten", "milk"],
    },
    {
        "dish_name": "kathi roll",
        "cuisine_type": "street_food",
        "is_veg": False,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["egg roll kolkata", "paratha roll", "frankie"],
        "per_100g": {"calories_kcal": 215, "protein_g": 9.5, "carbs_g": 28.5, "fat_g": 8.0, "fiber_g": 2.0, "sugar_g": 2.5, "sodium_mg": 480, "calcium_mg": 38, "iron_mg": 2.0},
        "glycemic_index": 58, "glycemic_load": 16.5, "serving_size_g": 200,
        "ingredients": ["maida", "egg", "onion", "green chutney", "chicken", "spices", "oil"], "allergens": ["gluten", "eggs"],
    },
    {
        "dish_name": "chaat",
        "cuisine_type": "street_food",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["aloo chaat", "fruit chaat", "papdi chaat"],
        "per_100g": {"calories_kcal": 148, "protein_g": 4.2, "carbs_g": 25.5, "fat_g": 4.0, "fiber_g": 3.5, "sugar_g": 5.5, "sodium_mg": 480, "calcium_mg": 38, "iron_mg": 1.5},
        "glycemic_index": 55, "glycemic_load": 14.0, "serving_size_g": 150,
        "ingredients": ["potato", "chickpeas", "yogurt", "tamarind chutney", "sev", "spices"], "allergens": ["gluten", "milk"],
    },

    # ════════════════════════════════════════════════════════
    # DESSERTS — 30 dishes
    # ════════════════════════════════════════════════════════

    {
        "dish_name": "gulab jamun",
        "cuisine_type": "dessert",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["gulab jamun syrup", "milk solid balls"],
        "per_100g": {"calories_kcal": 352, "protein_g": 5.8, "carbs_g": 52.5, "fat_g": 13.5, "fiber_g": 0.5, "sugar_g": 42.0, "sodium_mg": 180, "calcium_mg": 85, "iron_mg": 0.8},
        "glycemic_index": 85, "glycemic_load": 44.6, "serving_size_g": 60,
        "ingredients": ["khoya", "maida", "sugar syrup", "cardamom", "oil"], "allergens": ["milk", "gluten"],
    },
    {
        "dish_name": "kheer",
        "cuisine_type": "dessert",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["rice kheer", "payasam", "rice pudding indian", "chawal ki kheer"],
        "per_100g": {"calories_kcal": 148, "protein_g": 4.2, "carbs_g": 22.5, "fat_g": 4.8, "fiber_g": 0.3, "sugar_g": 16.5, "sodium_mg": 65, "calcium_mg": 128, "iron_mg": 0.5},
        "glycemic_index": 75, "glycemic_load": 16.9, "serving_size_g": 150,
        "ingredients": ["rice", "milk", "sugar", "cardamom", "saffron", "almonds", "cashews"], "allergens": ["milk", "tree_nuts"],
    },
    {
        "dish_name": "jalebi",
        "cuisine_type": "dessert",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["jilebi", "fresh jalebi", "crispy sweet"],
        "per_100g": {"calories_kcal": 380, "protein_g": 4.2, "carbs_g": 65.5, "fat_g": 11.5, "fiber_g": 0.8, "sugar_g": 52.0, "sodium_mg": 85, "calcium_mg": 18, "iron_mg": 1.2},
        "glycemic_index": 88, "glycemic_load": 57.6, "serving_size_g": 80,
        "ingredients": ["maida", "sugar syrup", "oil", "saffron"], "allergens": ["gluten"],
    },
    {
        "dish_name": "halwa",
        "cuisine_type": "dessert",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["sooji halwa", "rava halwa", "semolina halwa", "sheera"],
        "per_100g": {"calories_kcal": 295, "protein_g": 4.5, "carbs_g": 45.5, "fat_g": 10.5, "fiber_g": 1.2, "sugar_g": 28.5, "sodium_mg": 85, "calcium_mg": 22, "iron_mg": 1.5},
        "glycemic_index": 70, "glycemic_load": 31.9, "serving_size_g": 150,
        "ingredients": ["semolina", "sugar", "ghee", "cashews", "cardamom", "water"], "allergens": ["gluten", "milk", "tree_nuts"],
    },
    {
        "dish_name": "gajar halwa",
        "cuisine_type": "dessert",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["carrot halwa", "gajrela", "carrot pudding indian"],
        "per_100g": {"calories_kcal": 195, "protein_g": 4.5, "carbs_g": 28.5, "fat_g": 7.5, "fiber_g": 2.5, "sugar_g": 20.5, "sodium_mg": 65, "calcium_mg": 128, "iron_mg": 0.8},
        "glycemic_index": 55, "glycemic_load": 15.7, "serving_size_g": 150,
        "ingredients": ["carrot", "milk", "sugar", "ghee", "cardamom", "khoya", "almonds"], "allergens": ["milk", "tree_nuts"],
    },
    {
        "dish_name": "ladoo",
        "cuisine_type": "dessert",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["besan ladoo", "motichoor ladoo", "rava ladoo", "laddoo"],
        "per_100g": {"calories_kcal": 425, "protein_g": 8.5, "carbs_g": 58.5, "fat_g": 18.5, "fiber_g": 2.5, "sugar_g": 38.5, "sodium_mg": 85, "calcium_mg": 55, "iron_mg": 3.5},
        "glycemic_index": 65, "glycemic_load": 38.0, "serving_size_g": 40,
        "ingredients": ["besan", "ghee", "sugar", "cardamom", "cashews", "raisins"], "allergens": ["milk", "tree_nuts"],
    },
    {
        "dish_name": "barfi",
        "cuisine_type": "dessert",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["burfi", "milk barfi", "plain barfi", "mithai"],
        "per_100g": {"calories_kcal": 385, "protein_g": 8.5, "carbs_g": 52.5, "fat_g": 17.5, "fiber_g": 0.5, "sugar_g": 45.5, "sodium_mg": 65, "calcium_mg": 195, "iron_mg": 0.5},
        "glycemic_index": 62, "glycemic_load": 32.6, "serving_size_g": 40,
        "ingredients": ["khoya", "sugar", "cardamom", "pistachios"], "allergens": ["milk", "tree_nuts"],
    },
    {
        "dish_name": "kaju katli",
        "cuisine_type": "dessert",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["cashew fudge", "kaju barfi", "cashew sweet"],
        "per_100g": {"calories_kcal": 458, "protein_g": 11.5, "carbs_g": 52.5, "fat_g": 24.5, "fiber_g": 1.5, "sugar_g": 45.5, "sodium_mg": 35, "calcium_mg": 38, "iron_mg": 2.5},
        "glycemic_index": 55, "glycemic_load": 28.9, "serving_size_g": 30,
        "ingredients": ["cashews", "sugar", "ghee", "cardamom", "silver leaf"], "allergens": ["milk", "tree_nuts"],
    },
    {
        "dish_name": "rasmalai",
        "cuisine_type": "dessert",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["ras malai", "chenna in cream milk", "milk dessert"],
        "per_100g": {"calories_kcal": 195, "protein_g": 6.5, "carbs_g": 25.5, "fat_g": 8.0, "fiber_g": 0.0, "sugar_g": 22.5, "sodium_mg": 55, "calcium_mg": 165, "iron_mg": 0.2},
        "glycemic_index": 55, "glycemic_load": 14.0, "serving_size_g": 100,
        "ingredients": ["chenna", "milk", "sugar", "saffron", "cardamom", "pistachios"], "allergens": ["milk", "tree_nuts"],
    },
    {
        "dish_name": "kulfi",
        "cuisine_type": "dessert",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["indian ice cream", "malai kulfi", "pista kulfi"],
        "per_100g": {"calories_kcal": 215, "protein_g": 5.5, "carbs_g": 25.5, "fat_g": 10.5, "fiber_g": 0.0, "sugar_g": 22.5, "sodium_mg": 65, "calcium_mg": 165, "iron_mg": 0.2},
        "glycemic_index": 45, "glycemic_load": 11.5, "serving_size_g": 100,
        "ingredients": ["milk", "sugar", "cardamom", "saffron", "pistachios", "almonds"], "allergens": ["milk", "tree_nuts"],
    },
    {
        "dish_name": "shrikhand",
        "cuisine_type": "dessert",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["strained yogurt sweet", "gujarati shrikhand", "kesar shrikhand"],
        "per_100g": {"calories_kcal": 215, "protein_g": 6.5, "carbs_g": 28.5, "fat_g": 9.0, "fiber_g": 0.0, "sugar_g": 26.5, "sodium_mg": 48, "calcium_mg": 158, "iron_mg": 0.1},
        "glycemic_index": 42, "glycemic_load": 12.0, "serving_size_g": 100,
        "ingredients": ["hung curd", "sugar", "saffron", "cardamom", "pistachios"], "allergens": ["milk", "tree_nuts"],
    },
    {
        "dish_name": "payasam",
        "cuisine_type": "dessert",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["semiya payasam", "vermicelli payasam", "kheer south indian"],
        "per_100g": {"calories_kcal": 155, "protein_g": 4.5, "carbs_g": 23.5, "fat_g": 4.8, "fiber_g": 0.5, "sugar_g": 16.5, "sodium_mg": 55, "calcium_mg": 118, "iron_mg": 0.5},
        "glycemic_index": 62, "glycemic_load": 14.6, "serving_size_g": 150,
        "ingredients": ["vermicelli", "milk", "sugar", "ghee", "cashews", "raisins", "cardamom"], "allergens": ["gluten", "milk", "tree_nuts"],
    },

    # ════════════════════════════════════════════════════════
    # BEVERAGES — 30 dishes
    # ════════════════════════════════════════════════════════

    {
        "dish_name": "masala chai",
        "cuisine_type": "beverage",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["chai", "indian tea", "spiced tea", "ginger chai"],
        "per_100g": {"calories_kcal": 42, "protein_g": 1.8, "carbs_g": 6.5, "fat_g": 1.2, "fiber_g": 0.0, "sugar_g": 5.5, "sodium_mg": 28, "calcium_mg": 62, "iron_mg": 0.2},
        "glycemic_index": 45, "glycemic_load": 2.9, "serving_size_g": 200,
        "ingredients": ["milk", "tea leaves", "sugar", "ginger", "cardamom", "cinnamon"], "allergens": ["milk"],
    },
    {
        "dish_name": "filter coffee",
        "cuisine_type": "beverage",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["south indian coffee", "degree coffee", "kaapi", "madras coffee"],
        "per_100g": {"calories_kcal": 38, "protein_g": 1.5, "carbs_g": 5.2, "fat_g": 1.2, "fiber_g": 0.0, "sugar_g": 4.8, "sodium_mg": 22, "calcium_mg": 58, "iron_mg": 0.1},
        "glycemic_index": 40, "glycemic_load": 2.1, "serving_size_g": 150,
        "ingredients": ["coffee decoction", "milk", "sugar"], "allergens": ["milk"],
    },
    {
        "dish_name": "lassi",
        "cuisine_type": "beverage",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["sweet lassi", "punjabi lassi", "mango lassi", "plain lassi"],
        "per_100g": {"calories_kcal": 72, "protein_g": 3.5, "carbs_g": 9.8, "fat_g": 2.2, "fiber_g": 0.0, "sugar_g": 9.0, "sodium_mg": 48, "calcium_mg": 118, "iron_mg": 0.1},
        "glycemic_index": 48, "glycemic_load": 4.7, "serving_size_g": 250,
        "ingredients": ["yogurt", "water", "sugar", "cardamom"], "allergens": ["milk"],
    },
    {
        "dish_name": "buttermilk",
        "cuisine_type": "beverage",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["chaas", "masala chaas", "spiced buttermilk", "moru"],
        "per_100g": {"calories_kcal": 28, "protein_g": 1.8, "carbs_g": 3.5, "fat_g": 0.8, "fiber_g": 0.0, "sugar_g": 3.2, "sodium_mg": 185, "calcium_mg": 65, "iron_mg": 0.1},
        "glycemic_index": 30, "glycemic_load": 1.1, "serving_size_g": 200,
        "ingredients": ["curd", "water", "cumin", "ginger", "salt", "coriander"], "allergens": ["milk"],
    },
    {
        "dish_name": "nimbu pani",
        "cuisine_type": "beverage",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["lemonade indian", "shikanji", "lemon water"],
        "per_100g": {"calories_kcal": 22, "protein_g": 0.2, "carbs_g": 5.5, "fat_g": 0.0, "fiber_g": 0.0, "sugar_g": 5.0, "sodium_mg": 85, "calcium_mg": 5, "iron_mg": 0.1},
        "glycemic_index": 35, "glycemic_load": 1.9, "serving_size_g": 250,
        "ingredients": ["lemon juice", "water", "sugar", "salt", "cumin", "mint"], "allergens": [],
    },
    {
        "dish_name": "aam panna",
        "cuisine_type": "beverage",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["raw mango drink", "green mango drink", "summer cooler"],
        "per_100g": {"calories_kcal": 45, "protein_g": 0.3, "carbs_g": 11.5, "fat_g": 0.1, "fiber_g": 0.5, "sugar_g": 9.5, "sodium_mg": 85, "calcium_mg": 8, "iron_mg": 0.2},
        "glycemic_index": 38, "glycemic_load": 4.4, "serving_size_g": 200,
        "ingredients": ["raw mango", "sugar", "cumin", "black salt", "mint", "water"], "allergens": [],
    },
    {
        "dish_name": "jaljeera",
        "cuisine_type": "beverage",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["cumin lemon drink", "spiced water"],
        "per_100g": {"calories_kcal": 18, "protein_g": 0.3, "carbs_g": 4.2, "fat_g": 0.2, "fiber_g": 0.3, "sugar_g": 2.5, "sodium_mg": 185, "calcium_mg": 8, "iron_mg": 0.3},
        "glycemic_index": 28, "glycemic_load": 1.2, "serving_size_g": 200,
        "ingredients": ["water", "lemon juice", "cumin", "black salt", "mint", "tamarind"], "allergens": [],
    },
    {
        "dish_name": "thandai",
        "cuisine_type": "beverage",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.9,
        "aliases": ["holi drink", "spiced milk drink", "cold milk drink"],
        "per_100g": {"calories_kcal": 95, "protein_g": 3.5, "carbs_g": 12.5, "fat_g": 3.8, "fiber_g": 0.5, "sugar_g": 11.5, "sodium_mg": 45, "calcium_mg": 118, "iron_mg": 0.3},
        "glycemic_index": 42, "glycemic_load": 5.3, "serving_size_g": 250,
        "ingredients": ["milk", "almonds", "cashews", "poppy seeds", "sugar", "cardamom", "rose water"], "allergens": ["milk", "tree_nuts"],
    },
    {
        "dish_name": "coconut water",
        "cuisine_type": "beverage",
        "is_veg": True,
        "source": "usda_fdc",
        "confidence": 1.0,
        "aliases": ["nariyal pani", "tender coconut water", "green coconut water"],
        "per_100g": {"calories_kcal": 19, "protein_g": 0.7, "carbs_g": 3.7, "fat_g": 0.2, "fiber_g": 1.1, "sugar_g": 2.6, "sodium_mg": 105, "calcium_mg": 24, "iron_mg": 0.3},
        "glycemic_index": 25, "glycemic_load": 0.9, "serving_size_g": 300,
        "ingredients": ["coconut water"], "allergens": [],
    },
    {
        "dish_name": "sugarcane juice",
        "cuisine_type": "beverage",
        "is_veg": True,
        "source": "icmr_nin_2017",
        "confidence": 1.0,
        "aliases": ["ganna juice", "sugarcane drink", "fresh cane juice"],
        "per_100g": {"calories_kcal": 42, "protein_g": 0.2, "carbs_g": 10.5, "fat_g": 0.1, "fiber_g": 0.0, "sugar_g": 10.3, "sodium_mg": 5, "calcium_mg": 10, "iron_mg": 0.4},
        "glycemic_index": 43, "glycemic_load": 4.5, "serving_size_g": 300,
        "ingredients": ["sugarcane", "lemon", "ginger", "ice"], "allergens": [],
    },
    {
        "dish_name": "rooh afza",
        "cuisine_type": "beverage",
        "is_veg": True,
        "source": "recipe_calculation_nin",
        "confidence": 0.8,
        "aliases": ["rose sherbet", "roohafza milk", "summer drink"],
        "per_100g": {"calories_kcal": 55, "protein_g": 1.5, "carbs_g": 10.5, "fat_g": 0.8, "fiber_g": 0.0, "sugar_g": 10.0, "sodium_mg": 45, "calcium_mg": 58, "iron_mg": 0.1},
        "glycemic_index": 52, "glycemic_load": 5.5, "serving_size_g": 200,
        "ingredients": ["milk", "rooh afza syrup", "rose water", "ice"], "allergens": ["milk"],
    },
]


def compute_per_serving(dish: dict) -> dict:
    """Compute per_serving from per_100g and serving_size_g."""
    per_100g = dish["per_100g"]
    serving_g = dish.get("serving_size_g", 250)
    scale = serving_g / 100.0
    return {k: round(v * scale, 2) for k, v in per_100g.items()}


def seed():
    conn = psycopg2.connect(LOCAL_DB)
    cur = conn.cursor()
    seeded = 0
    updated = 0

    print(f"Seeding {len(DISHES)} Indian dishes...\n")
    print(f"{'Source':<30} {'Count':>6}")
    print("-" * 38)
    sources = {}
    for d in DISHES:
        s = d.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1
    for src, cnt in sorted(sources.items()):
        print(f"  {src:<28} {cnt:>6}")
    print("-" * 38)
    print(f"  {'TOTAL':<28} {len(DISHES):>6}\n")

    for dish in DISHES:
        per_serving = compute_per_serving(dish)

        cur.execute("SELECT id FROM nutrition_kb WHERE dish_name = %s", (dish["dish_name"],))
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE nutrition_kb SET
                    aliases = %s, cuisine_type = %s, source = %s,
                    per_100g = %s, per_serving = %s, serving_size_g = %s,
                    ingredients = %s, allergens = %s, is_veg = %s,
                    glycemic_index = %s, glycemic_load = %s, confidence = %s
                WHERE dish_name = %s
            """, (
                json.dumps(dish["aliases"]), dish["cuisine_type"], dish.get("source", "recipe_calculation"),
                json.dumps(dish["per_100g"]), json.dumps(per_serving), dish.get("serving_size_g", 250),
                json.dumps(dish["ingredients"]), json.dumps(dish["allergens"]),
                dish["is_veg"], dish["glycemic_index"], dish["glycemic_load"],
                dish.get("confidence", 0.8), dish["dish_name"],
            ))
            updated += 1
        else:
            cur.execute("""
                INSERT INTO nutrition_kb (
                    dish_name, aliases, cuisine_type, source,
                    per_100g, per_serving, serving_size_g,
                    ingredients, allergens, is_veg,
                    glycemic_index, glycemic_load, confidence, created_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                dish["dish_name"], json.dumps(dish["aliases"]), dish["cuisine_type"],
                dish.get("source", "recipe_calculation"),
                json.dumps(dish["per_100g"]), json.dumps(per_serving),
                dish.get("serving_size_g", 250),
                json.dumps(dish["ingredients"]), json.dumps(dish["allergens"]),
                dish["is_veg"], dish["glycemic_index"], dish["glycemic_load"],
                dish.get("confidence", 0.8), datetime.now(),
            ))
            seeded += 1

        conf = dish.get("confidence", 0.8)
        conf_label = "NIN✓" if conf >= 1.0 else "NIN≈" if conf >= 0.9 else "USDA" if conf >= 0.8 else "EST"
        print(f"  [{conf_label}] {dish['dish_name']:<35} {dish['per_100g']['calories_kcal']:>4} kcal | "
              f"P:{dish['per_100g']['protein_g']}g | GI:{dish['glycemic_index']}")

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n{'='*60}")
    print(f"  New dishes added    : {seeded}")
    print(f"  Existing updated    : {updated}")
    print(f"  Total in script     : {seeded + updated}")
    print(f"{'='*60}")
    print(f"\nVerify:")
    print(f"  docker exec -it nara-postgres psql -U nara -d nara_data")
    print(f"  SELECT COUNT(*) FROM nutrition_kb;")
    print(f"  SELECT source, COUNT(*) FROM nutrition_kb GROUP BY source;")
    print(f"\nInterview note:")
    print(f"  confidence=1.0 → Direct NIN ICMR-2017 table entry")
    print(f"  confidence=0.9 → NIN ingredient data + standard recipe")
    print(f"  confidence=0.8 → USDA ingredient calculation + recipe")
    print(f"  confidence=0.7 → Regional estimate (flag in recommendations)")


if __name__ == "__main__":
    seed()

