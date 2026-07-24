"""
Seeds restaurant_menu_items from real data already in the local DB —
no invented dish names, only real restaurants x real nutrition_kb dishes,
with a synthetic (clearly labeled) restaurant<->dish assignment and price.

Run inside the recommendation container, after applying
migrations/001_restaurant_menu_items.sql:

    docker compose exec recommendation-service python -m app.seed_restaurant_menus

Assignment logic, per restaurant:
  - Each restaurant gets 12-20 menu items (random within that range).
  - ~80% of items are pulled from dishes whose cuisine_type matches one of
    the restaurant's own cuisine_types (real overlap, not guessed).
  - ~20% are pulled from any other dish — real restaurants serve more than
    one cuisine in practice; a Gujarati place still might have a north
    Indian thali, etc. This avoids menus that look mechanically generated.
  - Price = avg_cost_for_two / 2 (a per-person baseline) adjusted by a
    per-dish category multiplier (snacks/beverages cheaper, mains pricier),
    then jittered ±15% so two restaurants with the same avg_cost_for_two
    don't show identical prices for the same dish.
  - is_available is randomly set False for ~5% of rows, simulating real
    out-of-stock items rather than assuming every restaurant always has
    everything in stock.

This is explicitly synthetic restaurant<->dish<->price ASSIGNMENT on top of
REAL dish data (nutrition_kb) and REAL restaurant data (restaurants table).
Swap this script's logic out once you have a real menu data source — the
table shape (restaurant_menu_items) doesn't need to change either way.
"""
import asyncio
import random
import sys

from sqlalchemy import text

from app.core.database import LocalSession

# Rough per-category price multiplier relative to avg_cost_for_two/2.
# Categories inferred from cuisine_type since nutrition_kb has no
# dedicated dish-category column — "dessert"/"beverage" cuisine_types are
# treated as snack-tier pricing, everything else as a main.
CATEGORY_MULTIPLIER = {
    "dessert":  0.5,
    "beverage": 0.35,
    "staple":   0.4,   # rice, papad, etc. — side items, not mains
}
DEFAULT_MULTIPLIER = 1.0

MIN_ITEMS_PER_RESTAURANT = 12
MAX_ITEMS_PER_RESTAURANT = 20
CROSS_CUISINE_BLEED = 0.20       # fraction of items pulled from non-matching cuisines
UNAVAILABLE_PROBABILITY = 0.05
PRICE_JITTER = 0.15              # ±15%


async def fetch_restaurants(db):
    result = await db.execute(text("""
        SELECT id, name, cuisine_types, avg_cost_for_two
        FROM restaurants
        WHERE is_active = TRUE
    """))
    return [dict(r) for r in result.mappings().all()]


async def fetch_dishes(db):
    result = await db.execute(text("""
        SELECT dish_name, cuisine_type
        FROM nutrition_kb
        WHERE per_serving != '{}'
    """))
    return [dict(r) for r in result.mappings().all()]


def price_for(dish_cuisine: str, avg_cost_for_two: float) -> float:
    base = float(avg_cost_for_two or 400) / 2
    multiplier = CATEGORY_MULTIPLIER.get(dish_cuisine, DEFAULT_MULTIPLIER)
    price = base * multiplier
    jitter = random.uniform(1 - PRICE_JITTER, 1 + PRICE_JITTER)
    return round(price * jitter, 2)


async def seed():
    async with LocalSession() as db:
        restaurants = await fetch_restaurants(db)
        dishes = await fetch_dishes(db)

        if not restaurants:
            print("No restaurants found — nothing to seed. Check the restaurants table.")
            return
        if not dishes:
            print("No dishes found in nutrition_kb — nothing to seed.")
            return

        print(f"Found {len(restaurants)} restaurants, {len(dishes)} dishes in nutrition_kb.")

        dishes_by_cuisine = {}
        for d in dishes:
            dishes_by_cuisine.setdefault(d["cuisine_type"], []).append(d)

        total_inserted = 0
        total_skipped = 0

        for resto in restaurants:
            cuisine_types = resto["cuisine_types"] or []
            if isinstance(cuisine_types, str):
                # JSONB occasionally arrives as a raw string depending on
                # driver settings — guard the same way ensure_dishes_loaded
                # does for occasion_tags.
                import json
                try:
                    cuisine_types = json.loads(cuisine_types)
                except Exception:
                    cuisine_types = []

            matching_dishes = []
            for c in cuisine_types:
                matching_dishes.extend(dishes_by_cuisine.get(c, []))

            other_dishes = [d for d in dishes if d not in matching_dishes]

            target_count = random.randint(MIN_ITEMS_PER_RESTAURANT, MAX_ITEMS_PER_RESTAURANT)
            n_cross = max(1, round(target_count * CROSS_CUISINE_BLEED)) if other_dishes else 0
            n_match = target_count - n_cross

            chosen = []
            if matching_dishes:
                chosen.extend(random.sample(matching_dishes, min(n_match, len(matching_dishes))))
            # If a restaurant's declared cuisines don't actually overlap
            # with any real nutrition_kb cuisine_type, fall back entirely
            # to the general pool rather than seeding an empty menu.
            remaining = target_count - len(chosen)
            if remaining > 0 and other_dishes:
                chosen.extend(random.sample(other_dishes, min(remaining, len(other_dishes))))

            if not chosen:
                print(f"  [skip] {resto['name']}: no dishes available to assign at all")
                total_skipped += 1
                continue

            for dish in chosen:
                price = price_for(dish["cuisine_type"], resto["avg_cost_for_two"])
                is_available = random.random() > UNAVAILABLE_PROBABILITY

                try:
                    await db.execute(
                        text("""
                            INSERT INTO restaurant_menu_items
                                (restaurant_id, dish_name, cuisine_type, price, is_available)
                            VALUES (:restaurant_id, :dish_name, :cuisine_type, :price, :is_available)
                            ON CONFLICT (restaurant_id, dish_name) DO NOTHING
                        """),
                        {
                            "restaurant_id": resto["id"],
                            "dish_name": dish["dish_name"],
                            "cuisine_type": dish["cuisine_type"],
                            "price": price,
                            "is_available": is_available,
                        },
                    )
                    total_inserted += 1
                except Exception as e:
                    print(f"  [error] {resto['name']} / {dish['dish_name']}: {e}")

            print(f"  [ok] {resto['name']}: {len(chosen)} items "
                  f"({len(cuisine_types)} declared cuisines)")

        await db.commit()
        print(f"\nDone. Inserted {total_inserted} menu items across "
              f"{len(restaurants) - total_skipped} restaurants "
              f"({total_skipped} skipped for lack of any matching dish).")


if __name__ == "__main__":
    asyncio.run(seed())