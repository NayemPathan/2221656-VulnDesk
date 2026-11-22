/**
 * frontend/src/api/client.ts
 * --------------------------
 * Centralized HTTP client with in-memory JWT Bearer storage, `credentials: "include"`
 * for HttpOnly refresh cookies, and automatic 401 silent token refresh.
 */

import {
  AdminOverview,
  AdminUser,
  AdminUserCreatePayload,
  AuditLogItem,
  AuthUser,
  CommentCreatePayload,
  CommentItem,
  DashboardSummary,
  GroupItem,
  LoginPayload,
  PaginatedResult,
  RegisterPayload,
  ReportCreatePayload,
  ReportListResponse,
  ReportRead,
  ReportUpdatePayload,
  SecurityViewData,
  SessionItem,
  SeverityUpdatePayload,
  StatusHistoryEntry,
  StatusUpdatePayload,
  TokenResponse,
  UserRole,
} from "../types";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

async function parseErrorResponse(response: Response): Promise<string> {
  let data: unknown = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    data = await response.json();
  } else {
    const text = await response.text();
    data = text ? { detail: text } : null;
  }

  let errorMessage = `Request failed with HTTP ${response.status}`;
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") {
      errorMessage = detail;
    } else if (Array.isArray(detail)) {
      errorMessage = detail
        .map((err: { loc?: (string | number)[]; msg?: string }) => {
          const field = err.loc ? err.loc[err.loc.length - 1] : "field";
          return `${field}: ${err.msg || "invalid value"}`;
        })
        .join(" | ");
    }
  }
  return errorMessage;
}

async function tryRefreshAccessToken(): Promise<TokenResponse | null> {
  try {
    const resp = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      credentials: "include",
    });
    if (!resp.ok) {
      setAccessToken(null);
      return null;
    }
    const data = (await resp.json()) as TokenResponse;
    setAccessToken(data.access_token);
    return data;
  } catch {
    setAccessToken(null);
    return null;
  }
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  allowRefresh = true
): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  let response = await fetch(path, {
    ...options,
    headers,
    credentials: "include",
  });

  // Silent refresh on 401 for non-auth endpoints
  if (
    response.status === 401 &&
    allowRefresh &&
    !path.startsWith("/api/v1/auth/login") &&
    !path.startsWith("/api/v1/auth/register") &&
    !path.startsWith("/api/v1/auth/refresh")
  ) {
    const refreshed = await tryRefreshAccessToken();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${refreshed.access_token}`;
      response = await fetch(path, {
        ...options,
        headers,
        credentials: "include",
      });
    }
  }

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    const msg = await parseErrorResponse(response);
    throw new ApiError(response.status, msg);
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }
  return undefined as T;
}

export interface ListReportsParams {
  keyword?: string;
  status?: string;
  severity?: string;
  component?: string;
  group_id?: number;
  page?: number;
  page_size?: number;
}

export const api = {
  // Auth & Profile
  register: (payload: RegisterPayload): Promise<AuthUser> =>
    apiFetch<AuthUser>(
      "/api/v1/auth/register",
      { method: "POST", body: JSON.stringify(payload) },
      false
    ),

  login: async (payload: LoginPayload): Promise<TokenResponse> => {
    const data = await apiFetch<TokenResponse>(
      "/api/v1/auth/login",
      { method: "POST", body: JSON.stringify(payload) },
      false
    );
    setAccessToken(data.access_token);
    return data;
  },

  refresh: (): Promise<TokenResponse | null> => tryRefreshAccessToken(),

  logout: async (): Promise<void> => {
    try {
      await apiFetch<void>("/api/v1/auth/logout", { method: "POST" }, false);
    } finally {
      setAccessToken(null);
    }
  },

  getMe: (): Promise<AuthUser> => apiFetch<AuthUser>("/api/v1/auth/me"),

  updateMe: (name: string): Promise<AuthUser> =>
    apiFetch<AuthUser>("/api/v1/auth/me", {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),

  changePassword: (
    current_password: string,
    new_password: string
  ): Promise<{ detail: string }> =>
    apiFetch<{ detail: string }>("/api/v1/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    }),

  // Dashboard
  getDashboardSummary: (): Promise<DashboardSummary> =>
    apiFetch<DashboardSummary>("/api/v1/dashboard/summary"),

  // Admin Governance
  adminListUsers: (includeDeleted = false): Promise<AdminUser[]> =>
    apiFetch<AdminUser[]>(
      `/api/v1/admin/users?include_deleted=${includeDeleted}`
    ),

  adminCreateUser: (payload: AdminUserCreatePayload): Promise<AdminUser> =>
    apiFetch<AdminUser>("/api/v1/admin/users", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  adminUpdateRole: (userId: number, role: UserRole): Promise<AdminUser> =>
    apiFetch<AdminUser>(`/api/v1/admin/users/${userId}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    }),

  adminSetBan: (userId: number, is_banned: boolean): Promise<AdminUser> =>
    apiFetch<AdminUser>(`/api/v1/admin/users/${userId}/ban`, {
      method: "PATCH",
      body: JSON.stringify({ is_banned }),
    }),

  adminDeleteUser: (userId: number): Promise<void> =>
    apiFetch<void>(`/api/v1/admin/users/${userId}`, { method: "DELETE" }),

  // Reports CRUD & Triage
  listReports: (params: ListReportsParams = {}): Promise<ReportListResponse> => {
    const search = new URLSearchParams();
    if (params.keyword?.trim()) search.set("keyword", params.keyword.trim());
    if (params.status) search.set("status", params.status);
    if (params.severity) search.set("severity", params.severity);
    if (params.component?.trim())
      search.set("component", params.component.trim());
    if (params.group_id !== undefined)
      search.set("group_id", String(params.group_id));
    search.set("page", String(params.page ?? 1));
    search.set("page_size", String(params.page_size ?? 10));
    return apiFetch<ReportListResponse>(`/api/v1/reports?${search.toString()}`);
  },

  getReport: (reportId: number | string): Promise<ReportRead> =>
    apiFetch<ReportRead>(`/api/v1/reports/${reportId}`),

  createReport: (payload: ReportCreatePayload): Promise<ReportRead> =>
    apiFetch<ReportRead>("/api/v1/reports", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateReport: (
    reportId: number | string,
    payload: ReportUpdatePayload
  ): Promise<ReportRead> =>
    apiFetch<ReportRead>(`/api/v1/reports/${reportId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  deleteReport: (reportId: number | string): Promise<void> =>
    apiFetch<void>(`/api/v1/reports/${reportId}`, { method: "DELETE" }),

  assignSeverity: (
    reportId: number | string,
    payload: SeverityUpdatePayload
  ): Promise<ReportRead> =>
    apiFetch<ReportRead>(`/api/v1/reports/${reportId}/severity`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  changeStatus: (
    reportId: number | string,
    payload: StatusUpdatePayload
  ): Promise<ReportRead> =>
    apiFetch<ReportRead>(`/api/v1/reports/${reportId}/status`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  getReportHistory: (
    reportId: number | string
  ): Promise<StatusHistoryEntry[]> =>
    apiFetch<StatusHistoryEntry[]>(`/api/v1/reports/${reportId}/history`),

  listComments: (reportId: number | string): Promise<CommentItem[]> =>
    apiFetch<CommentItem[]>(`/api/v1/reports/${reportId}/comments`),

  createComment: (
    reportId: number | string,
    payload: CommentCreatePayload
  ): Promise<CommentItem> =>
    apiFetch<CommentItem>(`/api/v1/reports/${reportId}/comments`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  forgotPassword: (
    email: string
  ): Promise<{ detail: string; reset_token: string | null }> =>
    apiFetch<{ detail: string; reset_token: string | null }>(
      "/api/v1/auth/forgot-password",
      { method: "POST", body: JSON.stringify({ email }) },
      false
    ),

  resetPassword: (
    token: string,
    new_password: string
  ): Promise<{ detail: string }> =>
    apiFetch<{ detail: string }>(
      "/api/v1/auth/reset-password",
      { method: "POST", body: JSON.stringify({ token, new_password }) },
      false
    ),
};

const API_BASE_URL = "/api/v1";

// Sessions
export const listMySessions = (): Promise<SessionItem[]> =>
  apiFetch<SessionItem[]>(`${API_BASE_URL}/auth/sessions`);

export const revokeMySession = (sessionId: number): Promise<void> =>
  apiFetch<void>(`${API_BASE_URL}/auth/sessions/${sessionId}`, {
    method: "DELETE",
  });

// Groups
export const listGroups = (): Promise<GroupItem[]> =>
  apiFetch<GroupItem[]>(`${API_BASE_URL}/groups`);

export const createGroup = (payload: {
  name: string;
  description?: string;
}): Promise<GroupItem> =>
  apiFetch<GroupItem>(`${API_BASE_URL}/groups`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const updateGroup = (
  groupId: number,
  payload: { name: string; description?: string }
): Promise<GroupItem> =>
  apiFetch<GroupItem>(`${API_BASE_URL}/groups/${groupId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

export const deleteGroup = (groupId: number): Promise<void> =>
  apiFetch<void>(`${API_BASE_URL}/groups/${groupId}`, { method: "DELETE" });

export const upsertGroupMember = (
  groupId: number,
  payload: {
    user_id: number;
    can_create: boolean;
    can_edit: boolean;
    can_assign: boolean;
  }
): Promise<GroupItem> =>
  apiFetch<GroupItem>(`${API_BASE_URL}/groups/${groupId}/members`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const removeGroupMember = (
  groupId: number,
  userId: number
): Promise<GroupItem> =>
  apiFetch<GroupItem>(
    `${API_BASE_URL}/groups/${groupId}/members/${userId}`,
    { method: "DELETE" }
  );

// Admin overview, users, moderation, audit, and security
export const getAdminOverview = (): Promise<AdminOverview> =>
  apiFetch<AdminOverview>(`${API_BASE_URL}/admin/overview`);

export const listAdminUsersPaginated = (params: {
  q?: string;
  role?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResult<AdminUser>> => {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.role) qs.set("role", params.role);
  if (params.status) qs.set("status", params.status);
  if (params.page) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));

  return apiFetch<PaginatedResult<AdminUser>>(
    `${API_BASE_URL}/admin/users/paginated?${qs.toString()}`
  );
};

export const getAdminUserDetail = (userId: number): Promise<{
  user: AdminUser;
  reports: ReportRead[];
  groups: GroupItem[];
  sessions: SessionItem[];
  recent_activity: AuditLogItem[];
}> =>
  apiFetch<{
    user: AdminUser;
    reports: ReportRead[];
    groups: GroupItem[];
    sessions: SessionItem[];
    recent_activity: AuditLogItem[];
  }>(`${API_BASE_URL}/admin/users/${userId}`);

export const banUserWithReason = (
  userId: number,
  is_banned: boolean,
  reason?: string
): Promise<AdminUser> =>
  apiFetch<AdminUser>(`${API_BASE_URL}/admin/users/${userId}/ban`, {
    method: "PATCH",
    body: JSON.stringify({ is_banned, reason }),
  });

export const revokeAllUserSessions = (
  userId: number
): Promise<{ revoked: number }> =>
  apiFetch<{ revoked: number }>(
    `${API_BASE_URL}/admin/users/${userId}/sessions`,
    { method: "DELETE" }
  );

export const bulkBanUsers = (
  user_ids: number[],
  reason: string
): Promise<{ affected: number; skipped: number }> =>
  apiFetch<{ affected: number; skipped: number }>(
    `${API_BASE_URL}/admin/users/bulk-ban`,
    { method: "POST", body: JSON.stringify({ user_ids, reason }) }
  );

export const bulkUnbanUsers = (
  user_ids: number[]
): Promise<{ affected: number; skipped: number }> =>
  apiFetch<{ affected: number; skipped: number }>(
    `${API_BASE_URL}/admin/users/bulk-unban`,
    { method: "POST", body: JSON.stringify({ user_ids }) }
  );

export const listAdminReports = (params: {
  q?: string;
  severity?: string;
  status?: string;
  page?: number;
}): Promise<PaginatedResult<ReportRead>> => {
  const qs = new URLSearchParams();
  if (params.q) qs.set("q", params.q);
  if (params.severity) qs.set("severity", params.severity);
  if (params.status) qs.set("status", params.status);
  if (params.page) qs.set("page", String(params.page));

  return apiFetch<PaginatedResult<ReportRead>>(
    `${API_BASE_URL}/admin/reports?${qs.toString()}`
  );
};

export const bulkDeleteReports = (
  report_ids: number[]
): Promise<{ affected: number; skipped: number }> =>
  apiFetch<{ affected: number; skipped: number }>(
    `${API_BASE_URL}/admin/reports/bulk-delete`,
    { method: "POST", body: JSON.stringify({ report_ids }) }
  );

export const listAdminGroups = (): Promise<GroupItem[]> =>
  apiFetch<GroupItem[]>(`${API_BASE_URL}/admin/groups`);

export const adminDeleteGroup = (groupId: number): Promise<void> =>
  apiFetch<void>(`${API_BASE_URL}/admin/groups/${groupId}`, {
    method: "DELETE",
  });

export const listAuditLogs = (params: {
  action?: string;
  q?: string;
  page?: number;
}): Promise<PaginatedResult<AuditLogItem>> => {
  const qs = new URLSearchParams();
  if (params.action) qs.set("action", params.action);
  if (params.q) qs.set("q", params.q);
  if (params.page) qs.set("page", String(params.page));

  return apiFetch<PaginatedResult<AuditLogItem>>(
    `${API_BASE_URL}/admin/audit-logs?${qs.toString()}`
  );
};

export const getSecurityView = (): Promise<SecurityViewData> =>
  apiFetch<SecurityViewData>(`${API_BASE_URL}/admin/security`);

export async function downloadAdminCsv(
  kind: "users" | "reports" | "audit-logs",
  params: Record<string, string | undefined>
): Promise<void> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) qs.set(key, value);
  });

  const query = qs.toString();
  const token = getAccessToken();
  const response = await fetch(
    `${API_BASE_URL}/admin/export/${kind}${query ? `?${query}` : ""}`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      credentials: "include",
    }
  );

  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorResponse(response));
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `vulndesk_${kind}.csv`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export const listGroupCandidateUsers = () =>
  apiFetch<{ id: number; name: string; email: string; role: string }[]>(
    `${API_BASE_URL}/groups/users-directory`
  );