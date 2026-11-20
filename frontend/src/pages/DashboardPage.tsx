import React, { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { DashboardSummary } from "../types";


const SEV_BAR_COLORS: Record<string, string> = {
  critical: "#dc2626",
  high: "#ea580c",
  medium: "#eab308",
  low: "#64748b",
};


export const DashboardPage: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);


  useEffect(() => {
    api
      .getDashboardSummary()
      .then(setSummary)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Failed to load stats")
      );
  }, []);


  if (error) {
    return (
      <div className="page-container">
        <div className="alert alert-danger">{error}</div>
      </div>
    );
  }


  if (!summary) {
    return (
      <div className="page-container">
        <div className="card loading-state">Loading dashboard metrics...</div>
      </div>
    );
  }


  const maxStatus = Math.max(1, ...Object.values(summary.by_status));
  const maxSeverity = Math.max(1, ...Object.values(summary.by_severity));


  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Vulnerability &amp; SLA Dashboard</h1>
          <p className="page-subtitle">
            Role-scoped metrics for <code>{summary.role}</code>.
          </p>
        </div>
      </div>


      <div className="kpi-grid">
        <div className="card kpi-card">
          <span className="kpi-label">Total Reports</span>
          <strong className="kpi-value">{summary.total_reports}</strong>
        </div>
        <div className="card kpi-card">
          <span className="kpi-label">Open Reports</span>
          <strong className="kpi-value">{summary.open_reports}</strong>
        </div>
        <div className="card kpi-card kpi-danger">
          <span className="kpi-label">Overdue SLA</span>
          <strong className="kpi-value">{summary.overdue_reports}</strong>
        </div>
        <div className="card kpi-card">
          <span className="kpi-label">Avg First Response</span>
          <strong className="kpi-value">
            {summary.avg_first_response_hours !== null
              ? `${summary.avg_first_response_hours}h`
              : "N/A"}
          </strong>
        </div>
        {summary.total_users !== null && (
          <div className="card kpi-card">
            <span className="kpi-label">Active Users (Banned)</span>
            <strong className="kpi-value">
              {summary.total_users} ({summary.banned_users ?? 0})
            </strong>
          </div>
        )}
      </div>


      <div className="bottom-grid mt-4">
        <section className="card section-card">
          <h2 className="section-title">Reports by Status</h2>
          <div className="chart-list mt-3">
            {Object.entries(summary.by_status).map(([st, count]) => (
              <div key={st} className="chart-row">
                <div className="chart-label-row">
                  <code>{st}</code>
                  <strong>{count}</strong>
                </div>
                <div className="chart-track">
                  <div
                    className="chart-fill"
                    style={{
                      width: `${Math.round((count / maxStatus) * 100)}%`,
                      backgroundColor: "var(--primary)",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>


        <section className="card section-card">
          <h2 className="section-title">Reports by Effective Severity</h2>
          <div className="chart-list mt-3">
            {Object.entries(summary.by_severity).map(([sev, count]) => (
              <div key={sev} className="chart-row">
                <div className="chart-label-row">
                  <code>{sev}</code>
                  <strong>{count}</strong>
                </div>
                <div className="chart-track">
                  <div
                    className="chart-fill"
                    style={{
                      width: `${Math.round((count / maxSeverity) * 100)}%`,
                      backgroundColor: SEV_BAR_COLORS[sev] || "var(--primary)",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};
