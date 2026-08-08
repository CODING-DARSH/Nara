import os
import sys
import numpy as np
import pandas as pd
import lightgbm as lgb

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    RANKER_FEATURES,
    RANKER_ACTION_MAP,
    CONDITION_FLAGS,
)

from utils import (
    load_users,
    load_interactions,
    load_nutrition_kb,
    expand_conditions,
    extract_nutrition_from_kb,
    FeatureEncoder,
    split_data,
    classification_metrics,
    ranker_metrics,
)

MODEL_PATH = "./models/ranker_lgbm.txt"


def load_data():
    interactions = load_interactions()
    users = load_users()
    kb = load_nutrition_kb()

    user_cols = [
        "user_id",
        "age",
        "health_literacy",
        "habit_strength",
        "bmi",
        "income_tier",
        "region",
        "is_vegetarian",
        "conditions",
        "activity_level",
        "stress_profile",
    ]

    user_slim = users[user_cols].drop_duplicates("user_id")

    df = interactions.merge(user_slim, on="user_id", how="left")

    df = extract_nutrition_from_kb(
        df,
        kb,
        dish_col="dish_name"
    )

    df = expand_conditions(
        df,
        conditions_col="conditions"
    )

    df["action_score"] = (
        df["action"]
        .map(RANKER_ACTION_MAP)
        .fillna(0)
        .astype(int)
    )

    num_cols = [
        c for c in RANKER_FEATURES["numerical"]
        if c in df.columns
    ]

    cat_cols = [
        c for c in RANKER_FEATURES["categorical"]
        if c in df.columns
    ]

    bin_cols = [
        c for c in RANKER_FEATURES["binary"]
        if c in df.columns
    ]

    condition_cols = [
        c for c in CONDITION_FLAGS
        if c in df.columns
    ]

    bin_cols = list(dict.fromkeys(
        bin_cols + condition_cols
    ))

    df[num_cols] = df[num_cols].fillna(0)
    df[bin_cols] = df[bin_cols].fillna(0).astype(int)

    encoder = FeatureEncoder()
    df = encoder.fit_transform(
        df,
        cat_cols,
        num_cols
    )

    feature_cols = (
        num_cols +
        cat_cols +
        bin_cols
    )

    X = df[feature_cols].fillna(0)
    y = df["action_score"]

    interaction_ids = (
        df["interaction_id"]
        .reset_index(drop=True)
    )

    X = X.reset_index(drop=True)
    y = y.reset_index(drop=True)

    return X, y, interaction_ids


def main():

    print("Loading data...")
    X, y, interaction_ids = load_data()

    print("Creating split...")
    _, _, X_test, _, _, y_test = split_data(X, y)

    ids_test = interaction_ids.loc[X_test.index]

    print("Loading model...")
    booster = lgb.Booster(
        model_file=MODEL_PATH
    )

    print("Predicting...")
    y_prob = booster.predict(X_test)

    y_pred = np.argmax(y_prob, axis=1)

    metrics = classification_metrics(
        y_test,
        y_pred,
        y_prob,
        label="TEST"
    )

    print("\nClassification")
    print(metrics)

    print("\nNDCG using order probability")

    ndcg_order = ranker_metrics(
        y_test.values,
        y_prob[:, 2],
        df_index=ids_test,
        label="ORDER_ONLY"
    )

    print(ndcg_order)

    rank_score = (
        y_prob[:, 1]
        + 2 * y_prob[:, 2]
    )

    print("\nNDCG using click + 2*order")

    ndcg_weighted = ranker_metrics(
        y_test.values,
        rank_score,
        df_index=ids_test,
        label="CLICK_PLUS_ORDER"
    )

    print(ndcg_weighted)


if __name__ == "__main__":
    main()
