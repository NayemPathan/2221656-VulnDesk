/**
 * frontend/src/api/client.ts
 * --------------------------
 * Centralized HTTP client for the VulnDesk FastAPI backend.
 *
 * Why we centralize fetch calls:
 * 1. Automatically attaches the `X-Demo-User` header on every request so our
 *    FastAPI RBAC dependency (`get_current_user` in `app/deps.py`) knows which
 *    seeded persona is acting.
 * 2. Normalizes FastAPI validation errors (HTTP 422 array of field issues) and
 *    business-rule conflicts (HTTP 403 / 404 / 409 string `detail`) into a
 *    clean `ApiError` with status code and human-readable message.
 * 3. Uses relative `/api/v1/...` paths so the exact same code works locally
 *    via Vite's dev proxy (`localhost:5173 -> 127.0.0.1:8000`) and in
 *    production on Vercel (`vercel.json` serverless rewrite).
 */

import {
  CommentCreatePayload,
  CommentItem,
  DemoUser,
  ReportCreatePayload,
  ReportListResponse,
  ReportRead,
  ReportUpdatePayload,
  SeverityUpdatePayload,
  StatusHistoryEntry,
  StatusUpdatePayload,
} from "../types";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const STORAGE_KEY = "vulndesk_demo_user_email";
const DEFAULT_DEMO_EMAIL = "alice@vulndesk.local";

export function getStoredDemoEmail(): string {
  return localStorage.getItem(STORAGE_KEY) || DEFAULT_DEMO_EMAIL;
}

export function setStoredDemoEmail(email: string): void {
  localStorage.setItem(STORAGE_KEY, email);
}

/**
 * Generic JSON request helper that injects `X-Demo-User` and parses FastAPI errors.
 */
async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  demoEmail?: string
): Promise<T> {
  const activeEmail = demoEmail || getStoredDemoEmail();

  const headers: Record<string, string> = {
    "X-Demo-User": activeEmail,
    ...(options.headers as Record<string, string> | undefined),
  };

  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(path, {
    ...options,
    headers,
  });

  // Handle 204 No Content (e.g., DELETE /api/v1/reports/{id})
  if (response.status === 204) {
    return undefined as T;
  }

  let data: unknown = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    data = await response.json();
  } else {
    const text = await response.text();
    data = text ? { detail: text } : null;
  }

  if (!response.ok) {
    let errorMessage = `Request failed with HTTP ${response.status}`;
    if (data && typeof data === "object" && "detail" in data) {
      const detail = (data as { detail: unknown }).detail;
      if (typeof detail === "string") {
        errorMessage = detail;
      } else if (Array.isArray(detail)) {
        // Format Pydantic 422 validation errors into a readable sentence
        errorMessage = detail
          .map((err: { loc?: (string | number)[]; msg?: string }) => {
            const field = err.loc ? err.loc[err.loc.length - 1] : "field";
            return `${field}: ${err.msg || "invalid value"}`;
          })
          .join(" | ");
      }
    }
    throw new ApiError(response.status, errorMessage);
  }

  return data as T;
}

export interface ListReportsParams {
  keyword?: string;
  status?: string;
  severity?: string;
  component?: string;
  page?: number;
  page_size?: number;
}

export const api = {
  /** Fetch all seeded demo personas for the top-bar role switcher */
  getDemoUsers: (): Promise<DemoUser[]> =>
    apiFetch<DemoUser[]>("/api/v1/reports/demo-users"),

  /** List reports (scoped automatically on the backend by the active role) */
  listReports: (params: ListReportsParams = {}): Promise<ReportListResponse> => {
    const search = new URLSearchParams();
    if (params.keyword && params.keyword.trim()) {
      search.set("keyword", params.keyword.trim());
    }
    if (params.status) search.set("status", params.status);
    if (params.severity) search.set("severity", params.severity);
    if (params.component && params.component.trim()) {
      search.set("component", params.component.trim());
    }
    search.set("page", String(params.page ?? 1));
    search.set("page_size", String(params.page_size ?? 10));

    return apiFetch<ReportListResponse>(`/api/v1/reports?${search.toString()}`);
  },

  /** Fetch a single report by numeric ID */
  getReport: (reportId: number | string): Promise<ReportRead> =>
    apiFetch<ReportRead>(`/api/v1/reports/${reportId}`),

  /** Submit a new vulnerability report (Researcher only, enforces 5 policy rules) */
  createReport: (payload: ReportCreatePayload): Promise<ReportRead> =>
    apiFetch<ReportRead>("/api/v1/reports", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  /** Update an existing vulnerability report (Researcher owner while status === "new") */
  updateReport: (
    reportId: number | string,
    payload: ReportUpdatePayload
  ): Promise<ReportRead> =>
    apiFetch<ReportRead>(`/api/v1/reports/${reportId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  /** Delete an existing vulnerability report (Researcher owner while status === "new") */
  deleteReport: (reportId: number | string): Promise<void> =>
    apiFetch<void>(`/api/v1/reports/${reportId}`, {
      method: "DELETE",
    }),

  /** Assign official final_severity (Analyst only — used in Phase 5) */
  assignSeverity: (
    reportId: number | string,
    payload: SeverityUpdatePayload
  ): Promise<ReportRead> =>
    apiFetch<ReportRead>(`/api/v1/reports/${reportId}/severity`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  /** Transition report status and record StatusHistory (Analyst/Admin — used in Phase 5) */
  changeStatus: (
    reportId: number | string,
    payload: StatusUpdatePayload
  ): Promise<ReportRead> =>
    apiFetch<ReportRead>(`/api/v1/reports/${reportId}/status`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  /** Fetch chronological status history timeline (used in Phase 5) */
  getReportHistory: (
    reportId: number | string
  ): Promise<StatusHistoryEntry[]> =>
    apiFetch<StatusHistoryEntry[]>(`/api/v1/reports/${reportId}/history`),

  /** Fetch role-filtered comments on a report (used in Phase 5) */
  listComments: (reportId: number | string): Promise<CommentItem[]> =>
    apiFetch<CommentItem[]>(`/api/v1/reports/${reportId}/comments`),

  /** Post a comment or internal analyst note (used in Phase 5) */
  createComment: (
    reportId: number | string,
    payload: CommentCreatePayload
  ): Promise<CommentItem> =>
    apiFetch<CommentItem>(`/api/v1/reports/${reportId}/comments`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};