"""
NARA — Recommendation Ranker — Baseline: Logistic Regression
─────────────────────────────────────────────────────────────
INPUT FEATURES (X):
  Numerical : context_time_of_day, context_day, context_budget,
              recommendation_rank, cuisine_affinity, price_match_score,
              user_health_match, age, health_literacy, habit_strength, bmi,
              gi_score, calories_kcal, protein_g, carbs_g, fat_g, fiber_g
  Categorical: context_season, context_stress, income_tier, region, cuisine_type
  Binary    : is_vegetarian, was_top3

PREDICTION TARGET (Y):
  action_score → 0=skip, 1=click, 2=order (multiclass)

WHY LOGISTIC REGRESSION AS BASELINE:
  Fast, interpretable, gives calibrated probabilities.
  Coefficients tell us exactly which features matter.
  Any improvement over this justifies XGBoost/LightGBM complexity.

EXPECTED METRICS:
  Accuracy ~0.55-0.65 (3-class problem, random=0.33)
  F1 weighted ~0.52-0.62
  NDCG@10 ~0.65-0.72

Run:
  python recommendation_ranker/train_logistic.py
"""
import os
import sys
import logging
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import label_binarize

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    PATHS, MODEL_PATHS, RANKER_FEATURES, RANKER_ACTION_MAP,
    LOGISTIC_PARAMS,
)
from utils import (
    load_users, load_interactions, load_nutrition_kb,
    expand_conditions, extract_nutrition_from_kb,
    FeatureEncoder, split_data,
    classification_metrics, ranker_metrics,
    save_sklearn_model, save_metrics,
    plot_confusion_matrix, plot_feature_importance,
)

log = logging.getLogger("nara.ranker.logistic")


def load_and_prepare_data() -> tuple[pd.DataFrame, pd.Series]:
    """
    Load interactions + users + nutrition KB.
    Join features. Return X, y.
    """
    log.info("Loading data...")
    interactions = load_interactions()
    users        = load_users()
    kb           = load_nutrition_kb()

    # ── Join user features ────────────────────────────────────
    user_cols = [
        "user_id", "age", "health_literacy", "habit_strength",
        "bmi", "income_tier", "region", "is_vegetarian", "conditions",
    ]
    user_slim = users[user_cols].drop_duplicates("user_id")
    df = interactions.merge(user_slim, on="user_id", how="left")

    # ── Join nutrition KB features ────────────────────────────
    df = extract_nutrition_from_kb(df, kb, dish_col="dish_name")

    # ── Expand conditions → binary flags ──────────────────────
    df = expand_conditions(df, conditions_col="conditions")

    # ── Map action to numeric score ───────────────────────────
    df["action_score"] = df["action"].map(RANKER_ACTION_MAP).fillna(0).astype(int)

    # ── Build feature matrix ──────────────────────────────────
    num_cols  = [c for c in RANKER_FEATURES["numerical"]  if c in df.columns]
    cat_cols  = [c for c in RANKER_FEATURES["categorical"] if c in df.columns]
    bin_cols  = [c for c in RANKER_FEATURES["binary"]      if c in df.columns]

    # Fill missing
    df[num_cols] = df[num_cols].fillna(0)
    df[bin_cols] = df[bin_cols].fillna(0).astype(int)

    log.info(f"  Numerical features:   {num_cols}")
    log.info(f"  Categorical features: {cat_cols}")
    log.info(f"  Binary features:      {bin_cols}")
    log.info(f"  Dataset shape: {df.shape}")

    # ── Encode ────────────────────────────────────────────────
    encoder = FeatureEncoder()
    df = encoder.fit_transform(df, cat_cols, num_cols)
    encoder.save(MODEL_PATHS["encoders"])

    feature_cols = num_cols + cat_cols + bin_cols
    X = df[feature_cols].fillna(0)
    y = df["action_score"]
    interaction_ids = df["interaction_id"].reset_index(drop=True)
    X = X.reset_index(drop=True)
    y = y.reset_index(drop=True)
    log.info(f"  Class distribution: {y.value_counts().to_dict()}")
    return X, y, feature_cols, encoder, interaction_ids 


def train():
    log.info("=" * 60)
    log.info("Recommendation Ranker — Logistic Regression (Baseline)")
    log.info("=" * 60)

    X, y, feature_cols, encoder, interaction_ids = load_and_prepare_data()
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)
    ids_val  = interaction_ids.loc[X_val.index]
    ids_test = interaction_ids.loc[X_test.index]
    # ── Train ─────────────────────────────────────────────────
    log.info("Training Logistic Regression...")
    model = LogisticRegression(**LOGISTIC_PARAMS, multi_class="multinomial",class_weight="balanced")
    model.fit(X_train, y_train)
    
    # ── Evaluate on validation ────────────────────────────────
    log.info("Evaluating on validation set...")
    y_val_pred = model.predict(X_val)
    y_val_prob = model.predict_proba(X_val)
    val_metrics = classification_metrics(
        y_val, y_val_pred, y_val_prob, label="VAL"
    )

    # NDCG on validation
    val_ndcg  = ranker_metrics(y_val.values,  y_val_prob[:, 2], df_index=ids_val,  label="VAL")
    val_metrics.update(val_ndcg)

    # ── Evaluate on test ──────────────────────────────────────
    log.info("Evaluating on test set...")
    y_test_pred = model.predict(X_test)
    y_test_prob = model.predict_proba(X_test)
    test_metrics = classification_metrics(
        y_test, y_test_pred, y_test_prob, label="TEST"
    )
    test_ndcg = ranker_metrics(y_test.values, y_test_prob[:, 2], df_index=ids_test, label="TEST")
    test_metrics.update(test_ndcg)

    # ── Feature coefficients (interpretability) ───────────────
    log.info("Top feature coefficients (order class):")
    coef_order = model.coef_[2]  # coefficients for class=2 (order)
    coef_df = pd.DataFrame({
        "feature":     feature_cols,
        "coefficient": coef_order,
    }).sort_values("coefficient", key=abs, ascending=False).head(15)
    log.info(f"\n{coef_df.to_string(index=False)}")

    # ── Plots ─────────────────────────────────────────────────
    plot_confusion_matrix(
        y_test, y_test_pred,
        labels=["skip", "click", "order"],
        title="Ranker Logistic — Confusion Matrix",
        filename="ranker_logistic_cm.png",
    )
    plot_feature_importance(
        feature_cols,
        list(abs(coef_order)),
        title="Ranker Logistic — Feature Importance (|coef|)",
        filename="ranker_logistic_fi.png",
    )

    # ── Save ──────────────────────────────────────────────────
    metadata = {
        "model":         "LogisticRegression",
        "features":      feature_cols,
        "val_metrics":   val_metrics,
        "test_metrics":  test_metrics,
        "n_train":       len(X_train),
        "n_test":        len(X_test),
        "classes":       list(model.classes_),
    }
    save_sklearn_model(model, MODEL_PATHS["ranker_logistic"], metadata)
    save_metrics(
        {"val": val_metrics, "test": test_metrics},
        "ranker_logistic"
    )

    log.info("\n" + "=" * 60)
    log.info("SUMMARY — Ranker Logistic Regression")
    log.info(f"  Test Accuracy : {test_metrics['accuracy']}")
    log.info(f"  Test F1       : {test_metrics['f1']}")
    log.info(f"  Test NDCG@10  : {test_metrics.get('ndcg_10', 'n/a')}")
    log.info(f"  Model saved   : {MODEL_PATHS['ranker_logistic']}")
    log.info("=" * 60)

    return model, test_metrics


if __name__ == "__main__":
    train()
