"""
Nutrition Lookup — KB fuzzy matching
Looks up dish names in nutrition_kb with:
  1. Exact match on dish_name
  2. Exact match on any alias
  3. Fuzzy match on dish_name (rapidfuzz)
  4. Fuzzy match on aliases

Confidence mapping:
  1.0  exact dish_name match
  0.95 exact alias match
  0.80 fuzzy dish_name match (score ≥ threshold)
  0.70 fuzzy alias match    (score ≥ threshold)
  None  no match → caller falls back to ingredient estimator

All entries are cached in memory at startup for fast lookup.
Cache refresh: on service restart (KB doesn't change at runtime).
"""
import time
from dataclasses import dataclass
from typing import Optional

import structlog
from rapidfuzz import fuzz, process
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.metrics import metrics, Timer
from app.models.nutrition import NutritionKB

log = structlog.get_logger()
settings = get_settings()


@dataclass
class LookupResult:
    dish_name: str              # canonical name from KB
    matched_on: str             # "exact", "alias_exact", "fuzzy", "alias_fuzzy"
    confidence: float
    nutrition: dict             # full per_serving nutrition dict
    per_100g: dict
    serving_size_g: Optional[float]
    ingredients: list
    allergens: list
    cuisine_type: Optional[str]
    is_veg: Optional[bool]
    glycemic_index: Optional[float]
    glycemic_load: Optional[float]
    kb_confidence: float        # the KB entry's own confidence score


class NutritionLookup:
    """
    In-memory KB cache with fuzzy matching.
    Load once at startup, query thousands of times per second.
    """

    def __init__(self):
        self._entries: list[NutritionKB] = []
        self._dish_names: list[str] = []          # for rapidfuzz process.extract
        self._alias_map: dict[str, NutritionKB] = {}  # alias → entry
        self._exact_map: dict[str, NutritionKB] = {}  # dish_name → entry
        self._loaded = False

    async def load(self, db: AsyncSession):
        """Load all KB entries into memory. Call once at startup."""
        log.info("nutrition_lookup.loading_kb")
        result = await db.execute(select(NutritionKB))
        entries = result.scalars().all()

        self._entries = list(entries)
        self._exact_map = {e.dish_name.lower(): e for e in entries}
        self._dish_names = [e.dish_name.lower() for e in entries]

        # Build alias map
        for entry in entries:
            aliases = entry.aliases or []
            for alias in aliases:
                self._alias_map[alias.lower()] = entry

        self._loaded = True
        log.info(
            "nutrition_lookup.kb_loaded",
            entries=len(self._entries),
            aliases=len(self._alias_map),
        )

    def lookup(self, dish_name: str) -> Optional[LookupResult]:
        """
        Attempt to find a dish in the KB.
        Returns LookupResult or None if no match found.
        """
        if not self._loaded:
            log.error("nutrition_lookup.not_loaded")
            return None

        query = dish_name.lower().strip()

        with Timer() as t:
            result = self._lookup(query)

        metrics.lookup_latency.record(t.elapsed_ms)

        if result:
            metrics.kb_hit_rate.record_hit()
            metrics.fallback_rate.record_miss()  # no fallback needed
            log.debug(
                "nutrition_lookup.hit",
                query=dish_name,
                matched=result.dish_name,
                method=result.matched_on,
                confidence=result.confidence,
                latency_ms=t.elapsed_ms,
            )
        else:
            metrics.kb_hit_rate.record_miss()
            metrics.fallback_rate.record_hit()  # fallback will be needed
            log.debug(
                "nutrition_lookup.miss",
                query=dish_name,
                latency_ms=t.elapsed_ms,
            )

        return result

    def _lookup(self, query: str) -> Optional[LookupResult]:
        # ── 1. Exact dish_name match ──────────────────────────
        if query in self._exact_map:
            return self._to_result(self._exact_map[query], "exact", 1.0)

        # ── 2. Exact alias match ──────────────────────────────
        if query in self._alias_map:
            return self._to_result(self._alias_map[query], "alias_exact", 0.95)

        # ── 3. Fuzzy match on dish names ──────────────────────
        if self._dish_names:
            best = process.extractOne(
                query,
                self._dish_names,
                scorer=fuzz.token_sort_ratio,
            )
            if best and best[1] >= settings.fuzzy_match_threshold:
                entry = self._exact_map[best[0]]
                confidence = 0.80 * (best[1] / 100)  # scale: 80% match → 0.64 confidence
                return self._to_result(entry, "fuzzy", round(confidence, 3))

        # ── 4. Fuzzy match on aliases ─────────────────────────
        if self._alias_map:
            alias_keys = list(self._alias_map.keys())
            best = process.extractOne(
                query,
                alias_keys,
                scorer=fuzz.token_sort_ratio,
            )
            if best and best[1] >= settings.fuzzy_match_threshold:
                entry = self._alias_map[best[0]]
                confidence = 0.70 * (best[1] / 100)
                return self._to_result(entry, "alias_fuzzy", round(confidence, 3))

        return None

    @staticmethod
    def _to_result(entry: NutritionKB, matched_on: str, confidence: float) -> LookupResult:
        return LookupResult(
            dish_name=entry.dish_name,
            matched_on=matched_on,
            confidence=confidence,
            nutrition=entry.per_serving or {},
            per_100g=entry.per_100g or {},
            serving_size_g=entry.serving_size_g,
            ingredients=entry.ingredients or [],
            allergens=entry.allergens or [],
            cuisine_type=entry.cuisine_type,
            is_veg=entry.is_veg,
            glycemic_index=entry.glycemic_index,
            glycemic_load=entry.glycemic_load,
            kb_confidence=entry.confidence or 1.0,
        )

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    @property
    def is_loaded(self) -> bool:
        return self._loaded


# ── Singleton ─────────────────────────────────────────────────
nutrition_lookup = NutritionLookup()
