"""
NARA ML Training — Central Config
All hyperparameters, paths, and settings in one place.
Change anything here — all training scripts read from this file.
"""
import os

# ── Data paths ────────────────────────────────────────────────
# Point these to wherever your CSVs are
DATA_DIR = os.environ.get("NARA_DATA_DIR", "../../scripts/synthetic_data/data")

PATHS = {
    "users":            os.path.join(DATA_DIR, "users.csv"),
    "meal_logs":        os.path.join(DATA_DIR, "meal_logs.csv"),
    "interactions":     os.path.join(DATA_DIR, "interactions.csv"),
    "life_events":      os.path.join(DATA_DIR, "life_events.csv"),
    "reorder_events":   os.path.join(DATA_DIR, "reorder_events.csv"),
    "health_outcomes":  os.path.join(DATA_DIR, "health_outcomes.csv"),
    "weekly_context":   os.path.join(DATA_DIR, "user_weekly_context.csv"),
    "social_context":   os.path.join(DATA_DIR, "social_eating_context.csv"),
    "nutrition_kb":     os.path.join(DATA_DIR, "nutrition_kb.csv"),
}

# ── Model output paths ────────────────────────────────────────
MODELS_DIR = os.environ.get("NARA_MODELS_DIR", "./models")

MODEL_PATHS = {
    # Recommendation Ranker
    "ranker_logistic":      os.path.join(MODELS_DIR, "ranker_logistic.joblib"),
    "ranker_xgboost":       os.path.join(MODELS_DIR, "ranker_xgboost.json"),
    "ranker_xgboost_onnx":  os.path.join(MODELS_DIR, "ranker_xgboost.onnx"),
    "ranker_lgbm":          os.path.join(MODELS_DIR, "ranker_lgbm.txt"),
    "ranker_lgbm_onnx":     os.path.join(MODELS_DIR, "ranker_lgbm.onnx"),

    # Cold Start
    "cold_start_knn":       os.path.join(MODELS_DIR, "cold_start_knn.joblib"),
    "cold_start_mlp":       os.path.join(MODELS_DIR, "cold_start_mlp.pt"),
    "cold_start_wide_deep": os.path.join(MODELS_DIR, "cold_start_wide_deep.pt"),

    # Health Scorer
    "health_rf":            os.path.join(MODELS_DIR, "health_rf.joblib"),
    "health_xgb":           os.path.join(MODELS_DIR, "health_xgb.json"),
    "health_xgb_onnx":      os.path.join(MODELS_DIR, "health_xgb.onnx"),

    # Occasion Classifier
    "occasion_dt":          os.path.join(MODELS_DIR, "occasion_dt.joblib"),
    "occasion_rf":          os.path.join(MODELS_DIR, "occasion_rf.joblib"),
    "occasion_xgb":         os.path.join(MODELS_DIR, "occasion_xgb.json"),
    "occasion_xgb_onnx":    os.path.join(MODELS_DIR, "occasion_xgb.onnx"),

    # Reorder Prediction
    "reorder_logistic":     os.path.join(MODELS_DIR, "reorder_logistic.joblib"),
    "reorder_rf":           os.path.join(MODELS_DIR, "reorder_rf.joblib"),
    "reorder_xgb":          os.path.join(MODELS_DIR, "reorder_xgb.json"),
    "reorder_xgb_onnx":     os.path.join(MODELS_DIR, "reorder_xgb.onnx"),

    # Encoders and preprocessors
    "encoders":             os.path.join(MODELS_DIR, "encoders.joblib"),
}

# ── Training settings ─────────────────────────────────────────
RANDOM_STATE = 42
TEST_SIZE    = 0.20   # 80/20 train/test split
VAL_SIZE     = 0.10   # 10% of train as validation

# ── Target label mappings ─────────────────────────────────────
# Recommendation Ranker
RANKER_ACTION_MAP = {"skip": 0, "click": 1, "order": 2}

# Meal Occasion Classifier
OCCASION_MAP = {
    "breakfast": 0, "lunch": 1, "snack": 2,
    "dinner": 3, "late_night": 4,
}
OCCASION_MAP_INV = {v: k for k, v in OCCASION_MAP.items()}

# ── Feature lists ─────────────────────────────────────────────
# These are the exact columns each model uses
# X = input features, Y = prediction target

RANKER_FEATURES = {
    # INPUT FEATURES (X)
    "numerical": [
        "context_time_of_day",    # hour 0-23
        "context_day",            # 0=Monday 6=Sunday
        "context_budget",         # 0.7-1.4 month position multiplier
        "recommendation_rank",    # 0-9 position shown to user
        "cuisine_affinity",       # 0-1 user affinity for this dish cuisine
        "price_match_score",      # 0-1 how well dish price matches budget
        "user_health_match",      # 0-1 how well dish matches health profile
        # From users.csv join
        "age",
        "health_literacy",
        "habit_strength",
        "bmi",
        # From nutrition_kb join
        "gi_score",
        "calories_kcal",
        "protein_g",
        "carbs_g",
        "fat_g",
        "fiber_g",
    ],
    "categorical": [
        "context_season",         # summer/monsoon/winter/autumn
        "context_stress",         # none/low/medium/high
        "income_tier",            # low/medium/high
        "region",                 # south/north/west/east
        "cuisine_type",           # dish cuisine category
    ],
    "binary": [
        "is_vegetarian",
        "was_top3",               # was dish in top 3 shown
    ],
    # PREDICTION TARGET (Y)
    "target": "action_score",     # 0=skip, 1=click, 2=order
}

COLD_START_FEATURES = {
    # INPUT FEATURES (X)
    "numerical": [
        "age",
        "health_literacy",
        "habit_strength",
        "bmi",
        "observance_level",
        "order_frequency_weekly",
    ],
    "categorical": [
        "birthplace_state",
        "current_state",
        "religion",
        "gender",
        "occupation",
        "income_tier",
        "living_situation",
        "activity_level",
    ],
    "binary": [
        "is_vegetarian",
        "is_jain",
        "is_halal",
    ],
    "multi_hot": [
        "conditions",             # pipe-separated, e.g. "type2_diabetes|hypertension"
        "dietary_restrictions",
    ],
    # PREDICTION TARGET (Y)
    "target": "top_cuisine",      # derived: most frequent cuisine in meal_logs for this user
}

HEALTH_SCORER_FEATURES = {
    # INPUT FEATURES (X)
    "numerical": [
        "gi_score",               # glycemic index of dish
        "estimated_calories",
        "estimated_protein_g",
        "estimated_carbs_g",
        "estimated_fat_g",
        "estimated_fiber_g",
        "portion_multiplier",
        "age",
        "bmi",
        "health_literacy",
    ],
    "categorical": [
        "meal_occasion",          # breakfast/lunch/dinner/snack
        "season",
        "stress_level",
        "activity_level",
    ],
    "binary": [
        "is_festival_day",
        "is_fast_day",
        "is_vegetarian",
        # Condition flags (derived from conditions column)
        "has_diabetes",
        "has_prediabetes",
        "has_hypertension",
        "has_obesity",
        "has_pcos",
        "has_high_cholesterol",
    ],
    # PREDICTION TARGET (Y)
    "target": "health_compliant",  # 0 or 1
}

OCCASION_FEATURES = {
    # INPUT FEATURES (X)
    "numerical": [
        "hour",                   # extracted from occurred_at
        "day_of_week",            # 0-6
        "month",                  # 1-12
        "budget_availability",    # 0.7-1.4
        "commute_minutes",
        "age",
    ],
    "categorical": [
        "season",
        "stress_level",
        "month_position",         # early/mid/late
        "occupation",
        "living_situation",
    ],
    "binary": [
        "is_weekend",
        "cooking_at_home",
        "ordered_delivery",
        "is_festival_day",
        "is_fast_day",
        "is_wfh",
    ],
    # PREDICTION TARGET (Y)
    "target": "meal_occasion",    # breakfast/lunch/snack/dinner/late_night
}

REORDER_FEATURES = {
    # INPUT FEATURES (X)
    "numerical": [
        "days_between",           # days since first order
        "total_orders_dish",      # how many times ordered this dish
        "last_rating_proxy",      # 3.0-5.0 satisfaction proxy
        "habit_strength",
        "health_literacy",
        "age",
        "order_frequency_weekly",
    ],
    "categorical": [
        "trigger_type",           # habit/craving/convenience/festival/stress
        "income_tier",
        "occupation",
        "stress_profile",
        "season",                 # derived from reorder_date
        "month_position",         # derived from reorder_date
    ],
    "binary": [
        "is_vegetarian",
    ],
    # PREDICTION TARGET (Y)
    "target": "reordered_yes_no",  # True/False
}

# ── Logistic Regression hyperparams ──────────────────────────
LOGISTIC_PARAMS = {
    "C":            1.0,
    "max_iter":     1000,
    "random_state": RANDOM_STATE,
    "n_jobs":       -1,
}

# ── Random Forest hyperparams ─────────────────────────────────
RF_PARAMS = {
    "n_estimators":     300,
    "max_depth":        12,
    "min_samples_leaf": 10,
    "n_jobs":           -1,
    "random_state":     RANDOM_STATE,
    "class_weight":     "balanced",
}

# ── XGBoost hyperparams ───────────────────────────────────────
XGB_PARAMS = {
    "n_estimators":     500,
    "max_depth":        8,
    "learning_rate":    0.05,
    "subsample":        0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "gamma":            0.1,
    "reg_alpha":        0.1,
    "reg_lambda":       1.0,
    "random_state":     RANDOM_STATE,
    "n_jobs":           -1,
    "tree_method":      "hist",   # fast histogram method
    "eval_metric":      "mlogloss",
}

# ── LightGBM hyperparams ──────────────────────────────────────
LGBM_PARAMS = {
    "n_estimators":         2000,
    "max_depth":            -1,
    "learning_rate":        0.03,
    "num_leaves":           255,
    "subsample":            0.85,
    "colsample_bytree":     0.85,
    "min_child_samples":    20,
    "reg_alpha":            0.5,
    "reg_lambda":           1.0,
    "random_state":         RANDOM_STATE,
    "n_jobs":               -1,
    "verbose":              -1,
}

# ── Decision Tree hyperparams ─────────────────────────────────
DT_PARAMS = {
    "max_depth":        8,
    "min_samples_leaf": 20,
    "class_weight":     "balanced",
    "random_state":     RANDOM_STATE,
}

# ── MLP hyperparams (PyTorch) ─────────────────────────────────
MLP_PARAMS = {
    "hidden_dims":  [128, 64, 32],
    "dropout":      0.3,
    "lr":           0.001,
    "batch_size":   512,
    "epochs":       50,
    "patience":     5,           # early stopping patience
}

# ── Wide and Deep hyperparams ─────────────────────────────────
WIDE_DEEP_PARAMS = {
    "deep_dims":    [256, 128, 64],
    "dropout":      0.3,
    "lr":           0.001,
    "batch_size":   512,
    "epochs":       50,
    "patience":     5,
    "embedding_dim": 16,         # embedding size for categorical features
}

# ── ONNX export settings ──────────────────────────────────────
ONNX_OPSET = 12

# ── Condition flags for health scorer ────────────────────────
# These get derived from the pipe-separated conditions column
CONDITION_FLAGS = [
    "has_diabetes",
    "has_prediabetes",
    "has_hypertension",
    "has_obesity",
    "has_pcos",
    "has_high_cholesterol",
    "has_thyroid",
    "has_ibs",
    "has_anemia",
]

CONDITION_MAP = {
    "has_diabetes":         "type2_diabetes",
    "has_prediabetes":      "prediabetes",
    "has_hypertension":     "hypertension",
    "has_obesity":          "obesity",
    "has_pcos":             "pcos",
    "has_high_cholesterol": "high_cholesterol",
    "has_thyroid":          "thyroid",
    "has_ibs":              "ibs",
    "has_anemia":           "anemia",
}

# ── Logging ───────────────────────────────────────────────────
LOG_LEVEL = "INFO"
SAVE_PLOTS = True
PLOTS_DIR  = os.path.join(MODELS_DIR, "plots")