"""
NARA — Recommendation Ranker — Mid: XGBoost
─────────────────────────────────────────────────────────────
INPUT FEATURES (X):
  Same as logistic but XGBoost handles non-linear interactions:
  Numerical : context_time_of_day, context_day, context_budget,
              recommendation_rank, cuisine_affinity, price_match_score,
              user_health_match, age, health_literacy, habit_strength, bmi,
              gi_score, calories_kcal, protein_g, carbs_g, fat_g, fiber_g
  Categorical: context_season, context_stress, income_tier, region, cuisine_type
  Binary    : is_vegetarian, was_top3, condition flags

PREDICTION TARGET (Y):
  action_score → 0=skip, 1=click, 2=order (multiclass)

WHY XGBOOST OVER LOGISTIC:
  Captures interaction: stressed user + biryani + Friday = high order prob
  Logistic misses these non-linear combinations.
  Gradient boosting on tabular data consistently outperforms linear models.

EXPECTED METRICS (improvement over logistic):
  Accuracy ~0.68-0.75
  F1 weighted ~0.66-0.74
  NDCG@10 ~0.74-0.82

Run:
  python recommendation_ranker/train_xgboost.py
"""
import os
import sys
import logging

import numpy as np
import pandas as pd
import xgboost as xgb

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    MODEL_PATHS, RANKER_FEATURES, RANKER_ACTION_MAP,
    XGB_PARAMS, CONDITION_FLAGS,
)
from sklearn.utils.class_weight import compute_sample_weight
from utils import (
    load_users, load_interactions, load_nutrition_kb,
    expand_conditions, extract_nutrition_from_kb,
    FeatureEncoder, split_data,
    classification_metrics, ranker_metrics,
    save_xgboost_model, save_metrics,
    plot_confusion_matrix, plot_feature_importance,
)

log = logging.getLogger("nara.ranker.xgboost")


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

    # Add condition flags to binary
    condition_cols = [c for c in CONDITION_FLAGS if c in df.columns]
    # NOTE: list(set(...)) does not guarantee a stable order across
    # process runs (Python string hash randomization), which can silently
    # shuffle the binary feature columns relative to what inference code
    # assumes. dict.fromkeys() dedupes while preserving insertion order.
    bin_cols = list(dict.fromkeys(bin_cols + condition_cols))

    df[num_cols] = df[num_cols].fillna(0)
    df[bin_cols] = df[bin_cols].fillna(0).astype(int)

    encoder = FeatureEncoder()
    df = encoder.fit_transform(df, cat_cols, num_cols)

    feature_cols = num_cols + cat_cols + bin_cols
    X = df[feature_cols].fillna(0)
    y = df["action_score"]
    interaction_ids = df["interaction_id"].reset_index(drop=True)
    X = X.reset_index(drop=True)    
    y = y.reset_index(drop=True)
    log.info(f"  Features: {len(feature_cols)} | Samples: {len(X):,}")
    log.info(f"  Class distribution: {y.value_counts().to_dict()}")
    return X, y, feature_cols, encoder, interaction_ids 


def train():
    log.info("=" * 60)
    log.info("Recommendation Ranker — XGBoost (Mid)")
    log.info("=" * 60)

    X, y, feature_cols, encoder, interaction_ids = load_and_prepare_data()
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)
    ids_val  = interaction_ids.loc[X_val.index]
    ids_test = interaction_ids.loc[X_test.index]
    # ── Train with early stopping ─────────────────────────────
    log.info("Training XGBoost...")
    params = {**XGB_PARAMS, "objective": "multi:softprob", "num_class": 3}

    model = xgb.XGBClassifier(**params, early_stopping_rounds=20)
    sample_weights = compute_sample_weight(
    class_weight="balanced",
    y=y_train
)
    model.fit(
        X_train, y_train, sample_weight=sample_weights,
        eval_set=[(X_val, y_val)],
        verbose=50,
    )

    log.info(f"  Best iteration: {model.best_iteration}")

    # ── Evaluate ──────────────────────────────────────────────
    y_val_pred  = model.predict(X_val)
    y_val_prob  = model.predict_proba(X_val)
    val_metrics = classification_metrics(y_val, y_val_pred, y_val_prob, label="VAL")
    val_ndcg    = ranker_metrics(y_val.values, y_val_prob[:, 2], df_index=ids_val, label="VAL")
    val_metrics.update(val_ndcg)
    
    y_test_pred  = model.predict(X_test)
    y_test_prob  = model.predict_proba(X_test)
    test_metrics = classification_metrics(y_test, y_test_pred, y_test_prob, label="TEST")
    test_ndcg    = ranker_metrics(y_test.values, y_test_prob[:, 2], df_index=ids_test, label="TEST")
    test_metrics.update(test_ndcg)

    # ── Feature importance ────────────────────────────────────
    importances = model.feature_importances_
    fi_df = pd.DataFrame({
        "feature":    feature_cols,
        "importance": importances,
    }).sort_values("importance", ascending=False).head(20)
    log.info(f"\nTop 20 features:\n{fi_df.to_string(index=False)}")

    # ── Plots ─────────────────────────────────────────────────
    plot_confusion_matrix(
        y_test, y_test_pred,
        labels=["skip", "click", "order"],
        title="Ranker XGBoost — Confusion Matrix",
        filename="ranker_xgboost_cm.png",
    )
    plot_feature_importance(
        feature_cols, list(importances),
        title="Ranker XGBoost — Feature Importance",
        filename="ranker_xgboost_fi.png",
    )

    # ── Save ──────────────────────────────────────────────────
    metadata = {
        "model":        "XGBoost",
        "features":     feature_cols,
        "val_metrics":  val_metrics,
        "test_metrics": test_metrics,
        "best_iter":    model.best_iteration,
        "n_train":      len(X_train),
    }
    save_xgboost_model(
        model,
        MODEL_PATHS["ranker_xgboost"],
        onnx_path=MODEL_PATHS["ranker_xgboost_onnx"],
        feature_names=feature_cols,
    )
    save_metrics({"val": val_metrics, "test": test_metrics}, "ranker_xgboost")

    log.info("\n" + "=" * 60)
    log.info("SUMMARY — Ranker XGBoost")
    log.info(f"  Test Accuracy : {test_metrics['accuracy']}")
    log.info(f"  Test F1       : {test_metrics['f1']}")
    log.info(f"  Test NDCG@10  : {test_metrics.get('ndcg_10', 'n/a')}")
    log.info(f"  Model saved   : {MODEL_PATHS['ranker_xgboost']}")
    log.info("=" * 60)

    return model, test_metrics


if __name__ == "__main__":
    train()
