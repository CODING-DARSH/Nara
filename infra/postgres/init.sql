-- ============================================================
-- NARA Database Initialization
-- Runs once on first container boot
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";          -- pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS "postgis";         -- geospatial for restaurant proximity

-- ============================================================
-- SCHEMA: auth
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           TEXT NOT NULL UNIQUE,
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    tier            TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'enterprise')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ  -- soft delete
);

CREATE TABLE IF NOT EXISTS user_credentials (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    password_hash   TEXT,                          -- NULL for OAuth-only users
    google_sub      TEXT UNIQUE,                   -- Google OAuth subject ID
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL UNIQUE,          -- stored hashed, never plaintext
    device_hint     TEXT,                          -- "iPhone 15", "Chrome/Mac" etc.
    ip_address      INET,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- SCHEMA: user intelligence
-- ============================================================

CREATE TABLE IF NOT EXISTS user_health_profiles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version                 INT NOT NULL DEFAULT 1,
    declared_conditions     JSONB NOT NULL DEFAULT '[]',   -- ["prediabetes", "lactose_intolerance"]
    dietary_restrictions    JSONB NOT NULL DEFAULT '[]',   -- ["vegetarian", "no_onion_garlic"]
    nutritional_goals       JSONB NOT NULL DEFAULT '{}',   -- {"target_protein_g": 80}
    allergies               JSONB NOT NULL DEFAULT '[]',
    wearable_integrations   JSONB NOT NULL DEFAULT '{}',
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uidx_health_profile_active
    ON user_health_profiles(user_id) WHERE is_active = TRUE;

-- ============================================================
-- SCHEMA: food events (core longitudinal table)
-- ============================================================

CREATE TABLE IF NOT EXISTS food_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type          TEXT NOT NULL CHECK (event_type IN ('order','photo_log','manual_log','import','barcode_scan')),
    occurred_at         TIMESTAMPTZ NOT NULL,
    source_ref          JSONB,                     -- {type: "swiggy", order_id: "..."}
    raw_input           JSONB NOT NULL DEFAULT '{}',
    meal_context        JSONB NOT NULL DEFAULT '{}', -- {occasion: "dinner", location_type: "home"}
    enrichment_status   TEXT NOT NULL DEFAULT 'pending'
                            CHECK (enrichment_status IN ('pending','processing','done','failed')),
    enriched_at         TIMESTAMPTZ,
    embedding           vector(1536),              -- pgvector: food semantic embedding
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_food_events_user_time
    ON food_events(user_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_food_events_enrichment_status
    ON food_events(enrichment_status) WHERE enrichment_status IN ('pending', 'processing');

CREATE TABLE IF NOT EXISTS food_event_nutrition (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id                UUID NOT NULL REFERENCES food_events(id) ON DELETE CASCADE UNIQUE,
    dish_name               TEXT NOT NULL,
    estimated_nutrition     JSONB NOT NULL DEFAULT '{}', -- {protein_g, carbs_g, fat_g, fiber_g, glycemic_load}
    confidence_score        FLOAT NOT NULL DEFAULT 0.0,
    model_version           TEXT,
    ingredients_inferred    JSONB NOT NULL DEFAULT '[]',
    cuisine_type            TEXT,
    portion_size_estimate   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- SCHEMA: restaurants (seeded separately, used by recommendation)
-- ============================================================

CREATE TABLE IF NOT EXISTS restaurants (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id     TEXT,                          -- Zomato/Swiggy restaurant ID
    source          TEXT,                          -- 'zomato', 'swiggy', 'google_places'
    name            TEXT NOT NULL,
    cuisine_types   JSONB NOT NULL DEFAULT '[]',
    location        GEOGRAPHY(POINT, 4326),        -- PostGIS geography
    address         TEXT,
    city            TEXT,
    avg_cost_for_two INT,
    rating          FLOAT,
    delivery_enabled BOOLEAN DEFAULT TRUE,
    is_active       BOOLEAN DEFAULT TRUE,
    raw_data        JSONB NOT NULL DEFAULT '{}',
    synced_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_restaurants_location
    ON restaurants USING GIST(location);

CREATE INDEX IF NOT EXISTS idx_restaurants_city
    ON restaurants(city) WHERE is_active = TRUE;

-- ============================================================
-- TRIGGERS: updated_at auto-update
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_user_credentials_updated_at
    BEFORE UPDATE ON user_credentials
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'NARA database initialized successfully.';
    RAISE NOTICE 'Extensions: uuid-ossp, pgcrypto, vector (pgvector), postgis';
    RAISE NOTICE 'Tables: users, user_credentials, refresh_tokens, user_health_profiles, food_events, food_event_nutrition, restaurants';
END $$;