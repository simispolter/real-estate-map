import { CompanyTable } from "@/components/dashboard/company-table";
import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { Panel } from "@/components/ui/panel";
import { getCompanies, getFiltersMetadata } from "@/lib/api";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function getSingle(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function CompaniesPage({ searchParams }: PageProps) {
  const params = (await searchParams) ?? {};
  const filters = {
    q: getSingle(params.q),
    city: getSingle(params.city),
    sort_by: getSingle(params.sort_by) ?? "project_count",
  };
  const [{ items, state }, metadata] = await Promise.all([getCompanies(filters), getFiltersMetadata()]);
  const safeItems = Array.isArray(items) ? items : [];
  const totalProjects = safeItems.reduce((sum, company) => sum + company.projectCount, 0);
  const totalCities = safeItems.reduce((sum, company) => sum + company.cityCount, 0);
  const knownUnsoldUnits = safeItems.reduce((sum, company) => sum + (company.knownUnsoldUnits ?? 0), 0);

  return (
    <>
      <Panel
        eyebrow="Companies"
        title="Public company coverage"
        description="This page now supports real company exploration, linkable detail pages, and lightweight research filtering."
      >
        <form action="/companies" className="filter-form" method="GET">
          <div className="filter-grid">
            <label className="filter-item filter-field">
              <span>Company name</span>
              <input defaultValue={filters.q ?? ""} name="q" placeholder="Search developer" type="text" />
            </label>
            <label className="filter-item filter-field">
              <span>City</span>
              <select defaultValue={filters.city ?? ""} name="city">
                <option value="">All</option>
                {metadata.cities.map((city) => (
                  <option key={city} value={city}>
                    {city}
                  </option>
                ))}
              </select>
            </label>
            <label className="filter-item filter-field">
              <span>Sort by</span>
              <select defaultValue={filters.sort_by} name="sort_by">
                <option value="project_count">Project count</option>
                <option value="city_count">City count</option>
                <option value="latest_report">Latest report</option>
              </select>
            </label>
          </div>
          <div className="filter-actions">
            <button type="submit">Apply filters</button>
            <a href="/companies" className="filter-reset">
              Reset
            </a>
          </div>
        </form>
      </Panel>

      {state === "error" ? (
        <Panel eyebrow="Data Status" title="Company data is temporarily unavailable" description="The page rendered safely, but the company API did not return a usable payload.">
          <p className="panel-copy">The route remains available while the backend recovers.</p>
        </Panel>
      ) : null}

      <KpiGrid
        title="Company summary"
        items={[
          { id: "companies", label: "Covered developers", value: String(safeItems.length), note: "The public coverage set after filters are applied." },
          { id: "projects", label: "Visible projects", value: String(totalProjects), note: "Counted from company-linked project masters." },
          { id: "cities", label: "Company-city coverage", value: String(totalCities), note: "Useful for spotting geographic concentration." },
          { id: "unsold", label: "Known unsold units", value: String(knownUnsoldUnits), note: "Summed only from known company-level project metrics." },
        ]}
      />

      {state === "empty" ? (
        <Panel eyebrow="No Matches" title="No companies matched the current view" description="The route is healthy, but the filter combination returned no company rows.">
          <p className="panel-copy">Reset filters to restore the full seeded company set.</p>
        </Panel>
      ) : null}

      <section className="company-grid">
        <CompanyTable companies={safeItems} />
        <Panel
          eyebrow="Coverage Notes"
          title="What this view is optimized for"
          description="This page is meant for fast scanning, while deeper provenance and project mix analysis live on the company detail pages."
        >
          <p className="panel-copy">
            Open a company row to inspect its latest report basis, city spread, business-type distribution, and linked project catalog.
          </p>
        </Panel>
      </section>
    </>
  );
}
