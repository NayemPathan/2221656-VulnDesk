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
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");

  const [moderationReports, setModerationReports] = useState<ReportRead[]>([]);
  const [selectedReportIds, setSelectedReportIds] = useState<number[]>([]);
  const [moderationGroups, setModerationGroups] = useState<GroupItem[]>([]);
  const [moderationPage, setModerationPage] = useState(1);
  const [moderationPageSize, setModerationPageSize] = useState(15);
  const [moderationTotal, setModerationTotal] = useState(0);
  const [moderationLoading, setModerationLoading] = useState(false);
  const [reportQ, setReportQ] = useState("");
  const [reportQInput, setReportQInput] = useState("");
  const [severity, setSeverity] = useState("");
  const [severityInput, setSeverityInput] = useState("");
  const [reportStatus, setReportStatus] = useState("");
  const [reportStatusInput, setReportStatusInput] = useState("");

  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditPage, setAuditPage] = useState(1);
  const [auditAction, setAuditAction] = useState("");
  const [auditSearchInput, setAuditSearchInput] = useState("");
  const [auditSearch, setAuditSearch] = useState("");
  const [auditLoading, setAuditLoading] = useState(false);

  const [securityView, setSecurityView] = useState<SecurityViewData | null>(null);
  const [securityLoading, setSecurityLoading] = useState(false);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newUserRole, setNewUserRole] = useState<UserRole>("analyst");

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
        listAdminReports({
          q: reportQ || undefined,
          severity: severity || undefined,
          status: reportStatus || undefined,
          page: moderationPage,
        }),
        listAdminGroups(),
      ]);
      setModerationReports(reportPage.items);
      setModerationTotal(reportPage.total);
      setModerationPageSize(reportPage.page_size);
      setModerationGroups(groups);
    } catch (err) {
      showToast(
        err instanceof ApiError ? err.message : "Failed to load moderation data.",
        "error"
      );
    } finally {
      setModerationLoading(false);
    }
  }, [moderationPage, reportQ, reportStatus, severity, showToast]);

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

  const handleBulkBan = async (userIds: number[]) => {
    if (userIds.length === 0) return;
    try {
      const result = await bulkBanUsers(userIds, bulkBanReason.trim());
      showToast(
        `Ban completed: ${result.affected} affected, ${result.skipped} skipped.`,
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

  const handleBulkUnban = async (userIds: number[]) => {
    if (userIds.length === 0) return;
    try {
      const result = await bulkUnbanUsers(userIds);
      showToast(
        `Unban completed: ${result.affected} affected, ${result.skipped} skipped.`,
        "success"
      );
      setSelectedUserIds([]);
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

  const handleAdminDeleteGroup = (groupId: number, groupName: string) => {
    confirmAction({
      title: `Delete "${groupName}"?`,
      message: "This removes the group and its memberships.",
      confirmLabel: "Delete Group",
      onConfirm: async () => {
        try {
          await adminDeleteGroup(groupId);
          showToast(`Deleted group "${groupName}".`, "success");
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
        role: newUserRole,
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
  const normalizedUserQuery = q.trim().toLowerCase();
  const filteredUsers = users.filter((user) => {
    const matchesQuery =
      !normalizedUserQuery ||
      user.name.toLowerCase().includes(normalizedUserQuery) ||
      user.email.toLowerCase().includes(normalizedUserQuery);
    const matchesRole = !role || user.role === role;
    const matchesStatus =
      !status || (status === "banned" ? user.is_banned : !user.is_banned);
    return matchesQuery && matchesRole && matchesStatus;
  });
  const selectedUserObjects = users.filter((u) => selectedUserIds.includes(u.id));
  const eligibleToBanIds = selectedUserObjects
    .filter((u) => !u.is_banned && u.role !== "admin" && u.id !== currentUser?.id)
    .map((u) => u.id);
  const eligibleToUnbanIds = selectedUserObjects
    .filter((u) => u.is_banned && u.role !== "admin" && u.id !== currentUser?.id)
    .map((u) => u.id);


  return (
    <div className="page-container">
      <div className="page-hero">
        <div>
          <span className="page-hero-eyebrow">Admin Console</span>
          <h1>Admin User Governance</h1>
          <p>
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

      <div className="tab-bar" role="tablist" aria-label="Admin sections">
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
            className={tab === activeTab ? "tab-btn active" : "tab-btn"}
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
                value={newUserRole}
                onChange={(e) => setNewUserRole(e.target.value as UserRole)}
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
            <h2 className="section-title">Platform Users</h2>
            <div className="filter-grid mb-3">
              <input
                className="form-input"
                placeholder="Search name or email"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <select
                className="form-select"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                aria-label="Filter users by role"
              >
                <option value="">All roles</option>
                <option value="researcher">Researcher</option>
                <option value="analyst">Analyst</option>
                <option value="admin">Admin</option>
              </select>
              <select
                className="form-select"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                aria-label="Filter users by status"
              >
                <option value="">All statuses</option>
                <option value="active">Active</option>
                <option value="banned">Banned</option>
              </select>
            </div>
            <div className="bulk-bar">
              <span className="muted">
                <strong>{selectedUserIds.length}</strong> user(s) selected
              </span>
              <div className="bulk-bar-actions">
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  disabled={eligibleToBanIds.length === 0}
                  onClick={() => void handleBulkBan(eligibleToBanIds)}
                >
                  Ban Selected ({eligibleToBanIds.length})
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  disabled={eligibleToUnbanIds.length === 0}
                  onClick={() => void handleBulkUnban(eligibleToUnbanIds)}
                >
                  Unban Selected ({eligibleToUnbanIds.length})
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() =>
                    void handleCsvDownload("users", {
                      q: q || undefined,
                      role: role || undefined,
                      status: status || undefined,
                    })
                  }
                >
                  Export Users CSV
                </button>
              </div>
            </div>
            <div className="filter-grid mb-3">
              <input
                className="form-input"
                placeholder="Reason for bulk ban"
                value={bulkBanReason}
                onChange={(e) => setBulkBanReason(e.target.value)}
              />
            </div>
            <div className="table-wrap">
              <table className="data-table">
              <thead>
                <tr>
                  <th>Select</th>
                  <th>User</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((u) => {
                  const isSelf = u.id === currentUser?.id;
                  const cannotBulkModerate =
                    isSelf || u.role === "admin";
                  return (
                    <tr key={u.id}>
                      <td>
                        <input
                          type="checkbox"
                          aria-label={`Select ${u.email}`}
                          disabled={cannotBulkModerate}
                          checked={selectedUserIds.includes(u.id)}
                          onChange={(e) =>
                            setSelectedUserIds((current) =>
                              e.target.checked
                                ? [...current, u.id]
                                : current.filter((id) => id !== u.id)
                            )
                          }
                        />
                      </td>
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
          </div>
        </>
      )}

      {activeTab === "moderation" && (
        <div className="vuln-form">
          <section className="card form-card">
            <h2 className="section-title">Report Moderation</h2>
            <form
              className="filter-grid mb-3"
              onSubmit={(e) => {
                e.preventDefault();
                setModerationPage(1);
                setReportQ(reportQInput.trim());
                setSeverity(severityInput);
                setReportStatus(reportStatusInput);
                setSelectedReportIds([]);
              }}
            >
              <input
                className="form-input"
                placeholder="Search reports"
                value={reportQInput}
                onChange={(e) => setReportQInput(e.target.value)}
              />
              <select
                className="form-select"
                value={severityInput}
                onChange={(e) => setSeverityInput(e.target.value)}
                aria-label="Filter reports by severity"
              >
                <option value="">All severities</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
              <select
                className="form-select"
                value={reportStatusInput}
                onChange={(e) => setReportStatusInput(e.target.value)}
                aria-label="Filter reports by status"
              >
                <option value="">All statuses</option>
                <option value="new">New</option>
                <option value="under_review">Under Review</option>
                <option value="confirmed">Confirmed</option>
                <option value="fixed">Fixed</option>
                <option value="closed">Closed</option>
                <option value="rejected">Rejected</option>
                <option value="duplicate">Duplicate</option>
              </select>
              <button type="submit" className="btn btn-primary btn-sm">
                Apply Filters
              </button>
            </form>
            <div className="bulk-bar">
              <span className="muted">
                <strong>{selectedReportIds.length}</strong> report(s) selected
              </span>
              <div className="bulk-bar-actions">
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  disabled={selectedReportIds.length === 0}
                  onClick={handleBulkDeleteReports}
                >
                  Delete Selected ({selectedReportIds.length})
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() =>
                    void handleCsvDownload("reports", {
                      q: reportQ || undefined,
                      severity: severity || undefined,
                      status: reportStatus || undefined,
                    })
                  }
                >
                  Export Reports CSV
                </button>
              </div>
            </div>
            {moderationLoading ? (
              <p className="muted">Loading moderation data...</p>
            ) : (
              <>
                <div className="table-wrap">
                  <table className="data-table">
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
                    disabled={
                      moderationPage * moderationPageSize >= moderationTotal
                    }
                    onClick={() => setModerationPage((page) => page + 1)}
                  >
                    Next
                  </button>
                </div>
              </>
            )}
          </section>

          <section className="card" style={{ marginTop: "1.25rem" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "0.75rem",
              }}
            >
              <h3 style={{ margin: 0 }}>
                Shared Groups Moderation ({moderationGroups.length})
              </h3>
            </div>
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Group Name</th>
                    <th>Owner</th>
                    <th>Members</th>
                    <th>Created</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {moderationGroups.map((group) => (
                    <tr key={group.id}>
                      <td>#{group.id}</td>
                      <td>
                        <strong>{group.name}</strong>
                        {group.description && (
                          <div
                            className="muted"
                            style={{ fontSize: "0.8rem" }}
                          >
                            {group.description}
                          </div>
                        )}
                      </td>
                      <td>{group.owner_email ?? `User #${group.owner_id}`}</td>
                      <td>
                        <span className="perm-pill on">
                          {group.members?.length ?? 0} member(s)
                        </span>
                      </td>
                      <td>
                        {new Date(group.created_at).toLocaleDateString()}
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-danger btn-sm"
                          onClick={() =>
                            handleAdminDeleteGroup(group.id, group.name)
                          }
                        >
                          Delete Group
                        </button>
                      </td>
                    </tr>
                  ))}
                  {moderationGroups.length === 0 && (
                    <tr>
                      <td colSpan={6} className="muted">
                        No shared groups found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
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
              setAuditSearch(auditSearchInput.trim());
            }}
          >
            <select
              value={auditAction}
              onChange={(e) => {
                setAuditAction(e.target.value);
                setAuditPage(1);
              }}
              className="form-select filter-select"
              aria-label="Filter audit logs by action"
            >
              <option value="">All Actions</option>
              <option value="login">Login</option>
              <option value="failed_login">Failed Login</option>
              <option value="logout">Logout</option>
              <option value="profile_update">Profile Update</option>
              <option value="password_change">Password Change</option>
              <option value="session_revoke">Session Revoke</option>
              <option value="role_change">Role Change</option>
              <option value="ban">Ban User</option>
              <option value="unban">Unban User</option>
              <option value="delete">Delete (User / Report)</option>
              <option value="group_create">Group Create</option>
              <option value="group_delete">Group Delete</option>
              <option value="export">CSV Export</option>
            </select>
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
            <div className="table-wrap">
              <table className="data-table">
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
                        {entry.target_type ? (
                          <span
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "0.4rem",
                            }}
                          >
                            <span
                              className="perm-pill off"
                              style={{ textTransform: "capitalize" }}
                            >
                              {entry.target_type}
                            </span>
                            <span>
                              {entry.target_label ||
                                (entry.target_id ? `#${entry.target_id}` : "—")}
                            </span>
                          </span>
                        ) : (
                          "—"
                        )}
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
                    <div className="table-wrap">
                      <table className="data-table">
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
                    </div>
                  )}
                </div>
                <div className="card">
                  <h3 className="section-title">By Account</h3>
                  {securityView.failed_by_account.length === 0 ? (
                    <p className="muted">No failed logins recorded.</p>
                  ) : (
                    <div className="table-wrap">
                      <table className="data-table">
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
                    </div>
                  )}
                </div>
              </div>
              <h3 className="section-title mt-3">Recent Failed Logins</h3>
              <div className="table-wrap">
                <table className="data-table">
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