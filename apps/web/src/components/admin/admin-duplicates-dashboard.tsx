"use client";

import type { AdminDuplicateSuggestion } from "@real-estat-map/shared";
import Link from "next/link";
import { useState, useTransition } from "react";

import { getAdminDuplicates, mergeAdminProjects } from "@/lib/api";

export function AdminDuplicatesDashboard({ initialItems }: { initialItems: AdminDuplicateSuggestion[] }) {
  const [items, setItems] = useState(initialItems);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleMerge(winnerProjectId: string, loserProjectId: string) {
    const mergeReason = `Merged from duplicate suggestion ${loserProjectId} into ${winnerProjectId}`;
    startTransition(async () => {
      setFeedback(null);
      const result = await mergeAdminProjects({
        winner_project_id: winnerProjectId,
        loser_project_id: loserProjectId,
        merge_reason: mergeReason,
      });
      if (!result.item) {
        setFeedback("Could not merge projects.");
        return;
      }
      const refreshed = await getAdminDuplicates();
      setItems(refreshed.items);
      setFeedback("Projects merged safely. The loser project is now marked as merged and hidden from the main index.");
    });
  }

  return (
    <div className="admin-form-card section-stack">
      {feedback ? <p className="muted-copy">{feedback}</p> : null}
      {items.length > 0 ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Project</th>
                <th>Duplicate</th>
                <th>Company</th>
                <th>State</th>
                <th>Score</th>
                <th>Signals</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <Link className="inline-link" href={`/admin/projects/${item.projectId}`}>
                      {item.projectName}
                    </Link>
                  </td>
                  <td>
                    <Link className="inline-link" href={`/admin/projects/${item.duplicateProjectId}`}>
                      {item.duplicateProjectName}
                    </Link>
                  </td>
                  <td>{item.companyName}</td>
                  <td>{item.matchState}</td>
                  <td>{item.score.toFixed(2)}</td>
                  <td>
                    {Object.entries(item.reasonsJson)
                      .slice(0, 3)
                      .map(([key, value]) => `${key}: ${String(value)}`)
                      .join(" | ")}
                  </td>
                  <td>
                    <div className="form-actions">
                      <button className="primary-button" disabled={isPending} onClick={() => handleMerge(item.projectId, item.duplicateProjectId)} type="button">
                        Merge into first
                      </button>
                      <button className="secondary-button" disabled={isPending} onClick={() => handleMerge(item.duplicateProjectId, item.projectId)} type="button">
                        Merge into second
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <strong>No likely duplicate projects were detected.</strong>
          <p className="panel-copy">As aliases, addresses, and snapshots expand, this page will surface the next likely collisions.</p>
        </div>
      )}
    </div>
  );
}
