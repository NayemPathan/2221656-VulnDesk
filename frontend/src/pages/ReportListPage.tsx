import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { SeverityBadge, StatusBadge } from "../components/Badges";
import { useAuth } from "../context/AuthContext";
import { ReportRead, ReportStatus, Severity } from "../types";
import { useToast } from "../context/ToastContext";

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
  const { currentUser } = useAuth();
  const {showToast, confirmAction} = useToast();

  const [reports, setReports] = useState<ReportRead[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [pageSize] = useState<number>(10);

  const [keyword, setKeyword] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [componentFilter, setComponentFilter] = useState<string>("");

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [overdueOnly, setOverdueOnly] = useState<boolean>(false);
  const [sortOrder, setSortOrder] = useState<"newest" | "oldest" | "severity">("newest");


  const fetchReports = useCallback(async () => {
    if (!currentUser) return;
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
    currentUser,
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

  if (!currentUser) return null;

  const handleResetFilters = () => {
  const snapshot = {
    keyword,
    statusFilter,
    severityFilter,
    componentFilter,
    overdueOnly,
    sortOrder,
  };
  setKeyword("");
  setStatusFilter("");
  setSeverityFilter("");
  setComponentFilter("");
  setOverdueOnly(false);
  setSortOrder("newest");
  setPage(1);


  if (
    snapshot.keyword ||
    snapshot.statusFilter ||
    snapshot.severityFilter ||
    snapshot.componentFilter ||
    snapshot.overdueOnly
  ) {
    showToast("Filters reset.", "info", () => {
      setKeyword(snapshot.keyword);
      setStatusFilter(snapshot.statusFilter);
      setSeverityFilter(snapshot.severityFilter);
      setComponentFilter(snapshot.componentFilter);
      setOverdueOnly(snapshot.overdueOnly);
      setSortOrder(snapshot.sortOrder);
    });
  }
};


  const SEV_WEIGHT: Record<Severity, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
};


const displayedReports = reports
  .filter((r) => (overdueOnly ? Boolean(r.is_overdue) : true))
  .slice()
  .sort((a, b) => {
    if (sortOrder === "oldest") {
      return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    }
    if (sortOrder === "severity") {
      const sa = SEV_WEIGHT[a.final_severity || a.proposed_severity] || 0;
      const sb = SEV_WEIGHT[b.final_severity || b.proposed_severity] || 0;
      return sb - sa;
    }
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });


const handleExportCsv = () => {
  const headers = ["ID", "Title", "Component", "Proposed Severity", "Final Severity", "Status", "Overdue SLA", "Created At"];
  const escape = (val: unknown) => `"${String(val ?? "").replace(/"/g, '""')}"`;
  const rows = displayedReports.map((r) =>
    [
      r.id,
      r.title,
      r.component,
      r.proposed_severity,
      r.final_severity || "",
      r.status,
      r.is_overdue ? "YES" : "NO",
      r.created_at,
    ]
      .map(escape)
      .join(",")
  );
  const csv = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "vulndesk_reports_export.csv";
  link.click();
  URL.revokeObjectURL(url);
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
            Signed in as <strong>{currentUser.name}</strong> (
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
          <strong>Account Banned:</strong> Your researcher account (
          <code>{currentUser.email}</code>) is flagged with{" "}
          <code>is_banned = true</code>.
        </div>
      )}

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
         Showing <strong>{displayedReports.length}</strong> of{" "}
         <strong>{total}</strong> matching report(s)
       </span>
       <div className="owner-actions" style={{ flexWrap: "wrap" }}>
         <label className="overdue-toggle-label">
           <input
             type="checkbox"
             checked={overdueOnly}
             onChange={(e) => setOverdueOnly(e.target.checked)}
           />
           <span>⏰ Overdue SLA Only</span>
         </label>
         <select
           className="form-select"
           style={{ padding: "0.3rem 0.5rem", fontSize: "0.82rem" }}
           value={sortOrder}
           onChange={(e) =>
             setSortOrder(e.target.value as "newest" | "oldest" | "severity")
           }
         >
           <option value="newest">Sort: Newest</option>
           <option value="oldest">Sort: Oldest</option>
           <option value="severity">Sort: Highest Severity</option>
         </select>
         <button
           type="button"
           className="btn btn-secondary btn-sm"
           onClick={handleExportCsv}
           disabled={displayedReports.length === 0}
         >
           ⬇ Export CSV
         </button>
         <button
           type="button"
           className="btn btn-secondary btn-sm"
           onClick={() => {
             handleResetFilters();
             setOverdueOnly(false);
             setSortOrder("newest");
           }}
         >
           Reset Filters
         </button>
       </div>
     </div>
      </section>

      {error && (
        <div className="alert alert-danger" role="alert">
          <strong>Error loading reports:</strong> {error}
        </div>
      )}

      {loading ? (
        <div className="card loading-state">Loading vulnerability reports...</div>
      ) : displayedReports.length === 0 ? (
        <div className="card empty-state">
          <h3>No vulnerability reports found</h3>
          <p>
            No reports match your current account scope or filter criteria.
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
              {displayedReports.map((report) => (
                <tr key={report.id}>
                  <td>
                    <Link
                      to={`/reports/${report.id}`}
                      className="report-title-link"
                    >
                      #{report.id} — {report.title}
                    </Link>
                    {report.is_overdue && (
                      <span className="overdue-badge">⏰ OVERDUE SLA</span>
                    )}
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