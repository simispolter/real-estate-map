import type { KpiDefinition } from "@real-estat-map/shared";

export function KpiGrid({
  items,
  title,
}: {
  items?: KpiDefinition[] | null;
  title: string;
}) {
  const safeItems = Array.isArray(items) ? items : [];

  return (
    <section className="content-stack">
      <div className="section-heading">
        <h2>{title}</h2>
        <p className="panel-copy">
          KPI placeholders are intentionally wired to the future canonical snapshot layer instead of
          hardcoded demo numbers.
        </p>
      </div>
      {safeItems.length > 0 ? (
        <div className="kpi-grid">
          {safeItems.map((item) => (
            <article key={item.id} className="kpi-card">
              <p className="eyebrow">{item.label}</p>
              <strong>{item.value}</strong>
              {item.note ? <p className="panel-copy">{item.note}</p> : null}
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <strong>No KPI data is available yet.</strong>
          <p className="panel-copy">The page is still healthy, but the upstream data did not produce KPI cards.</p>
        </div>
      )}
    </section>
  );
}
