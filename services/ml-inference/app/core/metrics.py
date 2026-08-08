"""
ML Inference Service — Metrics
In-memory rolling window metrics.
Tracks latency per stage, KB hit rate, NER confidence, vision confidence.
These are the baseline numbers we compare Sprint 5+ models against.

Metrics stored:
  enrichment_latency_ms     : end-to-end enrichment time
  ner_latency_ms            : spaCy extraction time
  lookup_latency_ms         : nutrition KB lookup time
  estimator_latency_ms      : ingredient fallback time
  vision_latency_ms         : Claude Vision API time

  kb_hit_rate               : dish found in KB (not fallback)
  ner_confidence            : spaCy entity confidence scores
  vision_confidence         : Claude vision confidence scores
  fallback_rate             : how often ingredient estimator was used
"""
import time
import statistics
from collections import deque
from dataclasses import dataclass, field
from typing import Optional
import structlog

log = structlog.get_logger()


@dataclass
class LatencyTracker:
    """Rolling window of latency samples in ms."""
    name: str
    window: deque = field(default_factory=lambda: deque(maxlen=1000))

    def record(self, ms: float):
        self.window.append(ms)

    def stats(self) -> dict:
        if not self.window:
            return {"count": 0, "p50": None, "p95": None, "p99": None, "mean": None}
        data = sorted(self.window)
        n = len(data)
        return {
            "count": n,
            "p50": data[int(n * 0.50)],
            "p95": data[int(n * 0.95)],
            "p99": data[int(n * 0.99)],
            "mean": round(statistics.mean(data), 2),
        }


@dataclass
class RateTracker:
    """Tracks hit/miss counts for computing rates."""
    name: str
    hits: int = 0
    misses: int = 0

    def record_hit(self):
        self.hits += 1

    def record_miss(self):
        self.misses += 1

    @property
    def rate(self) -> Optional[float]:
        total = self.hits + self.misses
        if total == 0:
            return None
        return round(self.hits / total, 4)

    def stats(self) -> dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total": self.hits + self.misses,
            "rate": self.rate,
        }


@dataclass
class ConfidenceTracker:
    """Rolling window of confidence scores."""
    name: str
    window: deque = field(default_factory=lambda: deque(maxlen=1000))

    def record(self, score: float):
        self.window.append(score)

    def stats(self) -> dict:
        if not self.window:
            return {"count": 0, "mean": None, "min": None, "max": None}
        data = list(self.window)
        return {
            "count": len(data),
            "mean": round(statistics.mean(data), 4),
            "min": round(min(data), 4),
            "max": round(max(data), 4),
        }


class MetricsStore:
    """
    Central metrics store for the ML Inference Service.
    Single instance shared across all workers.
    """

    def __init__(self):
        # Latency trackers
        self.enrichment_latency = LatencyTracker("enrichment_e2e")
        self.ner_latency = LatencyTracker("ner")
        self.lookup_latency = LatencyTracker("kb_lookup")
        self.estimator_latency = LatencyTracker("ingredient_estimator")
        self.vision_latency = LatencyTracker("vision_api")

        # Rate trackers
        self.kb_hit_rate = RateTracker("kb_hit")
        self.fallback_rate = RateTracker("fallback")   # estimator used vs lookup used

        # Confidence trackers
        self.ner_confidence = ConfidenceTracker("ner_confidence")
        self.vision_confidence = ConfidenceTracker("vision_confidence")

        # Event counters
        self.total_events_processed = 0
        self.total_events_failed = 0
        self.total_photos_processed = 0

    def summary(self) -> dict:
        return {
            "events": {
                "processed": self.total_events_processed,
                "failed": self.total_events_failed,
                "photos": self.total_photos_processed,
            },
            "latency_ms": {
                "enrichment_e2e": self.enrichment_latency.stats(),
                "ner": self.ner_latency.stats(),
                "kb_lookup": self.lookup_latency.stats(),
                "ingredient_estimator": self.estimator_latency.stats(),
                "vision_api": self.vision_latency.stats(),
            },
            "rates": {
                "kb_hit": self.kb_hit_rate.stats(),
                "fallback_used": self.fallback_rate.stats(),
            },
            "confidence": {
                "ner": self.ner_confidence.stats(),
                "vision": self.vision_confidence.stats(),
            },
        }

    def log_summary(self):
        log.info("metrics.summary", **self.summary())


# ── Context manager for timing ────────────────────────────────

class Timer:
    """Usage: async with Timer() as t: ... ; ms = t.elapsed_ms"""
    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = round((time.perf_counter() - self._start) * 1000, 2)


# ── Singleton ─────────────────────────────────────────────────
metrics = MetricsStore()
