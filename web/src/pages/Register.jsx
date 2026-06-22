// NARA — Register Page
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { auth } from "../services/api";

export default function Register() {
  const navigate = useNavigate();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    // FIX: previously only checked length >= 8. Backend
    // (services/auth/app/schemas/auth.py RegisterRequest.password_strength)
    // also requires at least one uppercase letter and one digit — those
    // requirements existed all along but were never enforced here, so a
    // password like "testpass" passed this check and then got rejected
    // by the backend with a confusing 422 the user never saw coming.
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (!/[A-Z]/.test(password)) {
      setError("Password must contain at least one uppercase letter");
      return;
    }
    if (!/[0-9]/.test(password)) {
      setError("Password must contain at least one number");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await auth.register(email, password);
      const data = await auth.login(email, password);
      localStorage.setItem("nara_token", data.access_token);
      localStorage.setItem("nara_user_id", data.user_id);
      localStorage.setItem("nara_email", email);
      navigate("/onboarding");
    } catch (err) {
      setError(err.message || "Registration failed");
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
      }}
    >
      <div style={{ marginBottom: "48px" }}>
        <div style={{ fontSize: "42px", fontWeight: "800", letterSpacing: "-0.04em" }}>
          NARA
        </div>
        <div style={{ fontSize: "15px", color: "var(--text-secondary)", marginTop: "8px" }}>
          Create your account
        </div>
      </div>

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        <input
          className="input-field"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          className="input-field"
          type="password"
          placeholder="Password (8+ chars, 1 uppercase, 1 number)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        {error && (
          <div style={{ fontSize: "13px", color: "var(--red)", padding: "10px 14px", background: "rgba(255,59,48,0.08)", borderRadius: "var(--radius-sm)" }}>
            {error}
          </div>
        )}

        <button type="submit" className="btn-primary" disabled={loading} style={{ marginTop: "8px" }}>
          {loading ? "Creating account..." : "Create Account"}
        </button>
      </form>

      <div style={{ marginTop: "24px", textAlign: "center", fontSize: "14px", color: "var(--text-secondary)" }}>
        Already have an account?{" "}
        <Link to="/login" style={{ color: "var(--text-primary)", fontWeight: 500 }}>
          Sign in
        </Link>
      </div>
    </div>
  );
}