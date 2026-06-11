"""
NARA Restaurant Seeder — OpenStreetMap Overpass API
100% free. No API key. No billing. No rate limits (be polite though).
Covers all of Bangalore's restaurants with location data.

Run:
    pip install psycopg2-binary requests
    python scripts/seed_restaurants_osm.py --city bangalore
"""
import json
import time
import argparse
import psycopg2
import requests
from datetime import datetime

LOCAL_DB = "postgresql://nara:nara_secret@127.0.0.1:5433/nara_data"

# Bounding boxes for Indian cities
CITY_BOUNDS = {
    "bangalore": {
        "south": 12.834, "west": 77.460,
        "north": 13.139, "east": 77.780,
        "display": "Bangalore"
    },
    "mumbai": {
        "south": 18.892, "west": 72.775,
        "north": 19.268, "east": 72.987,
        "display": "Mumbai"
    },
    "delhi": {
        "south": 28.404, "west": 76.838,
        "north": 28.883, "east": 77.347,
        "display": "Delhi"
    },
    "ahmedabad": {
        "south": 22.912, "west": 72.455,
        "north": 23.133, "east": 72.680,
        "display": "Ahmedabad"
    },
}

# Map OSM cuisine tags to NARA cuisine types
CUISINE_MAP = {
    "indian": "indian",
    "south_indian": "south_indian",
    "north_indian": "north_indian",
    "chinese": "chinese",
    "pizza": "pizza",
    "burger": "burger",
    "fast_food": "fast_food",
    "coffee_shop": "cafe",
    "cafe": "cafe",
    "biryani": "biryani",
    "kebab": "kebab",
    "regional": "regional_indian",
    "vegetarian": "vegetarian",
    "vegan": "vegan",
}


def fetch_osm_restaurants(bounds: dict) -> list:
    # Try multiple Overpass endpoints
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    ]
    
    query = f"""[out:json][timeout:60];(node["amenity"="restaurant"]["name"]({bounds['south']},{bounds['west']},{bounds['north']},{bounds['east']});node["amenity"="cafe"]["name"]({bounds['south']},{bounds['west']},{bounds['north']},{bounds['east']});node["amenity"="fast_food"]["name"]({bounds['south']},{bounds['west']},{bounds['north']},{bounds['east']}););out body;"""

    for endpoint in endpoints:
        print(f"  Trying {endpoint}...")
        try:
            resp = requests.get(
                endpoint,
                params={"data": query},
                headers={"User-Agent": "NARA-App/1.0"},
                timeout=90,
            )
            print(f"  Status: {resp.status_code}")
            if resp.status_code == 200:
                return resp.json().get("elements", [])
            print(f"  Failed: {resp.status_code}")
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(2)
    
    return []

def parse_cuisine(tags: dict) -> list:
    raw = tags.get("cuisine", "")
    if not raw:
        return ["indian"]  # default for India

    cuisines = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip().lower()
        mapped = CUISINE_MAP.get(part, part)
        if mapped:
            cuisines.append(mapped)

    return cuisines if cuisines else ["indian"]


def estimate_cost(tags: dict) -> int:
    """Estimate avg cost for two from OSM price range tag."""
    price_range = tags.get("price_range", "")
    price_level = tags.get("toilets:fee", "")  # sometimes used for price

    if "cheap" in price_range or price_range == "1":
        return 200
    elif "moderate" in price_range or price_range == "2":
        return 400
    elif "expensive" in price_range or price_range in ("3", "4"):
        return 800
    return 300  # Bangalore average


def seed_city(city_name: str):
    bounds = CITY_BOUNDS.get(city_name.lower())
    if not bounds:
        print(f"City '{city_name}' not supported. Options: {list(CITY_BOUNDS.keys())}")
        return

    print(f"Seeding restaurants for {bounds['display']}...")
    elements = fetch_osm_restaurants(bounds)
    print(f"  Found {len(elements)} restaurants in OSM")

    if not elements:
        print("  No restaurants found. Try again or check internet connection.")
        return

    conn = psycopg2.connect(LOCAL_DB)
    cur = conn.cursor()
    saved = 0
    skipped = 0

    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name", "").strip()
        if not name:
            continue

        lat = el.get("lat")
        lon = el.get("lon")
        if not lat or not lon:
            continue

        external_id = f"osm_{el['id']}"

        # Check if exists
        cur.execute("SELECT id FROM restaurants WHERE external_id = %s", (external_id,))
        if cur.fetchone():
            skipped += 1
            continue

        cuisine_types = parse_cuisine(tags)
        avg_cost = estimate_cost(tags)
        area = tags.get("addr:suburb") or tags.get("addr:neighbourhood") or ""

        cur.execute("""
            INSERT INTO restaurants (
                external_id, source, name, cuisine_types,
                location, address, city, area,
                avg_cost_for_two, delivery_enabled, raw_data, synced_at
            )
            VALUES (%s, %s, %s, %s,
                    ST_MakePoint(%s, %s)::geography,
                    %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            external_id,
            "openstreetmap",
            name,
            json.dumps(cuisine_types),
            lon, lat,
            tags.get("addr:full") or tags.get("addr:street", ""),
            bounds["display"],
            area,
            avg_cost,
            True,
            json.dumps(tags),
            datetime.now(),
        ))
        saved += 1

        if saved % 100 == 0:
            conn.commit()
            print(f"  Saved {saved}...")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\n✓ Done. Saved: {saved} new restaurants. Skipped (exists): {skipped}")
    print(f"  Total restaurants in DB for {bounds['display']}: {saved + skipped}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default="bangalore", help="City to seed")
    args = parser.parse_args()

    seed_city(args.city)
    print("\nTo seed another city: python scripts/seed_restaurants_osm.py --city mumbai")
