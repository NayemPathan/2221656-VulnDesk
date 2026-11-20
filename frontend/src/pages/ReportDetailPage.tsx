import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { RoleBadge, SeverityBadge, StatusBadge } from "../components/Badges";
import { useAuth } from "../context/AuthContext";
import {useToast} from "../context/ToastContext";

import {
  CommentItem,
  ReportRead,
  ReportStatus,
  Severity,
  StatusHistoryEntry,
} from "../types";

const SEVERITY_OPTIONS: { value: Severity; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

const ANALYST_NEXT_STATUSES: Record<
  ReportStatus,
  { value: ReportStatus; label: string }[]
> = {
  new: [
    { value: "under_review", label: "Under Review (Start Triage)" },
    { value: "rejected", label: "Rejected (Requires Reason)" },
    { value: "duplicate", label: "Duplicate (Requires Original ID)" },
  ],
  under_review: [
    { value: "confirmed", label: "Confirmed (Requires Final Severity)" },
    { value: "rejected", label: "Rejected (Requires Reason)" },
    { value: "duplicate", label: "Duplicate (Requires Original ID)" },
  ],
  confirmed: [{ value: "fixed", label: "Fixed (Patch Deployed)" }],
  fixed: [{ value: "closed", label: "Closed (Verified & Complete)" }],
  closed: [],
  rejected: [],
  duplicate: [],
};

const END_STATES: ReportStatus[] = ["closed", "rejected", "duplicate"];

export const ReportDetailPage: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const { currentUser } = useAuth();
  const {showToast, confirmAction} = useToast();
  const navigate = useNavigate();

  const [report, setReport] = useState<ReportRead | null>(null);
  const [history, setHistory] = useState<StatusHistoryEntry[]>([]);
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [editTitle, setEditTitle] = useState<string>("");
  const [editComponent, setEditComponent] = useState<string>("");
  const [editSeverity, setEditSeverity] = useState<Severity>("medium");
  const [editDescription, setEditDescription] = useState<string>("");
  const [editSteps, setEditSteps] = useState<string>("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [saving, setSaving] = useState<boolean>(false);
  const [deleting, setDeleting] = useState<boolean>(false);

  const [selectedFinalSeverity, setSelectedFinalSeverity] =
    useState<Severity>("high");
  const [savingSeverity, setSavingSeverity] = useState<boolean>(false);
  const [targetStatus, setTargetStatus] =
    useState<ReportStatus>("under_review");
  const [rejectionReason, setRejectionReason] = useState<string>("");
  const [duplicateOfId, setDuplicateOfId] = useState<string>("");
  const [savingStatus, setSavingStatus] = useState<boolean>(false);

  const [commentBody, setCommentBody] = useState<string>("");
  const [isInternalNote, setIsInternalNote] = useState<boolean>(false);
  const [postingComment, setPostingComment] = useState<boolean>(false);
  const [commentError, setCommentError] = useState<string | null>(null);

  const loadAllReportData = useCallback(async () => {
    if (!reportId || !currentUser) return;
    setLoading(true);
    setError(null);
    setActionError(null);
    setActionSuccess(null);
    setCommentError(null);

    try {
      const [reportData, historyData, commentsData] = await Promise.all([
        api.getReport(reportId),
        api.getReportHistory(reportId),
        api.listComments(reportId),
      ]);

      setReport(reportData);
      setHistory(historyData);
      setComments(commentsData);

      setEditTitle(reportData.title);
      setEditComponent(reportData.component);
      setEditSeverity(reportData.proposed_severity);
      setEditDescription(reportData.description);
      setEditSteps(reportData.steps_to_reproduce);
      setIsEditing(false);

      setSelectedFinalSeverity(
        reportData.final_severity || reportData.proposed_severity
      );

      const nextOptions = ANALYST_NEXT_STATUSES[reportData.status] || [];
      if (nextOptions.length > 0) {
        setTargetStatus(nextOptions[0].value);
      } else {
        setTargetStatus("under_review");
      }
      setRejectionReason(reportData.rejection_reason || "");
      setDuplicateOfId(
        reportData.duplicate_of_id ? String(reportData.duplicate_of_id) : ""
      );

      if (currentUser.role !== "analyst") {
        setIsInternalNote(false);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`HTTP ${err.status}: ${err.message}`);
      } else {
        setError("Failed to load report details.");
      }
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, [reportId, currentUser]);

  useEffect(() => {
    loadAllReportData();
  }, [loadAllReportData]);

  if (!currentUser) return null;

  const isOwner =
    report &&
    currentUser.role === "researcher" &&
    report.reporter_id === currentUser.id;
  const canMutateAsResearcher = Boolean(isOwner && report?.status === "new");

  const handleSaveUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!report) return;
    setSaving(true);
    setActionError(null);
    setActionSuccess(null);

    try {
      const updated = await api.updateReport(report.id, {
        title: editTitle.trim(),
        component: editComponent.trim(),
        proposed_severity: editSeverity,
        description: editDescription.trim(),
        steps_to_reproduce: editSteps.trim(),
      });
      setReport(updated);
      setIsEditing(false);
      setActionSuccess("Report details updated.");
    } catch (err) {
      if (err instanceof ApiError) {
        setActionError(`HTTP ${err.status}: ${err.message}`);
      } else {
        setActionError("Failed to update report.");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteReport = async () => {
    if (!report) return;
    const handleDeleteReport = () => {
  if (!report) return;
    confirmAction({
      title: `Delete Report #${report.id}?`,
      message: `Permanently withdraw "${report.title}"? This is only allowed while status is New.`,
      confirmLabel: "Delete Report",
      onConfirm: async () => {
        setDeleting(true);
        try {
          await api.deleteReport(report.id);
          showToast("Report deleted.", "success");
          navigate("/");
        } catch (err) {
          setActionError(err instanceof ApiError ? `HTTP ${err.status}: ${err.message}` : "Failed to delete report.");
          setDeleting(false);
        }
      },
    });
  };

    setDeleting(true);
    setActionError(null);
    try {
      await api.deleteReport(report.id);
      navigate("/");
    } catch (err) {
      if (err instanceof ApiError) {
        setActionError(`HTTP ${err.status}: ${err.message}`);
      } else {
        setActionError("Failed to delete report.");
      }
      setDeleting(false);
    }
  };

  const handleAssignSeverity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!report) return;
    setSavingSeverity(true);
    setActionError(null);
    setActionSuccess(null);

    try {
      const updated = await api.assignSeverity(report.id, {
        final_severity: selectedFinalSeverity,
      });
      setReport(updated);
      setActionSuccess(
        `Assigned official final severity: ${selectedFinalSeverity.toUpperCase()}.`
      );
    } catch (err) {
      if (err instanceof ApiError) {
        setActionError(`HTTP ${err.status}: ${err.message}`);
      } else {
        setActionError("Failed to assign final severity.");
      }
    } finally {
      setSavingSeverity(false);
    }
  };

  const handleStatusTransition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!report) return;
    setSavingStatus(true);
    setActionError(null);
    setActionSuccess(null);

    const parsedDuplicateId =
      duplicateOfId.trim() === ""
        ? null
        : Number.parseInt(duplicateOfId.trim(), 10);

    try {
      const updated = await api.changeStatus(report.id, {
        status: targetStatus,
        rejection_reason:
          targetStatus === "rejected" ? rejectionReason.trim() || null : null,
        duplicate_of_id:
          targetStatus === "duplicate" && !Number.isNaN(parsedDuplicateId as number)
            ? parsedDuplicateId
            : null,
      });
      const updatedHistory = await api.getReportHistory(report.id);
      setReport(updated);
      setHistory(updatedHistory);

      const nextOptions = ANALYST_NEXT_STATUSES[updated.status] || [];
      if (nextOptions.length > 0) {
        setTargetStatus(nextOptions[0].value);
      }
      setActionSuccess(
        `Status transitioned to "${updated.status}" and recorded in Status History.`
      );
    } catch (err) {
      if (err instanceof ApiError) {
        setActionError(`HTTP ${err.status}: ${err.message}`);
      } else {
        setActionError("Failed to transition report status.");
      }
    } finally {
      setSavingStatus(false);
    }
  };

  const handlePostComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!report || !commentBody.trim()) return;
    setPostingComment(true);
    setCommentError(null);

    try {
      const created = await api.createComment(report.id, {
        body: commentBody.trim(),
        is_internal: currentUser.role === "analyst" ? isInternalNote : false,
      });
      setComments((prev) => [...prev, created]);
      setCommentBody("");
      setIsInternalNote(false);
    } catch (err) {
      if (err instanceof ApiError) {
        setCommentError(`HTTP ${err.status}: ${err.message}`);
      } else {
        setCommentError("Failed to post comment.");
      }
    } finally {
      setPostingComment(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="card loading-state">Loading report details...</div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="page-container">
        <div className="breadcrumb-bar">
          <Link to="/" className="breadcrumb-link">
            ← Back to Reports Queue
          </Link>
        </div>
        <div className="alert alert-danger" role="alert">
          <strong>Access Denied or Not Found:</strong>{" "}
          {error || "Report could not be loaded."}
          <p className="mt-2">
            Note: In VulnDesk, Ownership Isolation (`FR-09`, `AC-04`) returns{" "}
            <code>404 Not Found</code> if a Researcher requests another
            Researcher&apos;s report so report IDs cannot be enumerated.
          </p>
        </div>
      </div>
    );
  }

  const analystAllowedTargets = ANALYST_NEXT_STATUSES[report.status] || [];
  const isEndState = END_STATES.includes(report.status);

  return (
    <div className="page-container">
      <div className="breadcrumb-bar">
        <Link to="/" className="breadcrumb-link">
          ← Back to Reports Queue
        </Link>
        <span className="report-uuid-label">
          Report ID: <code>#{report.id}</code> • Reporter ID:{" "}
          <code>#{report.reporter_id}</code>
          {report.sla_due_at && (
            <>
              {" "}
              • SLA Due:{" "}
              <strong>{new Date(report.sla_due_at).toLocaleString()}</strong>
            </>
          )}
          {report.first_response_at && (
            <>
              {" "}
              • First Triage Response:{" "}
              <strong>
                {new Date(report.first_response_at).toLocaleString()}
              </strong>
            </>
          )}
        </span>
      </div>

      {report.status === "rejected" && report.rejection_reason && (
        <div className="alert alert-danger" role="alert">
          <strong>Report Rejected by Security Analyst:</strong>{" "}
          {report.rejection_reason}
        </div>
      )}

      {report.status === "duplicate" && report.duplicate_of_id && (
        <div className="alert alert-warning">
          <strong>Marked as Duplicate:</strong> This report is a duplicate of
          canonical report{" "}
          <Link to={`/reports/${report.duplicate_of_id}`}>
            <strong>Report #{report.duplicate_of_id}</strong>
          </Link>
          .
        </div>
      )}

      {actionError && (
        <div className="alert alert-danger" role="alert">
          <strong>Operation Rejected:</strong> {actionError}
        </div>
      )}

      {actionSuccess && (
        <div className="alert alert-success" role="status">
          <strong>Success:</strong> {actionSuccess}
        </div>
      )}

      <div className="card detail-card">
        <div className="detail-header">
          <div>
            <div className="detail-badges">
              <StatusBadge status={report.status} />
              <SeverityBadge
                severity={report.proposed_severity}
                labelPrefix="Proposed"
              />
              {report.final_severity && (
                <SeverityBadge
                  severity={report.final_severity}
                  labelPrefix="Final"
                />
              )}
              {report.is_overdue && (
                <span className="overdue-badge">⏰ OVERDUE SLA</span>
              )}
              <code className="component-tag">{report.component}</code>
            </div>
            <h1 className="detail-title">
              #{report.id} — {report.title}
            </h1>
            <p className="detail-meta">
              Submitted on{" "}
              <strong>{new Date(report.created_at).toLocaleString()}</strong> •
              Last updated{" "}
              <strong>{new Date(report.updated_at).toLocaleString()}</strong>
            </p>
          </div>

          {isOwner && (
            <div className="owner-actions">
              {canMutateAsResearcher ? (
                <>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setIsEditing((prev) => !prev)}
                  >
                    {isEditing ? "Cancel Editing" : "✏️ Edit Report"}
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger"
                    disabled={deleting}
                    onClick={handleDeleteReport}
                  >
                    {deleting ? "Deleting..." : "🗑️ Delete Report"}
                  </button>
                </>
              ) : (
                <span className="lock-notice" title="FR-10a / FR-10b Lock">
                  🔒 Locked for Researcher edits (`status = {report.status}`)
                </span>
              )}
            </div>
          )}
        </div>

        {isEditing ? (
          <form onSubmit={handleSaveUpdate} className="vuln-form edit-form-box">
            <h3 className="section-heading">
              Edit Vulnerability Report (Allowed while Status is <code>new</code>)
            </h3>

            <div className="form-group">
              <label htmlFor="edit-title">Vulnerability Title (5–120 chars)</label>
              <input
                id="edit-title"
                type="text"
                className="form-input"
                required
                minLength={5}
                maxLength={120}
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
              />
            </div>

            <div className="form-row-2">
              <div className="form-group">
                <label htmlFor="edit-component">Affected Component</label>
                <input
                  id="edit-component"
                  type="text"
                  className="form-input"
                  required
                  value={editComponent}
                  onChange={(e) => setEditComponent(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label htmlFor="edit-severity">Proposed Severity</label>
                <select
                  id="edit-severity"
                  className="form-select"
                  value={editSeverity}
                  onChange={(e) => setEditSeverity(e.target.value as Severity)}
                >
                  {SEVERITY_OPTIONS.map((sev) => (
                    <option key={sev.value} value={sev.value}>
                      {sev.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="edit-description">
                Vulnerability Description &amp; Impact (50–5,000 chars)
              </label>
              <textarea
                id="edit-description"
                className="form-textarea"
                rows={4}
                required
                minLength={50}
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label htmlFor="edit-steps">Steps to Reproduce (PoC)</label>
              <textarea
                id="edit-steps"
                className="form-textarea"
                rows={5}
                required
                minLength={10}
                value={editSteps}
                onChange={(e) => setEditSteps(e.target.value)}
              />
            </div>

            <div className="form-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setIsEditing(false)}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={saving}
              >
                {saving ? "Saving Changes..." : "Save Report Changes"}
              </button>
            </div>
          </form>
        ) : (
          <div className="detail-sections">
            <section className="detail-section">
              <h3 className="section-heading">
                Vulnerability Description &amp; Impact
              </h3>
              <pre className="detail-pre">{report.description}</pre>
            </section>

            <section className="detail-section">
              <div className="section-header-inline">
                <h3 className="section-heading">Steps to Reproduce (Proof of Concept)</h3>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => {
                    navigator.clipboard.writeText(report.steps_to_reproduce);
                    showToast("PoC steps copied to clipboard!", "success");
                  }}
                >
                  📋 Copy PoC
                </button>
              </div>
              <pre className="detail-pre">{report.steps_to_reproduce}</pre>
            </section>

          </div>
        )}
      </div>

      {(currentUser.role === "analyst" || currentUser.role === "admin") && (
        <div className="card triage-card mt-4">
          <div className="triage-card-header">
            <div>
              <h2 className="section-title">
                🛡️ Security Triage &amp; Workflow Controls
              </h2>
              <p className="page-subtitle">
                Acting as <strong>{currentUser.name}</strong> (
                <code>{currentUser.role}</code>). Every status transition is
                atomically logged in the append-only Status History below.
              </p>
            </div>
            <RoleBadge role={currentUser.role} />
          </div>

          {currentUser.role === "analyst" && (
            <div className="triage-grid">
              <form onSubmit={handleAssignSeverity} className="triage-box">
                <h3 className="section-heading">
                  1. Assign Official Final Severity (`FR-12`)
                </h3>
                <p className="field-hint">
                  Current Final Severity:{" "}
                  <strong>
                    {report.final_severity
                      ? report.final_severity.toUpperCase()
                      : "Not assigned yet (Required before Confirmed)"}
                  </strong>
                </p>
                <div className="form-group mt-2">
                  <label htmlFor="triage-final-severity">Final Severity</label>
                  <select
                    id="triage-final-severity"
                    className="form-select"
                    value={selectedFinalSeverity}
                    onChange={(e) =>
                      setSelectedFinalSeverity(e.target.value as Severity)
                    }
                  >
                    {SEVERITY_OPTIONS.map((sev) => (
                      <option key={sev.value} value={sev.value}>
                        {sev.label}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  type="submit"
                  className="btn btn-primary btn-sm mt-2"
                  disabled={savingSeverity}
                >
                  {savingSeverity ? "Saving..." : "Assign Final Severity"}
                </button>
              </form>

              <form onSubmit={handleStatusTransition} className="triage-box">
                <h3 className="section-heading">
                  2. Transition Report Status (`FR-13`, `FR-14`)
                </h3>
                {analystAllowedTargets.length === 0 ? (
                  <p className="field-hint">
                    This report is in an end state (
                    <code>{report.status}</code>). Only an Administrator can
                    reopen end-state reports back to <code>under_review</code>{" "}
                    (`FR-16`).
                  </p>
                ) : (
                  <>
                    <div className="form-group">
                      <label htmlFor="triage-status-select">
                        Allowed Next Status (from <code>{report.status}</code>)
                      </label>
                      <select
                        id="triage-status-select"
                        className="form-select"
                        value={targetStatus}
                        onChange={(e) =>
                          setTargetStatus(e.target.value as ReportStatus)
                        }
                      >
                        {analystAllowedTargets.map((st) => (
                          <option key={st.value} value={st.value}>
                            {st.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    {targetStatus === "rejected" && (
                      <div className="form-group mt-2">
                        <label htmlFor="triage-rejection-reason">
                          Rejection Reason (`FR-14` / `AC-09`){" "}
                          <span className="req">*</span>
                        </label>
                        <textarea
                          id="triage-rejection-reason"
                          className="form-textarea"
                          rows={2}
                          placeholder="Explain why this report is invalid so the researcher can see feedback..."
                          value={rejectionReason}
                          onChange={(e) => setRejectionReason(e.target.value)}
                        />
                      </div>
                    )}

                    {targetStatus === "duplicate" && (
                      <div className="form-group mt-2">
                        <label htmlFor="triage-duplicate-id">
                          Original Report ID (`duplicate_of_id`){" "}
                          <span className="req">*</span>
                        </label>
                        <input
                          id="triage-duplicate-id"
                          type="number"
                          min={1}
                          className="form-input"
                          placeholder="e.g. 2"
                          value={duplicateOfId}
                          onChange={(e) => setDuplicateOfId(e.target.value)}
                        />
                      </div>
                    )}

                    <button
                      type="submit"
                      className="btn btn-primary btn-sm mt-2"
                      disabled={savingStatus}
                    >
                      {savingStatus
                        ? "Transitioning..."
                        : `Transition to ${targetStatus}`}
                    </button>
                  </>
                )}
              </form>
            </div>
          )}

          {currentUser.role === "admin" && (
            <div className="triage-box">
              <h3 className="section-heading">
                Administrator End-State Reopen Control (`FR-16`)
              </h3>
              {isEndState ? (
                <div className="admin-reopen-bar">
                  <p className="field-hint">
                    This report is currently in end state{" "}
                    <code>{report.status}</code>. As an Administrator, you can
                    reopen it back to <code>under_review</code>.
                  </p>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={savingStatus}
                    onClick={async () => {
                      setSavingStatus(true);
                      setActionError(null);
                      setActionSuccess(null);
                      try {
                        const updated = await api.changeStatus(report.id, {
                          status: "under_review",
                        });
                        const updatedHistory = await api.getReportHistory(
                          report.id
                        );
                        setReport(updated);
                        setHistory(updatedHistory);
                        setActionSuccess(
                          "End-state report reopened to 'under_review'."
                        );
                      } catch (err) {
                        if (err instanceof ApiError) {
                          setActionError(`HTTP ${err.status}: ${err.message}`);
                        }
                      } finally {
                        setSavingStatus(false);
                      }
                    }}
                  >
                    {savingStatus
                      ? "Reopening..."
                      : "🔓 Reopen Report to Under Review"}
                  </button>
                </div>
              ) : (
                <p className="field-hint">
                  This report is currently active (
                  <code>{report.status}</code>). Administrators only reopen
                  reports that have reached <code>closed</code>,{" "}
                  <code>rejected</code>, or <code>duplicate</code> (`FR-16`).
                </p>
              )}
            </div>
          )}
        </div>
      )}

      <div className="bottom-grid mt-4">
        <section className="card section-card">
          <h2 className="section-title">
            📜 Immutable Status History (`FR-15`)
          </h2>
          <p className="field-hint mb-3">
            Append-only audit trail recorded atomically in the same database
            transaction as each status change (`NFR-08`).
          </p>

          {history.length === 0 ? (
            <div className="empty-inline">
              No status transitions yet — report is still in its initial{" "}
              <code>new</code> state.
            </div>
          ) : (
            <ol className="history-timeline">
              {history.map((item) => (
                <li key={item.id} className="timeline-item">
                  <div className="timeline-transition">
                    <StatusBadge status={item.from_status} />
                    <span className="timeline-arrow">→</span>
                    <StatusBadge status={item.to_status} />
                  </div>
                  <div className="timeline-meta">
                    By{" "}
                    <strong>
                      {item.changed_by_name || `User #${item.changed_by}`}
                    </strong>{" "}
                    on {new Date(item.changed_at).toLocaleString()}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="card section-card">
          <h2 className="section-title">
            💬 Discussion &amp; Triage Notes (`FR-18`–`FR-20`)
          </h2>
          <p className="field-hint mb-3">
            {currentUser.role === "researcher"
              ? "Viewing as Researcher: Analyst-only internal notes (is_internal=true) are automatically filtered out by the backend API (AC-10)."
              : "Viewing as Analyst/Admin: Both public comments and amber-highlighted internal analyst notes are visible."}
          </p>

          {comments.length === 0 ? (
            <div className="empty-inline">
              No comments posted on this report yet.
            </div>
          ) : (
            <div className="comments-list">
              {comments.map((c) => (
                <div
                  key={c.id}
                  className={
                    c.is_internal
                      ? "comment-item comment-internal"
                      : "comment-item"
                  }
                >
                  <div className="comment-header">
                    <div className="comment-author">
                      <strong>{c.author_name || `User #${c.author_id}`}</strong>
                      {c.author_role && <RoleBadge role={c.author_role} />}
                      {c.is_internal && (
                        <span className="internal-pill">
                          🔒 Internal Analyst Note
                        </span>
                      )}
                    </div>
                    <span className="comment-date">
                      {new Date(c.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="comment-body">{c.body}</p>
                </div>
              ))}
            </div>
          )}

          {(currentUser.role === "researcher" ||
            currentUser.role === "analyst") && (
            <form onSubmit={handlePostComment} className="comment-form mt-3">
              {commentError && (
                <div className="alert alert-danger" role="alert">
                  {commentError}
                </div>
              )}

              <div className="form-group">
                <label htmlFor="new-comment-body">
                  Add {isInternalNote ? "Internal Analyst Note" : "Public Comment"}
                </label>
                <textarea
                  id="new-comment-body"
                  className="form-textarea"
                  rows={3}
                  required
                  maxLength={2000}
                  placeholder={
                    isInternalNote
                      ? "Write a private triage note visible ONLY to Security Analysts and Admins..."
                      : "Write a comment visible to the reporting Researcher and Security Analysts..."
                  }
                  value={commentBody}
                  onChange={(e) => setCommentBody(e.target.value)}
                />
              </div>

              <div className="comment-form-footer">
                {currentUser.role === "analyst" ? (
                  <label className="internal-checkbox-label">
                    <input
                      type="checkbox"
                      checked={isInternalNote}
                      onChange={(e) => setIsInternalNote(e.target.checked)}
                    />
                    <span>
                      Mark as <strong>Internal Analyst Note</strong> (hidden
                      from Researcher — <code>AC-10</code>)
                    </span>
                  </label>
                ) : (
                  <span className="field-hint">
                    Posting as Researcher (public comment)
                  </span>
                )}

                <button
                  type="submit"
                  className="btn btn-primary btn-sm"
                  disabled={postingComment || !commentBody.trim()}
                >
                  {postingComment
                    ? "Posting..."
                    : isInternalNote
                    ? "Post Internal Note"
                    : "Post Comment"}
                </button>
              </div>
            </form>
          )}
        </section>
      </div>
    </div>
  );
};