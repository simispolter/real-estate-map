import type { CompanyListItem } from "@real-estat-map/shared";
import Link from "next/link";

import { Panel } from "@/components/ui/panel";

export function CompanyTable({ companies }: { companies?: CompanyListItem[] | null }) {
  const safeCompanies = Array.isArray(companies) ? companies : [];

  return (
    <Panel
      eyebrow="Coverage"
      title="Developer coverage"
      description="The seeded company list reflects the five public residential developers selected for Phase 2."
    >
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Company</th>
              <th>Ticker</th>
              <th>Projects</th>
              <th>Cities</th>
              <th>Latest period</th>
            </tr>
          </thead>
          <tbody>
            {safeCompanies.length > 0 ? (
              safeCompanies.map((company) => (
                <tr key={company.id}>
                  <td>
                    <Link href={`/companies/${company.id}`}>{company.nameHe}</Link>
                  </td>
                  <td>{company.ticker ?? "N/A"}</td>
                  <td>{company.projectCount}</td>
                  <td>{company.cityCount}</td>
                  <td>{company.latestReportPeriodEnd ?? "Not disclosed"}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} className="empty-table">
                  No company coverage rows are available right now.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
