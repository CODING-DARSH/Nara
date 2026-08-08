"""
NARA — Meal Occasion Classifier — Best: XGBoost
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

WHY XGBOOST OVER RANDOM FOREST:
  Gradient boosting: each tree corrects previous tree's errors
  Better on imbalanced classes (late_night is rare)
  Early stopping prevents overfitting automatically
  Regularization (gamma, alpha, lambda) reduces variance

EXPECTED METRICS:
  Accuracy ~0.82-0.88
  F1 weighted ~0.80-0.87

Run:
  python meal_occasion_classifier/train_xgboost.py
"""
import os
import sys
import logging

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_PATHS, OCCASION_FEATURES, OCCASION_MAP, XGB_PARAMS
from utils import (
    load_users, load_meal_logs,
    extract_hour_from_timestamp,
    FeatureEncoder, split_data,
    classification_metrics, save_metrics,
    save_xgboost_model,
    plot_confusion_matrix, plot_feature_importance,
)

log = logging.getLogger("nara.occasion.xgboost")


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

    # XGBoost needs integer class labels
    le = LabelEncoder()
    y_raw = df["meal_occasion"]
    y     = pd.Series(le.fit_transform(y_raw), index=y_raw.index)

    log.info(f"  Features: {len(feature_cols)} | Samples: {len(X):,}")
    log.info(f"  Classes: {list(le.classes_)}")
    return X, y, feature_cols, encoder, le


def train():
    log.info("=" * 60)
    log.info("Meal Occasion Classifier — XGBoost (Best)")
    log.info("=" * 60)

    X, y, feature_cols, encoder, le = load_and_prepare_data()
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)

    log.info("Training XGBoost...")
    params = {
        **XGB_PARAMS,
        "objective":  "multi:softprob",
        "num_class":  len(le.classes_),
        "eval_metric":"mlogloss",
    }
    model = xgb.XGBClassifier(**params, early_stopping_rounds=20)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=50,
    )
    log.info(f"  Best iteration: {model.best_iteration}")

    # Decode predictions back to string labels
    y_val_pred_int  = model.predict(X_val)
    y_val_pred      = le.inverse_transform(y_val_pred_int)
    y_val_labels    = le.inverse_transform(y_val)
    y_val_prob      = model.predict_proba(X_val)
    val_metrics     = classification_metrics(y_val_labels, y_val_pred, label="VAL")

    y_test_pred_int = model.predict(X_test)
    y_test_pred     = le.inverse_transform(y_test_pred_int)
    y_test_labels   = le.inverse_transform(y_test)
    y_test_prob     = model.predict_proba(X_test)
    test_metrics    = classification_metrics(y_test_labels, y_test_pred, label="TEST")

    # Per-occasion performance
    log.info("\nPer-occasion F1:")
    from sklearn.metrics import f1_score
    for i, occasion in enumerate(le.classes_):
        mask = y_test == i
        if mask.sum() < 5:
            continue
        f1 = f1_score(y_test_labels, y_test_pred,
                      labels=[occasion], average="macro", zero_division=0)
        log.info(f"  {occasion:<15} n={mask.sum():>6,}  F1={f1:.3f}")

    importances = model.feature_importances_
    plot_confusion_matrix(
        y_test_labels, y_test_pred,
        labels=list(le.classes_),
        title="Occasion XGBoost — Confusion Matrix",
        filename="occasion_xgb_cm.png",
    )
    plot_feature_importance(
        feature_cols, list(importances),
        title="Occasion XGBoost — Feature Importance",
        filename="occasion_xgb_fi.png",
    )

    save_xgboost_model(
        model,
        MODEL_PATHS["occasion_xgb"],
        onnx_path=MODEL_PATHS["occasion_xgb_onnx"],
        feature_names=feature_cols,
    )
    save_metrics({"val": val_metrics, "test": test_metrics}, "occasion_xgb")

    log.info("\n" + "=" * 60)
    log.info("SUMMARY — Occasion XGBoost")
    log.info(f"  Test Accuracy : {test_metrics['accuracy']}")
    log.info(f"  Test F1       : {test_metrics['f1']}")
    log.info(f"  Best iter     : {model.best_iteration}")
    log.info(f"  Model saved   : {MODEL_PATHS['occasion_xgb']}")
    log.info("=" * 60)

    return model, test_metrics


if __name__ == "__main__":
    train()
