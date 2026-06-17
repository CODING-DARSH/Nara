// NARA — Home Page
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { user, meals, recommendations } from "../services/api";

function MacroRing({ value, max, color, label, unit }) {
  const pct = Math.min(100, (value / max) * 100);
  const r   = 28;
  const circ= 2 * Math.PI * r;
  const dash= (pct / 100) * circ;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px" }}>
      <svg width="72" height="72" viewBox="0 0 72 72">
        <circle cx="36" cy="36" r={r} fill="none" stroke="var(--border)" strokeWidth="4" />
        <circle
          cx="36" cy="36" r={r} fill="none"
          stroke={color} strokeWidth="4"
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
          transform="rotate(-90 36 36)"
          style={{ transition: "stroke-dasharray 0.6s cubic-bezier(0.4,0,0.2,1)" }}
        />
        <text x="36" y="40" textAnchor="middle" fill="white" fontSize="13" fontWeight="600" fontFamily="Inter">
          {Math.round(value)}
        </text>
      </svg>
      <span style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 500 }}>{label}</span>
    </div>
  );
}

function QuickLogChip({ label, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding:      "8px 16px",
        borderRadius: "100px",
        background:   "var(--surface)",
        border:       "1px solid var(--border)",
        color:        "var(--text-secondary)",
        fontSize:     "13px",
        fontWeight:   500,
        whiteSpace:   "nowrap",
        transition:   "all 0.2s",
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = "var(--text-secondary)"}
      onMouseLeave={e => e.currentTarget.style.borderColor = "var(--border)"}
    >
      {label}
    </button>
  );
}

export default function Home() {
  const navigate = useNavigate();
  const [graph,   setGraph]   = useState(null);
  const [recs,    setRecs]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [logInput, setLogInput] = useState("");
  const [logging,  setLogging]  = useState(false);
  const [logSuccess, setLogSuccess] = useState(false);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  useEffect(() => {
    async function load() {
      try {
        const [g, r] = await Promise.allSettled([
          user.getFoodGraph(),
          recommendations.get(null, null, null, 5),
        ]);
        if (g.status === "fulfilled") setGraph(g.value);
        if (r.status === "fulfilled") setRecs(r.value?.recommendations || []);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function quickLog(text) {
    setLogging(true);
    try {
      await meals.logText(text);
      setLogSuccess(true);
      setTimeout(() => setLogSuccess(false), 2500);
      const g = await user.getFoodGraph();
      setGraph(g);
    } catch {}
    finally { setLogging(false); }
  }

  async function handleLogSubmit(e) {
    e.preventDefault();
    if (!logInput.trim()) return;
    await quickLog(logInput);
    setLogInput("");
  }

  const last24 = graph?.last_24h || {};
  const cal    = Math.round(last24.calories_kcal || 0);
  const prot   = Math.round(last24.protein_g || 0);
  const carbs  = Math.round(last24.carbs_g || 0);
  const fat    = Math.round(last24.fat_g || 0);
  const total  = graph?.total_meals_logged || 0;

  return (
    <div className="page" style={{ padding: "0 0 var(--nav-height)" }}>
      {/* Header */}
      <div style={{ padding: "56px 24px 24px" }}>
        <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginBottom: "4px" }}>
          {greeting}
        </div>
        <div style={{ fontSize: "28px", fontWeight: "800", letterSpacing: "-0.03em" }}>
          What are you eating today?
        </div>
      </div>

      {/* Quick log bar */}
      <div style={{ padding: "0 24px", marginBottom: "28px" }}>
        <form onSubmit={handleLogSubmit}>
          <div
            style={{
              display:       "flex",
              alignItems:    "center",
              gap:           "10px",
              background:    "var(--surface)",
              border:        `1px solid ${logSuccess ? "var(--green)" : "var(--border)"}`,
              borderRadius:  "var(--radius-xl)",
              padding:       "12px 16px",
              transition:    "border-color 0.3s",
            }}
          >
            <span style={{ fontSize: "18px" }}>🍽</span>
            <input
              style={{ flex: 1, fontSize: "15px", background: "none", border: "none", color: "var(--text-primary)" }}
              placeholder="Had idli and sambar..."
              value={logInput}
              onChange={e => setLogInput(e.target.value)}
            />
            {logging ? (
              <span className="spinner" />
            ) : logSuccess ? (
              <span style={{ color: "var(--green)", fontSize: "18px" }}>✓</span>
            ) : (
              <button
                type="submit"
                style={{
                  background: "var(--text-primary)", color: "var(--bg)",
                  borderRadius: "100px", padding: "6px 14px",
                  fontSize: "13px", fontWeight: 600,
                }}
              >
                Log
              </button>
            )}
          </div>
        </form>

        {/* Quick chips */}
        <div style={{ display: "flex", gap: "8px", marginTop: "12px", overflowX: "auto", paddingBottom: "4px" }}>
          {["Had chai ☕", "Ate biryani 🍛", "Had idli 🥘", "Ate salad 🥗", "Had roti sabzi 🫓"].map(chip => (
            <QuickLogChip key={chip} label={chip} onClick={() => quickLog(chip)} />
          ))}
        </div>
      </div>

      {/* Today's nutrition */}
      {!loading && (
        <div style={{ padding: "0 24px", marginBottom: "32px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <span className="section-title" style={{ fontSize: "18px" }}>Today's nutrition</span>
            <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
              {total} meals logged
            </span>
          </div>

          <div className="card" style={{ display: "flex", justifyContent: "space-around", padding: "24px 16px" }}>
            <MacroRing value={cal}  max={2000} color="var(--blue)"   label="Calories" unit="kcal" />
            <MacroRing value={prot} max={60}   color="var(--green)"  label="Protein"  unit="g" />
            <MacroRing value={carbs}max={250}  color="var(--yellow)" label="Carbs"    unit="g" />
            <MacroRing value={fat}  max={65}   color="var(--orange)" label="Fat"      unit="g" />
          </div>

          {cal === 0 && (
            <div style={{ textAlign: "center", color: "var(--text-secondary)", fontSize: "13px", marginTop: "12px" }}>
              Start logging meals to see your nutrition
            </div>
          )}
        </div>
      )}

      {/* Recommendations */}
      {recs.length > 0 && (
        <div style={{ marginBottom: "32px" }}>
          <div style={{ padding: "0 24px", display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <span className="section-title" style={{ fontSize: "18px" }}>For you right now</span>
            <button
              onClick={() => navigate("/recommendations")}
              style={{ fontSize: "13px", color: "var(--text-secondary)", fontWeight: 500 }}
            >
              See all
            </button>
          </div>

          <div style={{ display: "flex", gap: "12px", overflowX: "auto", padding: "0 24px", paddingBottom: "4px" }}>
            {recs.map((rec, i) => (
              <div
                key={i}
                className="card"
                style={{
                  minWidth:   "160px",
                  padding:    "16px",
                  cursor:     "pointer",
                  flexShrink: 0,
                  animation:  `fadeUp 0.3s ease ${i * 0.05}s both`,
                }}
              >
                <div
                  style={{
                    width:        "100%",
                    height:       "80px",
                    background:   "var(--surface-2)",
                    borderRadius: "var(--radius-sm)",
                    marginBottom: "12px",
                    display:      "flex",
                    alignItems:   "center",
                    justifyContent:"center",
                    fontSize:     "32px",
                  }}
                >
                  {getCuisineEmoji(rec.cuisine_type)}
                </div>
                <div style={{ fontSize: "13px", fontWeight: 600, marginBottom: "4px" }}>
                  {rec.dish_name?.replace(/_/g, " ")}
                </div>
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  {rec.health_compliant && (
                    <span className="badge badge-green" style={{ fontSize: "9px" }}>✓ healthy</span>
                  )}
                  {rec.nutrition?.calories && (
                    <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                      {Math.round(rec.nutrition.calories)} kcal
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top dishes */}
      {graph?.top_dishes?.length > 0 && (
        <div style={{ padding: "0 24px" }}>
          <div className="section-title" style={{ fontSize: "18px", marginBottom: "16px" }}>
            Your favourites
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {graph.top_dishes.slice(0, 5).map((d, i) => (
              <div
                key={i}
                style={{
                  display:       "flex",
                  alignItems:    "center",
                  justifyContent:"space-between",
                  padding:       "14px 16px",
                  background:    "var(--surface)",
                  borderRadius:  "var(--radius)",
                  border:        "1px solid var(--border)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <span style={{ fontSize: "20px", width: "28px" }}>
                    {getCuisineEmoji(d.cuisine_type || d.cuisine)}
                  </span>
                  <span style={{ fontSize: "14px", fontWeight: 500, textTransform: "capitalize" }}>
                    {d.dish?.replace(/_/g, " ")}
                  </span>
                </div>
                <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                  {d.count}×
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div style={{ display: "flex", justifyContent: "center", padding: "60px 0" }}>
          <span className="spinner" />
        </div>
      )}
    </div>
  );
}

function getCuisineEmoji(cuisine) {
  const map = {
    south_indian: "🥘", north_indian: "🍛", biryani: "🍚",
    street_food: "🌮", gujarati: "🫓", maharashtrian: "🥙",
    bengali: "🐟", rajasthani: "🫕", dessert: "🍮",
    beverage: "☕", staple: "🍽", goan: "🍤",
  };
  return map[cuisine] || "🍽";
}