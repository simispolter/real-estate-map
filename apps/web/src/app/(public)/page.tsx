import { FiltersPanel } from "@/components/dashboard/filters-panel";
import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { ProjectMapPanel } from "@/components/dashboard/project-map-panel";
import { ProjectTable } from "@/components/dashboard/project-table";
import { Tag } from "@/components/ui/tag";
import { getFiltersMetadata, getHomeKpis, getMapExternalLayers, getMapLayers, getMapProjects, getProjects } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [kpis, filters, projects, mapResults, mapLayers, mapExternalLayers] = await Promise.all([
    getHomeKpis(),
    getFiltersMetadata(),
    getProjects({ page_size: "6" }),
    getMapProjects({}),
    getMapLayers(),
    getMapExternalLayers([], {}),
  ]);
  const filterFields = [
    {
      label: "City",
      name: "city",
      options: filters.cities.map((city) => ({ label: city, value: city })),
    },
    {
      label: "Company",
      name: "company_id",
      options: filters.companies
        .filter((company) => company.id)
        .map((company) => ({ label: company.label, value: company.id as string })),
    },
    {
      label: "Project business type",
      name: "project_business_type",
      options: filters.projectBusinessTypes.map((value) => ({ label: value, value })),
    },
  ];

  return (
    <>
      <section className="hero">
        <div className="hero-card content-stack">
          <div>
            <p className="eyebrow">Sprint 1 Phase 2</p>
            <h2>Public exploration now runs on a real residential seed from public company reports.</h2>
          </div>
          <p>
            The public workspace now reads sourced residential project data for five Israeli public
            developers, with provenance preserved for the fields we publish and nulls left intact when the
            report is silent.
          </p>
          <div className="hero-actions">
            <Tag>Residential only</Tag>
            <Tag>Real public data</Tag>
            <Tag tone="warning">No PDF parser yet</Tag>
          </div>
        </div>
        <aside className="hero-aside content-stack">
          <div>
            <p className="eyebrow">Phase boundaries</p>
            <h3>What this release intentionally does not do</h3>
          </div>
          <p className="panel-copy">
            PDF parsing, automated ingestion, authentication, and real map rendering are still deferred on
            purpose. This slice proves the real schema, real API, real DB, and public UI can all work
            together now.
          </p>
        </aside>
      </section>

      <FiltersPanel
        action="/projects"
        title="Public search surface"
        description="These controls already mirror the public API query surface and submit directly into the live `/projects` route."
        fields={filterFields}
        resetHref="/"
      />

      <KpiGrid items={kpis} title="Public KPI view" />

      <section className="two-column-grid">
        <ProjectTable rows={projects.items} title="Latest public projects" />
        <ProjectMapPanel
          selectedLayerIds={[]}
          state={mapResults.state}
          mapData={mapResults.item}
          layers={mapLayers.items}
          externalLayers={mapExternalLayers.item}
        />
      </section>
    </>
  );
}
