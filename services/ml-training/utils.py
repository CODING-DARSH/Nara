"""
NARA ML Training — Shared Utilities
Used by all training scripts.
Handles: data loading, feature engineering, encoding, metrics, model saving.
"""
import os
import sys
import json
import joblib
import logging
import numpy as np
import pandas as pd
from typing import Optional

from sklearn.preprocessing import LabelEncoder, StandardScaler, OrdinalEncoder
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
    ndcg_score, accuracy_score, f1_score, precision_score, recall_score,
    mean_absolute_error, mean_squared_error,
)
from sklearn.model_selection import train_test_split

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import (
    PATHS, MODEL_PATHS, MODELS_DIR, PLOTS_DIR,
    RANDOM_STATE, TEST_SIZE, VAL_SIZE,
    CONDITION_FLAGS, CONDITION_MAP, SAVE_PLOTS,
    RANKER_ACTION_MAP, OCCASION_MAP,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("nara.training")


# ── Data loaders ──────────────────────────────────────────────

def load_users() -> pd.DataFrame:
    log.info(f"Loading users from {PATHS['users']}")
    df = pd.read_csv(PATHS["users"])
    log.info(f"  {len(df):,} users loaded")
    return df


def load_meal_logs(parse_dates: bool = True) -> pd.DataFrame:
    log.info(f"Loading meal logs from {PATHS['meal_logs']}")
    df = pd.read_csv(
        PATHS["meal_logs"],
        parse_dates=["occurred_at"] if parse_dates else False,
    )
    log.info(f"  {len(df):,} meal logs loaded")
    return df


def load_interactions() -> pd.DataFrame:
    log.info(f"Loading interactions from {PATHS['interactions']}")
    df = pd.read_csv(PATHS["interactions"])
    log.info(f"  {len(df):,} interactions loaded")
    return df


def load_reorder_events() -> pd.DataFrame:
    log.info(f"Loading reorder events from {PATHS['reorder_events']}")
    df = pd.read_csv(PATHS["reorder_events"])
    log.info(f"  {len(df):,} reorder events loaded")
    return df


def load_nutrition_kb() -> pd.DataFrame:
    log.info(f"Loading nutrition KB from {PATHS['nutrition_kb']}")
    df = pd.read_csv(PATHS["nutrition_kb"])
    log.info(f"  {len(df):,} KB entries loaded")
    return df


# ── Feature engineering ───────────────────────────────────────

def expand_conditions(df: pd.DataFrame,
                       conditions_col: str = "conditions") -> pd.DataFrame:
    """
    Expand pipe-separated conditions column into binary flags.
    e.g. "type2_diabetes|hypertension" → has_diabetes=1, has_hypertension=1
    """
    for flag, condition in CONDITION_MAP.items():
        df[flag] = df[conditions_col].fillna("").str.contains(
            condition, regex=False
        ).astype(int)
    return df


def extract_nutrition_from_kb(df: pd.DataFrame,
                               kb: pd.DataFrame,
                               dish_col: str = "dish_name") -> pd.DataFrame:
    """
    Join nutrition features from KB onto a dataframe by dish_name.
    KB columns used: gi_score (glycemic_index), calories_kcal, protein_g, carbs_g, fat_g, fiber_g
    """
    # Rename KB columns to match our feature names
    kb_features = kb[[
        "dish_name", "glycemic_index", "per_serving"
    ]].copy()
    kb_features = kb_features.rename(columns={"glycemic_index": "gi_score"})

    # Parse per_serving JSON if it's a string
    if kb_features["per_serving"].dtype == object:
        def parse_nutrition(row):
            try:
                if isinstance(row, str):
                    d = json.loads(row.replace("'", '"'))
                elif isinstance(row, dict):
                    d = row
                else:
                    return {}
                return d
            except Exception:
                return {}

        nutrition_parsed = kb_features["per_serving"].apply(parse_nutrition)
        kb_features["calories_kcal"] = nutrition_parsed.apply(lambda x: x.get("calories_kcal", 0))
        kb_features["protein_g"]     = nutrition_parsed.apply(lambda x: x.get("protein_g", 0))
        kb_features["carbs_g"]       = nutrition_parsed.apply(lambda x: x.get("carbs_g", 0))
        kb_features["fat_g"]         = nutrition_parsed.apply(lambda x: x.get("fat_g", 0))
        kb_features["fiber_g"]       = nutrition_parsed.apply(lambda x: x.get("fiber_g", 0))

    kb_slim = kb_features[[
        "dish_name", "gi_score", "calories_kcal",
        "protein_g", "carbs_g", "fat_g", "fiber_g"
    ]].drop_duplicates("dish_name")

    df = df.merge(kb_slim, left_on=dish_col, right_on="dish_name", how="left")

    # Fill missing KB entries with median
    for col in ["gi_score", "calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g"]:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    return df


def derive_top_cuisine_per_user(meal_logs: pd.DataFrame) -> pd.DataFrame:
    """
    Derive the top cuisine for each user from meal logs.
    Used as Y target for cold start model.
    Returns dataframe with user_id → top_cuisine
    """
    top_cuisine = (
        meal_logs.groupby(["user_id", "cuisine_type"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .groupby("user_id")
        .first()
        .reset_index()[["user_id", "cuisine_type"]]
        .rename(columns={"cuisine_type": "top_cuisine"})
    )
    return top_cuisine


def extract_hour_from_timestamp(df: pd.DataFrame,
                                  ts_col: str = "occurred_at") -> pd.DataFrame:
    """Extract hour feature from timestamp column."""
    if df[ts_col].dtype == object:
        df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
    df["hour"] = df[ts_col].dt.hour.fillna(12).astype(int)
    return df


def derive_season_from_date(date_col: pd.Series) -> pd.Series:
    """Derive season from date."""
    month_season = {
        1: "winter", 2: "winter", 3: "summer_onset",
        4: "summer", 5: "summer", 6: "monsoon_onset",
        7: "monsoon", 8: "monsoon", 9: "monsoon_end",
        10: "autumn", 11: "winter_onset", 12: "winter",
    }
    if date_col.dtype == object:
        date_col = pd.to_datetime(date_col, errors="coerce")
    return date_col.dt.month.map(month_season).fillna("summer")


def derive_month_position(date_col: pd.Series) -> pd.Series:
    """Derive month position (early/mid/late) from date."""
    if date_col.dtype == object:
        date_col = pd.to_datetime(date_col, errors="coerce")
    day = date_col.dt.day
    return pd.cut(
        day,
        bins=[0, 10, 20, 31],
        labels=["early", "mid", "late"],
        right=True,
    ).astype(str)


# ── Encoding ──────────────────────────────────────────────────

class FeatureEncoder:
    """
    Fits and transforms categorical features.
    Save once after fitting, reuse for inference.
    """

    def __init__(self):
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.fitted = False

    def fit_transform(self, df: pd.DataFrame,
                       categorical_cols: list,
                       numerical_cols: list) -> pd.DataFrame:
        df = df.copy()

        # Encode categoricals
        for col in categorical_cols:
            if col not in df.columns:
                log.warning(f"Column {col} not found, skipping")
                continue
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].fillna("unknown").astype(str))
            self.label_encoders[col] = le

        # Scale numericals
        num_cols_present = [c for c in numerical_cols if c in df.columns]
        if num_cols_present:
            df[num_cols_present] = self.scaler.fit_transform(
                df[num_cols_present].fillna(0)
            )

        self.fitted = True
        return df

    def transform(self, df: pd.DataFrame,
                   categorical_cols: list,
                   numerical_cols: list) -> pd.DataFrame:
        df = df.copy()

        for col in categorical_cols:
            if col not in df.columns or col not in self.label_encoders:
                continue
            le = self.label_encoders[col]
            # Handle unseen labels
            known = set(le.classes_)
            df[col] = df[col].fillna("unknown").astype(str).apply(
                lambda x: x if x in known else "unknown"
            )
            if "unknown" not in known:
                le.classes_ = np.append(le.classes_, "unknown")
            df[col] = le.transform(df[col])

        num_cols_present = [c for c in numerical_cols if c in df.columns]
        if num_cols_present:
            df[num_cols_present] = self.scaler.transform(
                df[num_cols_present].fillna(0)
            )

        return df

    def save(self, path: str):
        joblib.dump(self, path)
        log.info(f"Encoder saved → {path}")

    @classmethod
    def load(cls, path: str) -> "FeatureEncoder":
        return joblib.load(path)


# ── Train/test split ──────────────────────────────────────────

def split_data(X: pd.DataFrame, y: pd.Series,
               stratify: bool = True) -> tuple:
    """
    Returns X_train, X_val, X_test, y_train, y_val, y_test
    80% train, 10% val, 10% test
    """
    strat = y if stratify and y.nunique() < 20 else None

    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=strat
    )
    strat2 = y_train_val if stratify and y_train_val.nunique() < 20 else None
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val,
        test_size=VAL_SIZE / (1 - TEST_SIZE),
        random_state=RANDOM_STATE,
        stratify=strat2,
    )

    log.info(f"  Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}")
    return X_train, X_val, X_test, y_train, y_val, y_test


# ── Metrics ───────────────────────────────────────────────────

def classification_metrics(y_true, y_pred, y_prob=None,
                             label: str = "") -> dict:
    """Compute and log classification metrics."""
    acc   = accuracy_score(y_true, y_pred)
    f1    = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    prec  = precision_score(y_true, y_pred, average="weighted", zero_division=0)
    rec   = recall_score(y_true, y_pred, average="weighted", zero_division=0)

    metrics = {
        "accuracy":  round(acc, 4),
        "f1":        round(f1, 4),
        "precision": round(prec, 4),
        "recall":    round(rec, 4),
    }

    if y_prob is not None:
        try:
            if y_prob.ndim == 2 and y_prob.shape[1] == 2:
                auc = roc_auc_score(y_true, y_prob[:, 1])
            else:
                auc = roc_auc_score(y_true, y_prob, multi_class="ovr", average="weighted")
            metrics["auc"] = round(auc, 4)
        except Exception:
            pass

    prefix = f"[{label}] " if label else ""
    log.info(f"{prefix}Accuracy={metrics['accuracy']} | F1={metrics['f1']} | "
             f"Precision={metrics['precision']} | Recall={metrics['recall']}"
             + (f" | AUC={metrics.get('auc', 'n/a')}" if "auc" in metrics else ""))

    log.info(f"\n{classification_report(y_true, y_pred, zero_division=0)}")
    return metrics


def ranker_metrics(y_true, y_scores, df_index=None, label: str = "") -> dict:
    """
    Correct per-session NDCG.
    y_true  : graded relevance 0=skip, 1=click, 2=order
    y_scores: model.predict_proba()[:, 2]  (order probability)
    df_index: the original df index so we can extract session from interaction_id
    """
    try:
        if df_index is not None:
            # interaction_id looks like INT00000001R3
            # session = INT00000001, rank = 3
            session_ids = df_index.str.extract(r"(INT\d+)R\d+")[0]

            tmp = pd.DataFrame({
                "session": session_ids.values,
                "y_true":  np.array(y_true),
                "y_score": np.array(y_scores),
            })

            session_ndcgs = []
            for _, grp in tmp.groupby("session"):
                if len(grp) < 2:
                    continue
                try:
                    n = ndcg_score(
                        np.array([grp["y_true"].values]),
                        np.array([grp["y_score"].values]),
                        k=min(10, len(grp)),
                    )
                    session_ndcgs.append(n)
                except Exception:
                    continue

            ndcg = float(np.mean(session_ndcgs)) if session_ndcgs else 0.0

        else:
            # No session info — log warning, return 0
            logging.getLogger("nara.training").warning(
                "ranker_metrics: no session index provided, NDCG will be 0"
            )
            ndcg = 0.0

    except Exception as e:
        logging.getLogger("nara.training").warning(f"NDCG failed: {e}")
        ndcg = 0.0

    logging.getLogger("nara.training").info(f"[{label}] NDCG@10={ndcg:.4f}")
    return {"ndcg_10": ndcg}


def regression_metrics(y_true, y_pred, label: str = "") -> dict:
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred) ** 0.5
    metrics = {"mae": round(mae, 4), "rmse": round(rmse, 4)}
    prefix = f"[{label}] " if label else ""
    log.info(f"{prefix}MAE={metrics['mae']} | RMSE={metrics['rmse']}")
    return metrics


# ── Model saving ──────────────────────────────────────────────

def save_sklearn_model(model, path: str, metadata: dict = None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {"model": model, "metadata": metadata or {}}
    joblib.dump(payload, path)
    size_mb = os.path.getsize(path) / (1024 * 1024)
    log.info(f"Model saved → {path} ({size_mb:.1f} MB)")


def save_xgboost_model(model, path: str, onnx_path: str = None,
                        feature_names: list = None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    model.save_model(path)
    log.info(f"XGBoost model saved → {path}")

    if onnx_path and feature_names:
        try:
            from skl2onnx import convert_sklearn
            from skl2onnx.common.data_types import FloatTensorType
            from onnxmltools import convert_xgboost

            initial_type = [("float_input", FloatTensorType([None, len(feature_names)]))]
            onnx_model = convert_xgboost(model, initial_types=initial_type)
            with open(onnx_path, "wb") as f:
                f.write(onnx_model.SerializeToString())
            log.info(f"ONNX model saved → {onnx_path}")
        except ImportError:
            log.warning("skl2onnx/onnxmltools not installed, skipping ONNX export")
        except Exception as e:
            log.warning(f"ONNX export failed: {e}")


def save_lgbm_model(model, path: str, onnx_path: str = None,
                     feature_names: list = None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    model.booster_.save_model(path)
    log.info(f"LightGBM model saved → {path}")

    if onnx_path and feature_names:
        try:
            from onnxmltools import convert_lightgbm
            from skl2onnx.common.data_types import FloatTensorType

            initial_type = [("float_input", FloatTensorType([None, len(feature_names)]))]
            onnx_model = convert_lightgbm(model.booster_, initial_types=initial_type)
            with open(onnx_path, "wb") as f:
                f.write(onnx_model.SerializeToString())
            log.info(f"ONNX model saved → {onnx_path}")
        except ImportError:
            log.warning("onnxmltools not installed, skipping ONNX export")
        except Exception as e:
            log.warning(f"ONNX export failed: {e}")


def save_metrics(metrics: dict, model_name: str):
    """Save metrics to JSON for comparison."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    path = os.path.join(MODELS_DIR, f"{model_name}_metrics.json")
    with open(path, "w") as f:
        json.dump(metrics, f, indent=2)
    log.info(f"Metrics saved → {path}")


def plot_confusion_matrix(y_true, y_pred, labels: list,
                           title: str, filename: str):
    """Save confusion matrix plot."""
    if not SAVE_PLOTS:
        return
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns

        os.makedirs(PLOTS_DIR, exist_ok=True)
        cm = confusion_matrix(y_true, y_pred)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt="d", xticklabels=labels, yticklabels=labels)
        plt.title(title)
        plt.ylabel("True")
        plt.xlabel("Predicted")
        plt.tight_layout()
        path = os.path.join(PLOTS_DIR, filename)
        plt.savefig(path)
        plt.close()
        log.info(f"Confusion matrix saved → {path}")
    except ImportError:
        log.warning("matplotlib/seaborn not installed, skipping plot")


def plot_feature_importance(feature_names: list, importances: list,
                             title: str, filename: str, top_n: int = 20):
    """Save feature importance plot."""
    if not SAVE_PLOTS:
        return
    try:
        import matplotlib.pyplot as plt

        os.makedirs(PLOTS_DIR, exist_ok=True)
        pairs = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)[:top_n]
        names, vals = zip(*pairs)

        plt.figure(figsize=(10, 6))
        plt.barh(list(names)[::-1], list(vals)[::-1])
        plt.title(title)
        plt.xlabel("Importance")
        plt.tight_layout()
        path = os.path.join(PLOTS_DIR, filename)
        plt.savefig(path)
        plt.close()
        log.info(f"Feature importance saved → {path}")
    except ImportError:
        log.warning("matplotlib not installed, skipping plot")


# ── Ensure model dir exists ───────────────────────────────────
os.makedirs(MODELS_DIR, exist_ok=True)