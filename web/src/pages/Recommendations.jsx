// NARA — Recommendations (redesigned)
// Restaurant cards are now the primary view. Each card shows:
//   - Name, area, rating, distance, delivery time
//   - 2-3 top dish chips from that restaurant's real menu
//   - Tap anywhere on the card → RestaurantDetail page (ranked full menu)
//
// Dish-only mode activates when location is unavailable — falls back to
// the standard recommendation list, no restaurant matching.
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { recommendations } from "../services/api";
import { useFoodGraphVersion } from "../context/AppContext";

const OCCASIONS = [
  { id: null,        label: "For You"   },
  { id: "breakfast", label: "Breakfast" },
  { id: "lunch",     label: "Lunch"     },
  { id: "snack",     label: "Snack"     },
  { id: "dinner",    label: "Dinner"    },
];

const CUISINE_EMOJI = {
  south_indian: "🥘", north_indian: "🍛", biryani: "🍚",
  street_food: "🌮",  gujarati: "🫓",     maharashtrian: "🥙",
  bengali: "🐟",      rajasthani: "🫕",   dessert: "🍮",
  beverage: "☕",     staple: "🍽",       goan: "🍤",
};

function cuisineEmoji(c) { return CUISINE_EMOJI[c] || "🍽"; }

// ── Restaurant card ────────────────────────────────────────────
function RestaurantCard({ restaurant, topDishes, index, onClick }) {
  const cuisines = Array.isArray(restaurant.cuisine_types)
    ? restaurant.cuisine_types
    : Object.keys(restaurant.cuisine_types || {});

  // Up to 3 dish chips visible on the card without tapping
  const chips = topDishes.slice(0, 3);

  return (
    <div
      onClick={onClick}
      style={{
        background:   "var(--surface)",
        border:       "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        padding:      "18px",
        cursor:       "pointer",
        animation:    `fadeUp 0.3s ease ${index * 0.05}s both`,
        transition:   "border-color 0.2s, transform 0.15s",
      }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = "var(--border-light)";
        e.currentTarget.style.transform   = "translateY(-1px)";
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = "var(--border)";
        e.currentTarget.style.transform   = "translateY(0)";
      }}
    >
      {/* Header row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: "16px", fontWeight: 700, marginBottom: "3px", textTransform: "capitalize" }}>
            {restaurant.name}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
            {restaurant.area}
            {restaurant.distance_km != null ? ` · ${restaurant.distance_km} km` : ""}
            {restaurant.avg_cost_for_two ? ` · ₹${restaurant.avg_cost_for_two} for two` : ""}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "4px", flexShrink: 0, marginLeft: "12px" }}>
          {restaurant.rating && (
            <span style={{ fontSize: "12px", color: "var(--yellow)", fontWeight: 700 }}>
              ★ {restaurant.rating}
            </span>
          )}
          {restaurant.delivery_enabled && (
            <span className="badge badge-blue" style={{ fontSize: "9px" }}>
              {restaurant.delivery_time_min ? `${restaurant.delivery_time_min} min` : "delivery"}
            </span>
          )}
        </div>
      </div>

      {/* Cuisine tags */}
      {cuisines.length > 0 && (
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "12px" }}>
          {cuisines.slice(0, 3).map(c => (
            <span key={c} className="badge badge-purple" style={{ fontSize: "9px" }}>
              {cuisineEmoji(c)} {c.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}

      {/* Dish chips — the key difference from the old design:
          you can see what this restaurant serves without tapping in */}
      {chips.length > 0 && (
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          {chips.map((dish, i) => (
            <div
              key={i}
              style={{
                padding:      "5px 10px",
                borderRadius: "100px",
                background:   "var(--surface-2)",
                border:       "1px solid var(--border)",
                fontSize:     "11px",
                color:        "var(--text-secondary)",
                textTransform:"capitalize",
                display:      "flex",
                alignItems:   "center",
                gap:          "4px",
              }}
            >
              {cuisineEmoji(dish.cuisine_type)}
              {dish.dish_name?.replace(/_/g, " ")}
              {dish.price && (
                <span style={{ color: "var(--text-tertiary)" }}>· ₹{Math.round(dish.price)}</span>
              )}
              {dish.health_compliant && (
                <span style={{ color: "var(--green)", fontSize: "9px" }}>✓</span>
              )}
            </div>
          ))}
          {topDishes.length > 3 && (
            <div style={{
              padding: "5px 10px", borderRadius: "100px",
              background: "var(--surface-2)", border: "1px solid var(--border)",
              fontSize: "11px", color: "var(--text-secondary)",
            }}>
              +{topDishes.length - 3} more →
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Dish-only card (when no location available) ────────────────
function DishCard({ rec, index }) {
  const n = rec.nutrition || {};
  return (
    <div
      style={{
        background:   "var(--surface)",
        border:       "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        padding:      "16px",
        animation:    `fadeUp 0.3s ease ${index * 0.04}s both`,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
        <div>
          <div style={{ fontSize: "15px", fontWeight: 600, textTransform: "capitalize", marginBottom: "3px" }}>
            {cuisineEmoji(rec.cuisine_type)} {rec.dish_name?.replace(/_/g, " ")}
          </div>
          <div style={{ display: "flex", gap: "6px" }}>
            {rec.is_veg && <span className="badge badge-green" style={{ fontSize: "9px" }}>veg</span>}
            {rec.health_compliant
              ? <span className="badge badge-green" style={{ fontSize: "9px" }}>✓ healthy</span>
              : <span className="badge badge-yellow" style={{ fontSize: "9px" }}>⚠ moderate</span>
            }
          </div>
        </div>
        <div style={{ fontSize: "12px", color: "var(--text-secondary)", textAlign: "right" }}>
          {n.calories && <div>{Math.round(n.calories)} kcal</div>}
          {n.protein_g && <div>{Math.round(n.protein_g)}g protein</div>}
        </div>
      </div>
      {rec.health_reasons?.length > 0 && rec.health_reasons.map((r, i) => (
        <div key={i} style={{ fontSize: "11px", color: "var(--yellow)", marginTop: "4px" }}>⚠ {r}</div>
      ))}
    </div>
  );
}

// Default fallback location — used whenever real geolocation isn't available
// (denied, unsupported, or timed out). This is where the seeded restaurant
// data actually lives right now, so falling back to `null` meant the
// restaurant view could never render for anyone who didn't grant location
// access. Swap this for a smarter default (user's saved city, IP-based geo,
// etc.) once that's wired up — for now it just needs to point at real data.
const DEFAULT_LOCATION = { lat: 12.9716, lng: 77.5946 }; // Bengaluru

// ── Main page ──────────────────────────────────────────────────
export default function Recommendations() {
  const navigate     = useNavigate();
  const graphVersion = useFoodGraphVersion();
  const [occasion,  setOccasion]  = useState(null);
  const [data,      setData]      = useState(null);
  const [loading,   setLoading]   = useState(true);
  const [location,  setLocation]  = useState(null);
  const [locState,  setLocState]  = useState("pending"); // pending | ok | fallback

  useEffect(() => {
    if (!navigator.geolocation) {
      setLocation(DEFAULT_LOCATION);
      setLocState("fallback");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      pos => {
        setLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setLocState("ok");
      },
      () => {
        // Denied or errored — still show restaurants, just using the
        // default location instead of the user's real one.
        setLocation(DEFAULT_LOCATION);
        setLocState("fallback");
      },
      { timeout: 6000 }
    );
  }, []);

  useEffect(() => {
    if (locState === "pending") return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        // location is now always set (real or Bengaluru fallback) by the
        // time locState leaves "pending", so this always requests the
        // restaurant-aware endpoint.
        const result = await recommendations.getWithRestaurants(
          location.lat, location.lng, occasion, 20
        );
        if (!cancelled) setData(result);
      } catch {
        if (!cancelled) setData(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [occasion, location, locState, graphVersion]);

  // Build restaurant view from the with-restaurants response.
  // Each rec can carry nearby_restaurants; we invert this to a
  // restaurant-primary list, with the top dishes per restaurant.
  const restaurantMap = {};
  (data?.recommendations || []).forEach(rec => {
    (rec.nearby_restaurants || []).forEach(r => {
      if (!restaurantMap[r.id]) {
        restaurantMap[r.id] = { restaurant: r, dishes: [] };
      }
      if (restaurantMap[r.id].dishes.length < 6) {
        restaurantMap[r.id].dishes.push(rec);
      }
    });
  });
  const restaurantList = Object.values(restaurantMap);
  const dishOnly = restaurantList.length === 0;

  return (
    <div className="page">
      {/* Header */}
      <div style={{ padding: "56px 24px 16px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: 800, letterSpacing: "-0.03em", marginBottom: "6px" }}>
          Discover
        </h1>
        <div style={{ fontSize: "12px", color: locState === "ok" ? "var(--green)" : "var(--text-secondary)" }}>
          {locState === "pending"  && "Getting your location..."}
          {locState === "ok"       && "📍 Showing restaurants near you"}
          {locState === "fallback" && "📍 Showing restaurants in Bengaluru — enable location for results near you"}
        </div>
      </div>

      {/* Occasion tabs */}
      <div style={{ display: "flex", gap: "8px", padding: "0 24px", overflowX: "auto", marginBottom: "20px", paddingBottom: "4px" }}>
        {OCCASIONS.map(o => (
          <button
            key={o.label}
            onClick={() => setOccasion(o.id)}
            style={{
              padding:    "8px 18px",
              borderRadius: "100px",
              background: occasion === o.id ? "var(--text-primary)" : "var(--surface)",
              color:      occasion === o.id ? "var(--bg)" : "var(--text-secondary)",
              border:     `1px solid ${occasion === o.id ? "var(--text-primary)" : "var(--border)"}`,
              fontSize:   "13px",
              fontWeight: occasion === o.id ? 600 : 400,
              whiteSpace: "nowrap",
              transition: "all 0.2s",
            }}
          >
            {o.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ padding: "0 24px", display: "flex", flexDirection: "column", gap: "12px" }}>
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card" style={{ height: "140px", animation: "pulse 1.5s ease infinite" }} />
          ))
        ) : dishOnly ? (
          // No location or no restaurant matches — show plain dish list
          (data?.recommendations || []).length === 0 ? (
            <div style={{ textAlign: "center", padding: "60px 0", color: "var(--text-secondary)" }}>
              <div style={{ fontSize: "40px", marginBottom: "16px" }}>🍽</div>
              <div style={{ fontSize: "16px", fontWeight: 500 }}>No recommendations yet</div>
              <div style={{ fontSize: "13px", marginTop: "6px" }}>Log some meals first</div>
            </div>
          ) : (
            (data?.recommendations || []).map((rec, i) => (
              <DishCard key={`${rec.dish_name}-${i}`} rec={rec} index={i} />
            ))
          )
        ) : (
          // Restaurant-first view
          restaurantList.length === 0 ? (
            <div style={{ textAlign: "center", padding: "60px 0", color: "var(--text-secondary)" }}>
              <div style={{ fontSize: "40px", marginBottom: "16px" }}>📍</div>
              <div style={{ fontSize: "16px", fontWeight: 500 }}>No restaurants nearby</div>
              <div style={{ fontSize: "13px", marginTop: "6px" }}>Try expanding your range</div>
            </div>
          ) : (
            restaurantList.map(({ restaurant, dishes }, i) => (
              <RestaurantCard
                key={restaurant.id}
                restaurant={restaurant}
                topDishes={dishes}
                index={i}
                onClick={() => navigate(`/restaurant/${restaurant.id}`, {
                  state: { restaurant, sessionId: data?.session_id || null }
                })}
              />
            ))
          )
        )}
      </div>
    </div>
  );
}