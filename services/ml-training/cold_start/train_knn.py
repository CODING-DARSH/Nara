"""
NARA — Cold Start — Baseline: KNN
─────────────────────────────────────────────────────────────
INPUT FEATURES (X):
  Numerical : age, health_literacy, habit_strength, bmi,
              observance_level, order_frequency_weekly
  Categorical: birthplace_state, current_state, religion,
               gender, occupation, income_tier,
               living_situation, activity_level
  Binary    : is_vegetarian, is_jain, is_halal
  Multi-hot : conditions (expanded), dietary_restrictions (expanded)

PREDICTION TARGET (Y):
  top_cuisine — most frequent cuisine type in user's meal history
  Derived from meal_logs: groupby user_id + cuisine_type, take mode

WHY KNN AS BASELINE:
  No training needed — just distance in demographic space
  Directly interpretable: "users similar to you eat X"
  Sets the floor — any model should beat demographic similarity

EXPECTED METRICS:
  Top-1 accuracy ~0.38-0.48
  Top-3 accuracy ~0.65-0.75

Run:
  python cold_start/train_knn.py
"""
import os
import sys
import logging

import numpy as np
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import top_k_accuracy_score

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_PATHS, COLD_START_FEATURES
from utils import (
    load_users, load_meal_logs,
    expand_conditions, derive_top_cuisine_per_user,
    FeatureEncoder, split_data,
    classification_metrics,
    save_sklearn_model, save_metrics,
    plot_confusion_matrix, plot_feature_importance,
)

log = logging.getLogger("nara.cold_start.knn")


def load_and_prepare_data() -> tuple:
    log.info("Loading data...")
    users     = load_users()
    meal_logs = load_meal_logs(parse_dates=False)

    # ── Derive Y: top cuisine per user ────────────────────────
    top_cuisine = derive_top_cuisine_per_user(meal_logs)
    df = users.merge(top_cuisine, on="user_id", how="inner")
    log.info(f"  Users with meal history: {len(df):,}")

    # ── Expand conditions ─────────────────────────────────────
    df = expand_conditions(df, "conditions")

    # Expand dietary restrictions
    restriction_flags = [
        "vegetarian", "low_gi", "low_sodium", "no_dairy",
        "no_gluten", "halal", "jain", "no_beef",
    ]
    for flag in restriction_flags:
        df[f"restr_{flag}"] = df["dietary_restrictions"].fillna("").str.contains(
            flag, regex=False
        ).astype(int)

    num_cols = [c for c in COLD_START_FEATURES["numerical"]  if c in df.columns]
    cat_cols = [c for c in COLD_START_FEATURES["categorical"] if c in df.columns]
    bin_cols = [c for c in COLD_START_FEATURES["binary"]      if c in df.columns]

    from config import CONDITION_FLAGS
    cond_cols  = [c for c in CONDITION_FLAGS if c in df.columns]
    restr_cols = [f"restr_{f}" for f in restriction_flags if f"restr_{f}" in df.columns]
    bin_cols   = list(set(bin_cols + cond_cols + restr_cols))

    df[num_cols] = df[num_cols].fillna(0)
    df[bin_cols] = df[bin_cols].fillna(0).astype(int)

    encoder = FeatureEncoder()
    df_enc = encoder.fit_transform(df.copy(), cat_cols, num_cols)

    feature_cols = num_cols + cat_cols + bin_cols
    X = df_enc[feature_cols].fillna(0)
    y = df["top_cuisine"]

    log.info(f"  Features: {len(feature_cols)} | Samples: {len(X):,}")
    log.info(f"  Cuisine distribution:\n{y.value_counts().head(10)}")
    return X, y, feature_cols, encoder


def train():
    log.info("=" * 60)
    log.info("Cold Start — KNN (Baseline)")
    log.info("=" * 60)
    
    X, y, feature_cols, encoder = load_and_prepare_data()
    counts = y.value_counts()
    rare_classes = counts[counts < 10].index
    y = y.replace(rare_classes, "other")
    print(y.value_counts())
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)

    # ── Train ─────────────────────────────────────────────────
    log.info("Training KNN (k=15)...")
    model = KNeighborsClassifier(
        n_neighbors=15,
        metric="euclidean",
        n_jobs=-1,
        weights="distance",
    )
    model.fit(X_train, y_train)

    # ── Evaluate ──────────────────────────────────────────────
    y_val_pred  = model.predict(X_val)
    y_val_prob  = model.predict_proba(X_val)
    val_metrics = classification_metrics(y_val, y_val_pred, label="VAL")

    # Top-3 accuracy
    try:
        top3_val = top_k_accuracy_score(y_val, y_val_prob, k=3, labels=model.classes_)
        val_metrics["top3_accuracy"] = round(top3_val, 4)
        log.info(f"[VAL] Top-3 accuracy: {top3_val:.4f}")
    except Exception:
        pass

    y_test_pred  = model.predict(X_test)
    y_test_prob  = model.predict_proba(X_test)
    test_metrics = classification_metrics(y_test, y_test_pred, label="TEST")

    try:
        top3_test = top_k_accuracy_score(y_test, y_test_prob, k=3, labels=model.classes_)
        test_metrics["top3_accuracy"] = round(top3_test, 4)
        log.info(f"[TEST] Top-3 accuracy: {top3_test:.4f}")
    except Exception:
        pass

    # ── Plots ─────────────────────────────────────────────────
    plot_confusion_matrix(
        y_test, y_test_pred,
        labels=list(model.classes_),
        title="Cold Start KNN — Confusion Matrix",
        filename="cold_start_knn_cm.png",
    )

    # ── Save ──────────────────────────────────────────────────
    metadata = {
        "model":        "KNN",
        "k":            15,
        "features":     feature_cols,
        "val_metrics":  val_metrics,
        "test_metrics": test_metrics,
        "classes":      list(model.classes_),
    }
    save_sklearn_model(model, MODEL_PATHS["cold_start_knn"], metadata)
    save_metrics({"val": val_metrics, "test": test_metrics}, "cold_start_knn")

    log.info("\n" + "=" * 60)
    log.info("SUMMARY — Cold Start KNN")
    log.info(f"  Test Accuracy     : {test_metrics['accuracy']}")
    log.info(f"  Test Top-3 Acc    : {test_metrics.get('top3_accuracy', 'n/a')}")
    log.info(f"  Test F1           : {test_metrics['f1']}")
    log.info(f"  Model saved       : {MODEL_PATHS['cold_start_knn']}")
    log.info("=" * 60)

    return model, test_metrics


if __name__ == "__main__":
    train()
