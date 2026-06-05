"""
NARA Synthetic Data Generator — Master Runner
Runs all generators in correct order.
Estimated time: 20-40 minutes for 50,000 users

Usage:
    python run_all.py                    # full 50,000 users
    python run_all.py --test             # 1,000 users for testing
    python run_all.py --users 10000      # custom user count
    python run_all.py --skip_existing    # skip files already generated

Output folder: data/
"""
import os
import sys
import time
import argparse
import pandas as pd
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from generate_users import generate_users_csv
from generate_meal_logs import generate_meal_logs_csv
from generate_remaining import (
    generate_weekly_context_csv,
    generate_interactions_csv,
    generate_life_events_csv,
    generate_fast_days_csv,
    generate_skip_events_csv,
    generate_reorder_events_csv,
    generate_health_outcomes_csv,
    generate_social_context_csv,
)


def format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def file_exists_and_nonempty(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 1000


def print_header():
    print("=" * 60)
    print("  NARA Synthetic Data Generator")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def print_summary(timings: dict, output_dir: str):
    print("\n" + "=" * 60)
    print("  GENERATION COMPLETE")
    print("=" * 60)

    total_time = sum(timings.values())
    print(f"\n  Timings:")
    for step, t in timings.items():
        print(f"    {step:<30} {format_time(t):>8}")
    print(f"    {'TOTAL':<30} {format_time(total_time):>8}")

    print(f"\n  Output files:")
    files = [
        "users.csv", "meal_logs.csv", "user_weekly_context.csv",
        "interactions.csv", "life_events.csv", "fast_days.csv",
        "skip_events.csv", "reorder_events.csv",
        "health_outcomes.csv", "social_eating_context.csv",
    ]
    total_size = 0
    for f in files:
        path = os.path.join(output_dir, f)
        if os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            total_size += size_mb
            try:
                rows = sum(1 for _ in open(path)) - 1
                print(f"    {f:<35} {rows:>10,} rows  {size_mb:>7.1f} MB")
            except Exception:
                print(f"    {f:<35} {size_mb:>7.1f} MB")

    print(f"\n    {'TOTAL SIZE':<35} {total_size:>7.1f} MB")
    print("\n  Upload these CSVs to Google Colab for model training.")
    print("  Each model uses only the CSVs it needs.")
    print("\n  Model → CSV mapping:")
    print("    Demographic embedding   → users.csv")
    print("    XGBoost ranker          → interactions.csv + users.csv")
    print("    Health scorer           → users.csv + meal_logs.csv")
    print("    Meal occasion classifier→ meal_logs.csv")
    print("    Reorder prediction      → reorder_events.csv + users.csv")
    print("    Matrix factorization    → interactions.csv")
    print("    Intent classifier       → (hand-crafted, separate)")
    print("    Nutrition2Vec           → meal_logs.csv")
    print("    Meal2Vec                → meal_logs.csv (sequences)")
    print("    Nutritional trend       → user_weekly_context.csv")
    print("    Churn prediction        → user_weekly_context.csv + interactions.csv")
    print("=" * 60)


def run(n_users: int = 50000, output_dir: str = "data",
        skip_existing: bool = False, test_mode: bool = False):

    if test_mode:
        n_users = 1000
        print("[TEST MODE] Running with 1,000 users")

    os.makedirs(output_dir, exist_ok=True)
    print_header()
    print(f"\n  Config:")
    print(f"    Users:       {n_users:,}")
    print(f"    Output:      {output_dir}/")
    print(f"    Skip exist:  {skip_existing}")
    print()

    timings = {}
    paths = {
        "users":          os.path.join(output_dir, "users.csv"),
        "meal_logs":      os.path.join(output_dir, "meal_logs.csv"),
        "weekly_context": os.path.join(output_dir, "user_weekly_context.csv"),
        "interactions":   os.path.join(output_dir, "interactions.csv"),
        "life_events":    os.path.join(output_dir, "life_events.csv"),
        "fast_days":      os.path.join(output_dir, "fast_days.csv"),
        "skip_events":    os.path.join(output_dir, "skip_events.csv"),
        "reorders":       os.path.join(output_dir, "reorder_events.csv"),
        "health_outcomes":os.path.join(output_dir, "health_outcomes.csv"),
        "social_context": os.path.join(output_dir, "social_eating_context.csv"),
    }

    # ── Step 1: Users ─────────────────────────────────────────
    print("─" * 60)
    print("Step 1/10 — Generating users")
    print("─" * 60)
    if skip_existing and file_exists_and_nonempty(paths["users"]):
        print(f"  Skipping — {paths['users']} already exists")
        timings["1. users"] = 0
    else:
        t = time.time()
        generate_users_csv(n_users=n_users, output_path=paths["users"])
        timings["1. users"] = time.time() - t
        print(f"  Time: {format_time(timings['1. users'])}")

    # ── Step 2: Meal logs ─────────────────────────────────────
    print("\n" + "─" * 60)
    print("Step 2/10 — Generating meal logs")
    print("  This is the longest step (~15-25 min for 50K users)")
    print("─" * 60)
    if skip_existing and file_exists_and_nonempty(paths["meal_logs"]):
        print(f"  Skipping — {paths['meal_logs']} already exists")
        timings["2. meal_logs"] = 0
    else:
        t = time.time()
        generate_meal_logs_csv(
            users_csv=paths["users"],
            output_path=paths["meal_logs"],
            days_of_history=365,
        )
        timings["2. meal_logs"] = time.time() - t
        print(f"  Time: {format_time(timings['2. meal_logs'])}")

    # ── Step 3: Life events ───────────────────────────────────
    print("\n" + "─" * 60)
    print("Step 3/10 — Generating life events")
    print("─" * 60)
    if skip_existing and file_exists_and_nonempty(paths["life_events"]):
        print(f"  Skipping — {paths['life_events']} already exists")
        timings["3. life_events"] = 0
    else:
        t = time.time()
        generate_life_events_csv(
            users_csv=paths["users"],
            output_path=paths["life_events"],
        )
        timings["3. life_events"] = time.time() - t
        print(f"  Time: {format_time(timings['3. life_events'])}")

    # ── Step 4: Fast days ─────────────────────────────────────
    print("\n" + "─" * 60)
    print("Step 4/10 — Generating fast days")
    print("─" * 60)
    if skip_existing and file_exists_and_nonempty(paths["fast_days"]):
        print(f"  Skipping — {paths['fast_days']} already exists")
        timings["4. fast_days"] = 0
    else:
        t = time.time()
        generate_fast_days_csv(
            users_csv=paths["users"],
            output_path=paths["fast_days"],
        )
        timings["4. fast_days"] = time.time() - t
        print(f"  Time: {format_time(timings['4. fast_days'])}")

    # ── Step 5: Interactions ──────────────────────────────────
    print("\n" + "─" * 60)
    print("Step 5/10 — Generating interactions")
    n_interactions = 100000 if test_mode else 1000000
    print(f"  Generating {n_interactions:,} interaction sessions")
    print("─" * 60)
    if skip_existing and file_exists_and_nonempty(paths["interactions"]):
        print(f"  Skipping — {paths['interactions']} already exists")
        timings["5. interactions"] = 0
    else:
        t = time.time()
        generate_interactions_csv(
            users_csv=paths["users"],
            output_path=paths["interactions"],
            n_interactions=n_interactions,
        )
        timings["5. interactions"] = time.time() - t
        print(f"  Time: {format_time(timings['5. interactions'])}")

    # ── Step 6: Weekly context ────────────────────────────────
    print("\n" + "─" * 60)
    print("Step 6/10 — Generating weekly context")
    print("─" * 60)
    if skip_existing and file_exists_and_nonempty(paths["weekly_context"]):
        print(f"  Skipping — {paths['weekly_context']} already exists")
        timings["6. weekly_context"] = 0
    else:
        t = time.time()
        generate_weekly_context_csv(
            users_csv=paths["users"],
            meal_logs_csv=paths["meal_logs"],
            output_path=paths["weekly_context"],
        )
        timings["6. weekly_context"] = time.time() - t
        print(f"  Time: {format_time(timings['6. weekly_context'])}")

    # ── Step 7: Skip events ───────────────────────────────────
    print("\n" + "─" * 60)
    print("Step 7/10 — Generating skip events")
    print("─" * 60)
    if skip_existing and file_exists_and_nonempty(paths["skip_events"]):
        print(f"  Skipping — {paths['skip_events']} already exists")
        timings["7. skip_events"] = 0
    else:
        t = time.time()
        generate_skip_events_csv(
            users_csv=paths["users"],
            meal_logs_csv=paths["meal_logs"],
            output_path=paths["skip_events"],
        )
        timings["7. skip_events"] = time.time() - t
        print(f"  Time: {format_time(timings['7. skip_events'])}")

    # ── Step 8: Reorder events ────────────────────────────────
    print("\n" + "─" * 60)
    print("Step 8/10 — Generating reorder events")
    print("─" * 60)
    if skip_existing and file_exists_and_nonempty(paths["reorders"]):
        print(f"  Skipping — {paths['reorders']} already exists")
        timings["8. reorders"] = 0
    else:
        t = time.time()
        generate_reorder_events_csv(
            meal_logs_csv=paths["meal_logs"],
            output_path=paths["reorders"],
        )
        timings["8. reorders"] = time.time() - t
        print(f"  Time: {format_time(timings['8. reorders'])}")

    # ── Step 9: Health outcomes ───────────────────────────────
    print("\n" + "─" * 60)
    print("Step 9/10 — Generating health outcomes")
    print("─" * 60)
    if skip_existing and file_exists_and_nonempty(paths["health_outcomes"]):
        print(f"  Skipping — {paths['health_outcomes']} already exists")
        timings["9. health_outcomes"] = 0
    else:
        t = time.time()
        generate_health_outcomes_csv(
            users_csv=paths["users"],
            meal_logs_csv=paths["meal_logs"],
            output_path=paths["health_outcomes"],
        )
        timings["9. health_outcomes"] = time.time() - t
        print(f"  Time: {format_time(timings['9. health_outcomes'])}")

    # ── Step 10: Social context ───────────────────────────────
    print("\n" + "─" * 60)
    print("Step 10/10 — Generating social eating context")
    print("─" * 60)
    if skip_existing and file_exists_and_nonempty(paths["social_context"]):
        print(f"  Skipping — {paths['social_context']} already exists")
        timings["10. social_context"] = 0
    else:
        t = time.time()
        generate_social_context_csv(
            meal_logs_csv=paths["meal_logs"],
            output_path=paths["social_context"],
        )
        timings["10. social_context"] = time.time() - t
        print(f"  Time: {format_time(timings['10. social_context'])}")

    print_summary(timings, output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NARA Synthetic Data Generator")
    parser.add_argument("--users",         type=int,  default=50000, help="Number of users (default: 50000)")
    parser.add_argument("--output",        type=str,  default="data", help="Output directory (default: data)")
    parser.add_argument("--test",          action="store_true", help="Test mode: 1,000 users")
    parser.add_argument("--skip_existing", action="store_true", help="Skip files that already exist")
    args = parser.parse_args()

    run(
        n_users=args.users,
        output_dir=args.output,
        skip_existing=args.skip_existing,
        test_mode=args.test,
    )