-- NARA 90-Day Rigorous Test Harness — SQLite Schema
-- =====================================================
-- Test-run bookkeeping ONLY. Never touches Neon or local Postgres schemas
-- directly — this is what the harness itself writes to, tracking what it
-- did and what it observed, separately from the real production side
-- effects the harness's API calls cause (real users/orders/meal-logs in
-- the real databases — those aren't duplicated here, only referenced by
-- user_id/email).

CREATE TABLE IF NOT EXISTS harness_runs (
    run_id          TEXT PRIMARY KEY,   -- uuid, one per full script execution
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    config_json      TEXT NOT NULL      -- full config snapshot (cohort sizes, city list, etc) for reproducibility
);

CREATE TABLE IF NOT EXISTS harness_users (
    user_id         TEXT PRIMARY KEY,   -- real user_id from auth service
    run_id          TEXT NOT NULL REFERENCES harness_runs(run_id),
    email           TEXT NOT NULL,
    city            TEXT NOT NULL,      -- Delhi | Ahmedabad | Bengaluru | Kolkata | Indore
    cohort          TEXT NOT NULL,      -- cold_start_early | cold_start_late | health_focus | consistent_logger | transition
    cohort_detail   TEXT,               -- e.g. declared condition for health_focus, transition day for transition cohort
    onboarding_json TEXT NOT NULL,      -- full onboarding payload sent, for reference
    created_at      TEXT NOT NULL
);

-- RESUMABILITY: a user is marked here ONLY after all 13 weeks complete
-- successfully. harness_users (above) gets a row as soon as a user
-- STARTS (right after login/onboarding) — that's not enough to know a
-- user's simulation actually finished, since a crash/interrupt partway
-- through would still have a harness_users row. This table is checked at
-- startup to skip users that are genuinely done, across ANY prior run —
-- keyed by email (deterministic per plan) not run_id, so resuming after
-- a full script restart works, not just resuming within one run.
CREATE TABLE IF NOT EXISTS harness_completed_users (
    email           TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL,
    completed_at    TEXT NOT NULL
);

-- Every meal-log call the harness made, with its BACKDATED occurred_at
-- (the simulated day) alongside the REAL wall-clock time the API call
-- itself happened (api_called_at) — these are deliberately different
-- columns since the simulation backdates occurred_at while the actual
-- HTTP call and enrichment pipeline run in real time.
CREATE TABLE IF NOT EXISTS meal_log_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              TEXT NOT NULL REFERENCES harness_runs(run_id),
    user_id             TEXT NOT NULL REFERENCES harness_users(user_id),
    simulated_day        INTEGER NOT NULL,   -- 1-90
    occurred_at          TEXT NOT NULL,       -- backdated timestamp sent to /v1/meals/log
    api_called_at         TEXT NOT NULL,       -- real wall-clock time of the API call
    description          TEXT NOT NULL,
    occasion              TEXT NOT NULL,
    event_id              TEXT,                -- from ingestion's response
    enrichment_status      TEXT                 -- pending | processing | done | failed | timeout
);

-- One row per recommendation snapshot pulled — the checkpoint mechanism.
CREATE TABLE IF NOT EXISTS recommendation_snapshots (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              TEXT NOT NULL REFERENCES harness_runs(run_id),
    user_id             TEXT NOT NULL REFERENCES harness_users(user_id),
    simulated_day        INTEGER NOT NULL,
    week_number          INTEGER NOT NULL,   -- 1-13
    occasion              TEXT NOT NULL,
    endpoint              TEXT NOT NULL,       -- plain | with_restaurants
    debug_mode            INTEGER NOT NULL,    -- 0/1, whether _models breakdown was requested
    http_status           INTEGER NOT NULL,
    response_json         TEXT NOT NULL,       -- full raw response, for anything not captured in structured columns below
    dish_count            INTEGER,
    top_dish_name          TEXT,
    top_dish_cuisine       TEXT,
    top_dish_score         REAL,
    api_called_at          TEXT NOT NULL
);

-- Per-dish, per-model breakdown — extracted from debug=true snapshots.
-- This is the table that actually answers "what contributed how much"
-- and "how did the health model change ranking".
CREATE TABLE IF NOT EXISTS model_scores_snapshot (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                  TEXT NOT NULL REFERENCES harness_runs(run_id),
    user_id                 TEXT NOT NULL REFERENCES harness_users(user_id),
    snapshot_id             INTEGER NOT NULL REFERENCES recommendation_snapshots(id),
    simulated_day            INTEGER NOT NULL,
    week_number              INTEGER NOT NULL,
    dish_name                TEXT NOT NULL,
    cuisine_type              TEXT,
    rank                      INTEGER NOT NULL,   -- position in the final returned list
    final_score               REAL NOT NULL,

    -- Ranker family (3 standalone + ensemble)
    ranker_lgbm_score          REAL,
    ranker_xgb_score           REAL,
    ranker_logistic_score      REAL,
    ranker_ensemble_score      REAL,

    -- Health scorer family (3 standalone + ensemble)
    health_rf_score            REAL,
    health_xgb_shap_score      REAL,
    health_rules_score         REAL,
    health_ensemble_confidence REAL,
    health_compliant           INTEGER,             -- 0/1
    -- The rank-displacement metric you specifically asked for
    rank_with_health           INTEGER,
    rank_without_health         INTEGER,             -- computed by re-ranking scored list with health term zeroed out

    -- Reorder family (3 standalone + ensemble)
    reorder_cox_score          REAL,
    reorder_logistic_score      REAL,
    reorder_rf_score            REAL,
    reorder_ensemble_prob       REAL,

    -- Cold-start family (KNN + MLP; Wide&Deep intentionally excluded —
    -- see conversation notes on the unrecoverable OneHotEncoder gap)
    cold_start_knn_top_class     TEXT,
    cold_start_mlp_top_class     TEXT,
    cold_start_predicted_cuisine TEXT,

    -- Occasion classifier family (3 standalone + ensemble) — ONE per
    -- snapshot, not per-dish, but stored per-row for query convenience
    occasion_dt_pred             TEXT,
    occasion_rf_pred             TEXT,
    occasion_xgb_pred            TEXT,
    occasion_ensemble_pred       TEXT,
    occasion_actual_declared     TEXT,   -- ground truth, when the user logged a meal with an explicit occasion this week

    cuisine_affinity_score       REAL,
    raw_gi                       REAL,   -- the dish's actual GI value, for the health-correlation metric
    raw_calories                 REAL,
    raw_sodium_mg                REAL
);

-- Every click/order action the harness performed.
CREATE TABLE IF NOT EXISTS interaction_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES harness_runs(run_id),
    user_id         TEXT NOT NULL REFERENCES harness_users(user_id),
    simulated_day    INTEGER NOT NULL,
    week_number      INTEGER NOT NULL,
    action            TEXT NOT NULL,   -- click | order
    dish_name         TEXT NOT NULL,
    cuisine_type      TEXT,
    restaurant_id      TEXT,
    was_ordered_before  INTEGER,        -- 0/1 — ground truth for reorder-model calibration
    api_called_at        TEXT NOT NULL
);

-- Mid-study profile transitions (the "advanced" cohort).
CREATE TABLE IF NOT EXISTS profile_transitions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES harness_runs(run_id),
    user_id         TEXT NOT NULL REFERENCES harness_users(user_id),
    simulated_day    INTEGER NOT NULL,
    transition_type   TEXT NOT NULL,   -- health_diagnosis | city_relocation
    before_json       TEXT NOT NULL,
    after_json        TEXT NOT NULL,
    api_called_at      TEXT NOT NULL
);

-- Final computed metrics, one row per (user, week, metric) — the actual
-- deliverable numbers (NDCG@k, MRR, Recall@k, Precision@k, ROC-AUC, F1,
-- etc), computed AFTER the run from the raw tables above, not inline
-- during collection (keeps collection simple, metric logic auditable and
-- re-runnable independently without re-hitting any API).
CREATE TABLE IF NOT EXISTS computed_metrics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES harness_runs(run_id),
    user_id         TEXT,                -- NULL = cohort/city-level aggregate row
    cohort          TEXT,
    city            TEXT,
    week_number      INTEGER,             -- NULL = whole-run aggregate
    model_family      TEXT NOT NULL,       -- ranker | health | reorder | occasion | cold_start | end_to_end
    metric_name       TEXT NOT NULL,       -- ndcg_at_10 | mrr | recall_at_5 | precision_at_5 | roc_auc | f1 | ...
    metric_value       REAL NOT NULL,
    sample_size         INTEGER NOT NULL,
    computed_at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_meal_log_user       ON meal_log_events(user_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_user_week   ON recommendation_snapshots(user_id, week_number);
CREATE INDEX IF NOT EXISTS idx_model_scores_user    ON model_scores_snapshot(user_id, week_number);
CREATE INDEX IF NOT EXISTS idx_interaction_user     ON interaction_events(user_id, week_number);
CREATE INDEX IF NOT EXISTS idx_metrics_lookup       ON computed_metrics(cohort, model_family, metric_name);