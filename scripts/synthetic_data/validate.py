"""
NARA Synthetic Data — Validation Script (v2)
Fixed:
  - M1: rank column name mismatch (recommendation_rank vs rank_position)
  - M2: avg meals/user threshold too narrow
  - M3: added cross-table life-event propagation check
  - M4: added BMI↔diabetes lift check with realistic threshold
  - Added: Ramadan food realism check
  - Added: health_outcomes BMI drift check
  - Added: per-week meal cadence check

Usage:
    python validate.py
    python validate.py --data_dir data/
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd


def check(condition: bool, msg: str, fail_msg: str = None):
    if condition:
        print(f"  ✓ {msg}")
    else:
        print(f"  ✗ {fail_msg or msg}")


# ─────────────────────────────────────────────────────────────
# FILE-LEVEL VALIDATORS
# ─────────────────────────────────────────────────────────────

def validate_users(path: str):
    print("\n── users.csv ─────────────────────────────────")
    df = pd.read_csv(path)
    n = len(df)
    print(f"  Rows: {n:,}")

    check(n >= 1000, f"Row count OK: {n:,}")
    check(df["user_id"].nunique() == n, "All user_ids unique")
    check(df["age"].between(18, 80).all(), "All ages 18-80")
    check(df["bmi"].between(14, 46).all(), "All BMIs realistic")
    check(df["gender"].isin(["male", "female", "other"]).all(), "Gender values valid")

    veg_pct = df["is_vegetarian"].mean() * 100
    check(20 <= veg_pct <= 45, f"Vegetarian % realistic: {veg_pct:.1f}%")

    religion_dist = df["religion"].value_counts(normalize=True)
    check("hindu" in religion_dist.index,
          f"Hindu present: {religion_dist.get('hindu', 0)*100:.1f}%")
    check("muslim" in religion_dist.index,
          f"Muslim present: {religion_dist.get('muslim', 0)*100:.1f}%")

    region_dist = df["region"].value_counts(normalize=True)
    check(region_dist.get("north", 0) > 0.20,
          f"North region present: {region_dist.get('north', 0)*100:.1f}%")
    check(region_dist.get("south", 0) > 0.10,
          f"South region present: {region_dist.get('south', 0)*100:.1f}%")

    has_diabetes = df["conditions"].str.contains("type2_diabetes", na=False).mean() * 100
    check(5 <= has_diabetes <= 20, f"Diabetes prevalence realistic: {has_diabetes:.1f}%")

    has_hypertension = df["conditions"].str.contains("hypertension", na=False).mean() * 100
    check(5 <= has_hypertension <= 30,
          f"Hypertension prevalence realistic: {has_hypertension:.1f}%")

    persona_dist = df["persona_type"].value_counts()
    check(len(persona_dist) > 5, f"Persona diversity: {len(persona_dist)} types")

    print(f"\n  Region distribution:")
    for region, pct in region_dist.items():
        print(f"    {region:<15} {pct*100:.1f}%")

    print(f"\n  Income tier:")
    for tier, pct in df["income_tier"].value_counts(normalize=True).items():
        print(f"    {tier:<15} {pct*100:.1f}%")

    return df


def validate_meal_logs(path: str, users_df: pd.DataFrame):
    print("\n── meal_logs.csv ─────────────────────────────")
    df = pd.read_csv(path, parse_dates=["occurred_at"])
    n = len(df)
    print(f"  Rows: {n:,}")

    check(n >= 100000, f"Row count OK: {n:,}")
    check(df["user_id"].nunique() > 100, f"Multiple users: {df['user_id'].nunique():,}")

    avg_meals_per_user = n / df["user_id"].nunique()
    # FIX M2: raised upper bound from 500 → 1500; 365 days × 3 meals = 1095
    check(20 <= avg_meals_per_user <= 1500,
          f"Avg meals/user: {avg_meals_per_user:.0f}")

    # FIX M2: add per-week check which is more meaningful
    date_span_days = (df["occurred_at"].max() - df["occurred_at"].min()).days
    date_span_weeks = max(1, date_span_days / 7)
    meals_per_user_per_week = avg_meals_per_user / date_span_weeks
    check(10 <= meals_per_user_per_week <= 30,
          f"Meals/user/week: {meals_per_user_per_week:.1f} (expect 14-28)",
          f"Meals/user/week out of range: {meals_per_user_per_week:.1f}")

    occasion_dist = df["meal_occasion"].value_counts(normalize=True)
    check("breakfast" in occasion_dist.index,
          f"Breakfast present: {occasion_dist.get('breakfast', 0)*100:.1f}%")
    check("lunch" in occasion_dist.index,
          f"Lunch present: {occasion_dist.get('lunch', 0)*100:.1f}%")
    check("dinner" in occasion_dist.index,
          f"Dinner present: {occasion_dist.get('dinner', 0)*100:.1f}%")

    avg_cal = df["estimated_calories"].mean()
    check(150 <= avg_cal <= 600, f"Avg calories per meal: {avg_cal:.0f} kcal")

    avg_gi = df["gi_score"].mean()
    check(30 <= avg_gi <= 75, f"Avg GI score: {avg_gi:.1f}")

    season_dist = df["season"].value_counts(normalize=True)
    check(len(season_dist) >= 4, f"Season diversity: {list(season_dist.index)}")

    festival_pct = df["is_festival_day"].mean() * 100
    check(2 <= festival_pct <= 20, f"Festival day %: {festival_pct:.1f}%")

    fast_pct = df["is_fast_day"].mean() * 100
    check(fast_pct <= 15, f"Fast day %: {fast_pct:.1f}%")

    compliance = df["health_compliant"].mean() * 100
    check(40 <= compliance <= 90, f"Health compliance: {compliance:.1f}%")

    dish_diversity = df["dish_name"].nunique()
    check(dish_diversity >= 30, f"Dish diversity: {dish_diversity} unique dishes")

    print(f"\n  Top 10 dishes:")
    for dish, cnt in df["dish_name"].value_counts().head(10).items():
        pct = cnt / n * 100
        print(f"    {dish:<35} {cnt:>8,} ({pct:.1f}%)")

    print(f"\n  Occasion distribution:")
    for occ, pct in occasion_dist.items():
        print(f"    {occ:<20} {pct*100:.1f}%")

    return df


def validate_interactions(path: str):
    print("\n── interactions.csv ───────────────────────────")
    df = pd.read_csv(path)
    n = len(df)
    print(f"  Rows: {n:,}")

    check(n >= 10000, f"Row count OK: {n:,}")

    action_dist = df["action"].value_counts(normalize=True)
    check("skip" in action_dist.index,
          f"Skip actions: {action_dist.get('skip', 0)*100:.1f}%")
    check("click" in action_dist.index,
          f"Click actions: {action_dist.get('click', 0)*100:.1f}%")
    check("order" in action_dist.index,
          f"Order actions: {action_dist.get('order', 0)*100:.1f}%")

    click_rate = (action_dist.get("click", 0) + action_dist.get("order", 0)) * 100
    check(10 <= click_rate <= 60, f"Click rate realistic: {click_rate:.1f}%")

    order_rate = action_dist.get("order", 0) * 100
    check(1 <= order_rate <= 20, f"Order rate realistic: {order_rate:.1f}%")

    print(f"\n  Action distribution:")
    for action, pct in action_dist.items():
        print(f"    {action:<15} {pct*100:.1f}%")


def validate_life_events(path: str):
    print("\n── life_events.csv ────────────────────────────")
    df = pd.read_csv(path)
    n = len(df)
    print(f"  Rows: {n:,}")

    check(n > 0, f"Has records: {n:,}")

    event_dist = df["event_type"].value_counts()
    check(len(event_dist) >= 4, f"Event type diversity: {len(event_dist)} types")

    print(f"\n  Event type distribution:")
    for evt, cnt in event_dist.items():
        print(f"    {evt:<30} {cnt:>8,}")


# ─────────────────────────────────────────────────────────────
# CROSS-TABLE / REALISM VALIDATORS
# ─────────────────────────────────────────────────────────────

def validate_religious_consistency(fast_days_path):
    print("\n── Religious Consistency ─────────────────────")
    df = pd.read_csv(fast_days_path)
    required = ["religion", "fast_type"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"  ⚠ Missing columns: {missing}")
        return

    ramadan_non_muslims = df[
        (df["fast_type"].str.contains("ramadan", case=False, na=False)) &
        (df["religion"] != "muslim")
    ]
    check(len(ramadan_non_muslims) == 0,
          "Ramadan only assigned to Muslims",
          f"Found {len(ramadan_non_muslims)} Ramadan records for non-Muslims")

    navratri_muslims = df[
        (df["fast_type"].str.contains("navratri|ekadashi|monday_fast", case=False, na=False)) &
        (df["religion"] == "muslim")
    ]
    check(len(navratri_muslims) == 0,
          "Hindu fasts not assigned to Muslims",
          f"Found {len(navratri_muslims)} Hindu-fast records for Muslims")

    # FIX: check Ramadan post-fast meals aren't Hindu vrat foods
    if "post_fast_meal" in df.columns:
        hindu_vrat_foods = ["sabudana khichdi", "kuttu roti", "singhare ki puri"]
        ramadan_rows = df[df["fast_type"] == "ramadan"]
        bad_iftar = ramadan_rows[ramadan_rows["post_fast_meal"].isin(hindu_vrat_foods)]
        check(len(bad_iftar) == 0,
              "No Hindu vrat foods used as Ramadan iftar",
              f"Found {len(bad_iftar)} Ramadan rows with Hindu vrat foods as iftar: "
              f"{bad_iftar['post_fast_meal'].value_counts().to_dict()}")


def validate_health_correlations(users_path):
    print("\n── Health Correlations ───────────────────────")
    users = pd.read_csv(users_path)

    diabetic = users["conditions"].str.contains("type2_diabetes", na=False)
    obese = users["bmi"] >= 30

    if obese.sum() == 0 or (~obese).sum() == 0:
        print("  ⚠ Insufficient BMI variance to check correlation")
        return

    obese_rate = diabetic[obese].mean() * 100
    normal_rate = diabetic[~obese].mean() * 100
    lift = obese_rate / max(normal_rate, 0.001)

    print(f"  Diabetes rate (BMI >=30): {obese_rate:.1f}%")
    print(f"  Diabetes rate (BMI <30):  {normal_rate:.1f}%")
    print(f"  Lift: {lift:.2f}×")

    check(obese_rate > normal_rate,
          "Obesity increases diabetes prevalence")
    # FIX M4: realistic lift should be 2-4×, not just ">1"
    check(lift >= 2.0,
          f"BMI↔diabetes lift realistic (≥2×): {lift:.2f}×",
          f"BMI↔diabetes lift too weak: {lift:.2f}× (expect ≥2×, got only marginal separation)")

    # Hypertension ↔ BMI
    hypertensive = users["conditions"].str.contains("hypertension", na=False)
    hyp_obese = hypertensive[obese].mean() * 100
    hyp_normal = hypertensive[~obese].mean() * 100
    hyp_lift = hyp_obese / max(hyp_normal, 0.001)
    print(f"\n  Hypertension rate (BMI >=30): {hyp_obese:.1f}%")
    print(f"  Hypertension rate (BMI <30):  {hyp_normal:.1f}%")
    check(hyp_lift >= 1.5,
          f"BMI↔hypertension lift realistic (≥1.5×): {hyp_lift:.2f}×",
          f"BMI↔hypertension lift weak: {hyp_lift:.2f}×")


def validate_life_event_diversity(path):
    print("\n── Life Event Quality ────────────────────────")
    df = pd.read_csv(path)
    counts = df["event_type"].value_counts()
    print(counts)
    check(len(counts) >= 4, f"Good event diversity ({len(counts)} types)")
    check(counts.max() / counts.sum() < 0.8,
          "No single event dominates dataset")


# FIX M3: NEW cross-table check
def validate_life_event_propagation(life_events_path, weekly_context_path):
    print("\n── Life Event Propagation ────────────────────")
    try:
        ev = pd.read_csv(life_events_path, parse_dates=["event_date"])
        wc = pd.read_csv(weekly_context_path, parse_dates=["week_start_date"])
    except Exception as e:
        print(f"  ⚠ Could not load files: {e}")
        return

    # Check 1: gym start → protein increase
    gym_users = ev[ev["event_type"] == "started_gym"]["user_id"].unique()
    protein_deltas = []
    for uid in gym_users[:100]:
        u_wc = wc[wc["user_id"] == uid].sort_values("week_start_date")
        ev_dates = ev[(ev["user_id"] == uid) & (ev["event_type"] == "started_gym")]["event_date"]
        if ev_dates.empty or len(u_wc) < 4:
            continue
        ev_date = ev_dates.iloc[0]
        pre  = u_wc[u_wc["week_start_date"] <  ev_date]["avg_protein_g"].mean()
        post = u_wc[u_wc["week_start_date"] >= ev_date]["avg_protein_g"].mean()
        if not (np.isnan(pre) or np.isnan(post)):
            protein_deltas.append(post - pre)

    if protein_deltas:
        avg_delta = np.mean(protein_deltas)
        check(avg_delta > 1.0,
              f"Gym start → protein increase: +{avg_delta:.1f}g avg",
              f"Gym start has no protein effect: {avg_delta:.1f}g avg (should be >1g)")
    else:
        print("  ⚠ Not enough gym users with pre/post weekly data to check")

    # Check 2: financial_stress → budget_state decreases
    stress_users = ev[ev["event_type"] == "financial_stress"]["user_id"].unique()
    budget_deltas = []
    for uid in stress_users[:100]:
        u_wc = wc[wc["user_id"] == uid].sort_values("week_start_date")
        ev_dates = ev[(ev["user_id"] == uid) & (ev["event_type"] == "financial_stress")]["event_date"]
        if ev_dates.empty or len(u_wc) < 4:
            continue
        ev_date = ev_dates.iloc[0]
        pre  = u_wc[u_wc["week_start_date"] <  ev_date]["budget_state"].mean()
        post = u_wc[u_wc["week_start_date"] >= ev_date]["budget_state"].mean()
        if not (np.isnan(pre) or np.isnan(post)):
            budget_deltas.append(post - pre)

    if budget_deltas:
        avg_delta = np.mean(budget_deltas)
        check(avg_delta < 0,
              f"Financial stress → budget decrease: {avg_delta:.3f} avg",
              f"Financial stress has no budget effect: {avg_delta:.3f} (should be negative)")
    else:
        print("  ⚠ Not enough financial_stress users with pre/post data")

    # Check 3: life_event_phase column in meal_logs is not always "normal"
    # (requires meal_logs to be passed — optional)
    print("  ℹ Run with meal_logs for life_event_phase propagation check")


def validate_cuisine_diversity(meals_path):
    print("\n── Cuisine Diversity ─────────────────────────")
    df = pd.read_csv(meals_path)
    if "cuisine_type" not in df.columns:
        print("  ⚠ cuisine_type column not found")
        return

    top = df["cuisine_type"].value_counts(normalize=True).head(10)
    for cuisine, pct in top.items():
        print(f"  {cuisine:<25} {pct*100:.1f}%")

    check(top.iloc[0] < 0.50,
          "No single cuisine dominates excessively")


# FIX M1: correct column name
def validate_interaction_leakage(path):
    print("\n── Position Bias Check ───────────────────────")
    df = pd.read_csv(path)

    # FIX: try multiple possible column names
    rank_col = next(
        (c for c in ["recommendation_rank", "rank_position", "rank"] if c in df.columns),
        None
    )
    if rank_col is None:
        print(f"  ⚠ No rank column found. Columns: {list(df.columns[:10])}")
        return

    if "action" not in df.columns:
        print("  ⚠ action column not found")
        return

    df["ordered"] = (df["action"] == "order").astype(int)
    stats = df.groupby(rank_col)["ordered"].mean().sort_index()

    print(f"\n  Order rate by {rank_col}:")
    for rank, rate in stats.head(15).items():
        print(f"  Rank {rank:<2} → {rate*100:.1f}%")

    if len(stats) >= 2:
        first = stats.iloc[0]
        last = stats.iloc[-1]
        lift = first / max(last, 0.001)
        check(lift < 20, f"Position bias not extreme (rank-0/rank-N lift: {lift:.1f}×)")
        check(first > last,
              f"Top-ranked items have higher order rate: rank0={first*100:.1f}% > last={last*100:.1f}%",
              f"No position bias detected — may indicate rank signal is unused")


def validate_calorie_spikes(weekly_context_path):
    print("\n── Calorie Spike Check ───────────────────────")
    df = pd.read_csv(weekly_context_path)
    if "avg_calories" not in df.columns:
        print("  ⚠ avg_calories column missing")
        return

    avg = df["avg_calories"].mean()
    p99 = df["avg_calories"].quantile(0.99)
    p95 = df["avg_calories"].quantile(0.95)

    print(f"  Mean calories : {avg:.1f}")
    print(f"  P95 calories  : {p95:.1f}")
    print(f"  P99 calories  : {p99:.1f}")

    # tighter threshold: 2.5× catches Ramadan-level spikes
    check(p99 < avg * 3.5, "No extreme calorie explosions (P99 < 3.5× mean)")
    check(p95 < avg * 2.5,
          f"P95 within 2.5× mean: {p95/avg:.1f}×",
          f"P95 calorie spike suspicious: {p95/avg:.1f}× mean — check fasting logic")


def validate_festival_distribution(path):
    print("\n── Festival Distribution ─────────────────────")
    df = pd.read_csv(path)
    if "festival_name" not in df.columns:
        return

    festival_rows = df["festival_name"].notna() & (df["festival_name"] != "")
    pct = festival_rows.sum() / len(df) * 100
    print(f"  Festival rows: {pct:.1f}%")
    check(1 <= pct <= 20, f"Festival frequency realistic ({pct:.1f}%)")


# NEW: check health_outcomes for the hardcoded BMI bug
def validate_health_outcomes(path):
    print("\n── Health Outcomes Sanity ────────────────────")
    df = pd.read_csv(path)
    if "bmi_change" not in df.columns:
        print("  ⚠ bmi_change column not found")
        return

    # Bug C1: all bmi_change == -2.0
    unique_bmi_changes = df["bmi_change"].nunique()
    check(unique_bmi_changes > 10,
          f"BMI change has variance: {unique_bmi_changes} unique values",
          f"BMI change nearly constant: only {unique_bmi_changes} unique values — hardcoded?")

    # Check no user's BMI falls below 14
    if "current_bmi" in df.columns:
        below_14 = (df["current_bmi"] < 14).sum()
        check(below_14 == 0,
              "No user BMI falls below 14",
              f"{below_14} rows have current_bmi < 14 (physiologically impossible)")

        above_50 = (df["current_bmi"] > 50).sum()
        check(above_50 == 0,
              "No user BMI exceeds 50",
              f"{above_50} rows have current_bmi > 50")

    # Check compliance_improvement is not always (compliance - 0.5)
    if "compliance_improvement" in df.columns and "compliance_rate" in df.columns:
        derived = (df["compliance_rate"] - 0.5).round(3)
        is_formula = (df["compliance_improvement"].round(3) == derived).mean()
        check(is_formula < 0.95,
              f"compliance_improvement is a real delta (not compliance-0.5)",
              f"compliance_improvement = compliance_rate - 0.5 in {is_formula*100:.0f}% of rows — hardcoded formula")

    # Check health_trend has variance
    if "health_trend" in df.columns:
        trend_dist = df["health_trend"].value_counts(normalize=True)
        all_stable = trend_dist.get("stable", 0)
        check(all_stable < 0.95,
              f"health_trend has variance: {trend_dist.to_dict()}",
              f"health_trend is 'stable' for {all_stable*100:.0f}% of rows — no dynamics")

    print(f"\n  BMI change distribution:")
    print(f"    mean={df['bmi_change'].mean():.3f}  "
          f"std={df['bmi_change'].std():.3f}  "
          f"min={df['bmi_change'].min():.2f}  "
          f"max={df['bmi_change'].max():.2f}")


# ─────────────────────────────────────────────────────────────
# MASTER RUNNER
# ─────────────────────────────────────────────────────────────

def validate_all(data_dir: str = "data"):
    print("=" * 60)
    print("  NARA Synthetic Data Validation v2")
    print("=" * 60)

    files = {
        "users":           os.path.join(data_dir, "users.csv"),
        "meal_logs":       os.path.join(data_dir, "meal_logs.csv"),
        "interactions":    os.path.join(data_dir, "interactions.csv"),
        "life_events":     os.path.join(data_dir, "life_events.csv"),
        "fast_days":       os.path.join(data_dir, "fast_days.csv"),
        "skip_events":     os.path.join(data_dir, "skip_events.csv"),
        "reorders":        os.path.join(data_dir, "reorder_events.csv"),
        "health_outcomes": os.path.join(data_dir, "health_outcomes.csv"),
        "weekly_context":  os.path.join(data_dir, "user_weekly_context.csv"),
        "social_context":  os.path.join(data_dir, "social_eating_context.csv"),
    }

    print("\n── File existence check ───────────────────────")
    all_exist = True
    for name, path in files.items():
        exists = os.path.exists(path)
        size_mb = os.path.getsize(path) / (1024 * 1024) if exists else 0
        check(exists, f"{name:<25} {size_mb:.1f} MB", f"{name} MISSING")
        if not exists:
            all_exist = False

    if not all_exist:
        print("\n  Some files missing. Run run_all.py first.")
        return

    users_df = validate_users(files["users"])
    validate_meal_logs(files["meal_logs"], users_df)
    validate_interactions(files["interactions"])
    validate_life_events(files["life_events"])

    for name in ["fast_days", "skip_events", "reorders"]:
        path = files[name]
        df = pd.read_csv(path)
        print(f"\n── {name}.csv → {len(df):,} rows ✓")

    # Cross-table and realism checks
    validate_religious_consistency(files["fast_days"])
    validate_health_correlations(files["users"])
    validate_life_event_diversity(files["life_events"])

    # FIX M3: life event propagation
    validate_life_event_propagation(files["life_events"], files["weekly_context"])

    validate_cuisine_diversity(files["meal_logs"])

    # FIX M1: correct column name handling
    validate_interaction_leakage(files["interactions"])

    validate_calorie_spikes(files["weekly_context"])
    validate_festival_distribution(files["weekly_context"])

    # NEW: health outcomes sanity (catches C1 BMI bug)
    validate_health_outcomes(files["health_outcomes"])

    print("\n" + "=" * 60)
    print("  Validation complete.")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="data")
    args = parser.parse_args()
    validate_all(args.data_dir)