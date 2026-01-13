import { useState } from "react";

import { confirmPasswordReset, requestPasswordReset } from "../api/client";
import Footer from "../components/Footer";

export default function ResetPassword() {
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRequest = async () => {
    setError(null);
    setMessage(null);
    if (!email) {
      setError("Email is required.");
      return;
    }
    try {
      const response = await requestPasswordReset(email);
      setMessage(response.message);
      setResetToken(response.reset_token || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to request reset token");
    }
  };

  const handleConfirm = async () => {
    setError(null);
    setMessage(null);
    if (!token || !newPassword) {
      setError("Reset token and new password are required.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    try {
      const response = await confirmPasswordReset(token, newPassword);
      setMessage(response.message);
      setToken("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reset password");
    }
  };

  return (
    <div className="app-shell">
      <div className="content auth-content">
        <div className="card" style={{ maxWidth: 520, margin: "0 auto" }}>
          <div className="brand">
            <h1>Kyronix Core</h1>
            <span>Reset your access</span>
          </div>

          <div className="grid" style={{ marginTop: 20 }}>
            <div>
              <label>
                Email
                <input
                  className="input"
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>
              <button className="button secondary" onClick={handleRequest} style={{ marginTop: 10 }}>
                Send reset token
              </button>
            </div>

            {resetToken && (
              <div className="card" style={{ padding: 16, background: "rgba(255, 255, 255, 0.7)" }}>
                <strong>Reset token (development):</strong>
                <div style={{ wordBreak: "break-all", marginTop: 6 }}>{resetToken}</div>
              </div>
            )}

            <div>
              <label>
                Reset token
                <input
                  className="input"
                  placeholder="Paste reset token"
                  value={token}
                  onChange={(event) => setToken(event.target.value)}
                />
              </label>
              <label>
                New password
                <input
                  className="input"
                  type="password"
                  placeholder="New password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                />
              </label>
              <label>
                Confirm new password
                <input
                  className="input"
                  type="password"
                  placeholder="Confirm new password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                />
              </label>
              <button className="button" onClick={handleConfirm}>
                Update password
              </button>
            </div>

            {message && <div style={{ color: "#0b1f2a" }}>{message}</div>}
            {error && <div style={{ color: "#b42318" }}>{error}</div>}
            <a href="/login" className="button secondary" style={{ justifySelf: "start" }}>
              Back to sign in
            </a>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
