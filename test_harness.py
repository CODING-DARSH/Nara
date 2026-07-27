"""
NARA — End-to-End Recommendation Pipeline Test Harness
========================================================

STANDALONE SCRIPT. Does not import, modify, or depend on any file inside
services/*. Talks to the real running docker-compose stack purely over
HTTP, using the actual verified API contracts (see the imports/endpoints
below — each was read directly from the real router/schema files:
auth/app/routers/auth.py + schemas/auth.py,
user-intelligence/app/routers/health_profile.py + schemas/intelligence.py,
ingestion/app/routers/meals.py + schemas/ingestion.py,
recommendation/app/routers/recommend.py + orders.py).

WHAT THIS DOES
--------------
1. Registers + logs in 5 dummy users, each with a DELIBERATELY
   non-overlapping profile (different region, diet, conditions,
   occupation) so their recommendations should be clearly distinguishable
   from each other — see PROFILES below.
2. Logs several real meals per user via free-text (/v1/meals/log),
   matching each profile's region/cuisine, and polls enrichment status
   until done (or times out) before moving on — meals need to actually
   finish enriching (NER + nutrition lookup + food graph update) before
   cuisine_affinity reflects them.
3. Pulls recommendations for all 4 real occasions (breakfast/lunch/
   dinner/snack) via BOTH /v1/recommend/ and /v1/recommend/with-restaurants,
   for every user, BEFORE any click/order behavior.
4. Randomly picks a shown dish (from the with-restaurants response, since
   that's what carries restaurant_id) per user, adds it to cart, checks
   out — using the real cart/checkout flow, no shortcuts.
5. Re-pulls recommendations for the same user/occasion AFTER checkout, to
   see whether the ordered dish/cuisine visibly moved in the ranking
   (reorder_boost + cuisine_affinity should reflect it).
6. Writes a single human-readable Markdown report (not raw JSON) with a
   dedicated section per user, a before/after comparison, and a documented
   PASS/CHECK against a stated expectation per profile — plus a companion
   raw JSON dump (full API responses) for anyone who wants to dig into a
   specific number afterward.

WHAT THIS DELIBERATELY DOES NOT DO
-----------------------------------
- No standalone-vs-ensemble per-model breakdown (e.g. "lgbm said 0.6, xgb
  said 0.7, ensemble said 0.65"). That data only exists inside
  ranker.py/model_loader.py and is not exposed by any current endpoint.
  Getting it requires a new, separate, explicitly-approved debug endpoint
  — NOT built here, since that's a production code change requiring its
  own review, not something to bundle into a test script silently.
- No fabricated/guessed API contracts. Every endpoint/payload shape below
  was read from the actual schema files, not assumed.

USAGE
-----
    pip install httpx
    python test_harness.py [--base-host localhost]

Run this from the machine that can reach the docker-compose services on
their mapped ports (8001-8005) — i.e. the same machine running
`docker compose up`.
"""
import argparse
import asyncio
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ── Service base URLs (from docker-compose.yml port mappings) ──────────
def base_urls(host: str) -> dict:
    return {
        "auth":           f"http://{host}:8001",
        "user_intel":     f"http://{host}:8002",
        "ingestion":      f"http://{host}:8003",
        "recommendation": f"http://{host}:8005",
    }

OCCASIONS = ["breakfast", "lunch", "snack", "dinner"]

ENRICHMENT_POLL_INTERVAL_S = 2
ENRICHMENT_POLL_TIMEOUT_S  = 30

DISCOVER_LAT, DISCOVER_LNG = 12.9716, 77.5946  # Bengaluru — matches the
                                                 # frontend's own fallback
                                                 # default, same reasoning:
                                                 # this is where seeded
                                                 # restaurant data actually
                                                 # is.

# ═════════════════════════════════════════════════════════════════════
# PROFILES — 5 users, deliberately sharing NO state: different region,
# diet, declared conditions, occupation, income tier, and the actual
# cuisine of meals logged. Each profile states an EXPECTATION up front
# (checked against real output later, not asserted as ground truth —
# region/cuisine affinity is a soft signal blended with other factors,
# not a hard filter, so the check reports a percentage, not pass/fail
# on an exact match).
# ═════════════════════════════════════════════════════════════════════

PROFILES = [
    {
        "id": "user1_riya_delhi",
        "email": "riya.test.harness@example.com",
        "password": "TestPass123",
        "onboarding": {
            "declared_conditions": [],
            "dietary_restrictions": [],
            "nutritional_goals": {"max_calories": 2200, "target_protein_g": 70},
            "age": 27, "weight_kg": 60, "height_cm": 165, "gender": "female",
            "activity_level": "moderately_active",
            "income_tier": "medium", "region": "north",
            "occupation": "salaried", "living_situation": "with_roommates",
            "stress_level": "medium", "is_wfh": False,
        },
        "meals": [
            "Had chole bhature for breakfast",
            "Butter chicken with naan for lunch",
            "Paratha with curd for dinner",
            "Samosa and chai as an evening snack",
        ],
        "expected_cuisine_hint": "north_indian",
        "note": "No conditions, no restrictions, non-veg, north Indian meals — a clean baseline warm-start profile.",
    },
    {
        "id": "user2_aarav_ahmedabad",
        "email": "aarav.test.harness@example.com",
        "password": "TestPass123",
        "onboarding": {
            "declared_conditions": [],
            "dietary_restrictions": ["vegetarian", "jain"],
            "nutritional_goals": {"target_fiber_g": 28, "target_protein_g": 60},
            "age": 34, "weight_kg": 72, "height_cm": 172, "gender": "male",
            "activity_level": "lightly_active",
            "income_tier": "high", "region": "west",
            "occupation": "self_employed", "living_situation": "with_family",
            "stress_level": "low", "is_wfh": True,
        },
        "meals": [
            "Khichadi with kadhi for lunch",
            "Dhokla for breakfast",
            "Thepla and chai as a snack",
            "Undhiyu for dinner",
        ],
        "expected_cuisine_hint": "gujarati",
        "note": "Vegetarian + Jain, Gujarati meals — tests hard dietary filtering + strong single-cuisine affinity.",
    },
    {
        "id": "user3_sourav_kolkata",
        "email": "sourav.test.harness@example.com",
        "password": "TestPass123",
        "onboarding": {
            "declared_conditions": ["type2_diabetes"],
            "dietary_restrictions": [],
            "nutritional_goals": {"max_sugar_g": 25, "target_fiber_g": 30},
            "age": 45, "weight_kg": 80, "height_cm": 170, "gender": "male",
            "activity_level": "sedentary",
            "income_tier": "medium", "region": "east",
            "occupation": "salaried", "living_situation": "with_family",
            "stress_level": "high", "is_wfh": False,
        },
        "meals": [
            "Macher jhol with rice for lunch",
            "Luchi and alur dom for breakfast",
            "Mishti doi as dessert",
            "Shorshe ilish for dinner",
        ],
        "expected_cuisine_hint": "bengali",
        "note": "type2_diabetes declared — tests health_score_dish / GI-aware filtering and health_reasons actually appearing on flagged high-GI dishes (mishti doi, luchi).",
    },
    {
        "id": "user4_meera_bengaluru",
        "email": "meera.test.harness@example.com",
        "password": "TestPass123",
        "onboarding": {
            "declared_conditions": [],
            "dietary_restrictions": ["vegetarian"],
            "nutritional_goals": {"target_protein_g": 55},
            "age": 24, "weight_kg": 55, "height_cm": 160, "gender": "female",
            "activity_level": "very_active",
            "income_tier": "low", "region": "south",
            "occupation": "student", "living_situation": "with_roommates",
            "stress_level": "medium", "is_wfh": False,
        },
        "meals": [
            "Idli sambar for breakfast",
            "Masala dosa for lunch",
            "Rava upma as a snack",
            "Curd rice for dinner",
        ],
        "expected_cuisine_hint": "south_indian",
        "note": "Low income_tier + vegetarian + South Indian meals — tests price_match_score behavior and warm-start with a distinct cuisine from users 1-3.",
    },
    {
        "id": "user5_priyanka_guwahati",
        "email": "priyanka.test.harness@example.com",
        "password": "TestPass123",
        "onboarding": {
            "declared_conditions": ["hypertension", "high_cholesterol"],
            "dietary_restrictions": ["low_sodium"],
            "nutritional_goals": {"max_sodium_mg": 2000},
            "age": 52, "weight_kg": 78, "height_cm": 168, "gender": "female",
            "activity_level": "sedentary",
            "income_tier": "medium", "region": "northeast",
            "occupation": "retired", "living_situation": "alone",
            "stress_level": "low", "is_wfh": False,
        },
        "meals": [],  # deliberately NO meals logged — true cold-start
        "expected_cuisine_hint": None,  # no behavioral signal exists yet;
                                          # this profile checks cold-start
                                          # + region-prior fallback instead
        "note": "TRUE COLD START — zero meals logged, two conditions declared. Tests whether cold-start/region-prior fallback produces a sane, non-empty, health-aware list with no behavioral data at all.",
    },
]


# ═════════════════════════════════════════════════════════════════════
# API helpers — one function per verified real endpoint
# ═════════════════════════════════════════════════════════════════════

async def register_and_login(client: httpx.AsyncClient, urls: dict, profile: dict) -> dict:
    reg = await client.post(f"{urls['auth']}/v1/auth/register", json={
        "email": profile["email"], "password": profile["password"],
    })
    # 201 on first run, 400/409-ish on re-run if the account already
    # exists from a prior harness run — either way, proceed to login.
    reg_info = {"status_code": reg.status_code, "body": _safe_json(reg)}

    login = await client.post(f"{urls['auth']}/v1/auth/login", json={
        "email": profile["email"], "password": profile["password"],
    })
    login.raise_for_status()
    login_body = login.json()
    return {
        "register": reg_info,
        "login": login_body,
        "token": login_body["access_token"],
        "user_id": login_body["user_id"],
    }


async def submit_onboarding(client: httpx.AsyncClient, urls: dict, token: str, onboarding: dict) -> dict:
    r = await client.post(
        f"{urls['user_intel']}/v1/health-profile",
        json=onboarding,
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"status_code": r.status_code, "body": _safe_json(r)}


async def log_meal(client: httpx.AsyncClient, urls: dict, token: str, description: str, occasion: str) -> dict:
    r = await client.post(
        f"{urls['ingestion']}/v1/meals/log",
        json={
            "description": description,
            "context": {"occasion": occasion, "location_type": "home", "notes": "harness-generated"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    return r.json()


async def poll_enrichment(client: httpx.AsyncClient, urls: dict, token: str, event_id: str) -> str:
    deadline = time.monotonic() + ENRICHMENT_POLL_TIMEOUT_S
    while time.monotonic() < deadline:
        r = await client.get(
            f"{urls['ingestion']}/v1/meals/{event_id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        status = r.json()["enrichment_status"]
        if status in ("done", "failed"):
            return status
        await asyncio.sleep(ENRICHMENT_POLL_INTERVAL_S)
    return "timeout"


async def get_recommendations(client: httpx.AsyncClient, urls: dict, token: str, occasion: str) -> dict:
    r = await client.get(
        f"{urls['recommendation']}/v1/recommend/",
        params={"occasion": occasion, "n": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"status_code": r.status_code, "body": _safe_json(r)}


async def get_recommendations_with_restaurants(client: httpx.AsyncClient, urls: dict, token: str, occasion: str) -> dict:
    r = await client.get(
        f"{urls['recommendation']}/v1/recommend/with-restaurants",
        params={"lat": DISCOVER_LAT, "lng": DISCOVER_LNG, "occasion": occasion, "n": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"status_code": r.status_code, "body": _safe_json(r)}


async def add_to_cart(client: httpx.AsyncClient, urls: dict, token: str, restaurant_id: str,
                       dish_name: str, cuisine_type: str, session_id: str | None) -> dict:
    r = await client.post(
        f"{urls['recommendation']}/v1/orders/cart/items",
        json={
            "restaurant_id": restaurant_id, "dish_name": dish_name,
            "cuisine_type": cuisine_type, "quantity": 1, "session_id": session_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"status_code": r.status_code, "body": _safe_json(r)}


async def checkout(client: httpx.AsyncClient, urls: dict, token: str) -> dict:
    r = await client.post(
        f"{urls['recommendation']}/v1/orders/checkout",
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"status_code": r.status_code, "body": _safe_json(r)}


def _safe_json(response: httpx.Response):
    try:
        return response.json()
    except Exception:
        return {"raw_text": response.text[:500]}


# ═════════════════════════════════════════════════════════════════════
# Per-user run
# ═════════════════════════════════════════════════════════════════════

async def run_profile(client: httpx.AsyncClient, urls: dict, profile: dict) -> dict:
    result = {"profile_id": profile["id"], "note": profile["note"]}

    auth_info = await register_and_login(client, urls, profile)
    result["auth"] = {"status": "ok", "user_id": auth_info["user_id"]}
    token = auth_info["token"]

    onboarding_result = await submit_onboarding(client, urls, token, profile["onboarding"])
    result["onboarding"] = onboarding_result

    # ── Log meals, matched to occasion order (breakfast/lunch/snack/dinner) ──
    meal_results = []
    for i, description in enumerate(profile["meals"]):
        occasion = OCCASIONS[i % len(OCCASIONS)]
        logged = await log_meal(client, urls, token, description, occasion)
        enrichment_status = await poll_enrichment(client, urls, token, logged["event_id"])
        meal_results.append({
            "description": description, "occasion": occasion,
            "event_id": logged["event_id"], "enrichment_status": enrichment_status,
        })
    result["meals_logged"] = meal_results

    # ── BEFORE: recommendations across all 4 occasions ──
    before = {}
    for occasion in OCCASIONS:
        plain = await get_recommendations(client, urls, token, occasion)
        with_r = await get_recommendations_with_restaurants(client, urls, token, occasion)
        before[occasion] = {"plain": plain, "with_restaurants": with_r}
    result["recommendations_before"] = before

    # ── RANDOM CLICK + CHECKOUT, using a real with-restaurants response ──
    click_and_order = {"performed": False}
    candidate_occasion = random.choice(OCCASIONS)
    wr_body = before[candidate_occasion]["with_restaurants"]["body"]
    recs = wr_body.get("recommendations", []) if isinstance(wr_body, dict) else []
    orderable = [r for r in recs if r.get("nearby_restaurants")]

    if orderable:
        chosen_dish = random.choice(orderable)
        chosen_restaurant = random.choice(chosen_dish["nearby_restaurants"])
        session_id = wr_body.get("session_id")

        add_result = await add_to_cart(
            client, urls, token,
            restaurant_id=chosen_restaurant["id"],
            dish_name=chosen_dish["dish_name"],
            cuisine_type=chosen_dish.get("cuisine_type"),
            session_id=session_id,
        )
        checkout_result = await checkout(client, urls, token)

        click_and_order = {
            "performed": True,
            "occasion_used": candidate_occasion,
            "dish_name": chosen_dish["dish_name"],
            "cuisine_type": chosen_dish.get("cuisine_type"),
            "restaurant_name": chosen_restaurant.get("name"),
            "add_to_cart": add_result,
            "checkout": checkout_result,
        }
    else:
        click_and_order["reason"] = "No orderable dish (with a real nearby restaurant match) found in any occasion's with-restaurants response."
    result["click_and_order"] = click_and_order

    # ── AFTER: recommendations again, same occasion the click happened in ──
    after = {}
    if click_and_order["performed"]:
        occasion = click_and_order["occasion_used"]
        plain = await get_recommendations(client, urls, token, occasion)
        with_r = await get_recommendations_with_restaurants(client, urls, token, occasion)
        after[occasion] = {"plain": plain, "with_restaurants": with_r}
    result["recommendations_after"] = after

    return result


# ═════════════════════════════════════════════════════════════════════
# Report generation
# ═════════════════════════════════════════════════════════════════════

def _dish_list(body: dict) -> list:
    if not isinstance(body, dict):
        return []
    return body.get("recommendations", [])


def _cuisine_match_pct(dishes: list, expected_cuisine: str | None) -> str:
    if not expected_cuisine:
        return "N/A (no behavioral signal expected for this profile)"
    if not dishes:
        return "N/A (no dishes returned)"
    matches = sum(1 for d in dishes if d.get("cuisine_type") == expected_cuisine)
    pct = round(100 * matches / len(dishes), 1)
    return f"{matches}/{len(dishes)} ({pct}%) tagged '{expected_cuisine}'"


def build_markdown_report(results: list) -> str:
    lines = []
    lines.append("# NARA Recommendation Pipeline — End-to-End Test Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## Scope and honest limitations")
    lines.append("")
    lines.append("- This report covers 5 independently created, non-overlapping user profiles run against the **real running services** — no mocked data, no production code modified to produce this.")
    lines.append("- Cuisine-match percentages are a **soft expectation check**, not a pass/fail contract — cuisine_affinity is one blended signal among several (region prior, health compliance, diversification, reorder boost), so 100% match is not the bar; a near-0% match for a strong-affinity profile IS worth investigating.")
    lines.append("- **Standalone-vs-ensemble per-model scores are NOT included** — that data isn't exposed by any current endpoint, and adding a debug endpoint to expose it was deliberately not done without separate explicit approval (see script docstring).")
    lines.append("")
    lines.append("---")
    lines.append("")

    for r in results:
        lines.append(f"## {r['profile_id']}")
        lines.append("")
        lines.append(f"**Profile note:** {r['note']}")
        lines.append("")
        lines.append(f"- Auth: `{r['auth']['status']}` (user_id: `{r['auth']['user_id']}`)")
        lines.append(f"- Onboarding: HTTP `{r['onboarding']['status_code']}`")
        lines.append("")

        lines.append("### Meals logged")
        lines.append("")
        if r["meals_logged"]:
            lines.append("| Description | Occasion | Enrichment status |")
            lines.append("|---|---|---|")
            for m in r["meals_logged"]:
                lines.append(f"| {m['description']} | {m['occasion']} | {m['enrichment_status']} |")
        else:
            lines.append("*(none — deliberate true cold-start profile)*")
        lines.append("")

        expected = next(p["expected_cuisine_hint"] for p in PROFILES if p["id"] == r["profile_id"])

        lines.append("### Recommendations — BEFORE any click/order")
        lines.append("")
        lines.append("| Occasion | HTTP | Dishes returned | Cuisine-match check | Top 3 dishes (score) |")
        lines.append("|---|---|---|---|---|")
        for occasion in OCCASIONS:
            entry = r["recommendations_before"].get(occasion, {})
            plain = entry.get("plain", {})
            dishes = _dish_list(plain.get("body"))
            match  = _cuisine_match_pct(dishes, expected)
            top3   = ", ".join(f"{d.get('dish_name')} ({d.get('score')})" for d in dishes[:3]) or "—"
            lines.append(f"| {occasion} | {plain.get('status_code')} | {len(dishes)} | {match} | {top3} |")
        lines.append("")

        co = r["click_and_order"]
        lines.append("### Simulated click + checkout")
        lines.append("")
        if co.get("performed"):
            lines.append(f"- Occasion used: **{co['occasion_used']}**")
            lines.append(f"- Dish ordered: **{co['dish_name']}** ({co.get('cuisine_type')}) from **{co.get('restaurant_name')}**")
            lines.append(f"- Add-to-cart: HTTP `{co['add_to_cart']['status_code']}`")
            lines.append(f"- Checkout: HTTP `{co['checkout']['status_code']}`")
        else:
            lines.append(f"- **Not performed** — {co.get('reason')}")
        lines.append("")

        if r["recommendations_after"]:
            lines.append("### Recommendations — AFTER checkout (same occasion)")
            lines.append("")
            occasion = co["occasion_used"]
            after_entry  = r["recommendations_after"][occasion]["plain"]
            before_entry = r["recommendations_before"][occasion]["plain"]
            after_dishes  = _dish_list(after_entry.get("body"))
            before_dishes = _dish_list(before_entry.get("body"))

            ordered_dish = co["dish_name"]
            before_rank = next((i for i, d in enumerate(before_dishes) if d.get("dish_name") == ordered_dish), None)
            after_rank  = next((i for i, d in enumerate(after_dishes)  if d.get("dish_name") == ordered_dish), None)

            lines.append(f"- `{ordered_dish}` rank before: **{before_rank if before_rank is not None else 'not in top 10'}**")
            lines.append(f"- `{ordered_dish}` rank after:  **{after_rank if after_rank is not None else 'not in top 10'}**")
            if before_rank is not None and after_rank is not None:
                moved = before_rank - after_rank
                lines.append(f"- Movement: **{'+' if moved > 0 else ''}{moved}** positions ({'improved' if moved > 0 else 'no change' if moved == 0 else 'dropped'})")
            lines.append("")
            lines.append("| Occasion | Top 3 AFTER checkout (score) |")
            lines.append("|---|---|")
            top3_after = ", ".join(f"{d.get('dish_name')} ({d.get('score')})" for d in after_dishes[:3]) or "—"
            lines.append(f"| {occasion} | {top3_after} |")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════════

async def main(host: str, output_dir: Path):
    urls = base_urls(host)
    results = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for profile in PROFILES:
            print(f"Running profile: {profile['id']}...")
            try:
                r = await run_profile(client, urls, profile)
                results.append(r)
                print(f"  done.")
            except Exception as e:
                print(f"  FAILED: {e}")
                results.append({"profile_id": profile["id"], "note": profile["note"], "error": str(e)})

    output_dir.mkdir(parents=True, exist_ok=True)

    raw_path = output_dir / "harness_raw_output.json"
    raw_path.write_text(json.dumps(results, indent=2, default=str))

    report_path = output_dir / "harness_report.md"
    report_path.write_text(build_markdown_report(results))

    print(f"\nWrote:\n  {report_path}\n  {raw_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-host", default="localhost", help="Host where docker-compose services are reachable")
    parser.add_argument("--output-dir", default="./harness_output")
    args = parser.parse_args()

    asyncio.run(main(args.base_host, Path(args.output_dir)))