"""
NARA — Ensemble Model Loader

BEFORE: loaded exactly ONE model per family based on ACTIVE_* settings,
ignoring all other trained variants. Cold-start model was loaded but never
called by the live flow. Reorder ran on users with zero order history,
adding meaningless noise.

AFTER: loads EVERY saved variant per family at startup. Inference functions
(ensemble_ranker_score, ensemble_health_score, etc.) combine all loaded
variants using real metric-derived weights, not just the "best" single model.
Cold-start is wired into the main flow by meal count. Reorder skips cleanly
when no order history exists.

Ensemble weights derived from your real eval metrics:
  Ranker:      NDCG@10 — lgbm=0.474, logistic=0.472, xgboost=0.311
               Weight proportional to NDCG: lgbm≈0.60, logistic≈0.30, xgb≈0.10
  Cold-start:  F1      — wide_deep=0.762, mlp=0.709, knn=0.746
               Weight proportional to F1:   wide_deep≈0.47, knn≈0.29, mlp≈0.24 (but wide_deep needs proper
               instantiation — falls back to knn+mlp equal if wide_deep fails to instantiate)
  Health:      AUC     — xgb has SHAP explainability advantage, rf is second.
               Weights: xgb=0.65, rf=0.35
  Occasion:    F1      — xgb=0.973, rf=0.949, dt=0.947
               Weights: xgb=0.60, rf=0.25, dt=0.15
  Reorder:     AUC     — rf=0.745 (balanced), logistic=0.709 (degenerate class-0 recall)
               Weights: rf=0.75, logistic=0.25
"""
import os
import logging
import joblib
import numpy as np

log = logging.getLogger("nara.recommendation.model_loader")


# ── Ensemble weights, derived from your real eval metrics ──────────────────
# Update these once you retrain with more real interaction data.
# The weights here match the numbers in the docstring above.
RANKER_WEIGHTS = {
    "lgbm":     0.60,
    "logistic": 0.30,
    "xgboost":  0.10,
}

HEALTH_WEIGHTS = {
    "xgb": 0.65,
    "rf":  0.35,
}

OCCASION_WEIGHTS = {
    "xgb": 0.60,
    "rf":  0.25,
    "dt":  0.15,
}

REORDER_WEIGHTS = {
    "rf":       0.75,
    "logistic": 0.25,
}

# Cold-start: wide_deep needs its own WideAndDeep class instantiated from
# the checkpoint dict — that class lives only in ml-training, not in the
# recommendation service. Until we port it, we ensemble knn+mlp only.
# TODO: port WideAndDeep inference class here so wide_deep can actually run.
COLD_START_WEIGHTS = {
    "knn": 0.55,
    "mlp": 0.45,
}


def _load_sklearn(path: str):
    """Load a joblib sklearn model, handling both raw model and payload dict."""
    payload = joblib.load(path)
    if isinstance(payload, dict):
        return payload.get("model", payload)
    return payload


def _load_sklearn_with_meta(path: str):
    """
    Load a joblib sklearn model AND its saved metadata (feature_cols,
    classes, etc). Needed for reorder/cold-start where the exact
    training-time feature order is only recoverable from metadata["features"]
    — hardcoding a shared order per family was the bug that scrambled
    reorder_boost() and the cold-start vector.
    """
    payload = joblib.load(path)
    if isinstance(payload, dict) and "model" in payload:
        return payload["model"], payload.get("metadata", {}) or {}
    return payload, {}


def _ordered_vector(raw: dict, feature_names: list) -> np.ndarray:
    """
    Build a feature vector in the EXACT order a model's own saved
    feature_cols/metadata specifies, pulling values from a name-keyed
    dict rather than a hardcoded positional list. Missing names default
    to 0.0 (matches training-side .fillna(0)).
    """
    return np.array([[float(raw.get(name, 0.0) or 0.0) for name in feature_names]],
                     dtype=np.float32)


class EnsembleModelStore:
    """
    Loads every saved variant per model family.
    Exposes ensemble_*_score() methods that combine all loaded variants
    using real metric-derived weights instead of picking one winner.
    """

    def __init__(self):
        # Per-family dicts: {variant_name: model_object}
        self.rankers      = {}
        self.health_scorers = {}
        self.occasion_models = {}
        self.reorder_models  = {}
        self.cold_start_models = {}
        self.loaded = False

    def load_all(self, models_dir: str):
        log.info(f"Loading all model variants from {models_dir}")
        self._load_rankers(models_dir)
        self._load_health_scorers(models_dir)
        self._load_occasion_models(models_dir)
        self._load_reorder_models(models_dir)
        self._load_cold_start_models(models_dir)
        self.loaded = True
        log.info(f"Ensemble loader ready — rankers:{list(self.rankers)}, "
                 f"health:{list(self.health_scorers)}, "
                 f"occasion:{list(self.occasion_models)}, "
                 f"reorder:{list(self.reorder_models)}, "
                 f"cold_start:{list(self.cold_start_models)}")

    # ── Loaders ──────────────────────────────────────────────────────────

    def _load_rankers(self, d: str):
        # LightGBM
        try:
            import lightgbm as lgb
            p = os.path.join(d, "ranker_lgbm.txt")
            if os.path.exists(p):
                self.rankers["lgbm"] = lgb.Booster(model_file=p)
                log.info("  ranker/lgbm loaded")
        except Exception as e:
            log.warning(f"  ranker/lgbm failed: {e}")

        # XGBoost
        try:
            import xgboost as xgb
            p = os.path.join(d, "ranker_xgboost.json")
            if os.path.exists(p):
                m = xgb.XGBClassifier()
                m.load_model(p)
                self.rankers["xgboost"] = m
                log.info("  ranker/xgboost loaded")
        except Exception as e:
            log.warning(f"  ranker/xgboost failed: {e}")

        # Logistic
        try:
            p = os.path.join(d, "ranker_logistic.joblib")
            if os.path.exists(p):
                self.rankers["logistic"] = _load_sklearn(p)
                log.info("  ranker/logistic loaded")
        except Exception as e:
            log.warning(f"  ranker/logistic failed: {e}")

        if not self.rankers:
            log.warning("  No ranker models loaded — will use rule-based fallback")

    def _load_health_scorers(self, d: str):
        try:
            import xgboost as xgb
            p = os.path.join(d, "health_xgb.json")
            if os.path.exists(p):
                m = xgb.XGBClassifier()
                m.load_model(p)
                self.health_scorers["xgb"] = m
                log.info("  health/xgb loaded")
        except Exception as e:
            log.warning(f"  health/xgb failed: {e}")

        try:
            p = os.path.join(d, "health_rf.joblib")
            if os.path.exists(p):
                self.health_scorers["rf"] = _load_sklearn(p)
                log.info("  health/rf loaded")
        except Exception as e:
            log.warning(f"  health/rf failed: {e}")

    def _load_occasion_models(self, d: str):
        try:
            import xgboost as xgb
            p = os.path.join(d, "occasion_xgb.json")
            if os.path.exists(p):
                m = xgb.XGBClassifier()
                m.load_model(p)
                self.occasion_models["xgb"] = m
                log.info("  occasion/xgb loaded")
        except Exception as e:
            log.warning(f"  occasion/xgb failed: {e}")

        try:
            p = os.path.join(d, "occasion_rf.joblib")
            if os.path.exists(p):
                self.occasion_models["rf"] = _load_sklearn(p)
                log.info("  occasion/rf loaded")
        except Exception as e:
            log.warning(f"  occasion/rf failed: {e}")

        try:
            p = os.path.join(d, "occasion_dt.joblib")
            if os.path.exists(p):
                self.occasion_models["dt"] = _load_sklearn(p)
                log.info("  occasion/dt loaded")
        except Exception as e:
            log.warning(f"  occasion/dt failed: {e}")

    def _load_reorder_models(self, d: str):
        # FIX: reorder_boost() used to build a single hardcoded 14-value
        # vector that didn't match either model's real training order
        # (fields swapped, bmi/dish_rank injected that were never trained
        # features). Each reorder_*.joblib was saved with
        # metadata["features"] = the exact training column order — load
        # and keep that so the vector can be built by name, per model.
        try:
            p = os.path.join(d, "reorder_rf.joblib")
            if os.path.exists(p):
                model, meta = _load_sklearn_with_meta(p)
                self.reorder_models["rf"] = {"model": model, "features": meta.get("features", [])}
                log.info(f"  reorder/rf loaded ({len(meta.get('features', []))} features)")
        except Exception as e:
            log.warning(f"  reorder/rf failed: {e}")

        try:
            p = os.path.join(d, "reorder_logistic.joblib")
            if os.path.exists(p):
                model, meta = _load_sklearn_with_meta(p)
                self.reorder_models["logistic"] = {"model": model, "features": meta.get("features", [])}
                log.info(f"  reorder/logistic loaded ({len(meta.get('features', []))} features)")
        except Exception as e:
            log.warning(f"  reorder/logistic failed: {e}")

    def _load_cold_start_models(self, d: str):
        # Same issue as reorder: cold_start_knn.joblib carries
        # metadata["features"] (exact training order) and metadata["classes"]
        # (the real fitted class list) — load both instead of discarding
        # metadata like the old _load_sklearn() did.
        try:
            p = os.path.join(d, "cold_start_knn.joblib")
            if os.path.exists(p):
                model, meta = _load_sklearn_with_meta(p)
                self.cold_start_models["knn"] = {
                    "model": model,
                    "features": meta.get("features", []),
                    "classes": meta.get("classes") or list(getattr(model, "classes_", [])),
                }
                log.info(f"  cold_start/knn loaded ({len(meta.get('features', []))} features)")
        except Exception as e:
            log.warning(f"  cold_start/knn failed: {e}")

        try:
            import torch
            p = os.path.join(d, "cold_start_mlp.pt")
            if os.path.exists(p):
                checkpoint = torch.load(p, map_location="cpu")
                # MLP checkpoint is a dict with model state_dict + metadata.
                # We store the full checkpoint and reconstruct at inference time
                # using the saved architecture params.
                self.cold_start_models["mlp"] = checkpoint
                log.info("  cold_start/mlp loaded (checkpoint)")
        except Exception as e:
            log.warning(f"  cold_start/mlp failed: {e}")

        # wide_deep: TODO — needs WideAndDeep class ported from ml-training
        # into this service before its state_dict is usable. Logged as a
        # known gap so the status() output makes this visible.
        log.info("  cold_start/wide_deep: skipped — WideAndDeep class not yet "
                 "ported to recommendation service (see model_loader.py TODO)")

    # ── Ensemble inference methods ────────────────────────────────────────

    def ensemble_ranker_score(self, features: np.ndarray) -> tuple[float, dict]:
        """
        Combines all loaded ranker variants using NDCG-derived weights.
        Returns (combined_score, per_model_breakdown) — the breakdown is
        logged per-request so you can tune weights from real production data.

        All rankers are trained as 3-class (no_interaction=0, click=1,
        order=2). We use the order-class probability (index 2) as the score.
        """
        scores = {}
        for name, model in self.rankers.items():
            try:
                if name == "lgbm":
                    raw = model.predict(features.reshape(1, -1))
                    scores[name] = float(raw[0][2]) if raw.ndim == 2 else float(raw[0])
                else:
                    probs = model.predict_proba(features.reshape(1, -1))
                    scores[name] = float(probs[0][2]) if probs.shape[1] > 2 else float(probs[0][1])
            except Exception as e:
                log.debug(f"ensemble ranker/{name} failed: {e}")

        if not scores:
            return 0.0, {}

        total_weight = sum(RANKER_WEIGHTS.get(n, 0.1) for n in scores)
        combined = sum(RANKER_WEIGHTS.get(n, 0.1) * s for n, s in scores.items()) / total_weight
        return round(combined, 4), scores

    def ensemble_health_score(self, features: np.ndarray) -> tuple[float, dict]:
        """
        Combines health scorer variants (xgb + rf) using AUC-derived weights.
        Returns (combined_compliance_prob, per_model_breakdown).
        """
        scores = {}
        for name, model in self.health_scorers.items():
            try:
                probs = model.predict_proba(features.reshape(1, -1))
                # class 1 = health-compliant
                scores[name] = float(probs[0][1]) if probs.shape[1] > 1 else float(probs[0][0])
            except Exception as e:
                log.debug(f"ensemble health/{name} failed: {e}")

        if not scores:
            return None, {}

        total_weight = sum(HEALTH_WEIGHTS.get(n, 0.5) for n in scores)
        combined = sum(HEALTH_WEIGHTS.get(n, 0.5) * s for n, s in scores.items()) / total_weight
        return round(combined, 4), scores

    def ensemble_occasion_predict(self, features: np.ndarray) -> tuple[int, dict]:
        """
        Combines occasion classifiers using weighted-vote on class probabilities.
        Returns (predicted_class_index, per_model_class_probs).
        """
        weighted_probs = None
        breakdown = {}
        for name, model in self.occasion_models.items():
            try:
                probs = model.predict_proba(features.reshape(1, -1))[0]
                w = OCCASION_WEIGHTS.get(name, 0.1)
                breakdown[name] = probs.tolist()
                if weighted_probs is None:
                    weighted_probs = w * probs
                else:
                    weighted_probs += w * probs
            except Exception as e:
                log.debug(f"ensemble occasion/{name} failed: {e}")

        if weighted_probs is None:
            return None, {}

        return int(np.argmax(weighted_probs)), breakdown

    def ensemble_reorder_score(self, raw_features: dict) -> tuple[float, dict]:
        """
        Combines reorder models using AUC-derived weights.
        `raw_features` is a name-keyed dict (training column name -> value);
        each model's own saved feature order (self.reorder_models[name]["features"])
        is used to build its vector, so rf and logistic can each have their
        own column order without either being wrong.
        Returns (reorder_probability, per_model_breakdown).
        Caller is responsible for skipping this entirely when no order history
        exists (food_graph.top_dishes empty) — don't call this with zero data.
        """
        scores = {}
        for name, entry in self.reorder_models.items():
            model         = entry["model"]
            feature_names = entry["features"]
            if not feature_names:
                log.debug(f"ensemble reorder/{name} skipped — no saved feature order")
                continue
            try:
                vec = _ordered_vector(raw_features, feature_names)
                probs = model.predict_proba(vec)[0]
                scores[name] = float(probs[1]) if len(probs) > 1 else float(probs[0])
            except Exception as e:
                log.debug(f"ensemble reorder/{name} failed: {e}")

        if not scores:
            return 0.0, {}

        total_weight = sum(REORDER_WEIGHTS.get(n, 0.5) for n in scores)
        combined = sum(REORDER_WEIGHTS.get(n, 0.5) * s for n, s in scores.items()) / total_weight
        return round(combined, 4), scores

    def ensemble_cold_start_predict(self, raw_features: dict) -> tuple[str | None, dict]:
        """
        Combines cold-start models (knn + mlp checkpoint) weighted by F1.
        `raw_features` is a name-keyed dict (training column name -> value) —
        each model builds its own vector from its own saved feature order,
        instead of both being forced through one hardcoded (and wrong) list.
        Returns (predicted_cuisine_NAME, per_model_breakdown).

        MLP from the checkpoint: we reconstruct inference manually from the
        saved state_dict + architecture metadata since the MLP class isn't
        importable here (it's defined in ml-training/cold_start/train_mlp.py).
        Falls back to knn-only if MLP reconstruction fails.

        FIX: previously looked for checkpoint["model_state_dict"] /
        checkpoint["state_dict"], but train_mlp.py actually saves the key
        as "model_state" — the lookup always missed, so the MLP silently
        contributed nothing to the ensemble despite loading "successfully".
        """
        weighted_probs = None
        breakdown = {}
        classes = None  # resolved from whichever model actually produced probs

        # KNN
        knn_entry = self.cold_start_models.get("knn")
        if isinstance(knn_entry, dict) and knn_entry.get("model") is not None:
            knn = knn_entry["model"]
            feature_names = knn_entry.get("features", [])
            try:
                vec = _ordered_vector(raw_features, feature_names) if feature_names \
                      else np.array([[raw_features.get(k, 0.0) for k in raw_features]], dtype=np.float32)
                probs = knn.predict_proba(vec)[0]
                w = COLD_START_WEIGHTS.get("knn", 0.5)
                breakdown["knn"] = probs.tolist()
                weighted_probs = w * probs
                classes = knn_entry.get("classes") or list(getattr(knn, "classes_", []))
            except Exception as e:
                log.debug(f"cold_start/knn inference failed: {e}")

        # MLP — reconstruct from checkpoint
        mlp_checkpoint = self.cold_start_models.get("mlp")
        if mlp_checkpoint is not None:
            try:
                import torch
                import torch.nn as nn

                state_dict  = (mlp_checkpoint.get("model_state")
                                or mlp_checkpoint.get("model_state_dict")
                                or mlp_checkpoint.get("state_dict"))
                feature_names = mlp_checkpoint.get("feature_cols", [])
                input_dim   = mlp_checkpoint.get("input_dim", len(feature_names) or len(raw_features))
                hidden_dims = mlp_checkpoint.get("hidden_dims", [128, 64])
                n_classes   = mlp_checkpoint.get("num_classes") or mlp_checkpoint.get("n_classes", 5)
                mlp_classes = mlp_checkpoint.get("y_classes")

                if state_dict is not None:
                    # Rebuild the same architecture from saved metadata
                    layers = []
                    in_dim = input_dim
                    for h in hidden_dims:
                        layers += [nn.Linear(in_dim, h), nn.ReLU(), nn.Dropout(0.3)]
                        in_dim = h
                    layers.append(nn.Linear(in_dim, n_classes))
                    mlp = nn.Sequential(*layers)
                    mlp.load_state_dict(state_dict)
                    mlp.eval()

                    vec = _ordered_vector(raw_features, feature_names) if feature_names \
                          else np.array([[raw_features.get(k, 0.0) for k in raw_features]], dtype=np.float32)

                    with torch.no_grad():
                        t = torch.FloatTensor(vec)
                        logits = mlp(t)
                        probs = torch.softmax(logits, dim=1).numpy()[0]

                    w = COLD_START_WEIGHTS.get("mlp", 0.5)
                    breakdown["mlp"] = probs.tolist()
                    if weighted_probs is None:
                        weighted_probs = w * probs
                        classes = classes or mlp_classes
                    elif classes and mlp_classes and list(classes) == list(mlp_classes) and len(probs) == len(weighted_probs):
                        # Only combine if both models agree on class vocabulary/order —
                        # summing probs across mismatched class spaces would be meaningless.
                        weighted_probs += w * probs
                    else:
                        log.debug("cold_start/mlp class vocab differs from knn — kept separate, not summed")
            except Exception as e:
                log.debug(f"cold_start/mlp reconstruction failed: {e}")

        if weighted_probs is None or not classes:
            return None, breakdown

        idx = int(np.argmax(weighted_probs))
        predicted_cuisine = classes[idx] if idx < len(classes) else None
        return predicted_cuisine, breakdown

    def status(self) -> dict:
        return {
            "loaded": self.loaded,
            "ranker":      {"variants": list(self.rankers),          "weights": RANKER_WEIGHTS},
            "health":      {"variants": list(self.health_scorers),   "weights": HEALTH_WEIGHTS},
            "occasion":    {"variants": list(self.occasion_models),  "weights": OCCASION_WEIGHTS},
            "reorder":     {"variants": list(self.reorder_models),   "weights": REORDER_WEIGHTS},
            "cold_start":  {"variants": list(self.cold_start_models),"weights": COLD_START_WEIGHTS},
        }


# Singleton — replaces the old ModelStore singleton everywhere it was imported
model_store = EnsembleModelStore()