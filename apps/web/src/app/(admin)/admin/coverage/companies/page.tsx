import Link from "next/link";

import { AdminCoverageDashboardPanel } from "@/components/admin/admin-coverage-dashboard";
import { Panel } from "@/components/ui/panel";
import { getAdminCoverage } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AdminCoverageCompaniesPage() {
  const result = await getAdminCoverage();

  return (
    <>
      <Panel
        eyebrow="Coverage Companies"
        title="Company coverage registry"
        description="Track in-scope status, latest-report ingestion, historical backfill posture, and field completeness for each public residential developer."
        actions={
          <div className="tag-row">
            <Link className="inline-link" href="/admin/coverage/reports">
              Reports
            </Link>
            <Link className="inline-link" href="/admin/coverage/gaps">
              Gaps
            </Link>
          </div>
        }
      />

      {result.state === "error" || !result.item ? (
        <Panel eyebrow="Status" title="Coverage companies are temporarily unavailable">
          <p className="panel-copy">The registry endpoint is live, but the companies payload could not be loaded right now.</p>
        </Panel>
      ) : (
        <AdminCoverageDashboardPanel initialItem={result.item} />
      )}
    </>
  );
}
