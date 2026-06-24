// NARA — Food Graph Page (FIXED: subscribes to graphVersion, no manual reload needed)
import { useState, useEffect } from "react";
import { user } from "../services/api";
import { useFoodGraphVersion } from "../context/AppContext";

function CircleProgress({ value, max, color, size = 80, strokeWidth = 6, label, sublabel }) {
  const r    = (size - strokeWidth * 2) / 2;
  const circ = 2 * Math.PI * r;
  const pct  = Math.min(100, (value / max) * 100);
  const dash = (pct / 100) * circ;
  const cx   = size / 2;

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={cx} cy={cx} r={r} fill="none" stroke="var(--border)" strokeWidth={strokeWidth} />
        <circle
          cx={cx} cy={cx} r={r} fill="none"
          stroke={color} strokeWidth={strokeWidth}
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cx})`}
          style={{ transition: "stroke-dasharray 0.8s cubic-bezier(0.4,0,0.2,1)" }}
        />
        <text x={cx} y={cx - 4} textAnchor="middle" fill="white" fontSize="14" fontWeight="700" fontFamily="Inter">
          {Math.round(value)}
        </text>
        <text x={cx} y={cx + 12} textAnchor="middle" fill="#6b6b6b" fontSize="9" fontFamily="Inter">
          {sublabel}
        </text>
      </svg>
      <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: 500, textAlign: "center" }}>
        {label}
      </span>
    </div>
  );
}

function Bar({ label, value, max, color }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
        <span style={{ fontSize: "13px", color: "var(--text-secondary)", textTransform: "capitalize" }}>
          {label.replace(/_/g, " ")}
        </span>
        <span style={{ fontSize: "13px", fontWeight: 600 }}>{Math.round(value * 100)}%</span>
      </div>
      <div style={{ height: "4px", background: "var(--border)", borderRadius: "100px" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: "100px", transition: "width 0.8s cubic-bezier(0.4,0,0.2,1)" }} />
      </div>
    </div>
  );
}

function GapCard({ gap }) {
  const severityColor = { low: "var(--blue)", medium: "var(--yellow)", high: "var(--red)" }[gap.severity] || "var(--yellow)";
  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderLeft: `3px solid ${severityColor}`, borderRadius: "var(--radius)", padding: "14px 16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
        <span style={{ fontSize: "14px", fontWeight: 600, textTransform: "capitalize" }}>{gap.nutrient?.replace(/_/g, " ")}</span>
        <span className="badge" style={{ background: `${severityColor}18`, color: severityColor, fontSize: "9px" }}>{gap.severity}</span>
      </div>
      {gap.hint && <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>{gap.hint}</div>}
    </div>
  );
}

export default function FoodGraph() {
  const graphVersion = useFoodGraphVersion();
  const [graph,   setGraph]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [period,  setPeriod]  = useState("24h");

  // FIX 4: re-fetches whenever a meal is logged anywhere in the app
  // (Home quick-log, LogMeal page, even from Chat) — graphVersion bumps
  // once via notifyMealLogged(), every subscribed page updates quietly.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    user.getFoodGraph()
      .then(g => { if (!cancelled) setGraph(g); })
      .catch(() => { if (!cancelled) setGraph(null); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [graphVersion]);

  if (loading && !graph) {
    return (
      <div className="page" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span className="spinner" />
      </div>
    );
  }

  if (!graph || graph.total_meals_logged === 0) {
    return (
      <div className="page" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "24px" }}>
        <div style={{ fontSize: "56px", marginBottom: "20px" }}>📊</div>
        <div style={{ fontSize: "20px", fontWeight: 700, marginBottom: "8px" }}>No data yet</div>
        <div style={{ fontSize: "14px", color: "var(--text-secondary)", textAlign: "center" }}>
          Start logging meals to build your food graph
        </div>
      </div>
    );
  }

  const data = period === "24h" ? graph.last_24h : period === "7d" ? graph.last_7d : graph.last_30d;

  const cal   = data?.calories_kcal || 0;
  const prot  = data?.protein_g     || 0;
  const carbs = data?.carbs_g       || 0;
  const fat   = data?.fat_g         || 0;
  const gi    = data?.glycemic_index || 0;
  const gl    = data?.glycemic_load  || 0;

  const cuisineAffinity = graph.cuisine_affinity || {};
  const topCuisines     = Object.entries(cuisineAffinity).sort(([, a], [, b]) => b - a).slice(0, 5);
  const gaps = graph.nutritional_gaps || [];
  const CUISINE_COLORS = ["var(--blue)", "var(--green)", "var(--purple)", "var(--orange)", "var(--yellow)"];

  return (
    <div className="page">
      <div style={{ padding: "56px 24px 0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "24px" }}>
          <div>
            <h1 style={{ fontSize: "28px", fontWeight: "800", letterSpacing: "-0.03em" }}>Food Graph</h1>
            <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "4px" }}>
              {graph.total_meals_logged} meals logged
            </div>
          </div>
          {loading && <span className="spinner" style={{ width: "16px", height: "16px" }} />}
        </div>

        <div style={{ display: "flex", gap: "8px", marginBottom: "28px" }}>
          {["24h", "7d", "30d"].map(p => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              style={{
                padding: "7px 18px", borderRadius: "100px",
                background: period === p ? "var(--text-primary)" : "var(--surface)",
                color: period === p ? "var(--bg)" : "var(--text-secondary)",
                border: `1px solid ${period === p ? "var(--text-primary)" : "var(--border)"}`,
                fontSize: "13px", fontWeight: period === p ? 600 : 400, transition: "all 0.2s",
              }}
            >
              {p}
            </button>
          ))}
        </div>

        <div className="card" style={{ marginBottom: "20px" }}>
          <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)", letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: "20px" }}>
            Macronutrients
          </div>
          <div style={{ display: "flex", justifyContent: "space-around" }}>
            <CircleProgress value={cal}   max={2000} color="var(--blue)"   size={80} label="Calories" sublabel="kcal" />
            <CircleProgress value={prot}  max={60}   color="var(--green)"  size={80} label="Protein"  sublabel="g" />
            <CircleProgress value={carbs} max={250}  color="var(--yellow)" size={80} label="Carbs"    sublabel="g" />
            <CircleProgress value={fat}   max={65}   color="var(--orange)" size={80} label="Fat"      sublabel="g" />
          </div>
        </div>

        {(gi > 0 || gl > 0) && (
          <div className="card" style={{ marginBottom: "20px" }}>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)", letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: "16px" }}>
              Glycemic Profile
            </div>
            <div style={{ display: "flex", gap: "20px" }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                  <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>Glycemic Index</span>
                  <span style={{ fontSize: "14px", fontWeight: 700, color: gi > 70 ? "var(--red)" : gi > 55 ? "var(--yellow)" : "var(--green)" }}>{Math.round(gi)}</span>
                </div>
                <div style={{ height: "4px", background: "var(--border)", borderRadius: "100px" }}>
                  <div style={{ height: "100%", width: `${Math.min(100, gi)}%`, background: gi > 70 ? "var(--red)" : gi > 55 ? "var(--yellow)" : "var(--green)", borderRadius: "100px", transition: "width 0.8s" }} />
                </div>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                  <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>Glycemic Load</span>
                  <span style={{ fontSize: "14px", fontWeight: 700, color: gl > 20 ? "var(--red)" : gl > 11 ? "var(--yellow)" : "var(--green)" }}>{Math.round(gl)}</span>
                </div>
                <div style={{ height: "4px", background: "var(--border)", borderRadius: "100px" }}>
                  <div style={{ height: "100%", width: `${Math.min(100, gl * 3)}%`, background: gl > 20 ? "var(--red)" : gl > 11 ? "var(--yellow)" : "var(--green)", borderRadius: "100px", transition: "width 0.8s" }} />
                </div>
              </div>
            </div>
          </div>
        )}

        {topCuisines.length > 0 && (
          <div className="card" style={{ marginBottom: "20px" }}>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)", letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: "16px" }}>
              Cuisine Affinity
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {topCuisines.map(([cuisine, score], i) => (
                <Bar key={cuisine} label={cuisine} value={score} max={1} color={CUISINE_COLORS[i % CUISINE_COLORS.length]} />
              ))}
            </div>
          </div>
        )}

        {graph.top_dishes?.length > 0 && (
          <div className="card" style={{ marginBottom: "20px" }}>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)", letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: "16px" }}>
              Top Dishes
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {graph.top_dishes.slice(0, 6).map((d, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "var(--surface-2)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px" }}>🍽</div>
                    <span style={{ fontSize: "14px", textTransform: "capitalize" }}>{d.dish?.replace(/_/g, " ")}</span>
                  </div>
                  <span style={{ fontSize: "12px", color: "var(--text-secondary)", background: "var(--surface-2)", padding: "3px 10px", borderRadius: "100px" }}>{d.count}×</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {gaps.length > 0 && (
          <div style={{ marginBottom: "20px" }}>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)", letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: "12px" }}>
              Nutritional Gaps
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {gaps.map((gap, i) => <GapCard key={i} gap={gap} />)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}