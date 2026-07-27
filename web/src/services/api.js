// NARA — API Service Layer
// All backend calls in one place

const BASE = {
  auth:           "http://localhost:8001",
  userIntel:      "http://localhost:8002",
  ingestion:      "http://localhost:8003",
  mlInference:    "http://localhost:8004",
  recommendation: "http://localhost:8005",
  conversation:   "http://localhost:8006",
};

function getToken() {
  return localStorage.getItem("nara_token");
}

function authHeaders() {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${getToken()}`,
  };
}

async function request(url, options = {}) {
  const res = await fetch(url, options);
  if (res.status === 401) {
    localStorage.removeItem("nara_token");
    window.location.href = "/login";
    return null;
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const message = typeof err.detail === "string" ? err.detail : (err.detail?.message || "Request failed");
    const error = new Error(message);
    error.status = res.status;
    error.body   = err.detail;
    throw error;
  }
  return res.json();
}

// ── Auth ───────────────────────────────────────────────────────
export const auth = {
  register: (email, password) =>
    request(`${BASE.auth}/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }),

  login: (email, password) =>
    request(`${BASE.auth}/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    }),

  logout: () =>
    request(`${BASE.auth}/v1/auth/logout`, {
      method: "POST",
      headers: authHeaders(),
    }),
};

// ── User Intelligence ──────────────────────────────────────────
export const user = {
  getHealthProfile: () =>
    request(`${BASE.userIntel}/v1/health-profile`, { headers: authHeaders() }),

  saveHealthProfile: (data) =>
    request(`${BASE.userIntel}/v1/health-profile`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(data),
    }),

  getFoodGraph: () =>
    request(`${BASE.userIntel}/v1/food-graph`, { headers: authHeaders() }),

  recomputeFoodGraph: () =>
    request(`${BASE.userIntel}/v1/food-graph/recompute`, {
      method: "POST",
      headers: authHeaders(),
    }),
};

// ── Ingestion ──────────────────────────────────────────────────
export const meals = {
  logText: (description, context = {}) =>
    request(`${BASE.ingestion}/v1/meals/log`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        description,
        context: {
          occasion: context.occasion || "lunch",
          location_type: context.location_type || "home",
          ...context,
        },
      }),
    }),

  getHistory: (page = 1, pageSize = 20) =>
    request(
      `${BASE.ingestion}/v1/meals/history?page=${page}&page_size=${pageSize}`,
      { headers: authHeaders() }
    ),

  getEventStatus: (eventId) =>
    request(`${BASE.ingestion}/v1/meals/${eventId}/status`, {
      headers: authHeaders(),
    }),
};

// ── Recommendations ────────────────────────────────────────────
export const recommendations = {
  get: (lat, lng, occasion, n = 10) => {
    const params = new URLSearchParams({ n });
    if (lat != null) params.append("lat", lat);
    if (lng != null) params.append("lng", lng);
    if (occasion) params.append("occasion", occasion);
    return request(`${BASE.recommendation}/v1/recommend/?${params}`, {
      headers: authHeaders(),
    });
  },

  getWithRestaurants: (lat, lng, occasion, n = 10) => {
    const params = new URLSearchParams({ n, lat, lng });
    if (occasion) params.append("occasion", occasion);
    return request(`${BASE.recommendation}/v1/recommend/with-restaurants?${params}`, {
      headers: authHeaders(),
    });
  },

  nearbyRestaurants: (lat, lng, cuisine = null) => {
    const params = new URLSearchParams({ lat, lng });
    if (cuisine) params.append("cuisine", cuisine);
    return request(`${BASE.recommendation}/v1/recommend/nearby-restaurants?${params}`, {
      headers: authHeaders(),
    });
  },
};

// ── Restaurants ────────────────────────────────────────────────
export const restaurants = {
  // GET /v1/recommend/restaurants/{id} — restaurant details + full ranked
  // menu from restaurant_menu_items, each dish scored by the full ensemble
  // pipeline with real price_match_score. This is what RestaurantDetail
  // calls when you tap a restaurant card.
  // FIX: this was missing the /recommend prefix segment that the actual
  // router (recommend.py, APIRouter(prefix="/v1/recommend")) is mounted
  // under — every request 404'd, which is why RestaurantDetail.jsx always
  // showed "Couldn't load menu" no matter what.
  getMenu: (restaurantId) =>
    request(`${BASE.recommendation}/v1/recommend/restaurants/${restaurantId}`, {
      headers: authHeaders(),
    }),
};

// ── Orders (cart + checkout, no payment) ─────────────────────────
// Backed by orders/order_items in Neon — see
// services/recommendation/app/migrations/003_orders.sql and
// services/recommendation/app/routers/orders.py for the full design:
// one order row per cart end-to-end (cart -> placed is the SAME row,
// never a second row), restaurant_id/dish_name validated against local
// Postgres at the application layer since they can't be real
// cross-database foreign keys.
export const orders = {
  getCart: () =>
    request(`${BASE.recommendation}/v1/orders/cart`, { headers: authHeaders() }),

  // Throws with error.status === 409 and error.body = { message,
  // existing_cart_id, existing_restaurant_id } if the user already has an
  // open cart for a different restaurant — the caller should catch this
  // and prompt to clear the existing cart before retrying.
  addCartItem: (restaurantId, dishName, cuisineType, quantity = 1, sessionId = null) =>
    request(`${BASE.recommendation}/v1/orders/cart/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        restaurant_id: restaurantId,
        dish_name:     dishName,
        cuisine_type:  cuisineType,
        quantity,
        session_id:    sessionId,
      }),
    }),

  removeCartItem: (dishName) =>
    request(`${BASE.recommendation}/v1/orders/cart/items/${encodeURIComponent(dishName)}`, {
      method: "DELETE",
      headers: authHeaders(),
    }),

  clearCart: () =>
    request(`${BASE.recommendation}/v1/orders/cart`, {
      method: "DELETE",
      headers: authHeaders(),
    }),

  checkout: () =>
    request(`${BASE.recommendation}/v1/orders/checkout`, {
      method: "POST",
      headers: authHeaders(),
    }),

  history: () =>
    request(`${BASE.recommendation}/v1/orders/history`, { headers: authHeaders() }),
};

// ── Conversation ───────────────────────────────────────────────
export const conversation = {
  chat: (message, sessionId) =>
    request(`${BASE.conversation}/v1/chat/`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ message, session_id: sessionId }),
    }),
};

// ── ML Inference ───────────────────────────────────────────────
export const mlInference = {
  lookupDish: (dish) =>
    request(`${BASE.mlInference}/debug/lookup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dish }),
    }),

  getMetrics: () =>
    request(`${BASE.mlInference}/metrics`, {
      headers: { "Content-Type": "application/json" },
    }),
};