"""
Nutrition Estimator — Ingredient-level fallback
When a dish is not found in nutrition_kb, this estimator:
  1. Breaks the dish into likely ingredients (rule-based)
  2. Looks up each ingredient in nutrition_kb
  3. Sums weighted nutrition values based on typical portion ratios
  4. Returns estimated nutrition with lower confidence score

Confidence: 0.4-0.5 (lower than KB lookup, higher than pure guess)

Example:
  "pesarattu" → ["green moong dal", "rice", "ginger", "cumin", "oil"]
               → look up each → sum with weights → return estimate
"""
from dataclasses import dataclass
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import metrics, Timer
from app.models.nutrition import NutritionKB

log = structlog.get_logger()

# ── Ingredient knowledge base ─────────────────────────────────
# dish_name → list of (ingredient, weight_fraction)
# weight_fraction: how much of the dish is this ingredient by weight
# All fractions in a dish should sum to ~1.0
DISH_INGREDIENT_MAP: dict[str, list[tuple[str, float]]] = {
    # South Indian
    "pesarattu":        [("green moong dal", 0.5), ("rice", 0.3), ("ginger", 0.05), ("oil", 0.05), ("onion", 0.1)],
    "appam":            [("rice", 0.6), ("coconut milk", 0.3), ("oil", 0.05), ("sugar", 0.05)],
    "puttu":            [("rice flour", 0.6), ("coconut", 0.3), ("water", 0.1)],
    "kozhukattai":      [("rice flour", 0.6), ("coconut", 0.2), ("jaggery", 0.15), ("oil", 0.05)],
    "murukku":          [("rice flour", 0.5), ("urad dal", 0.2), ("oil", 0.25), ("spices", 0.05)],
    "medu vada":        [("urad dal", 0.6), ("oil", 0.3), ("onion", 0.05), ("spices", 0.05)],
    "rava idli":        [("semolina", 0.5), ("curd", 0.3), ("oil", 0.1), ("vegetables", 0.1)],
    "rava dosa":        [("semolina", 0.4), ("rice flour", 0.2), ("maida", 0.2), ("oil", 0.15), ("spices", 0.05)],
    "set dosa":         [("rice", 0.5), ("urad dal", 0.2), ("oil", 0.2), ("fenugreek", 0.05), ("poha", 0.05)],
    "neer dosa":        [("rice", 0.7), ("coconut", 0.2), ("oil", 0.1)],

    # North Indian
    "aloo paratha":     [("wheat flour", 0.4), ("potato", 0.35), ("oil", 0.15), ("spices", 0.1)],
    "dal makhani":      [("black lentil", 0.4), ("kidney beans", 0.1), ("butter", 0.15), ("cream", 0.1), ("tomato", 0.15), ("spices", 0.1)],
    "palak paneer":     [("spinach", 0.4), ("paneer", 0.3), ("cream", 0.1), ("oil", 0.1), ("spices", 0.1)],
    "aloo gobi":        [("potato", 0.4), ("cauliflower", 0.4), ("oil", 0.1), ("spices", 0.1)],
    "matar paneer":     [("paneer", 0.35), ("green peas", 0.3), ("tomato", 0.15), ("oil", 0.1), ("spices", 0.1)],
    "chana masala":     [("chickpeas", 0.5), ("tomato", 0.2), ("oil", 0.1), ("onion", 0.1), ("spices", 0.1)],
    "butter chicken":   [("chicken", 0.45), ("butter", 0.1), ("cream", 0.1), ("tomato", 0.2), ("spices", 0.15)],
    "chicken curry":    [("chicken", 0.5), ("oil", 0.1), ("tomato", 0.15), ("onion", 0.1), ("spices", 0.15)],
    "mutton curry":     [("mutton", 0.5), ("oil", 0.12), ("tomato", 0.13), ("onion", 0.1), ("spices", 0.15)],
    "egg curry":        [("egg", 0.4), ("tomato", 0.2), ("onion", 0.15), ("oil", 0.1), ("spices", 0.15)],

    # Rice dishes
    "jeera rice":       [("rice", 0.75), ("oil", 0.1), ("cumin", 0.05), ("onion", 0.1)],
    "lemon rice":       [("rice", 0.7), ("lemon", 0.1), ("oil", 0.1), ("peanuts", 0.05), ("spices", 0.05)],
    "coconut rice":     [("rice", 0.65), ("coconut", 0.2), ("oil", 0.1), ("spices", 0.05)],
    "tamarind rice":    [("rice", 0.65), ("tamarind", 0.1), ("oil", 0.1), ("peanuts", 0.05), ("spices", 0.1)],
    "tomato rice":      [("rice", 0.6), ("tomato", 0.2), ("oil", 0.1), ("spices", 0.1)],
    "vegetable pulao":  [("rice", 0.55), ("mixed vegetables", 0.2), ("oil", 0.1), ("spices", 0.1), ("onion", 0.05)],

    # Breads
    "tandoori roti":    [("wheat flour", 0.7), ("water", 0.25), ("oil", 0.05)],
    "missi roti":       [("wheat flour", 0.5), ("chickpea flour", 0.3), ("oil", 0.1), ("spices", 0.1)],
    "rumali roti":      [("maida", 0.6), ("wheat flour", 0.2), ("oil", 0.1), ("milk", 0.1)],

    # Snacks
    "dhokla":           [("chickpea flour", 0.5), ("curd", 0.2), ("oil", 0.1), ("sugar", 0.05), ("spices", 0.15)],
    "khandvi":          [("chickpea flour", 0.4), ("buttermilk", 0.4), ("oil", 0.1), ("spices", 0.1)],
    "thepla":           [("wheat flour", 0.4), ("fenugreek leaves", 0.2), ("oil", 0.2), ("curd", 0.1), ("spices", 0.1)],
    "chakli":           [("rice flour", 0.5), ("urad dal", 0.2), ("oil", 0.25), ("spices", 0.05)],

    # Desserts
    "payasam":          [("rice", 0.3), ("milk", 0.4), ("sugar", 0.2), ("ghee", 0.05), ("cardamom", 0.05)],
    "semiya payasam":   [("vermicelli", 0.3), ("milk", 0.45), ("sugar", 0.15), ("ghee", 0.05), ("cashews", 0.05)],
    "rava kesari":      [("semolina", 0.35), ("sugar", 0.3), ("ghee", 0.2), ("water", 0.1), ("cardamom", 0.05)],
    "mysore pak":       [("chickpea flour", 0.3), ("ghee", 0.4), ("sugar", 0.25), ("water", 0.05)],

    # Generic fallbacks for common ingredients used as dishes
    "boiled egg":       [("egg", 0.95), ("water", 0.05)],
    "scrambled egg":    [("egg", 0.7), ("butter", 0.15), ("milk", 0.1), ("salt", 0.05)],
    "plain rice":       [("rice", 0.9), ("water", 0.1)],
    "plain dal":        [("lentil", 0.5), ("water", 0.35), ("oil", 0.1), ("spices", 0.05)],
}

# ── Base ingredient nutrition per 100g ────────────────────────
# Fallback values when ingredient not in nutrition_kb
# Format: {calories, protein_g, carbs_g, fat_g, fiber_g}
BASE_INGREDIENT_NUTRITION: dict[str, dict] = {
    "rice":             {"calories": 130, "protein_g": 2.7, "carbs_g": 28.2, "fat_g": 0.3, "fiber_g": 0.4},
    "rice flour":       {"calories": 366, "protein_g": 6.0, "carbs_g": 80.0, "fat_g": 1.4, "fiber_g": 2.4},
    "wheat flour":      {"calories": 340, "protein_g": 11.0, "carbs_g": 72.0, "fat_g": 1.0, "fiber_g": 2.7},
    "maida":            {"calories": 348, "protein_g": 9.0, "carbs_g": 76.0, "fat_g": 0.8, "fiber_g": 0.4},
    "semolina":         {"calories": 360, "protein_g": 12.0, "carbs_g": 73.0, "fat_g": 1.0, "fiber_g": 3.0},
    "chickpea flour":   {"calories": 387, "protein_g": 22.0, "carbs_g": 58.0, "fat_g": 6.0, "fiber_g": 10.0},
    "urad dal":         {"calories": 341, "protein_g": 25.0, "carbs_g": 59.0, "fat_g": 1.4, "fiber_g": 18.0},
    "lentil":           {"calories": 352, "protein_g": 25.0, "carbs_g": 60.0, "fat_g": 1.1, "fiber_g": 10.7},
    "green moong dal":  {"calories": 347, "protein_g": 24.0, "carbs_g": 63.0, "fat_g": 1.2, "fiber_g": 16.0},
    "black lentil":     {"calories": 341, "protein_g": 25.0, "carbs_g": 57.0, "fat_g": 1.6, "fiber_g": 11.0},
    "kidney beans":     {"calories": 333, "protein_g": 24.0, "carbs_g": 60.0, "fat_g": 0.8, "fiber_g": 25.0},
    "chickpeas":        {"calories": 364, "protein_g": 19.0, "carbs_g": 61.0, "fat_g": 6.0, "fiber_g": 17.0},
    "chicken":          {"calories": 165, "protein_g": 31.0, "carbs_g": 0.0, "fat_g": 3.6, "fiber_g": 0.0},
    "mutton":           {"calories": 294, "protein_g": 25.0, "carbs_g": 0.0, "fat_g": 21.0, "fiber_g": 0.0},
    "egg":              {"calories": 155, "protein_g": 13.0, "carbs_g": 1.1, "fat_g": 11.0, "fiber_g": 0.0},
    "paneer":           {"calories": 265, "protein_g": 18.0, "carbs_g": 3.4, "fat_g": 20.0, "fiber_g": 0.0},
    "milk":             {"calories": 61,  "protein_g": 3.2, "carbs_g": 4.8, "fat_g": 3.3, "fiber_g": 0.0},
    "coconut milk":     {"calories": 197, "protein_g": 2.0, "carbs_g": 2.8, "fat_g": 21.0, "fiber_g": 0.0},
    "coconut":          {"calories": 354, "protein_g": 3.3, "carbs_g": 15.0, "fat_g": 33.0, "fiber_g": 9.0},
    "butter":           {"calories": 717, "protein_g": 0.9, "carbs_g": 0.1, "fat_g": 81.0, "fiber_g": 0.0},
    "ghee":             {"calories": 900, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 99.0, "fiber_g": 0.0},
    "oil":              {"calories": 884, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 100.0, "fiber_g": 0.0},
    "cream":            {"calories": 340, "protein_g": 2.1, "carbs_g": 2.8, "fat_g": 36.0, "fiber_g": 0.0},
    "curd":             {"calories": 61,  "protein_g": 3.5, "carbs_g": 4.7, "fat_g": 3.3, "fiber_g": 0.0},
    "buttermilk":       {"calories": 40,  "protein_g": 3.3, "carbs_g": 5.0, "fat_g": 0.9, "fiber_g": 0.0},
    "potato":           {"calories": 77,  "protein_g": 2.0, "carbs_g": 17.0, "fat_g": 0.1, "fiber_g": 2.2},
    "tomato":           {"calories": 18,  "protein_g": 0.9, "carbs_g": 3.9, "fat_g": 0.2, "fiber_g": 1.2},
    "onion":            {"calories": 40,  "protein_g": 1.1, "carbs_g": 9.3, "fat_g": 0.1, "fiber_g": 1.7},
    "spinach":          {"calories": 23,  "protein_g": 2.9, "carbs_g": 3.6, "fat_g": 0.4, "fiber_g": 2.2},
    "cauliflower":      {"calories": 25,  "protein_g": 1.9, "carbs_g": 5.0, "fat_g": 0.3, "fiber_g": 2.0},
    "green peas":       {"calories": 81,  "protein_g": 5.4, "carbs_g": 14.0, "fat_g": 0.4, "fiber_g": 5.1},
    "mixed vegetables": {"calories": 35,  "protein_g": 1.5, "carbs_g": 7.0, "fat_g": 0.2, "fiber_g": 2.5},
    "fenugreek leaves": {"calories": 49,  "protein_g": 4.4, "carbs_g": 6.0, "fat_g": 0.9, "fiber_g": 2.7},
    "sugar":            {"calories": 387, "protein_g": 0.0, "carbs_g": 100.0, "fat_g": 0.0, "fiber_g": 0.0},
    "jaggery":          {"calories": 383, "protein_g": 0.4, "carbs_g": 98.0, "fat_g": 0.1, "fiber_g": 0.0},
    "peanuts":          {"calories": 567, "protein_g": 26.0, "carbs_g": 16.0, "fat_g": 49.0, "fiber_g": 8.5},
    "cashews":          {"calories": 553, "protein_g": 18.0, "carbs_g": 30.0, "fat_g": 44.0, "fiber_g": 3.3},
    "tamarind":         {"calories": 239, "protein_g": 2.8, "carbs_g": 63.0, "fat_g": 0.6, "fiber_g": 5.1},
    "lemon":            {"calories": 29,  "protein_g": 1.1, "carbs_g": 9.3, "fat_g": 0.3, "fiber_g": 2.8},
    "vermicelli":       {"calories": 348, "protein_g": 12.0, "carbs_g": 75.0, "fat_g": 1.0, "fiber_g": 3.0},
    "spices":           {"calories": 50,  "protein_g": 2.0, "carbs_g": 8.0, "fat_g": 1.5, "fiber_g": 4.0},
    "ginger":           {"calories": 80,  "protein_g": 1.8, "carbs_g": 18.0, "fat_g": 0.8, "fiber_g": 2.0},
    "cumin":            {"calories": 375, "protein_g": 18.0, "carbs_g": 44.0, "fat_g": 22.0, "fiber_g": 11.0},
    "cardamom":         {"calories": 311, "protein_g": 11.0, "carbs_g": 68.0, "fat_g": 7.0, "fiber_g": 28.0},
    "fenugreek":        {"calories": 323, "protein_g": 23.0, "carbs_g": 58.0, "fat_g": 6.0, "fiber_g": 25.0},
    "water":            {"calories": 0,   "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0},
    "salt":             {"calories": 0,   "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0},
}

NUTRITION_KEYS = ["calories", "protein_g", "carbs_g", "fat_g", "fiber_g"]

# Default serving size when we have no KB data (grams)
DEFAULT_SERVING_G = 250.0


@dataclass
class EstimatorResult:
    dish_name: str
    estimated_nutrition: dict     # per serving
    confidence: float             # 0.4-0.5
    ingredients_used: list[str]
    model_version: str = "ingredient_estimator_v1"


class NutritionEstimator:
    """
    Ingredient-level fallback estimator.
    Used when nutrition_kb lookup returns no match.
    """

    async def estimate(
        self,
        dish_name: str,
        db: AsyncSession,
        serving_size_g: float = DEFAULT_SERVING_G,
    ) -> EstimatorResult:
        """
        Estimate nutrition for a dish not in KB.
        Tries DISH_INGREDIENT_MAP first, then ingredient DB lookup,
        then BASE_INGREDIENT_NUTRITION as final fallback.
        """
        with Timer() as t:
            result = await self._estimate(dish_name, db, serving_size_g)

        metrics.estimator_latency.record(t.elapsed_ms)
        log.info(
            "nutrition_estimator.result",
            dish=dish_name,
            confidence=result.confidence,
            ingredients=result.ingredients_used,
            latency_ms=t.elapsed_ms,
        )
        return result

    async def _estimate(
        self,
        dish_name: str,
        db: AsyncSession,
        serving_size_g: float,
    ) -> EstimatorResult:
        query = dish_name.lower().strip()

        # ── Get ingredient list ───────────────────────────────
        ingredient_weights = DISH_INGREDIENT_MAP.get(query)
        confidence = 0.5

        if not ingredient_weights:
            # Not in our ingredient map — use a generic "grain + protein + fat" split
            ingredient_weights = self._generic_split(query)
            confidence = 0.4  # lower confidence for generic split

        # ── Look up each ingredient's nutrition ───────────────
        ingredient_names = [ing for ing, _ in ingredient_weights]
        kb_nutrition = await self._fetch_ingredient_nutrition(ingredient_names, db)

        # ── Compute weighted nutrition per 100g of dish ───────
        per_100g = {k: 0.0 for k in NUTRITION_KEYS}
        ingredients_used = []

        for ingredient, fraction in ingredient_weights:
            nutrition = (
                kb_nutrition.get(ingredient)
                or BASE_INGREDIENT_NUTRITION.get(ingredient)
            )
            if not nutrition:
                log.debug("nutrition_estimator.unknown_ingredient", ingredient=ingredient)
                continue

            for key in NUTRITION_KEYS:
                per_100g[key] += nutrition.get(key, 0.0) * fraction

            ingredients_used.append(ingredient)

        # ── Scale to serving size ─────────────────────────────
        scale = serving_size_g / 100.0
        per_serving = {k: round(v * scale, 2) for k, v in per_100g.items()}

        # Add GI estimate (rough — based on dominant ingredient)
        per_serving["glycemic_index"] = self._estimate_gi(ingredient_weights)
        per_serving["glycemic_load"] = round(
            per_serving["glycemic_index"] * per_serving.get("carbs_g", 0) / 100, 1
        )

        return EstimatorResult(
            dish_name=dish_name,
            estimated_nutrition=per_serving,
            confidence=confidence,
            ingredients_used=ingredients_used,
        )

    async def _fetch_ingredient_nutrition(
        self,
        ingredients: list[str],
        db: AsyncSession,
    ) -> dict[str, dict]:
        """Fetch per_100g nutrition for ingredients from nutrition_kb."""
        if not ingredients:
            return {}

        result = await db.execute(
            select(NutritionKB.dish_name, NutritionKB.per_100g).where(
                NutritionKB.dish_name.in_(ingredients)
            )
        )
        rows = result.all()
        return {row.dish_name: row.per_100g for row in rows}

    @staticmethod
    def _generic_split(dish_name: str) -> list[tuple[str, float]]:
        """
        Generic ingredient split for completely unknown dishes.
        Assumes a typical Indian mixed dish composition.
        """
        # Check for signals in the name
        name = dish_name.lower()
        if any(w in name for w in ["rice", "pulao", "biryani", "fried rice"]):
            return [("rice", 0.6), ("oil", 0.1), ("spices", 0.1), ("mixed vegetables", 0.2)]
        if any(w in name for w in ["roti", "paratha", "bread", "naan"]):
            return [("wheat flour", 0.6), ("oil", 0.2), ("water", 0.15), ("spices", 0.05)]
        if any(w in name for w in ["dal", "lentil", "soup"]):
            return [("lentil", 0.5), ("water", 0.3), ("oil", 0.1), ("spices", 0.1)]
        if any(w in name for w in ["chicken", "mutton", "meat"]):
            return [("chicken", 0.5), ("oil", 0.15), ("spices", 0.15), ("tomato", 0.2)]
        if any(w in name for w in ["paneer", "tofu"]):
            return [("paneer", 0.4), ("oil", 0.15), ("tomato", 0.2), ("spices", 0.15), ("onion", 0.1)]
        if any(w in name for w in ["sweet", "halwa", "kheer", "pudding"]):
            return [("sugar", 0.25), ("milk", 0.4), ("ghee", 0.15), ("semolina", 0.2)]
        # Default: mixed vegetable dish
        return [("mixed vegetables", 0.4), ("oil", 0.15), ("spices", 0.1), ("onion", 0.15), ("tomato", 0.2)]

    @staticmethod
    def _estimate_gi(ingredient_weights: list[tuple[str, float]]) -> float:
        """Rough GI estimate based on dominant carb ingredient."""
        gi_map = {
            "rice": 72, "rice flour": 72, "maida": 70, "semolina": 65,
            "wheat flour": 50, "potato": 78, "sugar": 65, "jaggery": 55,
            "lentil": 29, "chickpeas": 33, "green moong dal": 32,
            "urad dal": 43, "kidney beans": 24, "vermicelli": 53,
        }
        weighted_gi = 0.0
        total_weight = 0.0
        for ingredient, fraction in ingredient_weights:
            if ingredient in gi_map:
                weighted_gi += gi_map[ingredient] * fraction
                total_weight += fraction
        if total_weight == 0:
            return 50.0  # medium GI default
        return round(weighted_gi / total_weight, 1)


# ── Singleton ─────────────────────────────────────────────────
nutrition_estimator = NutritionEstimator()