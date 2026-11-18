import React, { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { RoleBadge } from "../components/Badges";
import { useAuth } from "../context/AuthContext";
import { AdminUser, UserRole } from "../types";


export const AdminUsersPage: React.FC = () => {
  const { currentUser } = useAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);


  // Create User form state
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("analyst");


  const loadUsers = useCallback(async () => {
    try {
      const data = await api.adminListUsers(false);
      setUsers(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load users.");
    }
  }, []);


  useEffect(() => {
    loadUsers();
  }, [loadUsers]);


  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    try {
      await api.adminCreateUser({
        name: name.trim(),
        email: email.trim(),
        password,
        role,
      });
      setName("");
      setEmail("");
      setPassword("");
      setSuccess("User created.");
      await loadUsers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Create failed.");
    }
  };


  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Admin User Governance</h1>
          <p className="page-subtitle">
            Manage roles, ban/unban researchers, and soft-delete accounts.
          </p>
        </div>
      </div>


      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}


      <div className="card form-card mb-3">
        <h2 className="section-title">Create New Account</h2>
        <form onSubmit={handleCreateUser} className="filter-grid mt-2">
          <input
            type="text"
            className="form-input"
            placeholder="Full Name"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            type="email"
            className="form-input"
            placeholder="Email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            type="password"
            className="form-input"
            placeholder="Password (min 8)"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <select
            className="form-select"
            value={role}
            onChange={(e) => setRole(e.target.value as UserRole)}
          >
            <option value="researcher">Researcher</option>
            <option value="analyst">Analyst</option>
            <option value="admin">Admin</option>
          </select>
          <button type="submit" className="btn btn-primary btn-sm">
            + Create User
          </button>
        </form>
      </div>


      <div className="card table-card">
        <table className="reports-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Role</th>
              <th>Status</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => {
              const isSelf = u.id === currentUser?.id;
              return (
                <tr key={u.id}>
                  <td>
                    <strong>{u.name}</strong>
                    <div className="field-hint">{u.email}</div>
                  </td>
                  <td>
                    <select
                      className="form-select"
                      disabled={isSelf}
                      value={u.role}
                      onChange={async (e) => {
                        setError(null);
                        try {
                          await api.adminUpdateRole(
                            u.id,
                            e.target.value as UserRole
                          );
                          await loadUsers();
                        } catch (err) {
                          setError(
                            err instanceof ApiError
                              ? err.message
                              : "Role update failed"
                          );
                        }
                      }}
                    >
                      <option value="researcher">researcher</option>
                      <option value="analyst">analyst</option>
                      <option value="admin">admin</option>
                    </select>
                  </td>
                  <td>
                    <RoleBadge role={u.role} isBanned={u.is_banned} />
                  </td>
                  <td className="text-right">
                    <div className="owner-actions" style={{ justifyContent: "flex-end" }}>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        disabled={isSelf}
                        onClick={async () => {
                          await api.adminSetBan(u.id, !u.is_banned);
                          await loadUsers();
                        }}
                      >
                        {u.is_banned ? "Unban" : "Ban"}
                      </button>
                      <button
                        type="button"
                        className="btn btn-danger btn-sm"
                        disabled={isSelf}
                        onClick={async () => {
                          if (window.confirm(`Soft-delete ${u.email}?`)) {
                            await api.adminDeleteUser(u.id);
                            await loadUsers();
                          }
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
