import Link from "next/link";

import { Panel } from "@/components/ui/panel";
import { getAdminCoverageGaps, getCompanies } from "@/lib/api";
import { formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function single(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function AdminCoverageGapsPage({ searchParams }: PageProps) {
  const params = (await searchParams) ?? {};
  const filters = {
    company_id: single(params.company_id),
    city: single(params.city),
    location_confidence: single(params.location_confidence),
    backfill_status: single(params.backfill_status),
    missing_group: single(params.missing_group),
  };
  const [gapsResult, companiesResult] = await Promise.all([getAdminCoverageGaps(filters), getCompanies()]);
  const exportBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const exportQuery = new URLSearchParams(
    Object.fromEntries(Object.entries(filters).filter(([, value]) => Boolean(value))) as Record<string, string>,
  ).toString();
  const exportBase = `${exportBaseUrl}/api/v1/admin/coverage/export${exportQuery ? `?${exportQuery}&` : "?"}`;

  return (
    <>
      <Panel
        eyebrow="Coverage Gaps"
        title="Backfill gaps and stale projects"
        description="Focus the backlog on projects missing key public fields, stale snapshot coverage, and weak location quality."
      >
        <form className="admin-form-grid" method="get">
          <label className="filter-field">
            <span>Company</span>
            <select defaultValue={filters.company_id ?? ""} name="company_id">
              <option value="">All companies</option>
              {companiesResult.items.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.nameHe}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>City</span>
            <input defaultValue={filters.city ?? ""} name="city" placeholder="Filter by city" />
          </label>
          <label className="filter-field">
            <span>Location confidence</span>
            <input defaultValue={filters.location_confidence ?? ""} name="location_confidence" placeholder="exact, approximate, city_only, unknown" />
          </label>
          <label className="filter-field">
            <span>Backfill status</span>
            <input defaultValue={filters.backfill_status ?? ""} name="backfill_status" placeholder="historical_backfill, complete" />
          </label>
          <label className="filter-field">
            <span>Gap type</span>
            <select defaultValue={filters.missing_group ?? ""} name="missing_group">
              <option value="">All</option>
              <option value="location">Location gaps</option>
              <option value="metrics">Metric gaps</option>
              <option value="stale">Stale / missing snapshot</option>
            </select>
          </label>
          <div className="form-actions">
            <button className="primary-button" type="submit">
              Apply filters
            </button>
            <a className="secondary-button" href="/admin/coverage/gaps">
              Clear
            </a>
            <a className="secondary-button" href={`${exportBase}kind=gaps`}>
              Export gaps
            </a>
            <a className="secondary-button" href={`${exportBase}kind=metrics_missing`}>
              Export missing metrics
            </a>
            <a className="secondary-button" href={`${exportBase}kind=location_missing`}>
              Export missing location
            </a>
          </div>
        </form>
      </Panel>

      {gapsResult.state === "error" || !gapsResult.item ? (
        <Panel eyebrow="Status" title="Coverage gaps are temporarily unavailable">
          <p className="panel-copy">The backlog endpoint did not return a usable payload right now.</p>
        </Panel>
      ) : (
        <>
          <section className="stats-grid">
            <div>
              <strong>{gapsResult.item.summary.totalItems}</strong>
              <span>Total rows</span>
            </div>
            <div>
              <strong>{gapsResult.item.summary.missingLocation}</strong>
              <span>Missing location</span>
            </div>
            <div>
              <strong>{gapsResult.item.summary.missingMetrics}</strong>
              <span>Missing metrics</span>
            </div>
            <div>
              <strong>{gapsResult.item.summary.staleOrMissingSnapshot}</strong>
              <span>Stale or no snapshot</span>
            </div>
          </section>

          <Panel eyebrow="Gap Table" title="Projects needing backfill attention">
            {gapsResult.item.items.length > 0 ? (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Project</th>
                      <th>Location</th>
                      <th>Latest snapshot</th>
                      <th>Missing fields</th>
                      <th>Coverage</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gapsResult.item.items.map((item) => (
                      <tr key={item.projectId}>
                        <td>
                          <div className="stacked-cell">
                            <Link href={`/admin/projects/${item.projectId}`}>{item.projectName}</Link>
                            <span className="muted-copy">
                              {item.companyNameHe} | {item.city ?? "Unknown city"}
                            </span>
                          </div>
                        </td>
                        <td>
                          <div className="stacked-cell">
                            <span>{item.locationQuality}</span>
                            <span className="muted-copy">{item.backfillStatus}</span>
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
                        <td>{item.missingFields.join(", ") || "No tracked gaps"}</td>
                        <td>
                          <div className="stacked-cell">
                            <span>{item.sourceCount} sources</span>
                            <span className="muted-copy">{item.addressCount} addresses</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state">
                <strong>No projects matched the current coverage-gap view.</strong>
                <p className="panel-copy">Try widening the filters or removing the gap-type constraint.</p>
              </div>
            )}
          </Panel>
        </>
      )}
    </>
  );
}
