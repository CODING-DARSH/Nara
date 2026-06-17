// NARA — Onboarding Page
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { user } from "../services/api";

const STEPS = [
  {
    id: "basics",
    title: "Let's get\nto know you",
    subtitle: "This helps us personalise your experience",
  },
  {
    id: "diet",
    title: "Your\ndiet",
    subtitle: "We'll filter recommendations accordingly",
  },
  {
    id: "health",
    title: "Any health\nconditions?",
    subtitle: "Completely optional — helps us be more accurate",
  },
  {
    id: "goals",
    title: "What's your\ngoal?",
    subtitle: "We'll optimise your recommendations",
  },
];

const CONDITIONS = [
  { id: "type2_diabetes", label: "Diabetes" },
  { id: "prediabetes",    label: "Pre-diabetes" },
  { id: "hypertension",   label: "Hypertension" },
  { id: "pcos",           label: "PCOS" },
  { id: "high_cholesterol", label: "High Cholesterol" },
  { id: "obesity",        label: "Obesity" },
  { id: "thyroid",        label: "Thyroid" },
  { id: "ibs",            label: "IBS" },
];

const GOALS = [
  { id: "lose_weight",     label: "Lose Weight",    emoji: "⚖️" },
  { id: "maintain",        label: "Maintain",        emoji: "✨" },
  { id: "gain_muscle",     label: "Gain Muscle",     emoji: "💪" },
  { id: "manage_condition",label: "Manage Condition",emoji: "🩺" },
  { id: "general_health",  label: "General Health",  emoji: "🌿" },
];

export default function Onboarding() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    age:                  "",
    gender:               "",
    weight_kg:            "",
    height_cm:            "",
    is_vegetarian:        false,
    dietary_restrictions: [],
    conditions:           [],
    fitness_goal:         "",
    activity_level:       "moderately_active",
  });

  function toggleCondition(id) {
    setForm((f) => ({
      ...f,
      conditions: f.conditions.includes(id)
        ? f.conditions.filter((c) => c !== id)
        : [...f.conditions, id],
    }));
  }

  function toggleRestriction(id) {
    setForm((f) => ({
      ...f,
      dietary_restrictions: f.dietary_restrictions.includes(id)
        ? f.dietary_restrictions.filter((r) => r !== id)
        : [...f.dietary_restrictions, id],
    }));
  }

  async function finish() {
    setLoading(true);
    setError("");
    try {
      await user.saveHealthProfile({
        declared_conditions:  form.conditions,
        dietary_restrictions: [
          ...(form.is_vegetarian ? ["vegetarian"] : []),
          ...form.dietary_restrictions,
        ],
        nutritional_goals:    { fitness_goal: form.fitness_goal },
        age:                  parseInt(form.age) || null,
        weight_kg:            parseFloat(form.weight_kg) || null,
        height_cm:            parseFloat(form.height_cm) || null,
        gender:               form.gender,
        activity_level:       form.activity_level,
      });
      navigate("/");
    } catch (err) {
      setError(err.message || "Couldn't save your profile. You can try again, or skip for now.");
    } finally {
      setLoading(false);
    }
  }

  const current = STEPS[step];

  return (
    <div
      style={{
        minHeight:     "100dvh",
        display:       "flex",
        flexDirection: "column",
        padding:       "60px 24px 40px",
        position:      "relative",
      }}
    >
      {/* Progress dots + back button */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "40px" }}>
        {step > 0 && (
          <button
            onClick={() => { setError(""); setStep(step - 1); }}
            style={{
              display:        "flex",
              alignItems:     "center",
              justifyContent: "center",
              width:          "28px",
              height:         "28px",
              flexShrink:     0,
              color:          "var(--text-secondary)",
            }}
            aria-label="Back"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M15 18L9 12L15 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        )}
        <div style={{ display: "flex", gap: "6px", flex: 1 }}>
          {STEPS.map((_, i) => (
            <div
              key={i}
              style={{
                height:       "3px",
                flex:         1,
                borderRadius: "100px",
                background:   i <= step ? "var(--text-primary)" : "var(--border)",
                transition:   "background 0.3s",
              }}
            />
          ))}
        </div>
      </div>

      {/* Title */}
      <div style={{ marginBottom: "40px" }}>
        <h1
          style={{
            fontSize:      "36px",
            fontWeight:    "800",
            letterSpacing: "-0.04em",
            lineHeight:    1.15,
            whiteSpace:    "pre-line",
          }}
        >
          {current.title}
        </h1>
        <p style={{ fontSize: "15px", color: "var(--text-secondary)", marginTop: "10px" }}>
          {current.subtitle}
        </p>
      </div>

      {/* Step content */}
      <div style={{ flex: 1 }}>
        {step === 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <input
              className="input-field"
              placeholder="Age"
              type="number"
              value={form.age}
              onChange={(e) => setForm({ ...form, age: e.target.value })}
            />
            <div style={{ display: "flex", gap: "10px" }}>
              {["male", "female", "other"].map((g) => (
                <button
                  key={g}
                  onClick={() => setForm({ ...form, gender: g })}
                  style={{
                    flex:         1,
                    padding:      "14px",
                    borderRadius: "var(--radius)",
                    background:   form.gender === g ? "var(--text-primary)" : "var(--surface)",
                    color:        form.gender === g ? "var(--bg)" : "var(--text-secondary)",
                    border:       `1px solid ${form.gender === g ? "var(--text-primary)" : "var(--border)"}`,
                    fontWeight:   500,
                    fontSize:     "14px",
                    textTransform:"capitalize",
                    transition:   "all 0.2s",
                  }}
                >
                  {g}
                </button>
              ))}
            </div>
            <div style={{ display: "flex", gap: "10px" }}>
              <input
                className="input-field"
                placeholder="Weight (kg)"
                type="number"
                value={form.weight_kg}
                onChange={(e) => setForm({ ...form, weight_kg: e.target.value })}
              />
              <input
                className="input-field"
                placeholder="Height (cm)"
                type="number"
                value={form.height_cm}
                onChange={(e) => setForm({ ...form, height_cm: e.target.value })}
              />
            </div>
          </div>
        )}

        {step === 1 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {[
              { id: "vegetarian", label: "Vegetarian", desc: "No meat or fish" },
              { id: "vegan",      label: "Vegan",      desc: "No animal products" },
              { id: "jain",       label: "Jain",       desc: "No root vegetables, onion, garlic" },
              { id: "halal",      label: "Halal",      desc: "Halal only" },
              { id: "no_gluten",  label: "Gluten-free",desc: "No wheat, barley, rye" },
              { id: "no_dairy",   label: "Dairy-free", desc: "Lactose intolerant" },
            ].map((opt) => {
              const active = opt.id === "vegetarian"
                ? form.is_vegetarian
                : form.dietary_restrictions.includes(opt.id);
              return (
                <button
                  key={opt.id}
                  onClick={() => {
                    if (opt.id === "vegetarian") {
                      setForm({ ...form, is_vegetarian: !form.is_vegetarian });
                    } else {
                      toggleRestriction(opt.id);
                    }
                  }}
                  style={{
                    display:       "flex",
                    alignItems:    "center",
                    justifyContent:"space-between",
                    padding:       "16px",
                    borderRadius:  "var(--radius)",
                    background:    active ? "var(--surface-2)" : "var(--surface)",
                    border:        `1px solid ${active ? "var(--border-light)" : "var(--border)"}`,
                    textAlign:     "left",
                    transition:    "all 0.2s",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 500, fontSize: "15px" }}>{opt.label}</div>
                    <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "2px" }}>{opt.desc}</div>
                  </div>
                  <div
                    style={{
                      width:        "22px",
                      height:       "22px",
                      borderRadius: "50%",
                      background:   active ? "var(--green)" : "var(--border)",
                      display:      "flex",
                      alignItems:   "center",
                      justifyContent:"center",
                      flexShrink:   0,
                      transition:   "background 0.2s",
                    }}
                  >
                    {active && (
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                        <path d="M2 6L5 9L10 3" stroke="#000" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {step === 2 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
            {CONDITIONS.map((c) => {
              const active = form.conditions.includes(c.id);
              return (
                <button
                  key={c.id}
                  onClick={() => toggleCondition(c.id)}
                  style={{
                    padding:      "10px 18px",
                    borderRadius: "100px",
                    background:   active ? "var(--text-primary)" : "var(--surface)",
                    color:        active ? "var(--bg)" : "var(--text-secondary)",
                    border:       `1px solid ${active ? "var(--text-primary)" : "var(--border)"}`,
                    fontSize:     "14px",
                    fontWeight:   active ? 600 : 400,
                    transition:   "all 0.2s",
                  }}
                >
                  {c.label}
                </button>
              );
            })}
            <button
              onClick={() => setStep(step + 1)}
              style={{
                width:        "100%",
                marginTop:    "8px",
                padding:      "14px",
                borderRadius: "100px",
                background:   "transparent",
                color:        "var(--text-secondary)",
                border:       "none",
                fontSize:     "15px",
              }}
            >
              Skip — none apply
            </button>
          </div>
        )}

        {step === 3 && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {GOALS.map((g) => {
              const active = form.fitness_goal === g.id;
              return (
                <button
                  key={g.id}
                  onClick={() => setForm({ ...form, fitness_goal: g.id })}
                  style={{
                    display:       "flex",
                    alignItems:    "center",
                    gap:           "16px",
                    padding:       "18px",
                    borderRadius:  "var(--radius-lg)",
                    background:    active ? "var(--surface-2)" : "var(--surface)",
                    border:        `1px solid ${active ? "var(--text-primary)" : "var(--border)"}`,
                    textAlign:     "left",
                    transition:    "all 0.2s",
                  }}
                >
                  <span style={{ fontSize: "24px" }}>{g.emoji}</span>
                  <span style={{ fontSize: "16px", fontWeight: active ? 600 : 400 }}>
                    {g.label}
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Next / Finish button */}
      <div style={{ marginTop: "32px" }}>
        {error && (
          <div
            style={{
              fontSize:     "13px",
              color:        "var(--red)",
              padding:      "10px 14px",
              background:   "rgba(255,59,48,0.08)",
              borderRadius: "var(--radius-sm)",
              marginBottom: "12px",
            }}
          >
            {error}
          </div>
        )}

        {step < STEPS.length - 1 ? (
          <button
            className="btn-primary"
            onClick={() => setStep(step + 1)}
          >
            Continue
          </button>
        ) : (
          <>
            <button
              className="btn-primary"
              onClick={finish}
              disabled={loading}
            >
              {loading ? "Setting up..." : error ? "Try again" : "Start using NARA"}
            </button>
            {error && (
              <button
                onClick={() => navigate("/")}
                style={{
                  width:      "100%",
                  marginTop:  "12px",
                  padding:    "12px",
                  fontSize:   "14px",
                  color:      "var(--text-secondary)",
                  background: "transparent",
                }}
              >
                Skip for now
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}