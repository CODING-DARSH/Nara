"""
NARA — Reorder Prediction — Mid: Random Forest
─────────────────────────────────────────────────────────────
INPUT FEATURES (X):
  Numerical : days_between, total_orders_dish, last_rating_proxy,
              habit_strength, health_literacy, age,
              order_frequency_weekly
  Categorical: trigger_type, income_tier, occupation,
               stress_profile, season, month_position
  Binary    : is_vegetarian

PREDICTION TARGET (Y):
  reordered_yes_no → True / False

WHY RANDOM FOREST OVER LOGISTIC:
  Captures non-linear patterns:
    "high habit_strength + low days_between + festival = very high reorder"
    Logistic sees these as additive, RF sees the interaction
  OOB score gives free honest estimate
  Better on imbalanced reorder/no-reorder ratio

EXPECTED METRICS:
  Accuracy ~0.72-0.79
  AUC      ~0.78-0.85
  F1       ~0.70-0.77

Run:
  python reorder_prediction/train_random_forest.py
"""
import os
import sys
import logging

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_PATHS, REORDER_FEATURES, RF_PARAMS
from utils import (
    load_users, load_reorder_events,
    derive_season_from_date, derive_month_position,
    FeatureEncoder, split_data,
    classification_metrics, save_metrics,
    save_sklearn_model,
    plot_confusion_matrix, plot_feature_importance,
)

log = logging.getLogger("nara.reorder.rf")


def load_and_prepare_data() -> tuple:
    log.info("Loading data...")
    reorders = load_reorder_events()
    users    = load_users()

    user_cols = [
        "user_id", "income_tier", "habit_strength", "health_literacy",
        "age", "occupation", "stress_profile", "is_vegetarian",
        "order_frequency_weekly",
    ]
    user_slim = users[user_cols].drop_duplicates("user_id")
    df = reorders.merge(user_slim, on="user_id", how="left")

    df["reorder_date"]  = pd.to_datetime(df["reorder_date"], errors="coerce")
    df["season"]        = derive_season_from_date(df["reorder_date"])
    df["month_position"]= derive_month_position(df["reorder_date"])
    df["reordered_yes_no"] = df["reordered_yes_no"].astype(int)

    num_cols = [c for c in REORDER_FEATURES["numerical"]  if c in df.columns]
    cat_cols = [c for c in REORDER_FEATURES["categorical"] if c in df.columns]
    bin_cols = [c for c in REORDER_FEATURES["binary"]      if c in df.columns]

    df[num_cols] = df[num_cols].fillna(0)
    df[bin_cols] = df[bin_cols].fillna(0).astype(int)

    encoder = FeatureEncoder()
    df_enc  = encoder.fit_transform(df.copy(), cat_cols, num_cols)

    feature_cols = num_cols + cat_cols + bin_cols
    X = df_enc[feature_cols].fillna(0)
    y = df["reordered_yes_no"]

    log.info(f"  Features: {len(feature_cols)} | Samples: {len(X):,}")
    log.info(f"  Reorder rate: {y.mean():.3f}")
    return X, y, feature_cols, encoder


def train():
    log.info("=" * 60)
    log.info("Reorder Prediction — Random Forest (Mid)")
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

    importances = model.feature_importances_
    fi_df = pd.DataFrame({
        "feature":    feature_cols,
        "importance": importances,
    }).sort_values("importance", ascending=False).head(15)
    log.info(f"\nTop 15 features:\n{fi_df.to_string(index=False)}")

    plot_confusion_matrix(
        y_test, y_test_pred,
        labels=["no_reorder", "reorder"],
        title="Reorder RF — Confusion Matrix",
        filename="reorder_rf_cm.png",
    )
    plot_feature_importance(
        feature_cols, list(importances),
        title="Reorder RF — Feature Importance",
        filename="reorder_rf_fi.png",
    )

    metadata = {
        "model":        "RandomForest",
        "features":     feature_cols,
        "oob_score":    model.oob_score_,
        "val_metrics":  val_metrics,
        "test_metrics": test_metrics,
    }
    save_sklearn_model(model, MODEL_PATHS["reorder_rf"], metadata)
    save_metrics({"val": val_metrics, "test": test_metrics}, "reorder_rf")

    log.info("\n" + "=" * 60)
    log.info("SUMMARY — Reorder Random Forest")
    log.info(f"  OOB Score     : {model.oob_score_:.4f}")
    log.info(f"  Test Accuracy : {test_metrics['accuracy']}")
    log.info(f"  Test F1       : {test_metrics['f1']}")
    log.info(f"  Test AUC      : {test_metrics.get('auc', 'n/a')}")
    log.info(f"  Model saved   : {MODEL_PATHS['reorder_rf']}")
    log.info("=" * 60)

    return model, test_metrics


if __name__ == "__main__":
    train()