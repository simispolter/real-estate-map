import { AdminLocationReviewDashboard } from "@/components/admin/admin-location-review-dashboard";
import { Panel } from "@/components/ui/panel";
import { getAdminLocationReview, getCompanies } from "@/lib/api";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function single(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function AdminProjectLocationReviewPage({ searchParams }: PageProps) {
  const params = (await searchParams) ?? {};
  const filters = {
    company_id: single(params.company_id),
    city: single(params.city),
    location_confidence: single(params.location_confidence),
    backfill_status: single(params.backfill_status),
    missing_fields: single(params.missing_fields),
    include_all: single(params.include_all),
  };
  const [reviewResult, companiesResult] = await Promise.all([getAdminLocationReview(filters), getCompanies()]);
  const exportBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const exportQuery = new URLSearchParams(
    Object.fromEntries(
      Object.entries({
        company_id: filters.company_id,
        city: filters.city,
        location_confidence: filters.location_confidence,
        backfill_status: filters.backfill_status,
      }).filter(([, value]) => Boolean(value)),
    ) as Record<string, string>,
  ).toString();

  return (
    <>
      <Panel
        eyebrow="Location Review"
        title="Projects needing location hardening"
        description="Route city-only and unknown projects into address normalization, geocoding, and manual geometry correction without leaving the canonical project workflow."
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
            <input defaultValue={filters.location_confidence ?? ""} name="location_confidence" placeholder="city_only or unknown" />
          </label>
          <label className="filter-field">
            <span>Backfill status</span>
            <input defaultValue={filters.backfill_status ?? ""} name="backfill_status" placeholder="historical_backfill, complete" />
          </label>
          <label className="filter-field">
            <span>Only rows missing fields</span>
            <select defaultValue={filters.missing_fields ?? ""} name="missing_fields">
              <option value="">All</option>
              <option value="yes">Yes</option>
            </select>
          </label>
          <label className="panel-copy">
            <input defaultChecked={filters.include_all === "true"} name="include_all" type="checkbox" value="true" /> Include exact / approximate projects too
          </label>
          <div className="form-actions">
            <button className="primary-button" type="submit">
              Apply filters
            </button>
            <a className="secondary-button" href="/admin/projects/location-review">
              Clear
            </a>
            <a
              className="secondary-button"
              href={`${exportBaseUrl}/api/v1/admin/coverage/export?kind=location_missing${exportQuery ? `&${exportQuery}` : ""}`}
            >
              Export missing location
            </a>
          </div>
        </form>
      </Panel>

      {reviewResult.state === "error" || !reviewResult.item ? (
        <Panel eyebrow="Status" title="Location review data is temporarily unavailable">
          <p className="panel-copy">The location queue endpoint did not return a usable payload right now.</p>
        </Panel>
      ) : (
        <>
          <section className="stats-grid">
            <div>
              <strong>{reviewResult.item.summary.totalItems}</strong>
              <span>Queue items</span>
            </div>
            <div>
              <strong>{reviewResult.item.summary.cityOnly}</strong>
              <span>City-only</span>
            </div>
            <div>
              <strong>{reviewResult.item.summary.unknown}</strong>
              <span>Unknown</span>
            </div>
            <div>
              <strong>{reviewResult.item.summary.geocodingReady}</strong>
              <span>Geocoding-ready</span>
            </div>
          </section>
          <AdminLocationReviewDashboard initialItems={reviewResult.item.items} />
        </>
      )}
    </>
  );
}
