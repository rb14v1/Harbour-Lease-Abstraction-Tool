import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("pm@example.com");
  const [password, setPassword] = useState("Demo1234!");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/properties");
    } catch {
      setError("Login failed. Check your email and password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="centered-page">
      <form className="card login-card" onSubmit={handleSubmit}>
        <h1>Lease Abstraction Tool</h1>
        <p className="muted">Sign in to manage properties and leases.</p>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? "Signing in..." : "Sign in"}
        </button>
        <p className="muted small">
          Demo logins: pm@example.com / Demo1234! (property manager)
          <br />
          admin@example.com / Demo1234! (admin)
        </p>
      </form>
    </div>
  );
}
