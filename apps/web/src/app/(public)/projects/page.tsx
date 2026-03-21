import type { SelectOption } from "@real-estat-map/shared";
import Link from "next/link";

import { FiltersPanel } from "@/components/dashboard/filters-panel";
import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { ProjectMapPanel } from "@/components/dashboard/project-map-panel";
import { ProjectTable } from "@/components/dashboard/project-table";
import { Panel } from "@/components/ui/panel";
import { getFiltersMetadata, getMapProjects, getProjects } from "@/lib/api";

export const dynamic = "force-dynamic";

type PageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function getSingle(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function toOptions(values: string[]): SelectOption[] {
  return values.map((value) => ({ id: value, label: value }));
}

export default async function ProjectsPage({ searchParams }: PageProps) {
  const params = (await searchParams) ?? {};
  const filters = {
    city: getSingle(params.city),
    company_id: getSingle(params.company_id),
    project_business_type: getSingle(params.project_business_type),
    government_program_type: getSingle(params.government_program_type),
    project_urban_renewal_type: getSingle(params.project_urban_renewal_type),
    permit_status: getSingle(params.permit_status),
  };
  const [projects, metadata, mapResults] = await Promise.all([
    getProjects(filters),
    getFiltersMetadata(),
    getMapProjects(filters),
  ]);
  const projectItems = Array.isArray(projects.items) ? projects.items : [];
  const knownUnsoldUnits = projectItems.reduce((sum, item) => sum + (item.unsoldUnits ?? 0), 0);
  const planningProjects = projectItems.filter((item) => item.projectStatus === "planning").length;
  const exactOrApproximateLocations = projectItems.filter((item) => item.locationQuality !== "city-only" && item.locationQuality !== "unknown").length;
  const exportParams = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) {
      exportParams.set(key, value);
    }
  }
  const exportBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const exportHref = `${exportBaseUrl}/api/v1/projects/export.csv${exportParams.toString() ? `?${exportParams.toString()}` : ""}`;

  const filterFields = [
    {
      label: "City",
      name: "city",
      value: filters.city,
      options: toOptions(metadata.cities).map((option) => ({ label: option.label, value: option.label })),
    },
    {
      label: "Company",
      name: "company_id",
      value: filters.company_id,
      options: metadata.companies.filter((company) => company.id).map((company) => ({ label: company.label, value: company.id as string })),
    },
    {
      label: "Project business type",
      name: "project_business_type",
      value: filters.project_business_type,
      options: metadata.projectBusinessTypes.map((value) => ({ label: value, value })),
    },
    {
      label: "Government program",
      name: "government_program_type",
      value: filters.government_program_type,
      options: metadata.governmentProgramTypes.map((value) => ({ label: value, value })),
    },
    {
      label: "Urban renewal type",
      name: "project_urban_renewal_type",
      value: filters.project_urban_renewal_type,
      options: metadata.projectUrbanRenewalTypes.map((value) => ({ label: value, value })),
    },
    {
      label: "Permit status",
      name: "permit_status",
      value: filters.permit_status,
      options: metadata.permitStatuses.map((value) => ({ label: value, value })),
    },
  ];

  return (
    <>
      <Panel
        eyebrow="Projects"
        title="Residential project catalog"
        description="This route is now a usable research surface with sharable URL filters, project deep links, provenance-aware detail pages, and CSV export."
        actions={
          <Link className="filter-reset" href={exportHref}>
            Export CSV
          </Link>
        }
      >
        <p className="panel-copy">
          Values stay null when the latest public report does not disclose them. Inferred classifications and statuses are preserved through provenance instead of being presented as raw facts.
        </p>
      </Panel>

      {projects.state === "error" ? (
        <Panel eyebrow="Data Status" title="Project data is temporarily unavailable" description="The page rendered safely, but the projects API did not return usable data.">
          <p className="panel-copy">Filters and layout stay available while the backend recovers.</p>
        </Panel>
      ) : null}

      <FiltersPanel
        action="/projects"
        title="Project filters"
        description="Filter the seeded public catalog by city, company, business type, government-program type, urban-renewal type, and permit status."
        fields={filterFields}
        resetHref="/projects"
      />

      <KpiGrid
        title="Project KPIs"
        items={[
          { id: "rows", label: "Returned projects", value: String(projects.total), note: "Based on the active filters." },
          { id: "unsold", label: "Known unsold units", value: String(knownUnsoldUnits), note: "Missing report values remain null and are excluded." },
          { id: "planning", label: "Projects in planning", value: String(planningProjects), note: "Useful for spotting pipeline and government-program inventory." },
          { id: "location", label: "Projects with better-than-city location", value: String(exactOrApproximateLocations), note: "Based on the location quality surface." },
        ]}
      />

      {projects.state === "empty" ? (
        <Panel eyebrow="No Matches" title="No projects matched the current filters" description="The route is healthy, but there were no rows for the current research view.">
          <p className="panel-copy">Reset filters to restore the full seeded research set.</p>
        </Panel>
      ) : null}

      <section className="two-column-grid">
        <ProjectTable rows={projectItems} title="Published project results" />
        <ProjectMapPanel state={mapResults.state} mapData={mapResults.item} />
      </section>
    </>
  );
}
