-- orders / order_items — lives in NEON, not local Postgres.
--
-- Why Neon: this is user-behavior data (keyed by user_id, which is a
-- Neon-side concept via auth/FoodGraph), not catalog data. Unlike
-- restaurant_menu_items/nutrition_kb (regenerable via seed scripts in
-- local Docker Postgres), a user's real order history can never be
-- regenerated if lost — it belongs with the other durable, managed data.
--
-- restaurant_id and dish_name are plain fields, NOT DB-enforced foreign
-- keys — the restaurants/nutrition_kb tables they reference live in the
-- *other* Postgres (local Docker), and Postgres cannot enforce FK
-- constraints across separate database instances/providers. Validity is
-- checked at the application layer (the orders router looks the
-- restaurant/dish up in local Postgres before writing), same pattern
-- already used by restaurant_menu_items.dish_name -> nutrition_kb.dish_name.
--
-- One order = one row, whole lifecycle. Adding dishes to a cart does NOT
-- create a new order row — it's the SAME orders row (status='cart') with
-- order_items added/updated underneath it. Checking out transitions that
-- SAME row from status='cart' to status='placed'. This is deliberate:
-- click-to-cart and checkout must never become two separate order rows
-- for what is conceptually one order.
--
-- No payment fields anywhere — this is direct order/checkout only, no
-- payment processing, per explicit instruction.
--
-- Run against NEON (not the local postgres container):
--   psql "$NEON_DATABASE_URL" -f 003_orders.sql
-- or via whatever Neon console / connection method you use — this is NOT
-- run through `docker compose exec postgres ...` like earlier migrations,
-- since Neon is a separate managed instance, not the local container.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL,   -- real FK target is the users table,
                                      -- which this migration doesn't own —
                                      -- add the actual REFERENCES clause
                                      -- once you confirm the users table
                                      -- name/schema on the Neon side.

    -- Plain field, not FK — restaurants table lives in local Postgres.
    -- Validated at the application layer before insert.
    restaurant_id   UUID NOT NULL,

    -- 'cart'   — being built, not yet finalized (this is what a click/
    --            "add to cart" action produces or updates)
    -- 'placed' — finalized by checkout. Terminal state — a placed order
    --            is never edited or reopened into 'cart' again; a new
    --            order starts a new row.
    status          TEXT NOT NULL DEFAULT 'cart'
                        CHECK (status IN ('cart', 'placed')),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    placed_at       TIMESTAMPTZ  -- set only on the cart -> placed transition

    -- Enforced at the application layer, not here (a partial unique index
    -- on (user_id) WHERE status='cart' would need every historical row to
    -- respect it retroactively, and Postgres partial unique indexes on a
    -- CHECK-constrained enum column are fine but the app already has to
    -- check-then-decide for the "different restaurant" conflict case
    -- anyway, so the DB-level version would be redundant, not additive).
);

CREATE TABLE IF NOT EXISTS order_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id        UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,

    -- Plain fields, not FK — nutrition_kb lives in local Postgres.
    dish_name       TEXT NOT NULL,
    cuisine_type    TEXT,

    quantity        INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Adding the same dish twice to a cart should increment quantity, not
    -- create a duplicate row — enforced by the app's upsert logic, backed
    -- by this constraint so a concurrent double-add can't slip through.
    UNIQUE (order_id, dish_name)
);

CREATE INDEX IF NOT EXISTS idx_orders_user_id        ON orders (user_id);
CREATE INDEX IF NOT EXISTS idx_orders_user_status     ON orders (user_id, status);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id   ON order_items (order_id);