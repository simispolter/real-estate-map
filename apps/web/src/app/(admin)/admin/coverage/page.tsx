import { AdminCoverageDashboardPanel } from "@/components/admin/admin-coverage-dashboard";
import { Panel } from "@/components/ui/panel";
import { getAdminCoverage } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AdminCoveragePage() {
  const result = await getAdminCoverage();

  return (
    <>
      <Panel
        eyebrow="Admin Coverage"
        title="Backfill and operational coverage"
        description="Track which public residential developers are in scope, how complete their source history is, and where intake, location, or key-field gaps still need manual work."
      />

      {result.state === "error" || !result.item ? (
        <Panel eyebrow="Status" title="Coverage data is temporarily unavailable">
          <p className="panel-copy">The coverage registry endpoint is live, but the dashboard payload could not be loaded right now.</p>
        </Panel>
      ) : (
        <AdminCoverageDashboardPanel initialItem={result.item} />
      )}
    </>
  );
}
