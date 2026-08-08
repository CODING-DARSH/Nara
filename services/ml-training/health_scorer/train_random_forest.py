"""
NARA — Health Scorer — Mid: Random Forest
─────────────────────────────────────────────────────────────
INPUT FEATURES (X):
  Numerical : gi_score, estimated_calories, estimated_protein_g,
              estimated_carbs_g, estimated_fat_g, estimated_fiber_g,
              portion_multiplier, age, bmi, health_literacy
  Categorical: meal_occasion, season, stress_level, activity_level
  Binary    : is_festival_day, is_fast_day, is_vegetarian,
              has_diabetes, has_prediabetes, has_hypertension,
              has_obesity, has_pcos, has_high_cholesterol

PREDICTION TARGET (Y):
  health_compliant → 0 or 1

WHY RANDOM FOREST OVER RULES:
  Learns interaction effects rules miss:
  "stressed + festival + diabetic = non-compliant even for medium GI dish"
  Handles non-linear boundaries between compliant/non-compliant
  Feature importance shows which factors actually drive compliance

EXPECTED METRICS:
  Accuracy  ~0.80-0.87
  F1        ~0.79-0.86
  AUC       ~0.85-0.91

Run:
  python health_scorer/train_random_forest.py
"""
import os
import sys
import logging

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_PATHS, HEALTH_SCORER_FEATURES, RF_PARAMS, CONDITION_FLAGS
from utils import (
    load_users, load_meal_logs,
    expand_conditions,
    FeatureEncoder, split_data,
    classification_metrics, save_metrics,
    save_sklearn_model,
    plot_confusion_matrix, plot_feature_importance,
)

log = logging.getLogger("nara.health_scorer.rf")


def load_and_prepare_data() -> tuple:
    log.info("Loading data...")
    meal_logs = load_meal_logs(parse_dates=False)
    users     = load_users()

    user_cols = [
        "user_id", "conditions", "health_literacy",
        "age", "bmi", "activity_level", "is_vegetarian",
    ]
    user_slim = users[user_cols].drop_duplicates("user_id")
    df = meal_logs.merge(user_slim, on="user_id", how="left")
    df = expand_conditions(df, "conditions")

    num_cols = [c for c in HEALTH_SCORER_FEATURES["numerical"]  if c in df.columns]
    cat_cols = [c for c in HEALTH_SCORER_FEATURES["categorical"] if c in df.columns]
    bin_cols = [c for c in HEALTH_SCORER_FEATURES["binary"]      if c in df.columns]
    cond_cols= [c for c in CONDITION_FLAGS if c in df.columns]
    bin_cols = list(set(bin_cols + cond_cols))

    df[num_cols] = df[num_cols].fillna(0)
    df[bin_cols] = df[bin_cols].fillna(0).astype(int)

    encoder = FeatureEncoder()
    df = encoder.fit_transform(df, cat_cols, num_cols)

    feature_cols = num_cols + cat_cols + bin_cols
    X = df[feature_cols].fillna(0)
    y = df["health_compliant"].fillna(1).astype(int)

    log.info(f"  Features: {len(feature_cols)} | Samples: {len(X):,}")
    log.info(f"  Compliance rate: {y.mean():.3f}")
    return X, y, feature_cols, encoder


def train():
    log.info("=" * 60)
    log.info("Health Scorer — Random Forest (Mid)")
    log.info("=" * 60)

    X, y, feature_cols, encoder = load_and_prepare_data()
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)

    log.info("Training Random Forest...")
    model = RandomForestClassifier(**RF_PARAMS)
    model.fit(X_train, y_train)

    # ── Evaluate ──────────────────────────────────────────────
    y_val_pred   = model.predict(X_val)
    y_val_prob   = model.predict_proba(X_val)
    val_metrics  = classification_metrics(y_val, y_val_pred, y_val_prob, label="VAL")

    y_test_pred  = model.predict(X_test)
    y_test_prob  = model.predict_proba(X_test)
    test_metrics = classification_metrics(y_test, y_test_pred, y_test_prob, label="TEST")

    # Per-condition breakdown
    df_test = X_test.copy()
    df_test["y_true"] = y_test.values
    df_test["y_pred"] = y_test_pred

    log.info("\nPer-condition F1:")
    for flag in CONDITION_FLAGS:
        if flag not in df_test.columns:
            continue
        mask = df_test[flag] == 1
        if mask.sum() < 10:
            continue
        from sklearn.metrics import f1_score
        f1 = f1_score(df_test[mask]["y_true"], df_test[mask]["y_pred"], zero_division=0)
        log.info(f"  {flag:<30} n={mask.sum():>6,}  F1={f1:.3f}")

    # ── Feature importance ────────────────────────────────────
    importances = model.feature_importances_
    fi_df = pd.DataFrame({
        "feature":    feature_cols,
        "importance": importances,
    }).sort_values("importance", ascending=False).head(15)
    log.info(f"\nTop 15 features:\n{fi_df.to_string(index=False)}")

    plot_confusion_matrix(
        y_test, y_test_pred,
        labels=["non_compliant", "compliant"],
        title="Health Scorer RF — Confusion Matrix",
        filename="health_rf_cm.png",
    )
    plot_feature_importance(
        feature_cols, list(importances),
        title="Health Scorer RF — Feature Importance",
        filename="health_rf_fi.png",
    )

    metadata = {
        "model":        "RandomForest",
        "features":     feature_cols,
        "val_metrics":  val_metrics,
        "test_metrics": test_metrics,
    }
    save_sklearn_model(model, MODEL_PATHS["health_rf"], metadata)
    save_metrics({"val": val_metrics, "test": test_metrics}, "health_rf")

    log.info("\n" + "=" * 60)
    log.info("SUMMARY — Health Scorer Random Forest")
    log.info(f"  Test Accuracy : {test_metrics['accuracy']}")
    log.info(f"  Test F1       : {test_metrics['f1']}")
    log.info(f"  Test AUC      : {test_metrics.get('auc', 'n/a')}")
    log.info(f"  Model saved   : {MODEL_PATHS['health_rf']}")
    log.info("=" * 60)

    return model, test_metrics


if __name__ == "__main__":
    train()
