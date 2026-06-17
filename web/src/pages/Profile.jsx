// NARA — Profile Page
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { user, auth } from "../services/api";

function Row({ label, value, onEdit }) {
  return (
    <div
      style={{
        display:        "flex",
        justifyContent: "space-between",
        alignItems:     "center",
        padding:        "14px 0",
        borderBottom:   "1px solid var(--border)",
      }}
    >
      <span style={{ fontSize: "14px", color: "var(--text-secondary)" }}>{label}</span>
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <span style={{ fontSize: "14px", fontWeight: 500 }}>{value || "—"}</span>
        {onEdit && (
          <button onClick={onEdit} style={{ color: "var(--blue)", fontSize: "13px" }}>Edit</button>
        )}
      </div>
    </div>
  );
}

export default function Profile() {
  const navigate  = useNavigate();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  const email = localStorage.getItem("nara_email") || "";

  useEffect(() => {
    user.getHealthProfile()
      .then(setProfile)
      .catch(() => setProfile(null))
      .finally(() => setLoading(false));
  }, []);

  async function handleLogout() {
    try { await auth.logout(); } catch {}
    localStorage.removeItem("nara_token");
    localStorage.removeItem("nara_user_id");
    localStorage.removeItem("nara_email");
    navigate("/login");
  }

  const conditions    = profile?.declared_conditions || [];
  const restrictions  = profile?.dietary_restrictions || [];
  const bmi = profile?.weight_kg && profile?.height_cm
    ? (profile.weight_kg / Math.pow(profile.height_cm / 100, 2)).toFixed(1)
    : null;

  return (
    <div className="page">
      <div style={{ padding: "56px 24px 0" }}>
        {/* Avatar */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginBottom: "36px" }}>
          <div
            style={{
              width:         "80px",
              height:        "80px",
              borderRadius:  "50%",
              background:    "var(--surface)",
              border:        "1px solid var(--border)",
              display:       "flex",
              alignItems:    "center",
              justifyContent:"center",
              fontSize:      "36px",
              marginBottom:  "12px",
            }}
          >
            👤
          </div>
          <div style={{ fontSize: "18px", fontWeight: 700 }}>{email || "User"}</div>
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
            Free tier
          </div>
        </div>

        {/* Health profile */}
        {!loading && (
          <>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: "4px" }}>
              Health Profile
            </div>
            <div className="card" style={{ marginBottom: "20px" }}>
              <Row label="Age"           value={profile?.age} />
              <Row label="Gender"        value={profile?.gender} />
              <Row label="Weight"        value={profile?.weight_kg ? `${profile.weight_kg} kg` : null} />
              <Row label="Height"        value={profile?.height_cm ? `${profile.height_cm} cm` : null} />
              <Row label="BMI"           value={bmi} />
              <Row label="Activity"      value={profile?.activity_level?.replace(/_/g, " ")} />
              <Row label="Fitness Goal"  value={profile?.nutritional_goals?.fitness_goal?.replace(/_/g, " ")} />
            </div>

            {conditions.length > 0 && (
              <>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: "8px" }}>
                  Conditions
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "20px" }}>
                  {conditions.map(c => (
                    <span key={c} className="badge badge-blue" style={{ fontSize: "11px" }}>
                      {c.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              </>
            )}

            {restrictions.length > 0 && (
              <>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: "8px" }}>
                  Dietary Restrictions
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "20px" }}>
                  {restrictions.map(r => (
                    <span key={r} className="badge badge-green" style={{ fontSize: "11px" }}>
                      {r.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              </>
            )}

            <button
              onClick={() => navigate("/onboarding")}
              className="btn-secondary"
              style={{ marginBottom: "12px" }}
            >
              Update Health Profile
            </button>
          </>
        )}

        {loading && (
          <div style={{ display: "flex", justifyContent: "center", padding: "40px 0" }}>
            <span className="spinner" />
          </div>
        )}

        {/* Settings */}
        <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: "4px", marginTop: "8px" }}>
          Account
        </div>
        <div className="card" style={{ marginBottom: "20px" }}>
          <Row label="Email" value={email} />
          <Row label="Version" value="0.1.0 · Sprint 6" />
        </div>

        <button
          onClick={handleLogout}
          style={{
            width:        "100%",
            padding:      "14px",
            borderRadius: "100px",
            background:   "rgba(255,59,48,0.1)",
            color:        "var(--red)",
            border:       "1px solid rgba(255,59,48,0.2)",
            fontSize:     "15px",
            fontWeight:   600,
            marginBottom: "40px",
          }}
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}