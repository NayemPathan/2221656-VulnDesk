import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { PasswordInput } from "../components/PasswordInput";
import { useToast } from "../context/ToastContext";

export const ForgotPasswordPage: React.FC = () => {
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [step, setStep] = useState<"request" | "reset">("request");
  const [info, setInfo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleRequestToken = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.forgotPassword(email.trim());
      setInfo(res.detail);
      if (res.reset_token) {
        setToken(res.reset_token);
      }
      setStep("reset");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Request failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.resetPassword(token.trim(), newPassword);
      showToast("Password reset! Please sign in.", "success");
      navigate("/login");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reset failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-container auth-container">
      <div className="card form-card">
        <h1 className="page-title">Reset Password</h1>
        <p className="page-subtitle">
          {step === "request"
            ? "Enter your account email to generate a 15-minute single-use reset token."
            : "Enter your reset token and choose a new password."}
        </p>

        {info && <div className="alert alert-success mt-3">{info}</div>}
        {error && <div className="alert alert-danger mt-3">{error}</div>}

        {step === "request" ? (
          <form onSubmit={handleRequestToken} className="vuln-form mt-3">
            <div className="form-group">
              <label htmlFor="fp-email">Email Address</label>
              <input
                id="fp-email"
                type="email"
                className="form-input"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? "Generating..." : "Send Reset Token"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleResetPassword} className="vuln-form mt-3">
            <div className="form-group">
              <label htmlFor="fp-token">Reset Token</label>
              <input
                id="fp-token"
                type="text"
                className="form-input"
                required
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
              <span className="field-hint">
                In production this token is emailed; for academic demo it is pre-filled above.
              </span>
            </div>
            <div className="form-group">
              <label htmlFor="fp-new-pw">New Password (min 8 characters)</label>
              <PasswordInput
                id="fp-new-pw"
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? "Resetting..." : "Update Password"}
            </button>
          </form>
        )}

        <p className="mt-3 field-hint">
          Remembered it? <Link to="/login">Back to Sign In</Link>
        </p>
      </div>
    </div>
  );
};