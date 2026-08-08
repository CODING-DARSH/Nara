"""
NARA — Reorder Prediction — Best: Cox PH + XGBoost
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
  Cox PH additionally models: time_to_reorder (days_between as duration)

WHY COX PH + XGBOOST:
  Cox Proportional Hazards is the right model for reorder prediction:
    - Models TIME to reorder, not just whether reorder happens
    - "User will reorder in 7 days" is more useful than "user will reorder"
    - Handles censored data: users who haven't reordered YET
  XGBoost on top captures non-linear hazard ratio adjustments
  Together: Cox gives time-aware baseline, XGBoost refines it

  C-index (concordance index) is the primary metric:
    0.5 = random, 1.0 = perfect, 0.7+ = clinically useful

EXPECTED METRICS:
  C-index  ~0.72-0.80
  AUC      ~0.82-0.88
  F1       ~0.76-0.83

Run:
  python reorder_prediction/train_cox_xgboost.py
"""
import os
import sys
import logging

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MODEL_PATHS, REORDER_FEATURES, XGB_PARAMS, RANDOM_STATE
from utils import (
    load_users, load_reorder_events,
    derive_season_from_date, derive_month_position,
    FeatureEncoder, split_data,
    classification_metrics, save_metrics,
    save_xgboost_model,
    plot_confusion_matrix, plot_feature_importance,
)

log = logging.getLogger("nara.reorder.cox_xgb")


def compute_c_index(y_true: np.ndarray, risk_scores: np.ndarray,
                     durations: np.ndarray) -> float:
    """
    Compute concordance index (C-index) for survival analysis.
    Measures how well model ranks reorder times.
    C-index = P(risk_i > risk_j | duration_i < duration_j, both reordered)
    """
    concordant = 0
    discordant = 0
    tied       = 0

    n = len(y_true)
    for i in range(n):
        for j in range(i + 1, n):
            if y_true[i] == 0 and y_true[j] == 0:
                continue
            if y_true[i] == 1 and y_true[j] == 1:
                if durations[i] < durations[j]:
                    if risk_scores[i] > risk_scores[j]:
                        concordant += 1
                    elif risk_scores[i] < risk_scores[j]:
                        discordant += 1
                    else:
                        tied += 1
                elif durations[i] > durations[j]:
                    if risk_scores[j] > risk_scores[i]:
                        concordant += 1
                    elif risk_scores[j] < risk_scores[i]:
                        discordant += 1
                    else:
                        tied += 1

    total = concordant + discordant + tied
    if total == 0:
        return 0.5
    return concordant / (concordant + discordant + tied * 0.5)


def fit_cox_baseline(df_train: pd.DataFrame,
                      feature_cols: list) -> dict:
    """
    Fit Cox PH model using lifelines library.
    Returns fitted model or None if lifelines not installed.
    """
    try:
        from lifelines import CoxPHFitter

        cox_df = df_train[feature_cols + ["days_between", "reordered_yes_no"]].copy()
        cox_df = cox_df.rename(columns={
            "days_between":     "duration",
            "reordered_yes_no": "event",
        })
        cox_df = cox_df.dropna()
        cox_df["duration"] = cox_df["duration"].clip(lower=1)

        cph = CoxPHFitter(penalizer=0.1)
        cph.fit(cox_df, duration_col="duration", event_col="event")
        log.info(f"\nCox PH summary:\n{cph.summary[['coef', 'exp(coef)', 'p']].head(10).to_string()}")
        return cph
    except ImportError:
        log.warning("lifelines not installed. Cox PH baseline skipped. pip install lifelines")
        return None


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

    # Keep durations for C-index calculation
    durations = df["days_between"].fillna(0).values

    log.info(f"  Features: {len(feature_cols)} | Samples: {len(X):,}")
    log.info(f"  Reorder rate: {y.mean():.3f}")
    log.info(f"  Median days to reorder: {df[df['reordered_yes_no']==1]['days_between'].median():.1f}")
    return X, y, feature_cols, encoder, durations, df


def train():
    log.info("=" * 60)
    log.info("Reorder Prediction — Cox PH + XGBoost (Best)")
    log.info("=" * 60)

    X, y, feature_cols, encoder, durations, df_full = load_and_prepare_data()

    # Split indices to keep durations aligned
    idx = np.arange(len(X))
    idx_tv, idx_test = train_test_split(idx, test_size=0.20, random_state=RANDOM_STATE, stratify=y)
    idx_train, idx_val = train_test_split(idx_tv, test_size=0.125, random_state=RANDOM_STATE, stratify=y.iloc[idx_tv])

    X_train = X.iloc[idx_train]
    X_val   = X.iloc[idx_val]
    X_test  = X.iloc[idx_test]
    y_train = y.iloc[idx_train]
    y_val   = y.iloc[idx_val]
    y_test  = y.iloc[idx_test]
    dur_test = durations[idx_test]

    log.info(f"  Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}")

    # ── Step 1: Cox PH baseline ───────────────────────────────
    log.info("\nStep 1: Fitting Cox PH baseline...")
    df_train = df_full.iloc[idx_train].copy()
    num_cols  = [c for c in REORDER_FEATURES["numerical"] if c in X_train.columns]
    cox_model = fit_cox_baseline(df_train, num_cols)

    # ── Step 2: XGBoost on top ────────────────────────────────
    log.info("\nStep 2: Training XGBoost...")
    params = {
        **XGB_PARAMS,
        "objective":        "binary:logistic",
        "eval_metric":      "auc",
        "scale_pos_weight": (y_train == 0).sum() / max((y_train == 1).sum(), 1),
    }

    # If Cox PH fitted, use its predicted partial hazard as an additional feature
    if cox_model is not None:
        try:
            from lifelines import CoxPHFitter
            cox_features = num_cols + [c for c in feature_cols if c in df_train.columns]
            train_risk = cox_model.predict_partial_hazard(df_train).values
            val_risk   = cox_model.predict_partial_hazard(df_full.iloc[idx_val]).values
            test_risk  = cox_model.predict_partial_hazard(df_full.iloc[idx_test]).values

            X_train_aug = X_train.copy()
            X_val_aug   = X_val.copy()
            X_test_aug  = X_test.copy()
            X_train_aug["cox_risk"] = train_risk
            X_val_aug["cox_risk"]   = val_risk
            X_test_aug["cox_risk"]  = test_risk
            feature_cols_aug = feature_cols + ["cox_risk"]
            log.info("  Cox PH risk scores added as feature")
        except Exception as e:
            log.warning(f"  Cox feature augmentation failed: {e}")
            X_train_aug, X_val_aug, X_test_aug = X_train, X_val, X_test
            feature_cols_aug = feature_cols
    else:
        X_train_aug, X_val_aug, X_test_aug = X_train, X_val, X_test
        feature_cols_aug = feature_cols

    model = xgb.XGBClassifier(**params, early_stopping_rounds=20)
    model.fit(
        X_train_aug, y_train,
        eval_set=[(X_val_aug, y_val)],
        verbose=50,
    )
    log.info(f"  Best iteration: {model.best_iteration}")

    # ── Evaluate ──────────────────────────────────────────────
    y_test_pred = model.predict(X_test_aug)
    y_test_prob = model.predict_proba(X_test_aug)
    test_metrics = classification_metrics(y_test, y_test_pred, y_test_prob, label="TEST")

    # C-index
    risk_scores = y_test_prob[:, 1]
    c_index = compute_c_index(y_test.values, risk_scores, dur_test)
    test_metrics["c_index"] = round(c_index, 4)
    log.info(f"[TEST] C-index: {c_index:.4f}")

    # Reorder time analysis
    reordered_mask  = y_test == 1
    if reordered_mask.sum() > 0:
        median_time = np.median(dur_test[reordered_mask])
        log.info(f"[TEST] Median days to reorder (actual): {median_time:.1f}")

        high_risk   = risk_scores > 0.7
        low_risk    = risk_scores < 0.3
        if high_risk.sum() > 0 and low_risk.sum() > 0:
            log.info(f"  High risk (>0.7) reorder rate: {y_test.values[high_risk].mean():.3f}")
            log.info(f"  Low  risk (<0.3) reorder rate: {y_test.values[low_risk].mean():.3f}")

    importances = model.feature_importances_
    plot_confusion_matrix(
        y_test, y_test_pred,
        labels=["no_reorder", "reorder"],
        title="Reorder Cox+XGBoost — Confusion Matrix",
        filename="reorder_cox_xgb_cm.png",
    )
    plot_feature_importance(
        feature_cols_aug, list(importances),
        title="Reorder Cox+XGBoost — Feature Importance",
        filename="reorder_cox_xgb_fi.png",
    )

    save_xgboost_model(
        model,
        MODEL_PATHS["reorder_xgb"],
        onnx_path=MODEL_PATHS["reorder_xgb_onnx"],
        feature_names=feature_cols_aug,
    )
    save_metrics({"test": test_metrics}, "reorder_cox_xgb")

    log.info("\n" + "=" * 60)
    log.info("SUMMARY — Reorder Cox PH + XGBoost")
    log.info(f"  Test Accuracy : {test_metrics['accuracy']}")
    log.info(f"  Test F1       : {test_metrics['f1']}")
    log.info(f"  Test AUC      : {test_metrics.get('auc', 'n/a')}")
    log.info(f"  C-index       : {test_metrics.get('c_index', 'n/a')}")
    log.info(f"  Model saved   : {MODEL_PATHS['reorder_xgb']}")
    log.info("=" * 60)

    return model, test_metrics


if __name__ == "__main__":
    train()
