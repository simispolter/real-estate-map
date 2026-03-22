import Link from "next/link";

import { AdminProjectCreatePanel } from "@/components/admin/admin-project-create-panel";
import { Panel } from "@/components/ui/panel";
import { Tag } from "@/components/ui/tag";
import { getAdminProjects, getCompanies, getFiltersMetadata } from "@/lib/api";
import { formatDate } from "@/lib/format";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function single(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function AdminProjectsPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const filters = {
    q: single(params.q),
    company_id: single(params.company_id),
    city: single(params.city),
    project_business_type: single(params.project_business_type),
    government_program_type: single(params.government_program_type),
    project_urban_renewal_type: single(params.project_urban_renewal_type),
    visibility: single(params.visibility),
    location_confidence: single(params.location_confidence),
    sort_by: single(params.sort_by),
  };

  const [{ items, state }, { items: companies }, metadata] = await Promise.all([
    getAdminProjects(filters),
    getCompanies(),
    getFiltersMetadata(),
  ]);

  return (
    <>
      <Panel
        eyebrow="Admin Projects"
        title="Canonical project workspace"
        description="Projects are now the core admin entity. Create canonical projects directly, review existing records, and jump into snapshots, provenance, intake links, and sources from one place."
      >
        <div className="tag-row">
          <Tag>project-first</Tag>
          <Tag tone="warning">no auth yet</Tag>
          <Tag>placeholder reviewer</Tag>
        </div>
      </Panel>

      <Panel eyebrow="Filters" title="Project search and queue controls">
        <form className="admin-form-grid" method="get">
          <label className="filter-field">
            <span>Search</span>
            <input defaultValue={filters.q ?? ""} name="q" placeholder="Canonical name, alias, company, city, address" />
          </label>
          <label className="filter-field">
            <span>Company</span>
            <select defaultValue={filters.company_id ?? ""} name="company_id">
              <option value="">All companies</option>
              {metadata.companies.map((company) => (
                <option key={company.id ?? company.label} value={company.id ?? ""}>
                  {company.label}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>City</span>
            <select defaultValue={filters.city ?? ""} name="city">
              <option value="">All cities</option>
              {metadata.cities.map((city) => (
                <option key={city} value={city}>
                  {city}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Business type</span>
            <select defaultValue={filters.project_business_type ?? ""} name="project_business_type">
              <option value="">All</option>
              {metadata.projectBusinessTypes.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Government program</span>
            <select defaultValue={filters.government_program_type ?? ""} name="government_program_type">
              <option value="">All</option>
              {metadata.governmentProgramTypes.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Urban renewal</span>
            <select defaultValue={filters.project_urban_renewal_type ?? ""} name="project_urban_renewal_type">
              <option value="">All</option>
              {metadata.projectUrbanRenewalTypes.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>Visibility</span>
            <select defaultValue={filters.visibility ?? ""} name="visibility">
              <option value="">All</option>
              <option value="public">Public</option>
              <option value="internal">Internal only</option>
            </select>
          </label>
          <label className="filter-field">
            <span>Location confidence</span>
            <input defaultValue={filters.location_confidence ?? ""} name="location_confidence" placeholder="exact, approximate, city_only, unknown" />
          </label>
          <label className="filter-field">
            <span>Sort by</span>
            <select defaultValue={filters.sort_by ?? "latest_snapshot"} name="sort_by">
              <option value="latest_snapshot">Latest snapshot</option>
              <option value="canonical_name">Canonical name</option>
              <option value="company">Company</option>
              <option value="city">City</option>
              <option value="source_count">Source count</option>
              <option value="address_count">Address count</option>
            </select>
          </label>
          <div className="form-actions">
            <button className="primary-button" type="submit">
              Apply filters
            </button>
            <Link className="secondary-button" href="/admin/projects">
              Clear
            </Link>
            <Link className="secondary-button" href="/admin/projects/location-review">
              Location review
            </Link>
          </div>
        </form>
      </Panel>

      <AdminProjectCreatePanel companies={companies} />

      {state === "error" ? (
        <Panel eyebrow="Status" title="Admin project data is temporarily unavailable">
          <p className="panel-copy">The project workspace is live, but the canonical project API did not return a usable payload.</p>
        </Panel>
      ) : null}

      <Panel eyebrow="Canonical Projects" title="Project management index">
        {items.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Company</th>
                  <th>City</th>
                  <th>Classification</th>
                  <th>Status</th>
                  <th>Location</th>
                  <th>Sources</th>
                  <th>Addresses</th>
                  <th>Visibility</th>
                  <th>Latest snapshot</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <Link href={`/admin/projects/${item.id}`}>{item.canonicalName}</Link>
                    </td>
                    <td>{item.company.nameHe}</td>
                    <td>{item.city ?? "Unknown"}</td>
                    <td>
                      <div className="stacked-cell">
                        <span>{item.projectBusinessType}</span>
                        <span className="muted-copy">
                          {[item.governmentProgramType, item.projectUrbanRenewalType].join(" | ")}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div className="stacked-cell">
                        <span>{item.projectStatus ?? "Unknown"}</span>
                        <span className="muted-copy">{item.permitStatus ?? "No permit status"}</span>
                      </div>
                    </td>
                    <td>{item.locationConfidence}</td>
                    <td>{item.sourceCount}</td>
                    <td>{item.addressCount}</td>
                    <td>
                      <div className="stacked-cell">
                        <span>{item.isPubliclyVisible ? "public" : "internal"}</span>
                        {item.sourceConflictFlag ? <Tag tone="warning">conflict</Tag> : null}
                      </div>
                    </td>
                    <td>{formatDate(item.latestSnapshotDate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <strong>No canonical projects matched this view.</strong>
            <p className="panel-copy">Adjust the filters or create a new project directly from this page.</p>
          </div>
        )}
      </Panel>
    </>
  );
}
