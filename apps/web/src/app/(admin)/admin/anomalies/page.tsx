import { AdminAnomaliesDashboard } from "@/components/admin/admin-anomalies-dashboard";
import { Panel } from "@/components/ui/panel";
import { getAdminAnomalies } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AdminAnomaliesPage() {
  const result = await getAdminAnomalies();

  return (
    <>
      <Panel
        eyebrow="Admin Anomalies"
        title="Trust and anomaly review"
        description="Monitor suspicious metrics, chronology problems, location downgrades, and source-cycle gaps before they quietly affect the research product."
      />

      {result.state === "error" ? (
        <Panel eyebrow="Status" title="Anomalies are temporarily unavailable">
          <p className="panel-copy">The anomaly endpoint could not be loaded right now.</p>
        </Panel>
      ) : (
        <AdminAnomaliesDashboard items={result.items} />
      )}
    </>
  );
}
