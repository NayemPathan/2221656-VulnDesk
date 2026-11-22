import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  api,
  ApiError,
  listMySessions,
  revokeMySession,
} from "../api/client";
import { RoleBadge } from "../components/Badges";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { SessionItem } from "../types";


export const ProfilePage: React.FC = () => {
  const { currentUser, refreshProfile, logout } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();


  const [name, setName] = useState<string>(currentUser?.name || "");
  const [currentPassword, setCurrentPassword] = useState<string>("");
  const [newPassword, setNewPassword] = useState<string>("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [revokingSessionId, setRevokingSessionId] = useState<number | null>(
    null
  );

  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    setSessionsError(null);
    try {
      setSessions(await listMySessions());
    } catch (err) {
      setSessionsError(
        err instanceof ApiError ? err.message : "Failed to load active sessions."
      );
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (currentUser) void loadSessions();
  }, [currentUser, loadSessions]);

  if (!currentUser) return null;


  const handleSaveName = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    setError(null);
    try {
      await api.updateMe(name.trim());
      await refreshProfile();
      setMessage("Profile name updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed.");
    }
  };


  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    setError(null);
    try {
      await api.changePassword(currentPassword, newPassword);
      await logout();
      navigate("/login");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Password change failed."
      );
    }
  };

  const handleRevokeSession = async (id: number) => {
    setRevokingSessionId(id);
    try {
      await revokeMySession(id);
      showToast("Session revoked", "success");
      await loadSessions();
    } catch (err) {
      showToast(
        err instanceof ApiError ? err.message : "Failed to revoke session.",
        "error"
      );
    } finally {
      setRevokingSessionId(null);
    }
  };


  return (
    <div className="page-container narrow-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Account Profile</h1>
          <p className="page-subtitle">
            Signed in as <code>{currentUser.name} - {currentUser.role}</code>
          </p>
        </div>
        <RoleBadge role={currentUser.role} isBanned={currentUser.is_banned} />
      </div>


      {message && <div className="alert alert-success">{message}</div>}
      {error && <div className="alert alert-danger">{error}</div>}


      <div className="card form-card">
        <h2 className="section-title">Display Name</h2>
        <form onSubmit={handleSaveName} className="vuln-form mt-2">
          <div className="form-group">
            <label htmlFor="profile-name">Full Name</label>
            <input
              id="profile-name"
              type="text"
              className="form-input"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <button type="submit" className="btn btn-primary btn-sm">
              Save Name
            </button>
          </div>
        </form>
      </div>


      <div className="card form-card mt-4">
        <h2 className="section-title">Change Password</h2>
        <p className="field-hint mb-3">
          Updating your password revokes all active refresh sessions.
        </p>
        <form onSubmit={handleChangePassword} className="vuln-form">
          <div className="form-group">
            <label htmlFor="cur-pw">Current Password</label>
            <input
              id="cur-pw"
              type="password"
              className="form-input"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label htmlFor="new-pw">New Password (min 8 characters)</label>
            <input
              id="new-pw"
              type="password"
              className="form-input"
              required
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </div>
          <div>
            <button type="submit" className="btn btn-danger btn-sm">
              Change Password &amp; Re-Login
            </button>
          </div>
        </form>
      </div>

      <section className="card" style={{ marginTop: "1.5rem" }}>
        <h3>Active Sessions ({sessions.length})</h3>
        {sessionsLoading ? (
          <p className="muted">Loading active sessions...</p>
        ) : sessionsError ? (
          <p className="alert alert-danger">{sessionsError}</p>
        ) : sessions.length === 0 ? (
          <p className="muted">No active refresh sessions.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>IP Address</th>
                <th>Browser / Device</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr key={session.id}>
                  <td>#{session.id}</td>
                  <td>{session.ip_address || "unknown"}</td>
                  <td
                    style={{
                      maxWidth: 260,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {session.user_agent || "Unknown client"}
                  </td>
                  <td>{new Date(session.created_at).toLocaleString()}</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      disabled={revokingSessionId === session.id}
                      onClick={() => handleRevokeSession(session.id)}
                    >
                      {revokingSessionId === session.id
                        ? "Revoking..."
                        : "Revoke"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
};
