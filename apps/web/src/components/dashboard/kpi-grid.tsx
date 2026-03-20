import type { KpiDefinition } from "@real-estat-map/shared";

export function KpiGrid({
  items,
  title,
}: {
  items: KpiDefinition[];
  title: string;
}) {
  return (
    <section className="content-stack">
      <div className="section-heading">
        <h2>{title}</h2>
        <p className="panel-copy">
          KPI placeholders are intentionally wired to the future canonical snapshot layer instead of
          hardcoded demo numbers.
        </p>
      </div>
      <div className="kpi-grid">
        {items.map((item) => (
          <article key={item.id} className="kpi-card">
            <p className="eyebrow">{item.label}</p>
            <strong>{item.value}</strong>
            {item.note ? <p className="panel-copy">{item.note}</p> : null}
          </article>
        ))}
      </div>
    </section>
  );
}
