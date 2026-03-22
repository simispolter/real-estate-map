"use client";

import type { AdminOpsDashboard } from "@real-estat-map/shared";

export function AdminOpsDashboardPanel({ item }: { item: AdminOpsDashboard }) {
  const summaryCards = [
    { label: "Reports registered", value: item.summary.reportsRegistered },
    { label: "Projects created", value: item.summary.projectsCreated },
    { label: "Snapshots created", value: item.summary.snapshotsCreated },
    { label: "Open anomalies", value: item.summary.openAnomalies },
    { label: "Parser failed runs", value: item.summary.parserFailedRuns },
    { label: "Ready to publish", value: item.summary.readyToPublish },
  ];
  const parserHealth = item.parserHealth;
  const recentRuns = Array.isArray(parserHealth.recent_runs)
    ? (parserHealth.recent_runs as Array<Record<string, unknown>>)
    : [];
  const locationBreakdown = typeof item.locationCompleteness.breakdown === "object" && item.locationCompleteness.breakdown !== null
    ? (item.locationCompleteness.breakdown as Record<string, unknown>)
    : {};

  return (
    <div className="section-stack">
      <div className="stats-grid">
        {summaryCards.map((card) => (
          <div key={card.label}>
            <strong>{card.value}</strong>
            <span>{card.label}</span>
          </div>
        ))}
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Ops Dashboard</p>
          <h3>Operational monitoring</h3>
        </div>
        <div className="stats-grid">
          {Object.entries(item.matchingBacklog).map(([key, value]) => (
            <div key={key}>
              <strong>{value}</strong>
              <span>{key.replaceAll("_", " ")}</span>
            </div>
          ))}
          {Object.entries(item.publishBacklog).map(([key, value]) => (
            <div key={key}>
              <strong>{value}</strong>
              <span>{key.replaceAll("_", " ")}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Location Completeness</p>
          <h3>Canonical location confidence</h3>
        </div>
        <div className="tag-row">
          {Object.entries(locationBreakdown).map(([key, value]) => (
            <span className="tag" key={key}>
              {key}: {String(value)}
            </span>
          ))}
        </div>
      </div>

      <div className="admin-form-card section-stack">
        <div>
          <p className="eyebrow">Parser Health</p>
          <h3>Recent extraction runs</h3>
        </div>
        {recentRuns.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Report</th>
                  <th>Candidates</th>
                  <th>Warnings</th>
                  <th>Errors</th>
                  <th>Finished</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run, index) => (
                  <tr key={String(run.id ?? index)}>
                    <td>{String(run.status ?? "unknown")}</td>
                    <td>{String(run.report_id ?? "--")}</td>
                    <td>{String(run.candidate_count ?? 0)}</td>
                    <td>{String(run.warnings_count ?? 0)}</td>
                    <td>{String(run.errors_count ?? 0)}</td>
                    <td>{String(run.finished_at ?? "--")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <strong>No parser runs yet.</strong>
            <p className="panel-copy">Run extraction from a source report to populate parser-health diagnostics here.</p>
          </div>
        )}
      </div>
    </div>
  );
}
