import React, { useCallback, useEffect, useState } from "react";
import {
  adminDeleteGroup,
  api,
  ApiError,
  bulkBanUsers,
  bulkDeleteReports,
  bulkUnbanUsers,
  downloadAdminCsv,
  getAdminOverview,
  getSecurityView,
  listAdminGroups,
  listAdminReports,
  listAuditLogs,
} from "../api/client";
import { RoleBadge } from "../components/Badges";
import { PasswordInput } from "../components/PasswordInput";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import {
  AdminOverview,
  AdminUser,
  AuditLogItem,
  GroupItem,
  ReportRead,
  SecurityViewData,
  UserRole,
} from "../types";

type AdminTab = "users" | "moderation" | "audit" | "security";

export const AdminUsersPage: React.FC = () => {
  const { currentUser } = useAuth();
  const { showToast, confirmAction } = useToast();

  const [activeTab, setActiveTab] = useState<AdminTab>("users");
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selectedUserIds, setSelectedUserIds] = useState<number[]>([]);
  const [bulkBanReason, setBulkBanReason] = useState("");

  const [moderationReports, setModerationReports] = useState<ReportRead[]>([]);
  const [selectedReportIds, setSelectedReportIds] = useState<number[]>([]);
  const [moderationGroups, setModerationGroups] = useState<GroupItem[]>([]);
  const [moderationPage, setModerationPage] = useState(1);
  const [moderationTotal, setModerationTotal] = useState(0);
  const [moderationLoading, setModerationLoading] = useState(false);

  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditPage, setAuditPage] = useState(1);
  const [auditAction, setAuditAction] = useState("");
  const [auditActionInput, setAuditActionInput] = useState("");
  const [auditSearchInput, setAuditSearchInput] = useState("");
  const [auditSearch, setAuditSearch] = useState("");
  const [auditLoading, setAuditLoading] = useState(false);

  const [securityView, setSecurityView] = useState<SecurityViewData | null>(null);
  const [securityLoading, setSecurityLoading] = useState(false);

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

  useEffect(() => {
    getAdminOverview()
      .then(setOverview)
      .catch((err: unknown) => {
        showToast(
          err instanceof ApiError ? err.message : "Failed to load admin overview.",
          "error"
        );
      });
  }, [showToast]);

  const loadModeration = useCallback(async () => {
    setModerationLoading(true);
    try {
      const [reportPage, groups] = await Promise.all([
        listAdminReports({ page: moderationPage }),
        listAdminGroups(),
      ]);
      setModerationReports(reportPage.items);
      setModerationTotal(reportPage.total);
      setModerationGroups(groups);
    } catch (err) {
      showToast(
        err instanceof ApiError ? err.message : "Failed to load moderation data.",
        "error"
      );
    } finally {
      setModerationLoading(false);
    }
  }, [moderationPage, showToast]);

  useEffect(() => {
    if (activeTab === "moderation") void loadModeration();
  }, [activeTab, loadModeration]);

  const loadAuditLogs = useCallback(async () => {
    setAuditLoading(true);
    try {
      const result = await listAuditLogs({
        action: auditAction || undefined,
        q: auditSearch || undefined,
        page: auditPage,
      });
      setAuditLogs(result.items);
      setAuditTotal(result.total);
    } catch (err) {
      showToast(
        err instanceof ApiError ? err.message : "Failed to load audit logs.",
        "error"
      );
    } finally {
      setAuditLoading(false);
    }
  }, [auditAction, auditPage, auditSearch, showToast]);

  useEffect(() => {
    if (activeTab === "audit") void loadAuditLogs();
  }, [activeTab, loadAuditLogs]);

  const loadSecurityView = useCallback(async () => {
    setSecurityLoading(true);
    try {
      setSecurityView(await getSecurityView());
    } catch (err) {
      showToast(
        err instanceof ApiError ? err.message : "Failed to load security view.",
        "error"
      );
    } finally {
      setSecurityLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    if (activeTab === "security" && !securityView) void loadSecurityView();
  }, [activeTab, loadSecurityView, securityView]);

  const handleBulkUserAction = async (ban: boolean) => {
    if (selectedUserIds.length === 0) return;
    try {
      const result = ban
        ? await bulkBanUsers(selectedUserIds, bulkBanReason.trim())
        : await bulkUnbanUsers(selectedUserIds);
      showToast(
        `${ban ? "Ban" : "Unban"} completed: ${result.affected} affected, ${result.skipped} skipped.`,
        "success"
      );
      setSelectedUserIds([]);
      setBulkBanReason("");
      await loadUsers();
    } catch (err) {
      showToast(
        err instanceof ApiError ? err.message : "Bulk user action failed.",
        "error"
      );
    }
  };

  const handleBulkDeleteReports = () => {
    if (selectedReportIds.length === 0) return;
    confirmAction({
      title: "Delete selected reports?",
      message: `This permanently deletes ${selectedReportIds.length} report(s) and their related records.`,
      confirmLabel: "Delete Reports",
      onConfirm: async () => {
        try {
          const result = await bulkDeleteReports(selectedReportIds);
          showToast(
            `Report deletion completed: ${result.affected} deleted, ${result.skipped} skipped.`,
            "success"
          );
          setSelectedReportIds([]);
          await loadModeration();
        } catch (err) {
          showToast(
            err instanceof ApiError ? err.message : "Failed to delete reports.",
            "error"
          );
        }
      },
    });
  };

  const handleAdminDeleteGroup = (group: GroupItem) => {
    confirmAction({
      title: `Delete "${group.name}"?`,
      message: "This removes the group and its memberships.",
      confirmLabel: "Delete Group",
      onConfirm: async () => {
        try {
          await adminDeleteGroup(group.id);
          showToast(`Deleted group "${group.name}".`, "success");
          await loadModeration();
        } catch (err) {
          showToast(
            err instanceof ApiError ? err.message : "Failed to delete group.",
            "error"
          );
        }
      },
    });
  };

  const handleCsvDownload = async (
    kind: "users" | "reports" | "audit-logs",
    params: Record<string, string | undefined> = {}
  ) => {
    try {
      await downloadAdminCsv(kind, params);
    } catch (err) {
      showToast(
        err instanceof ApiError ? err.message : "Failed to export CSV.",
        "error"
      );
    }
  };

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
      showToast("User account created.", "success");
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
            Platform users, moderation, audit activity, and security signals.
          </p>
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {overview && (
        <div className="kpi-grid mb-3">
          {[
            ["Total Users", overview.total_users],
            ["Banned Users", overview.banned_users],
            ["Total Reports", overview.total_reports],
            ["Groups", overview.total_groups],
            ["New Users (7d)", overview.new_users_7d],
            ["New Reports (7d)", overview.new_reports_7d],
          ].map(([label, value]) => (
            <div className="kpi-card" key={label}>
              <span className="kpi-label">{label}</span>
              <strong className="kpi-value">{value}</strong>
            </div>
          ))}
        </div>
      )}

      <div
        className="owner-actions mb-3"
        role="tablist"
        aria-label="Admin sections"
      >
        {(
          [
            ["users", "Users"],
            ["moderation", "Moderation"],
            ["audit", "Audit Log"],
            ["security", "Security View"],
          ] as const
        ).map(([tab, label]) => (
          <button
            key={tab}
            type="button"
            role="tab"
            aria-selected={activeTab === tab}
            className={`btn btn-sm ${
              activeTab === tab ? "btn-primary" : "btn-secondary"
            }`}
            onClick={() => setActiveTab(tab)}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === "users" && (
        <>
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
              <PasswordInput
                id="admin-create-pw"
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
            <div className="page-header">
              <h2 className="section-title">Platform Users</h2>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => handleCsvDownload("users", {})}
              >
                Export CSV
              </button>
            </div>
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
                              showToast(`Updated role for ${u.email}`, "success");
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
                        <div
                          className="owner-actions"
                          style={{ justifyContent: "flex-end" }}
                        >
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            disabled={isSelf}
                            onClick={async () => {
                              const prevBanned = u.is_banned;
                              try {
                                await api.adminSetBan(u.id, !prevBanned);
                                await loadUsers();
                                showToast(
                                  prevBanned
                                    ? `Unbanned ${u.email}`
                                    : `Banned ${u.email}`,
                                  "info",
                                  async () => {
                                    await api.adminSetBan(u.id, prevBanned);
                                    await loadUsers();
                                    showToast(
                                      `Reverted ban status for ${u.email}`,
                                      "success"
                                    );
                                  }
                                );
                              } catch (err) {
                                showToast(
                                  err instanceof ApiError
                                    ? err.message
                                    : "Failed to update ban status.",
                                  "error"
                                );
                              }
                            }}
                          >
                            {u.is_banned ? "Unban" : "Ban"}
                          </button>
                          <button
                            type="button"
                            className="btn btn-danger btn-sm"
                            disabled={isSelf}
                            onClick={() => {
                              confirmAction({
                                title: `Soft-delete ${u.email}?`,
                                message:
                                  "This disables login and revokes active sessions while preserving historical report audit trails.",
                                confirmLabel: "Soft-Delete User",
                                onConfirm: async () => {
                                  try {
                                    await api.adminDeleteUser(u.id);
                                    await loadUsers();
                                    showToast(
                                      `Soft-deleted ${u.email}`,
                                      "success"
                                    );
                                  } catch (err) {
                                    showToast(
                                      err instanceof ApiError
                                        ? err.message
                                        : "Failed to delete user.",
                                      "error"
                                    );
                                  }
                                },
                              });
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
        </>
      )}

      {activeTab === "moderation" && (
        <div className="vuln-form">
          <section className="card form-card">
            <div className="page-header">
              <div>
                <h2 className="section-title">Bulk User Moderation</h2>
                <p className="page-subtitle">
                  Administrators and your own account cannot be selected.
                </p>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => handleCsvDownload("users", {})}
              >
                Export Users
              </button>
            </div>
            <div className="filter-grid mb-3">
              <input
                className="form-input"
                placeholder="Ban reason"
                value={bulkBanReason}
                onChange={(e) => setBulkBanReason(e.target.value)}
              />
              <button
                type="button"
                className="btn btn-danger btn-sm"
                disabled={!selectedUserIds.length}
                onClick={() => void handleBulkUserAction(true)}
              >
                Ban Selected ({selectedUserIds.length})
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={!selectedUserIds.length}
                onClick={() => void handleBulkUserAction(false)}
              >
                Unban Selected
              </button>
            </div>
            <div className="table-card">
              <table className="reports-table">
                <thead>
                  <tr>
                    <th>Select</th>
                    <th>User</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Ban Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => {
                    const disabled =
                      user.id === currentUser?.id || user.role === "admin";
                    return (
                      <tr key={user.id}>
                        <td>
                          <input
                            type="checkbox"
                            aria-label={`Select ${user.email}`}
                            disabled={disabled}
                            checked={selectedUserIds.includes(user.id)}
                            onChange={(e) =>
                              setSelectedUserIds((current) =>
                                e.target.checked
                                  ? [...current, user.id]
                                  : current.filter((id) => id !== user.id)
                              )
                            }
                          />
                        </td>
                        <td>
                          {user.name}
                          <div className="field-hint">{user.email}</div>
                        </td>
                        <td>{user.role}</td>
                        <td>{user.is_banned ? "Banned" : "Active"}</td>
                        <td>{user.ban_reason || "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          <section className="card form-card">
            <div className="page-header">
              <h2 className="section-title">Report Moderation</h2>
              <div className="owner-actions">
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => handleCsvDownload("reports", {})}
                >
                  Export Reports
                </button>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  disabled={!selectedReportIds.length}
                  onClick={handleBulkDeleteReports}
                >
                  Delete Selected ({selectedReportIds.length})
                </button>
              </div>
            </div>
            {moderationLoading ? (
              <p className="muted">Loading moderation data...</p>
            ) : (
              <>
                <div className="table-card">
                  <table className="reports-table">
                    <thead>
                      <tr>
                        <th>Select</th>
                        <th>Report</th>
                        <th>Severity</th>
                        <th>Status</th>
                        <th>Reporter ID</th>
                      </tr>
                    </thead>
                    <tbody>
                      {moderationReports.map((report) => (
                        <tr key={report.id}>
                          <td>
                            <input
                              type="checkbox"
                              aria-label={`Select report ${report.id}`}
                              checked={selectedReportIds.includes(report.id)}
                              onChange={(e) =>
                                setSelectedReportIds((current) =>
                                  e.target.checked
                                    ? [...current, report.id]
                                    : current.filter((id) => id !== report.id)
                                )
                              }
                            />
                          </td>
                          <td>
                            <strong>#{report.id} {report.title}</strong>
                            <div className="field-hint">{report.component}</div>
                          </td>
                          <td>{report.final_severity || report.proposed_severity}</td>
                          <td>{report.status}</td>
                          <td>{report.reporter_id}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="form-actions">
                  <span className="field-hint">
                    {moderationTotal} report(s)
                  </span>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={moderationPage <= 1}
                    onClick={() => setModerationPage((page) => page - 1)}
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={moderationPage * 15 >= moderationTotal}
                    onClick={() => setModerationPage((page) => page + 1)}
                  >
                    Next
                  </button>
                </div>
              </>
            )}
          </section>

          <section className="card form-card">
            <h2 className="section-title">Group Moderation</h2>
            {moderationGroups.length === 0 ? (
              <p className="muted">No groups found.</p>
            ) : (
              <div className="table-card">
                <table className="reports-table">
                  <thead>
                    <tr>
                      <th>Group</th>
                      <th>Owner</th>
                      <th>Members</th>
                      <th>Created</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {moderationGroups.map((group) => (
                      <tr key={group.id}>
                        <td>{group.name}</td>
                        <td>{group.owner_email}</td>
                        <td>{group.members?.length ?? 0}</td>
                        <td>{new Date(group.created_at).toLocaleDateString()}</td>
                        <td>
                          <button
                            type="button"
                            className="btn btn-danger btn-sm"
                            onClick={() => handleAdminDeleteGroup(group)}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}

      {activeTab === "audit" && (
        <section className="card form-card">
          <div className="page-header">
            <div>
              <h2 className="section-title">Audit Log</h2>
              <p className="page-subtitle">{auditTotal} event(s)</p>
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() =>
                void handleCsvDownload("audit-logs", {
                    action: auditAction || undefined,
                    q: auditSearch || undefined,
                  })
              }
            >
              Export CSV
            </button>
          </div>
          <form
            className="filter-grid mb-3"
            onSubmit={(e) => {
              e.preventDefault();
              setAuditPage(1);
              setAuditAction(auditActionInput.trim());
              setAuditSearch(auditSearchInput.trim());
            }}
          >
            <input
              className="form-input"
              placeholder="Filter by action"
              value={auditActionInput}
              onChange={(e) => setAuditActionInput(e.target.value)}
            />
            <input
              className="form-input"
              placeholder="Search email or details"
              value={auditSearchInput}
              onChange={(e) => setAuditSearchInput(e.target.value)}
            />
            <button type="submit" className="btn btn-primary btn-sm">
              Search
            </button>
          </form>
          {auditLoading ? (
            <p className="muted">Loading audit logs...</p>
          ) : (
            <div className="table-card">
              <table className="reports-table">
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Actor</th>
                    <th>Action</th>
                    <th>Target</th>
                    <th>Details</th>
                    <th>IP Address</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.map((entry) => (
                    <tr key={entry.id}>
                      <td>{new Date(entry.created_at).toLocaleString()}</td>
                      <td>{entry.actor_email}</td>
                      <td>{entry.action}</td>
                      <td>
                        {entry.target_type || "—"}
                        {entry.target_id ? ` #${entry.target_id}` : ""}
                      </td>
                      <td>{entry.details || "—"}</td>
                      <td>{entry.ip_address || "unknown"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="form-actions">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={auditPage <= 1}
              onClick={() => setAuditPage((page) => page - 1)}
            >
              Previous
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={auditPage * 20 >= auditTotal}
              onClick={() => setAuditPage((page) => page + 1)}
            >
              Next
            </button>
          </div>
        </section>
      )}

      {activeTab === "security" && (
        <section className="card form-card">
          <div className="page-header">
            <div>
              <h2 className="section-title">Security View</h2>
              <p className="page-subtitle">
                Failed login activity grouped by IP address and account.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => void loadSecurityView()}
            >
              Refresh
            </button>
          </div>
          {securityLoading ? (
            <p className="muted">Loading security data...</p>
          ) : securityView ? (
            <>
              <div className="kpi-grid mb-3">
                <div className="kpi-card">
                  <span className="kpi-label">Failed Login IPs</span>
                  <strong className="kpi-value">
                    {securityView.failed_by_ip.length}
                  </strong>
                </div>
                <div className="kpi-card">
                  <span className="kpi-label">Affected Accounts</span>
                  <strong className="kpi-value">
                    {securityView.failed_by_account.length}
                  </strong>
                </div>
                <div className="kpi-card">
                  <span className="kpi-label">Recent Failures</span>
                  <strong className="kpi-value">
                    {securityView.recent_failures.length}
                  </strong>
                </div>
              </div>
              <div className="form-row-2">
                <div className="card">
                  <h3 className="section-title">By IP Address</h3>
                  {securityView.failed_by_ip.length === 0 ? (
                    <p className="muted">No failed logins recorded.</p>
                  ) : (
                    <table className="reports-table">
                      <thead>
                        <tr><th>IP Address</th><th>Failures</th></tr>
                      </thead>
                      <tbody>
                        {securityView.failed_by_ip.map((item) => (
                          <tr key={item.ip}>
                            <td>{item.ip}</td>
                            <td>{item.count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
                <div className="card">
                  <h3 className="section-title">By Account</h3>
                  {securityView.failed_by_account.length === 0 ? (
                    <p className="muted">No failed logins recorded.</p>
                  ) : (
                    <table className="reports-table">
                      <thead>
                        <tr><th>Account</th><th>Failures</th></tr>
                      </thead>
                      <tbody>
                        {securityView.failed_by_account.map((item) => (
                          <tr key={item.email}>
                            <td>{item.email}</td>
                            <td>{item.count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
              <h3 className="section-title mt-3">Recent Failed Logins</h3>
              <div className="table-card">
                <table className="reports-table">
                  <thead>
                    <tr>
                      <th>When</th>
                      <th>Account</th>
                      <th>IP Address</th>
                      <th>Client</th>
                    </tr>
                  </thead>
                  <tbody>
                    {securityView.recent_failures.map((entry) => (
                      <tr key={entry.id}>
                        <td>{new Date(entry.created_at).toLocaleString()}</td>
                        <td>{entry.actor_email}</td>
                        <td>{entry.ip_address || "unknown"}</td>
                        <td>{entry.user_agent || "Unknown client"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p className="muted">Security data is unavailable.</p>
          )}
        </section>
      )}
    </div>
  );
};