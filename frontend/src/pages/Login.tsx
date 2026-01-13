import { FormEvent, useState } from "react";

import Footer from "../components/Footer";

type Props = {
  onLogin: (email: string, password: string) => Promise<void>;
};

export default function Login({ onLogin }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await onLogin(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <div className="content auth-content">
        <div className="card" style={{ maxWidth: 520, margin: "0 auto" }}>
          <div className="brand">
            <h1>Kyronix Core</h1>
            <span>Secure employee access to pay, documents, and records</span>
          </div>
          <p style={{ marginTop: 12 }}>
            Sign in to view and download your paystubs, employment documents, and verification letters.
          </p>
          <form className="grid" onSubmit={handleSubmit} style={{ marginTop: 12 }}>
            <input
              className="input"
              type="email"
              placeholder="Email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
            <input
              className="input"
              type="password"
              placeholder="Password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
            {error && <div style={{ color: "#b42318" }}>{error}</div>}
            <button className="button" type="submit" disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </button>
            <a href="/reset" className="button secondary" style={{ textAlign: "center" }}>
              Reset password
            </a>
          </form>
        </div>
      </div>
      <Footer />
    </div>
  );
}
