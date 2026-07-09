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
    throw new Error(err.detail || "Request failed");
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

  // FIX 3: safety-net synchronous recompute, called right after a meal
  // log so the next getFoodGraph() call is guaranteed fresh instead of
  // racing the async Kafka enrichment pipeline. Requires
  // food_graph_recompute.py wired into user-intelligence service.
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
  // FIX 2: occasion is now sent and the backend treats it as STRICT
  // filtering when present, so the UI tabs actually change results.
  get: (lat, lng, occasion, n = 10) => {
    const params = new URLSearchParams({ n });
    if (lat != null) params.append("lat", lat);
    if (lng != null) params.append("lng", lng);
    if (occasion) params.append("occasion", occasion);
    return request(`${BASE.recommendation}/v1/recommend/?${params}`, {
      headers: authHeaders(),
    });
  },

  // FIX 5: combined dish + nearby restaurant recommendations
  getWithRestaurants: (lat, lng, occasion, n = 10, radiusKm = 5) => {
    const params = new URLSearchParams({ n, radius_km: radiusKm, lat, lng });
    if (occasion) params.append("occasion", occasion);
    return request(`${BASE.recommendation}/v1/recommend/with-restaurants?${params}`, {
      headers: authHeaders(),
    });
  },

  coldStart: (profile) => {
    const params = new URLSearchParams(profile);
    return request(`${BASE.recommendation}/v1/recommend/cold-start?${params}`, {
      headers: authHeaders(),
    });
  },

  nearbyRestaurants: (lat, lng, radius = 5, cuisine = null) => {
    const params = new URLSearchParams({ lat, lng, radius_km: radius });
    if (cuisine) params.append("cuisine", cuisine);
    return request(`${BASE.recommendation}/v1/recommend/nearby-restaurants?${params}`, {
      headers: authHeaders(),
    });
  },
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