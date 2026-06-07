"""
NARA — Recommendation Ranker — Best: LightGBM
─────────────────────────────────────────────────────────────
INPUT FEATURES (X):
  Numerical : context_time_of_day, context_day, context_budget,
              recommendation_rank, cuisine_affinity, price_match_score,
              user_health_match, age, health_literacy, habit_strength, bmi,
              gi_score, calories_kcal, protein_g, carbs_g, fat_g, fiber_g
  Categorical: context_season, context_stress, income_tier, region, cuisine_type
  Binary    : is_vegetarian, was_top3, all condition flags

PREDICTION TARGET (Y):
  action_score → 0=skip, 1=click, 2=order (multiclass)

WHY LIGHTGBM OVER XGBOOST:
  Leaf-wise tree growth vs depth-wise → better accuracy on our sparse data
  Faster training: histogram-based algorithm
  Better handling of high-cardinality categoricals natively
  Lower memory footprint for same n_estimators

EXPECTED METRICS (improvement over XGBoost):
  Accuracy ~0.72-0.78
  F1 weighted ~0.70-0.76
  NDCG@10 ~0.76-0.84

Run:
  python recommendation_ranker/train_lightgbm.py
"""
import os
import sys
import logging

import numpy as np
import pandas as pd
import lightgbm as lgb

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    MODEL_PATHS, RANKER_FEATURES, RANKER_ACTION_MAP,
    LGBM_PARAMS, CONDITION_FLAGS,
)
from utils import (
    load_users, load_interactions, load_nutrition_kb,
    expand_conditions, extract_nutrition_from_kb,
    FeatureEncoder, split_data,
    classification_metrics, ranker_metrics,
    save_lgbm_model, save_metrics,
    plot_confusion_matrix, plot_feature_importance,
)
from sklearn.utils.class_weight import compute_sample_weight
log = logging.getLogger("nara.ranker.lightgbm")


def load_and_prepare_data() -> tuple:
    log.info("Loading data...")
    interactions = load_interactions()
    users        = load_users()
    kb           = load_nutrition_kb()

    user_cols = [
        "user_id", "age", "health_literacy", "habit_strength",
        "bmi", "income_tier", "region", "is_vegetarian", "conditions",
        "activity_level", "stress_profile",
    ]
    user_slim = users[user_cols].drop_duplicates("user_id")
    df = interactions.merge(user_slim, on="user_id", how="left")
    df = extract_nutrition_from_kb(df, kb, dish_col="dish_name")
    df = expand_conditions(df, conditions_col="conditions")

    df["action_score"] = df["action"].map(RANKER_ACTION_MAP).fillna(0).astype(int)

    num_cols = [c for c in RANKER_FEATURES["numerical"]  if c in df.columns]
    cat_cols = [c for c in RANKER_FEATURES["categorical"] if c in df.columns]
    bin_cols = [c for c in RANKER_FEATURES["binary"]      if c in df.columns]
    condition_cols = [c for c in CONDITION_FLAGS if c in df.columns]
    bin_cols = list(set(bin_cols + condition_cols))

    df[num_cols] = df[num_cols].fillna(0)
    df[bin_cols] = df[bin_cols].fillna(0).astype(int)

    encoder = FeatureEncoder()
    df = encoder.fit_transform(df, cat_cols, num_cols)

    feature_cols = num_cols + cat_cols + bin_cols
    X = df[feature_cols].fillna(0)
    y = df["action_score"]

    log.info(f"  Features: {len(feature_cols)} | Samples: {len(X):,}")
    log.info(f"  Class distribution: {y.value_counts().to_dict()}")
    return X, y, feature_cols, encoder


def train():
    log.info("=" * 60)
    log.info("Recommendation Ranker — LightGBM (Best)")
    log.info("=" * 60)

    X, y, feature_cols, encoder = load_and_prepare_data()
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)

    # ── Train ─────────────────────────────────────────────────
    log.info("Training LightGBM...")
    params = {
        **LGBM_PARAMS,
        "objective":    "multiclass",
        "num_class":    3,
        "metric":       "multi_logloss",
    }

    model = lgb.LGBMClassifier(**params)
    sample_weights = compute_sample_weight(
    class_weight="balanced",
    y=y_train
)
    model.fit(
        X_train, y_train,sample_weight=sample_weights,
        eval_set=[(X_val, y_val)],
        callbacks=[
            lgb.early_stopping(stopping_rounds=20, verbose=True),
            lgb.log_evaluation(period=50),
        ],
    )

    log.info(f"  Best iteration: {model.best_iteration_}")

    # ── Evaluate ──────────────────────────────────────────────
    y_val_pred   = model.predict(X_val)
    y_val_prob   = model.predict_proba(X_val)
    val_metrics  = classification_metrics(y_val, y_val_pred, y_val_prob, label="VAL")
    val_ndcg     = ranker_metrics(y_val.values, y_val_prob[:, 2], label="VAL")
    val_metrics.update(val_ndcg)

    y_test_pred  = model.predict(X_test)
    y_test_prob  = model.predict_proba(X_test)
    test_metrics = classification_metrics(y_test, y_test_pred, y_test_prob, label="TEST")
    test_ndcg    = ranker_metrics(y_test.values, y_test_prob[:, 2], label="TEST")
    test_metrics.update(test_ndcg)

    # ── Feature importance — two types ────────────────────────
    fi_gain  = model.booster_.feature_importance(importance_type="gain")
    fi_split = model.booster_.feature_importance(importance_type="split")

    fi_df = pd.DataFrame({
        "feature":    feature_cols,
        "gain":       fi_gain,
        "split":      fi_split,
    }).sort_values("gain", ascending=False).head(20)
    log.info(f"\nTop 20 features (by gain):\n{fi_df.to_string(index=False)}")

    # ── Plots ─────────────────────────────────────────────────
    plot_confusion_matrix(
        y_test, y_test_pred,
        labels=["skip", "click", "order"],
        title="Ranker LightGBM — Confusion Matrix",
        filename="ranker_lgbm_cm.png",
    )
    plot_feature_importance(
        feature_cols, list(fi_gain),
        title="Ranker LightGBM — Feature Importance (gain)",
        filename="ranker_lgbm_fi.png",
    )

    # ── Save ──────────────────────────────────────────────────
    save_lgbm_model(
        model,
        MODEL_PATHS["ranker_lgbm"],
        onnx_path=MODEL_PATHS["ranker_lgbm_onnx"],
        feature_names=feature_cols,
    )
    save_metrics({"val": val_metrics, "test": test_metrics}, "ranker_lgbm")

    log.info("\n" + "=" * 60)
    log.info("SUMMARY — Ranker LightGBM")
    log.info(f"  Test Accuracy : {test_metrics['accuracy']}")
    log.info(f"  Test F1       : {test_metrics['f1']}")
    log.info(f"  Test NDCG@10  : {test_metrics.get('ndcg_10', 'n/a')}")
    log.info(f"  Model saved   : {MODEL_PATHS['ranker_lgbm']}")
    log.info("=" * 60)

    return model, test_metrics


if __name__ == "__main__":
    train()