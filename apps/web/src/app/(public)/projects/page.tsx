import { FiltersPanel } from "@/components/dashboard/filters-panel";
import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { ProjectMapPanel } from "@/components/dashboard/project-map-panel";
import { ProjectTable } from "@/components/dashboard/project-table";
import { Panel } from "@/components/ui/panel";
import { filterGroups, homeKpis, placeholderProjectRows } from "@/lib/content";

export default function ProjectsPage() {
  return (
    <>
      <Panel
        eyebrow="Projects"
        title="Residential project catalog"
        description="This page is reserved for the paginated public project list defined in the API contract. The current implementation keeps the production route, layout, and component contract in place."
      >
        <p className="panel-copy">
          Future work will bind this screen to the versioned project list, detail, and history endpoints.
        </p>
      </Panel>

      <FiltersPanel
        title="Project filters"
        description="The filters mirror the documented public search surface without introducing fake result logic."
        items={filterGroups}
      />

      <KpiGrid items={homeKpis} title="Project KPIs" />

      <section className="two-column-grid">
        <ProjectTable rows={placeholderProjectRows} title="Published project results" />
        <ProjectMapPanel />
      </section>
    </>
  );
}
