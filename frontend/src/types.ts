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

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_banned: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface AdminUser {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  ban_reason?: string | null;
  is_banned: boolean;
  is_deleted: boolean;
  failed_login_attempts: number;
  locked_until: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminUserCreatePayload {
  name: string;
  email: string;
  password: string;
  role: UserRole;
}

export interface DashboardSummary {
  role: UserRole;
  total_reports: number;
  open_reports: number;
  overdue_reports: number;
  by_status: Record<string, number>;
  by_severity: Record<string, number>;
  avg_first_response_hours: number | null;
  total_users: number | null;
  banned_users: number | null;
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
  group_id?: number | null;
  duplicate_of_id: number | null;
  first_responder_id: number | null;
  first_response_at: string | null;
  created_at: string;
  updated_at: string;
  sla_due_at?: string;
  is_overdue?: boolean;
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
  group_id?: number | null;
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
export interface SessionItem {
  id: number;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  expires_at: string;
}

export interface GroupMember {
  user_id: number;
  email: string;
  name: string;
  can_create: boolean;
  can_edit: boolean;
  can_assign: boolean;
  added_at: string;
}

export interface GroupItem {
  id: number;
  name: string;
  description: string | null;
  owner_id: number;
  owner_email: string;
  created_at: string;
  members: GroupMember[];
}

export interface AdminOverview {
  total_users: number;
  banned_users: number;
  total_reports: number;
  total_groups: number;
  new_users_7d: number;
  new_reports_7d: number;
}

export interface AuditLogItem {
  id: number;
  user_id: number | null;
  actor_email: string;
  action: string;
  target_type: string | null;
  target_id: number | null;
  details: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface SecurityViewData {
  failed_by_ip: { ip: string; count: number }[];
  failed_by_account: { email: string; count: number }[];
  recent_failures: AuditLogItem[];
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
