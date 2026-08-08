"""
NARA — Health Scorer — Best: XGBoost + SHAP
─────────────────────────────────────────────────────────────
INPUT FEATURES (X):
  Same as Random Forest but XGBoost captures deeper interactions.
  SHAP values added for per-prediction explainability.

PREDICTION TARGET (Y):
  health_compliant → 0 or 1

WHY XGBOOST + SHAP:
  XGBoost: better accuracy than RF on this tabular data
  SHAP: every prediction gets an explanation
    "This dish flagged because: GI contributes +0.42, diabetes flag +0.38"
  Critical for health recommendations — users need to trust explanations
  SHAP values are additive: sum of all SHAP = prediction score

EXPECTED METRICS:
  Accuracy ~0.85-0.91
  F1       ~0.84-0.90
  AUC      ~0.90-0.95

Run:
  python health_scorer/train_xgboost_shap.py
"""
import os
import sys
import logging

import numpy as np
import pandas as pd
import xgboost as xgb

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_PATHS, HEALTH_SCORER_FEATURES, XGB_PARAMS, CONDITION_FLAGS
from utils import (
    load_users, load_meal_logs,
    expand_conditions,
    FeatureEncoder, split_data,
    classification_metrics, save_metrics,
    save_xgboost_model,
    plot_confusion_matrix, plot_feature_importance,
)

log = logging.getLogger("nara.health_scorer.xgb_shap")


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

    num_cols  = [c for c in HEALTH_SCORER_FEATURES["numerical"]  if c in df.columns]
    cat_cols  = [c for c in HEALTH_SCORER_FEATURES["categorical"] if c in df.columns]
    bin_cols  = [c for c in HEALTH_SCORER_FEATURES["binary"]      if c in df.columns]
    cond_cols = [c for c in CONDITION_FLAGS if c in df.columns]
    bin_cols  = list(set(bin_cols + cond_cols))

    df[num_cols] = df[num_cols].fillna(0)
    df[bin_cols] = df[bin_cols].fillna(0).astype(int)

    encoder = FeatureEncoder()
    df = encoder.fit_transform(df, cat_cols, num_cols)

    feature_cols = num_cols + cat_cols + bin_cols
    X = df[feature_cols].fillna(0)
    y = df["health_compliant"].fillna(1).astype(int)

    log.info(f"  Features: {len(feature_cols)} | Samples: {len(X):,}")
    return X, y, feature_cols, encoder


def compute_shap_values(model, X_test: pd.DataFrame,
                         feature_cols: list) -> pd.DataFrame:
    """Compute SHAP values for test set."""
    try:
        import shap
        explainer   = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test)

        # For binary classification, shap_values is list of 2 arrays
        if isinstance(shap_values, list):
            shap_arr = shap_values[1]  # positive class SHAP
        else:
            shap_arr = shap_values

        shap_df = pd.DataFrame(shap_arr, columns=feature_cols)

        # Mean absolute SHAP per feature (global importance)
        mean_shap = shap_df.abs().mean().sort_values(ascending=False)
        log.info("\nSHAP Feature Importance (mean |SHAP|):")
        log.info(f"\n{mean_shap.head(15).to_string()}")

        return shap_df
    except ImportError:
        log.warning("shap not installed. Run: pip install shap")
        return pd.DataFrame()


def explain_prediction(model, X_row: pd.DataFrame,
                        feature_cols: list) -> str:
    """Generate human-readable explanation for a single prediction."""
    try:
        import shap
        explainer   = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_row)
        if isinstance(shap_values, list):
            sv = shap_values[1][0]
        else:
            sv = shap_values[0]

        # Top 3 contributing features
        pairs = sorted(zip(feature_cols, sv), key=lambda x: abs(x[1]), reverse=True)[:3]
        parts = []
        for feat, val in pairs:
            direction = "increases" if val > 0 else "decreases"
            parts.append(f"{feat} {direction} risk by {abs(val):.3f}")
        return " | ".join(parts)
    except Exception:
        return "explanation unavailable"


def train():
    log.info("=" * 60)
    log.info("Health Scorer — XGBoost + SHAP (Best)")
    log.info("=" * 60)

    X, y, feature_cols, encoder = load_and_prepare_data()
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)

    log.info("Training XGBoost...")
    params = {
        **XGB_PARAMS,
        "objective":  "binary:logistic",
        "eval_metric":"logloss",
        "scale_pos_weight": (y_train == 0).sum() / (y_train == 1).sum(),
    }

    model = xgb.XGBClassifier(**params, early_stopping_rounds=20)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=50,
    )

    log.info(f"  Best iteration: {model.best_iteration}")

    # ── Evaluate ──────────────────────────────────────────────
    y_val_pred   = model.predict(X_val)
    y_val_prob   = model.predict_proba(X_val)
    val_metrics  = classification_metrics(y_val, y_val_pred, y_val_prob, label="VAL")

    y_test_pred  = model.predict(X_test)
    y_test_prob  = model.predict_proba(X_test)
    test_metrics = classification_metrics(y_test, y_test_pred, y_test_prob, label="TEST")

    # ── SHAP analysis ─────────────────────────────────────────
    log.info("\nComputing SHAP values on test set...")
    shap_df = compute_shap_values(model, X_test, feature_cols)

    # Sample explanations
    if not shap_df.empty:
        log.info("\nSample non-compliant explanations:")
        non_compliant_idx = np.where(y_test_pred == 0)[0][:5]
        for idx in non_compliant_idx:
            row_df = X_test.iloc[[idx]]
            explanation = explain_prediction(model, row_df, feature_cols)
            dish = X_test.index[idx] if hasattr(X_test.index, '__getitem__') else idx
            log.info(f"  Sample {idx}: {explanation}")

    # ── Feature importance ────────────────────────────────────
    importances = model.feature_importances_
    plot_confusion_matrix(
        y_test, y_test_pred,
        labels=["non_compliant", "compliant"],
        title="Health Scorer XGBoost — Confusion Matrix",
        filename="health_xgb_cm.png",
    )
    plot_feature_importance(
        feature_cols, list(importances),
        title="Health Scorer XGBoost — Feature Importance",
        filename="health_xgb_fi.png",
    )

    # ── Save ──────────────────────────────────────────────────
    save_xgboost_model(
        model,
        MODEL_PATHS["health_xgb"],
        onnx_path=MODEL_PATHS["health_xgb_onnx"],
        feature_names=feature_cols,
    )
    save_metrics({"val": val_metrics, "test": test_metrics}, "health_xgb_shap")

    log.info("\n" + "=" * 60)
    log.info("SUMMARY — Health Scorer XGBoost + SHAP")
    log.info(f"  Test Accuracy : {test_metrics['accuracy']}")
    log.info(f"  Test F1       : {test_metrics['f1']}")
    log.info(f"  Test AUC      : {test_metrics.get('auc', 'n/a')}")
    log.info(f"  Model saved   : {MODEL_PATHS['health_xgb']}")
    log.info("=" * 60)

    return model, test_metrics


if __name__ == "__main__":
    train()
