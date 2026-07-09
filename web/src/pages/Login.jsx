// NARA — Login Page
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { auth } from "../services/api";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await auth.login(email, password);
      localStorage.setItem("nara_token", data.access_token);
      localStorage.setItem("nara_user_id", data.user_id);
      localStorage.setItem("nara_email", email);
      navigate("/");
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        minHeight:      "100dvh",
        display:        "flex",
        flexDirection:  "column",
        justifyContent: "center",
        padding:        "0 24px",
        background:     "var(--bg)",
      }}
    >
      {/* Logo */}
      <div style={{ marginBottom: "48px" }}>
        <div
          style={{
            fontSize:      "42px",
            fontWeight:    "800",
            letterSpacing: "-0.04em",
            color:         "var(--text-primary)",
            lineHeight:    1,
          }}
        >
          NARA
        </div>
        <div
          style={{
            fontSize:  "15px",
            color:     "var(--text-secondary)",
            marginTop: "8px",
          }}
        >
          Your personal food intelligence
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        <input
          className="input-field"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />
        <input
          className="input-field"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />

        {error && (
          <div
            style={{
              fontSize:  "13px",
              color:     "var(--red)",
              padding:   "10px 14px",
              background:"rgba(255,59,48,0.08)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          className="btn-primary"
          disabled={loading}
          style={{ marginTop: "8px" }}
        >
          {loading ? (
            <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
              <span className="spinner" style={{ borderTopColor: "#000" }} />
              Signing in...
            </span>
          ) : (
            "Sign In"
          )}
        </button>
      </form>

      {/* Register link */}
      <div
        style={{
          marginTop:  "24px",
          textAlign:  "center",
          fontSize:   "14px",
          color:      "var(--text-secondary)",
        }}
      >
        Don't have an account?{" "}
        <Link
          to="/register"
          style={{ color: "var(--text-primary)", fontWeight: 500 }}
        >
          Create one
        </Link>
      </div>
    </div>
  );
}