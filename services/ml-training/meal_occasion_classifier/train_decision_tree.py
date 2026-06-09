"""
NARA — Meal Occasion Classifier — Baseline: Decision Tree
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

WHY DECISION TREE AS BASELINE:
  Hour of day is the dominant feature — tree splits on it first
  Fully interpretable: "if hour < 10 → breakfast"
  Fast inference, zero latency overhead
  Sets floor for RF and XGBoost to beat

EXPECTED METRICS:
  Accuracy ~0.65-0.72
  F1 weighted ~0.63-0.70

Run:
  python meal_occasion_classifier/train_decision_tree.py
"""
import os
import sys
import logging

import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_PATHS, OCCASION_FEATURES, OCCASION_MAP, DT_PARAMS
from utils import (
    load_users, load_meal_logs,
    extract_hour_from_timestamp,
    FeatureEncoder, split_data,
    classification_metrics, save_metrics,
    save_sklearn_model,
    plot_confusion_matrix, plot_feature_importance,
)

log = logging.getLogger("nara.occasion.dt")


def load_and_prepare_data() -> tuple:
    log.info("Loading data...")
    meal_logs = load_meal_logs(parse_dates=True)
    users     = load_users()

    user_cols = ["user_id", "occupation", "age", "living_situation",
                 "commute_minutes", "is_wfh"]
    user_slim = users[user_cols].drop_duplicates("user_id")
    df = meal_logs.merge(user_slim, on="user_id", how="left")

    df = extract_hour_from_timestamp(df, "occurred_at")

    # Drop rows with missing target
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
    log.info(f"  Class distribution:\n{y.value_counts().to_string()}")
    return X, y, feature_cols, encoder


def train():
    log.info("=" * 60)
    log.info("Meal Occasion Classifier — Decision Tree (Baseline)")
    log.info("=" * 60)

    X, y, feature_cols, encoder = load_and_prepare_data()
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)

    log.info("Training Decision Tree...")
    model = DecisionTreeClassifier(**DT_PARAMS)
    model.fit(X_train, y_train)

    log.info(f"  Tree depth: {model.get_depth()} | Leaves: {model.get_n_leaves()}")

    # Print top-level tree rules
    tree_rules = export_text(model, feature_names=feature_cols, max_depth=3)
    log.info(f"\nTop-level decision rules:\n{tree_rules}")

    y_val_pred   = model.predict(X_val)
    val_metrics  = classification_metrics(y_val, y_val_pred, label="VAL")

    y_test_pred  = model.predict(X_test)
    test_metrics = classification_metrics(y_test, y_test_pred, label="TEST")

    importances = model.feature_importances_
    fi_df = pd.DataFrame({
        "feature":    feature_cols,
        "importance": importances,
    }).sort_values("importance", ascending=False).head(10)
    log.info(f"\nTop 10 features:\n{fi_df.to_string(index=False)}")

    plot_confusion_matrix(
        y_test, y_test_pred,
        labels=list(OCCASION_MAP.keys()),
        title="Occasion DT — Confusion Matrix",
        filename="occasion_dt_cm.png",
    )
    plot_feature_importance(
        feature_cols, list(importances),
        title="Occasion DT — Feature Importance",
        filename="occasion_dt_fi.png",
    )

    metadata = {
        "model":        "DecisionTree",
        "features":     feature_cols,
        "val_metrics":  val_metrics,
        "test_metrics": test_metrics,
        "tree_depth":   model.get_depth(),
        "n_leaves":     model.get_n_leaves(),
    }
    save_sklearn_model(model, MODEL_PATHS["occasion_dt"], metadata)
    save_metrics({"val": val_metrics, "test": test_metrics}, "occasion_dt")

    log.info("\n" + "=" * 60)
    log.info("SUMMARY — Occasion Decision Tree")
    log.info(f"  Test Accuracy : {test_metrics['accuracy']}")
    log.info(f"  Test F1       : {test_metrics['f1']}")
    log.info(f"  Model saved   : {MODEL_PATHS['occasion_dt']}")
    log.info("=" * 60)

    return model, test_metrics


if __name__ == "__main__":
    train()