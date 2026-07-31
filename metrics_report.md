# NARA 90-Day Harness — Computed Metrics Report

Generated: 2026-07-30T12:26:47.389183+00:00
Users included: 12 (excluded 17 with data-quality issues)

## Known gaps in this report
- Occasion classifier metrics: N/A — this harness always passes an explicit occasion, so detect_occasion() never executes.
- Per-standalone-model ranker NDCG/MRR: not computed — only the ensemble's shown ranking could be clicked/ordered. Standalone contribution is in model_scores_snapshot directly (ranker_lgbm_score etc.), not re-derived here as a separate ranking metric.

---

## end_to_end

| Cohort | Metric | Value | Sample Size |
|---|---|---|---|
| cold_start_early | mrr | 0.2397 | 5 |
| cold_start_early | ndcg_at_10 | 0.4133 | 5 |
| cold_start_early | precision_at_5 | 0.0800 | 5 |
| cold_start_early | recall_at_5 | 0.4000 | 5 |
| consistent_logger | mrr | 0.1885 | 4 |
| consistent_logger | ndcg_at_10 | 0.3726 | 4 |
| consistent_logger | precision_at_5 | 0.0500 | 4 |
| consistent_logger | recall_at_5 | 0.2500 | 4 |
| health_focus | mrr | 0.1429 | 1 |
| health_focus | ndcg_at_10 | 0.3333 | 1 |
| health_focus | precision_at_5 | 0.0000 | 1 |
| health_focus | recall_at_5 | 0.0000 | 1 |
| transition | mrr | 0.3181 | 6 |
| transition | ndcg_at_10 | 0.4825 | 6 |
| transition | precision_at_5 | 0.1667 | 6 |
| transition | recall_at_5 | 0.8333 | 6 |

## cold_start

| Cohort | Metric | Value | Sample Size |
|---|---|---|---|
| cold_start_early | cuisine_prediction_accuracy | 0.2564 | 39 |
| consistent_logger | cuisine_prediction_accuracy | 0.3415 | 41 |
| health_focus | cuisine_prediction_accuracy | 0.3846 | 13 |
| transition | cuisine_prediction_accuracy | 0.2558 | 43 |

## health

| Cohort | Metric | Value | Sample Size |
|---|---|---|---|
| cold_start_early | avg_rank_displacement | 0.0000 | 660 |
| consistent_logger | avg_rank_displacement | 0.0000 | 880 |
| diabetes_declared | avg_recommended_gi | 47.1818 | 440 |
| health_focus | avg_rank_displacement | 0.0000 | 220 |
| no_diabetes_declared | avg_recommended_gi | 47.6141 | 2200 |
| transition | avg_rank_displacement | 0.0000 | 880 |
