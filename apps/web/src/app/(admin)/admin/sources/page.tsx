import { AdminReportsDashboard } from "@/components/admin/admin-reports-dashboard";
import { Panel } from "@/components/ui/panel";
import { getAdminReportQa, getAdminReports, getCompanies } from "@/lib/api";

export const dynamic = "force-dynamic";

const BOOTSTRAP_BATCH_LABEL = "Bootstrap annual report batch 2026-03-26";

export default async function AdminSourcesPage() {
  const [{ items: reports, state: reportsState }, { items: companies, state: companiesState }] = await Promise.all([
    getAdminReports(),
    getCompanies(),
  ]);
  const bootstrapReports = reports.filter((report) => (report.sourceLabel ?? "").includes(BOOTSTRAP_BATCH_LABEL));
  const bootstrapQaResults = await Promise.all(bootstrapReports.map((report) => getAdminReportQa(report.id)));
  const bootstrapSummary = bootstrapQaResults.reduce(
    (summary, result) => {
      if (!result.item) {
        return summary;
      }
      summary.candidatesExtracted += result.item.summary.extractedCandidates;
      summary.matchedExisting += result.item.summary.matchedExistingProjects;
      summary.newProjectsCreated += result.item.summary.newCanonicalProjectsCreated;
      summary.manuallyAdded += result.item.summary.manualCandidates;
      summary.snapshotsPublished += result.item.summary.publishedCandidates;
      summary.unresolvedPending += result.item.summary.unresolvedPendingCandidates;
      return summary;
    },
    {
      reportsRegistered: bootstrapReports.length,
      candidatesExtracted: 0,
      matchedExisting: 0,
      newProjectsCreated: 0,
      manuallyAdded: 0,
      snapshotsPublished: 0,
      unresolvedPending: 0,
    },
  );

  return (
    <>
      <Panel
        eyebrow="Admin Sources"
        title="Source registry and staging"
        description="Reports live here as supporting source records. Use this area to register annual reports, run extraction into staging, and hand reviewed candidates into the canonical project database."
      />

      {bootstrapReports.length > 0 ? (
        <Panel
          eyebrow="Bootstrap Batch"
          title="Latest annual-report bootstrap status"
          description="This rollup tracks the practical batch loaded from the newest uploaded annual reports so you can verify that canonical projects and snapshots are landing in the database."
        >
          <div className="table-wrap">
            <table className="data-table">
              <tbody>
                <tr>
                  <th>Reports registered</th>
                  <td>{bootstrapSummary.reportsRegistered}</td>
                  <th>Extracted candidates</th>
                  <td>{bootstrapSummary.candidatesExtracted}</td>
                </tr>
                <tr>
                  <th>Matched existing</th>
                  <td>{bootstrapSummary.matchedExisting}</td>
                  <th>New canonical projects</th>
                  <td>{bootstrapSummary.newProjectsCreated}</td>
                </tr>
                <tr>
                  <th>Manually added candidates</th>
                  <td>{bootstrapSummary.manuallyAdded}</td>
                  <th>Snapshots published</th>
                  <td>{bootstrapSummary.snapshotsPublished}</td>
                </tr>
                <tr>
                  <th>Unresolved pending</th>
                  <td>{bootstrapSummary.unresolvedPending}</td>
                  <th>Batch label</th>
                  <td>{BOOTSTRAP_BATCH_LABEL}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Panel>
      ) : null}

      {reportsState === "error" || companiesState === "error" ? (
        <Panel eyebrow="Status" title="Source data is temporarily unavailable">
          <p className="panel-copy">The source registry is live, but the reports or companies payload is currently unavailable.</p>
        </Panel>
      ) : null}

      <AdminReportsDashboard companies={companies} reports={reports} />
    </>
  );
}
