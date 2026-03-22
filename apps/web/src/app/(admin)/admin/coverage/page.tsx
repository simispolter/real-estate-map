import Link from "next/link";

import { Panel } from "@/components/ui/panel";
import { getAdminCoverage } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AdminCoverageOverviewPage() {
  const result = await getAdminCoverage();

  return (
    <>
      <Panel
        eyebrow="Coverage"
        title="Coverage operations"
        description="Use the coverage workspace to expand company/report coverage, identify backfill gaps, and route location cleanup into the canonical project editor."
      />

      {result.state === "error" || !result.item ? (
        <Panel eyebrow="Status" title="Coverage data is temporarily unavailable">
          <p className="panel-copy">The overview is live, but the coverage dashboard payload could not be loaded right now.</p>
        </Panel>
      ) : (
        <section className="admin-grid">
          <Panel eyebrow="Companies" title="Company registry">
            <p className="panel-copy">
              {result.item.summary.companiesInScope} in-scope companies, {result.item.summary.companiesMissingLatestReport} missing the latest registered report.
            </p>
            <Link className="inline-link" href="/admin/coverage/companies">
              Open company coverage
            </Link>
          </Panel>
          <Panel eyebrow="Reports" title="Report coverage">
            <p className="panel-copy">
              {result.item.summary.reportsRegistered} reports registered, {result.item.summary.reportsPublishedIntoCanonical} already linked into canonical snapshots.
            </p>
            <Link className="inline-link" href="/admin/coverage/reports">
              Open report coverage
            </Link>
          </Panel>
          <Panel eyebrow="Gaps" title="Backfill gaps">
            <p className="panel-copy">
              {result.item.summary.projectsMissingKeyFields} projects still miss key fields, and {result.item.summary.projectsCityOnlyLocation} remain city-only or unknown on location.
            </p>
            <Link className="inline-link" href="/admin/coverage/gaps">
              Open coverage gaps
            </Link>
          </Panel>
        </section>
      )}
    </>
  );
}
