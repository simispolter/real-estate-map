import Link from "next/link";
import { notFound } from "next/navigation";

import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { Panel } from "@/components/ui/panel";
import { Tag } from "@/components/ui/tag";
import { getCompanyDetail } from "@/lib/api";
import { formatCurrency, formatDate, formatNumber } from "@/lib/format";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function CompanyDetailPage({ params }: PageProps) {
  const { id } = await params;
  const companyResult = await getCompanyDetail(id);

  if (companyResult.state === "error" || !companyResult.item) {
    notFound();
  }

  const company = companyResult.item;

  return (
    <>
      <Panel
        eyebrow="Company Detail"
        title={company.nameHe}
        description="Public developer research view with latest report basis, KPI rollups, city coverage, and project drill-down."
        actions={<Tag>{company.ticker ?? "No ticker"}</Tag>}
      >
        <div className="detail-grid">
          <div className="detail-card section-stack">
            <div>
              <p className="eyebrow">Identity</p>
              <h3>{company.nameHe}</h3>
            </div>
            <p className="panel-copy">Ticker: {company.ticker ?? "Not disclosed"}</p>
            <p className="panel-copy">Project count: {company.projectCount}</p>
            <p className="panel-copy">City count: {company.cityCount}</p>
          </div>

          <div className="detail-card section-stack">
            <div>
              <p className="eyebrow">Latest Public Report</p>
              <h3>{company.latestReportName ?? "Latest available report"}</h3>
            </div>
            <p className="panel-copy">Period end: {formatDate(company.latestReportPeriodEnd)}</p>
            <p className="panel-copy">Published: {formatDate(company.latestPublishedAt)}</p>
          </div>
        </div>
      </Panel>

      <KpiGrid
        title="Company KPI summary"
        items={[
          {
            id: "projects",
            label: "Tracked projects",
            value: String(company.projectCount),
            note: "Based on the current seeded public residential set.",
          },
          {
            id: "cities",
            label: "City spread",
            value: String(company.kpis.companyCitySpread),
            note: "Distinct cities represented by linked public projects.",
          },
          {
            id: "precise",
            label: "Projects with precise location",
            value: String(company.kpis.projectsWithPreciseLocationCount),
            note: "Exact or street-level entries only.",
          },
          {
            id: "unsold",
            label: "Known unsold units",
            value: formatNumber(company.kpis.knownUnsoldUnits),
            note: "Null-safe sum from the latest linked project snapshots.",
          },
          {
            id: "avg-price",
            label: "Known average price per sqm",
            value: formatCurrency(company.kpis.latestKnownAvgPricePerSqm),
            note: "Only computed when report data exists.",
          },
        ]}
      />

      <section className="detail-grid">
        <Panel eyebrow="Coverage" title="City coverage summary">
          {company.cityCoverage.length > 0 ? (
            <div className="callout-list">
              {company.cityCoverage.map((entry) => (
                <div key={entry.city} className="callout-item">
                  <strong>{entry.city}</strong>
                  <p className="panel-copy">{entry.projectCount} linked projects</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <strong>No city coverage data is available.</strong>
              <p className="panel-copy">The company still has a public identity block and project table.</p>
            </div>
          )}
        </Panel>

        <Panel eyebrow="Mix" title="Project business type distribution">
          {company.projectBusinessTypeDistribution.length > 0 ? (
            <div className="callout-list">
              {company.projectBusinessTypeDistribution.map((entry) => (
                <div key={entry.projectBusinessType} className="callout-item">
                  <strong>{entry.projectBusinessType}</strong>
                  <p className="panel-copy">{entry.projectCount} projects</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <strong>No business-type distribution is available.</strong>
              <p className="panel-copy">This will populate as more canonical projects are added.</p>
            </div>
          )}
        </Panel>
      </section>

      <Panel eyebrow="Projects" title="Company projects table">
        {company.projects.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Project</th>
                  <th>City</th>
                  <th>Business type</th>
                  <th>Status</th>
                  <th>Unsold</th>
                  <th>Snapshot</th>
                </tr>
              </thead>
              <tbody>
                {company.projects.map((project) => (
                  <tr key={project.id}>
                    <td>
                      <Link href={`/projects/${project.id}`}>{project.canonicalName}</Link>
                    </td>
                    <td>{project.city ?? "Unknown"}</td>
                    <td>
                      <div className="stacked-cell">
                        <span>{project.projectBusinessType}</span>
                        <Tag>{project.locationQuality}</Tag>
                      </div>
                    </td>
                    <td>{project.projectStatus ?? "Not disclosed"}</td>
                    <td>{formatNumber(project.unsoldUnits)}</td>
                    <td>{formatDate(project.latestSnapshotDate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <strong>No linked company projects are available.</strong>
            <p className="panel-copy">The company page remains stable even when the project set is empty.</p>
          </div>
        )}
      </Panel>
    </>
  );
}
