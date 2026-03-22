import { AdminOpsDashboardPanel } from "@/components/admin/admin-ops-dashboard";
import { Panel } from "@/components/ui/panel";
import { getAdminOps } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AdminOpsPage() {
  const result = await getAdminOps();

  return (
    <>
      <Panel
        eyebrow="Admin Ops"
        title="Ingestion and review operations"
        description="Track parser health, backlog, publish readiness, and location completeness from one operational surface."
      />

      {result.state === "error" || !result.item ? (
        <Panel eyebrow="Status" title="Ops data is temporarily unavailable">
          <p className="panel-copy">The ops dashboard could not be loaded right now.</p>
        </Panel>
      ) : (
        <AdminOpsDashboardPanel item={result.item} />
      )}
    </>
  );
}
