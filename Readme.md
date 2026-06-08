# NARA — Personalized Food Intelligence Platform

> AI-powered food recommendation engine that learns what your body needs,
> finds what's available near you, and gets smarter every meal.

---

## Table of Contents

1. [What Is NARA](#1-what-is-nara)
2. [Project Structure](#2-project-structure)
3. [What Is Built So Far](#3-what-is-built-so-far)
4. [How To Run Locally](#4-how-to-run-locally)
5. [Neon Postgres Setup — Do This Now](#5-neon-postgres-setup--do-this-now)
6. [Database Schema — Every Table Explained](#6-database-schema--every-table-explained)
7. [Auth Service — Every File Explained](#7-auth-service--every-file-explained)
8. [API Reference — Auth Endpoints](#8-api-reference--auth-endpoints)
9. [What Is Coming Next — Full Roadmap](#9-what-is-coming-next--full-roadmap)
10. [Architecture Decisions](#10-architecture-decisions)

---

## 1. What Is NARA

NARA is a food intelligence system. It is not a recipe app. It is not a calorie counter.
It is a system that watches your eating patterns over time, understands your health context,
and recommends exactly what you should eat right now — from real restaurants near you —
based on what your body actually needs.

**The core loop:**

```
User logs a meal (photo / text / Zomato import)
        ↓
System enriches it async (vision model → nutrition DB → food graph update)
        ↓
Food graph builds a picture of nutritional gaps and eating patterns
        ↓
User asks "what should I eat?" (or opens the app at dinner time)
        ↓
Recommendation engine cross-references: nutritional gaps + health profile
+ available restaurants near user + user's cuisine preferences + budget
        ↓
Ranked list with plain-English explanations, orderable in one tap
```

**Seven services total when complete:**

| Service | What It Does | Status |
|---|---|---|
| Infrastructure | Postgres, Redis, Kafka, MinIO, all wired up | ✅ Built |
| Auth Service | Register, login, JWT, Google OAuth | ✅ Built |
| User Intelligence Service | Health profile, food graph, pattern detection | 🔜 Sprint 2 |
| Ingestion Service | Meal logging (text, photo, Zomato import) | 🔜 Sprint 3 |
| ML Inference Service | Vision model, nutrition estimation, embeddings | 🔜 Sprint 4 |
| Recommendation Service | Rule-based → ML ranking → LightGBM → RAG | 🔜 Sprint 5 |
| Conversation Agent Service | LangGraph multi-agent, streaming chat | 🔜 Sprint 6 |
| Commerce Integration | Zomato/Swiggy API, order placement | 🔜 Sprint 7 |

---

## 2. Project Structure

This is the full intended structure of the project.
Files marked `[built]` exist. Files marked `[next]` are coming.

```
nara/
│
├── docker-compose.yml              [built] — spins up entire infra stack
├── dev.sh                          [built] — helper script (up/down/logs/test)
├── .env                            [built] — local environment variables
├── .gitignore                      [built] — never commit .env or model weights
│
├── infra/
│   └── postgres/
│       └── init.sql                [built] — DB extensions + all 7 tables
│
├── services/
│   │
│   ├── auth/                       [built] — Identity & Auth Service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── alembic.ini
│   │   ├── alembic/
│   │   │   ├── env.py              [built] — async migration runner
│   │   │   ├── script.py.mako      [built] — migration file template
│   │   │   └── versions/           [empty] — migration files go here
│   │   └── app/
│   │       ├── main.py             [built] — FastAPI app, middleware, startup
│   │       ├── core/
│   │       │   ├── config.py       [built] — settings from env vars
│   │       │   ├── database.py     [built] — async SQLAlchemy session pool
│   │       │   ├── redis.py        [built] — async Redis client
│   │       │   └── security.py     [built] — bcrypt, JWT, refresh token utils
│   │       ├── models/
│   │       │   └── auth.py         [built] — User, UserCredential, RefreshToken ORM
│   │       ├── schemas/
│   │       │   └── auth.py         [built] — Pydantic request/response models
│   │       ├── dependencies/
│   │       │   └── auth.py         [built] — CurrentUserId JWT dependency
│   │       └── routers/
│   │           └── auth.py         [built] — all auth endpoints
│   │
│   ├── user-intelligence/          [next — Sprint 2]
│   │   └── app/
│   │       ├── routers/
│   │       │   ├── health_profile.py   — CRUD for health conditions, goals
│   │       │   └── food_graph.py       — aggregated nutrition, gap detection
│   │       ├── workers/
│   │       │   ├── graph_update.py     — Kafka consumer: food.events.enriched
│   │       │   └── pattern_detector.py — detects nutritional gaps, trends
│   │       └── models/
│   │           └── intelligence.py     — health profile, food graph ORM
│   │
│   ├── ingestion/                  [next — Sprint 3]
│   │   └── app/
│   │       └── routers/
│   │           ├── meals.py            — POST /meals/log, /meals/photo
│   │           └── import.py           — Zomato/Swiggy order history import
│   │
│   ├── ml-inference/               [next — Sprint 4]
│   │   ├── models/                     — EfficientNet-B4, nutrition estimator
│   │   ├── workers/
│   │   │   ├── vision_worker.py        — Kafka: photo.upload.pending
│   │   │   └── enrichment_worker.py    — Kafka: food.events.raw
│   │   └── triton/                     — Triton Inference Server configs
│   │
│   ├── recommendation/             [next — Sprint 5]
│   │   └── app/
│   │       ├── pipeline/
│   │       │   ├── candidate_gen.py    — PostGIS geo query + bloom filter
│   │       │   ├── ranker.py           — rule-based → LightGBM → ONNX
│   │       │   ├── rag_retriever.py    — vector search over nutrition KB
│   │       │   └── explainer.py        — plain-English reason generation
│   │       └── routers/
│   │           └── recommendations.py
│   │
│   ├── conversation/               [next — Sprint 6]
│   │   └── app/
│   │       ├── agents/
│   │       │   ├── perception.py       — entity extraction from natural lang
│   │       │   ├── memory.py           — queries food graph context
│   │       │   ├── reasoning.py        — health constraint application
│   │       │   ├── recommendation.py   — calls recommendation service
│   │       │   └── execution.py        — places orders, builds meal plans
│   │       └── graph.py                — LangGraph agent orchestration
│   │
│   └── commerce/                   [next — Sprint 7]
│       └── app/
│           ├── zomato.py               — Zomato API wrapper
│           ├── swiggy.py               — Swiggy API wrapper
│           └── order_flow.py           — unified order placement
│
├── scripts/                        [next — Sprint 1 parallel]
│   ├── seed_nutrition_kb.py            — USDA + IFCT scraper
│   ├── seed_restaurants.py             — Google Places API bulk pull
│   └── scrape_food_images.py           — Zomato image scraper for ML training
│
└── gateway/                        [next — Sprint 8]
    └── kong.yml                        — API Gateway: JWT validation, rate limiting
```

---

## 3. What Is Built So Far

### Part 1 — Infrastructure (`docker-compose.yml` + `infra/postgres/init.sql`)

A single `docker-compose up -d` command starts the entire data layer.

**What starts:**

**Postgres 16 with extensions**
Standard Postgres is not enough for NARA. Two extensions are enabled:
- `pgvector` — stores 1536-dimensional AI embeddings as columns in regular tables.
  This means "find meals semantically similar to this one" is a SQL query, not a
  separate AI service.
- `PostGIS` — adds geography types and spatial functions. The `restaurants` table
  stores locations as `GEOGRAPHY(POINT, 4326)` and a GIST index on that column makes
  "restaurants within 3km of lat/lng" run in under 5ms for a city-sized dataset.

**Redis 7**
Configured with 2GB max memory and LRU eviction. Used for four separate things:
- Recommendation cache keyed by `reco:{user_id}:{context_hash}` — TTL 3 minutes
- Food graph hot cache keyed by `foodgraph:{user_id}` — TTL 15 minutes, invalidated on new meal
- Rate limiting using sorted sets + Lua scripts for atomic token bucket
- Distributed locks (`enrichment_lock:{event_id}`) to prevent duplicate ML processing

**Kafka + Zookeeper**
7 topics created on first boot, each partitioned by `user_id` so all events
for one user land on the same partition and are processed in order:

| Topic | Purpose |
|---|---|
| `food.events.raw` | New meal log needing enrichment |
| `food.events.enriched` | Enriched meal (triggers food graph update) |
| `photo.upload.pending` | Photo needing vision model inference |
| `user.graph.updated` | Food graph changed (triggers reco cache invalidation) |
| `recommendation.feedback` | User accepted/rejected recommendation (ML training signal) |
| `wearable.sync.events` | CGM / Apple Health / Google Fit data |
| `api.requests` | All API calls logged for analytics |

**MinIO**
S3-compatible object storage. 4 buckets created:
- `nara-food-photos-raw` — original uploads, immutable, never deleted (needed for model retraining)
- `nara-food-photos-processed` — resized variants (thumbnail, medium, 224x224 for ML inference)
- `nara-model-artifacts` — versioned model weights (EfficientNet, LightGBM, ONNX files)
- `nara-exports` — user data export files (DPDP compliance)

**Adminer**
Web UI for Postgres at `http://localhost:8080`. Useful for inspecting tables during development.

---

### Part 2 — Auth Service (`services/auth/`)

A complete FastAPI microservice running on port 8001.

**What it handles:**
- User registration with email + password
- Login returning JWT access token + refresh token
- Refresh token rotation (old token revoked on use)
- Single device logout and logout from all devices
- Authenticated `/me` endpoint
- Full Google OAuth flow (authorize redirect + callback + account linking)

**Security design:**
- Passwords stored as bcrypt hash only — plaintext never persists anywhere
- Refresh tokens stored as SHA-256 hash — raw token only lives in API response
- JWT access tokens are short-lived (30 min), verified cryptographically in memory
  without a DB query on every request
- Refresh token rotation — each use invalidates the previous token, so a stolen
  refresh token is useless after one legitimate use
- Soft delete on users — `deleted_at` timestamp, data preserved for compliance

---
### Part-3
# Machine Learning Platform

NARA is powered by a multi-model machine learning system designed to understand
food behavior, health constraints, meal patterns, and recommendation preferences.

Unlike traditional food recommendation systems that rely solely on collaborative
filtering, NARA combines behavioral modeling, nutritional intelligence, health-aware
reasoning, and personalized ranking into a unified recommendation pipeline.

---

## Dataset

The ML platform was trained and evaluated on a large-scale synthetic behavioral
dataset constructed using published Indian dietary, epidemiological, and consumer
food behavior research.

### Dataset Scale

| Dataset | Rows |
|----------|----------:|
| users.csv | 5,000 |
| meal_logs.csv | 4.6M+ |
| interactions.csv | 7.3M+ |
| reorder_events.csv | 2.2M+ |
| user_weekly_context.csv | 260,000+ |
| fast_days.csv | thousands |
| skip_events.csv | hundreds of thousands |
| social_eating_context.csv | 4.6M+ |
| health_outcomes.csv | longitudinal outcomes |
| life_events.csv | user transition events |

Total:
- 20M+ generated records
- 160+ Indian dishes
- Multiple years of simulated behavior
- Health, lifestyle, culture, seasonality, and recommendation feedback signals

---

## Machine Learning Models

### Cold Start Recommendation

Predicts cuisine affinity for new users before interaction history exists.

Inputs:
- Age
- State
- Region
- Religion
- Lifestyle
- Health profile
- Dietary preferences

Models:
- KNN
- MLP
- Wide & Deep Networks

Purpose:
- Generate initial cuisine preferences
- Solve user cold-start problem

---

### Recommendation Ranking

Ranks dishes after candidate generation.

Target Classes:
- Skip
- Click
- Order

Models:
- Logistic Regression
- XGBoost
- LightGBM

Features:
- Cuisine affinity
- Health match score
- Price match score
- Recommendation position
- Nutrition features
- User context

Best Results:
- Accuracy ≈ 49%
- F1 ≈ 0.55
- NDCG@10 ≈ 0.48

Applications:
- Personalized recommendation ranking
- Restaurant and dish ordering prioritization

---

### Health Compliance Scoring

Predicts whether a meal aligns with a user's health requirements.

Models:
- Random Forest
- XGBoost
- LightGBM

Signals:
- Glycemic Index
- Calories
- Macronutrients
- Chronic conditions
- BMI
- Lifestyle patterns

Applications:
- Diabetic-safe recommendations
- Nutritional guidance
- Health-aware ranking

---

### Meal Occasion Classification

Predicts meal type from context.

Classes:
- Breakfast
- Lunch
- Snack
- Dinner
- Late Night

Models:
- Decision Tree
- Random Forest
- XGBoost

Best Results:
- Accuracy: 97.4%
- Weighted F1: 97.3%

Applications:
- Context-aware recommendation serving
- Meal planning
- Behavioral analysis

---

### Reorder Prediction

Predicts likelihood of a dish being reordered.

Models:
- Logistic Regression
- Random Forest
- XGBoost

Signals:
- Historical orders
- Habit strength
- Previous ratings
- Reorder intervals

Applications:
- Retention optimization
- Personalized resurfacing
- Habit modeling

---

## Validation Against Real-World Research

To ensure realistic behavioral simulation, generated distributions were validated
against published datasets and studies.

Sources include:

- Census of India
- NFHS-5
- ICMR What India Eats
- INDIAB Study
- Pew Research
- NSS Consumer Expenditure Survey
- Published recommendation system literature

Examples:

✓ Vegetarian population ≈ NFHS-5 benchmarks

✓ BMI–diabetes relationships reproduce epidemiological findings

✓ Regional cuisine preferences mirror Indian consumption surveys

✓ Recommendation position bias follows published recommendation-system behavior

✓ Fasting patterns align with religious observance studies

✓ Meal occasion distributions closely match ICMR dietary studies

✓ Reorder rates align with publicly reported food-delivery behavior

---

## Future ML Roadmap

Planned additions include:

- Food Image Classification
- Portion Size Estimation
- Nutrition Estimation Models
- Food Embeddings
- Two-Tower Retrieval
- Contextual Bandits
- RAG-based Nutrition Intelligence
- Wearable Integration Models
- Continuous Online Learning 
## 4. How To Run Locally

**Prerequisites:** Docker Desktop installed and running.

```bash
# 1. Clone or download the project
cd nara

# 2. Start everything
./dev.sh up

# 3. Verify auth is working
./dev.sh test-auth

# 4. Open API docs
# http://localhost:8001/docs
```

**What ./dev.sh up does step by step:**
1. Starts Postgres, Redis, Zookeeper, Kafka, MinIO, Adminer containers
2. Waits for Postgres healthcheck to pass
3. Starts the auth service container
4. Prints all URLs

**Access points after startup:**

| Service | URL | Credentials |
|---|---|---|
| Auth API docs | http://localhost:8001/docs | — |
| Adminer (Postgres UI) | http://localhost:8080 | server: postgres, user: nara, pass: nara_secret |
| MinIO console | http://localhost:9001 | user: nara_minio, pass: nara_minio_secret |
| Kafka | localhost:29092 | — |

---

## 5. Neon Postgres Setup — Do This Now

Neon gives you a free cloud Postgres that persists between sessions.
Replace the local Docker Postgres with Neon so your data is never lost.

### Step 1 — Create Neon account and project

1. Go to https://neon.tech and sign up (free, no credit card)
2. Create a new project — name it `nara`
3. Choose region closest to you (Asia Pacific / Singapore for India)
4. On the dashboard, click **Connection Details**
5. Copy the connection string — it looks like:
   ```
   postgresql://nara_owner:xxxxxxxxxxxx@ep-xxx-xxx.ap-southeast-1.aws.neon.tech/nara?sslmode=require
   ```

### Step 2 — Enable extensions in Neon

Neon supports pgvector natively. PostGIS needs to be enabled manually.

Go to your Neon dashboard → **SQL Editor** and run this:

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
```

Run each line. If postgis throws an error, check if your Neon plan supports it —
on free tier, run without PostGIS for now and add it when you upgrade.
The restaurants geo-query feature needs PostGIS but nothing in Sprint 1-2 requires it.

### Step 3 — Run the full schema on Neon

In the Neon SQL Editor, paste and run the entire contents of `infra/postgres/init.sql`.

This creates all 7 tables with the right indexes, constraints, and triggers.
It is safe to run multiple times — all statements use `IF NOT EXISTS`.

### Step 4 — Update your .env file

Open `.env` in the project root and replace the DATABASE_URL:

```bash
# Before (local Docker)
# DATABASE_URL is set inside docker-compose.yml

# After — add this to .env
DATABASE_URL=postgresql+asyncpg://nara_owner:xxxxxxxxxxxx@ep-xxx-xxx.ap-southeast-1.aws.neon.tech/nara?ssl=require
```

Note: Neon connection strings use `postgresql://` but SQLAlchemy async needs
`postgresql+asyncpg://` — change the prefix.

Also update `services/auth/alembic.ini` line:
```
sqlalchemy.url = postgresql+asyncpg://your-neon-connection-string-here
```

### Step 5 — Update docker-compose.yml auth service env

In `docker-compose.yml`, find the `auth-service` section and change:
```yaml
environment:
  DATABASE_URL: postgresql+asyncpg://YOUR_NEON_CONNECTION_STRING?ssl=require
```

### Step 6 — Remove local Postgres from docker-compose (optional)

Once you're on Neon, you can comment out or remove these services from
`docker-compose.yml` since you no longer need them locally:
- `postgres`
- `adminer`

Keep Redis, Kafka, Zookeeper, and MinIO running locally — those are not on Neon.

### Step 7 — Restart

```bash
./dev.sh down
./dev.sh up
./dev.sh test-auth
```

If auth still works and you can see users in the Neon dashboard SQL editor,
migration is complete.

---

## 6. Database Schema — Every Table Explained

### `users`
The core identity record. Minimal by design — only what cannot change.

| Column | Type | Purpose |
|---|---|---|
| id | UUID | Primary key, auto-generated |
| email | TEXT | Unique, stored lowercase |
| email_verified | BOOL | False until verification email clicked |
| tier | TEXT | free / pro / enterprise — controls feature access |
| created_at | TIMESTAMPTZ | Account creation time |
| updated_at | TIMESTAMPTZ | Auto-updated by trigger |
| deleted_at | TIMESTAMPTZ | Soft delete — null means active |

Why split from credentials? A user might have both password login and Google login.
Keeping identity and credentials separate makes account linking clean.

---

### `user_credentials`
Authentication methods per user. One user can have multiple auth methods.

| Column | Type | Purpose |
|---|---|---|
| user_id | UUID FK | Links to users.id |
| password_hash | TEXT | bcrypt hash, null for OAuth-only users |
| google_sub | TEXT | Google's unique user ID (subject), null for password-only |

---

### `refresh_tokens`
Every active login session. One row per device/browser.

| Column | Type | Purpose |
|---|---|---|
| token_hash | TEXT | SHA-256 hash of the raw token — raw never stored |
| device_hint | TEXT | First 200 chars of User-Agent header |
| ip_address | INET | IP at login time |
| expires_at | TIMESTAMPTZ | 30 days from creation |
| revoked_at | TIMESTAMPTZ | Set on logout — null means still active |

---

### `user_health_profiles`
The health context NARA uses to filter and rank food recommendations.

| Column | Type | Purpose |
|---|---|---|
| declared_conditions | JSONB | `["prediabetes", "hypertension", "lactose_intolerance"]` |
| dietary_restrictions | JSONB | `["vegetarian", "no_onion_garlic", "jain"]` |
| nutritional_goals | JSONB | `{"target_protein_g": 80, "reduce_sugar": true, "target_fiber_g": 25}` |
| allergies | JSONB | `["peanuts", "shellfish"]` — hard filters, not preferences |
| wearable_integrations | JSONB | `{"apple_health": true, "cgm_connected": false}` |
| version | INT | Profiles are versioned — health changes are tracked over time |
| is_active | BOOL | Only one active profile per user (enforced by partial unique index) |

---

### `food_events`
The core longitudinal table. Every meal ever logged, in order.

| Column | Type | Purpose |
|---|---|---|
| event_type | TEXT | order / photo_log / manual_log / import / barcode_scan |
| occurred_at | TIMESTAMPTZ | Actual meal time, not when it was logged |
| source_ref | JSONB | `{"type": "swiggy", "order_id": "SW123"}` |
| raw_input | JSONB | Original data before enrichment |
| meal_context | JSONB | `{"occasion": "dinner", "location_type": "office"}` |
| enrichment_status | TEXT | pending → processing → done / failed |
| embedding | vector(1536) | pgvector: 1536-dim semantic embedding of the meal |

The `embedding` column is what makes "find meals similar to this one" possible.
Once the ML inference service is built, every food event gets a vector stored here.

Index on `(user_id, occurred_at DESC)` — all food graph queries hit this index.
Partial index on `enrichment_status` for pending/processing — enrichment workers
query this constantly, only scanning rows that actually need work.

---

### `food_event_nutrition`
The enriched nutritional data. Separate from food_events so it can be
re-computed when models improve without touching the event record.

| Column | Type | Purpose |
|---|---|---|
| dish_name | TEXT | Canonical dish name after enrichment |
| estimated_nutrition | JSONB | `{"protein_g": 24, "carbs_g": 45, "fat_g": 12, "fiber_g": 3, "glycemic_load": 18}` |
| confidence_score | FLOAT | 0.0–1.0. Below 0.7 shown with "~" prefix in UI |
| model_version | TEXT | Which model version produced this estimate |
| ingredients_inferred | JSONB | `["chicken", "turmeric", "coconut milk"]` |
| cuisine_type | TEXT | `"south_indian"`, `"north_indian"`, `"chinese"` etc |
| portion_size_estimate | TEXT | `"small"`, `"medium"`, `"large"` |

---

### `restaurants`
Restaurant data seeded from Zomato/Swiggy/Google Places. Used by the
recommendation engine for candidate generation.

| Column | Type | Purpose |
|---|---|---|
| external_id | TEXT | Zomato or Swiggy's restaurant ID for API calls |
| location | GEOGRAPHY(POINT) | PostGIS type enabling `ST_DWithin` geo queries |
| cuisine_types | JSONB | `["south_indian", "biryani", "seafood"]` |
| avg_cost_for_two | INT | In rupees |
| rating | FLOAT | 0–5 aggregated rating |

GIST spatial index on `location` — makes the "restaurants within 3km" query
run in under 5ms for city-scale datasets.

---

## 7. Auth Service — Every File Explained

```
services/auth/
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── script.py.mako
└── app/
    ├── main.py
    ├── core/
    │   ├── config.py
    │   ├── database.py
    │   ├── redis.py
    │   └── security.py
    ├── models/
    │   └── auth.py
    ├── schemas/
    │   └── auth.py
    ├── dependencies/
    │   └── auth.py
    └── routers/
        └── auth.py
```

### `Dockerfile`
Builds the auth service into a Docker container.
Order: install dependencies first (cached by Docker), copy code second.
On container start: runs `alembic upgrade head` to apply any pending DB migrations,
then starts uvicorn with 2 worker processes.

### `requirements.txt`
13 packages. Key ones:
- `fastapi` + `uvicorn` — web framework and server
- `sqlalchemy[asyncio]` + `asyncpg` — async ORM + Postgres driver
- `alembic` — database migrations
- `python-jose[cryptography]` — JWT encode/decode
- `passlib[bcrypt]` — password hashing
- `redis[hiredis]` — async Redis client with C extension for speed
- `httpx` — async HTTP client (used for Google OAuth API calls)
- `structlog` — structured JSON logging

### `app/core/config.py`
Reads environment variables into a typed `Settings` object using pydantic-settings.
`@lru_cache()` means the settings object is created once and reused — not re-read
from env on every request. All other files import `get_settings()` to access config.

### `app/core/database.py`
Creates the async SQLAlchemy engine with a connection pool:
- `pool_size=10` — 10 connections kept open and ready
- `max_overflow=20` — up to 20 additional connections under load
- `pool_pre_ping=True` — tests each connection before use, handles Neon idle disconnects

The `get_db()` async generator is a FastAPI dependency — each request gets its own
session, commits on success, rolls back on exception, closes when done.

### `app/core/redis.py`
Single shared async Redis connection. `decode_responses=True` means values come
back as Python strings, not bytes. Lazy initialization — connection made on first use.

### `app/core/security.py`
Four functions:

`hash_password(password)` — bcrypt with automatic salt. Takes ~100ms intentionally
(makes brute force slow even with a leaked database).

`verify_password(plain, hashed)` — bcrypt comparison. Constant-time to prevent
timing attacks.

`create_access_token(user_id, email)` — creates a JWT with sub (user_id), email,
type=access, exp (30 min from now), iat (issued at). Signed with HS256.

`generate_refresh_token()` — returns `(raw_token, hashed_token)`. Raw is 64 bytes
of cryptographic randomness from `secrets.token_urlsafe`. Hash is SHA-256.
Caller sends raw to client, stores hash in DB.

### `app/models/auth.py`
SQLAlchemy ORM models. Three classes mapping to three tables.

`RefreshToken.is_valid` property — checks two conditions: not revoked AND not expired.
Used in the refresh endpoint to reject invalid tokens in one check.

### `app/schemas/auth.py`
Pydantic models for request validation and response serialization.

`RegisterRequest` has a `@field_validator` on password that runs before the
handler even starts — rejects weak passwords with a clear error message.

`TokenResponse` is what login and refresh return — both access and refresh tokens,
plus metadata (expires_in in seconds, user_id, email, tier).

### `app/dependencies/auth.py`
`get_current_user_id` is a reusable FastAPI dependency. Any endpoint that needs
authentication just adds `current_user_id: CurrentUserId` to its parameters.

What it does: extracts Bearer token from Authorization header → decodes JWT →
checks Redis blacklist → returns user UUID. No DB query. Pure crypto + cache.

`CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]` is a type alias
so endpoints look clean:
```python
async def get_me(current_user_id: CurrentUserId, db: ...):
```

### `app/routers/auth.py`
All endpoints. 334 lines. Key implementation decisions:

**Register:** Creates User and UserCredential in the same transaction with `flush()`
between them so the user gets an ID before the credential references it.

**Login:** Uses `selectinload(User.credentials)` to load credentials in the same
query as the user — one DB round trip, not two.

**Refresh:** Rotates the token — revokes old one, issues new pair in the same
transaction. If the transaction fails, neither happens. Atomic rotation.

**Logout-all:** Finds all non-revoked, non-expired tokens for the user and sets
`revoked_at` on all of them in one transaction.

**Google OAuth callback:** Handles three cases cleanly:
1. Existing Google user → find by google_sub, return tokens
2. Existing email user → link Google to their account, return tokens
3. New user → create user + credential, return tokens

### `app/main.py`
FastAPI app assembly. CORS configured wide-open for development
(tighten to specific origins when deploying). Request logging middleware
logs method + path + status for every request. Lifespan handler closes
Redis connection cleanly on shutdown.

### `alembic/env.py`
Configures Alembic to use async SQLAlchemy. Imports all models so Alembic
can auto-detect schema changes. Overrides the database URL from environment
variable so the same alembic.ini works in all environments.

---

## 8. API Reference — Auth Endpoints

Base URL: `http://localhost:8001`

All endpoints return JSON. Errors return `{"detail": "message"}`.

### POST /v1/auth/register
Create a new account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "MyPass123"
}
```

Password rules: min 8 chars, at least 1 uppercase, at least 1 digit.

**Response 201:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "message": "Registration successful. Please verify your email."
}
```

**Errors:** 409 if email already exists.

---

### POST /v1/auth/login
Login and receive tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "MyPass123"
}
```

**Response 200:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "dGhpc...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user_id": "uuid",
  "email": "user@example.com",
  "tier": "free"
}
```

Store both tokens. Use `access_token` in `Authorization: Bearer` header.
Use `refresh_token` to get new tokens before the access token expires.

---

### POST /v1/auth/refresh
Get new tokens using refresh token.

**Request:**
```json
{
  "refresh_token": "dGhpc..."
}
```

**Response 200:** Same shape as login response.

The old refresh token is immediately revoked. Use the new one for next refresh.

---

### POST /v1/auth/logout
Revoke refresh token for current device.

Requires: `Authorization: Bearer <access_token>` header.

**Request:**
```json
{
  "refresh_token": "dGhpc..."
}
```

**Response 200:**
```json
{ "message": "Logged out successfully" }
```

---

### POST /v1/auth/logout-all
Revoke all sessions across all devices.

Requires: `Authorization: Bearer <access_token>` header.
No request body.

**Response 200:**
```json
{ "message": "Revoked 3 active sessions" }
```

---

### GET /v1/auth/me
Get current user profile.

Requires: `Authorization: Bearer <access_token>` header.

**Response 200:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "email_verified": false,
  "tier": "free",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### GET /v1/auth/google/authorize
Redirect to Google OAuth consent screen.
Open in browser — redirects to Google, then to callback.

Only works if `GOOGLE_CLIENT_ID` is set in environment.

---

### GET /health
Service health check. Used by Docker.

**Response 200:**
```json
{ "status": "ok", "service": "nara-auth" }
```

---

## 9. What Is Coming Next — Full Roadmap

### Sprint 2 — User Intelligence Service

**What gets built:**
- `POST /v1/health-profile` — set health conditions, dietary restrictions, goals
- `GET /v1/health-profile` — get current profile
- Food graph schema — aggregated rolling windows of nutrition data
- Kafka consumer on `food.events.enriched` → updates food graph
- Pattern detector — identifies nutritional gaps (e.g. low fiber 5 days running)
- Redis hot cache for food graph per user

**Why it comes next:** Every recommendation depends on knowing the user's health context
and eating history. This service is what makes NARA different from a generic food app.

---

### Sprint 3 — Ingestion Service

**What gets built:**
- `POST /v1/meals/log` — text-based meal logging ("had biryani for lunch")
- `POST /v1/meals/photo` — photo upload → S3 → Kafka → ML pipeline
- `POST /v1/meals/import` — bulk Zomato/Swiggy order history import
- `GET /v1/meals/{event_id}/status` — poll enrichment progress
- NLP entity extraction for text logs

**Data starts flowing into the food graph here.**

---

### Sprint 4 — ML Inference Service

**What gets built:**
- EfficientNet-B4 fine-tuned on South Asian cuisine dataset (100K images)
- Nutrition estimation pipeline: dish name → IFCT/USDA lookup → MLP fallback
- Food embedding model (1536-dim vectors stored in pgvector)
- Kafka workers: `photo.upload.pending` → vision → `food.events.raw` → nutrition → `food.events.enriched`
- Triton Inference Server for GPU batching
- Training scripts + Vast.ai GPU setup (under $10 for first training run)

**This is where the vision model comes alive.**

---

### Sprint 5 — Recommendation Service

**Phase 1 — Rule-based ranker:**
- PostGIS candidate generation (restaurants within radius)
- Health constraint bloom filter
- Scoring: nutritional gap fill + cuisine preference + proximity + time-of-day pattern + price fit
- Plain-English explanation builder from top features
- Redis cache on context hash

**Phase 2 — ML ranker (after real interaction data accumulates):**
- LightGBM ranking model trained on `recommendation.feedback` events
- ONNX export → ONNX Runtime serving on CPU (<30ms inference)
- Replaces rule-based scorer, explanation builder adapts to ML feature importance

**Phase 3 — RAG layer:**
- Nutritional knowledge base indexed in pgvector (IFCT, USDA, research summaries)
- Semantic retrieval over KB at query time
- Recommendations become reasoning over retrieved knowledge, not just scoring

**Phase 4 — Wearable integration:**
- Apple HealthKit + Google Fit connectors
- CGM (continuous glucose monitor) data via `wearable.sync.events` Kafka topic
- Recommendations become real-time physiological — blood sugar up right now → lower glycemic options

---

### Sprint 6 — Conversation Agent Service

**What gets built:**
- LangGraph agent graph with 5 specialized agents:
  - PerceptionAgent — extracts location, time, budget, cuisine intent from natural language
  - MemoryAgent — queries food graph for user context
  - ReasoningAgent — applies health constraints, identifies nutritional opportunities
  - RecommendationAgent — calls recommendation service with assembled context
  - ExecutionAgent — places orders, builds meal plans, generates recipes
- WebSocket streaming — response streams token by token
- Redis session state — 30-min conversation memory
- Llama 3.1 8B self-hosted on Ollama for development (zero cost)

**The conversation layer is the face. Everything else is the brain.**

---

### Sprint 7 — Commerce Integration

**What gets built:**
- Restaurant data sync pipeline (Zomato scraper + nightly Celery beat)
- Zomato API wrapper for order placement
- Swiggy API wrapper
- Delivery time estimation via routing API
- Deep-link fallback when direct API access is unavailable

---

### Sprint 8 — API Gateway + Observability

**What gets built:**
- Kong API Gateway: JWT validation, rate limiting per tier, versioning
- Prometheus + Grafana: per-service metrics, Kafka consumer lag, ML confidence distributions
- Jaeger distributed tracing: trace IDs through every service and Kafka message
- Structured logging (ELK/Loki)
- MLflow: model versioning, experiment tracking, A/B testing for recommendation models

---

## 10. Architecture Decisions

**Why async (asyncio) everywhere?**
The auth service and all future services use async Python. This means a single
process can handle hundreds of simultaneous requests without blocking. A sync
implementation blocks the server while waiting for a DB query — async does not.
At recommendation query scale (potentially thousands of concurrent users), this
is the difference between 4 servers and 40.

**Why Kafka instead of direct service calls?**
When a user logs a meal, three things need to happen: vision inference, nutrition
lookup, food graph update. These take 1–5 seconds combined. Making the user wait
is bad UX. Kafka lets the API return "logged" instantly and processes the pipeline
in the background. It also means if the ML service goes down, events queue up and
process when it comes back. Nothing is lost.

**Why pgvector instead of a separate vector database?**
Vector databases (Pinecone, Weaviate) are a separate service to run and pay for.
pgvector stores embeddings as a column in the existing Postgres table. A similarity
query is just SQL. At the scale of one user's meal history (even 10,000 events),
pgvector with HNSW index returns in under 10ms. A separate vector DB would add
network latency and operational complexity for no benefit at this scale.

**Why two token types (access + refresh)?**
Access tokens are short-lived (30 min) so a leaked token is only valid briefly.
Refresh tokens are long-lived (30 days) but stored hashed and rotated on every use.
This gives users persistent login without permanent security exposure.

**Why rule-based recommendations before ML?**
You cannot train a ranking model with no data. The rule-based ranker generates
recommendations from day one, which users interact with, which generates the
`recommendation.feedback` events that train the LightGBM model. You need data
before you can learn from data.




You're right to push back. The ML architecture as planned is actually much deeper than one model. Let me lay out the full picture.

---

## Every ML Model In The Full System

### Layer 1 — Perception (Understanding What You Ate)

**Vision Model — EfficientNet-B4 / ConvNeXt**
Photo → dish classification. But this is just the entry point. Fine-tuned on Indian cuisine specifically — not ImageNet generalization. Outputs top-5 dish candidates with confidence scores.

**Multimodal Fallback — Claude Vision / GPT-4V**
When vision model confidence is below 0.4, kicks in a multimodal LLM that looks at the image AND reasons about it. More expensive but handles edge cases — home cooked food, fusion dishes, unclear photos.

**OCR + NLP for Text Logs**
When user types "had dal makhani with two rotis and a small raita", a named entity recognition model extracts dish names, quantities, modifiers. Not a simple keyword match — understands "light" vs "heavy", "small bowl", "extra ghee".

**Barcode Scanner Model**
For packaged food — OCR on barcode → USDA/OpenFoodFacts lookup → exact nutrition. No estimation needed.

---

### Layer 2 — Nutrition Intelligence

**Nutrition Estimation MLP**
When a dish isn't in the knowledge base (home cooked variations, regional dishes), a multi-layer perceptron trained on dish-ingredient-nutrition triplets estimates macros from inferred ingredients. Handles "dal with extra ghee" differently from "plain dal".

**Portion Size Estimator**
Separate CV model that estimates portion size from photo — uses reference objects in frame (plate diameter, hand size) to estimate grams. Feeds into nutrition calculation. A "medium biryani" at a dhaba vs a restaurant are very different portions.

**Glycemic Load Predictor**
Specific to NARA's health angle. Predicts glycemic load of a meal from ingredients + cooking method + portion. Critical for diabetic/prediabetic users. Not just glycemic index of individual foods — actual meal-level glycemic load considering interactions.

---

### Layer 3 — User Modelling

**Food Embedding Model — Fine-tuned SBERT**
Every meal gets a 1536-dim semantic vector encoding dish type, cuisine, nutrition profile, meal occasion. Trained on food description pairs. Powers "find meals similar to this one" and preference clustering.

**Preference Learning Model — Collaborative Filtering**
Learns implicit preferences from behavior — not just what you say you like but what you actually order repeatedly, what you skip, what time of day you order what. Matrix factorization style, updated continuously from interaction events.

**Health State Model**
Tracks nutritional state as a time series. Not just "average protein this week" — detects trends, velocity of change, correlations between eating patterns and wearable data. Flags when someone is consistently missing targets vs occasionally missing them.

**Cuisine Affinity Model**
Learns your actual cuisine preferences at the dish level, not just cuisine level. You might love North Indian but hate certain dishes. Builds a personal food affinity graph that gets more accurate with every meal.

---

### Layer 4 — Recommendation

**Candidate Generation — Two-Tower Model**
A user tower encodes your food graph + health state + context into a vector. A restaurant/dish tower encodes every dish into a vector. Fast approximate nearest neighbor search finds candidates whose dish vector is close to your user vector. This replaces the simple geo + filter approach for deeper personalization.

**Ranking Model — LightGBM → Neural Ranker**
LightGBM first (interpretable, fast to train, works with small data). As interaction data grows, upgrades to a neural ranker (deep learning on the full feature set). The neural ranker can capture non-linear interactions between features that LightGBM misses.

**Multi-Armed Bandit — LinUCB**
Balances exploration vs exploitation. Doesn't just recommend what it's most confident about — occasionally tries new recommendations to discover new preferences. LinUCB with contextual features (time of day, location, recent nutrition) makes the exploration intelligent rather than random.

**RAG Recommendation Layer**
Query the nutritional knowledge base semantically. "User has prediabetes, low fiber, high stress week" → retrieve relevant research on what foods help → feed into reasoning layer → recommendation grounded in actual nutritional science, not just pattern matching.

---

### Layer 5 — Conversation Intelligence

**Intent Classifier**
Lightweight BERT-style classifier — is this message a food query, health question, order request, general chat, or ambiguous? Routes to the right agent. Needs to be fast — runs on every message before anything else.

**NER for Food Entities**
Fine-tuned NER model for food domain. Extracts: dish names, cuisine types, locations, budget, time constraints, health context from natural language. "Something light near Vastrapur under 300" → structured query.

**Llama 3.1 8B Fine-tuned on Food Domain**
The core conversation LLM. Fine-tuned specifically on food, nutrition, and health conversations in Indian context. Knows regional cuisines, local restaurant types, Indian health contexts. Far better than a generic LLM for this specific domain.

**Response Quality Scorer**
A small model that scores the agent's planned response before sending — checks for hallucination risk, health advice accuracy, recommendation relevance. Acts as a gate before the response reaches the user.

---

### Layer 6 — Wearable Integration ML

**CGM Pattern Analyser**
When continuous glucose monitor data is connected, a time-series model analyses glucose response patterns to different meals. Learns YOUR personal glycemic response — because the same food affects different people differently. This is genuinely cutting-edge personalization.

**Activity-Nutrition Correlation Model**
Cross-correlates fitness tracker data (steps, workout intensity, sleep quality) with nutrition data. Recommendations change based on your activity — rest day vs post-workout day are completely different nutritional needs.

**Anomaly Detector**
Detects unusual patterns — sudden change in eating habits, missed meals, unusual glucose spikes. Feeds into proactive nudges ("you haven't logged anything today, your glucose data suggests you ate — want to log it?").

---

### Layer 7 — Continuous Learning

**Online Learning Pipeline**
Models don't just train once and freeze. Every interaction is a signal. The preference model updates continuously. The ranking model retrains weekly on accumulated feedback. The nutrition estimator improves as more dishes get verified.

**A/B Testing Framework**
Every model upgrade runs as an experiment — new ranking model to 10% of users, measure recommendation acceptance rate, promote or rollback. MLflow tracks every experiment. Nothing goes to 100% without proving itself.

**Federated Learning (future)**
When user base grows — train personalization models on-device so raw health data never leaves the phone. Only model gradients sync to the server. This is the privacy-preserving ML architecture that makes NARA trustworthy for sensitive health data.

---

## The Model Count

| Layer | Models |
|---|---|
| Perception | Vision classifier, Multimodal LLM fallback, Food NER, Barcode OCR |
| Nutrition | Nutrition MLP, Portion estimator, Glycemic load predictor |
| User modelling | Food embeddings, Collaborative filter, Health state tracker, Cuisine affinity |
| Recommendation | Two-tower candidate gen, LightGBM ranker, Neural ranker, LinUCB bandit, RAG retriever |
| Conversation | Intent classifier, Food NER, Llama 3.1 fine-tuned, Response quality scorer |
| Wearables | CGM pattern analyser, Activity-nutrition correlator, Anomaly detector |
| Infrastructure | Online learning pipeline, A/B testing, Federated learning |

That's roughly 20 distinct models across 7 layers. Some are small and fast (intent classifier — runs in milliseconds on CPU). Some are heavy and async (vision model, neural ranker — GPU batch processing). Some are continuous (online learning — always updating in background).

This is not a basic ML system. Built fully, this is genuinely research-grade personalization applied to a real consumer product. The kind of thing a well-funded food tech startup would spend 18 months building with a team of 6 ML engineers. We're building it in 8 weeks because I write the code and you run it.