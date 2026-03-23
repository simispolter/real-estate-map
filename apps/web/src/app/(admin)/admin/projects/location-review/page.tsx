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
        eyebrow="בקרת מיקום"
        title="תור פרויקטים לטיוב מיקום"
        description="עברו על פרויקטים עם מיקום חלש, השלימו כתובת או גוש / חלקה, ופתחו את מסך הפרויקט למיקום מדויק יותר."
      >
        <form className="admin-form-grid" method="get">
          <label className="filter-field">
            <span>חברה</span>
            <select defaultValue={filters.company_id ?? ""} name="company_id">
              <option value="">כל החברות</option>
              {companiesResult.items.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.nameHe}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span>עיר</span>
            <input defaultValue={filters.city ?? ""} name="city" placeholder="סינון לפי עיר" />
          </label>
          <label className="filter-field">
            <span>איכות מיקום</span>
            <input defaultValue={filters.location_confidence ?? ""} name="location_confidence" placeholder="למשל city_only" />
          </label>
          <label className="filter-field">
            <span>סטטוס backfill</span>
            <input defaultValue={filters.backfill_status ?? ""} name="backfill_status" placeholder="למשל historical_backfill" />
          </label>
          <label className="filter-field">
            <span>רק פריטים עם חוסרים</span>
            <select defaultValue={filters.missing_fields ?? ""} name="missing_fields">
              <option value="">הכול</option>
              <option value="yes">כן</option>
            </select>
          </label>
          <label className="panel-copy">
            <input defaultChecked={filters.include_all === "true"} name="include_all" type="checkbox" value="true" /> לכלול גם פרויקטים עם מיקום מדויק / בקירוב
          </label>
          <div className="form-actions">
            <button className="primary-button" type="submit">
              החל מסננים
            </button>
            <a className="secondary-button" href="/admin/projects/location-review">
              ניקוי
            </a>
            <a
              className="secondary-button"
              href={`${exportBaseUrl}/api/v1/admin/coverage/export?kind=location_missing${exportQuery ? `&${exportQuery}` : ""}`}
            >
              ייצוא חוסרי מיקום
            </a>
          </div>
        </form>
      </Panel>

      {reviewResult.state === "error" || !reviewResult.item ? (
        <Panel eyebrow="סטטוס" title="נתוני תור המיקומים לא זמינים כרגע">
          <p className="panel-copy">לא התקבל כרגע payload תקין מהשרת עבור תור בקרת המיקום.</p>
        </Panel>
      ) : (
        <>
          <section className="stats-grid">
            <div>
              <strong>{reviewResult.item.summary.totalItems}</strong>
              <span>פריטים בתור</span>
            </div>
            <div>
              <strong>{reviewResult.item.summary.cityOnly}</strong>
              <span>ברמת עיר בלבד</span>
            </div>
            <div>
              <strong>{reviewResult.item.summary.unknown}</strong>
              <span>לא ידוע</span>
            </div>
            <div>
              <strong>{reviewResult.item.summary.geocodingReady}</strong>
              <span>מוכנים לאיתור</span>
            </div>
          </section>
          <AdminLocationReviewDashboard initialItems={reviewResult.item.items} />
        </>
      )}
    </>
  );
}
