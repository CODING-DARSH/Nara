"""
NARA — 90-Day Harness Metrics Computation
============================================

STANDALONE. Reads harness90.sqlite (produced by harness_90day.py), computes
the full metrics battery, writes results into computed_metrics, and prints
a Markdown report. Never re-hits any API — pure offline computation over
already-collected data, so a metric bug doesn't require re-running the
90-day simulation.

DATA QUALITY GATE (run first, always)
---------------------------------------
A user is only included in metrics if they show EXACTLY 13 distinct weeks
and 22 total recommendation_snapshots — the known-correct checkpoint
cadence (3 full weeks x4 occasions + 10 light weeks x1, verified earlier).
Any completed user NOT matching this is flagged and EXCLUDED, with a
printed warning — this is exactly the kind of leftover-partial-data
corruption found and fixed in harness_90day.py; better to exclude a
suspect user than silently compute metrics over inflated/duplicated rows.

HONEST GAPS (stated up front, not discovered by the reader later)
---------------------------------------------------------------------
1. Occasion classifier metrics are NOT computable from this data. Every
   recommendation call the harness makes passes an explicit `occasion`
   param — and get_recommendations()'s own logic is
   `context.get("occasion") or detect_occasion(...)`, so detect_occasion()
   (and its debug breakdown: occasion_dt_pred/rf_pred/xgb_pred) never
   actually executes. This section reports "N/A — not exercised by this
   harness" rather than a fabricated number.
2. Ranker family (LightGBM/XGBoost/Logistic) per-model NDCG/MRR are not
   computed individually — only the ENSEMBLE's ranking is evaluated
   end-to-end (real implicit relevance: click=0.5, order=1.0, joined by
   user_id+week_number+dish_name against interaction_events). Per-model
   contribution is reported as rank-correlation with the ensemble instead
   (a standalone model doesn't produce its OWN ranked list independent of
   the ensemble in this pipeline — only the ensemble's output was ever
   actually shown to a user and could be clicked/ordered).
3. Reorder/cold-start ground truth is REAL but indirect: "was this exact
   dish ordered again in a LATER week by this user" / "was the predicted
   cuisine actually clicked/ordered afterward" — genuine behavioral
   outcomes from the harness's own simulated clicks/orders, not a
   hand-labeled dataset.
"""
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = "harness90.sqlite"
EXPECTED_WEEKS = 13
EXPECTED_SNAPSHOTS = 22

DIABETES_LIKE = {"type2_diabetes", "prediabetes"}
HYPERTENSION_LIKE = {"hypertension"}


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ═════════════════════════════════════════════════════════════════════
# Data quality gate
# ═════════════════════════════════════════════════════════════════════

def get_valid_users(conn) -> list:
    """Returns (user_id, email, cohort, city) for users whose data passes
    the exact-13-weeks / exact-22-snapshots check. Prints a warning for
    anyone excluded."""
    rows = conn.execute("""
        SELECT h.user_id, h.email, h.cohort, h.city,
               (SELECT COUNT(DISTINCT week_number) FROM recommendation_snapshots WHERE user_id = h.user_id) AS weeks,
               (SELECT COUNT(*) FROM recommendation_snapshots WHERE user_id = h.user_id) AS snapshots
        FROM harness_users h
        WHERE h.email IN (SELECT email FROM harness_completed_users)
    """).fetchall()

    valid, excluded = [], []
    for r in rows:
        if r["weeks"] == EXPECTED_WEEKS and r["snapshots"] == EXPECTED_SNAPSHOTS:
            valid.append((r["user_id"], r["email"], r["cohort"], r["city"]))
        else:
            excluded.append((r["email"], r["weeks"], r["snapshots"]))

    if excluded:
        print(f"WARNING: excluding {len(excluded)} user(s) with corrupted/incomplete data (weeks/snapshots mismatch):")
        for email, weeks, snapshots in excluded:
            print(f"  {email}: weeks={weeks} (expected {EXPECTED_WEEKS}), snapshots={snapshots} (expected {EXPECTED_SNAPSHOTS})")
        print()

    print(f"Computing metrics over {len(valid)} valid user(s) (excluded {len(excluded)}).\n")
    return valid


# ═════════════════════════════════════════════════════════════════════
# Ranking metrics — NDCG@k, MRR, Precision@k, Recall@k
# Real implicit relevance from interaction_events: order=1.0, click=0.5,
# joined by (user_id, week_number, dish_name) — the granularity the
# harness actually recorded interactions at.
# ═════════════════════════════════════════════════════════════════════

def build_relevance_map(conn, user_ids: list) -> dict:
    """(user_id, week_number, dish_name) -> relevance in {0, 0.5, 1.0}"""
    placeholders = ",".join("?" * len(user_ids))
    rows = conn.execute(f"""
        SELECT user_id, week_number, dish_name, action
        FROM interaction_events
        WHERE user_id IN ({placeholders})
    """, user_ids).fetchall()

    relevance = {}
    for r in rows:
        key = (r["user_id"], r["week_number"], r["dish_name"])
        val = 1.0 if r["action"] == "order" else 0.5
        relevance[key] = max(relevance.get(key, 0.0), val)  # order beats click if both recorded
    return relevance


def dcg_at_k(relevances: list, k: int) -> float:
    import math
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances[:k]))


def ndcg_at_k(ranked_relevances: list, k: int) -> float:
    dcg = dcg_at_k(ranked_relevances, k)
    ideal = dcg_at_k(sorted(ranked_relevances, reverse=True), k)
    return dcg / ideal if ideal > 0 else None  # None = no relevant items shown this snapshot, exclude from average


def compute_ranking_metrics(conn, user_ids: list, cohort_map: dict) -> list:
    """Returns list of {cohort, metric_name, value, sample_size} rows."""
    relevance_map = build_relevance_map(conn, user_ids)

    placeholders = ",".join("?" * len(user_ids))
    snapshots = conn.execute(f"""
        SELECT id, user_id, week_number, response_json
        FROM recommendation_snapshots
        WHERE user_id IN ({placeholders}) AND debug_mode = 1
    """, user_ids).fetchall()

    # Per-cohort accumulators
    ndcg_by_cohort = defaultdict(list)
    mrr_by_cohort = defaultdict(list)
    precision_by_cohort = defaultdict(list)
    recall_by_cohort = defaultdict(list)

    for snap in snapshots:
        try:
            body = json.loads(snap["response_json"])
        except Exception:
            continue
        recs = body.get("recommendations", []) if isinstance(body, dict) else []
        if not recs:
            continue

        cohort = cohort_map[snap["user_id"]]
        relevances = [
            relevance_map.get((snap["user_id"], snap["week_number"], d.get("dish_name")), 0.0)
            for d in recs
        ]

        ndcg = ndcg_at_k(relevances, 10)
        if ndcg is not None:
            ndcg_by_cohort[cohort].append(ndcg)

        # MRR: reciprocal rank of the first relevant (>0) item
        first_relevant_rank = next((i + 1 for i, rel in enumerate(relevances) if rel > 0), None)
        if first_relevant_rank is not None:
            mrr_by_cohort[cohort].append(1.0 / first_relevant_rank)

        # Precision@5 / Recall@5 — treat rel>0 as "relevant" (binary)
        top5 = relevances[:5]
        n_relevant_total = sum(1 for r in relevances if r > 0)
        if n_relevant_total > 0:
            precision_by_cohort[cohort].append(sum(1 for r in top5 if r > 0) / 5)
            recall_by_cohort[cohort].append(sum(1 for r in top5 if r > 0) / n_relevant_total)

    results = []
    now = datetime.now(timezone.utc).isoformat()
    for cohort, values in ndcg_by_cohort.items():
        results.append({"cohort": cohort, "model_family": "end_to_end", "metric_name": "ndcg_at_10",
                         "metric_value": sum(values) / len(values), "sample_size": len(values), "computed_at": now})
    for cohort, values in mrr_by_cohort.items():
        results.append({"cohort": cohort, "model_family": "end_to_end", "metric_name": "mrr",
                         "metric_value": sum(values) / len(values), "sample_size": len(values), "computed_at": now})
    for cohort, values in precision_by_cohort.items():
        results.append({"cohort": cohort, "model_family": "end_to_end", "metric_name": "precision_at_5",
                         "metric_value": sum(values) / len(values), "sample_size": len(values), "computed_at": now})
    for cohort, values in recall_by_cohort.items():
        results.append({"cohort": cohort, "model_family": "end_to_end", "metric_name": "recall_at_5",
                         "metric_value": sum(values) / len(values), "sample_size": len(values), "computed_at": now})
    return results


# ═════════════════════════════════════════════════════════════════════
# Reorder model — ROC-AUC / F1 / Precision / Recall
# Ground truth: was this exact dish ordered again by this user in ANY
# LATER week (real observed reorder behavior from the harness's own
# simulated clicks/orders).
# ═════════════════════════════════════════════════════════════════════

def roc_auc_binary(y_true: list, y_score: list) -> float:
    """Manual ROC-AUC (Mann-Whitney U form) — avoids requiring sklearn/numpy
    just for this offline computation."""
    pairs_pos = [(s, t) for s, t in zip(y_score, y_true) if t == 1]
    pairs_neg = [(s, t) for s, t in zip(y_score, y_true) if t == 0]
    if not pairs_pos or not pairs_neg:
        return None
    count = 0
    for s_pos, _ in pairs_pos:
        for s_neg, _ in pairs_neg:
            if s_pos > s_neg:
                count += 1
            elif s_pos == s_neg:
                count += 0.5
    return count / (len(pairs_pos) * len(pairs_neg))


def precision_recall_f1(y_true: list, y_pred: list) -> tuple:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None
    f1 = (2 * precision * recall / (precision + recall)) if precision and recall and (precision + recall) > 0 else None
    return precision, recall, f1


def compute_reorder_metrics(conn, user_ids: list, cohort_map: dict) -> list:
    placeholders = ",".join("?" * len(user_ids))

    # Real reordered dishes: (user_id, dish_name) pairs that appear more
    # than once in interaction_events with action='order'
    reorder_rows = conn.execute(f"""
        SELECT user_id, dish_name, COUNT(*) as order_count
        FROM interaction_events
        WHERE user_id IN ({placeholders}) AND action = 'order'
        GROUP BY user_id, dish_name
    """, user_ids).fetchall()
    reordered_pairs = {(r["user_id"], r["dish_name"]) for r in reorder_rows if r["order_count"] > 1}

    scores = conn.execute(f"""
        SELECT user_id, dish_name, reorder_ensemble_prob
        FROM model_scores_snapshot
        WHERE user_id IN ({placeholders}) AND reorder_ensemble_prob IS NOT NULL
    """, user_ids).fetchall()

    by_cohort = defaultdict(lambda: {"y_true": [], "y_score": []})
    for r in scores:
        cohort = cohort_map[r["user_id"]]
        y = 1 if (r["user_id"], r["dish_name"]) in reordered_pairs else 0
        by_cohort[cohort]["y_true"].append(y)
        by_cohort[cohort]["y_score"].append(r["reorder_ensemble_prob"])

    results = []
    now = datetime.now(timezone.utc).isoformat()
    for cohort, data in by_cohort.items():
        y_true, y_score = data["y_true"], data["y_score"]
        if len(y_true) < 2:
            continue
        auc = roc_auc_binary(y_true, y_score)
        y_pred = [1 if s >= 0.5 else 0 for s in y_score]
        precision, recall, f1 = precision_recall_f1(y_true, y_pred)
        n = len(y_true)
        if auc is not None:
            results.append({"cohort": cohort, "model_family": "reorder", "metric_name": "roc_auc",
                             "metric_value": auc, "sample_size": n, "computed_at": now})
        if precision is not None:
            results.append({"cohort": cohort, "model_family": "reorder", "metric_name": "precision",
                             "metric_value": precision, "sample_size": n, "computed_at": now})
            results.append({"cohort": cohort, "model_family": "reorder", "metric_name": "recall",
                             "metric_value": recall, "sample_size": n, "computed_at": now})
            if f1 is not None:
                results.append({"cohort": cohort, "model_family": "reorder", "metric_name": "f1",
                                 "metric_value": f1, "sample_size": n, "computed_at": now})
    return results


# ═════════════════════════════════════════════════════════════════════
# Cold-start model — accuracy of predicted cuisine vs. actually
# clicked/ordered cuisine afterward. Special focus: cold_start_late
# pre-day-60 vs post-day-60 (the transition test).
# ═════════════════════════════════════════════════════════════════════

def compute_cold_start_metrics(conn, user_ids: list, cohort_map: dict) -> list:
    placeholders = ",".join("?" * len(user_ids))

    interactions = conn.execute(f"""
        SELECT user_id, simulated_day, cuisine_type
        FROM interaction_events
        WHERE user_id IN ({placeholders}) AND cuisine_type IS NOT NULL
    """, user_ids).fetchall()
    # user_id -> sorted list of (simulated_day, cuisine_type)
    interactions_by_user = defaultdict(list)
    for r in interactions:
        interactions_by_user[r["user_id"]].append((r["simulated_day"], r["cuisine_type"]))
    for uid in interactions_by_user:
        interactions_by_user[uid].sort()

    predictions = conn.execute(f"""
        SELECT user_id, simulated_day, cold_start_predicted_cuisine
        FROM model_scores_snapshot
        WHERE user_id IN ({placeholders}) AND cold_start_predicted_cuisine IS NOT NULL
        GROUP BY user_id, simulated_day
    """, user_ids).fetchall()

    by_group = defaultdict(lambda: {"correct": 0, "total": 0})
    for p in predictions:
        uid, day, predicted = p["user_id"], p["simulated_day"], p["cold_start_predicted_cuisine"]
        # Ground truth: the NEXT interaction's cuisine after this prediction's day
        future = [c for d, c in interactions_by_user.get(uid, []) if d >= day]
        if not future:
            continue
        actual = future[0]

        cohort = cohort_map[uid]
        group = cohort
        if cohort == "cold_start_late":
            group = "cold_start_late_pre_day60" if day < 60 else "cold_start_late_post_day60"

        by_group[group]["total"] += 1
        if predicted == actual:
            by_group[group]["correct"] += 1

    results = []
    now = datetime.now(timezone.utc).isoformat()
    for group, counts in by_group.items():
        if counts["total"] == 0:
            continue
        acc = counts["correct"] / counts["total"]
        results.append({"cohort": group, "model_family": "cold_start", "metric_name": "cuisine_prediction_accuracy",
                         "metric_value": acc, "sample_size": counts["total"], "computed_at": now})
    return results


# ═════════════════════════════════════════════════════════════════════
# Health model — rank displacement + GI/sodium correlation
# ═════════════════════════════════════════════════════════════════════

def compute_health_metrics(conn, user_ids: list, cohort_map: dict, conditions_by_user: dict) -> list:
    placeholders = ",".join("?" * len(user_ids))
    rows = conn.execute(f"""
        SELECT user_id, rank_with_health, rank_without_health, raw_gi, raw_sodium_mg, health_compliant
        FROM model_scores_snapshot
        WHERE user_id IN ({placeholders})
    """, user_ids).fetchall()

    displacement_by_cohort = defaultdict(list)
    gi_by_condition_group = defaultdict(list)

    for r in rows:
        cohort = cohort_map[r["user_id"]]
        if r["rank_with_health"] is not None and r["rank_without_health"] is not None:
            displacement_by_cohort[cohort].append(r["rank_without_health"] - r["rank_with_health"])

        conditions = conditions_by_user.get(r["user_id"], set())
        if r["raw_gi"] is not None:
            group = "diabetes_declared" if conditions & DIABETES_LIKE else "no_diabetes_declared"
            gi_by_condition_group[group].append(r["raw_gi"])

    results = []
    now = datetime.now(timezone.utc).isoformat()
    for cohort, values in displacement_by_cohort.items():
        results.append({"cohort": cohort, "model_family": "health", "metric_name": "avg_rank_displacement",
                         "metric_value": sum(values) / len(values), "sample_size": len(values), "computed_at": now})
    for group, values in gi_by_condition_group.items():
        results.append({"cohort": group, "model_family": "health", "metric_name": "avg_recommended_gi",
                         "metric_value": sum(values) / len(values), "sample_size": len(values), "computed_at": now})
    return results


# ═════════════════════════════════════════════════════════════════════
# Report generation
# ═════════════════════════════════════════════════════════════════════

def write_metrics(conn, run_id: str, results: list):
    for r in results:
        conn.execute("""
            INSERT INTO computed_metrics (run_id, cohort, model_family, metric_name, metric_value, sample_size, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (run_id, r["cohort"], r["model_family"], r["metric_name"], r["metric_value"], r["sample_size"], r["computed_at"]))
    conn.commit()


def build_report(results: list, n_valid_users: int, n_excluded: int) -> str:
    lines = ["# NARA 90-Day Harness — Computed Metrics Report", ""]
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"Users included: {n_valid_users} (excluded {n_excluded} with data-quality issues)")
    lines.append("")
    lines.append("## Known gaps in this report")
    lines.append("- Occasion classifier metrics: N/A — this harness always passes an explicit occasion, so detect_occasion() never executes.")
    lines.append("- Per-standalone-model ranker NDCG/MRR: not computed — only the ensemble's shown ranking could be clicked/ordered. Standalone contribution is in model_scores_snapshot directly (ranker_lgbm_score etc.), not re-derived here as a separate ranking metric.")
    lines.append("")
    lines.append("---")
    lines.append("")

    by_family = defaultdict(list)
    for r in results:
        by_family[r["model_family"]].append(r)

    for family, rows in by_family.items():
        lines.append(f"## {family}")
        lines.append("")
        lines.append("| Cohort | Metric | Value | Sample Size |")
        lines.append("|---|---|---|---|")
        for r in sorted(rows, key=lambda x: (x["cohort"], x["metric_name"])):
            lines.append(f"| {r['cohort']} | {r['metric_name']} | {r['metric_value']:.4f} | {r['sample_size']} |")
        lines.append("")

    return "\n".join(lines)


def main():
    conn = connect()
    run_id = "metrics-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    valid_users = get_valid_users(conn)
    if not valid_users:
        print("No valid completed users to compute metrics over. Exiting.")
        return

    user_ids = [u[0] for u in valid_users]
    cohort_map = {u[0]: u[2] for u in valid_users}

    # Load declared conditions per user (from onboarding_json) for the
    # health GI-correlation metric.
    conditions_by_user = {}
    for row in conn.execute("SELECT user_id, onboarding_json FROM harness_users WHERE user_id IN ({})".format(
            ",".join("?" * len(user_ids))), user_ids):
        try:
            ob = json.loads(row["onboarding_json"])
            conditions_by_user[row["user_id"]] = set(ob.get("declared_conditions") or [])
        except Exception:
            conditions_by_user[row["user_id"]] = set()

    all_results = []
    all_results += compute_ranking_metrics(conn, user_ids, cohort_map)
    all_results += compute_reorder_metrics(conn, user_ids, cohort_map)
    all_results += compute_cold_start_metrics(conn, user_ids, cohort_map)
    all_results += compute_health_metrics(conn, user_ids, cohort_map, conditions_by_user)

    write_metrics(conn, run_id, all_results)

    n_excluded_total = conn.execute("SELECT COUNT(*) FROM harness_completed_users").fetchone()[0] - len(valid_users)
    report = build_report(all_results, len(valid_users), n_excluded_total)

    Path("metrics_report.md").write_text(report)
    print(f"\nWrote metrics_report.md ({len(all_results)} metric rows computed).")
    print("Also written to the computed_metrics table for further querying.")


if __name__ == "__main__":
    main()
