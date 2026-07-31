"""
NARA ML — Benchmark
Loads all trained models, runs inference on test data,
compares metrics and latency side by side.
"""
import os
import sys
import json
import time
import logging
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
import torch

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import MODEL_PATHS, MODELS_DIR, PLOTS_DIR, RANDOM_STATE
from utils import (
    load_users, load_meal_logs, load_interactions,
    load_reorder_events, load_nutrition_kb,
    expand_conditions, extract_nutrition_from_kb,
    derive_top_cuisine_per_user,
    FeatureEncoder, split_data,
    classification_metrics, ranker_metrics,
)

log = logging.getLogger("nara.benchmark")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

LATENCY_RUNS = 1000  # number of inference calls for latency measurement


# ── Latency measurement ───────────────────────────────────────

def measure_latency_ms(fn, *args, n_runs: int = LATENCY_RUNS) -> dict:
    """
    Measure inference latency over n_runs calls.
    Returns p50, p95, p99, mean in milliseconds.
    """
    times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        fn(*args)
        times.append((time.perf_counter() - t0) * 1000)

    times = sorted(times)
    return {
        "p50_ms":  round(times[int(n_runs * 0.50)], 3),
        "p95_ms":  round(times[int(n_runs * 0.95)], 3),
        "p99_ms":  round(times[int(n_runs * 0.99)], 3),
        "mean_ms": round(np.mean(times), 3),
    }


# ── Data preparation helpers ──────────────────────────────────

def prepare_ranker_data():
    from config import RANKER_FEATURES, RANKER_ACTION_MAP, CONDITION_FLAGS
    interactions = load_interactions()
    users        = load_users()
    kb           = load_nutrition_kb()

    user_cols = ["user_id", "age", "health_literacy", "habit_strength",
                 "bmi", "income_tier", "region", "is_vegetarian",
                 "conditions", "activity_level", "stress_profile"]
    user_slim = users[user_cols].drop_duplicates("user_id")
    df = interactions.merge(user_slim, on="user_id", how="left")
    df = extract_nutrition_from_kb(df, kb, dish_col="dish_name")
    df = expand_conditions(df, "conditions")
    df["action_score"] = df["action"].map(RANKER_ACTION_MAP).fillna(0).astype(int)

    num_cols  = [c for c in RANKER_FEATURES["numerical"]  if c in df.columns]
    cat_cols  = [c for c in RANKER_FEATURES["categorical"] if c in df.columns]
    bin_cols  = [c for c in RANKER_FEATURES["binary"]      if c in df.columns]
    cond_cols = [c for c in CONDITION_FLAGS if c in df.columns]
    bin_cols  = list(set(bin_cols + cond_cols))
    df[num_cols] = df[num_cols].fillna(0)
    df[bin_cols] = df[bin_cols].fillna(0).astype(int)

    encoder = FeatureEncoder()
    df_enc  = encoder.fit_transform(df.copy(), cat_cols, num_cols)
    feature_cols = num_cols + cat_cols + bin_cols
    X = df_enc[feature_cols].fillna(0)
    y = df["action_score"]
    _, _, X_test, _, _, y_test = split_data(X, y)
    return X_test, y_test, feature_cols


def prepare_cold_start_data():
    from config import COLD_START_FEATURES, CONDITION_FLAGS
    users     = load_users()
    meal_logs = load_meal_logs(parse_dates=False)

    top_cuisine = derive_top_cuisine_per_user(meal_logs)
    df = users.merge(top_cuisine, on="user_id", how="inner")
    df = expand_conditions(df, "conditions")

    restriction_flags = ["vegetarian", "low_gi", "low_sodium", "no_dairy",
                         "no_gluten", "halal", "jain", "no_beef"]
    for flag in restriction_flags:
        df[f"restr_{flag}"] = df["dietary_restrictions"].fillna("").str.contains(
            flag, regex=False).astype(int)

    num_cols  = [c for c in COLD_START_FEATURES["numerical"]  if c in df.columns]
    cat_cols  = [c for c in COLD_START_FEATURES["categorical"] if c in df.columns]
    bin_cols  = [c for c in COLD_START_FEATURES["binary"]      if c in df.columns]
    cond_cols = [c for c in CONDITION_FLAGS if c in df.columns]
    restr_cols= [f"restr_{f}" for f in restriction_flags if f"restr_{f}" in df.columns]
    bin_cols  = list(set(bin_cols + cond_cols + restr_cols))
    df[num_cols] = df[num_cols].fillna(0)
    df[bin_cols] = df[bin_cols].fillna(0).astype(int)

    encoder = FeatureEncoder()
    df_enc  = encoder.fit_transform(df.copy(), cat_cols, num_cols)
    feature_cols = num_cols + cat_cols + bin_cols
    X = df_enc[feature_cols].fillna(0)
    y = df["top_cuisine"]
    _, _, X_test, _, _, y_test = split_data(X, y)
    return X_test, y_test, feature_cols


def prepare_health_data():
    from config import HEALTH_SCORER_FEATURES, CONDITION_FLAGS
    meal_logs = load_meal_logs(parse_dates=False)
    users     = load_users()

    user_cols = ["user_id", "conditions", "health_literacy",
                 "age", "bmi", "activity_level", "is_vegetarian"]
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
    df_enc  = encoder.fit_transform(df.copy(), cat_cols, num_cols)
    feature_cols = num_cols + cat_cols + bin_cols
    X = df_enc[feature_cols].fillna(0)
    y = df["health_compliant"].fillna(1).astype(int)
    _, _, X_test, _, _, y_test = split_data(X, y)
    return X_test, y_test, feature_cols


# ── Individual model benchmarkers ─────────────────────────────

def benchmark_ranker_logistic(X_test, y_test):
    path = MODEL_PATHS["ranker_logistic"]
    if not os.path.exists(path):
        return None
    payload = joblib.load(path)
    model   = payload["model"]

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)
    metrics = classification_metrics(y_test, y_pred, y_prob, label="ranker_logistic")
    metrics.update(ranker_metrics(y_test.values, y_prob[:, 2], label="ranker_logistic"))

    single_row = X_test.iloc[[0]]
    latency = measure_latency_ms(model.predict_proba, single_row)
    return {**metrics, **latency, "model_size_mb": os.path.getsize(path) / 1e6}


def benchmark_ranker_xgboost(X_test, y_test):
    import xgboost as xgb
    path = MODEL_PATHS["ranker_xgboost"]
    if not os.path.exists(path):
        return None
    model = xgb.XGBClassifier()
    model.load_model(path)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)
    metrics = classification_metrics(y_test, y_pred, y_prob, label="ranker_xgboost")
    metrics.update(ranker_metrics(y_test.values, y_prob[:, 2], label="ranker_xgboost"))

    single_row = X_test.iloc[[0]]
    latency = measure_latency_ms(model.predict_proba, single_row)
    return {**metrics, **latency, "model_size_mb": os.path.getsize(path) / 1e6}


def benchmark_ranker_lgbm(X_test, y_test):
    import lightgbm as lgb
    path = MODEL_PATHS["ranker_lgbm"]
    if not os.path.exists(path):
        return None
    booster = lgb.Booster(model_file=path)

    y_prob = booster.predict(X_test)
    y_pred = np.argmax(y_prob, axis=1)
    metrics = classification_metrics(y_test, y_pred, y_prob, label="ranker_lgbm")
    metrics.update(ranker_metrics(y_test.values, y_prob[:, 2], label="ranker_lgbm"))

    single_row = X_test.iloc[[0]]
    latency = measure_latency_ms(booster.predict, single_row)
    return {**metrics, **latency, "model_size_mb": os.path.getsize(path) / 1e6}


def benchmark_cold_start_knn(X_test, y_test):
    path = MODEL_PATHS["cold_start_knn"]
    if not os.path.exists(path):
        return None
    payload = joblib.load(path)
    model   = payload["model"]

    y_pred = model.predict(X_test)
    metrics = classification_metrics(y_test, y_pred, label="cold_start_knn")

    single_row = X_test.iloc[[0]]
    latency = measure_latency_ms(model.predict, single_row)
    return {**metrics, **latency, "model_size_mb": os.path.getsize(path) / 1e6}


def benchmark_cold_start_mlp(X_test, y_test):
    path = MODEL_PATHS["cold_start_mlp"]
    if not os.path.exists(path):
        return None

    from cold_start.train_mlp import DemographicMLP
    checkpoint  = torch.load(path, map_location="cpu")
    model       = DemographicMLP(
        input_dim   = checkpoint["input_dim"],
        hidden_dims = checkpoint["hidden_dims"],
        num_classes = checkpoint["num_classes"],
        dropout     = checkpoint["dropout"],
    )
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    X_arr   = torch.FloatTensor(X_test.values)
    with torch.no_grad():
        probs = torch.softmax(model(X_arr), dim=1).numpy()
    y_pred_idx = np.argmax(probs, axis=1)

    y_classes  = checkpoint["y_classes"]
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    le.classes_ = np.array(y_classes)
    y_pred = le.inverse_transform(y_pred_idx)

    metrics = classification_metrics(y_test, y_pred, label="cold_start_mlp")

    single = torch.FloatTensor(X_test.iloc[[0]].values)
    latency = measure_latency_ms(lambda x: model(x), single)
    return {**metrics, **latency, "model_size_mb": os.path.getsize(path) / 1e6}


def benchmark_cold_start_wide_deep(X_test, y_test):
    path = MODEL_PATHS["cold_start_wide_deep"]
    if not os.path.exists(path):
        return None

    from cold_start.train_wide_deep import WideAndDeep
    from sklearn.preprocessing import OneHotEncoder, LabelEncoder
    from config import COLD_START_FEATURES, CONDITION_FLAGS

    checkpoint = torch.load(path, map_location="cpu")
    model = WideAndDeep(
        wide_dim      = checkpoint["wide_dim"],
        deep_input_dim= checkpoint["deep_dim"],
        deep_dims     = checkpoint["deep_dims"],
        num_classes   = checkpoint["num_classes"],
        dropout       = checkpoint["dropout"],
    )
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    # Approximate wide/deep split from test data
    X_arr = X_test.values.astype(np.float32)
    split = checkpoint["wide_dim"]
    X_w   = torch.FloatTensor(X_arr[:, :split] if X_arr.shape[1] >= split else X_arr)
    X_d   = torch.FloatTensor(X_arr)

    with torch.no_grad():
        probs = torch.softmax(model(X_w, X_d), dim=1).numpy()
    y_pred_idx = np.argmax(probs, axis=1)

    y_classes = checkpoint["y_classes"]
    le = LabelEncoder()
    le.classes_ = np.array(y_classes)
    y_pred = le.inverse_transform(np.clip(y_pred_idx, 0, len(y_classes) - 1))

    metrics = classification_metrics(y_test, y_pred, label="cold_start_wide_deep")
    latency = measure_latency_ms(lambda: model(X_w[[0]], X_d[[0]]))
    return {**metrics, **latency, "model_size_mb": os.path.getsize(path) / 1e6}


def benchmark_health_rf(X_test, y_test):
    path = MODEL_PATHS["health_rf"]
    if not os.path.exists(path):
        return None
    payload = joblib.load(path)
    model   = payload["model"]

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)
    metrics = classification_metrics(y_test, y_pred, y_prob, label="health_rf")

    single_row = X_test.iloc[[0]]
    latency = measure_latency_ms(model.predict, single_row)
    return {**metrics, **latency, "model_size_mb": os.path.getsize(path) / 1e6}


def benchmark_health_xgb(X_test, y_test):
    import xgboost as xgb
    path = MODEL_PATHS["health_xgb"]
    if not os.path.exists(path):
        return None
    model = xgb.XGBClassifier()
    model.load_model(path)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)
    metrics = classification_metrics(y_test, y_pred, y_prob, label="health_xgb")

    single_row = X_test.iloc[[0]]
    latency = measure_latency_ms(model.predict_proba, single_row)
    return {**metrics, **latency, "model_size_mb": os.path.getsize(path) / 1e6}


def benchmark_health_rules(X_test, y_test):
    from health_scorer.train_rules import RuleBasedHealthScorer
    scorer = RuleBasedHealthScorer()
    y_pred = scorer.predict_batch(X_test)
    metrics = classification_metrics(y_test, y_pred, label="health_rules")

    single_row = X_test.iloc[0:1]
    latency = measure_latency_ms(scorer.predict_batch, single_row)
    metrics.update(latency)
    metrics["model_size_mb"] = 0.001
    return metrics


# ── Comparison table ──────────────────────────────────────────

def print_comparison_table(results: dict):
    rows = []
    for model_name, metrics in results.items():
        if metrics is None:
            continue
        rows.append({
            "Model":        model_name,
            "Accuracy":     metrics.get("accuracy", "—"),
            "F1":           metrics.get("f1", "—"),
            "AUC":          metrics.get("auc", "—"),
            "NDCG@10":      metrics.get("ndcg_10", "—"),
            "p50_ms":       metrics.get("p50_ms", "—"),
            "p95_ms":       metrics.get("p95_ms", "—"),
            "Size_MB":      round(metrics.get("model_size_mb", 0), 2),
        })

    df = pd.DataFrame(rows)
    print("\n" + "=" * 100)
    print("  NARA MODEL BENCHMARK RESULTS")
    print("=" * 100)
    print(df.to_string(index=False))
    print("=" * 100)

    # Save
    os.makedirs(MODELS_DIR, exist_ok=True)
    path = os.path.join(MODELS_DIR, "benchmark_results.csv")
    df.to_csv(path, index=False)
    log.info(f"Benchmark results saved → {path}")

    # Save full JSON
    json_path = os.path.join(MODELS_DIR, "benchmark_results.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    log.info(f"Full benchmark saved → {json_path}")

    # Print winners per category
    print("\n  WINNERS PER CATEGORY")
    print("-" * 60)
    categories = {
        "Recommendation Ranker": ["ranker_logistic", "ranker_xgboost", "ranker_lgbm"],
        "Cold Start":            ["cold_start_knn", "cold_start_mlp", "cold_start_wide_deep"],
        "Health Scorer":         ["health_rules", "health_rf", "health_xgb"],
    }
    for cat, models in categories.items():
        best_f1   = -1
        best_model= None
        for m in models:
            if m in results and results[m] and results[m].get("f1", 0) > best_f1:
                best_f1   = results[m]["f1"]
                best_model= m
        if best_model:
            lat = results[best_model].get("p50_ms", "?")
            print(f"  {cat:<30} → {best_model:<35} F1={best_f1:.4f}  p50={lat}ms")
    print("=" * 100)


# ── Main ──────────────────────────────────────────────────────

def run_benchmark():
    log.info("=" * 60)
    log.info("NARA ML Benchmark Starting")
    log.info("=" * 60)

    results = {}

    # ── Recommendation Ranker ─────────────────────────────────
    log.info("\n[1/3] Benchmarking Recommendation Ranker...")
    try:
        X_test, y_test, _ = prepare_ranker_data()
        results["ranker_logistic"] = benchmark_ranker_logistic(X_test, y_test)
        results["ranker_xgboost"]  = benchmark_ranker_xgboost(X_test, y_test)
        results["ranker_lgbm"]     = benchmark_ranker_lgbm(X_test, y_test)
    except Exception as e:
        log.error(f"Ranker benchmark failed: {e}")

    # ── Cold Start ────────────────────────────────────────────
    log.info("\n[2/3] Benchmarking Cold Start...")
    try:
        X_test, y_test, _ = prepare_cold_start_data()
        results["cold_start_knn"]       = benchmark_cold_start_knn(X_test, y_test)
        results["cold_start_mlp"]       = benchmark_cold_start_mlp(X_test, y_test)
        results["cold_start_wide_deep"] = benchmark_cold_start_wide_deep(X_test, y_test)
    except Exception as e:
        log.error(f"Cold start benchmark failed: {e}")

    # ── Health Scorer ─────────────────────────────────────────
    log.info("\n[3/3] Benchmarking Health Scorer...")
    try:
        X_test, y_test, _ = prepare_health_data()
        results["health_rules"] = benchmark_health_rules(X_test, y_test)
        results["health_rf"]    = benchmark_health_rf(X_test, y_test)
        results["health_xgb"]   = benchmark_health_xgb(X_test, y_test)
    except Exception as e:
        log.error(f"Health scorer benchmark failed: {e}")

    print_comparison_table(results)
    return results


if __name__ == "__main__":
    run_benchmark()