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
      setFeedback("לפרויקט הזה עדיין אין כתובת ראשית.");
      return;
    }
    startTransition(async () => {
      setFeedback(null);
      const result = await normalizeAdminProjectAddress(projectId, addressId);
      if (!result.item) {
        setFeedback("נרמול הכתובת נכשל.");
        return;
      }
      setFeedback("הכתובת הראשית נורמלה בהצלחה.");
      router.refresh();
    });
  }

  function geocodePrimary(projectId: string, addressId: string | null) {
    if (!addressId) {
      setFeedback("לפרויקט הזה עדיין אין כתובת ראשית.");
      return;
    }
    startTransition(async () => {
      setFeedback(null);
      const result = await geocodeAdminProjectAddress(projectId, addressId);
      if (!result.item) {
        setFeedback("איתור הכתובת הראשית נכשל.");
        return;
      }
      setFeedback("הכתובת הראשית אותרה בהצלחה.");
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
                <th>פרויקט</th>
                <th>איכות מיקום</th>
                <th>כתובת ראשית</th>
                <th>איתור</th>
                <th>עדכניות</th>
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
                        {item.company.nameHe} | {item.city ?? "עיר לא ידועה"}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="stacked-cell">
                      <span>{item.locationQuality}</span>
                      <span className="muted-copy">
                        {item.geometryType} | {item.geometryIsManual ? "ידני" : item.geometrySource}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="stacked-cell">
                      <span>{item.primaryAddressSummary ?? "אין כתובת מסוכמת"}</span>
                      <span className="muted-copy">
                        {item.addressCount} כתובות | {item.backfillStatus}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="stacked-cell">
                      <span>{item.geocodingStatus ?? "לא התחיל"}</span>
                      <span className="muted-copy">
                        {item.geocodingMethod ?? "ללא שיטה"} | {item.isGeocodingReady ? "מוכן" : "לא מוכן"}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="stacked-cell">
                      <span>{formatDate(item.latestSnapshotDate)}</span>
                      <span className="muted-copy">
                        {item.latestSnapshotAgeDays !== null ? `${item.latestSnapshotAgeDays} ימים` : "ללא snapshot"}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="form-actions">
                      <button className="secondary-button" disabled={isPending} onClick={() => normalizePrimary(item.projectId, item.primaryAddressId)} type="button">
                        נרמול
                      </button>
                      <button className="secondary-button" disabled={isPending} onClick={() => geocodePrimary(item.projectId, item.primaryAddressId)} type="button">
                        איתור
                      </button>
                      <Link className="primary-button" href={`/admin/projects/${item.projectId}`}>
                        פתיחת פרויקט
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
          <strong>אין כרגע פרויקטים שדורשים טיפול ממוקד במיקום לפי המסננים שנבחרו.</strong>
          <p className="panel-copy">נסו להרחיב את המסננים או לכלול גם פרויקטים עם מיקום מדויק / בקירוב.</p>
        </div>
      )}
    </div>
  );
}
