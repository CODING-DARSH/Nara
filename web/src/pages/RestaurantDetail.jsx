// NARA — Restaurant Detail
// Shows a restaurant's full menu ranked by the ensemble pipeline, plus a
// simple cart: add multiple dishes from THIS restaurant, checkout directly
// (no payment step — see services/recommendation/app/routers/orders.py).
import { useState, useEffect } from "react";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import { restaurants, orders } from "../services/api";

const CUISINE_EMOJI = {
  south_indian: "🥘", north_indian: "🍛", biryani: "🍚",
  street_food:  "🌮", gujarati:    "🫓",  maharashtrian: "🥙",
  bengali:      "🐟", rajasthani:  "🫕",  dessert: "🍮",
  beverage:     "☕", staple:      "🍽",  goan: "🍤",
};
function emoji(c) { return CUISINE_EMOJI[c] || "🍽"; }

function DishRow({ dish, index, cartQuantity, onAdd, adding }) {
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

      {/* Price + add-to-cart */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "8px", flexShrink: 0 }}>
        {dish.price && (
          <div style={{ fontSize: "15px", fontWeight: 700, paddingTop: "2px" }}>
            ₹{Math.round(dish.price)}
          </div>
        )}
        <button
          onClick={onAdd}
          disabled={adding}
          style={{
            fontSize:     "12px",
            fontWeight:   600,
            padding:      "6px 12px",
            borderRadius: "100px",
            border:       `1px solid ${cartQuantity ? "var(--green)" : "var(--border)"}`,
            background:   cartQuantity ? "var(--green)" : "var(--surface)",
            color:        cartQuantity ? "#000" : "var(--text-primary)",
            opacity:      adding ? 0.6 : 1,
          }}
        >
          {cartQuantity ? `Added ×${cartQuantity} · +1` : "Add"}
        </button>
      </div>
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

  // Cart state — items keyed by dish_name -> quantity, only ever for
  // THIS restaurant. If the user has an open cart for a different
  // restaurant, cartConflict holds that info instead (so we can prompt
  // them to clear it, per the "same restaurant only" rule enforced
  // server-side by orders.py).
  const [cartItems,     setCartItems]     = useState({});  // { dish_name: quantity }
  const [addingDish,    setAddingDish]    = useState(null);
  const [cartConflict,  setCartConflict]  = useState(null); // { message, existing_restaurant_id }
  const [checkingOut,   setCheckingOut]   = useState(false);
  const [checkoutError, setCheckoutError] = useState("");
  const [checkoutDone,  setCheckoutDone]  = useState(false);

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

  // Restore any existing open cart for THIS restaurant on load, so cart
  // state survives navigation/reload instead of only living in memory.
  useEffect(() => {
    let cancelled = false;
    async function loadCart() {
      try {
        const { cart, items } = await orders.getCart();
        if (cancelled) return;
        if (cart && cart.restaurant_id === restaurantId) {
          const map = {};
          items.forEach(i => { map[i.dish_name] = i.quantity; });
          setCartItems(map);
        } else if (cart) {
          setCartConflict({
            message: `You have an open cart from another restaurant.`,
            existing_restaurant_id: cart.restaurant_id,
          });
        }
      } catch {
        // Cart restore is best-effort — a failure here shouldn't block
        // browsing the menu.
      }
    }
    loadCart();
    return () => { cancelled = true; };
  }, [restaurantId]);

  async function handleAdd(dish) {
    setAddingDish(dish.dish_name);
    setCartConflict(null);
    try {
      const { items } = await orders.addCartItem(restaurantId, dish.dish_name, dish.cuisine_type);
      const map = {};
      items.forEach(i => { map[i.dish_name] = i.quantity; });
      setCartItems(map);
    } catch (e) {
      if (e.status === 409) {
        setCartConflict(e.body);
      }
      // Other errors: fail quietly on the button itself, menu stays usable.
    } finally {
      setAddingDish(null);
    }
  }

  async function handleClearOtherCart() {
    await orders.clearCart().catch(() => {});
    setCartConflict(null);
  }

  async function handleCheckout() {
    setCheckingOut(true);
    setCheckoutError("");
    try {
      await orders.checkout();
      setCheckoutDone(true);
      setCartItems({});
    } catch (e) {
      setCheckoutError(e.message || "Couldn't place order");
    } finally {
      setCheckingOut(false);
    }
  }

  const restaurant = menuData?.restaurant || navRestaurant;
  const menu       = menuData?.menu || [];

  const cartCount = Object.values(cartItems).reduce((a, b) => a + b, 0);
  const cartTotal = menu.reduce((sum, d) => {
    const qty = cartItems[d.dish_name] || 0;
    return sum + qty * (d.price || 0);
  }, 0);

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

      {/* Cart conflict banner */}
      {cartConflict && (
        <div style={{ margin: "0 24px 12px", padding: "12px 14px", borderRadius: "var(--radius)",
                       background: "rgba(255,204,0,0.08)", border: "1px solid var(--yellow)" }}>
          <div style={{ fontSize: "13px", marginBottom: "8px" }}>
            {cartConflict.message} Adding a dish here will require clearing it first.
          </div>
          <button
            onClick={handleClearOtherCart}
            style={{ fontSize: "12px", fontWeight: 600, color: "var(--yellow)" }}
          >
            Clear other cart
          </button>
        </div>
      )}

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
            <DishRow
              key={dish.dish_name}
              dish={dish}
              index={i}
              cartQuantity={cartItems[dish.dish_name] || 0}
              adding={addingDish === dish.dish_name}
              onAdd={() => handleAdd(dish)}
            />
          ))
        )}
      </div>

      {/* Sticky checkout bar */}
      {cartCount > 0 && !checkoutDone && (
        <div style={{
          position: "fixed", left: 0, right: 0, bottom: "var(--nav-height)",
          padding: "12px 24px", background: "var(--bg)", borderTop: "1px solid var(--border)",
          display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px",
        }}>
          <div>
            <div style={{ fontSize: "13px", fontWeight: 600 }}>{cartCount} item{cartCount > 1 ? "s" : ""}</div>
            {cartTotal > 0 && <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>₹{Math.round(cartTotal)}</div>}
          </div>
          <button
            className="btn-primary"
            onClick={handleCheckout}
            disabled={checkingOut}
            style={{ width: "auto", padding: "12px 28px" }}
          >
            {checkingOut ? "Placing order..." : "Checkout"}
          </button>
        </div>
      )}
      {checkoutError && (
        <div style={{ position: "fixed", left: 24, right: 24, bottom: "calc(var(--nav-height) + 70px)",
                       fontSize: "13px", color: "var(--red)", textAlign: "center" }}>
          {checkoutError}
        </div>
      )}

      {/* Post-checkout confirmation */}
      {checkoutDone && (
        <div style={{
          position: "fixed", left: 0, right: 0, bottom: "var(--nav-height)",
          padding: "16px 24px", background: "var(--green)", color: "#000",
          textAlign: "center", fontWeight: 600, fontSize: "14px",
        }}>
          ✓ Order placed
        </div>
      )}
    </div>
  );
}