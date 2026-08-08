"""
NARA — Intent Classifier
Uses DistilBERT zero-shot classification.
When fine-tuned model is ready: change model path in config.
"""
import logging
from app.core.config import get_settings

log      = logging.getLogger("nara.conversation.intent")
settings = get_settings()

_classifier = None


def load_classifier():
    global _classifier
    if _classifier is not None:
        return
    try:
        from transformers import pipeline
        _classifier = pipeline(
            "zero-shot-classification",
            model="typeform/distilbert-base-uncased-mnli",
            device=-1,  # CPU
        )
        log.info("Intent classifier loaded: DistilBERT zero-shot")
    except Exception as e:
        log.warning(f"DistilBERT load failed: {e}. Using keyword fallback.")
        _classifier = None


# ── Keyword fallback (works without transformers) ─────────────
INTENT_KEYWORDS = {
    "get_recommendation": [
        "hungry", "recommend", "suggest", "what should i eat",
        "what to eat", "food near", "show me", "craving",
    ],
    "log_meal": [
        "had", "ate", "eating", "just had", "logged", "log",
        "i ate", "i had", "breakfast was", "lunch was", "dinner was",
    ],
    "ask_nutrition": [
        "calories", "protein", "carbs", "fat", "nutrition",
        "healthy", "gi", "glycemic", "fiber", "how much",
    ],
    "check_food_graph": [
        "food graph", "history", "what i ate", "my meals",
        "pattern", "intake", "summary", "week",
    ],
    "set_preference": [
        "prefer", "like", "dont like", "vegetarian", "vegan",
        "allergy", "avoid", "budget", "spicy",
    ],
    "order_food": [
        "order", "delivery", "zomato", "swiggy", "place order",
        "buy", "get food",
    ],
    "general_chat": [],
}


def classify_intent(text: str) -> dict:
    """
    Classify intent from user message.
    Returns {intent, confidence, all_scores}
    """
    text_lower = text.lower()

    # Try DistilBERT first
    if _classifier is not None:
        try:
            result = _classifier(
                text,
                candidate_labels=settings.intent_labels,
                multi_label=False,
            )
            top_intent = result["labels"][0]
            top_score  = result["scores"][0]
            return {
                "intent":     top_intent,
                "confidence": round(top_score, 4),
                "all_scores": dict(zip(result["labels"], result["scores"])),
                "method":     "distilbert",
            }
        except Exception as e:
            log.debug(f"DistilBERT inference failed: {e}")

    # Keyword fallback
    scores = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[intent] = score

    best_intent = max(scores, key=scores.get)
    best_score  = scores[best_intent]

    if best_score == 0:
        best_intent = "general_chat"
        confidence  = 0.5
    else:
        confidence = min(0.9, 0.5 + best_score * 0.1)

    return {
        "intent":     best_intent,
        "confidence": round(confidence, 4),
        "all_scores": scores,
        "method":     "keyword_fallback",
    }
