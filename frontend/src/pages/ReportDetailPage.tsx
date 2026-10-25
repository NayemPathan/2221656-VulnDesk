/**
 * frontend/src/pages/ReportDetailPage.tsx
 * ---------------------------------------
 * Implements:
 * 1. **Read (Single) (`GET /api/v1/reports/{id}`, `FR-09`)**: Displays full
 *    vulnerability report metadata, technical description, reproduction steps,
 *    and the visible `rejection_reason` alert banner whenever a report has been
 *    `rejected` (`FR-14`, `AC-09`).
 * 2. **Update (`PUT /api/v1/reports/{id}`, `FR-10a`, `AC-05`)**: Allows the
 *    owning Researcher to edit their report inline ONLY while `status === "new"`.
 * 3. **Delete (`DELETE /api/v1/reports/{id}`, `FR-10b`, `AC-06`, `AC-07`)**:
 *    Allows the owning Researcher to withdraw/delete their report ONLY while
 *    `status === "new"`.
 *
 * Note: Phase 5 will enrich this page with the Analyst Triage Panel,
 * Status History Timeline, and Role-Filtered Comments Thread.
 */


import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { SeverityBadge, StatusBadge } from "../components/Badges";
import { useDemoUser } from "../context/DemoUserContext";
import { ReportRead, Severity } from "../types";


const SEVERITY_OPTIONS: { value: Severity; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];


export const ReportDetailPage: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const { currentUser } = useDemoUser();
  const navigate = useNavigate();


  const [report, setReport] = useState<ReportRead | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);


  // Inline Edit Mode state (FR-10a)
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [editTitle, setEditTitle] = useState<string>("");
  const [editComponent, setEditComponent] = useState<string>("");
  const [editSeverity, setEditSeverity] = useState<Severity>("medium");
  const [editDescription, setEditDescription] = useState<string>("");
  const [editSteps, setEditSteps] = useState<string>("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [saving, setSaving] = useState<boolean>(false);
  const [deleting, setDeleting] = useState<boolean>(false);


  const loadReport = useCallback(async () => {
    if (!reportId) return;
    setLoading(true);
    setError(null);
    setActionError(null);
    try {
      const data = await api.getReport(reportId);
      setReport(data);
      // Pre-populate edit form fields
      setEditTitle(data.title);
      setEditComponent(data.component);
      setEditSeverity(data.proposed_severity);
      setEditDescription(data.description);
      setEditSteps(data.steps_to_reproduce);
      setIsEditing(false);
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
  }, [reportId, currentUser.email]);


  useEffect(() => {
    loadReport();
  }, [loadReport]);


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
    const confirmed = window.confirm(
      `Are you sure you want to permanently withdraw and delete Report #${report.id} ("${report.title}")? This action is only allowed while status is New.`
    );
    if (!confirmed) return;


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


  return (
    <div className="page-container">
      <div className="breadcrumb-bar">
        <Link to="/" className="breadcrumb-link">
          ← Back to Reports Queue
        </Link>
        <span className="report-uuid-label">
          Report ID: <code>#{report.id}</code> (Reporter ID:{" "}
          <code>#{report.reporter_id}</code>)
        </span>
      </div>


      {/* Rejection Feedback Banner (FR-08 / FR-14 / AC-09) */}
      {report.status === "rejected" && report.rejection_reason && (
        <div className="alert alert-danger" role="alert">
          <strong>Report Rejected by Security Analyst:</strong>{" "}
          {report.rejection_reason}
        </div>
      )}


      {/* Duplicate Reference Banner */}
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
          <strong>Operation Failed:</strong> {actionError}
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


          {/* Researcher Owner CRUD Controls (FR-10a & FR-10b) */}
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
              <h3 className="section-heading">
                Steps to Reproduce (Proof of Concept)
              </h3>
              <pre className="detail-pre">{report.steps_to_reproduce}</pre>
            </section>
          </div>
        )}
      </div>
    </div>
  );
};
