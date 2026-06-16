"""
NARA — Model Loader
Loads all trained models at startup.
Swap models by changing config.active_* settings.
"""
import os
import logging
import joblib
import torch
import numpy as np

log = logging.getLogger("nara.recommendation.model_loader")


class ModelStore:
    """
    Central store for all loaded models.
    Loaded once at startup, reused for every request.
    """

    def __init__(self):
        self.ranker         = None
        self.ranker_type    = None
        self.cold_start     = None
        self.cold_start_type= None
        self.health_scorer  = None
        self.health_type    = None
        self.occasion       = None
        self.occasion_type  = None
        self.reorder        = None
        self.reorder_type   = None
        self.loaded         = False
        self._y_classes     = {}

    def load_all(self, models_dir: str, settings):
        log.info(f"Loading models from {models_dir}")

        self._load_ranker(models_dir, settings.active_ranker)
        self._load_cold_start(models_dir, settings.active_cold_start)
        self._load_health_scorer(models_dir, settings.active_health_scorer)
        self._load_occasion(models_dir, settings.active_occasion)
        self._load_reorder(models_dir, settings.active_reorder)

        self.loaded = True
        log.info("All models loaded successfully")

    def _load_ranker(self, models_dir: str, model_type: str):
        try:
            if model_type == "lgbm":
                import lightgbm as lgb
                path = os.path.join(models_dir, "ranker_lgbm.txt")
                if os.path.exists(path):
                    self.ranker = lgb.Booster(model_file=path)
                    self.ranker_type = "lgbm"
                    log.info(f"  Ranker: LightGBM loaded")
                else:
                    self._fallback_ranker(models_dir)
            elif model_type == "xgboost":
                import xgboost as xgb
                path = os.path.join(models_dir, "ranker_xgboost.json")
                if os.path.exists(path):
                    model = xgb.XGBClassifier()
                    model.load_model(path)
                    self.ranker = model
                    self.ranker_type = "xgboost"
                    log.info(f"  Ranker: XGBoost loaded")
                else:
                    self._fallback_ranker(models_dir)
            else:
                self._fallback_ranker(models_dir)
        except Exception as e:
            log.warning(f"  Ranker load failed: {e}, using fallback")
            self._fallback_ranker(models_dir)

    def _fallback_ranker(self, models_dir: str):
        path = os.path.join(models_dir, "ranker_logistic.joblib")
        if os.path.exists(path):
            payload = joblib.load(path)
            self.ranker = payload.get("model", payload)
            self.ranker_type = "logistic"
            log.info("  Ranker: Logistic fallback loaded")
        else:
            log.warning("  Ranker: No model found, using rule-based fallback")
            self.ranker = None
            self.ranker_type = "rules"

    def _load_cold_start(self, models_dir: str, model_type: str):
        try:
            if model_type == "wide_deep":
                path = os.path.join(models_dir, "cold_start_wide_deep.pt")
                if os.path.exists(path):
                    self.cold_start = torch.load(path, map_location="cpu")
                    self.cold_start_type = "wide_deep"
                    self._y_classes["cold_start"] = self.cold_start.get("y_classes", [])
                    log.info("  Cold start: Wide & Deep loaded")
                else:
                    self._fallback_cold_start(models_dir)
            elif model_type == "mlp":
                path = os.path.join(models_dir, "cold_start_mlp.pt")
                if os.path.exists(path):
                    self.cold_start = torch.load(path, map_location="cpu")
                    self.cold_start_type = "mlp"
                    self._y_classes["cold_start"] = self.cold_start.get("y_classes", [])
                    log.info("  Cold start: MLP loaded")
                else:
                    self._fallback_cold_start(models_dir)
            else:
                self._fallback_cold_start(models_dir)
        except Exception as e:
            log.warning(f"  Cold start load failed: {e}")
            self._fallback_cold_start(models_dir)

    def _fallback_cold_start(self, models_dir: str):
        path = os.path.join(models_dir, "cold_start_knn.joblib")
        if os.path.exists(path):
            payload = joblib.load(path)
            self.cold_start = payload.get("model", payload)
            self.cold_start_type = "knn"
            log.info("  Cold start: KNN fallback loaded")
        else:
            self.cold_start = None
            self.cold_start_type = "rules"

    def _load_health_scorer(self, models_dir: str, model_type: str):
        try:
            if model_type == "xgb":
                import xgboost as xgb
                path = os.path.join(models_dir, "health_xgb.json")
                if os.path.exists(path):
                    model = xgb.XGBClassifier()
                    model.load_model(path)
                    self.health_scorer = model
                    self.health_type = "xgb"
                    log.info("  Health scorer: XGBoost loaded")
                else:
                    self._fallback_health(models_dir)
            elif model_type == "rf":
                path = os.path.join(models_dir, "health_rf.joblib")
                if os.path.exists(path):
                    payload = joblib.load(path)
                    self.health_scorer = payload.get("model", payload)
                    self.health_type = "rf"
                    log.info("  Health scorer: Random Forest loaded")
                else:
                    self._fallback_health(models_dir)
            else:
                self._fallback_health(models_dir)
        except Exception as e:
            log.warning(f"  Health scorer load failed: {e}")
            self._fallback_health(models_dir)

    def _fallback_health(self, models_dir: str):
        self.health_scorer = None
        self.health_type = "rules"
        log.info("  Health scorer: Rule-based fallback")

    def _load_occasion(self, models_dir: str, model_type: str):
        try:
            if model_type == "xgb":
                import xgboost as xgb
                path = os.path.join(models_dir, "occasion_xgb.json")
                if os.path.exists(path):
                    model = xgb.XGBClassifier()
                    model.load_model(path)
                    self.occasion = model
                    self.occasion_type = "xgb"
                    log.info("  Occasion: XGBoost loaded")
                else:
                    self._fallback_occasion(models_dir)
            elif model_type == "rf":
                path = os.path.join(models_dir, "occasion_rf.joblib")
                if os.path.exists(path):
                    payload = joblib.load(path)
                    self.occasion = payload.get("model", payload)
                    self.occasion_type = "rf"
                    log.info("  Occasion: Random Forest loaded")
                else:
                    self._fallback_occasion(models_dir)
            else:
                self._fallback_occasion(models_dir)
        except Exception as e:
            log.warning(f"  Occasion load failed: {e}")
            self._fallback_occasion(models_dir)

    def _fallback_occasion(self, models_dir: str):
        path = os.path.join(models_dir, "occasion_dt.joblib")
        if os.path.exists(path):
            payload = joblib.load(path)
            self.occasion = payload.get("model", payload)
            self.occasion_type = "dt"
            log.info("  Occasion: Decision Tree fallback loaded")
        else:
            self.occasion = None
            self.occasion_type = "rules"

    def _load_reorder(self, models_dir: str, model_type: str):
        try:
            if model_type == "xgb":
                import xgboost as xgb
                path = os.path.join(models_dir, "reorder_xgb.json")
                if os.path.exists(path):
                    model = xgb.XGBClassifier()
                    model.load_model(path)
                    self.reorder = model
                    self.reorder_type = "xgb"
                    log.info("  Reorder: XGBoost loaded")
                else:
                    self._fallback_reorder(models_dir)
            elif model_type == "rf":
                path = os.path.join(models_dir, "reorder_rf.joblib")
                if os.path.exists(path):
                    payload = joblib.load(path)
                    self.reorder = payload.get("model", payload)
                    self.reorder_type = "rf"
                    log.info("  Reorder: Random Forest loaded")
                else:
                    self._fallback_reorder(models_dir)
            else:
                self._fallback_reorder(models_dir)
        except Exception as e:
            log.warning(f"  Reorder load failed: {e}")
            self._fallback_reorder(models_dir)

    def _fallback_reorder(self, models_dir: str):
        path = os.path.join(models_dir, "reorder_logistic.joblib")
        if os.path.exists(path):
            payload = joblib.load(path)
            self.reorder = payload.get("model", payload)
            self.reorder_type = "logistic"
            log.info("  Reorder: Logistic fallback loaded")
        else:
            self.reorder = None
            self.reorder_type = "rules"

    def status(self) -> dict:
        return {
            "loaded": self.loaded,
            "ranker":        {"type": self.ranker_type,      "ready": self.ranker is not None or self.ranker_type == "rules"},
            "cold_start":    {"type": self.cold_start_type,  "ready": True},
            "health_scorer": {"type": self.health_type,      "ready": True},
            "occasion":      {"type": self.occasion_type,    "ready": True},
            "reorder":       {"type": self.reorder_type,     "ready": True},
        }


# Singleton
model_store = ModelStore()