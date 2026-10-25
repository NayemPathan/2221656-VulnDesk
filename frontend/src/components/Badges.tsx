/**
 * frontend/src/components/Badges.tsx
 * ----------------------------------
 * Reusable visual pills for ReportStatus, Severity, and UserRole.
 * Color-coding helps Security Analysts immediately spot Critical/High issues
 * and distinguish New vs Confirmed/Rejected reports during triage.
 */


import React from "react";
import { ReportStatus, Severity, UserRole } from "../types";


const STATUS_LABELS: Record<ReportStatus, string> = {
  new: "New",
  under_review: "Under Review",
  confirmed: "Confirmed",
  fixed: "Fixed",
  closed: "Closed",
  rejected: "Rejected",
  duplicate: "Duplicate",
};


const SEVERITY_LABELS: Record<Severity, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};


const ROLE_LABELS: Record<UserRole, string> = {
  researcher: "Researcher",
  analyst: "Analyst",
  admin: "Admin",
};


export const StatusBadge: React.FC<{ status: ReportStatus }> = ({ status }) => {
  const classMap: Record<ReportStatus, string> = {
    new: "badge status-new",
    under_review: "badge status-triaging",
    confirmed: "badge status-validated",
    duplicate: "badge status-duplicate",
    fixed: "badge status-informative",
    closed: "badge status-resolved",
    rejected: "badge status-rejected",
  };
  return (
    <span className={classMap[status] || "badge"}>
      {STATUS_LABELS[status] || status}
    </span>
  );
};


export const SeverityBadge: React.FC<{
  severity: Severity;
  labelPrefix?: string;
}> = ({ severity, labelPrefix }) => {
  const classMap: Record<Severity, string> = {
    low: "badge sev-low",
    medium: "badge sev-medium",
    high: "badge sev-high",
    critical: "badge sev-critical",
  };
  return (
    <span className={classMap[severity] || "badge"}>
      {labelPrefix ? `${labelPrefix}: ` : ""}
      {SEVERITY_LABELS[severity] || severity}
    </span>
  );
};


export const RoleBadge: React.FC<{ role: UserRole; isBanned?: boolean }> = ({
  role,
  isBanned,
}) => {
  if (isBanned) {
    return <span className="badge role-banned">Banned Researcher</span>;
  }
  const classMap: Record<UserRole, string> = {
    researcher: "badge role-researcher",
    analyst: "badge role-analyst",
    admin: "badge role-admin",
  };
  return (
    <span className={classMap[role] || "badge"}>
      {ROLE_LABELS[role] || role}
    </span>
  );
};
