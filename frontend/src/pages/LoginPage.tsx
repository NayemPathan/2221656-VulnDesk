import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { PasswordInput } from "../components/PasswordInput";
import { useAuth } from "../context/AuthContext";

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login({ email: email.trim(), password });
      navigate("/");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`HTTP ${err.status}: ${err.message}`);
      } else {
        setError("Failed to sign in.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const fillCredentials = (presetEmail: string, presetPass: string) => {
    setEmail(presetEmail);
    setPassword(presetPass);
    setError(null);
  };

  return (
    <div className="page-container auth-container">
      <div className="card form-card">
        <h1 className="page-title">Sign In to VulnDesk</h1>
        <p className="page-subtitle">
          Authenticate with your email and password to receive a 15-minute JWT
          and rotating session cookie.
        </p>

        {error && (
          <div className="alert alert-danger mt-3" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="vuln-form mt-3">
          <div className="form-group">
            <label htmlFor="login-email">Email Address</label>
            <input
              id="login-email"
              type="email"
              className="form-input"
              required
              placeholder="role@vulndesk.local"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label htmlFor="login-password">Password</label>
            <PasswordInput
              id="login-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting}
          >
            {submitting ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <div
          className="mt-3 field-hint"
          style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem" }}
        >
          <span>
            New Researcher? <Link to="/register">Create an account</Link>
          </span>
          <Link to="/forgot-password">Forgot password?</Link>
        </div>

        <div className="credentials-box mt-4">
          <h3 className="section-heading">Evaluator &amp; Demo Accounts</h3>
          <div className="cred-buttons">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() =>
                fillCredentials("tutor@vulndesk.local", "TutorPass123!")
              }
            >
              Tutor (Admin)
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() =>
                fillCredentials("charlie@vulndesk.local", "DemoPass123!")
              }
            >
              Charlie (Analyst)
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() =>
                fillCredentials("alice@vulndesk.local", "DemoPass123!")
              }
            >
              Alice (Researcher)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};