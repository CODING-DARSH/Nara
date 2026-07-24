// NARA — Restaurant Detail
// Shows a restaurant's full menu ranked by the ensemble pipeline.
// No cart, no ordering — just browse the ranked dishes.
import { useState, useEffect } from "react";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import { restaurants } from "../services/api";

const CUISINE_EMOJI = {
  south_indian: "🥘", north_indian: "🍛", biryani: "🍚",
  street_food:  "🌮", gujarati:    "🫓",  maharashtrian: "🥙",
  bengali:      "🐟", rajasthani:  "🫕",  dessert: "🍮",
  beverage:     "☕", staple:      "🍽",  goan: "🍤",
};
function emoji(c) { return CUISINE_EMOJI[c] || "🍽"; }

function DishRow({ dish, index }) {
  const n = dish.nutrition || {};
  return (
    <div style={{
      padding:      "16px 0",
      borderBottom: "1px solid var(--border)",
      display:      "flex",
      gap:          "12px",
      alignItems:   "flex-start",
      animation:    `fadeUp 0.25s ease ${index * 0.03}s both`,
    }}>
      {/* Emoji thumbnail */}
      <div style={{
        width: "52px", height: "52px", borderRadius: "var(--radius)",
        background: "var(--surface-2)", display: "flex",
        alignItems: "center", justifyContent: "center",
        fontSize: "22px", flexShrink: 0,
      }}>
        {emoji(dish.cuisine_type)}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Name + badges */}
        <div style={{ fontSize: "14px", fontWeight: 600, textTransform: "capitalize", marginBottom: "4px" }}>
          {dish.dish_name?.replace(/_/g, " ")}
        </div>
        <div style={{ display: "flex", gap: "5px", flexWrap: "wrap", marginBottom: "4px" }}>
          {dish.is_veg && (
            <span className="badge badge-green" style={{ fontSize: "9px" }}>veg</span>
          )}
          {dish.health_compliant
            ? <span className="badge badge-green" style={{ fontSize: "9px" }}>✓ healthy</span>
            : <span className="badge badge-yellow" style={{ fontSize: "9px" }}>⚠ moderate</span>
          }
        </div>

        {/* Nutrition */}
        <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
          {n.calories  && `${Math.round(n.calories)} kcal`}
          {n.protein_g && ` · ${Math.round(n.protein_g)}g protein`}
          {n.gi != null && (
            <span style={{
              color: n.gi > 70 ? "var(--red)" : n.gi > 55 ? "var(--yellow)" : "var(--green)",
            }}>
              {` · GI ${Math.round(n.gi)}`}
            </span>
          )}
        </div>

        {/* Health reasons */}
        {dish.health_reasons?.map((r, i) => (
          <div key={i} style={{ fontSize: "11px", color: "var(--yellow)", marginTop: "3px" }}>
            ⚠ {r}
          </div>
        ))}
      </div>

      {/* Price */}
      {dish.price && (
        <div style={{ fontSize: "15px", fontWeight: 700, flexShrink: 0, paddingTop: "2px" }}>
          ₹{Math.round(dish.price)}
        </div>
      )}
    </div>
  );
}

export default function RestaurantDetail() {
  const { restaurantId } = useParams();
  const { state }        = useLocation();
  const navigate         = useNavigate();

  const navRestaurant = state?.restaurant || null;

  const [menuData, setMenuData] = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await restaurants.getMenu(restaurantId);
        if (!cancelled) setMenuData(data);
      } catch (e) {
        if (!cancelled) setError(e.message || "Could not load menu");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [restaurantId]);

  const restaurant = menuData?.restaurant || navRestaurant;
  const menu       = menuData?.menu || [];

  if (loading) {
    return (
      <div className="page" style={{ padding: "56px 24px" }}>
        <button
          onClick={() => navigate(-1)}
          style={{ marginBottom: "20px", fontSize: "14px", color: "var(--text-secondary)" }}
        >
          ← Back
        </button>
        {navRestaurant && (
          <div style={{ fontSize: "24px", fontWeight: 800, marginBottom: "20px" }}>
            {navRestaurant.name}
          </div>
        )}
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="card" style={{ height: "80px", marginBottom: "12px", animation: "pulse 1.5s ease infinite" }} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="page" style={{ padding: "56px 24px", textAlign: "center" }}>
        <div style={{ fontSize: "40px", marginBottom: "16px" }}>😕</div>
        <div style={{ fontSize: "16px", fontWeight: 500, marginBottom: "8px" }}>Couldn't load menu</div>
        <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "24px" }}>{error}</div>
        <button onClick={() => navigate(-1)} style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
          ← Go back
        </button>
      </div>
    );
  }

  return (
    <div className="page" style={{ paddingBottom: "var(--nav-height)" }}>
      {/* Header */}
      <div style={{ padding: "56px 24px 16px" }}>
        <button
          onClick={() => navigate(-1)}
          style={{ marginBottom: "16px", fontSize: "14px", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "6px" }}
        >
          ← Back
        </button>

        {restaurant && (
          <>
            <div style={{ fontSize: "26px", fontWeight: 800, letterSpacing: "-0.02em", marginBottom: "6px" }}>
              {restaurant.name}
            </div>
            <div style={{ fontSize: "13px", color: "var(--text-secondary)", display: "flex", gap: "12px", flexWrap: "wrap" }}>
              {restaurant.area              && <span>📍 {restaurant.area}</span>}
              {restaurant.rating            && <span>★ {restaurant.rating}</span>}
              {restaurant.avg_cost_for_two  && <span>₹{restaurant.avg_cost_for_two} for two</span>}
              {restaurant.delivery_time_min && <span>🕐 {restaurant.delivery_time_min} min</span>}
            </div>
          </>
        )}
      </div>

      {/* Menu label */}
      <div style={{ padding: "0 24px 4px" }}>
        <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>
          {menu.length} items · ranked for you
        </div>
      </div>

      {/* Menu */}
      <div style={{ padding: "0 24px" }}>
        {menu.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px 0", color: "var(--text-secondary)" }}>
            <div style={{ fontSize: "40px", marginBottom: "16px" }}>🍽</div>
            <div>No menu items available right now</div>
          </div>
        ) : (
          menu.map((dish, i) => (
            <DishRow key={dish.dish_name} dish={dish} index={i} />
          ))
        )}
      </div>
    </div>
  );
}