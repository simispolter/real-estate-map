"use client";

import type { AdminAnomalyItem } from "@real-estat-map/shared";
import Link from "next/link";

function severityClass(severity: string) {
  if (severity === "high") {
    return "tag tag-warning";
  }
  if (severity === "medium") {
    return "tag tag-accent";
  }
  return "tag";
}

export function AdminAnomaliesDashboard({ items }: { items: AdminAnomalyItem[] }) {
  if (items.length === 0) {
    return (
      <div className="empty-state">
        <strong>No anomalies are currently flagged.</strong>
        <p className="panel-copy">The checks for trust, chronology, and metric consistency did not surface any current review items.</p>
      </div>
    );
  }

  return (
    <div className="admin-form-card section-stack">
      <div>
        <p className="eyebrow">Admin Anomalies</p>
        <h3>Trust and data-quality checks</h3>
        <p className="panel-copy">These flags are read-only in this sprint. Use them to jump into the affected project or source workflow and correct the underlying data.</p>
      </div>

      <div className="section-stack">
        {items.map((item) => (
          <div className="candidate-suggestion-card" key={item.id}>
            <div className="candidate-queue-header">
              <div>
                <strong>{item.projectName}</strong>
                <p className="panel-copy">{item.companyName}</p>
              </div>
              <div className="tag-row">
                <span className={severityClass(item.severity)}>{item.severity}</span>
                <span className="tag">{item.anomalyType}</span>
              </div>
            </div>
            <p className="panel-copy">{item.summary}</p>
            <p className="muted-copy">
              {Object.entries(item.detailsJson)
                .slice(0, 4)
                .map(([key, value]) => `${key}: ${String(value)}`)
                .join(" | ") || "No structured detail captured."}
            </p>
            <div className="form-actions">
              <Link className="inline-link" href={`/admin/projects/${item.projectId}`}>
                Open project
              </Link>
              {item.reportId ? (
                <Link className="inline-link" href={`/admin/sources/${item.reportId}`}>
                  Open source
                </Link>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
