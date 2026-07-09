// NARA — Log Meal Page (FIXED: uses notifyMealLogged, history refreshes via shared context version)
import { useState, useEffect } from "react";
import { meals } from "../services/api";
import { useAppContext, useFoodGraphVersion } from "../context/AppContext";

const OCCASIONS = ["breakfast", "lunch", "snack", "dinner", "late_night"];
const LOCATIONS = ["home", "office", "restaurant", "street_food", "cafe", "other"];

export default function LogMeal() {
  const { notifyMealLogged } = useAppContext();
  const graphVersion = useFoodGraphVersion();

  const [description, setDescription] = useState("");
  const [occasion,    setOccasion]    = useState("lunch");
  const [location,    setLocation]    = useState("home");
  const [loading,     setLoading]     = useState(false);
  const [success,     setSuccess]     = useState(false);
  const [error,       setError]       = useState("");
  const [history,     setHistory]     = useState([]);
  const [histLoading, setHistLoading] = useState(true);

  // FIX 4: refetch history whenever graphVersion bumps — covers both this
  // page's own logs AND meals logged from Home's quick-log chips, without
  // a full reload.
  useEffect(() => {
    let cancelled = false;
    async function loadHistory() {
      try {
        const data = await meals.getHistory(1, 10);
        if (!cancelled) setHistory(data.events || []);
      } catch {
        if (!cancelled) setHistory([]);
      } finally {
        if (!cancelled) setHistLoading(false);
      }
    }
    loadHistory();
    return () => { cancelled = true; };
  }, [graphVersion]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!description.trim()) return;
    setLoading(true);
    setError("");
    try {
      await meals.logText(description, { occasion, location_type: location });
      setSuccess(true);
      setDescription("");
      setTimeout(() => setSuccess(false), 3000);
      // FIX 3: forces a synchronous food-graph recompute + bumps shared
      // version, so this page's history AND Home/FoodGraph/Recommendations
      // all refresh consistently — no manual refetch wiring per page.
      await notifyMealLogged();
    } catch (err) {
      setError(err.message || "Failed to log meal");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <div style={{ padding: "56px 24px 0" }}>
        <h1 style={{ fontSize: "28px", fontWeight: "800", letterSpacing: "-0.03em", marginBottom: "24px" }}>
          Log a meal
        </h1>

        <form onSubmit={handleSubmit}>
          <div
            style={{
              background:   "var(--surface)",
              border:       `1px solid ${success ? "var(--green)" : error ? "var(--red)" : "var(--border)"}`,
              borderRadius: "var(--radius-lg)",
              padding:      "16px",
              marginBottom: "16px",
              transition:   "border-color 0.3s",
            }}
          >
            <textarea
              style={{ width: "100%", minHeight: "80px", fontSize: "15px", lineHeight: 1.5, resize: "none" }}
              placeholder="What did you eat? e.g. Had chicken biryani with raita for lunch"
              value={description}
              onChange={e => setDescription(e.target.value)}
              disabled={loading}
            />
          </div>

          <div style={{ marginBottom: "12px" }}>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: "8px" }}>
              Occasion
            </div>
            <div style={{ display: "flex", gap: "8px", overflowX: "auto", paddingBottom: "4px" }}>
              {OCCASIONS.map(o => (
                <button
                  key={o}
                  type="button"
                  onClick={() => setOccasion(o)}
                  style={{
                    padding: "7px 14px", borderRadius: "100px",
                    background: occasion === o ? "var(--text-primary)" : "var(--surface)",
                    color: occasion === o ? "var(--bg)" : "var(--text-secondary)",
                    border: `1px solid ${occasion === o ? "var(--text-primary)" : "var(--border)"}`,
                    fontSize: "12px", fontWeight: occasion === o ? 600 : 400,
                    whiteSpace: "nowrap", transition: "all 0.2s",
                  }}
                >
                  {o.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: "20px" }}>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: "8px" }}>
              Where
            </div>
            <div style={{ display: "flex", gap: "8px", overflowX: "auto", paddingBottom: "4px" }}>
              {LOCATIONS.map(l => (
                <button
                  key={l}
                  type="button"
                  onClick={() => setLocation(l)}
                  style={{
                    padding: "7px 14px", borderRadius: "100px",
                    background: location === l ? "var(--text-primary)" : "var(--surface)",
                    color: location === l ? "var(--bg)" : "var(--text-secondary)",
                    border: `1px solid ${location === l ? "var(--text-primary)" : "var(--border)"}`,
                    fontSize: "12px", fontWeight: location === l ? 600 : 400,
                    whiteSpace: "nowrap", transition: "all 0.2s",
                  }}
                >
                  {l.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div style={{ fontSize: "13px", color: "var(--red)", marginBottom: "12px" }}>{error}</div>
          )}

          <button type="submit" className="btn-primary" disabled={loading || !description.trim()}>
            {loading ? "Logging..." : success ? "✓ Logged!" : "Log Meal"}
          </button>
        </form>

        <div style={{ marginTop: "36px" }}>
          <div style={{ fontSize: "18px", fontWeight: 700, letterSpacing: "-0.02em", marginBottom: "16px" }}>
            Recent meals
          </div>

          {histLoading ? (
            <div style={{ display: "flex", justifyContent: "center", padding: "40px 0" }}>
              <span className="spinner" />
            </div>
          ) : history.length === 0 ? (
            <div style={{ textAlign: "center", color: "var(--text-secondary)", padding: "40px 0", fontSize: "14px" }}>
              No meals logged yet
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {history.map((event, i) => (
                <div key={i} style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius)", padding: "14px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontSize: "14px", fontWeight: 500, marginBottom: "3px" }}>
                      {event.raw_input?.description || "Meal logged"}
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                      {event.meal_context?.occasion || ""} · {formatTime(event.occurred_at)}
                    </div>
                  </div>
                  <StatusDot status={event.enrichment_status} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusDot({ status }) {
  const map = {
    pending:    { color: "var(--yellow)" },
    processing: { color: "var(--blue)" },
    done:       { color: "var(--green)" },
    failed:     { color: "var(--red)" },
  };
  const s = map[status] || map.pending;
  return (
    <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: s.color, flexShrink: 0, animation: status === "processing" ? "pulse 1s ease infinite" : "none" }} />
  );
}

function formatTime(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}