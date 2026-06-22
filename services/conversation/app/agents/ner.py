"""
NARA — Food NER Agent
Extracts entities from user messages.
Uses spaCy now → swap to fine-tuned DistilBERT later.
"""
import logging
import re
from app.core.config import get_settings

log      = logging.getLogger("nara.conversation.ner")
settings = get_settings()

_nlp = None

FOOD_SIGNALS = {
    "idli", "dosa", "masala dosa", "rava dosa", "uttapam", "vada",
    "upma", "pongal", "curd rice", "sambar", "rasam", "biryani",
    "chicken biryani", "mutton biryani", "veg biryani", "dal makhani",
    "dal tadka", "butter chicken", "chicken curry", "palak paneer",
    "paneer tikka", "chole", "rajma", "roti", "naan", "paratha",
    "aloo paratha", "puri", "bhatura", "pav bhaji", "vada pav",
    "samosa", "pani puri", "bhel puri", "poha", "dhokla", "khichdi",
    "rice", "dal", "sabzi", "chai", "coffee", "lassi",
}

LOCATION_SIGNALS = [
    "near", "in", "at", "around", "koramangala", "indiranagar",
    "bandra", "connaught place", "anna nagar", "t nagar", "juhu",
    "whitefield", "hsr layout", "btm layout", "jayanagar",
]

CONDITION_SIGNALS = {
    "diabetic": "type2_diabetes", "diabetes": "type2_diabetes",
    "bp": "hypertension", "blood pressure": "hypertension",
    "hypertension": "hypertension", "pcos": "pcos",
    "cholesterol": "high_cholesterol", "weight": "obesity",
    "thyroid": "thyroid",
}

QUANTITY_PATTERN = re.compile(r'(\d+)\s*(plate|bowl|piece|cup|glass|kg|g|ml|l)s?', re.I)


def load_ner():
    global _nlp
    if _nlp is not None:
        return
    try:
        import spacy
        _nlp = spacy.load(settings.ner_model)
        log.info("NER: spaCy loaded")
    except Exception as e:
        log.warning(f"spaCy load failed: {e}")
        _nlp = None


def extract_entities(text: str) -> dict:
    """
    Extract entities from text.
    Returns {dishes, locations, conditions, quantities, time_context}
    """
    text_lower = text.lower()
    entities   = {
        "dishes":       [],
        "locations":    [],
        "conditions":   [],
        "quantities":   [],
        "time_context": None,
        "budget":       None,
    }

    # Extract dishes (keyword matching)
    for food in FOOD_SIGNALS:
        if food in text_lower:
            entities["dishes"].append(food)

    # Extract locations
    for loc in LOCATION_SIGNALS:
        if loc in text_lower:
            entities["locations"].append(loc)

    # Extract health conditions
    for signal, condition in CONDITION_SIGNALS.items():
        if signal in text_lower:
            if condition not in entities["conditions"]:
                entities["conditions"].append(condition)

    # Extract quantities
    for match in QUANTITY_PATTERN.finditer(text):
        entities["quantities"].append({
            "amount": int(match.group(1)),
            "unit":   match.group(2),
        })

    # Time context
    time_map = {
        "morning": "breakfast", "breakfast": "breakfast",
        "lunch": "lunch", "afternoon": "lunch",
        "evening": "snack", "snack": "snack",
        "dinner": "dinner", "night": "dinner",
        "late night": "late_night",
    }
    for word, occasion in time_map.items():
        if word in text_lower:
            entities["time_context"] = occasion
            break

    # Budget
    budget_match = re.search(r'(?:budget|under|within|less than)\s*(?:rs\.?|₹)?\s*(\d+)', text_lower)
    if budget_match:
        entities["budget"] = int(budget_match.group(1))

    # spaCy for additional entities
    if _nlp:
        try:
            doc = _nlp(text)
            for ent in doc.ents:
                if ent.label_ in ("GPE", "LOC") and ent.text.lower() not in entities["locations"]:
                    entities["locations"].append(ent.text.lower())
        except Exception:
            pass

    return entities