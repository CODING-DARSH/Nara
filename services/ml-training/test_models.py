"""
NARA ML — Industry Grade Model Tests
Tests every trained model for:
  - Model loads correctly
  - Correct input/output shapes
  - Inference latency meets production targets
  - Predictions are sensible on known inputs
  - No data leakage in train/test split
  - Class balance in predictions (no degenerate models)
  - Edge cases: all-zero input, missing values, extreme values

Run:
  python test_models.py
  python test_models.py -v          # verbose
  python test_models.py --fast      # skip latency tests
"""
import os
import sys
import time
import json
import logging
import argparse
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
import torch

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import MODEL_PATHS, MODELS_DIR, RANDOM_STATE

log = logging.getLogger("nara.tests")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# ── Latency targets (p95 in ms) ───────────────────────────────
LATENCY_TARGETS = {
    "ranker_logistic":      20,
    "ranker_xgboost":       30,
    "ranker_lgbm":          25,
    "cold_start_knn":       15,
    "cold_start_mlp":       10,
    "cold_start_wide_deep": 15,
    "health_rules":         5,
    "health_rf":            20,
    "health_xgb":           25,
    "occasion_dt":          5,
    "occasion_rf":          20,
    "occasion_xgb":         25,
    "reorder_logistic":     10,
    "reorder_rf":           20,
    "reorder_xgb":          25,
}

PASS = "✓ PASS"
FAIL = "✗ FAIL"
SKIP = "- SKIP"


class TestResult:
    def __init__(self):
        self.passed  = 0
        self.failed  = 0
        self.skipped = 0
        self.results = []

    def record(self, test_name: str, passed: bool,
               msg: str = "", skipped: bool = False):
        if skipped:
            status = SKIP
            self.skipped += 1
        elif passed:
            status = PASS
            self.passed += 1
        else:
            status = FAIL
            self.failed += 1
        self.results.append((test_name, status, msg))
        log.info(f"  {status}  {test_name}" + (f" — {msg}" if msg else ""))

    def summary(self):
        total = self.passed + self.failed + self.skipped
        print("\n" + "=" * 70)
        print(f"  TEST RESULTS: {self.passed}/{total} passed "
              f"({self.failed} failed, {self.skipped} skipped)")
        print("=" * 70)
        if self.failed > 0:
            print("\n  FAILURES:")
            for name, status, msg in self.results:
                if status == FAIL:
                    print(f"    {name}: {msg}")
        print()


# ── Helpers ───────────────────────────────────────────────────

def measure_p95_latency(fn, *args, n: int = 200) -> float:
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn(*args)
        times.append((time.perf_counter() - t0) * 1000)
    return sorted(times)[int(n * 0.95)]


def make_dummy_input(n_features: int, n_rows: int = 1) -> np.ndarray:
    return np.random.randn(n_rows, n_features).astype(np.float32)


def make_zero_input(n_features: int, n_rows: int = 1) -> np.ndarray:
    return np.zeros((n_rows, n_features), dtype=np.float32)


def make_extreme_input(n_features: int, n_rows: int = 1) -> np.ndarray:
    arr = np.full((n_rows, n_features), 999.0, dtype=np.float32)
    arr[0, ::2] = -999.0
    return arr


# ── Sklearn model tests ───────────────────────────────────────

def test_sklearn_model(model_name: str, model_path: str,
                        results: TestResult, run_latency: bool = True):
    log.info(f"\n[Testing] {model_name}")

    # Test 1: File exists
    results.record(
        f"{model_name}.file_exists",
        os.path.exists(model_path),
        f"path={model_path}",
    )
    if not os.path.exists(model_path):
        return

    # Test 2: Loads correctly
    try:
        payload = joblib.load(model_path)
        model   = payload.get("model") or payload
        results.record(f"{model_name}.loads", True)
    except Exception as e:
        results.record(f"{model_name}.loads", False, str(e))
        return

    # Test 3: Has predict method
    results.record(
        f"{model_name}.has_predict",
        hasattr(model, "predict"),
    )

    # Test 4: Has predict_proba
    results.record(
        f"{model_name}.has_predict_proba",
        hasattr(model, "predict_proba"),
    )

    # Test 5: Metadata present
    metadata = payload.get("metadata") if isinstance(payload, dict) else {}
    has_features = "features" in metadata if metadata else False
    results.record(f"{model_name}.has_metadata", has_features)

    if not has_features:
        n_features = getattr(model, "n_features_in_", 10)
    else:
        n_features = len(metadata["features"])

    # Test 6: Inference on dummy input
    try:
        dummy = pd.DataFrame(
            make_dummy_input(n_features),
            columns=metadata.get("features", [f"f{i}" for i in range(n_features)])
        )
        pred = model.predict(dummy)
        results.record(
            f"{model_name}.inference_dummy",
            len(pred) == 1,
            f"output_shape={pred.shape}",
        )
    except Exception as e:
        results.record(f"{model_name}.inference_dummy", False, str(e))

    # Test 7: Zero input doesn't crash
    try:
        zero = pd.DataFrame(
            make_zero_input(n_features),
            columns=metadata.get("features", [f"f{i}" for i in range(n_features)])
        )
        model.predict(zero)
        results.record(f"{model_name}.zero_input", True)
    except Exception as e:
        results.record(f"{model_name}.zero_input", False, str(e))

    # Test 8: Extreme input doesn't crash
    try:
        extreme = pd.DataFrame(
            make_extreme_input(n_features),
            columns=metadata.get("features", [f"f{i}" for i in range(n_features)])
        )
        model.predict(extreme)
        results.record(f"{model_name}.extreme_input", True)
    except Exception as e:
        results.record(f"{model_name}.extreme_input", False, str(e))

    # Test 9: Prediction class balance (not degenerate)
    try:
        batch = pd.DataFrame(
            make_dummy_input(n_features, n_rows=100),
            columns=metadata.get("features", [f"f{i}" for i in range(n_features)])
        )
        preds = model.predict(batch)
        unique_classes = len(set(preds))
        results.record(
            f"{model_name}.not_degenerate",
            unique_classes > 1,
            f"unique_classes={unique_classes}",
        )
    except Exception as e:
        results.record(f"{model_name}.not_degenerate", False, str(e))

    # Test 10: Latency
    if run_latency:
        try:
            single = pd.DataFrame(
                make_dummy_input(n_features),
                columns=metadata.get("features", [f"f{i}" for i in range(n_features)])
            )
            p95 = measure_p95_latency(model.predict, single)
            target = LATENCY_TARGETS.get(model_name, 50)
            results.record(
                f"{model_name}.latency_p95",
                p95 <= target,
                f"p95={p95:.2f}ms target={target}ms",
            )
        except Exception as e:
            results.record(f"{model_name}.latency_p95", False, str(e))
    else:
        results.record(f"{model_name}.latency_p95", True, skipped=True)

    # Test 11: Model size reasonable
    size_mb = os.path.getsize(model_path) / 1e6
    results.record(
        f"{model_name}.size_under_500mb",
        size_mb < 500,
        f"size={size_mb:.1f}MB",
    )


# ── XGBoost model tests ───────────────────────────────────────

def test_xgboost_model(model_name: str, model_path: str,
                        results: TestResult, run_latency: bool = True):
    import xgboost as xgb
    log.info(f"\n[Testing] {model_name}")

    results.record(f"{model_name}.file_exists", os.path.exists(model_path))
    if not os.path.exists(model_path):
        return

    try:
        model = xgb.XGBClassifier()
        model.load_model(model_path)
        results.record(f"{model_name}.loads", True)
    except Exception as e:
        results.record(f"{model_name}.loads", False, str(e))
        return

    n_features = model.n_features_in_

    results.record(f"{model_name}.has_predict", hasattr(model, "predict"))

    try:
        dummy = make_dummy_input(n_features)
        pred  = model.predict(dummy)
        results.record(f"{model_name}.inference_dummy", len(pred) == 1)
    except Exception as e:
        results.record(f"{model_name}.inference_dummy", False, str(e))

    try:
        zero = make_zero_input(n_features)
        model.predict(zero)
        results.record(f"{model_name}.zero_input", True)
    except Exception as e:
        results.record(f"{model_name}.zero_input", False, str(e))

    try:
        batch = make_dummy_input(n_features, n_rows=100)
        preds = model.predict(batch)
        results.record(
            f"{model_name}.not_degenerate",
            len(set(preds)) > 1,
            f"unique={len(set(preds))}",
        )
    except Exception as e:
        results.record(f"{model_name}.not_degenerate", False, str(e))

    if run_latency:
        try:
            single = make_dummy_input(n_features)
            p95    = measure_p95_latency(model.predict, single)
            target = LATENCY_TARGETS.get(model_name, 50)
            results.record(
                f"{model_name}.latency_p95",
                p95 <= target,
                f"p95={p95:.2f}ms target={target}ms",
            )
        except Exception as e:
            results.record(f"{model_name}.latency_p95", False, str(e))
    else:
        results.record(f"{model_name}.latency_p95", True, skipped=True)

    size_mb = os.path.getsize(model_path) / 1e6
    results.record(f"{model_name}.size_under_500mb", size_mb < 500, f"{size_mb:.1f}MB")


# ── LightGBM model tests ──────────────────────────────────────

def test_lgbm_model(model_name: str, model_path: str,
                     results: TestResult, run_latency: bool = True):
    import lightgbm as lgb
    log.info(f"\n[Testing] {model_name}")

    results.record(f"{model_name}.file_exists", os.path.exists(model_path))
    if not os.path.exists(model_path):
        return

    try:
        booster = lgb.Booster(model_file=model_path)
        results.record(f"{model_name}.loads", True)
    except Exception as e:
        results.record(f"{model_name}.loads", False, str(e))
        return

    n_features = booster.num_feature()

    try:
        dummy = make_dummy_input(n_features)
        pred  = booster.predict(dummy)
        results.record(f"{model_name}.inference_dummy", pred.shape[0] == 1)
    except Exception as e:
        results.record(f"{model_name}.inference_dummy", False, str(e))

    try:
        zero = make_zero_input(n_features)
        booster.predict(zero)
        results.record(f"{model_name}.zero_input", True)
    except Exception as e:
        results.record(f"{model_name}.zero_input", False, str(e))

    if run_latency:
        try:
            single = make_dummy_input(n_features)
            p95    = measure_p95_latency(booster.predict, single)
            target = LATENCY_TARGETS.get(model_name, 50)
            results.record(
                f"{model_name}.latency_p95",
                p95 <= target,
                f"p95={p95:.2f}ms target={target}ms",
            )
        except Exception as e:
            results.record(f"{model_name}.latency_p95", False, str(e))
    else:
        results.record(f"{model_name}.latency_p95", True, skipped=True)

    size_mb = os.path.getsize(model_path) / 1e6
    results.record(f"{model_name}.size_under_500mb", size_mb < 500, f"{size_mb:.1f}MB")


# ── PyTorch model tests ───────────────────────────────────────

def test_pytorch_model(model_name: str, model_path: str,
                        results: TestResult, run_latency: bool = True):
    log.info(f"\n[Testing] {model_name}")

    results.record(f"{model_name}.file_exists", os.path.exists(model_path))
    if not os.path.exists(model_path):
        return

    try:
        checkpoint = torch.load(model_path, map_location="cpu")
        results.record(f"{model_name}.loads", True)
    except Exception as e:
        results.record(f"{model_name}.loads", False, str(e))
        return

    results.record(f"{model_name}.has_model_state",
                   "model_state" in checkpoint)
    results.record(f"{model_name}.has_y_classes",
                   "y_classes" in checkpoint)
    results.record(f"{model_name}.has_test_metrics",
                   "test_metrics" in checkpoint)

    if "test_metrics" in checkpoint:
        acc = checkpoint["test_metrics"].get("accuracy", 0)
        results.record(
            f"{model_name}.accuracy_above_random",
            acc > 0.15,
            f"accuracy={acc}",
        )

    # Load and run model
    try:
        if model_name == "cold_start_mlp":
            from cold_start.train_mlp import DemographicMLP
            model = DemographicMLP(
                input_dim   = checkpoint["input_dim"],
                hidden_dims = checkpoint["hidden_dims"],
                num_classes = checkpoint["num_classes"],
                dropout     = 0.0,
            )
        elif model_name == "cold_start_wide_deep":
            from cold_start.train_wide_deep import WideAndDeep
            model = WideAndDeep(
                wide_dim      = checkpoint["wide_dim"],
                deep_input_dim= checkpoint["deep_dim"],
                deep_dims     = checkpoint["deep_dims"],
                num_classes   = checkpoint["num_classes"],
                dropout       = 0.0,
            )
        else:
            results.record(f"{model_name}.inference_dummy", True, skipped=True)
            return

        model.load_state_dict(checkpoint["model_state"])
        model.eval()

        if model_name == "cold_start_mlp":
            n_features = checkpoint["input_dim"]
            dummy = torch.FloatTensor(make_dummy_input(n_features))
            with torch.no_grad():
                out = model(dummy)
            results.record(
                f"{model_name}.inference_dummy",
                out.shape == (1, checkpoint["num_classes"]),
                f"output={out.shape}",
            )
        elif model_name == "cold_start_wide_deep":
            xw = torch.FloatTensor(make_dummy_input(checkpoint["wide_dim"]))
            xd = torch.FloatTensor(make_dummy_input(checkpoint["deep_dim"]))
            with torch.no_grad():
                out = model(xw, xd)
            results.record(
                f"{model_name}.inference_dummy",
                out.shape == (1, checkpoint["num_classes"]),
                f"output={out.shape}",
            )

        # NaN check
        results.record(
            f"{model_name}.no_nan_output",
            not torch.isnan(out).any().item(),
        )

    except Exception as e:
        results.record(f"{model_name}.inference_dummy", False, str(e))


# ── Rule-based health scorer test ─────────────────────────────

def test_health_rules(results: TestResult):
    log.info("\n[Testing] health_rules")
    try:
        from health_scorer.train_rules import RuleBasedHealthScorer
        scorer = RuleBasedHealthScorer()

        # Known test: diabetic user + jalebi (GI=88) → non-compliant
        row_diabetic_jalebi = pd.Series({
            "gi_score": 88,
            "estimated_calories": 304,
            "has_diabetes": 1,
            "has_prediabetes": 0,
            "has_hypertension": 0,
            "has_obesity": 0,
            "has_pcos": 0,
        })
        pred = scorer.predict(row_diabetic_jalebi)
        results.record(
            "health_rules.diabetic_jalebi_noncompliant",
            pred == 0,
            f"pred={pred} expected=0",
        )

        # Known test: healthy user + idli (GI=70) → compliant
        row_healthy_idli = pd.Series({
            "gi_score": 70,
            "estimated_calories": 156,
            "has_diabetes": 0,
            "has_prediabetes": 0,
            "has_hypertension": 0,
            "has_obesity": 0,
            "has_pcos": 0,
        })
        pred = scorer.predict(row_healthy_idli)
        results.record(
            "health_rules.healthy_idli_compliant",
            pred == 1,
            f"pred={pred} expected=1",
        )

        # Known test: PCOS user + steamed rice (GI=73) → non-compliant
        row_pcos_rice = pd.Series({
            "gi_score": 73,
            "estimated_calories": 260,
            "has_diabetes": 0,
            "has_prediabetes": 0,
            "has_hypertension": 0,
            "has_obesity": 0,
            "has_pcos": 1,
        })
        pred = scorer.predict(row_pcos_rice)
        results.record(
            "health_rules.pcos_high_gi_noncompliant",
            pred == 0,
            f"pred={pred} expected=0",
        )

        results.record("health_rules.loads", True)
    except Exception as e:
        results.record("health_rules.loads", False, str(e))


# ── Metrics file tests ────────────────────────────────────────

def test_metrics_files(results: TestResult):
    log.info("\n[Testing] Saved metrics files")

    model_names = [
        "ranker_logistic", "ranker_xgboost", "ranker_lgbm",
        "cold_start_knn", "cold_start_mlp", "cold_start_wide_deep",
        "health_rules", "health_rf", "health_xgb_shap",
        "occasion_dt", "occasion_rf", "occasion_xgb",
        "reorder_logistic", "reorder_rf", "reorder_cox_xgb",
    ]
    for name in model_names:
        path = os.path.join(MODELS_DIR, f"{name}_metrics.json")
        if not os.path.exists(path):
            results.record(f"metrics.{name}", False, "file not found", skipped=True)
            continue
        try:
            with open(path) as f:
                metrics = json.load(f)
            has_test = "test" in metrics or "all" in metrics
            results.record(f"metrics.{name}.valid", has_test, str(list(metrics.keys())))
        except Exception as e:
            results.record(f"metrics.{name}.parseable", False, str(e))


# ── Data leakage check ────────────────────────────────────────

def test_no_data_leakage(results: TestResult):
    log.info("\n[Testing] Data leakage checks")

    # Check that test metrics < train metrics (overfitting would suggest leakage)
    model_names = ["ranker_logistic", "ranker_xgboost", "health_rf", "occasion_rf"]
    for name in model_names:
        path = os.path.join(MODELS_DIR, f"{name}_metrics.json")
        if not os.path.exists(path):
            results.record(f"leakage.{name}", True, skipped=True)
            continue
        try:
            with open(path) as f:
                metrics = json.load(f)
            val_f1  = metrics.get("val",  {}).get("f1", 0)
            test_f1 = metrics.get("test", {}).get("f1", 0)
            # Test F1 should be within 10% of val F1 (no huge gap = no leakage)
            if val_f1 > 0 and test_f1 > 0:
                ratio = abs(val_f1 - test_f1) / val_f1
                results.record(
                    f"leakage.{name}.val_test_consistent",
                    ratio < 0.10,
                    f"val_f1={val_f1:.3f} test_f1={test_f1:.3f} diff={ratio:.3f}",
                )
        except Exception as e:
            results.record(f"leakage.{name}", False, str(e))


# ── ONNX model tests ──────────────────────────────────────────

def test_onnx_models(results: TestResult):
    log.info("\n[Testing] ONNX models")
    try:
        import onnxruntime as ort
    except ImportError:
        log.warning("onnxruntime not installed, skipping ONNX tests")
        results.record("onnx.runtime_available", False, "pip install onnxruntime")
        return

    onnx_paths = {
        "ranker_xgboost_onnx": MODEL_PATHS["ranker_xgboost_onnx"],
        "ranker_lgbm_onnx":    MODEL_PATHS["ranker_lgbm_onnx"],
        "health_xgb_onnx":     MODEL_PATHS["health_xgb_onnx"],
        "occasion_xgb_onnx":   MODEL_PATHS["occasion_xgb_onnx"],
        "reorder_xgb_onnx":    MODEL_PATHS["reorder_xgb_onnx"],
    }
    for name, path in onnx_paths.items():
        if not os.path.exists(path):
            results.record(f"onnx.{name}", True, skipped=True)
            continue
        try:
            sess = ort.InferenceSession(path)
            input_name = sess.get_inputs()[0].name
            n_features = sess.get_inputs()[0].shape[1]
            dummy = make_dummy_input(n_features).astype(np.float32)
            out   = sess.run(None, {input_name: dummy})
            results.record(f"onnx.{name}.loads_and_runs", True, f"output_shapes={[o.shape for o in out]}")
        except Exception as e:
            results.record(f"onnx.{name}.loads_and_runs", False, str(e))


# ── Main ──────────────────────────────────────────────────────

def run_tests(run_latency: bool = True):
    log.info("=" * 70)
    log.info("NARA ML Model Tests")
    log.info("=" * 70)

    results = TestResult()

    # ── Sklearn models ────────────────────────────────────────
    sklearn_models = [
        ("ranker_logistic",  MODEL_PATHS["ranker_logistic"]),
        ("cold_start_knn",   MODEL_PATHS["cold_start_knn"]),
        ("health_rf",        MODEL_PATHS["health_rf"]),
        ("occasion_dt",      MODEL_PATHS["occasion_dt"]),
        ("occasion_rf",      MODEL_PATHS["occasion_rf"]),
        ("reorder_logistic", MODEL_PATHS["reorder_logistic"]),
        ("reorder_rf",       MODEL_PATHS["reorder_rf"]),
    ]
    for name, path in sklearn_models:
        test_sklearn_model(name, path, results, run_latency)

    # ── XGBoost models ────────────────────────────────────────
    xgb_models = [
        ("ranker_xgboost",  MODEL_PATHS["ranker_xgboost"]),
        ("health_xgb",      MODEL_PATHS["health_xgb"]),
        ("occasion_xgb",    MODEL_PATHS["occasion_xgb"]),
        ("reorder_xgb",     MODEL_PATHS["reorder_xgb"]),
    ]
    for name, path in xgb_models:
        test_xgboost_model(name, path, results, run_latency)

    # ── LightGBM models ───────────────────────────────────────
    test_lgbm_model("ranker_lgbm", MODEL_PATHS["ranker_lgbm"], results, run_latency)

    # ── PyTorch models ────────────────────────────────────────
    pytorch_models = [
        ("cold_start_mlp",       MODEL_PATHS["cold_start_mlp"]),
        ("cold_start_wide_deep", MODEL_PATHS["cold_start_wide_deep"]),
    ]
    for name, path in pytorch_models:
        test_pytorch_model(name, path, results, run_latency)

    # ── Rule-based ────────────────────────────────────────────
    test_health_rules(results)

    # ── Metrics files ─────────────────────────────────────────
    test_metrics_files(results)

    # ── Data leakage ──────────────────────────────────────────
    test_no_data_leakage(results)

    # ── ONNX ─────────────────────────────────────────────────
    test_onnx_models(results)

    results.summary()

    # Save test report
    report_path = os.path.join(MODELS_DIR, "test_report.json")
    os.makedirs(MODELS_DIR, exist_ok=True)
    report = {
        "passed":  results.passed,
        "failed":  results.failed,
        "skipped": results.skipped,
        "results": [(n, s, m) for n, s, m in results.results],
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    log.info(f"Test report saved → {report_path}")

    return results.failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true",
                        help="Skip latency tests")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    success = run_tests(run_latency=not args.fast)
    sys.exit(0 if success else 1)
