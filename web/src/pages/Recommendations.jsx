// NARA — Recommendations Page
import { useState, useEffect } from "react";
import { recommendations } from "../services/api";

const OCCASIONS = [
  { id: null,        label: "For You" },
  { id: "breakfast", label: "Breakfast" },
  { id: "lunch",     label: "Lunch" },
  { id: "snack",     label: "Snack" },
  { id: "dinner",    label: "Dinner" },
];

function NutritionPill({ label, value, color }) {
  if (!value) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "2px" }}>
      <span style={{ fontSize: "13px", fontWeight: 600, color }}>{Math.round(value)}</span>
      <span style={{ fontSize: "10px", color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</span>
    </div>
  );
}

function RecCard({ rec, index }) {
  const [expanded, setExpanded] = useState(false);
  const n = rec.nutrition || {};

  return (
    <div
      onClick={() => setExpanded(!expanded)}
      style={{
        background:    "var(--surface)",
        border:        "1px solid var(--border)",
        borderRadius:  "var(--radius-lg)",
        padding:       "20px",
        cursor:        "pointer",
        transition:    "border-color 0.2s, transform 0.2s",
        animation:     `fadeUp 0.3s ease ${index * 0.04}s both`,
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
      {/* Top row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: "16px", fontWeight: 600, marginBottom: "4px", textTransform: "capitalize" }}>
            {rec.dish_name?.replace(/_/g, " ")}
          </div>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {rec.cuisine_type && (
              <span className="badge badge-purple" style={{ fontSize: "9px" }}>
                {rec.cuisine_type.replace(/_/g, " ")}
              </span>
            )}
            {rec.is_veg && (
              <span className="badge badge-green" style={{ fontSize: "9px" }}>veg</span>
            )}
            {rec.health_compliant ? (
              <span className="badge badge-green" style={{ fontSize: "9px" }}>✓ healthy</span>
            ) : (
              <span className="badge badge-yellow" style={{ fontSize: "9px" }}>⚠ moderate</span>
            )}
          </div>
        </div>

        {/* Score ring */}
        <div
          style={{
            width:         "44px",
            height:        "44px",
            borderRadius:  "50%",
            background:    `conic-gradient(var(--green) ${rec.score * 360}deg, var(--border) 0deg)`,
            display:       "flex",
            alignItems:    "center",
            justifyContent:"center",
            flexShrink:    0,
          }}
        >
          <div
            style={{
              width:         "34px",
              height:        "34px",
              borderRadius:  "50%",
              background:    "var(--surface)",
              display:       "flex",
              alignItems:    "center",
              justifyContent:"center",
              fontSize:      "11px",
              fontWeight:    700,
            }}
          >
            {Math.round(rec.score * 100)}
          </div>
        </div>
      </div>

      {/* Nutrition row */}
      <div
        style={{
          display:        "flex",
          justifyContent: "space-around",
          padding:        "12px 0",
          borderTop:      "1px solid var(--border)",
          borderBottom:   expanded ? "1px solid var(--border)" : "none",
          marginBottom:   expanded ? "12px" : 0,
        }}
      >
        <NutritionPill label="kcal"    value={n.calories}  color="var(--blue)" />
        <NutritionPill label="protein" value={n.protein_g} color="var(--green)" />
        <NutritionPill label="carbs"   value={n.carbs_g}   color="var(--yellow)" />
        <NutritionPill label="fat"     value={n.fat_g}     color="var(--orange)" />
        {n.gi && <NutritionPill label="GI" value={n.gi} color={n.gi > 70 ? "var(--red)" : n.gi > 55 ? "var(--yellow)" : "var(--green)"} />}
      </div>

      {/* Expanded health reasons */}
      {expanded && rec.health_reasons?.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {rec.health_reasons.map((r, i) => (
            <div key={i} style={{ fontSize: "12px", color: "var(--yellow)", display: "flex", gap: "6px", alignItems: "flex-start" }}>
              <span>⚠</span>
              <span>{r}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Recommendations() {
  const [occasion,  setOccasion]  = useState(null);
  const [recs,      setRecs]      = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [location,  setLocation]  = useState(null);
  const [locError,  setLocError]  = useState(false);

  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        pos => setLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        ()  => setLocError(true),
        { timeout: 5000 }
      );
    }
  }, []);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const data = await recommendations.get(
          location?.lat, location?.lng, occasion, 15
        );
        setRecs(data?.recommendations || []);
      } catch {
        setRecs([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [occasion, location]);

  return (
    <div className="page">
      {/* Header */}
      <div style={{ padding: "56px 24px 20px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: "800", letterSpacing: "-0.03em", marginBottom: "6px" }}>
          Discover
        </h1>
        {location ? (
          <div style={{ fontSize: "12px", color: "var(--green)", display: "flex", alignItems: "center", gap: "4px" }}>
            <span>📍</span> Location enabled — showing nearby options
          </div>
        ) : locError ? (
          <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
            Enable location for nearby recommendations
          </div>
        ) : null}
      </div>

      {/* Occasion filter */}
      <div style={{ display: "flex", gap: "8px", padding: "0 24px", overflowX: "auto", marginBottom: "24px", paddingBottom: "4px" }}>
        {OCCASIONS.map(o => (
          <button
            key={o.id}
            onClick={() => setOccasion(o.id)}
            style={{
              padding:      "8px 18px",
              borderRadius: "100px",
              background:   occasion === o.id ? "var(--text-primary)" : "var(--surface)",
              color:        occasion === o.id ? "var(--bg)" : "var(--text-secondary)",
              border:       `1px solid ${occasion === o.id ? "var(--text-primary)" : "var(--border)"}`,
              fontSize:     "13px",
              fontWeight:   occasion === o.id ? 600 : 400,
              whiteSpace:   "nowrap",
              transition:   "all 0.2s",
            }}
          >
            {o.label}
          </button>
        ))}
      </div>

      {/* Results */}
      <div style={{ padding: "0 24px", display: "flex", flexDirection: "column", gap: "12px" }}>
        {loading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="card" style={{ height: "120px", animation: "pulse 1.5s ease infinite" }} />
          ))
        ) : recs.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px 0", color: "var(--text-secondary)" }}>
            <div style={{ fontSize: "40px", marginBottom: "16px" }}>🍽</div>
            <div style={{ fontSize: "16px", fontWeight: 500 }}>No recommendations yet</div>
            <div style={{ fontSize: "13px", marginTop: "6px" }}>Log some meals first</div>
          </div>
        ) : (
          recs.map((rec, i) => <RecCard key={i} rec={rec} index={i} />)
        )}
      </div>
    </div>
  );
}