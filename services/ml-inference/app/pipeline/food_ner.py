"""
Food NER — Named Entity Recognition for dish names
Extracts dish names from free-text meal descriptions.

Examples:
  "Had idli, sambar and coffee this morning"  → ["idli", "sambar", "coffee"]
  "biryani and raita for lunch"               → ["biryani", "raita"]
  "ate some random stuff"                     → ["random stuff"]  (low confidence)

Strategy:
  1. spaCy en_core_web_sm for noun chunks + entity extraction
  2. Food-specific keyword list to boost confidence on known terms
  3. Fallback: return the whole description if nothing extracted
  4. Returns list of (dish_name, confidence) tuples

Confidence scoring:
  1.0 — matched a known food keyword exactly
  0.8 — spaCy noun chunk, looks like food (no verbs, reasonable length)
  0.5 — spaCy entity of type PRODUCT/GPE/ORG (sometimes catches food names)
  0.3 — full-text fallback (nothing better found)
"""
import re
import time
from typing import NamedTuple

import spacy
import structlog

from app.core.config import get_settings
from app.core.metrics import metrics, Timer

log = structlog.get_logger()
settings = get_settings()

# ── Food signal words (expand this list over time) ────────────
FOOD_SIGNALS = {
    # South Indian
    "idli", "dosa", "sambar", "rasam", "upma", "poha", "vada", "uttapam",
    "pongal", "curd rice", "bisibele bath", "pesarattu", "appam",
    # North Indian
    "biryani", "biriyani", "roti", "paratha", "naan", "dal", "sabzi",
    "paneer", "chole", "rajma", "aloo", "puri", "bhatura", "khichdi",
    "pulao", "pulav", "chapati", "chapathi",
    # Snacks / Street food
    "samosa", "pakora", "bhajia", "chaat", "pani puri", "bhel",
    "sev puri", "vada pav", "pav bhaji",
    # Proteins
    "chicken", "mutton", "egg", "fish", "prawn", "paneer",
    # Drinks
    "tea", "coffee", "chai", "lassi", "buttermilk", "juice",
    # Desserts
    "kheer", "halwa", "gulab jamun", "rasgulla", "barfi", "ladoo",
    # International (common in India)
    "pizza", "burger", "pasta", "noodles", "maggi", "sandwich",
    # Generic
    "rice", "bread", "roti", "curry", "gravy", "soup", "salad",
    "raita", "pickle", "chutney", "papad",
}

# Noise words — if noun chunk is only these, skip it
NOISE_WORDS = {
    "morning", "lunch", "dinner", "breakfast", "snack", "meal",
    "today", "yesterday", "home", "office", "little", "some",
    "bit", "food", "something", "stuff", "thing", "lot", "much",
}

# Compiled regex to clean up extracted text
_CLEANER = re.compile(r"[^a-zA-Z0-9\s\-]")


class DishCandidate(NamedTuple):
    name: str
    confidence: float
    source: str   # "keyword", "noun_chunk", "entity", "fallback"


class FoodNER:
    """
    Extract dish names from free-text meal descriptions.
    Loads spaCy model once at startup.
    """

    def __init__(self):
        self._nlp = None
        self._loaded = False

    def load(self):
        """Load spaCy model. Called once at service startup."""
        if self._loaded:
            return
        log.info("food_ner.loading_model", model=settings.spacy_model)
        self._nlp = spacy.load(settings.spacy_model)
        self._loaded = True
        log.info("food_ner.model_loaded")

    def extract(self, text: str) -> list[DishCandidate]:
        """
        Extract dish candidates from text.
        Returns list sorted by confidence descending.
        """
        if not self._loaded:
            self.load()

        with Timer() as t:
            candidates = self._extract(text)

        # Record latency and average confidence
        metrics.ner_latency.record(t.elapsed_ms)
        if candidates:
            avg_conf = sum(c.confidence for c in candidates) / len(candidates)
            metrics.ner_confidence.record(avg_conf)
        else:
            metrics.ner_confidence.record(0.0)

        log.debug(
            "food_ner.extracted",
            text=text[:60],
            candidates=[(c.name, c.confidence) for c in candidates],
            latency_ms=t.elapsed_ms,
        )
        return candidates

    def _extract(self, text: str) -> list[DishCandidate]:
        text_lower = text.lower().strip()
        doc = self._nlp(text_lower)
        seen = set()
        candidates = []

        # ── Pass 1: Keyword matching (highest confidence) ─────
        for keyword in FOOD_SIGNALS:
            if keyword in text_lower:
                normalized = self._normalize(keyword)
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    candidates.append(DishCandidate(
                        name=normalized,
                        confidence=1.0,
                        source="keyword",
                    ))

        # ── Pass 2: spaCy noun chunks ─────────────────────────
        for chunk in doc.noun_chunks:
            normalized = self._normalize(chunk.text)
            if not normalized or normalized in seen:
                continue
            if normalized in NOISE_WORDS:
                continue
            if len(normalized.split()) > 5:   # too long to be a dish name
                continue
            # Check if chunk root is a noun (not "had some", "ate a")
            if chunk.root.pos_ in ("NOUN", "PROPN"):
                seen.add(normalized)
                candidates.append(DishCandidate(
                    name=normalized,
                    confidence=0.8,
                    source="noun_chunk",
                ))

        # ── Pass 3: spaCy entities (PRODUCT, GPE sometimes = food) ──
        for ent in doc.ents:
            if ent.label_ in ("PRODUCT", "ORG", "GPE", "NORP"):
                normalized = self._normalize(ent.text)
                if normalized and normalized not in seen and normalized not in NOISE_WORDS:
                    seen.add(normalized)
                    candidates.append(DishCandidate(
                        name=normalized,
                        confidence=0.5,
                        source="entity",
                    ))

        # ── Pass 4: Fallback — return full text if nothing found ──
        if not candidates:
            normalized = self._normalize(text_lower)
            if normalized:
                candidates.append(DishCandidate(
                    name=normalized[:100],  # cap length
                    confidence=0.3,
                    source="fallback",
                ))

        # Sort by confidence descending
        return sorted(candidates, key=lambda c: c.confidence, reverse=True)

    @staticmethod
    def _normalize(text: str) -> str:
        """Clean and normalize a dish name candidate."""
        cleaned = _CLEANER.sub("", text).strip()
        # Remove leading articles
        for article in ("a ", "an ", "the ", "some ", "few "):
            if cleaned.startswith(article):
                cleaned = cleaned[len(article):]
        cleaned = " ".join(cleaned.split())  # collapse whitespace
        return cleaned.lower()

    def top_dish(self, text: str) -> tuple[str, float]:
        """
        Convenience method — returns the single best dish name + confidence.
        Used by enrichment worker when it just needs one name to look up.
        """
        candidates = self.extract(text)
        if candidates:
            return candidates[0].name, candidates[0].confidence
        return text.strip().lower(), 0.3


# ── Singleton ─────────────────────────────────────────────────
food_ner = FoodNER()