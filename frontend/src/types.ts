/**
 * frontend/src/types.ts
 * ---------------------
 * Centralized TypeScript data contracts matching our FastAPI Pydantic schemas
 * (`backend/app/schemas/report.py`, `triage.py`, and `comment.py`).
 *
 * Keeping all interfaces in one file guarantees compile-time type safety across
 * API calls, React Context, and UI components.
 */

export type UserRole = "researcher" | "analyst" | "admin";

export type ReportStatus =
  | "new"
  | "under_review"
  | "confirmed"
  | "fixed"
  | "closed"
  | "rejected"
  | "duplicate";

export type Severity = "low" | "medium" | "high" | "critical";

export interface DemoUser {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_banned: boolean;
}

export interface ReportRead {
  id: number;
  title: string;
  description: string;
  component: string;
  steps_to_reproduce: string;
  proposed_severity: Severity;
  final_severity: Severity | null;
  status: ReportStatus;
  rejection_reason: string | null;
  reporter_id: number;
  duplicate_of_id: number | null;
  first_responder_id: number | null;
  first_response_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReportListResponse {
  items: ReportRead[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ReportCreatePayload {
  title: string;
  description: string;
  component: string;
  steps_to_reproduce: string;
  proposed_severity: Severity;
}

export interface ReportUpdatePayload {
  title: string;
  description: string;
  component: string;
  steps_to_reproduce: string;
  proposed_severity: Severity;
}

export interface SeverityUpdatePayload {
  final_severity: Severity;
}

export interface StatusUpdatePayload {
  status: ReportStatus;
  rejection_reason?: string | null;
  duplicate_of_id?: number | null;
}

export interface StatusHistoryEntry {
  id: number;
  report_id: number;
  changed_by: number;
  changed_by_name: string | null;
  from_status: ReportStatus;
  to_status: ReportStatus;
  changed_at: string;
}

export interface CommentItem {
  id: number;
  report_id: number;
  author_id: number;
  author_name: string | null;
  author_role: UserRole | null;
  body: string;
  is_internal: boolean;
  created_at: string;
}

export interface CommentCreatePayload {
  body: string;
  is_internal: boolean;
}