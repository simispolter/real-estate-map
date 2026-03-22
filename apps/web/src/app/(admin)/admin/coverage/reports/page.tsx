import { AdminCoverageReportsPanel } from "@/components/admin/admin-coverage-reports-panel";
import { Panel } from "@/components/ui/panel";
import { getAdminCoverageReports, getCompanies } from "@/lib/api";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function single(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function AdminCoverageReportsPage({ searchParams }: PageProps) {
  const params = (await searchParams) ?? {};
  const filters = {
    company_id: single(params.company_id),
    ingestion_status: single(params.ingestion_status),
    scope: single(params.scope),
    published: single(params.published),
  };
  const [reportsResult, companiesResult] = await Promise.all([getAdminCoverageReports(filters), getCompanies()]);
  const exportBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  return (
    <>
      <Panel
        eyebrow="Coverage Reports"
        title="Report coverage and publication status"
        description="Track which reports are in scope, which have been ingested, and which have actually created or updated canonical project snapshots."
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
            <span>Ingestion status</span>
            <input defaultValue={filters.ingestion_status ?? ""} name="ingestion_status" placeholder="draft, in_review, published" />
          </label>
          <label className="filter-field">
            <span>Scope</span>
            <select defaultValue={filters.scope ?? ""} name="scope">
              <option value="">All</option>
              <option value="in_scope">In scope</option>
              <option value="out_of_scope">Out of scope</option>
            </select>
          </label>
          <label className="filter-field">
            <span>Published into canonical</span>
            <select defaultValue={filters.published ?? ""} name="published">
              <option value="">All</option>
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </select>
          </label>
          <div className="form-actions">
            <button className="primary-button" type="submit">
              Apply filters
            </button>
            <a className="secondary-button" href="/admin/coverage/reports">
              Clear
            </a>
            <a className="secondary-button" href={`${exportBaseUrl}/api/v1/admin/coverage/export?kind=reports`}>
              Export CSV
            </a>
          </div>
        </form>
      </Panel>

      {reportsResult.state === "error" ? (
        <Panel eyebrow="Status" title="Coverage reports are temporarily unavailable">
          <p className="panel-copy">The report coverage endpoint did not return a usable payload right now.</p>
        </Panel>
      ) : (
        <AdminCoverageReportsPanel initialItems={reportsResult.items} />
      )}
    </>
  );
}
