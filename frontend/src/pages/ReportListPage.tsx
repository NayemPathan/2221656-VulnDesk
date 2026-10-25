/**
 * frontend/src/pages/ReportListPage.tsx
 * -------------------------------------
 * Implements the **Read (List)** part of Frontend CRUD (`FR-09`, `FR-11`):
 * - Automatically re-fetches whenever `currentUser.email` changes in the
 *   top-bar Demo Persona Switcher, demonstrating Ownership Isolation live:
 *   - Alice (`alice@vulndesk.local`) sees only Alice's 3 reports (`#1`, `#2`, `#3`).
 *   - Bob (`bob@vulndesk.local`) sees only Bob's 1 report (`#4`).
 *   - Charlie (`charlie@vulndesk.local`) and Admin (`admin@vulndesk.local`) see all 4 global reports.
 * - Provides keyword search (`keyword`), status filter (`status`), severity filter
 *   (`severity`), and component filter (`component`) mapped directly to
 *   `GET /api/v1/reports` query parameters.
 */


import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { SeverityBadge, StatusBadge } from "../components/Badges";
import { useDemoUser } from "../context/DemoUserContext";
import { ReportRead, ReportStatus, Severity } from "../types";


const STATUS_OPTIONS: { value: ReportStatus; label: string }[] = [
  { value: "new", label: "New" },
  { value: "under_review", label: "Under Review" },
  { value: "confirmed", label: "Confirmed" },
  { value: "fixed", label: "Fixed" },
  { value: "closed", label: "Closed" },
  { value: "rejected", label: "Rejected" },
  { value: "duplicate", label: "Duplicate" },
];


const SEVERITY_OPTIONS: { value: Severity; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];


export const ReportListPage: React.FC = () => {
  const { currentUser } = useDemoUser();


  const [reports, setReports] = useState<ReportRead[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [pageSize] = useState<number>(10);


  // Filter states matching backend/app/routers/reports.py query params
  const [keyword, setKeyword] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [componentFilter, setComponentFilter] = useState<string>("");


  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);


  const fetchReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listReports({
        keyword,
        status: statusFilter,
        severity: severityFilter,
        component: componentFilter,
        page,
        page_size: pageSize,
      });
      setReports(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to load vulnerability reports from the backend API.");
      }
    } finally {
      setLoading(false);
    }
  }, [
    currentUser.email,
    keyword,
    statusFilter,
    severityFilter,
    componentFilter,
    page,
    pageSize,
  ]);


  useEffect(() => {
    fetchReports();
  }, [fetchReports]);


  const handleResetFilters = () => {
    setKeyword("");
    setStatusFilter("");
    setSeverityFilter("");
    setComponentFilter("");
    setPage(1);
  };


  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">
            {currentUser.role === "researcher"
              ? "My Submitted Vulnerability Reports"
              : "Global Vulnerability Triage Queue"}
          </h1>
          <p className="page-subtitle">
            Viewing as <strong>{currentUser.name}</strong> (
            <code>{currentUser.email}</code>).{" "}
            {currentUser.role === "researcher"
              ? "Ownership isolation (FR-09) scopes this list strictly to reports you submitted."
              : "Analyst/Admin privileges grant read access to all platform submissions."}
          </p>
        </div>


        {currentUser.role === "researcher" && (
          <Link to="/reports/new" className="btn btn-primary">
            + Submit New Report
          </Link>
        )}
      </div>


      {currentUser.is_banned && (
        <div className="alert alert-warning">
          <strong>Account Banned (`FR-08` Rule iv):</strong> This demo
          researcher account (<code>{currentUser.email}</code>) is flagged with{" "}
          <code>is_banned = true</code>. Try clicking{" "}
          <Link to="/reports/new">Submit New Report</Link> to verify the backend
          409 Conflict policy enforcement.
        </div>
      )}


      {/* Search & Filter Bar (FR-11) */}
      <section className="card filter-card">
        <div className="filter-grid">
          <div className="form-group">
            <label htmlFor="filter-keyword">Title Keyword (`keyword`)</label>
            <input
              id="filter-keyword"
              type="text"
              className="form-input"
              placeholder="Search report title (e.g. XSS, IDOR)..."
              value={keyword}
              onChange={(e) => {
                setKeyword(e.target.value);
                setPage(1);
              }}
            />
          </div>


          <div className="form-group">
            <label htmlFor="filter-status">Lifecycle Status (`status`)</label>
            <select
              id="filter-status"
              className="form-select"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Statuses</option>
              {STATUS_OPTIONS.map((st) => (
                <option key={st.value} value={st.value}>
                  {st.label}
                </option>
              ))}
            </select>
          </div>


          <div className="form-group">
            <label htmlFor="filter-severity">Severity Level (`severity`)</label>
            <select
              id="filter-severity"
              className="form-select"
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Severities</option>
              {SEVERITY_OPTIONS.map((sev) => (
                <option key={sev.value} value={sev.value}>
                  {sev.label}
                </option>
              ))}
            </select>
          </div>


          <div className="form-group">
            <label htmlFor="filter-component">
              Affected Component (`component`)
            </label>
            <input
              id="filter-component"
              type="text"
              className="form-input"
              placeholder="e.g. Billing, Merchant Portal"
              value={componentFilter}
              onChange={(e) => {
                setComponentFilter(e.target.value);
                setPage(1);
              }}
            />
          </div>
        </div>


        <div className="filter-actions">
          <span className="results-counter">
            Showing <strong>{reports.length}</strong> of{" "}
            <strong>{total}</strong> matching report(s)
          </span>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handleResetFilters}
          >
            Reset Filters
          </button>
        </div>
      </section>


      {error && (
        <div className="alert alert-danger" role="alert">
          <strong>Error loading reports:</strong> {error}
        </div>
      )}


      {loading ? (
        <div className="card loading-state">Loading vulnerability reports...</div>
      ) : reports.length === 0 ? (
        <div className="card empty-state">
          <h3>No vulnerability reports found</h3>
          <p>
            No reports match your current persona scope or filter criteria.
          </p>
          {currentUser.role === "researcher" && !currentUser.is_banned && (
            <Link to="/reports/new" className="btn btn-primary">
              Submit Your First Report
            </Link>
          )}
        </div>
      ) : (
        <div className="card table-card">
          <table className="reports-table">
            <thead>
              <tr>
                <th>ID &amp; Title</th>
                <th>Affected Component</th>
                <th>Severity (Proposed / Final)</th>
                <th>Status</th>
                <th>Submitted</th>
                <th className="text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr key={report.id}>
                  <td>
                    <Link
                      to={`/reports/${report.id}`}
                      className="report-title-link"
                    >
                      #{report.id} — {report.title}
                    </Link>
                    <div className="report-meta-id">
                      <span>Reporter ID: #{report.reporter_id}</span>
                      {report.rejection_reason && (
                        <span className="rejection-pill">
                          Has Rejection Reason
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <code className="component-tag">{report.component}</code>
                  </td>
                  <td>
                    <div className="severity-stack">
                      <SeverityBadge
                        severity={
                          report.final_severity || report.proposed_severity
                        }
                        labelPrefix={
                          report.final_severity ? "Final" : "Proposed"
                        }
                      />
                    </div>
                  </td>
                  <td>
                    <StatusBadge status={report.status} />
                  </td>
                  <td className="date-cell">
                    {new Date(report.created_at).toLocaleDateString()}
                  </td>
                  <td className="text-right">
                    <Link
                      to={`/reports/${report.id}`}
                      className="btn btn-secondary btn-sm"
                    >
                      View Details →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>


          {totalPages > 1 && (
            <div className="pagination-bar">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                ← Previous
              </button>
              <span>
                Page <strong>{page}</strong> of <strong>{totalPages}</strong>
              </span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
