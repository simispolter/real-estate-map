import Link from "next/link";
import { notFound } from "next/navigation";

import { Panel } from "@/components/ui/panel";
import { Tag } from "@/components/ui/tag";
import { getProjectDetail, getProjectHistory, logServerPageTiming } from "@/lib/api";
import {
  formatAddressLabel,
  formatCurrency,
  formatDate,
  formatEnumLabel,
  formatLocationQuality,
  formatNumber,
  formatPercent,
} from "@/lib/format";

export const revalidate = 120;

type PageProps = {
  params: Promise<{ id: string }>;
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function getSingle(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function locationExplanation(value: string) {
  if (value === "exact") {
    return "The current display point is treated as an exact project location.";
  }
  if (value === "approximate") {
    return "The display point is useful for nearby map browsing, but not treated as an exact footprint.";
  }
  if (value === "city-only") {
    return "The public map uses a city centroid fallback for this project because no stronger location is currently trusted.";
  }
  return "Location quality is still weak, so this project should be read primarily through its company and source context.";
}

export default async function ProjectDetailPage({ params, searchParams }: PageProps) {
  const startedAt = Date.now();
  const { id } = await params;
  const routeSearchParams = (await searchParams) ?? {};
  const returnTo = getSingle(routeSearchParams.return_to) ?? "/projects";
  const [projectResult, historyResult] = await Promise.all([getProjectDetail(id), getProjectHistory(id)]);

  if (projectResult.state === "error" || !projectResult.item) {
    notFound();
  }

  const project = projectResult.item;
  const history = historyResult.items;

  logServerPageTiming("/projects/[id]", startedAt, {
    project_id: id,
    history_items: history.length,
  });

  return (
    <div className="project-product-page">
      <section className="project-product-hero">
        <div className="project-product-hero-main">
          <div className="tag-row">
            <Link className="filter-reset" href={returnTo}>
              Back to map
            </Link>
            <Tag tone={project.location.locationQuality === "exact" ? "accent" : project.location.locationQuality === "unknown" ? "warning" : "default"}>
              {formatLocationQuality(project.location.locationQuality)}
            </Tag>
            <Tag>{project.classification.classificationConfidence}</Tag>
          </div>
          <div>
            <p className="eyebrow">Project research page</p>
            <h1 className="project-product-title">{project.identity.canonicalName}</h1>
          </div>
          <p className="project-product-subtitle">
            <Link className="inline-link" href={`/companies/${project.identity.company.id}`}>
              {project.identity.company.nameHe}
            </Link>
            {" · "}
            {project.location.city ?? "Unknown city"}
            {project.location.neighborhood ? ` · ${project.location.neighborhood}` : ""}
          </p>
          <div className="tag-row">
            <Tag>{formatEnumLabel(project.classification.projectBusinessType)}</Tag>
            <Tag>{formatEnumLabel(project.classification.governmentProgramType)}</Tag>
            <Tag>{formatEnumLabel(project.classification.projectUrbanRenewalType)}</Tag>
            <Tag>{project.classification.projectStatus ? formatEnumLabel(project.classification.projectStatus) : "Status n/a"}</Tag>
            <Tag>{project.classification.permitStatus ? formatEnumLabel(project.classification.permitStatus) : "Permit n/a"}</Tag>
          </div>
        </div>

        <aside className="project-product-hero-side">
          <div className="project-summary-stack">
            <div>
              <p className="eyebrow">Location quality</p>
              <h3>{formatLocationQuality(project.displayGeometry.locationQuality)}</h3>
            </div>
            <p className="panel-copy">{locationExplanation(project.displayGeometry.locationQuality)}</p>
            <div className="detail-list">
              <div>
                <strong>Display geometry</strong>
                <p className="panel-copy">{formatEnumLabel(project.displayGeometry.geometryType)}</p>
              </div>
              <div>
                <strong>Geometry source</strong>
                <p className="panel-copy">
                  {formatEnumLabel(project.displayGeometry.geometrySource)}
                  {project.displayGeometry.isManualOverride ? " · manual correction" : project.displayGeometry.isSourceDerived ? " · source-derived" : ""}
                </p>
              </div>
              <div>
                <strong>Address summary</strong>
                <p className="panel-copy">{project.displayGeometry.addressSummary ?? "City-level only"}</p>
              </div>
              <div>
                <strong>Latest snapshot</strong>
                <p className="panel-copy">{formatDate(project.latestSnapshot.snapshotDate)}</p>
              </div>
            </div>
          </div>
        </aside>
      </section>

      <section className="detail-grid">
        <Panel eyebrow="Location" title="Location block">
          <div className="detail-list">
            <div>
              <strong>City</strong>
              <p className="panel-copy">{project.location.city ?? "Not disclosed"}</p>
            </div>
            <div>
              <strong>Neighborhood</strong>
              <p className="panel-copy">{project.location.neighborhood ?? "Not disclosed"}</p>
            </div>
            <div>
              <strong>District</strong>
              <p className="panel-copy">{project.location.district ?? "Not disclosed"}</p>
            </div>
            <div>
              <strong>Location confidence</strong>
              <p className="panel-copy">{formatLocationQuality(project.location.locationConfidence)}</p>
            </div>
          </div>
        </Panel>

        <Panel eyebrow="Status" title="Classification and status">
          <div className="detail-list">
            <div>
              <strong>Business type</strong>
              <p className="panel-copy">{formatEnumLabel(project.classification.projectBusinessType)}</p>
            </div>
            <div>
              <strong>Government program</strong>
              <p className="panel-copy">{formatEnumLabel(project.classification.governmentProgramType)}</p>
            </div>
            <div>
              <strong>Urban renewal type</strong>
              <p className="panel-copy">{formatEnumLabel(project.classification.projectUrbanRenewalType)}</p>
            </div>
            <div>
              <strong>Project status</strong>
              <p className="panel-copy">{project.classification.projectStatus ? formatEnumLabel(project.classification.projectStatus) : "Not disclosed"}</p>
            </div>
            <div>
              <strong>Permit status</strong>
              <p className="panel-copy">{project.classification.permitStatus ? formatEnumLabel(project.classification.permitStatus) : "Not disclosed"}</p>
            </div>
            <div>
              <strong>Classification confidence</strong>
              <p className="panel-copy">{project.classification.classificationConfidence}</p>
            </div>
          </div>
        </Panel>
      </section>

      <Panel eyebrow="Key Metrics" title="Latest public metrics">
        <div className="project-metric-grid">
          <div className="project-metric-card">
            <strong>Total units</strong>
            <span>{formatNumber(project.latestSnapshot.totalUnits)}</span>
          </div>
          <div className="project-metric-card">
            <strong>Marketed units</strong>
            <span>{formatNumber(project.latestSnapshot.marketedUnits)}</span>
          </div>
          <div className="project-metric-card">
            <strong>Sold cumulative</strong>
            <span>{formatNumber(project.latestSnapshot.soldUnitsCumulative)}</span>
          </div>
          <div className="project-metric-card">
            <strong>Unsold units</strong>
            <span>{formatNumber(project.latestSnapshot.unsoldUnits)}</span>
          </div>
          <div className="project-metric-card">
            <strong>Avg price / sqm</strong>
            <span>{formatCurrency(project.latestSnapshot.avgPricePerSqmCumulative)}</span>
          </div>
          <div className="project-metric-card">
            <strong>Gross profit expected</strong>
            <span>{formatCurrency(project.latestSnapshot.grossProfitTotalExpected)}</span>
          </div>
          <div className="project-metric-card">
            <strong>Gross margin expected</strong>
            <span>{formatPercent(project.latestSnapshot.grossMarginExpectedPct)}</span>
          </div>
          <div className="project-metric-card">
            <strong>Sell-through rate</strong>
            <span>{formatPercent(project.derivedMetrics.sellThroughRate)}</span>
          </div>
        </div>
      </Panel>

      <section className="detail-grid">
        <Panel eyebrow="History" title="Snapshot and history summary">
          {historyResult.state === "error" ? (
            <div className="empty-state">
              <strong>Project history is temporarily unavailable.</strong>
              <p className="panel-copy">The rest of the product page stays available while the history route recovers.</p>
            </div>
          ) : history.length > 0 ? (
            <div className="timeline-list">
              {history.map((snapshot) => (
                <div key={snapshot.snapshotId} className="timeline-item">
                  <div className="timeline-item-header">
                    <strong>{formatDate(snapshot.snapshotDate)}</strong>
                    <div className="tag-row">
                      <Tag>{snapshot.projectStatus ? formatEnumLabel(snapshot.projectStatus) : "status n/a"}</Tag>
                      <Tag>{snapshot.permitStatus ? formatEnumLabel(snapshot.permitStatus) : "permit n/a"}</Tag>
                    </div>
                  </div>
                  <div className="detail-list">
                    <div>
                      <strong>Sold delta</strong>
                      <p className="panel-copy">
                        {formatNumber(snapshot.soldUnitsCumulative)}
                        {snapshot.soldUnitsDelta !== null ? ` (${snapshot.soldUnitsDelta >= 0 ? "+" : ""}${snapshot.soldUnitsDelta})` : ""}
                      </p>
                    </div>
                    <div>
                      <strong>Unsold delta</strong>
                      <p className="panel-copy">
                        {formatNumber(snapshot.unsoldUnits)}
                        {snapshot.unsoldUnitsDelta !== null ? ` (${snapshot.unsoldUnitsDelta >= 0 ? "+" : ""}${snapshot.unsoldUnitsDelta})` : ""}
                      </p>
                    </div>
                    <div>
                      <strong>Marketed</strong>
                      <p className="panel-copy">{formatNumber(snapshot.marketedUnits)}</p>
                    </div>
                    <div>
                      <strong>Avg price / sqm</strong>
                      <p className="panel-copy">{formatCurrency(snapshot.avgPricePerSqmCumulative)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <strong>No historical snapshots are available yet.</strong>
              <p className="panel-copy">This page still uses the latest public snapshot as its primary basis.</p>
            </div>
          )}
        </Panel>

        <Panel eyebrow="Sources" title="Sources and provenance">
          <div className="detail-list">
            <div>
              <strong>Source company</strong>
              <p className="panel-copy">{project.sourceQuality.sourceCompany}</p>
            </div>
            <div>
              <strong>Source report</strong>
              <p className="panel-copy">{project.sourceQuality.sourceReportName ?? "Not disclosed"}</p>
            </div>
            <div>
              <strong>Report period end</strong>
              <p className="panel-copy">{formatDate(project.sourceQuality.reportPeriodEnd)}</p>
            </div>
            <div>
              <strong>Published at</strong>
              <p className="panel-copy">{formatDate(project.sourceQuality.publishedAt)}</p>
            </div>
            <div>
              <strong>Confidence level</strong>
              <p className="panel-copy">{project.sourceQuality.confidenceLevel}</p>
            </div>
            <div>
              <strong>Source pages</strong>
              <p className="panel-copy">{project.sourceQuality.sourcePages ?? "Not disclosed"}</p>
            </div>
          </div>
          <div className="tag-row">
            <Tag>{`reported ${String(project.sourceQuality.valueOriginSummary.reported ?? 0)}`}</Tag>
            <Tag>{`inferred ${String(project.sourceQuality.valueOriginSummary.inferred ?? 0)}`}</Tag>
            <Tag>{`manual ${String(project.sourceQuality.valueOriginSummary.manual ?? 0)}`}</Tag>
            <Tag tone="warning">{`unknown ${String(project.sourceQuality.valueOriginSummary.unknown ?? 0)}`}</Tag>
          </div>
          {project.sourceQuality.sourceUrl ? (
            <a className="inline-link" href={project.sourceQuality.sourceUrl} rel="noreferrer" target="_blank">
              Open latest source report
            </a>
          ) : null}
          {project.sourceQuality.missingFields.length > 0 ? (
            <p className="panel-copy">
              Fields still null from source: {project.sourceQuality.missingFields.join(", ")}
            </p>
          ) : null}
        </Panel>
      </section>

      <section className="detail-grid">
        <Panel eyebrow="Addresses" title="Addresses and geocoding">
          {project.addresses.length > 0 ? (
            <div className="address-list">
              {project.addresses.map((address) => (
                <div key={address.id} className="address-card">
                  <strong>{formatAddressLabel(address)}</strong>
                  <p className="panel-copy">
                    {address.isPrimary ? "Primary address" : "Additional address"} · {formatLocationQuality(address.locationQuality)}
                  </p>
                  <p className="panel-copy">Display label: {address.normalizedDisplayAddress ?? "Not prepared yet"}</p>
                  <p className="panel-copy">
                    Geocoding: {[address.geocodingStatus, address.geocodingMethod ?? "no-method", address.geometrySource].join(" · ")}
                  </p>
                  {address.geocodingSourceLabel ? <p className="panel-copy">Source label: {address.geocodingSourceLabel}</p> : null}
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <strong>No project addresses are currently stored.</strong>
              <p className="panel-copy">This project remains discoverable through city-level research.</p>
            </div>
          )}
        </Panel>

        <Panel eyebrow="Raw Provenance" title="Field provenance table">
          {project.fieldProvenance.length > 0 ? (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>Normalized value</th>
                    <th>Origin</th>
                    <th>Confidence</th>
                    <th>Source page</th>
                  </tr>
                </thead>
                <tbody>
                  {project.fieldProvenance.map((row) => (
                    <tr key={`${row.fieldName}-${row.sourcePage ?? "na"}-${row.normalizedValue ?? "null"}`}>
                      <td>{row.fieldName}</td>
                      <td>{row.normalizedValue ?? row.rawValue ?? "Unknown"}</td>
                      <td>{formatEnumLabel(row.valueOriginType)}</td>
                      <td>{row.confidenceScore ?? "Not scored"}</td>
                      <td>{row.sourcePage ?? "Unknown"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <strong>No field-level provenance rows are available.</strong>
              <p className="panel-copy">The project still exposes a source summary above.</p>
            </div>
          )}
        </Panel>
      </section>
    </div>
  );
}
