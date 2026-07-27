-- recommendation_events — raw, append-only log of every impression,
-- click, skip, and order. Lives in NEON, same reasoning as orders/
-- order_items (see 003_orders.sql): user-behavior data, never
-- regenerable, keyed by user_id which is a Neon-side concept.
--
-- This is NOT a replacement for orders/order_items (which tracks actual
-- cart/checkout state) or FoodGraph.cuisine_affinity (which tracks the
-- rolling aggregate) — it's the raw event stream underneath both, kept
-- durably instead of living only in Kafka's 7-day retention window
-- (KAFKA_LOG_RETENTION_HOURS: 168 in docker-compose.yml) or being boiled
-- straight into an aggregate with the individual event discarded.
--
-- What this unlocks, none of which was previously possible:
--   - Reconstructing the actual funnel: which dishes were shown (with
--     what rank/score), which one got clicked, which one got ordered —
--     for debugging ("why did this user see this") and future retraining.
--   - Offline evaluation: precision@k / NDCG against real logged outcomes,
--     using score+rank captured AT THE MOMENT OF SHOWING (recomputing
--     scores later would drift as models get retrained).
--   - A/B testing later: model_variant is included now (default
--     'production') so the schema doesn't need another migration once
--     live experiments start — see conversation notes on why live A/B
--     isn't meaningful yet with current traffic volume.
--
-- restaurant_id/dish_name are plain fields, not FKs — same cross-database
-- reasoning as orders/order_items (nutrition_kb/restaurants live in local
-- Postgres, Neon can't enforce a FK across separate database instances).
--
-- Run against NEON:
--   psql "$NEON_DATABASE_URL" -f 004_recommendation_events.sql

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS recommendation_events (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL,

    -- 'impression' — dish was shown in a recommendation list
    -- 'click'      — user tapped/opened a dish (recommendation card OR
    --                 add-to-cart, both are "click" strength — see
    --                 core/redis.DISH_INTERACTION_WEIGHTS)
    -- 'skip'       — explicit negative signal via /feedback
    -- 'order'      — dish was part of a placed order (orders.checkout())
    event_type     TEXT NOT NULL
                       CHECK (event_type IN ('impression', 'click', 'skip', 'order')),

    dish_name      TEXT NOT NULL,
    cuisine_type   TEXT,
    restaurant_id  UUID,     -- only set when this came from the
                               -- with-restaurants / orders flow
    occasion       TEXT,

    -- Captured AT THE MOMENT the dish was shown/acted on — never
    -- recomputed later. rank is 0-indexed position in the list shown;
    -- score is the ranker's own final_score for that dish at that time.
    rank           INT,
    score          FLOAT,

    -- Which model configuration produced this — hardcoded 'production'
    -- until live experiments exist (see conversation notes). Included now
    -- so no migration is needed when that changes.
    model_variant  TEXT NOT NULL DEFAULT 'production',

    -- Groups every impression row from ONE recommendation request
    -- together, so a later click/order can (when the frontend passes it
    -- back) be joined to exactly which shown list it came from, rather
    -- than guessed at via timestamp proximity. NULL is fine/expected for
    -- click/skip/order rows until the frontend is wired to round-trip it.
    session_id     UUID,

    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_recommendation_events_user_id
    ON recommendation_events (user_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_events_user_type
    ON recommendation_events (user_id, event_type);
CREATE INDEX IF NOT EXISTS idx_recommendation_events_session
    ON recommendation_events (session_id);
CREATE INDEX IF NOT EXISTS idx_recommendation_events_created_at
    ON recommendation_events (created_at);