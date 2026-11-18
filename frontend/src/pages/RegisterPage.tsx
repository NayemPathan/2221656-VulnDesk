import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";


export const RegisterPage: React.FC = () => {
  const { register, login } = useAuth();
  const navigate = useNavigate();


  const [name, setName] = useState<string>("");
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await register({ name: name.trim(), email: email.trim(), password });
      await login({ email: email.trim(), password });
      navigate("/");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`HTTP ${err.status}: ${err.message}`);
      } else {
        setError("Failed to register account.");
      }
    } finally {
      setSubmitting(false);
    }
  };


  return (
    <div className="page-container auth-container">
      <div className="card form-card">
        <h1 className="page-title">Register Researcher Account</h1>
        <p className="page-subtitle">
          New registrations receive the <code>researcher</code> role.
        </p>


        {error && (
          <div className="alert alert-danger mt-3" role="alert">
            {error}
          </div>
        )}


        <form onSubmit={handleSubmit} className="vuln-form mt-3">
          <div className="form-group">
            <label htmlFor="reg-name">Full Name</label>
            <input
              id="reg-name"
              type="text"
              className="form-input"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>


          <div className="form-group">
            <label htmlFor="reg-email">Email Address</label>
            <input
              id="reg-email"
              type="email"
              className="form-input"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>


          <div className="form-group">
            <label htmlFor="reg-password">Password (min 8 characters)</label>
            <input
              id="reg-password"
              type="password"
              className="form-input"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>


          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting}
          >
            {submitting ? "Creating account..." : "Register & Sign In"}
          </button>
        </form>


        <p className="mt-3 field-hint">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
};
