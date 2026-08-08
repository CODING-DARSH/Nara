"""
NARA — Meal Occasion Classifier — Mid: Random Forest
─────────────────────────────────────────────────────────────
INPUT FEATURES (X):
  Numerical : hour, day_of_week, month, budget_availability,
              commute_minutes, age
  Categorical: season, stress_level, month_position,
               occupation, living_situation
  Binary    : is_weekend, cooking_at_home, ordered_delivery,
              is_festival_day, is_fast_day, is_wfh

PREDICTION TARGET (Y):
  meal_occasion → breakfast / lunch / snack / dinner / late_night

WHY RANDOM FOREST OVER DECISION TREE:
  Ensemble of 300 trees reduces overfitting
  Captures interactions: student + 11pm + weekend = late_night
  Decision tree misses these cross-feature patterns
  OOB score gives free validation estimate

EXPECTED METRICS:
  Accuracy ~0.76-0.83
  F1 weighted ~0.74-0.81

Run:
  python meal_occasion_classifier/train_random_forest.py
"""
import os
import sys
import logging

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_PATHS, OCCASION_FEATURES, OCCASION_MAP, RF_PARAMS
from utils import (
    load_users, load_meal_logs,
    extract_hour_from_timestamp,
    FeatureEncoder, split_data,
    classification_metrics, save_metrics,
    save_sklearn_model,
    plot_confusion_matrix, plot_feature_importance,
)

log = logging.getLogger("nara.occasion.rf")


def load_and_prepare_data() -> tuple:
    log.info("Loading data...")
    meal_logs = load_meal_logs(parse_dates=True)
    users     = load_users()

    user_cols = ["user_id", "occupation", "age", "living_situation",
                 "commute_minutes", "is_wfh"]
    user_slim = users[user_cols].drop_duplicates("user_id")
    df = meal_logs.merge(user_slim, on="user_id", how="left")
    df = extract_hour_from_timestamp(df, "occurred_at")
    df = df[df["meal_occasion"].notna()]
    df = df[df["meal_occasion"].isin(OCCASION_MAP.keys())]

    num_cols = [c for c in OCCASION_FEATURES["numerical"]  if c in df.columns]
    cat_cols = [c for c in OCCASION_FEATURES["categorical"] if c in df.columns]
    bin_cols = [c for c in OCCASION_FEATURES["binary"]      if c in df.columns]

    df[num_cols] = df[num_cols].fillna(0)
    df[bin_cols] = df[bin_cols].fillna(0).astype(int)

    encoder = FeatureEncoder()
    df_enc  = encoder.fit_transform(df.copy(), cat_cols, num_cols)

    feature_cols = num_cols + cat_cols + bin_cols
    X = df_enc[feature_cols].fillna(0)
    y = df["meal_occasion"]

    log.info(f"  Features: {len(feature_cols)} | Samples: {len(X):,}")
    return X, y, feature_cols, encoder


def train():
    log.info("=" * 60)
    log.info("Meal Occasion Classifier — Random Forest (Mid)")
    log.info("=" * 60)

    X, y, feature_cols, encoder = load_and_prepare_data()
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)

    log.info("Training Random Forest...")
    params = {**RF_PARAMS, "oob_score": True}
    model  = RandomForestClassifier(**params)
    model.fit(X_train, y_train)

    log.info(f"  OOB Score: {model.oob_score_:.4f}")

    y_val_pred   = model.predict(X_val)
    y_val_prob   = model.predict_proba(X_val)
    val_metrics  = classification_metrics(y_val, y_val_pred, y_val_prob, label="VAL")

    y_test_pred  = model.predict(X_test)
    y_test_prob  = model.predict_proba(X_test)
    test_metrics = classification_metrics(y_test, y_test_pred, y_test_prob, label="TEST")

    # Per-occasion breakdown
    log.info("\nPer-occasion accuracy:")
    for occasion in OCCASION_MAP.keys():
        mask = y_test == occasion
        if mask.sum() < 5:
            continue
        acc = (y_test_pred[mask] == y_test.values[mask]).mean()
        log.info(f"  {occasion:<15} n={mask.sum():>6,}  acc={acc:.3f}")

    importances = model.feature_importances_
    plot_confusion_matrix(
        y_test, y_test_pred,
        labels=list(OCCASION_MAP.keys()),
        title="Occasion RF — Confusion Matrix",
        filename="occasion_rf_cm.png",
    )
    plot_feature_importance(
        feature_cols, list(importances),
        title="Occasion RF — Feature Importance",
        filename="occasion_rf_fi.png",
    )

    metadata = {
        "model":        "RandomForest",
        "features":     feature_cols,
        "oob_score":    model.oob_score_,
        "val_metrics":  val_metrics,
        "test_metrics": test_metrics,
    }
    save_sklearn_model(model, MODEL_PATHS["occasion_rf"], metadata)
    save_metrics({"val": val_metrics, "test": test_metrics}, "occasion_rf")

    log.info("\n" + "=" * 60)
    log.info("SUMMARY — Occasion Random Forest")
    log.info(f"  OOB Score     : {model.oob_score_:.4f}")
    log.info(f"  Test Accuracy : {test_metrics['accuracy']}")
    log.info(f"  Test F1       : {test_metrics['f1']}")
    log.info(f"  Model saved   : {MODEL_PATHS['occasion_rf']}")
    log.info("=" * 60)

    return model, test_metrics


if __name__ == "__main__":
    train()
