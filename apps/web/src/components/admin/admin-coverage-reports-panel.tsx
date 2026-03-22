"use client";

import type { AdminCoverageReportItem } from "@real-estat-map/shared";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { applyAdminCoverageBulk } from "@/lib/api";
import { formatDate } from "@/lib/format";

export function AdminCoverageReportsPanel({ initialItems }: { initialItems: AdminCoverageReportItem[] }) {
  const router = useRouter();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [scopeValue, setScopeValue] = useState<"in_scope" | "out_of_scope">("in_scope");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function runBulkScopeUpdate() {
    if (selectedIds.length === 0) {
      setFeedback("Select at least one report first.");
      return;
    }

    startTransition(async () => {
      setFeedback(null);
      const result = await applyAdminCoverageBulk({
        target_type: "report",
        action: "set_scope",
        ids: selectedIds,
        is_in_scope: scopeValue === "in_scope",
      });
      if (!result.item) {
        setFeedback("Could not update report scope.");
        return;
      }
      setFeedback(`Updated ${result.item.appliedCount} reports.`);
      setSelectedIds([]);
      router.refresh();
    });
  }

  return (
    <div className="section-stack">
      {feedback ? <p className="muted-copy">{feedback}</p> : null}

      <div className="admin-form-grid">
        <label className="filter-field">
          <span>Bulk scope</span>
          <select value={scopeValue} onChange={(event) => setScopeValue(event.target.value as "in_scope" | "out_of_scope")}>
            <option value="in_scope">In scope</option>
            <option value="out_of_scope">Out of scope</option>
          </select>
        </label>
        <div className="form-actions">
          <button className="primary-button" disabled={isPending || selectedIds.length === 0} onClick={runBulkScopeUpdate} type="button">
            Apply to {selectedIds.length} reports
          </button>
        </div>
      </div>

      {initialItems.length > 0 ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th></th>
                <th>Company</th>
                <th>Report</th>
                <th>Period</th>
                <th>Status</th>
                <th>Canonical impact</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {initialItems.map((item) => (
                <tr key={item.reportId}>
                  <td>
                    <input
                      checked={selectedIds.includes(item.reportId)}
                      type="checkbox"
                      onChange={(event) =>
                        setSelectedIds((current) =>
                          event.target.checked
                            ? [...current, item.reportId]
                            : current.filter((value) => value !== item.reportId),
                        )
                      }
                    />
                  </td>
                  <td>{item.companyNameHe}</td>
                  <td>
                    <div className="stacked-cell">
                      <Link href={`/admin/sources/${item.reportId}`}>{item.reportName ?? "Manual source"}</Link>
                      <span className="muted-copy">{item.reportType}</span>
                    </div>
                  </td>
                  <td>
                    <div className="stacked-cell">
                      <span>{formatDate(item.periodEndDate)}</span>
                      <span className="muted-copy">{formatDate(item.publishedAt)}</span>
                    </div>
                  </td>
                  <td>
                    <div className="stacked-cell">
                      <span>{item.ingestionStatus}</span>
                      <span className="muted-copy">{item.isInScope ? "in scope" : "out of scope"}</span>
                    </div>
                  </td>
                  <td>
                    <div className="stacked-cell">
                      <span>{item.linkedProjectCount} projects</span>
                      <span className="muted-copy">{item.linkedSnapshotCount} snapshots</span>
                    </div>
                  </td>
                  <td>
                    <div className="stacked-cell">
                      <span>{item.sourceLabel ?? "No source label"}</span>
                      <span className="muted-copy">
                        {item.sourceIsOfficial ? "official" : "non-official"} | {item.isPublishedIntoCanonical ? "published" : "not published"}
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <strong>No reports matched this view.</strong>
          <p className="panel-copy">Try broadening the filters or register additional source reports.</p>
        </div>
      )}
    </div>
  );
}
