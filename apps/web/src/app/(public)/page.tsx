import { FiltersPanel } from "@/components/dashboard/filters-panel";
import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { ProjectMapPanel } from "@/components/dashboard/project-map-panel";
import { ProjectTable } from "@/components/dashboard/project-table";
import { Tag } from "@/components/ui/tag";
import { filterGroups, homeKpis, placeholderProjectRows } from "@/lib/content";

export default function HomePage() {
  return (
    <>
      <section className="hero">
        <div className="hero-card content-stack">
          <div>
            <p className="eyebrow">Sprint 1 Foundation</p>
            <h2>Public exploration starts with a canonical residential project surface.</h2>
          </div>
          <p>
            This first phase keeps the public catalog, project filters, KPI framing, and map placeholder
            aligned with the schema-first product direction from the docs.
          </p>
          <div className="hero-actions">
            <Tag>Residential only</Tag>
            <Tag>Public/admin split</Tag>
            <Tag tone="warning">No Mapbox yet</Tag>
          </div>
        </div>
        <aside className="hero-aside content-stack">
          <div>
            <p className="eyebrow">Phase boundaries</p>
            <h3>What this release intentionally does not do</h3>
          </div>
          <p className="panel-copy">
            PDF parsing, real map rendering, and ingestion workflows are left out on purpose. The repo now
            has the structure those pieces can plug into without rework.
          </p>
        </aside>
      </section>

      <FiltersPanel
        title="Search and filter scaffold"
        description="Filter state is represented as a dedicated surface from the first sprint so URL synchronization and public API wiring can land without redesign."
        items={filterGroups}
      />

      <KpiGrid items={homeKpis} title="Public KPI scaffold" />

      <section className="two-column-grid">
        <ProjectTable rows={placeholderProjectRows} title="Latest public projects" />
        <ProjectMapPanel />
      </section>
    </>
  );
}
