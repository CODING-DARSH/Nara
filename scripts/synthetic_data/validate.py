# """
# NARA Synthetic Data — Validation Script (v2)
# Fixed:
#   - M1: rank column name mismatch (recommendation_rank vs rank_position)
#   - M2: avg meals/user threshold too narrow
#   - M3: added cross-table life-event propagation check
#   - M4: added BMI↔diabetes lift check with realistic threshold
#   - Added: Ramadan food realism check
#   - Added: health_outcomes BMI drift check
#   - Added: per-week meal cadence check

# Usage:
#     python validate.py
#     python validate.py --data_dir data/
# """
# import os
# import sys
# import argparse
# import numpy as np
# import pandas as pd


# def check(condition: bool, msg: str, fail_msg: str = None):
#     if condition:
#         print(f"  ✓ {msg}")
#     else:
#         print(f"  ✗ {fail_msg or msg}")


# # ─────────────────────────────────────────────────────────────
# # FILE-LEVEL VALIDATORS
# # ─────────────────────────────────────────────────────────────

# def validate_users(path: str):
#     print("\n── users.csv ─────────────────────────────────")
#     df = pd.read_csv(path)
#     n = len(df)
#     print(f"  Rows: {n:,}")

#     check(n >= 1000, f"Row count OK: {n:,}")
#     check(df["user_id"].nunique() == n, "All user_ids unique")
#     check(df["age"].between(18, 80).all(), "All ages 18-80")
#     check(df["bmi"].between(14, 46).all(), "All BMIs realistic")
#     check(df["gender"].isin(["male", "female", "other"]).all(), "Gender values valid")

#     veg_pct = df["is_vegetarian"].mean() * 100
#     check(20 <= veg_pct <= 45, f"Vegetarian % realistic: {veg_pct:.1f}%")

#     religion_dist = df["religion"].value_counts(normalize=True)
#     check("hindu" in religion_dist.index,
#           f"Hindu present: {religion_dist.get('hindu', 0)*100:.1f}%")
#     check("muslim" in religion_dist.index,
#           f"Muslim present: {religion_dist.get('muslim', 0)*100:.1f}%")

#     region_dist = df["region"].value_counts(normalize=True)
#     check(region_dist.get("north", 0) > 0.20,
#           f"North region present: {region_dist.get('north', 0)*100:.1f}%")
#     check(region_dist.get("south", 0) > 0.10,
#           f"South region present: {region_dist.get('south', 0)*100:.1f}%")

#     has_diabetes = df["conditions"].str.contains("type2_diabetes", na=False).mean() * 100
#     check(5 <= has_diabetes <= 20, f"Diabetes prevalence realistic: {has_diabetes:.1f}%")

#     has_hypertension = df["conditions"].str.contains("hypertension", na=False).mean() * 100
#     check(5 <= has_hypertension <= 30,
#           f"Hypertension prevalence realistic: {has_hypertension:.1f}%")

#     persona_dist = df["persona_type"].value_counts()
#     check(len(persona_dist) > 5, f"Persona diversity: {len(persona_dist)} types")

#     print(f"\n  Region distribution:")
#     for region, pct in region_dist.items():
#         print(f"    {region:<15} {pct*100:.1f}%")

#     print(f"\n  Income tier:")
#     for tier, pct in df["income_tier"].value_counts(normalize=True).items():
#         print(f"    {tier:<15} {pct*100:.1f}%")

#     return df


# def validate_meal_logs(path: str, users_df: pd.DataFrame):
#     print("\n── meal_logs.csv ─────────────────────────────")
#     df = pd.read_csv(path, parse_dates=["occurred_at"])
#     n = len(df)
#     print(f"  Rows: {n:,}")

#     check(n >= 100000, f"Row count OK: {n:,}")
#     check(df["user_id"].nunique() > 100, f"Multiple users: {df['user_id'].nunique():,}")

#     avg_meals_per_user = n / df["user_id"].nunique()
#     # FIX M2: raised upper bound from 500 → 1500; 365 days × 3 meals = 1095
#     check(20 <= avg_meals_per_user <= 1500,
#           f"Avg meals/user: {avg_meals_per_user:.0f}")

#     # FIX M2: add per-week check which is more meaningful
#     date_span_days = (df["occurred_at"].max() - df["occurred_at"].min()).days
#     date_span_weeks = max(1, date_span_days / 7)
#     meals_per_user_per_week = avg_meals_per_user / date_span_weeks
#     check(10 <= meals_per_user_per_week <= 30,
#           f"Meals/user/week: {meals_per_user_per_week:.1f} (expect 14-28)",
#           f"Meals/user/week out of range: {meals_per_user_per_week:.1f}")

#     occasion_dist = df["meal_occasion"].value_counts(normalize=True)
#     check("breakfast" in occasion_dist.index,
#           f"Breakfast present: {occasion_dist.get('breakfast', 0)*100:.1f}%")
#     check("lunch" in occasion_dist.index,
#           f"Lunch present: {occasion_dist.get('lunch', 0)*100:.1f}%")
#     check("dinner" in occasion_dist.index,
#           f"Dinner present: {occasion_dist.get('dinner', 0)*100:.1f}%")

#     avg_cal = df["estimated_calories"].mean()
#     check(150 <= avg_cal <= 600, f"Avg calories per meal: {avg_cal:.0f} kcal")

#     avg_gi = df["gi_score"].mean()
#     check(30 <= avg_gi <= 75, f"Avg GI score: {avg_gi:.1f}")

#     season_dist = df["season"].value_counts(normalize=True)
#     check(len(season_dist) >= 4, f"Season diversity: {list(season_dist.index)}")

#     festival_pct = df["is_festival_day"].mean() * 100
#     check(2 <= festival_pct <= 20, f"Festival day %: {festival_pct:.1f}%")

#     fast_pct = df["is_fast_day"].mean() * 100
#     check(fast_pct <= 15, f"Fast day %: {fast_pct:.1f}%")

#     compliance = df["health_compliant"].mean() * 100
#     check(40 <= compliance <= 90, f"Health compliance: {compliance:.1f}%")

#     dish_diversity = df["dish_name"].nunique()
#     check(dish_diversity >= 30, f"Dish diversity: {dish_diversity} unique dishes")

#     print(f"\n  Top 10 dishes:")
#     for dish, cnt in df["dish_name"].value_counts().head(10).items():
#         pct = cnt / n * 100
#         print(f"    {dish:<35} {cnt:>8,} ({pct:.1f}%)")

#     print(f"\n  Occasion distribution:")
#     for occ, pct in occasion_dist.items():
#         print(f"    {occ:<20} {pct*100:.1f}%")

#     return df


# def validate_interactions(path: str):
#     print("\n── interactions.csv ───────────────────────────")
#     df = pd.read_csv(path)
#     n = len(df)
#     print(f"  Rows: {n:,}")

#     check(n >= 10000, f"Row count OK: {n:,}")

#     action_dist = df["action"].value_counts(normalize=True)
#     check("skip" in action_dist.index,
#           f"Skip actions: {action_dist.get('skip', 0)*100:.1f}%")
#     check("click" in action_dist.index,
#           f"Click actions: {action_dist.get('click', 0)*100:.1f}%")
#     check("order" in action_dist.index,
#           f"Order actions: {action_dist.get('order', 0)*100:.1f}%")

#     click_rate = (action_dist.get("click", 0) + action_dist.get("order", 0)) * 100
#     check(10 <= click_rate <= 60, f"Click rate realistic: {click_rate:.1f}%")

#     order_rate = action_dist.get("order", 0) * 100
#     check(1 <= order_rate <= 20, f"Order rate realistic: {order_rate:.1f}%")

#     print(f"\n  Action distribution:")
#     for action, pct in action_dist.items():
#         print(f"    {action:<15} {pct*100:.1f}%")


# def validate_life_events(path: str):
#     print("\n── life_events.csv ────────────────────────────")
#     df = pd.read_csv(path)
#     n = len(df)
#     print(f"  Rows: {n:,}")

#     check(n > 0, f"Has records: {n:,}")

#     event_dist = df["event_type"].value_counts()
#     check(len(event_dist) >= 4, f"Event type diversity: {len(event_dist)} types")

#     print(f"\n  Event type distribution:")
#     for evt, cnt in event_dist.items():
#         print(f"    {evt:<30} {cnt:>8,}")


# # ─────────────────────────────────────────────────────────────
# # CROSS-TABLE / REALISM VALIDATORS
# # ─────────────────────────────────────────────────────────────

# def validate_religious_consistency(fast_days_path):
#     print("\n── Religious Consistency ─────────────────────")
#     df = pd.read_csv(fast_days_path)
#     required = ["religion", "fast_type"]
#     missing = [c for c in required if c not in df.columns]
#     if missing:
#         print(f"  ⚠ Missing columns: {missing}")
#         return

#     ramadan_non_muslims = df[
#         (df["fast_type"].str.contains("ramadan", case=False, na=False)) &
#         (df["religion"] != "muslim")
#     ]
#     check(len(ramadan_non_muslims) == 0,
#           "Ramadan only assigned to Muslims",
#           f"Found {len(ramadan_non_muslims)} Ramadan records for non-Muslims")

#     navratri_muslims = df[
#         (df["fast_type"].str.contains("navratri|ekadashi|monday_fast", case=False, na=False)) &
#         (df["religion"] == "muslim")
#     ]
#     check(len(navratri_muslims) == 0,
#           "Hindu fasts not assigned to Muslims",
#           f"Found {len(navratri_muslims)} Hindu-fast records for Muslims")

#     # FIX: check Ramadan post-fast meals aren't Hindu vrat foods
#     if "post_fast_meal" in df.columns:
#         hindu_vrat_foods = ["sabudana khichdi", "kuttu roti", "singhare ki puri"]
#         ramadan_rows = df[df["fast_type"] == "ramadan"]
#         bad_iftar = ramadan_rows[ramadan_rows["post_fast_meal"].isin(hindu_vrat_foods)]
#         check(len(bad_iftar) == 0,
#               "No Hindu vrat foods used as Ramadan iftar",
#               f"Found {len(bad_iftar)} Ramadan rows with Hindu vrat foods as iftar: "
#               f"{bad_iftar['post_fast_meal'].value_counts().to_dict()}")


# def validate_health_correlations(users_path):
#     print("\n── Health Correlations ───────────────────────")
#     users = pd.read_csv(users_path)

#     diabetic = users["conditions"].str.contains("type2_diabetes", na=False)
#     obese = users["bmi"] >= 30

#     if obese.sum() == 0 or (~obese).sum() == 0:
#         print("  ⚠ Insufficient BMI variance to check correlation")
#         return

#     obese_rate = diabetic[obese].mean() * 100
#     normal_rate = diabetic[~obese].mean() * 100
#     lift = obese_rate / max(normal_rate, 0.001)

#     print(f"  Diabetes rate (BMI >=30): {obese_rate:.1f}%")
#     print(f"  Diabetes rate (BMI <30):  {normal_rate:.1f}%")
#     print(f"  Lift: {lift:.2f}×")

#     check(obese_rate > normal_rate,
#           "Obesity increases diabetes prevalence")
#     # FIX M4: realistic lift should be 2-4×, not just ">1"
#     check(lift >= 2.0,
#           f"BMI↔diabetes lift realistic (≥2×): {lift:.2f}×",
#           f"BMI↔diabetes lift too weak: {lift:.2f}× (expect ≥2×, got only marginal separation)")

#     # Hypertension ↔ BMI
#     hypertensive = users["conditions"].str.contains("hypertension", na=False)
#     hyp_obese = hypertensive[obese].mean() * 100
#     hyp_normal = hypertensive[~obese].mean() * 100
#     hyp_lift = hyp_obese / max(hyp_normal, 0.001)
#     print(f"\n  Hypertension rate (BMI >=30): {hyp_obese:.1f}%")
#     print(f"  Hypertension rate (BMI <30):  {hyp_normal:.1f}%")
#     check(hyp_lift >= 1.5,
#           f"BMI↔hypertension lift realistic (≥1.5×): {hyp_lift:.2f}×",
#           f"BMI↔hypertension lift weak: {hyp_lift:.2f}×")


# def validate_life_event_diversity(path):
#     print("\n── Life Event Quality ────────────────────────")
#     df = pd.read_csv(path)
#     counts = df["event_type"].value_counts()
#     print(counts)
#     check(len(counts) >= 4, f"Good event diversity ({len(counts)} types)")
#     check(counts.max() / counts.sum() < 0.8,
#           "No single event dominates dataset")


# # FIX M3: NEW cross-table check
# def validate_life_event_propagation(life_events_path, weekly_context_path):
#     print("\n── Life Event Propagation ────────────────────")
#     try:
#         ev = pd.read_csv(life_events_path, parse_dates=["event_date"])
#         wc = pd.read_csv(weekly_context_path, parse_dates=["week_start_date"])
#     except Exception as e:
#         print(f"  ⚠ Could not load files: {e}")
#         return

#     # Check 1: gym start → protein increase
#     gym_users = ev[ev["event_type"] == "started_gym"]["user_id"].unique()
#     protein_deltas = []
#     for uid in gym_users[:100]:
#         u_wc = wc[wc["user_id"] == uid].sort_values("week_start_date")
#         ev_dates = ev[(ev["user_id"] == uid) & (ev["event_type"] == "started_gym")]["event_date"]
#         if ev_dates.empty or len(u_wc) < 4:
#             continue
#         ev_date = ev_dates.iloc[0]
#         pre  = u_wc[u_wc["week_start_date"] <  ev_date]["avg_protein_g"].mean()
#         post = u_wc[u_wc["week_start_date"] >= ev_date]["avg_protein_g"].mean()
#         if not (np.isnan(pre) or np.isnan(post)):
#             protein_deltas.append(post - pre)

#     if protein_deltas:
#         avg_delta = np.mean(protein_deltas)
#         check(avg_delta > 1.0,
#               f"Gym start → protein increase: +{avg_delta:.1f}g avg",
#               f"Gym start has no protein effect: {avg_delta:.1f}g avg (should be >1g)")
#     else:
#         print("  ⚠ Not enough gym users with pre/post weekly data to check")

#     # Check 2: financial_stress → budget_state decreases
#     stress_users = ev[ev["event_type"] == "financial_stress"]["user_id"].unique()
#     budget_deltas = []
#     for uid in stress_users[:100]:
#         u_wc = wc[wc["user_id"] == uid].sort_values("week_start_date")
#         ev_dates = ev[(ev["user_id"] == uid) & (ev["event_type"] == "financial_stress")]["event_date"]
#         if ev_dates.empty or len(u_wc) < 4:
#             continue
#         ev_date = ev_dates.iloc[0]
#         pre  = u_wc[u_wc["week_start_date"] <  ev_date]["budget_state"].mean()
#         post = u_wc[u_wc["week_start_date"] >= ev_date]["budget_state"].mean()
#         if not (np.isnan(pre) or np.isnan(post)):
#             budget_deltas.append(post - pre)

#     if budget_deltas:
#         avg_delta = np.mean(budget_deltas)
#         check(avg_delta < 0,
#               f"Financial stress → budget decrease: {avg_delta:.3f} avg",
#               f"Financial stress has no budget effect: {avg_delta:.3f} (should be negative)")
#     else:
#         print("  ⚠ Not enough financial_stress users with pre/post data")

#     # Check 3: life_event_phase column in meal_logs is not always "normal"
#     # (requires meal_logs to be passed — optional)
#     print("  ℹ Run with meal_logs for life_event_phase propagation check")


# def validate_cuisine_diversity(meals_path):
#     print("\n── Cuisine Diversity ─────────────────────────")
#     df = pd.read_csv(meals_path)
#     if "cuisine_type" not in df.columns:
#         print("  ⚠ cuisine_type column not found")
#         return

#     top = df["cuisine_type"].value_counts(normalize=True).head(10)
#     for cuisine, pct in top.items():
#         print(f"  {cuisine:<25} {pct*100:.1f}%")

#     check(top.iloc[0] < 0.50,
#           "No single cuisine dominates excessively")


# # FIX M1: correct column name
# def validate_interaction_leakage(path):
#     print("\n── Position Bias Check ───────────────────────")
#     df = pd.read_csv(path)

#     # FIX: try multiple possible column names
#     rank_col = next(
#         (c for c in ["recommendation_rank", "rank_position", "rank"] if c in df.columns),
#         None
#     )
#     if rank_col is None:
#         print(f"  ⚠ No rank column found. Columns: {list(df.columns[:10])}")
#         return

#     if "action" not in df.columns:
#         print("  ⚠ action column not found")
#         return

#     df["ordered"] = (df["action"] == "order").astype(int)
#     stats = df.groupby(rank_col)["ordered"].mean().sort_index()

#     print(f"\n  Order rate by {rank_col}:")
#     for rank, rate in stats.head(15).items():
#         print(f"  Rank {rank:<2} → {rate*100:.1f}%")

#     if len(stats) >= 2:
#         first = stats.iloc[0]
#         last = stats.iloc[-1]
#         lift = first / max(last, 0.001)
#         check(lift < 20, f"Position bias not extreme (rank-0/rank-N lift: {lift:.1f}×)")
#         check(first > last,
#               f"Top-ranked items have higher order rate: rank0={first*100:.1f}% > last={last*100:.1f}%",
#               f"No position bias detected — may indicate rank signal is unused")


# def validate_calorie_spikes(weekly_context_path):
#     print("\n── Calorie Spike Check ───────────────────────")
#     df = pd.read_csv(weekly_context_path)
#     if "avg_calories" not in df.columns:
#         print("  ⚠ avg_calories column missing")
#         return

#     avg = df["avg_calories"].mean()
#     p99 = df["avg_calories"].quantile(0.99)
#     p95 = df["avg_calories"].quantile(0.95)

#     print(f"  Mean calories : {avg:.1f}")
#     print(f"  P95 calories  : {p95:.1f}")
#     print(f"  P99 calories  : {p99:.1f}")

#     # tighter threshold: 2.5× catches Ramadan-level spikes
#     check(p99 < avg * 3.5, "No extreme calorie explosions (P99 < 3.5× mean)")
#     check(p95 < avg * 2.5,
#           f"P95 within 2.5× mean: {p95/avg:.1f}×",
#           f"P95 calorie spike suspicious: {p95/avg:.1f}× mean — check fasting logic")


# def validate_festival_distribution(path):
#     print("\n── Festival Distribution ─────────────────────")
#     df = pd.read_csv(path)
#     if "festival_name" not in df.columns:
#         return

#     festival_rows = df["festival_name"].notna() & (df["festival_name"] != "")
#     pct = festival_rows.sum() / len(df) * 100
#     print(f"  Festival rows: {pct:.1f}%")
#     check(1 <= pct <= 20, f"Festival frequency realistic ({pct:.1f}%)")


# # NEW: check health_outcomes for the hardcoded BMI bug
# def validate_health_outcomes(path):
#     print("\n── Health Outcomes Sanity ────────────────────")
#     df = pd.read_csv(path)
#     if "bmi_change" not in df.columns:
#         print("  ⚠ bmi_change column not found")
#         return

#     # Bug C1: all bmi_change == -2.0
#     unique_bmi_changes = df["bmi_change"].nunique()
#     check(unique_bmi_changes > 10,
#           f"BMI change has variance: {unique_bmi_changes} unique values",
#           f"BMI change nearly constant: only {unique_bmi_changes} unique values — hardcoded?")

#     # Check no user's BMI falls below 14
#     if "current_bmi" in df.columns:
#         below_14 = (df["current_bmi"] < 14).sum()
#         check(below_14 == 0,
#               "No user BMI falls below 14",
#               f"{below_14} rows have current_bmi < 14 (physiologically impossible)")

#         above_50 = (df["current_bmi"] > 50).sum()
#         check(above_50 == 0,
#               "No user BMI exceeds 50",
#               f"{above_50} rows have current_bmi > 50")

#     # Check compliance_improvement is not always (compliance - 0.5)
#     if "compliance_improvement" in df.columns and "compliance_rate" in df.columns:
#         derived = (df["compliance_rate"] - 0.5).round(3)
#         is_formula = (df["compliance_improvement"].round(3) == derived).mean()
#         check(is_formula < 0.95,
#               f"compliance_improvement is a real delta (not compliance-0.5)",
#               f"compliance_improvement = compliance_rate - 0.5 in {is_formula*100:.0f}% of rows — hardcoded formula")

#     # Check health_trend has variance
#     if "health_trend" in df.columns:
#         trend_dist = df["health_trend"].value_counts(normalize=True)
#         all_stable = trend_dist.get("stable", 0)
#         check(all_stable < 0.95,
#               f"health_trend has variance: {trend_dist.to_dict()}",
#               f"health_trend is 'stable' for {all_stable*100:.0f}% of rows — no dynamics")

#     print(f"\n  BMI change distribution:")
#     print(f"    mean={df['bmi_change'].mean():.3f}  "
#           f"std={df['bmi_change'].std():.3f}  "
#           f"min={df['bmi_change'].min():.2f}  "
#           f"max={df['bmi_change'].max():.2f}")


# # ─────────────────────────────────────────────────────────────
# # MASTER RUNNER
# # ─────────────────────────────────────────────────────────────

# def validate_all(data_dir: str = "data"):
#     print("=" * 60)
#     print("  NARA Synthetic Data Validation v2")
#     print("=" * 60)

#     files = {
#         "users":           os.path.join(data_dir, "users.csv"),
#         "meal_logs":       os.path.join(data_dir, "meal_logs.csv"),
#         "interactions":    os.path.join(data_dir, "interactions.csv"),
#         "life_events":     os.path.join(data_dir, "life_events.csv"),
#         "fast_days":       os.path.join(data_dir, "fast_days.csv"),
#         "skip_events":     os.path.join(data_dir, "skip_events.csv"),
#         "reorders":        os.path.join(data_dir, "reorder_events.csv"),
#         "health_outcomes": os.path.join(data_dir, "health_outcomes.csv"),
#         "weekly_context":  os.path.join(data_dir, "user_weekly_context.csv"),
#         "social_context":  os.path.join(data_dir, "social_eating_context.csv"),
#     }

#     print("\n── File existence check ───────────────────────")
#     all_exist = True
#     for name, path in files.items():
#         exists = os.path.exists(path)
#         size_mb = os.path.getsize(path) / (1024 * 1024) if exists else 0
#         check(exists, f"{name:<25} {size_mb:.1f} MB", f"{name} MISSING")
#         if not exists:
#             all_exist = False

#     if not all_exist:
#         print("\n  Some files missing. Run run_all.py first.")
#         return

#     users_df = validate_users(files["users"])
#     validate_meal_logs(files["meal_logs"], users_df)
#     validate_interactions(files["interactions"])
#     validate_life_events(files["life_events"])

#     for name in ["fast_days", "skip_events", "reorders"]:
#         path = files[name]
#         df = pd.read_csv(path)
#         print(f"\n── {name}.csv → {len(df):,} rows ✓")

#     # Cross-table and realism checks
#     validate_religious_consistency(files["fast_days"])
#     validate_health_correlations(files["users"])
#     validate_life_event_diversity(files["life_events"])

#     # FIX M3: life event propagation
#     validate_life_event_propagation(files["life_events"], files["weekly_context"])

#     validate_cuisine_diversity(files["meal_logs"])

#     # FIX M1: correct column name handling
#     validate_interaction_leakage(files["interactions"])

#     validate_calorie_spikes(files["weekly_context"])
#     validate_festival_distribution(files["weekly_context"])

#     # NEW: health outcomes sanity (catches C1 BMI bug)
#     validate_health_outcomes(files["health_outcomes"])

#     print("\n" + "=" * 60)
#     print("  Validation complete.")
#     print("=" * 60)


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--data_dir", type=str, default="data")
#     args = parser.parse_args()
#     validate_all(args.data_dir)



"""
NARA Synthetic Data — Validation Script v3
Senior-level: row-level logic, cross-table causality, distribution shape,
temporal consistency, biological plausibility, cultural realism.

Usage:
    python validate_v3.py --data_dir data/
    python validate_v3.py --data_dir data/ --fast       # skip slow cross-table checks
    python validate_v3.py --data_dir data/ --section users
"""
import os
import sys
import argparse
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

PASS = 0
FAIL = 0
WARN = 0


def check(condition, msg, fail_msg=None, warn=False):
    global PASS, FAIL, WARN
    if condition:
        print(f"  ✓ {msg}")
        PASS += 1
    elif warn:
        print(f"  ⚠ {fail_msg or msg}")
        WARN += 1
    else:
        print(f"  ✗ {fail_msg or msg}")
        FAIL += 1


def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ══════════════════════════════════════════════════════════════
# 1. USERS — row-level biological and cultural plausibility
# ══════════════════════════════════════════════════════════════

def validate_users(path):
    section("users.csv — biological + cultural plausibility")
    df = pd.read_csv(path)
    n = len(df)
    print(f"  Rows: {n:,}")

    # ── Basic integrity ───────────────────────────────────────
    check(df["user_id"].nunique() == n, "All user_ids unique")
    check(df["age"].between(18, 80).all(), "All ages 18–80")
    check(df["bmi"].between(14, 46).all(), "All BMIs 14–46")
    check(df["gender"].isin(["male", "female", "other"]).all(), "Gender values valid")
    check(df["observance_level"].between(0, 1).all(), "Observance level 0–1")
    check(df["health_literacy"].between(0, 1).all(), "Health literacy 0–1")
    check(df["habit_strength"].between(0, 1).all(), "Habit strength 0–1")
    check(df["cooking_skill"].between(0, 1).all(), "Cooking skill 0–1")

    # ── BMI ↔ weight ↔ height consistency ────────────────────
    df["bmi_calc"] = df["weight_kg"] / (df["height_cm"] / 100) ** 2
    bmi_error = (df["bmi_calc"] - df["bmi"]).abs()
    check((bmi_error < 1.0).mean() > 0.95,
          "BMI = weight/height² consistent (>95% rows)",
          f"BMI inconsistent in {(bmi_error >= 1.0).sum()} rows — weight/height don't match bmi column")

    # ── BMI ranges by gender (biological) ────────────────────
    male_bmi = df[df["gender"] == "male"]["bmi"]
    female_bmi = df[df["gender"] == "female"]["bmi"]
    check(male_bmi.mean() < female_bmi.mean() + 2,
          f"Male BMI mean ({male_bmi.mean():.1f}) not implausibly higher than female ({female_bmi.mean():.1f})")

    # ── Obesity condition ↔ BMI hard gate ────────────────────
    obese_flag = df["conditions"].str.contains("obesity", na=False)
    obese_bmi = df[obese_flag]["bmi"]
    check((obese_bmi >= 28).mean() > 0.90,
          f"Obesity condition → BMI≥28 in >90% cases: {(obese_bmi >= 28).mean()*100:.1f}%",
          f"Obesity condition users have BMI<28 in {(obese_bmi < 28).sum()} rows — biological impossibility")

    non_obese_high_bmi = df[~obese_flag & (df["bmi"] >= 35)]
    check(len(non_obese_high_bmi) / n < 0.05,
          f"Users with BMI≥35 but no obesity condition: {len(non_obese_high_bmi)} ({len(non_obese_high_bmi)/n*100:.1f}%)",
          warn=True)

    # ── BMI ↔ diabetes lift (must be ≥2×) ────────────────────
    diabetic = df["conditions"].str.contains("type2_diabetes", na=False)
    obese = df["bmi"] >= 30
    if obese.sum() > 10 and (~obese).sum() > 10:
        obese_rate = diabetic[obese].mean()
        normal_rate = diabetic[~obese].mean()
        lift = obese_rate / max(normal_rate, 0.001)
        check(lift >= 2.0,
              f"BMI↔diabetes lift ≥2×: {lift:.2f}×",
              f"BMI↔diabetes lift too weak: {lift:.2f}× (need ≥2×). Fix BMI_RISK_WEIGHTS in constants.py")

    # ── BMI ↔ hypertension lift ───────────────────────────────
    hyp = df["conditions"].str.contains("hypertension", na=False)
    if obese.sum() > 10:
        hyp_obese = hyp[obese].mean()
        hyp_normal = hyp[~obese].mean()
        hyp_lift = hyp_obese / max(hyp_normal, 0.001)
        check(hyp_lift >= 1.5,
              f"BMI↔hypertension lift ≥1.5×: {hyp_lift:.2f}×",
              f"BMI↔hypertension lift weak: {hyp_lift:.2f}×")

    # ── Family history ↔ conditions correlation ───────────────
    has_diabetes_cond = df["conditions"].str.contains("type2_diabetes", na=False)
    has_diabetes_fh   = df["family_history"].str.contains("diabetes", na=False)
    fh_given_cond = has_diabetes_fh[has_diabetes_cond].mean()
    fh_given_no_cond = has_diabetes_fh[~has_diabetes_cond].mean()
    check(fh_given_cond > fh_given_no_cond * 1.5,
          f"Family history correlated with conditions: diabetes fh={fh_given_cond*100:.1f}% (with cond) vs {fh_given_no_cond*100:.1f}% (without)",
          f"Family history NOT correlated with conditions — still random sampling")

    # ── Jain religion → vegetarian ────────────────────────────
    jain_non_veg = df[(df["religion"] == "jain") & (~df["is_vegetarian"])]
    check(len(jain_non_veg) == 0,
          "All Jains are vegetarian",
          f"{len(jain_non_veg)} Jain users are non-vegetarian — impossible")

    # ── Muslim → halal dietary restriction ───────────────────
    muslim_no_halal = df[(df["religion"] == "muslim") & (~df["dietary_restrictions"].str.contains("halal", na=False))]
    check(len(muslim_no_halal) / max(df["religion"].eq("muslim").sum(), 1) < 0.05,
          "Muslim users have halal restriction (>95%)",
          f"{len(muslim_no_halal)} Muslim users missing halal restriction")

    # ── Age ↔ occupation logic ─────────────────────────────────
    retired_young = df[(df["occupation"] == "retired") & (df["age"] < 45)]
    check(len(retired_young) / n < 0.02,
          f"Retired users age≥45 (>98%): {len(retired_young)} young retirees",
          warn=True)

    student_old = df[(df["occupation"] == "student") & (df["age"] > 35)]
    check(len(student_old) / n < 0.03,
          f"Students age≤35 (>97%): {len(student_old)} old students",
          warn=True)

    # ── PCOS → female only ─────────────────────────────────────
    pcos_male = df[(df["conditions"].str.contains("pcos", na=False)) & (df["gender"] == "male")]
    check(len(pcos_male) == 0,
          "PCOS only assigned to female users",
          f"{len(pcos_male)} male users have PCOS — biological impossibility")

    # ── Pregnancy → female only ────────────────────────────────
    # (only checkable if pregnancy is in conditions — some datasets have it)
    if "pregnancy" in df.get("conditions", pd.Series()).str.cat():
        preg_male = df[(df["conditions"].str.contains("pregnancy", na=False)) & (df["gender"] == "male")]
        check(len(preg_male) == 0, "Pregnancy only for female users",
              f"{len(preg_male)} male users have pregnancy")

    # ── Living situation ↔ family size ─────────────────────────
    alone_big_family = df[(df["living_situation"] == "alone") & (df["family_size"] > 2)]
    check(len(alone_big_family) / n < 0.02,
          f"alone living_situation → family_size≤2: {len(alone_big_family)} violations",
          warn=True)

    # ── Income tier ↔ occupation consistency ─────────────────
    high_income_low_occ = df[(df["income_tier"] == "high") & (df["occupation"].isin(["daily_wage_worker", "field_worker"]))]
    check(len(high_income_low_occ) / n < 0.03,
          f"High income + low-wage occupation: {len(high_income_low_occ)} ({len(high_income_low_occ)/n*100:.1f}%)",
          warn=True)

    # ── Distribution checks ────────────────────────────────────
    veg_pct = df["is_vegetarian"].mean() * 100
    check(20 <= veg_pct <= 45, f"Vegetarian %: {veg_pct:.1f}% (expect 20–45%)")

    rel_dist = df["religion"].value_counts(normalize=True)
    check(rel_dist.get("hindu", 0) > 0.60, f"Hindu dominant: {rel_dist.get('hindu',0)*100:.1f}%")
    check(rel_dist.get("muslim", 0) > 0.10, f"Muslim present: {rel_dist.get('muslim',0)*100:.1f}%")

    region_dist = df["region"].value_counts(normalize=True)
    check(region_dist.get("north", 0) > 0.25, f"North region: {region_dist.get('north',0)*100:.1f}%")

    # ── Persona diversity ──────────────────────────────────────
    persona_dist = df["persona_type"].value_counts()
    check(len(persona_dist) > 5, f"Persona diversity: {len(persona_dist)} types")
    check(persona_dist.max() / n < 0.20, "No persona dominates >20% of users")

    print(f"\n  BMI distribution: mean={df['bmi'].mean():.1f} std={df['bmi'].std():.1f} "
          f"p10={df['bmi'].quantile(0.1):.1f} p90={df['bmi'].quantile(0.9):.1f}")
    print(f"  Age distribution: mean={df['age'].mean():.1f} std={df['age'].std():.1f}")

    return df


# ══════════════════════════════════════════════════════════════
# 2. MEAL LOGS — row-level temporal + nutritional + cultural
# ══════════════════════════════════════════════════════════════

def validate_meal_logs(path, users_df):
    section("meal_logs.csv — temporal + nutritional + cultural logic")
    df = pd.read_csv(path, parse_dates=["occurred_at"])
    n = len(df)
    print(f"  Rows: {n:,}")

    # ── Basic counts ──────────────────────────────────────────
    check(n >= 50000, f"Row count: {n:,}")
    check(df["user_id"].nunique() > 100, f"Unique users: {df['user_id'].nunique():,}")

    avg_per_user = n / df["user_id"].nunique()
    date_span = (df["occurred_at"].max() - df["occurred_at"].min()).days
    weeks = max(1, date_span / 7)
    per_week = avg_per_user / weeks
    check(10 <= per_week <= 30, f"Meals/user/week: {per_week:.1f} (expect 14–28)")

    # ── Timestamp logic ────────────────────────────────────────
    df["hour"] = df["occurred_at"].dt.hour
    df["dow"]  = df["occurred_at"].dt.dayofweek

    breakfast_hours = df[df["meal_occasion"] == "breakfast"]["hour"]
    check(breakfast_hours.between(4, 11).mean() > 0.90,
          f"Breakfast between 4–11am: {breakfast_hours.between(4,11).mean()*100:.1f}%",
          f"Breakfast timing wrong: {breakfast_hours.between(4,11).mean()*100:.1f}% in valid window")

    dinner_hours = df[df["meal_occasion"] == "dinner"]["hour"]
    check(dinner_hours.between(17, 23).mean() > 0.85,
          f"Dinner between 5–11pm: {dinner_hours.between(17,23).mean()*100:.1f}%",
          f"Dinner timing wrong: {dinner_hours.between(17,23).mean()*100:.1f}% in valid window")

    late_night_hours = df[df["meal_occasion"] == "late_night"]["hour"] if "late_night" in df["meal_occasion"].values else pd.Series([], dtype=float)
    if len(late_night_hours) > 0:
        check(late_night_hours.between(21, 23).mean() > 0.70,
              f"Late-night meals 9–11pm: {late_night_hours.between(21,23).mean()*100:.1f}%")

    # ── Duplicate meal check (same user, same timestamp) ──────
    dupes = df.duplicated(subset=["user_id", "occurred_at"])
    check(dupes.sum() == 0,
          "No duplicate (user, timestamp) pairs",
          f"{dupes.sum()} duplicate (user, timestamp) rows — meal_id collision")

    # ── Same-day meal ordering sanity ─────────────────────────
    # Breakfast should precede lunch should precede dinner
    occasion_order = {"breakfast": 0, "lunch": 1, "snack": 2, "dinner": 3, "late_night": 4}
    df["occ_order"] = df["meal_occasion"].map(occasion_order)
    df_sorted = df.sort_values(["user_id", "occurred_at"])
    df_sorted["date"] = df_sorted["occurred_at"].dt.date

    sample_days = df_sorted.groupby(["user_id", "date"]).filter(lambda x: len(x) >= 2)
    inversions = 0
    for _, day_meals in sample_days.head(50000).groupby(["user_id", "date"]):
        ordered = day_meals.sort_values("occurred_at")["occ_order"].tolist()
        for i in range(len(ordered) - 1):
            if ordered[i] > ordered[i+1]:
                inversions += 1
    check(inversions < 100,
          f"Meal occasion ordering within days: {inversions} inversions",
          f"Meal ordering issues: {inversions} days where dinner precedes lunch etc.")

    # ── Calorie plausibility per occasion ─────────────────────
    for occ, (lo, hi) in [("breakfast", (50, 600)), ("lunch", (100, 900)),
                           ("dinner", (100, 900)), ("snack", (30, 500))]:
        sub = df[df["meal_occasion"] == occ]["estimated_calories"]
        if len(sub) == 0:
            continue
        pct_valid = sub.between(lo, hi).mean()
        check(pct_valid > 0.90,
              f"{occ} calories in {lo}–{hi} kcal range: {pct_valid*100:.1f}%",
              f"{occ} has {(1-pct_valid)*100:.1f}% meals outside plausible calorie range")

    # ── GI score validity ─────────────────────────────────────
    check(df["gi_score"].between(0, 100).all(),
          "All GI scores 0–100",
          f"{(~df['gi_score'].between(0,100)).sum()} rows have GI outside 0–100")

    # ── Nutritional consistency: calories ≈ macro sum ─────────
    # 4 cal/g protein, 4 cal/g carbs, 9 cal/g fat
    df["macro_cal"] = (df["estimated_protein_g"] * 4 +
                       df["estimated_carbs_g"] * 4 +
                       df["estimated_fat_g"] * 9)
    macro_ratio = (df["macro_cal"] / df["estimated_calories"].replace(0, np.nan)).dropna()
    check(macro_ratio.between(0.5, 2.0).mean() > 0.85,
          f"Calorie ≈ macro sum (within 2×) in {macro_ratio.between(0.5,2.0).mean()*100:.1f}% rows",
          warn=True)

    # ── Portion multiplier range ───────────────────────────────
    check(df["portion_multiplier"].between(0.3, 3.0).all(),
          "Portion multipliers 0.3–3.0",
          f"{(~df['portion_multiplier'].between(0.3,3.0)).sum()} rows have extreme portion multipliers")

    # ── Vegetarian users eating non-veg dishes ────────────────
    if users_df is not None:
        veg_users = set(users_df[users_df["is_vegetarian"] == True]["user_id"])
        non_veg_dishes = {"chicken biryani","mutton biryani","butter chicken","chicken curry",
                          "chicken tikka","mutton curry","laal maas","machher jhol",
                          "egg curry","anda bhurji","tandoori chicken","rogan josh",
                          "shorshe ilish","chingri malai curry","kerala fish curry"}
        veg_eating_nonveg = df[(df["user_id"].isin(veg_users)) & (df["dish_name"].isin(non_veg_dishes))]
        check(len(veg_eating_nonveg) == 0,
              "No vegetarian users eating non-veg dishes",
              f"{len(veg_eating_nonveg)} rows: vegetarian users eating non-veg — fix get_restricted_dishes()")

    # ── Muslim users eating pork dishes ───────────────────────
    if users_df is not None:
        muslim_users = set(users_df[users_df["religion"] == "muslim"]["user_id"])
        pork_dishes = {"vindaloo", "pork curry", "bacon"}
        muslim_pork = df[(df["user_id"].isin(muslim_users)) & (df["dish_name"].isin(pork_dishes))]
        check(len(muslim_pork) == 0,
              "No Muslim users eating pork dishes",
              f"{len(muslim_pork)} rows: Muslim users eating pork")

    # ── Fast day food sanity ───────────────────────────────────
    if "is_fast_day" in df.columns:
        fast_meals = df[df["is_fast_day"] == True]
        if len(fast_meals) > 0:
            hindu_fast_forbidden = {"chicken biryani","butter chicken","mutton curry","egg curry"}
            bad_fast_meals = fast_meals[fast_meals["dish_name"].isin(hindu_fast_forbidden)]
            check(len(bad_fast_meals) / max(len(fast_meals), 1) < 0.02,
                  f"Fast day meals: non-fasting foods <2%: {len(bad_fast_meals)} rows",
                  f"Fast day meals contain non-fasting foods: {len(bad_fast_meals)} rows ({bad_fast_meals['dish_name'].value_counts().head(3).to_dict()})")

    # ── Season ↔ month consistency ────────────────────────────
    MONTH_SEASON = {1:"winter",2:"winter",3:"summer_onset",4:"summer",5:"summer",
                    6:"monsoon_onset",7:"monsoon",8:"monsoon",9:"monsoon_end",
                    10:"autumn",11:"winter_onset",12:"winter"}
    df["expected_season"] = df["occurred_at"].dt.month.map(MONTH_SEASON)
    season_mismatch = (df["season"] != df["expected_season"]).sum()
    check(season_mismatch / n < 0.01,
          f"Season matches month: {season_mismatch} mismatches",
          f"Season/month mismatch in {season_mismatch} rows ({season_mismatch/n*100:.1f}%)")

    # ── Day of week ↔ is_weekend consistency ──────────────────
    df["expected_weekend"] = df["dow"].isin([5, 6])
    weekend_mismatch = (df["is_weekend"] != df["expected_weekend"]).sum()
    check(weekend_mismatch == 0,
          "is_weekend matches day_of_week",
          f"is_weekend wrong in {weekend_mismatch} rows")

    # ── life_event_phase always 'normal' ──────────────────────
    if "life_event_phase" in df.columns:
        always_normal = (df["life_event_phase"] == "normal").mean()
        check(always_normal < 0.95,
              f"life_event_phase has non-normal values: {(1-always_normal)*100:.1f}%",
              f"life_event_phase is 'normal' in {always_normal*100:.1f}% rows — life events not propagated (C3 fix needed)")

    # ── Dish diversity ─────────────────────────────────────────
    top_dish_pct = df["dish_name"].value_counts(normalize=True).iloc[0] * 100
    check(top_dish_pct < 10,
          f"Top dish <10% of all meals: {df['dish_name'].value_counts().index[0]} at {top_dish_pct:.1f}%",
          f"Top dish dominates: {top_dish_pct:.1f}% — cuisine pool too narrow")

    check(df["dish_name"].nunique() >= 50, f"Dish diversity: {df['dish_name'].nunique()} unique dishes")

    # ── Cuisine type distribution ──────────────────────────────
    cuisine_top = df["cuisine_type"].value_counts(normalize=True).iloc[0]
    check(cuisine_top < 0.40, f"Top cuisine <40%: {cuisine_top*100:.1f}%",
          f"Cuisine dominates: {cuisine_top*100:.1f}%")

    # ── health_compliant ↔ conditions logic ───────────────────
    if users_df is not None and "health_compliant" in df.columns:
        diabetic_users = set(users_df[users_df["conditions"].str.contains("type2_diabetes", na=False)]["user_id"])
        diabetic_meals = df[df["user_id"].isin(diabetic_users)]
        if len(diabetic_meals) > 0:
            high_gi_compliant = diabetic_meals[(diabetic_meals["gi_score"] > 70) & (diabetic_meals["health_compliant"] == True)]
            check(len(high_gi_compliant) / len(diabetic_meals) < 0.05,
                  f"Diabetic users: high-GI meals not marked compliant (<5%): {len(high_gi_compliant)/len(diabetic_meals)*100:.1f}%",
                  f"Diabetic users: {len(high_gi_compliant)} high-GI meals marked health_compliant — logic error")

    print(f"\n  Occasion dist: {df['meal_occasion'].value_counts(normalize=True).round(3).to_dict()}")
    print(f"  Avg cal/meal: {df['estimated_calories'].mean():.0f}  "
          f"Avg protein: {df['estimated_protein_g'].mean():.1f}g  "
          f"Avg GI: {df['gi_score'].mean():.1f}")

    return df


# ══════════════════════════════════════════════════════════════
# 3. FAST DAYS — religion-food cultural correctness
# ══════════════════════════════════════════════════════════════

def validate_fast_days(path):
    section("fast_days.csv — religion ↔ food cultural correctness")
    df = pd.read_csv(path)
    n = len(df)
    print(f"  Rows: {n:,}")

    # ── Ramadan only Muslims ───────────────────────────────────
    ramadan_non_muslim = df[(df["fast_type"] == "ramadan") & (df["religion"] != "muslim")]
    check(len(ramadan_non_muslim) == 0,
          "Ramadan → Muslims only",
          f"{len(ramadan_non_muslim)} Ramadan records for non-Muslims")

    # ── Hindu fasts not for Muslims ───────────────────────────
    hindu_fasts = ["monday_fast", "ekadashi", "navratri"]
    hindu_fast_for_muslim = df[(df["fast_type"].isin(hindu_fasts)) & (df["religion"] == "muslim")]
    check(len(hindu_fast_for_muslim) == 0,
          "Hindu fasts → Hindus only",
          f"{len(hindu_fast_for_muslim)} Hindu fast records for Muslims")

    # ── Paryushan only Jains ──────────────────────────────────
    paryushan_non_jain = df[(df["fast_type"] == "paryushan") & (df["religion"] != "jain")]
    check(len(paryushan_non_jain) == 0,
          "Paryushan → Jains only",
          f"{len(paryushan_non_jain)} Paryushan records for non-Jains")

    # ── Hindu vrat foods in Ramadan iftar ────────────────────
    hindu_vrat = {"sabudana khichdi", "kuttu roti", "singhare ki puri", "sendha namak"}
    if "post_fast_meal" in df.columns:
        ramadan_rows = df[df["fast_type"] == "ramadan"]
        bad_iftar = ramadan_rows[ramadan_rows["post_fast_meal"].isin(hindu_vrat)]
        check(len(bad_iftar) == 0,
              "No Hindu vrat foods as Ramadan iftar",
              f"{len(bad_iftar)} Ramadan rows with Hindu vrat iftar foods: {bad_iftar['post_fast_meal'].value_counts().to_dict()}")

    # ── Pre-fast meal realism ─────────────────────────────────
    if "pre_fast_meal" in df.columns:
        ramadan_rows = df[df["fast_type"] == "ramadan"]
        good_sehri = {"roti", "paratha", "eggs", "dal tadka", "steamed rice", "dahi"}
        bad_sehri = ramadan_rows[~ramadan_rows["pre_fast_meal"].isin(good_sehri)]
        check(len(bad_sehri) / max(len(ramadan_rows), 1) < 0.30,
              f"Ramadan sehri foods realistic: {len(bad_sehri)/max(len(ramadan_rows),1)*100:.1f}% unrecognized",
              warn=True)

    # ── Calorie impact direction ───────────────────────────────
    if "calorie_impact" in df.columns:
        positive_impact = (df["calorie_impact"] > 0).sum()
        check(positive_impact == 0,
              "All fast day calorie impacts negative",
              f"{positive_impact} fast days have positive calorie impact — fasting should reduce calories")

    # ── Complete fast ↔ calorie impact ────────────────────────
    if "complete_fast" in df.columns and "calorie_impact" in df.columns:
        complete = df[df["complete_fast"] == True]["calorie_impact"]
        incomplete = df[df["complete_fast"] == False]["calorie_impact"]
        if len(complete) > 0 and len(incomplete) > 0:
            check(complete.mean() < incomplete.mean(),
                  f"Complete fast → bigger calorie reduction: {complete.mean():.2f} vs {incomplete.mean():.2f}",
                  f"Complete fast calorie impact not more negative than incomplete fast")

    # ── Observance level ↔ fasting frequency ─────────────────
    if "observance_level" in df.columns:
        check(df["observance_level"].between(0, 1).all(),
              "Observance level 0–1 in fast_days")

    print(f"  Fast type dist: {df['fast_type'].value_counts().to_dict()}")


# ══════════════════════════════════════════════════════════════
# 4. INTERACTIONS — position bias, click logic, signal quality
# ══════════════════════════════════════════════════════════════

def validate_interactions(path):
    section("interactions.csv — click logic + position bias + signal quality")
    df = pd.read_csv(path)
    n = len(df)
    print(f"  Rows: {n:,}")

    # ── Action distribution ────────────────────────────────────
    action_dist = df["action"].value_counts(normalize=True)
    check("skip" in action_dist and action_dist["skip"] > 0.40,
          f"Skip dominates >40%: {action_dist.get('skip',0)*100:.1f}%")
    check("order" in action_dist and 0.01 <= action_dist["order"] <= 0.20,
          f"Order rate 1–20%: {action_dist.get('order',0)*100:.1f}%")

    # ── Position bias: rank 0 should have highest order rate ──
    rank_col = next((c for c in ["recommendation_rank","rank_position","rank"] if c in df.columns), None)
    if rank_col:
        df["ordered"] = (df["action"] == "order").astype(int)
        stats = df.groupby(rank_col)["ordered"].mean().sort_index()
        if len(stats) >= 3:
            # Rank 0 should be higher than rank 3+
            rank0 = stats.iloc[0]
            rank3 = stats.iloc[3] if len(stats) > 3 else stats.iloc[-1]
            check(rank0 > rank3,
                  f"Position bias: rank-0 order rate ({rank0*100:.1f}%) > rank-3 ({rank3*100:.1f}%)",
                  f"No position bias — rank-0={rank0*100:.1f}% ≤ rank-3={rank3*100:.1f}%")
            lift = rank0 / max(stats.iloc[-1], 0.001)
            check(3 < lift < 25,
                  f"Position bias lift in realistic range 3–25×: {lift:.1f}×",
                  f"Position bias lift {lift:.1f}× — {'too extreme' if lift >= 25 else 'too weak, no signal'}")

    # ── final_ordered ↔ action consistency ───────────────────
    if "final_ordered" in df.columns:
        action_order = df[df["action"] == "order"]["final_ordered"]
        check(action_order.mean() > 0.95,
              f"action=order → final_ordered=True: {action_order.mean()*100:.1f}%",
              f"action=order but final_ordered=False in {(~action_order).sum()} rows — inconsistency")

        skip_order = df[df["action"] == "skip"]["final_ordered"]
        check(skip_order.mean() < 0.05,
              f"action=skip → final_ordered=False: {(~skip_order).mean()*100:.1f}%",
              f"action=skip but final_ordered=True in {skip_order.sum()} rows — inconsistency")

    # ── was_top3 ↔ recommendation_rank consistency ────────────
    if "was_top3" in df.columns and rank_col:
        top3_check = df[(df[rank_col] < 3) & (~df["was_top3"])].shape[0]
        not_top3_check = df[(df[rank_col] >= 3) & (df["was_top3"])].shape[0]
        check(top3_check == 0 and not_top3_check == 0,
              "was_top3 consistent with recommendation_rank",
              f"was_top3 inconsistent: {top3_check + not_top3_check} rows wrong")

    # ── Session duration: clicks > skips ─────────────────────
    if "session_duration_sec" in df.columns:
        click_dur = df[df["action"] == "click"]["session_duration_sec"].mean()
        skip_dur = df[df["action"] == "skip"]["session_duration_sec"].mean()
        order_dur = df[df["action"] == "order"]["session_duration_sec"].mean()
        check(order_dur > click_dur > skip_dur,
              f"Session duration: order({order_dur:.0f}s) > click({click_dur:.0f}s) > skip({skip_dur:.0f}s)",
              f"Session duration order wrong: order={order_dur:.0f}s click={click_dur:.0f}s skip={skip_dur:.0f}s")

    # ── Vegetarian users not ordering non-veg ────────────────
    # Can't check without users_df here — done in cross-table

    # ── user_health_match / price_match_score range ───────────
    for col in ["user_health_match", "price_match_score", "cuisine_affinity"]:
        if col in df.columns:
            check(df[col].between(0, 1).all(),
                  f"{col} in [0,1]",
                  f"{(~df[col].between(0,1)).sum()} rows have {col} outside [0,1]")

    print(f"  Rank 0 order rate: {df[df[rank_col]==0]['ordered'].mean()*100:.1f}%" if rank_col else "")


# ══════════════════════════════════════════════════════════════
# 5. HEALTH OUTCOMES — BMI physics, compliance delta, trend
# ══════════════════════════════════════════════════════════════

def validate_health_outcomes(path, users_df=None):
    section("health_outcomes.csv — BMI physics + compliance reality")
    df = pd.read_csv(path)
    n = len(df)
    print(f"  Rows: {n:,}")

    # ── BMI change variance ───────────────────────────────────
    unique_bmi = df["bmi_change"].nunique()
    check(unique_bmi > 20,
          f"BMI change has variance: {unique_bmi} unique values",
          f"BMI change has only {unique_bmi} unique values — likely hardcoded constant")

    bmi_std = df["bmi_change"].std()
    check(bmi_std > 0.3,
          f"BMI change std dev: {bmi_std:.3f} (expect >0.3)",
          f"BMI change std={bmi_std:.3f} — too uniform, not realistic")

    # ── BMI change range ──────────────────────────────────────
    check(df["bmi_change"].between(-3, 3).mean() > 0.95,
          f"BMI change in [-3, +3] per quarter: {df['bmi_change'].between(-3,3).mean()*100:.1f}%")

    # ── current_bmi physiologically possible ─────────────────
    if "current_bmi" in df.columns:
        check((df["current_bmi"] < 14).sum() == 0,
              "No current_bmi < 14 (physiologically impossible)",
              f"{(df['current_bmi'] < 14).sum()} rows have current_bmi < 14")
        check((df["current_bmi"] > 55).sum() == 0,
              "No current_bmi > 55",
              f"{(df['current_bmi'] > 55).sum()} rows have current_bmi > 55")

    # ── BMI trajectory per user ───────────────────────────────
    if "current_bmi" in df.columns:
        user_bmi = df.groupby("user_id")["current_bmi"]
        extreme_drop = user_bmi.apply(lambda x: x.max() - x.min() > 15)
        check(extreme_drop.sum() == 0,
              "No user loses/gains >15 BMI points across quarters",
              f"{extreme_drop.sum()} users have >15 BMI point swings — unrealistic trajectory")

    # ── Compliance improvement is actual delta ────────────────
    if "compliance_improvement" in df.columns and "compliance_rate" in df.columns:
        derived = (df["compliance_rate"] - 0.5).round(3)
        formula_match = (df["compliance_improvement"].round(3) == derived).mean()
        check(formula_match < 0.90,
              f"compliance_improvement is real delta (not compliance-0.5): {formula_match*100:.0f}% formula match",
              f"compliance_improvement = compliance_rate - 0.5 in {formula_match*100:.0f}% rows — hardcoded formula, fix compute_compliance_improvement()")

    # ── Health trend variance ─────────────────────────────────
    if "health_trend" in df.columns:
        trend_dist = df["health_trend"].value_counts(normalize=True)
        stable_pct = trend_dist.get("stable", 0)
        check(stable_pct < 0.95,
              f"health_trend not always stable: stable={stable_pct*100:.1f}%",
              f"health_trend='stable' for {stable_pct*100:.1f}% — no dynamics modelled")

    # ── Condition severity change makes sense ─────────────────
    if "condition_severity_change" in df.columns:
        all_zero = (df["condition_severity_change"] == 0).mean()
        check(all_zero < 0.80,
              f"condition_severity_change has variation: {all_zero*100:.1f}% are zero",
              f"condition_severity_change is 0 for {all_zero*100:.1f}% rows — not tracking condition changes")

    print(f"  BMI change: mean={df['bmi_change'].mean():.3f} "
          f"std={df['bmi_change'].std():.3f} "
          f"min={df['bmi_change'].min():.2f} max={df['bmi_change'].max():.2f}")


# ══════════════════════════════════════════════════════════════
# 6. REORDER EVENTS — semantic consistency
# ══════════════════════════════════════════════════════════════

def validate_reorders(path):
    section("reorder_events.csv — semantic consistency")
    df = pd.read_csv(path)
    n = len(df)
    print(f"  Rows: {n:,}")

    # ── days_between ≥ 0 ──────────────────────────────────────
    check((df["days_between"] >= 0).all(),
          "days_between ≥ 0",
          f"{(df['days_between'] < 0).sum()} rows have negative days_between")

    # ── total_orders_dish increases monotonically per user+dish
    df_sorted = df.sort_values(["user_id", "dish_name", "reorder_date"])
    non_mono = 0
    for (uid, dish), grp in df_sorted.groupby(["user_id", "dish_name"]):
        counts = grp["total_orders_dish"].tolist()
        for i in range(len(counts) - 1):
            if counts[i] > counts[i+1]:
                non_mono += 1
                break
    check(non_mono == 0,
          "total_orders_dish monotonically increases per user+dish",
          f"{non_mono} user+dish combos have non-monotonic order counts")

    # ── reorder_again_prob logic: more orders → higher prob ───
    df["reorder_bin"] = pd.cut(df["total_orders_dish"], bins=[0,2,5,10,100], labels=["1-2","3-5","6-10","10+"])
    reorder_by_orders = df.groupby("reorder_bin", observed=True)["reordered_yes_no"].mean()
    if len(reorder_by_orders) >= 2:
        check(reorder_by_orders.iloc[-1] >= reorder_by_orders.iloc[0],
              f"More orders → higher reorder probability: {reorder_by_orders.to_dict()}",
              f"Reorder probability not increasing with order count — formula broken")

    # ── Rating proxy 3–5 ─────────────────────────────────────
    if "last_rating_proxy" in df.columns:
        check(df["last_rating_proxy"].between(1, 5).all(),
              "Rating proxy in [1, 5]",
              f"{(~df['last_rating_proxy'].between(1,5)).sum()} rows have rating outside [1,5]")

    print(f"  Reorder rate: {df['reordered_yes_no'].mean()*100:.1f}%")
    print(f"  Avg days between orders: {df['days_between'].mean():.1f}")


# ══════════════════════════════════════════════════════════════
# 7. SKIP EVENTS — compensatory logic
# ══════════════════════════════════════════════════════════════

def validate_skip_events(path):
    section("skip_events.csv — compensatory meal logic")
    df = pd.read_csv(path)
    n = len(df)
    print(f"  Rows: {n:,}")

    # ── Compensatory only for breakfast skips ─────────────────
    dinner_comp = df[(df["skipped_meal_occasion"] == "dinner") & (df["compensatory_meal_occurred"] == True)]
    check(len(dinner_comp) / max(n, 1) < 0.05,
          f"Dinner skips rarely have compensatory meals: {len(dinner_comp)/n*100:.1f}%",
          warn=True)

    # ── Skip reason plausibility per occasion ─────────────────
    breakfast_reasons = df[df["skipped_meal_occasion"] == "breakfast"]["skip_reason"].value_counts()
    valid_breakfast_reasons = {"running_late", "not_hungry", "meeting", "fasting", "forgot"}
    invalid = set(breakfast_reasons.index) - valid_breakfast_reasons
    check(len(invalid) == 0,
          f"Breakfast skip reasons valid: {set(breakfast_reasons.index)}",
          f"Invalid breakfast skip reasons: {invalid}", warn=True)

    # ── Compensatory calorie increase direction ───────────────
    if "compensatory_calorie_increase" in df.columns:
        comp_meals = df[df["compensatory_meal_occurred"] == True]
        if len(comp_meals) > 0:
            # Some should be positive (ate more at lunch), some negative
            positive_pct = (comp_meals["compensatory_calorie_increase"] > 0).mean()
            check(0.1 <= positive_pct <= 0.9,
                  f"Compensatory calorie increase has variance: {positive_pct*100:.1f}% positive",
                  warn=True)

    print(f"  Skip occasion dist: {df['skipped_meal_occasion'].value_counts().to_dict()}")


# ══════════════════════════════════════════════════════════════
# 8. LIFE EVENTS ↔ WEEKLY CONTEXT — causal propagation
# ══════════════════════════════════════════════════════════════

def validate_life_event_propagation(events_path, weekly_path):
    section("life_events ↔ weekly_context — causal propagation")
    ev = pd.read_csv(events_path, parse_dates=["event_date"])
    wc = pd.read_csv(weekly_path, parse_dates=["week_start_date"])

    def get_pre_post(ev_df, wc_df, event_type, metric):
        users = ev_df[ev_df["event_type"] == event_type]["user_id"].unique()
        deltas = []
        for uid in users[:200]:
            u_wc = wc_df[wc_df["user_id"] == uid].sort_values("week_start_date")
            ev_dates = ev_df[(ev_df["user_id"] == uid) & (ev_df["event_type"] == event_type)]["event_date"]
            if ev_dates.empty or len(u_wc) < 4:
                continue
            ev_date = ev_dates.iloc[0]
            pre  = u_wc[u_wc["week_start_date"] <  ev_date][metric].mean()
            post = u_wc[u_wc["week_start_date"] >= ev_date][metric].mean()
            if not (np.isnan(pre) or np.isnan(post)):
                deltas.append(post - pre)
        return np.mean(deltas) if deltas else None

    # gym → protein up
    gym_protein = get_pre_post(ev, wc, "started_gym", "avg_protein_g")
    if gym_protein is not None:
        check(gym_protein > 1.0,
              f"started_gym → protein increase: +{gym_protein:.1f}g avg",
              f"started_gym has no protein effect: {gym_protein:.1f}g (C3 fix needed — life events not propagated to meal generator)")
    else:
        print("  ⚠ Not enough gym users with pre/post weekly data")

    # financial_stress → budget down
    fs_budget = get_pre_post(ev, wc, "financial_stress", "budget_state")
    if fs_budget is not None:
        check(fs_budget < 0,
              f"financial_stress → budget decrease: {fs_budget:.3f}",
              f"financial_stress has no budget effect: {fs_budget:.3f} (C3 fix needed)")
    else:
        print("  ⚠ Not enough financial_stress users with pre/post data")

    # health_diagnosis → compliance up
    hd_compliance = get_pre_post(ev, wc, "health_diagnosis", "health_compliance_rate")
    if hd_compliance is not None:
        check(hd_compliance > 0.02,
              f"health_diagnosis → compliance increase: +{hd_compliance:.3f}",
              f"health_diagnosis has no compliance effect: {hd_compliance:.3f} (C3 fix needed)")
    else:
        print("  ⚠ Not enough health_diagnosis users with pre/post data")

    # Event diversity
    event_dist = ev["event_type"].value_counts()
    check(len(event_dist) >= 5, f"Event type diversity: {len(event_dist)}")
    check(event_dist.max() / event_dist.sum() < 0.40,
          "No single event type dominates >40%")


# ══════════════════════════════════════════════════════════════
# 9. WEEKLY CONTEXT — calorie spikes, nutritional gaps, trend
# ══════════════════════════════════════════════════════════════

def validate_weekly_context(path):
    section("user_weekly_context.csv — calorie spikes + nutritional gaps")
    df = pd.read_csv(path, parse_dates=["week_start_date"])
    n = len(df)
    print(f"  Rows: {n:,}")

    # ── Calorie spike check ───────────────────────────────────
    avg_cal = df["avg_calories"].mean()
    p95 = df["avg_calories"].quantile(0.95)
    p99 = df["avg_calories"].quantile(0.99)
    check(p99 < avg_cal * 3.5, f"No calorie explosions (P99={p99:.0f} < {avg_cal*3.5:.0f})")
    check(p95 < avg_cal * 2.5,
          f"P95 calories within 2.5× mean: {p95/avg_cal:.1f}×",
          f"P95 calorie spike: {p95/avg_cal:.1f}× mean — check Ramadan logic")

    # ── Nutritional gaps must be ≥ 0 ─────────────────────────
    for col in ["protein_gap_g", "carb_gap_g", "fat_gap_g", "fiber_gap_g"]:
        if col in df.columns:
            neg = (df[col] < 0).sum()
            check(neg == 0, f"{col} ≥ 0", f"{neg} rows have negative {col}")

    # ── Budget state in valid range ───────────────────────────
    if "budget_state" in df.columns:
        check(df["budget_state"].between(0.5, 1.6).mean() > 0.95,
              f"budget_state in realistic range [0.5, 1.6]")

    # ── Season ↔ week_start_date consistency ──────────────────
    MONTH_SEASON = {1:"winter",2:"winter",3:"summer_onset",4:"summer",5:"summer",
                    6:"monsoon_onset",7:"monsoon",8:"monsoon",9:"monsoon_end",
                    10:"autumn",11:"winter_onset",12:"winter"}
    df["expected_season"] = df["week_start_date"].dt.month.map(MONTH_SEASON)
    season_mismatch = (df["season"] != df["expected_season"]).sum()
    check(season_mismatch / n < 0.02,
          f"Season matches month in weekly context: {season_mismatch} mismatches")

    # ── compliance rate [0, 1] ────────────────────────────────
    if "health_compliance_rate" in df.columns:
        check(df["health_compliance_rate"].between(0, 1).all(),
              "health_compliance_rate in [0,1]",
              f"{(~df['health_compliance_rate'].between(0,1)).sum()} rows outside [0,1]")

    # ── meals_ordered + meals_cooked ≤ meals_logged ───────────
    if all(c in df.columns for c in ["meals_logged", "meals_ordered", "meals_cooked"]):
        total_acc = df["meals_ordered"] + df["meals_cooked"]
        over = (total_acc > df["meals_logged"] + 2).sum()
        check(over / n < 0.05,
              f"meals_ordered + meals_cooked ≤ meals_logged in {(1-over/n)*100:.1f}% rows",
              f"{over} rows have ordered+cooked > logged — accounting mismatch", warn=True)

    print(f"  Avg weekly calories: {avg_cal:.1f}  P95: {p95:.1f}  P99: {p99:.1f}")


# ══════════════════════════════════════════════════════════════
# 10. SOCIAL CONTEXT — location ↔ living_situation
# ══════════════════════════════════════════════════════════════

def validate_social_context(path, users_df=None):
    section("social_eating_context.csv — location plausibility")
    df = pd.read_csv(path)
    n = len(df)
    print(f"  Rows: {n:,}")

    # ── Location type ↔ social context ────────────────────────
    alone_hostel = df[(df["social_context"] == "alone") & (df["location_type"] == "hostel")]
    if users_df is not None:
        non_hostel_users = set(users_df[~users_df["living_situation"].isin(["hostel_pg"])]["user_id"])
        false_hostel = alone_hostel[alone_hostel["user_id"].isin(non_hostel_users)]
        check(len(false_hostel) / max(n, 1) < 0.02,
              f"Non-hostel users assigned hostel location: {len(false_hostel)/n*100:.2f}%",
              f"{len(false_hostel)} non-hostel users with location_type=hostel — fix living_situation filter")
    else:
        check(alone_hostel.shape[0] / n < 0.15,
              f"Hostel location for alone meals: {alone_hostel.shape[0]/n*100:.1f}% (warn if >15%)",
              warn=True)

    # ── Group size ↔ social context ───────────────────────────
    alone_group = df[(df["social_context"] == "alone") & (df["group_size"] > 1)]
    check(len(alone_group) == 0,
          "alone social_context → group_size = 1",
          f"{len(alone_group)} rows: alone but group_size > 1")

    restaurant_solo = df[(df["social_context"] == "at_restaurant") & (df["group_size"] == 1)]
    check(restaurant_solo.shape[0] / max(df["social_context"].eq("at_restaurant").sum(), 1) < 0.10,
          f"at_restaurant → group_size > 1 in >90%",
          warn=True)

    # ── Budget multiplier ranges ──────────────────────────────
    if "budget_multiplier" in df.columns:
        check(df["budget_multiplier"].between(0.5, 2.5).all(),
              "Budget multipliers in [0.5, 2.5]",
              f"{(~df['budget_multiplier'].between(0.5,2.5)).sum()} extreme budget multipliers")

    # ── variety_score [0,1] ────────────────────────────────────
    if "variety_score" in df.columns:
        check(df["variety_score"].between(0, 1).all(),
              "variety_score in [0,1]",
              f"{(~df['variety_score'].between(0,1)).sum()} rows outside [0,1]")

    print(f"  Social context dist: {df['social_context'].value_counts(normalize=True).round(3).to_dict()}")


# ══════════════════════════════════════════════════════════════
# MASTER RUNNER
# ══════════════════════════════════════════════════════════════

def validate_all(data_dir="data", fast=False, section_filter=None):
    global PASS, FAIL, WARN
    PASS = FAIL = WARN = 0

    print("=" * 60)
    print("  NARA Synthetic Data Validation v3")
    print("  Senior-level: row logic + causality + cultural realism")
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
        size_mb = os.path.getsize(path) / (1024*1024) if exists else 0
        rows = ""
        if exists:
            try:
                rows = f"{sum(1 for _ in open(path))-1:,} rows"
            except:
                pass
        check(exists, f"{name:<20} {size_mb:>7.1f} MB  {rows}",
              f"{name} MISSING")
        if not exists:
            all_exist = False

    if not all_exist:
        print("\n  Some files missing. Run run_all.py first.")
        return

    users_df = None

    run = lambda name: section_filter is None or section_filter == name

    if run("users"):
        users_df = validate_users(files["users"])

    if run("meals"):
        validate_meal_logs(files["meal_logs"], users_df)

    if run("fast"):
        validate_fast_days(files["fast_days"])

    if run("interactions"):
        validate_interactions(files["interactions"])

    if run("outcomes"):
        validate_health_outcomes(files["health_outcomes"], users_df)

    if run("reorders"):
        validate_reorders(files["reorders"])

    if run("skips"):
        validate_skip_events(files["skip_events"])

    if run("weekly"):
        validate_weekly_context(files["weekly_context"])

    if run("social"):
        validate_social_context(files["social_context"], users_df)

    if not fast and run("propagation"):
        validate_life_event_propagation(files["life_events"], files["weekly_context"])

    print("\n" + "=" * 60)
    print(f"  Results: ✓ {PASS} passed  ✗ {FAIL} failed  ⚠ {WARN} warnings")
    print(f"  Score: {PASS}/{PASS+FAIL} checks passing "
          f"({PASS/(PASS+FAIL)*100:.1f}%)" if PASS+FAIL > 0 else "")
    if FAIL == 0:
        print("  ✅ All checks passed — data ready for training")
    elif FAIL <= 3:
        print("  🟡 Minor issues — review failures above before training")
    else:
        print("  🔴 Significant issues — fix failures before training")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str, default="data")
    parser.add_argument("--fast", action="store_true", help="Skip slow cross-table checks")
    parser.add_argument("--section", type=str, default=None,
                        choices=["users","meals","fast","interactions","outcomes",
                                 "reorders","skips","weekly","social","propagation"],
                        help="Run only one section")
    args = parser.parse_args()
    validate_all(args.data_dir, fast=args.fast, section_filter=args.section)