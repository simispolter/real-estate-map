import Link from "next/link";
import { notFound } from "next/navigation";

import { Panel } from "@/components/ui/panel";
import { Tag } from "@/components/ui/tag";
import { getProjectDetail, getProjectHistory } from "@/lib/api";
import { formatAddressLabel, formatCurrency, formatDate, formatNumber, formatPercent } from "@/lib/format";

export const dynamic = "force-dynamic";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function ProjectDetailPage({ params }: PageProps) {
  const { id } = await params;
  const [projectResult, historyResult] = await Promise.all([getProjectDetail(id), getProjectHistory(id)]);

  if (projectResult.state === "error" || !projectResult.item) {
    notFound();
  }

  const project = projectResult.item;
  const history = historyResult.items;

  return (
    <>
      <Panel
        eyebrow="Project Detail"
        title={project.identity.canonicalName}
        description="Canonical public project view with classification, metrics, provenance, and historical snapshots."
        actions={
          <div className="tag-row">
            <Tag tone={project.location.locationQuality === "exact" ? "accent" : "default"}>
              {project.location.locationQuality}
            </Tag>
            <Tag>{project.classification.classificationConfidence}</Tag>
          </div>
        }
      >
        <div className="detail-grid">
          <div className="detail-card section-stack">
            <div>
              <p className="eyebrow">Identity</p>
              <h3>{project.identity.canonicalName}</h3>
            </div>
            <p className="panel-copy">
              <Link className="inline-link" href={`/companies/${project.identity.company.id}`}>
                {project.identity.company.nameHe}
              </Link>
            </p>
            <div className="tag-row">
              <Tag>{project.location.city ?? "Unknown city"}</Tag>
              {project.location.neighborhood ? <Tag>{project.location.neighborhood}</Tag> : null}
            </div>
          </div>

          <div className="detail-card section-stack">
            <div>
              <p className="eyebrow">Source Basis</p>
              <h3>{project.sourceQuality.sourceReportName ?? "Latest public report"}</h3>
            </div>
            <p className="panel-copy">
              Report period end: {formatDate(project.sourceQuality.reportPeriodEnd)}
            </p>
            <p className="panel-copy">
              Published: {formatDate(project.sourceQuality.publishedAt)}
            </p>
            {project.sourceQuality.sourceUrl ? (
              <a className="inline-link" href={project.sourceQuality.sourceUrl} rel="noreferrer" target="_blank">
                Open source report
              </a>
            ) : null}
          </div>
        </div>
      </Panel>

      <section className="detail-grid">
        <Panel eyebrow="Classification" title="Project classification block">
          <div className="detail-list">
            <div>
              <strong>Business type</strong>
              <p className="panel-copy">{project.classification.projectBusinessType}</p>
            </div>
            <div>
              <strong>Government program</strong>
              <p className="panel-copy">{project.classification.governmentProgramType}</p>
            </div>
            <div>
              <strong>Urban renewal type</strong>
              <p className="panel-copy">{project.classification.projectUrbanRenewalType}</p>
            </div>
            <div>
              <strong>Project status</strong>
              <p className="panel-copy">{project.classification.projectStatus ?? "Not disclosed"}</p>
            </div>
            <div>
              <strong>Permit status</strong>
              <p className="panel-copy">{project.classification.permitStatus ?? "Not disclosed"}</p>
            </div>
            <div>
              <strong>Location confidence</strong>
              <p className="panel-copy">{project.location.locationConfidence}</p>
            </div>
            <div>
              <strong>Address summary</strong>
              <p className="panel-copy">{project.location.addressSummary ?? "City-level only"}</p>
            </div>
          </div>
        </Panel>

        <Panel eyebrow="Metrics" title="Key metrics block">
          <div className="stats-grid">
            <div>
              <strong>Total units</strong>
              <p className="panel-copy">{formatNumber(project.latestSnapshot.totalUnits)}</p>
            </div>
            <div>
              <strong>Marketed units</strong>
              <p className="panel-copy">{formatNumber(project.latestSnapshot.marketedUnits)}</p>
            </div>
            <div>
              <strong>Sold units cumulative</strong>
              <p className="panel-copy">{formatNumber(project.latestSnapshot.soldUnitsCumulative)}</p>
            </div>
            <div>
              <strong>Unsold units</strong>
              <p className="panel-copy">{formatNumber(project.latestSnapshot.unsoldUnits)}</p>
            </div>
            <div>
              <strong>Average price per sqm</strong>
              <p className="panel-copy">{formatCurrency(project.latestSnapshot.avgPricePerSqmCumulative)}</p>
            </div>
            <div>
              <strong>Gross profit expected</strong>
              <p className="panel-copy">{formatCurrency(project.latestSnapshot.grossProfitTotalExpected)}</p>
            </div>
            <div>
              <strong>Gross margin expected</strong>
              <p className="panel-copy">{formatPercent(project.latestSnapshot.grossMarginExpectedPct)}</p>
            </div>
            <div>
              <strong>Sell-through rate</strong>
              <p className="panel-copy">{formatPercent(project.derivedMetrics.sellThroughRate)}</p>
            </div>
            <div>
              <strong>Latest snapshot date</strong>
              <p className="panel-copy">{formatDate(project.latestSnapshot.snapshotDate)}</p>
            </div>
          </div>
        </Panel>
      </section>

      <section className="detail-grid">
        <Panel eyebrow="Spatial" title="Location model">
          <div className="detail-list">
            <div>
              <strong>Display geometry</strong>
              <p className="panel-copy">{project.displayGeometry.geometryType}</p>
            </div>
            <div>
              <strong>Geometry source</strong>
              <p className="panel-copy">{project.displayGeometry.geometrySource}</p>
            </div>
            <div>
              <strong>Location quality</strong>
              <p className="panel-copy">{project.displayGeometry.locationQuality}</p>
            </div>
            <div>
              <strong>Map center</strong>
              <p className="panel-copy">
                {project.displayGeometry.centerLat !== null && project.displayGeometry.centerLng !== null
                  ? `${project.displayGeometry.centerLat}, ${project.displayGeometry.centerLng}`
                  : "No coordinates"}
              </p>
            </div>
          </div>
          {project.displayGeometry.note ? (
            <p className="panel-copy">Note: {project.displayGeometry.note}</p>
          ) : null}
        </Panel>

        <Panel eyebrow="Addresses" title="Project addresses">
          {project.addresses.length > 0 ? (
            <div className="address-list">
              {project.addresses.map((address) => (
                <div key={address.id} className="address-card">
                  <strong>{formatAddressLabel(address)}</strong>
                  <p className="panel-copy">
                    {address.isPrimary ? "Primary address" : "Additional address"} | {address.locationQuality}
                  </p>
                  <p className="panel-copy">Normalized: {address.normalizedAddressText ?? "Not normalized yet"}</p>
                  <p className="panel-copy">
                    Coordinates:{" "}
                    {address.lat !== null && address.lng !== null
                      ? `${address.lat}, ${address.lng}`
                      : "City-level only"}
                  </p>
                  <p className="panel-copy">
                    Geocoding: {[address.geocodingStatus, address.geometrySource].join(" | ")}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <strong>No project addresses are currently stored.</strong>
              <p className="panel-copy">This project is still available through city-level research.</p>
            </div>
          )}
        </Panel>

        <Panel eyebrow="Provenance" title="Provenance summary block">
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
            <Tag>{`reported: ${String(project.sourceQuality.valueOriginSummary.reported ?? 0)}`}</Tag>
            <Tag>{`inferred: ${String(project.sourceQuality.valueOriginSummary.inferred ?? 0)}`}</Tag>
            <Tag tone="warning">{`unknown: ${String(project.sourceQuality.valueOriginSummary.unknown ?? 0)}`}</Tag>
          </div>
          {project.sourceQuality.missingFields.length > 0 ? (
            <p className="panel-copy">
              Missing fields left null from source: {project.sourceQuality.missingFields.join(", ")}
            </p>
          ) : null}
        </Panel>
      </section>

      <Panel eyebrow="History" title="Project history timeline">
        {historyResult.state === "error" ? (
          <div className="empty-state">
            <strong>Project history is temporarily unavailable.</strong>
            <p className="panel-copy">The detail page remains usable while the history route recovers.</p>
          </div>
        ) : history.length > 0 ? (
          <div className="timeline-list">
            {history.map((snapshot) => (
              <div key={snapshot.snapshotId} className="timeline-item">
                <div className="timeline-item-header">
                  <strong>{formatDate(snapshot.snapshotDate)}</strong>
                  <div className="tag-row">
                    <Tag>{snapshot.projectStatus ?? "status n/a"}</Tag>
                    <Tag>{snapshot.permitStatus ?? "permit n/a"}</Tag>
                  </div>
                </div>
                <div className="detail-list">
                  <div>
                    <strong>Sold units</strong>
                    <p className="panel-copy">
                      {formatNumber(snapshot.soldUnitsCumulative)}
                      {snapshot.soldUnitsDelta !== null ? ` (${snapshot.soldUnitsDelta >= 0 ? "+" : ""}${snapshot.soldUnitsDelta})` : ""}
                    </p>
                  </div>
                  <div>
                    <strong>Unsold units</strong>
                    <p className="panel-copy">
                      {formatNumber(snapshot.unsoldUnits)}
                      {snapshot.unsoldUnitsDelta !== null ? ` (${snapshot.unsoldUnitsDelta >= 0 ? "+" : ""}${snapshot.unsoldUnitsDelta})` : ""}
                    </p>
                  </div>
                  <div>
                    <strong>Marketed units</strong>
                    <p className="panel-copy">{formatNumber(snapshot.marketedUnits)}</p>
                  </div>
                  <div>
                    <strong>Average price per sqm</strong>
                    <p className="panel-copy">{formatCurrency(snapshot.avgPricePerSqmCumulative)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <strong>No historical snapshots are available for this project.</strong>
            <p className="panel-copy">The project still renders from its latest public snapshot.</p>
          </div>
        )}
      </Panel>

      <Panel eyebrow="Raw Fields" title="Field provenance table">
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
                    <td>{row.valueOriginType}</td>
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
            <p className="panel-copy">The project still exposes source summary metadata above.</p>
          </div>
        )}
      </Panel>
    </>
  );
}
