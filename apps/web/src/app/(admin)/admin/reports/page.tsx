import { AdminReportsDashboard } from "@/components/admin/admin-reports-dashboard";
import { Panel } from "@/components/ui/panel";
import { getAdminReports, getCompanies } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AdminReportsPage() {
  const [{ items: reports, state: reportsState }, { items: companies, state: companiesState }] = await Promise.all([
    getAdminReports(),
    getCompanies(),
  ]);

  return (
    <>
      <Panel
        eyebrow="Admin Reports"
        title="Manual ingestion bridge"
        description="Register a real source report, create staging project candidates, review match suggestions, compare against canonical values, and publish with audit and provenance."
      />

      {reportsState === "error" || companiesState === "error" ? (
        <Panel eyebrow="Status" title="Admin report data is temporarily unavailable">
          <p className="panel-copy">
            The route is live, but the report registry or company list API did not return a usable payload.
          </p>
        </Panel>
      ) : null}

      <AdminReportsDashboard companies={companies} reports={reports} />
    </>
  );
}
