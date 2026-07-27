# NARA Recommendation Pipeline — End-to-End Test Report

Generated: 2026-07-25T18:43:53.729530+00:00

## Scope and honest limitations

- This report covers 5 independently created, non-overlapping user profiles run against the **real running services** — no mocked data, no production code modified to produce this.
- Cuisine-match percentages are a **soft expectation check**, not a pass/fail contract — cuisine_affinity is one blended signal among several (region prior, health compliance, diversification, reorder boost), so 100% match is not the bar; a near-0% match for a strong-affinity profile IS worth investigating.
- **Standalone-vs-ensemble per-model scores are NOT included** — that data isn't exposed by any current endpoint, and adding a debug endpoint to expose it was deliberately not done without separate explicit approval (see script docstring).

---

## user1_riya_delhi

**Profile note:** No conditions, no restrictions, non-veg, north Indian meals — a clean baseline warm-start profile.

- Auth: `ok` (user_id: `e8c82126-8ee6-49c9-bcab-db4165e44778`)
- Onboarding: HTTP `201`

### Meals logged

| Description | Occasion | Enrichment status |
|---|---|---|
| Had chole bhature for breakfast | breakfast | done |
| Butter chicken with naan for lunch | lunch | done |
| Paratha with curd for dinner | snack | done |
| Samosa and chai as an evening snack | dinner | done |

### Recommendations — BEFORE any click/order

| Occasion | HTTP | Dishes returned | Cuisine-match check | Top 3 dishes (score) |
|---|---|---|---|---|
| breakfast | 200 | 10 | 2/10 (20.0%) tagged 'north_indian' | paratha (0.5822), paneer bhurji (0.5622), idli (0.3187) |
| lunch | 200 | 10 | 2/10 (20.0%) tagged 'north_indian' | chole (0.5822), naan (0.5819), masala dosa (0.321) |
| snack | 200 | 10 | 1/10 (10.0%) tagged 'north_indian' | chicken tikka (0.5618), idli (0.2709), samosa (0.2469) |
| dinner | 200 | 10 | 2/10 (20.0%) tagged 'north_indian' | pulao (0.5622), dal makhani (0.5622), gatte ki sabzi (0.3069) |

### Simulated click + checkout

- Occasion used: **breakfast**
- Dish ordered: **jalebi** (dessert) from **Ibaco**
- Add-to-cart: HTTP `200`
- Checkout: HTTP `200`

### Recommendations — AFTER checkout (same occasion)

- `jalebi` rank before: **6**
- `jalebi` rank after:  **3**
- Movement: **+3** positions (improved)

| Occasion | Top 3 AFTER checkout (score) |
|---|---|
| breakfast | aloo paratha (0.5622), gobi paratha (0.5622), idli (0.2709) |

---

## user2_aarav_ahmedabad

**Profile note:** Vegetarian + Jain, Gujarati meals — tests hard dietary filtering + strong single-cuisine affinity.

- Auth: `ok` (user_id: `bacb5d03-a609-4929-97d9-6e582df64ea3`)
- Onboarding: HTTP `201`

### Meals logged

| Description | Occasion | Enrichment status |
|---|---|---|
| Khichadi with kadhi for lunch | breakfast | done |
| Dhokla for breakfast | lunch | done |
| Thepla and chai as a snack | snack | done |
| Undhiyu for dinner | dinner | done |

### Recommendations — BEFORE any click/order

| Occasion | HTTP | Dishes returned | Cuisine-match check | Top 3 dishes (score) |
|---|---|---|---|---|
| breakfast | 200 | 10 | 2/10 (20.0%) tagged 'gujarati' | dhokla (0.583), thepla (0.563), puri (0.4875) |
| lunch | 200 | 10 | 2/10 (20.0%) tagged 'gujarati' | undhiyu (0.583), gujarati kadhi (0.5633), jeera rice (0.4877) |
| snack | 200 | 10 | 2/10 (20.0%) tagged 'gujarati' | sukhdi (0.5633), khandvi (0.5632), ukdiche modak (0.4275) |
| dinner | 200 | 10 | 2/10 (20.0%) tagged 'gujarati' | rotlo (0.5631), dal dhokli (0.563), naan (0.4875) |

### Simulated click + checkout

- Occasion used: **dinner**
- Dish ordered: **roti** (north_indian) from **Devi Sri Juice and Condiments**
- Add-to-cart: HTTP `400`
- Checkout: HTTP `400`

### Recommendations — AFTER checkout (same occasion)

- `roti` rank before: **not in top 10**
- `roti` rank after:  **not in top 10**

| Occasion | Top 3 AFTER checkout (score) |
|---|---|
| dinner | rotlo (0.5631), dal dhokli (0.563), naan (0.4875) |

---

## user3_sourav_kolkata

**Profile note:** type2_diabetes declared — tests health_score_dish / GI-aware filtering and health_reasons actually appearing on flagged high-GI dishes (mishti doi, luchi).

- Auth: `ok` (user_id: `d89b6cef-2747-4d9f-97a6-acf3f76f993a`)
- Onboarding: HTTP `201`

### Meals logged

| Description | Occasion | Enrichment status |
|---|---|---|
| Macher jhol with rice for lunch | breakfast | done |
| Luchi and alur dom for breakfast | lunch | done |
| Mishti doi as dessert | snack | done |
| Shorshe ilish for dinner | dinner | done |

### Recommendations — BEFORE any click/order

| Occasion | HTTP | Dishes returned | Cuisine-match check | Top 3 dishes (score) |
|---|---|---|---|---|
| breakfast | 200 | 10 | 1/10 (10.0%) tagged 'bengali' | idli (0.6535), luchi (0.5807), dosa (0.5698) |
| lunch | 200 | 10 | 2/10 (20.0%) tagged 'bengali' | masala dosa (0.6513), pesarattu upma (0.5636), shorshe ilish (0.5624) |
| snack | 200 | 10 | 0/10 (0.0%) tagged 'bengali' | idli (0.5555), rava dosa (0.5078), samosa (0.2479) |
| dinner | 200 | 10 | 2/10 (20.0%) tagged 'bengali' | pongal festival dish (0.5693), machher jhol (0.5623), chingri malai curry (0.5623) |

### Simulated click + checkout

- Occasion used: **lunch**
- Dish ordered: **masala dosa** (south_indian) from **Aaha Thindi**
- Add-to-cart: HTTP `200`
- Checkout: HTTP `200`

### Recommendations — AFTER checkout (same occasion)

- `masala dosa` rank before: **0**
- `masala dosa` rank after:  **0**
- Movement: **0** positions (no change)

| Occasion | Top 3 AFTER checkout (score) |
|---|---|
| lunch | masala dosa (0.5838), luchi (0.4936), lemon rice (0.4875) |

---

## user4_meera_bengaluru

**Profile note:** Low income_tier + vegetarian + South Indian meals — tests price_match_score behavior and warm-start with a distinct cuisine from users 1-3.

- Auth: `ok` (user_id: `f889f4fc-ed94-4924-9c6d-e2960730cd2b`)
- Onboarding: HTTP `201`

### Meals logged

| Description | Occasion | Enrichment status |
|---|---|---|
| Idli sambar for breakfast | breakfast | done |
| Masala dosa for lunch | lunch | done |
| Rava upma as a snack | snack | done |
| Curd rice for dinner | dinner | done |

### Recommendations — BEFORE any click/order

| Occasion | HTTP | Dishes returned | Cuisine-match check | Top 3 dishes (score) |
|---|---|---|---|---|
| breakfast | 200 | 10 | 2/10 (20.0%) tagged 'south_indian' | idli (0.6954), dosa (0.6563), paneer bhurji (0.4866) |
| lunch | 200 | 10 | 2/10 (20.0%) tagged 'south_indian' | masala dosa (0.6948), pesarattu upma (0.6392), pulao (0.4866) |
| snack | 200 | 10 | 2/10 (20.0%) tagged 'south_indian' | idli (0.5911), rava dosa (0.575), jaljeera (0.1897) |
| dinner | 200 | 10 | 2/10 (20.0%) tagged 'south_indian' | pongal festival dish (0.6392), pesarattu upma (0.5906), dal makhani (0.4866) |

### Simulated click + checkout

- Occasion used: **lunch**
- Dish ordered: **gatte ki sabzi** (rajasthani) from **Jaypore Delights**
- Add-to-cart: HTTP `400`
- Checkout: HTTP `400`

### Recommendations — AFTER checkout (same occasion)

- `gatte ki sabzi` rank before: **not in top 10**
- `gatte ki sabzi` rank after:  **not in top 10**

| Occasion | Top 3 AFTER checkout (score) |
|---|---|
| lunch | masala dosa (0.6948), pesarattu upma (0.6392), pulao (0.4866) |

---

## user5_priyanka_guwahati

**Profile note:** TRUE COLD START — zero meals logged, two conditions declared. Tests whether cold-start/region-prior fallback produces a sane, non-empty, health-aware list with no behavioral data at all.

- Auth: `ok` (user_id: `6d1072ab-f036-42d4-94f1-f3ed5ad805ca`)
- Onboarding: HTTP `201`

### Meals logged

*(none — deliberate true cold-start profile)*

### Recommendations — BEFORE any click/order

| Occasion | HTTP | Dishes returned | Cuisine-match check | Top 3 dishes (score) |
|---|---|---|---|---|
| breakfast | 200 | 10 | N/A (no behavioral signal expected for this profile) | paneer bhurji (0.8), paratha (0.8), chole bhature (0.4) |
| lunch | 200 | 10 | N/A (no behavioral signal expected for this profile) | pulao (0.8), jeera rice (0.8), kathi roll (0.4) |
| snack | 200 | 10 | N/A (no behavioral signal expected for this profile) | chicken tikka (0.8), samosa (0.4), pani puri (0.4) |
| dinner | 200 | 10 | N/A (no behavioral signal expected for this profile) | dal makhani (0.8), dal tadka (0.8), kathi roll (0.34) |

### Simulated click + checkout

- Occasion used: **snack**
- Dish ordered: **jalebi** (dessert) from **Belgian Waffles**
- Add-to-cart: HTTP `200`
- Checkout: HTTP `200`

### Recommendations — AFTER checkout (same occasion)

- `jalebi` rank before: **not in top 10**
- `jalebi` rank after:  **3**

| Occasion | Top 3 AFTER checkout (score) |
|---|---|
| snack | chicken tikka (0.68), bhel puri (0.4), sev puri (0.4) |

---
