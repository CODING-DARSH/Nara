"""
Run this once against your real encoders.joblib to get the exact category
strings the occasion_xgb / health_xgb / ranker models were trained on.

Usage (from services/ml-training/):
    python inspect_encoders.py

Paste the full output back — I'll lock VALID_OCCUPATIONS / VALID_LIVING_
SITUATIONS / VALID_STRESS_LEVELS in
services/user-intelligence/app/schemas/intelligence.py to match exactly,
instead of the placeholder guesses currently there.
"""
import joblib
import os
import sys

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
ENCODERS_PATH = os.path.join(MODELS_DIR, "encoders.joblib")


def main():
    # FIX: the docstring/help text documented an optional path argument
    # but main() never actually read sys.argv — the override was
    # advertised but not implemented. Fixed here.
    path = sys.argv[1] if len(sys.argv) > 1 else ENCODERS_PATH

    if not os.path.exists(path):
        print(f"Not found: {path}")
        print("Pass the correct path if your models/ dir is elsewhere:")
        print("  python inspect_encoders.py /path/to/encoders.joblib")
        return

    encoders = joblib.load(path)

    print(f"Loaded encoders.joblib — top-level type: {type(encoders)}")
    print("=" * 60)

    # Real shape confirmed from utils.py: FeatureEncoder.label_encoders is
    # the dict of {column_name: LabelEncoder}. My first guess (.encoders)
    # was wrong — fixed after seeing the actual class definition.
    items = None
    if isinstance(encoders, dict):
        items = encoders.items()
    elif hasattr(encoders, "label_encoders") and isinstance(encoders.label_encoders, dict):
        items = encoders.label_encoders.items()
    elif hasattr(encoders, "encoders") and isinstance(encoders.encoders, dict):
        items = encoders.encoders.items()
    else:
        print("Unrecognized encoders.joblib structure. Raw repr:")
        print(repr(encoders)[:2000])
        print("Available attributes:", [a for a in dir(encoders) if not a.startswith("_")])
        return

    interesting = {
        "occupation", "living_situation", "stress_level", "context_stress",
        "income_tier", "region", "season", "month_position",
    }

    for name, enc in items:
        classes = getattr(enc, "classes_", None)
        if classes is None:
            print(f"{name}: (no classes_ attribute, type={type(enc)})")
            continue
        marker = "  <-- NEEDED" if name in interesting else ""
        print(f"{name}: {list(classes)}{marker}")


if __name__ == "__main__":
    main()