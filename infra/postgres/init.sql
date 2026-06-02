-- ============================================================
-- NARA Database Initialization
-- Runs once on first container boot
-- Creates both: nara (user data) and nara_data (restaurant/nutrition data)
-- ============================================================

-- ============================================================
-- DATABASE: nara (connects to Neon in production, local in dev)
-- ============================================================
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- ── Auth ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           TEXT NOT NULL UNIQUE,
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    tier            TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'enterprise')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_credentials (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    password_hash   TEXT,
    google_sub      TEXT UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL UNIQUE,
    device_hint     TEXT,
    ip_address      INET,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── User Intelligence ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS user_health_profiles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version                 INT NOT NULL DEFAULT 1,
    declared_conditions     JSONB NOT NULL DEFAULT '[]',
    dietary_restrictions    JSONB NOT NULL DEFAULT '[]',
    nutritional_goals       JSONB NOT NULL DEFAULT '{}',
    allergies               JSONB NOT NULL DEFAULT '[]',
    cuisine_preferences     JSONB NOT NULL DEFAULT '{}',
    budget_preferences      JSONB NOT NULL DEFAULT '{}',
    activity_level          TEXT NOT NULL DEFAULT 'moderately_active',
    age                     INT,
    weight_kg               FLOAT,
    height_cm               FLOAT,
    gender                  TEXT,
    wearable_integrations   JSONB NOT NULL DEFAULT '{}',
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uidx_health_profile_active
    ON user_health_profiles(user_id) WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS food_graphs (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    last_24h                JSONB NOT NULL DEFAULT '{}',
    last_7d                 JSONB NOT NULL DEFAULT '{}',
    last_30d                JSONB NOT NULL DEFAULT '{}',
    nutritional_gaps        JSONB NOT NULL DEFAULT '[]',
    cuisine_affinity        JSONB NOT NULL DEFAULT '{}',
    meal_timing_patterns    JSONB NOT NULL DEFAULT '{}',
    top_dishes              JSONB NOT NULL DEFAULT '[]',
    detected_patterns       JSONB NOT NULL DEFAULT '{}',
    total_meals_logged      INT NOT NULL DEFAULT 0,
    last_computed_at        TIMESTAMPTZ,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_food_graphs_user ON food_graphs(user_id);

-- ── Food Events ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS food_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type          TEXT NOT NULL CHECK (event_type IN ('order','photo_log','manual_log','import','barcode_scan')),
    occurred_at         TIMESTAMPTZ NOT NULL,
    source_ref          JSONB,
    raw_input           JSONB NOT NULL DEFAULT '{}',
    meal_context        JSONB NOT NULL DEFAULT '{}',
    enrichment_status   TEXT NOT NULL DEFAULT 'pending'
                            CHECK (enrichment_status IN ('pending','processing','done','failed')),
    enriched_at         TIMESTAMPTZ,
    embedding           vector(1536),
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
    estimated_nutrition     JSONB NOT NULL DEFAULT '{}',
    confidence_score        FLOAT NOT NULL DEFAULT 0.0,
    model_version           TEXT,
    ingredients_inferred    JSONB NOT NULL DEFAULT '[]',
    cuisine_type            TEXT,
    portion_size_estimate   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Triggers ──────────────────────────────────────────────────

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

DO $$
BEGIN
    RAISE NOTICE 'nara database initialized.';
END $$;

-- ============================================================
-- DATABASE: nara_data (local only — restaurants, nutrition, ML data)
-- ============================================================

CREATE DATABASE nara_data;

\c nara_data;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS restaurants (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id         TEXT UNIQUE,
    source              TEXT,
    name                TEXT NOT NULL,
    cuisine_types       JSONB NOT NULL DEFAULT '[]',
    location            GEOGRAPHY(POINT, 4326),
    address             TEXT,
    city                TEXT,
    area                TEXT,
    avg_cost_for_two    INT,
    rating              FLOAT,
    rating_count        INT,
    delivery_enabled    BOOLEAN DEFAULT TRUE,
    delivery_time_min   INT,
    is_active           BOOLEAN DEFAULT TRUE,
    raw_data            JSONB NOT NULL DEFAULT '{}',
    synced_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_restaurants_location
    ON restaurants USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_restaurants_city
    ON restaurants(city) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_restaurants_area
    ON restaurants(area) WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS dishes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id   UUID REFERENCES restaurants(id) ON DELETE CASCADE,
    external_id     TEXT,
    name            TEXT NOT NULL,
    description     TEXT,
    price           INT,
    cuisine_type    TEXT,
    dish_type       TEXT,
    is_veg          BOOLEAN,
    is_available    BOOLEAN DEFAULT TRUE,
    image_url       TEXT,
    raw_data        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dishes_restaurant ON dishes(restaurant_id);
CREATE INDEX IF NOT EXISTS idx_dishes_name ON dishes(name);

CREATE TABLE IF NOT EXISTS nutrition_kb (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dish_name       TEXT NOT NULL UNIQUE,
    aliases         JSONB NOT NULL DEFAULT '[]',
    cuisine_type    TEXT,
    source          TEXT,
    per_100g        JSONB NOT NULL DEFAULT '{}',
    per_serving     JSONB NOT NULL DEFAULT '{}',
    serving_size_g  FLOAT,
    ingredients     JSONB NOT NULL DEFAULT '[]',
    allergens       JSONB NOT NULL DEFAULT '[]',
    is_veg          BOOLEAN,
    glycemic_index  FLOAT,
    glycemic_load   FLOAT,
    confidence      FLOAT DEFAULT 1.0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nutrition_kb_dish ON nutrition_kb(dish_name);

CREATE TABLE IF NOT EXISTS food_images (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dish_name       TEXT NOT NULL,
    cuisine_type    TEXT,
    source_url      TEXT,
    minio_key       TEXT,
    label_verified  BOOLEAN DEFAULT FALSE,
    split           TEXT DEFAULT 'train',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_food_images_dish ON food_images(dish_name);
CREATE INDEX IF NOT EXISTS idx_food_images_split ON food_images(split);

DO $$
BEGIN
    RAISE NOTICE 'nara_data database initialized.';
END $$;