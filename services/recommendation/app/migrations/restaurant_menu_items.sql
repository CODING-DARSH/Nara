-- restaurant_menu_items table
-- Run manually against the local Postgres container, since:
--   1. recommendation has no Alembic setup (unlike auth/ingestion/
--      user-intelligence, which were fixed earlier this session)
--   2. infra/postgres/init.sql (where `restaurants` and `nutrition_kb` are
--      presumably defined, run once via docker-entrypoint-initdb.d) wasn't
--      included in what I've read, so editing it blind risks clobbering
--      whatever's actually in it
--
-- How to run:
--   docker compose exec postgres psql -U nara -d nara_data -f /tmp/restaurant_menu_items.sql
-- (copy this file into the container first, or pipe it in — see the
-- accompanying instructions)

-- Defensive: gen_random_uuid() needs pgcrypto. restaurants.id is already
-- a UUID column, so something must already populate it — this extension
-- may already be enabled, but I couldn't confirm that from anything I've
-- read, so enabling it here is a safe no-op if it's already on.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS restaurant_menu_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_id   UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,

    -- Links to nutrition_kb.dish_name — deliberately NOT a foreign key,
    -- since nutrition_kb's primary key shape wasn't confirmed (the
    -- existing query at recommend.py just reads dish_name as the
    -- identifying field, no separate id column was ever referenced). If
    -- nutrition_kb does have a real id column, this should become a real
    -- FK instead of a name match.
    dish_name       TEXT NOT NULL,
    cuisine_type    TEXT NOT NULL,

    -- Real per-restaurant price — this is the field that didn't exist
    -- anywhere before, and that price_match_score in ranker.py has been
    -- waiting on (see the "HONEST LIMITATION" comment in
    -- get_recommendations()). Once this is populated, price_match_score
    -- can become a real computed comparison instead of a placeholder.
    price           NUMERIC(8, 2) NOT NULL,

    is_available    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- A restaurant shouldn't list the same dish name twice
    UNIQUE (restaurant_id, dish_name)
);

CREATE INDEX IF NOT EXISTS idx_restaurant_menu_items_restaurant_id
    ON restaurant_menu_items (restaurant_id);

CREATE INDEX IF NOT EXISTS idx_restaurant_menu_items_dish_name
    ON restaurant_menu_items (dish_name);

CREATE INDEX IF NOT EXISTS idx_restaurant_menu_items_cuisine_type
    ON restaurant_menu_items (cuisine_type);