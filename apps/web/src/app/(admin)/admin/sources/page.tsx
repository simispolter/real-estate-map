import { AdminReportsDashboard } from "@/components/admin/admin-reports-dashboard";
import { Panel } from "@/components/ui/panel";
import { getAdminReports, getCompanies } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AdminSourcesPage() {
  const [{ items: reports, state: reportsState }, { items: companies, state: companiesState }] = await Promise.all([
    getAdminReports(),
    getCompanies(),
  ]);

  return (
    <>
      <Panel
        eyebrow="Admin Sources"
        title="Source registry and staging"
        description="Reports live here as supporting source records. Use this area to register source metadata and create staging candidates that later flow into the project-centric intake queue."
      />

      {reportsState === "error" || companiesState === "error" ? (
        <Panel eyebrow="Status" title="Source data is temporarily unavailable">
          <p className="panel-copy">The source registry is live, but the reports or companies payload is currently unavailable.</p>
        </Panel>
      ) : null}

      <AdminReportsDashboard companies={companies} reports={reports} />
    </>
  );
}
