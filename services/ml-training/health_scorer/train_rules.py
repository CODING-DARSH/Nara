"""
NARA — Health Scorer — Baseline: Rule-based Thresholds
─────────────────────────────────────────────────────────────
INPUT FEATURES (X):
  gi_score, estimated_calories, estimated_protein_g,
  estimated_fat_g, estimated_fiber_g, has_diabetes,
  has_prediabetes, has_hypertension, has_obesity, has_pcos

PREDICTION TARGET (Y):
  health_compliant → 0 or 1

WHY RULES AS BASELINE:
  Fully interpretable, clinically grounded
  Sets floor — any ML model must beat this
  Also serves as a sanity check on synthetic data quality

RULES APPLIED:
  Diabetes/Prediabetes : GI > 70 → non-compliant
  Hypertension         : estimated sodium proxy > threshold → non-compliant
  Obesity              : calories > 600 per meal → non-compliant
  PCOS                 : GI > 65 → non-compliant (insulin resistance)

EXPECTED METRICS:
  Precision ~0.72-0.82 (rules are conservative)
  Recall    ~0.55-0.65 (rules miss subtle non-compliance)
  F1        ~0.62-0.72

Run:
  python health_scorer/train_rules.py
"""
import os
import sys
import logging
import json

import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_PATHS, HEALTH_SCORER_FEATURES, CONDITION_FLAGS
from utils import (
    load_users, load_meal_logs,
    expand_conditions,
    classification_metrics, save_metrics,
    plot_confusion_matrix,
)

log = logging.getLogger("nara.health_scorer.rules")


# ── Rule engine ───────────────────────────────────────────────

class RuleBasedHealthScorer:
    """
    Deterministic rule-based health compliance scorer.
    No training needed — rules derived from clinical guidelines.
    """

    # Thresholds sourced from:
    # - ADA (American Diabetes Association) GI guidelines
    # - WHO sodium intake guidelines
    # - ICMR caloric guidelines for Indian adults
    RULES = {
        "diabetes_gi_threshold":     70,   # ADA: low GI < 55, medium 55-70, high > 70
        "prediabetes_gi_threshold":  68,
        "pcos_gi_threshold":         65,   # PCOS: stricter GI control needed
        "obesity_cal_threshold":     600,  # kcal per meal
        "hypertension_cal_proxy":    500,  # proxy — high cal meals tend to be high sodium
    }

    def predict(self, row: pd.Series) -> int:
        gi       = float(row.get("gi_score", 55))
        calories = float(row.get("estimated_calories", 300))

        # Diabetes
        if row.get("has_diabetes", 0) == 1:
            if gi > self.RULES["diabetes_gi_threshold"]:
                return 0

        # Prediabetes
        if row.get("has_prediabetes", 0) == 1:
            if gi > self.RULES["prediabetes_gi_threshold"]:
                return 0

        # PCOS
        if row.get("has_pcos", 0) == 1:
            if gi > self.RULES["pcos_gi_threshold"]:
                return 0

        # Obesity
        if row.get("has_obesity", 0) == 1:
            if calories > self.RULES["obesity_cal_threshold"]:
                return 0

        # Hypertension — proxy via high calorie meals
        if row.get("has_hypertension", 0) == 1:
            if calories > self.RULES["hypertension_cal_proxy"]:
                return 0

        return 1

    def predict_batch(self, df: pd.DataFrame) -> np.ndarray:
        return df.apply(self.predict, axis=1).values

    def get_rule_explanation(self, row: pd.Series) -> str:
        """Return human-readable reason for non-compliance."""
        gi       = float(row.get("gi_score", 55))
        calories = float(row.get("estimated_calories", 300))
        reasons  = []

        if row.get("has_diabetes", 0) == 1 and gi > self.RULES["diabetes_gi_threshold"]:
            reasons.append(f"GI={gi} exceeds diabetic threshold of {self.RULES['diabetes_gi_threshold']}")
        if row.get("has_prediabetes", 0) == 1 and gi > self.RULES["prediabetes_gi_threshold"]:
            reasons.append(f"GI={gi} exceeds prediabetic threshold of {self.RULES['prediabetes_gi_threshold']}")
        if row.get("has_pcos", 0) == 1 and gi > self.RULES["pcos_gi_threshold"]:
            reasons.append(f"GI={gi} exceeds PCOS threshold of {self.RULES['pcos_gi_threshold']}")
        if row.get("has_obesity", 0) == 1 and calories > self.RULES["obesity_cal_threshold"]:
            reasons.append(f"Calories={calories} exceeds obesity threshold of {self.RULES['obesity_cal_threshold']}")
        if row.get("has_hypertension", 0) == 1 and calories > self.RULES["hypertension_cal_proxy"]:
            reasons.append(f"Calories={calories} flagged for hypertension")

        return "; ".join(reasons) if reasons else "compliant"


def load_and_prepare_data() -> pd.DataFrame:
    log.info("Loading data...")
    meal_logs = load_meal_logs(parse_dates=False)
    users     = load_users()

    user_cols = ["user_id", "conditions", "health_literacy", "age", "bmi", "activity_level"]
    user_slim = users[user_cols].drop_duplicates("user_id")
    df = meal_logs.merge(user_slim, on="user_id", how="left")
    df = expand_conditions(df, "conditions")

    log.info(f"  Samples: {len(df):,}")
    log.info(f"  Compliance rate: {df['health_compliant'].mean():.3f}")
    return df


def train():
    log.info("=" * 60)
    log.info("Health Scorer — Rule-based Baseline")
    log.info("=" * 60)

    df = load_and_prepare_data()

    scorer  = RuleBasedHealthScorer()
    y_pred  = scorer.predict_batch(df)
    y_true  = df["health_compliant"].fillna(1).astype(int).values

    metrics = classification_metrics(y_true, y_pred, label="ALL")

    # Per-condition breakdown
    log.info("\nPer-condition compliance accuracy:")
    for flag in CONDITION_FLAGS:
        if flag not in df.columns:
            continue
        mask = df[flag] == 1
        if mask.sum() < 10:
            continue
        acc = (y_pred[mask] == y_true[mask]).mean()
        log.info(f"  {flag:<30} n={mask.sum():>6,}  acc={acc:.3f}")

    # Sample explanations
    log.info("\nSample non-compliant explanations:")
    non_compliant = df[y_pred == 0].head(5)
    for _, row in non_compliant.iterrows():
        explanation = scorer.get_rule_explanation(row)
        log.info(f"  {row.get('dish_name', 'unknown')[:30]:<30} → {explanation}")

    plot_confusion_matrix(
        y_true, y_pred,
        labels=["non_compliant", "compliant"],
        title="Health Scorer Rules — Confusion Matrix",
        filename="health_rules_cm.png",
    )

    # Save scorer rules as JSON (no model artifact needed)
    os.makedirs(os.path.dirname(MODEL_PATHS["health_rf"]), exist_ok=True)
    rules_path = os.path.join(os.path.dirname(MODEL_PATHS["health_rf"]), "health_rules.json")
    with open(rules_path, "w") as f:
        json.dump({"rules": scorer.RULES, "metrics": metrics}, f, indent=2)
    log.info(f"Rules saved → {rules_path}")
    save_metrics({"all": metrics}, "health_rules")

    log.info("\n" + "=" * 60)
    log.info("SUMMARY — Health Scorer Rules")
    log.info(f"  Accuracy  : {metrics['accuracy']}")
    log.info(f"  Precision : {metrics['precision']}")
    log.info(f"  Recall    : {metrics['recall']}")
    log.info(f"  F1        : {metrics['f1']}")
    log.info("=" * 60)

    return scorer, metrics


if __name__ == "__main__":
    train()
