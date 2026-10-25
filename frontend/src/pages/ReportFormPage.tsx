/**
 * frontend/src/pages/ReportFormPage.tsx
 * -------------------------------------
 * Implements the **Create** part of Frontend CRUD (`POST /api/v1/reports`,
 * `FR-07`, `FR-08`).
 *
 * Key academic features for the viva:
 * 1. Live character counters helping the researcher satisfy our 5-rule
 *    Submission Policy (`title` 5–120 chars, `description` 50–5,000 chars,
 *    `component` 1–100 chars, `steps_to_reproduce` 10–5,000 chars).
 * 2. Includes a 1-click "Auto-Fill Sample PoC" button for fast live demos, and
 *    surfaces backend HTTP 403 / 409 / 422 policy errors in a prominent banner.
 */


import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useDemoUser } from "../context/DemoUserContext";
import { Severity } from "../types";


const SEVERITY_OPTIONS: { value: Severity; label: string }[] = [
  { value: "low", label: "Low (10-day SLA)" },
  { value: "medium", label: "Medium (5-day SLA)" },
  { value: "high", label: "High (2-day SLA)" },
  { value: "critical", label: "Critical (1-day SLA)" },
];


export const ReportFormPage: React.FC = () => {
  const { currentUser } = useDemoUser();
  const navigate = useNavigate();


  const [title, setTitle] = useState<string>("");
  const [component, setComponent] = useState<string>("");
  const [proposedSeverity, setProposedSeverity] = useState<Severity>("high");
  const [description, setDescription] = useState<string>("");
  const [stepsToReproduce, setStepsToReproduce] = useState<string>("");


  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorStatus(null);
    setErrorMessage(null);


    try {
      const created = await api.createReport({
        title: title.trim(),
        component: component.trim(),
        proposed_severity: proposedSeverity,
        description: description.trim(),
        steps_to_reproduce: stepsToReproduce.trim(),
      });
      navigate(`/reports/${created.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorStatus(err.status);
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Unexpected network error while submitting report.");
      }
    } finally {
      setSubmitting(false);
    }
  };


  /**
   * Quick-fill helper so the student can test a valid submission or a banned-user
   * rejection in 1 click during the viva demonstration.
   */
  const fillSampleValidReport = () => {
    setTitle("Reflected XSS in Search Filter Query Parameter");
    setComponent("Storefront Web - Search");
    setProposedSeverity("medium");
    setDescription(
      "The product catalog search page echoes the 'q' query parameter directly into the DOM error banner without HTML entity encoding when no products match, allowing arbitrary JavaScript execution."
    );
    setStepsToReproduce(
      "1. Open /catalog?q=<svg/onload=alert(document.domain)>\n2. Observe that the script executes in the victim's browser session."
    );
    setErrorMessage(null);
    setErrorStatus(null);
  };


  return (
    <div className="page-container narrow-container">
      <div className="breadcrumb-bar">
        <Link to="/" className="breadcrumb-link">
          ← Back to Reports Queue
        </Link>
      </div>


      <div className="card form-card">
        <div className="form-card-header">
          <div>
            <h1 className="page-title">Submit Vulnerability Report</h1>
            <p className="page-subtitle">
              Submitting as <strong>{currentUser.name}</strong> (
              <code>{currentUser.email}</code>)
            </p>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={fillSampleValidReport}
          >
            Auto-Fill Sample PoC
          </button>
        </div>


        {currentUser.role !== "researcher" && (
          <div className="alert alert-warning">
            <strong>Role Notice:</strong> You are currently acting as{" "}
            <strong>{currentUser.role}</strong>. Only users with the{" "}
            <code>researcher</code> role can submit new vulnerability reports (
            <code>POST /api/v1/reports</code> will return HTTP 403 Forbidden).
          </div>
        )}


        {errorMessage && (
          <div className="alert alert-danger" role="alert">
            <strong>
              Submission Rejected
              {errorStatus ? ` (HTTP ${errorStatus})` : ""}:
            </strong>{" "}
            {errorMessage}
          </div>
        )}


        <form onSubmit={handleSubmit} className="vuln-form">
          <div className="form-group">
            <label htmlFor="report-title">
              Vulnerability Title <span className="req">*</span>
            </label>
            <input
              id="report-title"
              type="text"
              className="form-input"
              required
              placeholder="e.g. Stored XSS in Customer Support Ticket Subject"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <span className="field-hint">
              Characters: {title.trim().length} / 120 (Policy Rule i requires
              5–120 characters)
            </span>
          </div>


          <div className="form-row-2">
            <div className="form-group">
              <label htmlFor="report-component">
                Affected Component <span className="req">*</span>
              </label>
              <input
                id="report-component"
                type="text"
                className="form-input"
                required
                placeholder="e.g. Merchant Portal - Support Module"
                value={component}
                onChange={(e) => setComponent(e.target.value)}
              />
            </div>


            <div className="form-group">
              <label htmlFor="report-severity">
                Proposed Severity <span className="req">*</span>
              </label>
              <select
                id="report-severity"
                className="form-select"
                value={proposedSeverity}
                onChange={(e) =>
                  setProposedSeverity(e.target.value as Severity)
                }
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
            <label htmlFor="report-description">
              Vulnerability Description &amp; Impact{" "}
              <span className="req">*</span>
            </label>
            <textarea
              id="report-description"
              className="form-textarea"
              rows={4}
              required
              placeholder="Explain the root cause, vulnerable endpoint, parameters involved, and security impact (minimum 50 characters)..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
            <span className="field-hint">
              Characters: {description.trim().length} / 5000 (Policy Rule ii
              requires 50–5,000 characters)
            </span>
          </div>


          <div className="form-group">
            <label htmlFor="report-steps">
              Steps to Reproduce (PoC) <span className="req">*</span>
            </label>
            <textarea
              id="report-steps"
              className="form-textarea"
              rows={5}
              required
              placeholder={
                "1. Log into the application.\n2. Send request with payload...\n3. Observe the response..."
              }
              value={stepsToReproduce}
              onChange={(e) => setStepsToReproduce(e.target.value)}
            />
            <span className="field-hint">
              Characters: {stepsToReproduce.trim().length} / 5000 (minimum 10
              characters required)
            </span>
          </div>


          <div className="form-actions">
            <Link to="/" className="btn btn-secondary">
              Cancel
            </Link>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting}
            >
              {submitting ? "Submitting Report..." : "Submit Vulnerability Report"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
