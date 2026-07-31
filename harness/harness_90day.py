"""
NARA — 90-Day / 100-User Rigorous End-to-End Test Harness
============================================================

STANDALONE. Talks only to the real running services over HTTP, using
verified API contracts (same sources as the earlier 5-user harness:
auth/routers/auth.py, user-intelligence/routers/health_profile.py +
schemas/intelligence.py, ingestion/routers/meals.py + schemas/ingestion.py,
recommendation/routers/recommend.py + orders.py). No production code is
imported or modified by this script.

DESIGN
------
100 users, 20 per city (Delhi, Ahmedabad, Bengaluru, Kolkata, Indore),
split into 4 cohorts (6/6/4/4 per city = 20):

  - cold_start_early (15 total): minimal-optional onboarding, sparse
    meal-logging FROM WEEK 1, click/order every week throughout.
  - cold_start_late  (15 total): minimal-optional onboarding, ZERO meal
    logs until simulated day 60 (week 9), THEN sparse logging weeks 9-13.
    Click/order every week throughout — this is the group that tests
    whether cold-start genuinely transitions to warm-start signal once
    real behavioral data finally arrives.
  - health_focus (30 total): mandatory declared_conditions (non-empty),
    occasional/sparse meal logging every week, click/order every week.
    This cohort is what the health-model rank-displacement and
    GI/sodium-correlation metrics are computed from.
  - consistent_logger (20 total): regular (not daily, ~4-5x/week) meal
    logging every week, click/order every week. The steady baseline.

A 5th behavior — mid-study PROFILE TRANSITION (health diagnosis or city
relocation via the real PUT /v1/health-profile, at week 7) — is layered
onto 10 of the consistent_logger users rather than being a separate
cohort with its own city/onboarding rules, since a transition is a thing
that HAPPENS TO an existing profile, not a distinct starting condition.

TIME SIMULATION
---------------
occurred_at on /v1/meals/log is client-settable (confirmed from
ingestion/schemas/ingestion.py), so the whole 90-day window is generated
and logged in ONE real script run — no waiting 90 actual days. Each
"week" (1-13) is a checkpoint: log that week's backdated meals, poll
enrichment to completion, then pull a recommendation snapshot.

HONEST LIMITATION: recommendation context (hour/day_of_week/month/season)
is always REAL wall-clock "now" — recommend.py's _build_context() has no
concept of simulated time. This harness can validly test whether
cuisine_affinity/dish_interactions/reorder_boost adapt over the simulated
90 days (those depend only on cumulative FoodGraph/Redis state, not
wall-clock time) — it CANNOT test "what would recommendations look like
on a specific simulated calendar date." That's a real, structural
limitation of testing this system without literally waiting, not a bug
in this script.

CHECKPOINT CADENCE (bounds total API call volume — see runtime note below)
----------------------------------------------------------------------
- Weeks 1, 7, 13: FULL checkpoint — recommendations for all 4 occasions,
  debug=true (full per-model breakdown captured into model_scores_snapshot).
- All other weeks (2-6, 8-12): LIGHT checkpoint — one occasion (lunch),
  debug=true.
- Every week, every user: exactly one random click, ~30% chance of a
  follow-up checkout — this is what feeds the reorder-model calibration
  metric (predicted probability vs. real observed reorder behavior).

RUNTIME NOTE: even at this bounded cadence, 100 users x 13 weeks with
real HTTP round-trips + enrichment polling is substantial. Concurrency is
bounded by --concurrency (default 8 simultaneous users) to avoid
hammering a local docker-compose stack. Expect this to take a real amount
of wall-clock time (likely 30-90+ minutes depending on your machine/stack)
— it is NOT a quick script.

STORAGE
-------
SQLite (schema.sql, same directory) — a separate, purely-bookkeeping
database, distinct from both Neon and local Postgres. Written to
incrementally as results arrive (not held in memory until the end), so a
partial run still leaves usable data if interrupted.

METRICS
-------
This script ONLY collects raw data. Computing NDCG/MRR/Recall/Precision/
ROC-AUC/F1/calibration curves/SHAP-attribution happens in a SEPARATE
script (compute_metrics.py) reading from the SQLite file afterward — kept
separate so metric logic is auditable/re-runnable without re-hitting any
API, and a metric bug doesn't require re-running the whole 90-day
simulation.
"""
import argparse
import asyncio
import json
import random
import sqlite3
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

TOTAL_DAYS = 90
TOTAL_WEEKS = 13
OCCASIONS = ["breakfast", "lunch", "snack", "dinner"]
FULL_CHECKPOINT_WEEKS = {1, 7, 13}

ENRICHMENT_POLL_INTERVAL_S = 2
ENRICHMENT_POLL_TIMEOUT_S = 30

# ── Cities: 20 users each, with real-ish coordinates for with-restaurants
# calls and a region/cuisine mapping used for realistic meal descriptions.
# Indore doesn't cleanly map to any of the 5 region buckets (north/south/
# east/west/northeast) the system actually uses (it's central India) —
# mapped to "west" as the nearest approximation; flagged here rather than
# silently treated as exact.
CITIES = {
    "Delhi":      {"lat": 28.7041, "lng": 77.1025, "region": "north", "cuisine": "north_indian"},
    "Ahmedabad":  {"lat": 23.0225, "lng": 72.5714, "region": "west",  "cuisine": "gujarati"},
    "Bengaluru":  {"lat": 12.9716, "lng": 77.5946, "region": "south", "cuisine": "south_indian"},
    "Kolkata":    {"lat": 22.5726, "lng": 88.3639, "region": "east",  "cuisine": "bengali"},
    "Indore":     {"lat": 22.7196, "lng": 75.8577, "region": "west",  "cuisine": "north_indian"},  # approximation — see note above
}

MEAL_DESCRIPTIONS = {
    "north_indian":  ["Chole bhature", "Butter chicken with naan", "Paratha with curd", "Rajma chawal", "Samosa and chai"],
    "gujarati":      ["Khichadi with kadhi", "Dhokla", "Thepla and chai", "Undhiyu", "Handvo"],
    "south_indian":  ["Idli sambar", "Masala dosa", "Rava upma", "Curd rice", "Filter coffee and vada"],
    "bengali":       ["Macher jhol with rice", "Luchi and alur dom", "Mishti doi", "Shorshe ilish", "Cholar dal"],
}

CONDITION_POOL = ["type2_diabetes", "hypertension", "high_cholesterol", "prediabetes", "obesity"]

BASE_HOST = "localhost"


def base_urls(host: str) -> dict:
    return {
        "auth":           f"http://{host}:8001",
        "user_intel":     f"http://{host}:8002",
        "ingestion":      f"http://{host}:8003",
        "recommendation": f"http://{host}:8005",
    }


# ═════════════════════════════════════════════════════════════════════
# SQLite — single connection, serialized writes via an asyncio.Lock
# ═════════════════════════════════════════════════════════════════════

class HarnessDB:
    def __init__(self, path: Path, run_id: str):
        self.path = path
        self.run_id = run_id
        self.conn = sqlite3.connect(str(path))
        self.conn.execute("PRAGMA journal_mode=WAL")  # allows concurrent readers while we write
        self.lock = asyncio.Lock()
        schema_path = Path(__file__).parent / "schema.sql"
        self.conn.executescript(schema_path.read_text())
        self.conn.commit()

    async def start_run(self, config: dict):
        async with self.lock:
            self.conn.execute(
                "INSERT INTO harness_runs (run_id, started_at, config_json) VALUES (?, ?, ?)",
                (self.run_id, datetime.now(timezone.utc).isoformat(), json.dumps(config)),
            )
            self.conn.commit()

    async def finish_run(self):
        async with self.lock:
            self.conn.execute(
                "UPDATE harness_runs SET finished_at = ? WHERE run_id = ?",
                (datetime.now(timezone.utc).isoformat(), self.run_id),
            )
            self.conn.commit()

    async def is_completed(self, email: str) -> bool:
        async with self.lock:
            row = self.conn.execute(
                "SELECT 1 FROM harness_completed_users WHERE email = ?", (email,)
            ).fetchone()
            return row is not None

    async def mark_completed(self, email: str, run_id: str):
        async with self.lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO harness_completed_users (email, run_id, completed_at) VALUES (?, ?, ?)",
                (email, run_id, datetime.now(timezone.utc).isoformat()),
            )
            self.conn.commit()

    def count_completed(self) -> int:
        # Not lock-guarded — called for progress reporting only, a
        # slightly stale read here is harmless (just a printed percentage).
        return self.conn.execute("SELECT COUNT(*) FROM harness_completed_users").fetchone()[0]

    async def insert(self, table: str, row: dict, or_ignore: bool = False) -> int:
        async with self.lock:
            cols = ", ".join(row.keys())
            placeholders = ", ".join(["?"] * len(row))
            verb = "INSERT OR IGNORE" if or_ignore else "INSERT"
            cur = self.conn.execute(
                f"{verb} INTO {table} ({cols}) VALUES ({placeholders})",
                list(row.values()),
            )
            self.conn.commit()
            return cur.lastrowid


# ═════════════════════════════════════════════════════════════════════
# User plan generation — decides cohort/city/onboarding/behavior pattern
# BEFORE any API calls happen, so the whole plan is inspectable/loggable.
# ═════════════════════════════════════════════════════════════════════

def build_user_plans(seed: int = 42) -> list:
    rng = random.Random(seed)
    plans = []
    uid_counter = 0

    for city, city_info in CITIES.items():
        # Per city (x5 cities = 100 total):
        #   cold_start_early: 3   \_ 30 cold-start total (15/15 early/late)
        #   cold_start_late:  3   /
        #   health_focus:     6   -> 30 total
        #   consistent_logger:4   -> 20 total (steady baseline, no transition)
        #   transition:       4   -> 20 total (the "advanced" cohort — mid-
        #                            study health diagnosis or city move,
        #                            layered onto an otherwise
        #                            consistent-logger-like behavior
        #                            pattern, own dedicated slots so it
        #                            doesn't eat into the 20 plain
        #                            consistent_logger users)
        # 3+3+6+4+4 = 20 per city x 5 cities = 100.
        city_cohort_counts = [
            ("cold_start_early", 3),
            ("cold_start_late", 3),
            ("health_focus", 6),
            ("consistent_logger", 4),
            ("transition", 4),
        ]

        for cohort, count in city_cohort_counts:
            for j in range(count):
                uid_counter += 1
                is_transition = cohort == "transition"
                plan = {
                    "idx": uid_counter,
                    "email": f"h90.{city.lower()}.{cohort}.{j}@harness100.example.com",
                    "password": "TestPass123",
                    "city": city,
                    "region": city_info["region"],
                    "cuisine": city_info["cuisine"],
                    "cohort": cohort,
                    # transition users otherwise BEHAVE like consistent_logger
                    # (regular meal logging) until their week-7 transition —
                    # cohort_base drives onboarding/meal-cadence rules, while
                    # `cohort` (above) is what gets stored/reported.
                    "cohort_base": "consistent_logger" if is_transition else cohort,
                    "has_transition": is_transition,
                }
                plans.append(plan)

    assert len(plans) == 100, f"expected 100 user plans, got {len(plans)}"
    return plans


def build_onboarding(plan: dict, rng: random.Random) -> dict:
    cohort = plan["cohort_base"]
    is_cold_start = cohort in ("cold_start_early", "cold_start_late")

    onboarding = {
        "declared_conditions": [],
        "dietary_restrictions": [],
        "nutritional_goals": {},
        "age": rng.randint(22, 58),
        "weight_kg": round(rng.uniform(52, 88), 1),
        "height_cm": round(rng.uniform(155, 182), 1),
        "gender": rng.choice(["male", "female"]),
        "activity_level": rng.choice(["sedentary", "lightly_active", "moderately_active", "very_active"]),
        "income_tier": rng.choice(["low", "medium", "high"]),
        "region": plan["region"],
        "occupation": rng.choice(["salaried", "self_employed", "student", "homemaker", "retired"]),
        "living_situation": rng.choice(["alone", "with_family", "with_roommates", "with_partner"]),
        "stress_level": rng.choice(["low", "medium", "high"]),
        "is_wfh": rng.random() < 0.3,
    }

    if is_cold_start:
        # True cold-start: minimal-optional fields only. Age/gender kept
        # (schema requires SOME identity) but everything non-mandatory
        # left at the schema's own defaults instead of populated —
        # region/occupation/living_situation/stress deliberately omitted
        # (None) so there's genuinely no behavioral OR declared signal
        # beyond the bare minimum.
        onboarding.update({
            "income_tier": None, "occupation": None,
            "living_situation": None, "stress_level": None, "is_wfh": False,
        })

    if cohort == "health_focus" or plan["has_transition"]:
        n_conditions = rng.choice([1, 1, 2])  # mostly single-condition, sometimes comorbid
        onboarding["declared_conditions"] = rng.sample(CONDITION_POOL, n_conditions)

    return onboarding


def meals_for_week(plan: dict, week: int, rng: random.Random) -> list:
    """Returns a list of (description, occasion, day_offset_within_week) for this week."""
    cohort = plan["cohort"] if not plan["has_transition"] else plan["cohort_base"]
    dishes = MEAL_DESCRIPTIONS[plan["cuisine"]]

    if plan["cohort_base"] == "cold_start_early":
        # Sparse from week 1: ~1 meal every 2-3 days -> roughly 2-3/week
        n = rng.choice([0, 1, 1, 2])
    elif plan["cohort_base"] == "cold_start_late":
        # Nothing until week 9 (day ~57-63), then sparse
        n = 0 if week < 9 else rng.choice([0, 1, 1, 2])
    elif plan["cohort_base"] == "health_focus":
        # Occasional — similar sparsity to cold_start_early but with
        # declared conditions already present from onboarding
        n = rng.choice([0, 1, 1, 2])
    else:  # consistent_logger / transition
        n = rng.choice([3, 4, 4, 5])  # regular but not literally daily (max 5/week < 7)

    entries = []
    days_used = rng.sample(range(1, 8), min(n, 7))
    for d in days_used:
        occasion = rng.choice(OCCASIONS)
        description = rng.choice(dishes)
        entries.append((description, occasion, d))
    return entries


# ═════════════════════════════════════════════════════════════════════
# API helpers
# ═════════════════════════════════════════════════════════════════════

def _safe_json(response: httpx.Response):
    try:
        return response.json()
    except Exception:
        return {"raw_text": response.text[:500]}


async def register_and_login(client, urls, email, password) -> dict:
    """
    Login-first, register-on-demand — makes the harness resumable. A
    previous run may have already created some accounts (or failed
    partway through, as happened with the .local email bug), so blindly
    re-registering every time either wastes a call on an account that
    already exists or, worse, silently proceeds past a register failure
    without ever checking it (which is exactly what masked the real
    problem last run — register's response was never inspected, so the
    422 only ever surfaced on the login call afterward). This tries login
    first; only registers if login genuinely fails because the account
    doesn't exist, then retries login once.
    """
    login = await client.post(f"{urls['auth']}/v1/auth/login", json={"email": email, "password": password})
    if login.status_code == 200:
        body = login.json()
        return {"token": body["access_token"], "user_id": body["user_id"]}

    # Account doesn't exist yet (or some other login failure) — register,
    # then retry login. If registration itself fails, raise with the real
    # response body instead of silently falling through to a second,
    # equally-doomed login attempt.
    reg = await client.post(f"{urls['auth']}/v1/auth/register", json={"email": email, "password": password})
    if reg.status_code >= 400:
        reg.raise_for_status()

    login2 = await client.post(f"{urls['auth']}/v1/auth/login", json={"email": email, "password": password})
    login2.raise_for_status()
    body = login2.json()
    return {"token": body["access_token"], "user_id": body["user_id"]}


async def submit_onboarding(client, urls, token, onboarding):
    r = await client.post(f"{urls['user_intel']}/v1/health-profile", json=onboarding,
                           headers={"Authorization": f"Bearer {token}"})
    return r.status_code


async def update_onboarding(client, urls, token, onboarding):
    r = await client.put(f"{urls['user_intel']}/v1/health-profile", json=onboarding,
                          headers={"Authorization": f"Bearer {token}"})
    return r.status_code, _safe_json(r)


async def log_meal(client, urls, token, description, occasion, occurred_at: datetime):
    r = await client.post(
        f"{urls['ingestion']}/v1/meals/log",
        json={
            "description": description,
            "occurred_at": occurred_at.isoformat(),
            "context": {"occasion": occasion, "location_type": "home", "notes": "harness90"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    return r.json()


async def poll_enrichment(client, urls, token, event_id) -> str:
    deadline = time.monotonic() + ENRICHMENT_POLL_TIMEOUT_S
    while time.monotonic() < deadline:
        r = await client.get(f"{urls['ingestion']}/v1/meals/{event_id}/status",
                              headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        status = r.json()["enrichment_status"]
        if status in ("done", "failed"):
            return status
        await asyncio.sleep(ENRICHMENT_POLL_INTERVAL_S)
    return "timeout"


async def get_recommendations(client, urls, token, occasion, debug=False):
    r = await client.get(f"{urls['recommendation']}/v1/recommend/",
                         params={"occasion": occasion, "n": 10, "debug": str(debug).lower()},
                         headers={"Authorization": f"Bearer {token}"})
    return r.status_code, _safe_json(r)


async def get_recommendations_with_restaurants(client, urls, token, lat, lng, occasion):
    r = await client.get(f"{urls['recommendation']}/v1/recommend/with-restaurants",
                         params={"lat": lat, "lng": lng, "occasion": occasion, "n": 10},
                         headers={"Authorization": f"Bearer {token}"})
    return r.status_code, _safe_json(r)


async def get_restaurant_menu(client, urls, token, restaurant_id):
    r = await client.get(f"{urls['recommendation']}/v1/recommend/restaurants/{restaurant_id}",
                         headers={"Authorization": f"Bearer {token}"})
    return r.status_code, _safe_json(r)


async def add_to_cart(client, urls, token, restaurant_id, dish_name, cuisine_type, session_id):
    r = await client.post(f"{urls['recommendation']}/v1/orders/cart/items",
                          json={"restaurant_id": restaurant_id, "dish_name": dish_name,
                                "cuisine_type": cuisine_type, "quantity": 1, "session_id": session_id},
                          headers={"Authorization": f"Bearer {token}"})
    return r.status_code, _safe_json(r)


async def checkout(client, urls, token):
    r = await client.post(f"{urls['recommendation']}/v1/orders/checkout",
                          headers={"Authorization": f"Bearer {token}"})
    return r.status_code, _safe_json(r)


# ═════════════════════════════════════════════════════════════════════
# Per-user 90-day simulation
# ═════════════════════════════════════════════════════════════════════

def extract_model_score_rows(snapshot_body: dict, snapshot_id: int, run_id: str, user_id: str,
                              simulated_day: int, week_number: int) -> list:
    """Flattens a debug=true recommendation response into model_scores_snapshot rows."""
    rows = []
    recs = snapshot_body.get("recommendations", []) if isinstance(snapshot_body, dict) else []

    # Compute rank-without-health by re-sorting on (score - health contribution)
    # — approximate, using each dish's own final_score minus its health
    # breakdown's implied contribution isn't directly available as a delta,
    # so this uses a simpler, honestly-labeled proxy: rank order if dishes
    # were sorted by ranker-only ensemble score (health term fully excluded
    # from the comparison key), which IS a valid "would health have changed
    # the ordering" check even though it isn't a literal partial-sum removal.
    ranker_only_order = sorted(
        recs, key=lambda d: d.get("_models", {}).get("ranker", {}).get("ensemble_score",
                              d.get("score", 0)), reverse=True
    )
    rank_without_health = {d.get("dish_name"): i for i, d in enumerate(ranker_only_order)}

    for rank, dish in enumerate(recs):
        models = dish.get("_models", {})
        ranker = models.get("ranker", {}) or {}
        health = models.get("health", {}) or {}
        reorder = models.get("reorder", {}) or {}
        cold = models.get("cold_start", {}) or {}
        occ = models.get("occasion_detection", {}) or {}

        ranker_standalone = ranker.get("standalone", {}) if isinstance(ranker, dict) else {}
        health_standalone = health.get("standalone", {}) if isinstance(health, dict) else {}
        reorder_standalone = reorder.get("standalone", {}) if isinstance(reorder, dict) else {}
        occ_standalone = occ.get("standalone", {}) if isinstance(occ, dict) else {}

        rows.append({
            "run_id": run_id, "user_id": user_id, "snapshot_id": snapshot_id,
            "simulated_day": simulated_day, "week_number": week_number,
            "dish_name": dish.get("dish_name"), "cuisine_type": dish.get("cuisine_type"),
            "rank": rank, "final_score": dish.get("score"),

            "ranker_lgbm_score": ranker_standalone.get("lgbm"),
            "ranker_xgb_score": ranker_standalone.get("xgb"),
            "ranker_logistic_score": ranker_standalone.get("logistic"),
            "ranker_ensemble_score": ranker.get("ensemble_score", dish.get("score")),

            "health_rf_score": health_standalone.get("rf"),
            "health_xgb_shap_score": health_standalone.get("xgb"),
            "health_rules_score": health_standalone.get("rules"),
            "health_ensemble_confidence": health.get("confidence"),
            "health_compliant": 1 if dish.get("health_compliant") else 0,
            "rank_with_health": rank,
            "rank_without_health": rank_without_health.get(dish.get("dish_name")),

            "reorder_cox_score": reorder_standalone.get("cox_xgboost") or reorder_standalone.get("cox"),
            "reorder_logistic_score": reorder_standalone.get("logistic"),
            "reorder_rf_score": reorder_standalone.get("rf"),
            "reorder_ensemble_prob": reorder.get("ensemble_prob"),

            "cold_start_knn_top_class": (cold.get("knn") or [None])[0] if isinstance(cold.get("knn"), list) else None,
            "cold_start_mlp_top_class": (cold.get("mlp") or [None])[0] if isinstance(cold.get("mlp"), list) else None,
            "cold_start_predicted_cuisine": models.get("cold_start_predicted_cuisine"),

            "occasion_dt_pred": occ_standalone.get("dt"),
            "occasion_rf_pred": occ_standalone.get("rf"),
            "occasion_xgb_pred": occ_standalone.get("xgb"),
            "occasion_ensemble_pred": snapshot_body.get("occasion"),
            "occasion_actual_declared": None,  # filled in post-hoc by compute_metrics.py, joined against meal_log_events

            "cuisine_affinity_score": dish.get("cuisine_affinity_score"),
            "raw_gi": (dish.get("nutrition") or {}).get("gi"),
            "raw_calories": (dish.get("nutrition") or {}).get("calories"),
            "raw_sodium_mg": (dish.get("nutrition") or {}).get("sodium_mg"),
        })
    return rows


async def run_user_simulation(client, urls, db: HarnessDB, run_id: str, plan: dict, rng: random.Random):
    onboarding = build_onboarding(plan, rng)
    auth = await register_and_login(client, urls, plan["email"], plan["password"])
    user_id, token = auth["user_id"], auth["token"]
    token_acquired_at = time.monotonic()

    # or_ignore=True: build_user_plans() is deterministic (fixed seed), so
    # re-running the script generates the SAME 100 emails every time. If a
    # prior run got partway through before failing/stopping, those
    # accounts already exist — login (in register_and_login above)
    # correctly finds them and returns their real, same user_id. Without
    # or_ignore, re-inserting that same user_id here would crash with a
    # primary-key collision instead of just continuing the simulation.
    # NOTE: this means harness_users' onboarding_json/cohort_detail reflect
    # whichever run first created the row, not necessarily the latest — a
    # resumed user's ACTUAL backend health-profile still gets updated to
    # this run's values via submit_onboarding() below regardless, so this
    # is a bookkeeping-table staleness note, not a functional gap.
    await db.insert("harness_users", {
        "user_id": user_id, "run_id": run_id, "email": plan["email"], "city": plan["city"],
        "cohort": plan["cohort"], "cohort_detail": json.dumps({"conditions": onboarding["declared_conditions"]}),
        "onboarding_json": json.dumps(onboarding), "created_at": datetime.now(timezone.utc).isoformat(),
    }, or_ignore=True)
    await submit_onboarding(client, urls, token, onboarding)

    city_info = CITIES[plan["city"]]
    sim_start = datetime.now(timezone.utc) - timedelta(days=TOTAL_DAYS)

    for week in range(1, TOTAL_WEEKS + 1):
        simulated_day = week * 7

        TOKEN_REFRESH_MARGIN_S = 25 * 60  # refresh at 25 min, before the real 30 min expiry
        if time.monotonic() - token_acquired_at > TOKEN_REFRESH_MARGIN_S:
            auth = await register_and_login(client, urls, plan["email"], plan["password"])
            token = auth["token"]
            token_acquired_at = time.monotonic()

        # Mid-study transition (week 7 only, transition users only)
        if plan["has_transition"] and week == 7:
            new_onboarding = dict(onboarding)
            transition_type = rng.choice(["health_diagnosis", "city_relocation"])
            before = dict(new_onboarding)
            if transition_type == "health_diagnosis":
                new_onboarding["declared_conditions"] = list(set(
                    new_onboarding["declared_conditions"] + [rng.choice(CONDITION_POOL)]
                ))
            else:
                other_cities = [c for c in CITIES if c != plan["city"]]
                new_city = rng.choice(other_cities)
                new_onboarding["region"] = CITIES[new_city]["region"]
            status, _ = await update_onboarding(client, urls, token, new_onboarding)
            await db.insert("profile_transitions", {
                "run_id": run_id, "user_id": user_id, "simulated_day": simulated_day,
                "transition_type": transition_type, "before_json": json.dumps(before),
                "after_json": json.dumps(new_onboarding), "api_called_at": datetime.now(timezone.utc).isoformat(),
            })
            onboarding = new_onboarding

        # ── Meal logging for this week (backdated occurred_at) ──
        for description, occasion, day_offset in meals_for_week(plan, week, rng):
            occurred_at = sim_start + timedelta(days=simulated_day - 7 + day_offset,
                                                 hours=rng.randint(7, 21), minutes=rng.randint(0, 59))
            try:
                logged = await log_meal(client, urls, token, description, occasion, occurred_at)
                enrichment_status = await poll_enrichment(client, urls, token, logged["event_id"])
                await db.insert("meal_log_events", {
                    "run_id": run_id, "user_id": user_id, "simulated_day": simulated_day,
                    "occurred_at": occurred_at.isoformat(), "api_called_at": datetime.now(timezone.utc).isoformat(),
                    "description": description, "occasion": occasion,
                    "event_id": logged.get("event_id"), "enrichment_status": enrichment_status,
                })
            except Exception:
                pass  # a single failed meal log shouldn't abort the whole 90-day run for this user

        # ── Recommendation checkpoint(s) ──
        occasions_this_week = OCCASIONS if week in FULL_CHECKPOINT_WEEKS else ["lunch"]
        for occasion in occasions_this_week:
            status, body = await get_recommendations(client, urls, token, occasion, debug=True)
            recs = body.get("recommendations", []) if isinstance(body, dict) else []
            top = recs[0] if recs else {}
            snapshot_id = await db.insert("recommendation_snapshots", {
                "run_id": run_id, "user_id": user_id, "simulated_day": simulated_day, "week_number": week,
                "occasion": occasion, "endpoint": "plain", "debug_mode": 1, "http_status": status,
                "response_json": json.dumps(body)[:20000],  # cap stored size
                "dish_count": len(recs), "top_dish_name": top.get("dish_name"),
                "top_dish_cuisine": top.get("cuisine_type"), "top_dish_score": top.get("score"),
                "api_called_at": datetime.now(timezone.utc).isoformat(),
            })
            for row in extract_model_score_rows(body, snapshot_id, run_id, user_id, simulated_day, week):
                await db.insert("model_scores_snapshot", row)

        # ── Weekly click + probabilistic checkout, via with-restaurants ──
        wr_status, wr_body = await get_recommendations_with_restaurants(
            client, urls, token, city_info["lat"], city_info["lng"], rng.choice(OCCASIONS)
        )
        recs = wr_body.get("recommendations", []) if isinstance(wr_body, dict) else []
        orderable = [r for r in recs if r.get("nearby_restaurants")]
        if orderable:
            chosen_rec = rng.choice(orderable)
            restaurant = rng.choice(chosen_rec["nearby_restaurants"])
            session_id = wr_body.get("session_id")

            # FIX: the recommended dish (chosen_rec) is matched to nearby
            # restaurants purely by CUISINE overlap — it is NOT guaranteed
            # to actually be on this specific restaurant's real menu
            # (restaurant_menu_items is a randomized per-restaurant subset
            # of nutrition_kb, not the full catalog). Adding that dish
            # straight to cart was hitting orders.py's own menu-validation
            # check and failing with 400. Fetch the restaurant's REAL menu
            # and pick a dish that's actually confirmed to be there.
            menu_status, menu_body = await get_restaurant_menu(client, urls, token, restaurant["id"])
            menu_items = menu_body.get("menu", []) if isinstance(menu_body, dict) else []

            if menu_items:
                dish = rng.choice(menu_items)
                dish_name, cuisine_type = dish["dish_name"], dish.get("cuisine_type")

                await add_to_cart(client, urls, token, restaurant["id"], dish_name, cuisine_type, session_id)
                await db.insert("interaction_events", {
                    "run_id": run_id, "user_id": user_id, "simulated_day": simulated_day, "week_number": week,
                    "action": "click", "dish_name": dish_name, "cuisine_type": cuisine_type,
                    "restaurant_id": restaurant["id"], "was_ordered_before": None,
                    "api_called_at": datetime.now(timezone.utc).isoformat(),
                })
                if rng.random() < 0.30:
                    await checkout(client, urls, token)
                    await db.insert("interaction_events", {
                        "run_id": run_id, "user_id": user_id, "simulated_day": simulated_day, "week_number": week,
                        "action": "order", "dish_name": dish_name, "cuisine_type": cuisine_type,
                        "restaurant_id": restaurant["id"], "was_ordered_before": None,
                        "api_called_at": datetime.now(timezone.utc).isoformat(),
                    })


# ═════════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════════

async def main(host: str, db_path: Path, concurrency: int, max_users: int | None = None):
    urls = base_urls(host)
    run_id = str(uuid.uuid4())
    db = HarnessDB(db_path, run_id)

    all_plans = build_user_plans()
    if max_users is not None:
        all_plans = all_plans[:max_users]
        print(f"--max-users {max_users}: limiting this run to the first {len(all_plans)} user(s).\n")

    await db.start_run({"total_users": len(all_plans), "total_weeks": TOTAL_WEEKS, "cities": list(CITIES.keys())})

    # RESUMABILITY: skip any plan whose email is already marked completed
    # from a prior run (or an earlier attempt within a script that was
    # interrupted, e.g. Ctrl+C / KeyboardInterrupt) — this is what makes
    # "start from where it stopped" actually true, instead of always
    # reprocessing all 100 users from scratch.
    plans = []
    skipped = 0
    for plan in all_plans:
        if await db.is_completed(plan["email"]):
            skipped += 1
        else:
            plans.append(plan)

    if skipped:
        print(f"Resuming: {skipped} user(s) already completed in a prior run, skipping them.")
    print(f"Processing {len(plans)} remaining user(s) out of {len(all_plans)} total.\n")

    sem = asyncio.Semaphore(concurrency)

    # Progress milestones — printed once each, the first time cumulative
    # completions (across ALL plans, including ones skipped as already-done
    # from a prior run) crosses each threshold.
    milestones = [20, 40, 50, 80, 100]
    milestones_hit = set()
    total_users = len(all_plans)

    async def bounded_run(plan):
        async with sem:
            rng = random.Random(1000 + plan["idx"])
            async with httpx.AsyncClient(timeout=60.0) as client:
                print(f"[{plan['idx']:3d}/100] starting {plan['email']} ({plan['cohort']}, {plan['city']})")
                try:
                    await run_user_simulation(client, urls, db, run_id, plan, rng)
                    await db.mark_completed(plan["email"], run_id)
                    print(f"[{plan['idx']:3d}/100] done")
                except Exception as e:
                    # FIX: str(e) can be EMPTY for several real exception
                    # types (httpx.ReadTimeout, httpx.ConnectError,
                    # asyncio.TimeoutError often carry no message at all),
                    # which was printing "[N/100] FAILED: " with zero
                    # diagnostic info — impossible to tell a network
                    # timeout from a real bug from a service being down.
                    # Always show the exception TYPE, and the full
                    # traceback on stderr so the actual failure point is
                    # visible.
                    import traceback
                    print(f"[{plan['idx']:3d}/100] FAILED: {type(e).__name__}: {e}")
                    traceback.print_exc()
                    # Deliberately NOT marked completed — a failed user
                    # will be retried on the next run instead of silently
                    # staying missing from the dataset forever.

            completed_now = db.count_completed()
            pct = round(100 * completed_now / total_users)
            for m in milestones:
                if pct >= m and m not in milestones_hit:
                    milestones_hit.add(m)
                    print(f"\n=== PROGRESS: {completed_now}/{total_users} users complete ({pct}%) ===\n")

    await asyncio.gather(*(bounded_run(p) for p in plans))
    await db.finish_run()
    print(f"\nRun {run_id} complete. Data in {db_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-host", default="localhost")
    parser.add_argument("--db-path", default="./harness90.sqlite")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--max-users", type=int, default=None,
                         help="Only process the first N users (by plan order) — useful for a quick smoke test "
                              "before committing to the full 100-user run. Takes the first N in city order "
                              "(e.g. --max-users 20 = all 20 Delhi users, full cohort diversity in one city).")
    args = parser.parse_args()

    asyncio.run(main(args.base_host, Path(args.db_path), args.concurrency, args.max_users))