"use client";

import type { AdminLocationReviewItem } from "@real-estat-map/shared";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { geocodeAdminProjectAddress, normalizeAdminProjectAddress } from "@/lib/api";
import { formatDate } from "@/lib/format";

export function AdminLocationReviewDashboard({ initialItems }: { initialItems: AdminLocationReviewItem[] }) {
  const router = useRouter();
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function normalizePrimary(projectId: string, addressId: string | null) {
    if (!addressId) {
      setFeedback("This project does not have a primary address yet.");
      return;
    }
    startTransition(async () => {
      setFeedback(null);
      const result = await normalizeAdminProjectAddress(projectId, addressId);
      if (!result.item) {
        setFeedback("Address normalization failed.");
        return;
      }
      setFeedback("Primary address normalized.");
      router.refresh();
    });
  }

  function geocodePrimary(projectId: string, addressId: string | null) {
    if (!addressId) {
      setFeedback("This project does not have a primary address yet.");
      return;
    }
    startTransition(async () => {
      setFeedback(null);
      const result = await geocodeAdminProjectAddress(projectId, addressId);
      if (!result.item) {
        setFeedback("Primary address geocoding failed.");
        return;
      }
      setFeedback("Primary address geocoded.");
      router.refresh();
    });
  }

  return (
    <div className="section-stack">
      {feedback ? <p className="muted-copy">{feedback}</p> : null}
      {initialItems.length > 0 ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Project</th>
                <th>Location quality</th>
                <th>Primary address</th>
                <th>Geocoding</th>
                <th>Snapshot freshness</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {initialItems.map((item) => (
                <tr key={item.projectId}>
                  <td>
                    <div className="stacked-cell">
                      <Link href={`/admin/projects/${item.projectId}`}>{item.projectName}</Link>
                      <span className="muted-copy">
                        {item.company.nameHe} | {item.city ?? "Unknown city"}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="stacked-cell">
                      <span>{item.locationQuality}</span>
                      <span className="muted-copy">
                        {item.geometryType} | {item.geometryIsManual ? "manual" : item.geometrySource}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="stacked-cell">
                      <span>{item.primaryAddressSummary ?? "No address summary"}</span>
                      <span className="muted-copy">
                        {item.addressCount} addresses | {item.backfillStatus}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="stacked-cell">
                      <span>{item.geocodingStatus ?? "not_started"}</span>
                      <span className="muted-copy">
                        {item.geocodingMethod ?? "No method"} | {item.isGeocodingReady ? "ready" : "not ready"}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="stacked-cell">
                      <span>{formatDate(item.latestSnapshotDate)}</span>
                      <span className="muted-copy">
                        {item.latestSnapshotAgeDays !== null ? `${item.latestSnapshotAgeDays} days` : "No snapshot"}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="form-actions">
                      <button className="secondary-button" disabled={isPending} onClick={() => normalizePrimary(item.projectId, item.primaryAddressId)} type="button">
                        Normalize
                      </button>
                      <button className="secondary-button" disabled={isPending} onClick={() => geocodePrimary(item.projectId, item.primaryAddressId)} type="button">
                        Geocode
                      </button>
                      <Link className="primary-button" href={`/admin/projects/${item.projectId}`}>
                        Open project
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <strong>No projects need focused location review in this filter set.</strong>
          <p className="panel-copy">Try including all projects or broadening the company and city filters.</p>
        </div>
      )}
    </div>
  );
}
