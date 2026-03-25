import { FiltersPanel } from "@/components/dashboard/filters-panel";
import { KpiGrid } from "@/components/dashboard/kpi-grid";
import { ProjectTable } from "@/components/dashboard/project-table";
import { Panel } from "@/components/ui/panel";
import { Tag } from "@/components/ui/tag";
import { getFiltersMetadata, getProjects, logServerPageTiming } from "@/lib/api";
import { formatEnumLabel } from "@/lib/format";

export const revalidate = 120;

type PageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function getSingle(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

export default async function ProjectsPage({ searchParams }: PageProps) {
  const startedAt = Date.now();
  const params = (await searchParams) ?? {};
  const filters = {
    q: getSingle(params.q),
    city: getSingle(params.city),
    company_id: getSingle(params.company_id),
    lifecycle_stage: getSingle(params.lifecycle_stage),
    disclosure_level: getSingle(params.disclosure_level),
    project_business_type: getSingle(params.project_business_type),
    government_program_type: getSingle(params.government_program_type),
    project_urban_renewal_type: getSingle(params.project_urban_renewal_type),
    project_status: getSingle(params.project_status),
    permit_status: getSingle(params.permit_status),
    location_confidence: getSingle(params.location_confidence),
    page_size: getSingle(params.page_size) ?? "100",
  };

  const [metadata, projects] = await Promise.all([getFiltersMetadata(), getProjects(filters)]);
  const safeItems = Array.isArray(projects.items) ? projects.items : [];
  const exportSearchParams = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (typeof value === "string" && value.trim() !== "") {
      exportSearchParams.set(key, value);
    }
  });
  const query = exportSearchParams.toString();
  const exportHref = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/v1/projects/export.csv${
    query ? `?${query}` : ""
  }`;

  const locationBreakdown = safeItems.reduce<Record<string, number>>((accumulator, item) => {
    const key = item.locationConfidence ?? "unknown";
    accumulator[key] = (accumulator[key] ?? 0) + 1;
    return accumulator;
  }, {});

  logServerPageTiming("/projects", startedAt, {
    filters: Object.values(filters).filter(Boolean).length,
    projects: safeItems.length,
  });

  return (
    <>
      <Panel
        eyebrow="Projects Database"
        title="Residential project database"
        description="The working public product in this phase is a clean, filterable database of canonical residential projects and snapshots from public-developer reports."
        actions={
          <div className="tag-row">
            <Tag tone="accent">core workflow</Tag>
            <Tag>filters + export</Tag>
          </div>
        }
      >
        <p className="panel-copy">
          This route is intentionally database-first. Use it to inspect the canonical project set after report extraction, review, and snapshot publish.
        </p>
      </Panel>

      <FiltersPanel
        action="/projects"
        description="Filter the canonical residential project database by company, city, lifecycle stage, disclosure depth, classification, and current status."
        fields={[
          {
            label: "Search",
            name: "q",
            type: "text",
            value: filters.q,
            placeholder: "Project, company, city, neighborhood",
          },
          {
            label: "Company",
            name: "company_id",
            value: filters.company_id,
            options: metadata.companies
              .filter((company) => company.id)
              .map((company) => ({ label: company.label, value: company.id ?? "" })),
          },
          {
            label: "City",
            name: "city",
            value: filters.city,
            options: metadata.cities.map((city) => ({ label: city, value: city })),
          },
          {
            label: "Lifecycle stage",
            name: "lifecycle_stage",
            value: filters.lifecycle_stage,
            options: metadata.lifecycleStages.map((value) => ({ label: formatEnumLabel(value), value })),
          },
          {
            label: "Disclosure depth",
            name: "disclosure_level",
            value: filters.disclosure_level,
            options: metadata.disclosureLevels.map((value) => ({ label: formatEnumLabel(value), value })),
          },
          {
            label: "Business type",
            name: "project_business_type",
            value: filters.project_business_type,
            options: metadata.projectBusinessTypes.map((value) => ({ label: formatEnumLabel(value), value })),
          },
          {
            label: "Government program",
            name: "government_program_type",
            value: filters.government_program_type,
            options: metadata.governmentProgramTypes.map((value) => ({ label: formatEnumLabel(value), value })),
          },
          {
            label: "Urban renewal",
            name: "project_urban_renewal_type",
            value: filters.project_urban_renewal_type,
            options: metadata.projectUrbanRenewalTypes.map((value) => ({ label: formatEnumLabel(value), value })),
          },
          {
            label: "Project status",
            name: "project_status",
            value: filters.project_status,
            options: metadata.projectStatuses.map((value) => ({ label: formatEnumLabel(value), value })),
          },
          {
            label: "Permit status",
            name: "permit_status",
            value: filters.permit_status,
            options: metadata.permitStatuses.map((value) => ({ label: formatEnumLabel(value), value })),
          },
          {
            label: "Location quality",
            name: "location_confidence",
            value: filters.location_confidence,
            options: metadata.locationConfidences.map((value) => ({ label: formatEnumLabel(value), value })),
          },
        ]}
      />

      {projects.state === "error" ? (
        <Panel
          eyebrow="Data Status"
          title="Project data is temporarily unavailable"
          description="The route rendered safely, but the project API did not return a usable payload."
        >
          <p className="panel-copy">Check the API container and refresh. The canonical database remains the source of truth for this phase.</p>
        </Panel>
      ) : null}

      <KpiGrid
        title="Database insight summary"
        items={[
          {
            id: "projects",
            label: "Visible canonical projects",
            value: String(projects.total),
            note: "Counted after the current filters are applied.",
          },
          {
            id: "companies",
            label: "Covered developers",
            value: String(new Set(safeItems.map((item) => item.company.id)).size),
            note: "Unique public residential developers in the current slice.",
          },
          {
            id: "snapshots",
            label: "Rows with latest snapshot",
            value: String(safeItems.filter((item) => item.latestSnapshotDate).length),
            note: "Projects with at least one published canonical snapshot.",
          },
          {
            id: "exactish",
            label: "Exact or approximate locations",
            value: String((locationBreakdown.exact ?? 0) + (locationBreakdown.approximate ?? 0)),
            note: "Location quality stays visible, but analysis does not depend on map precision.",
          },
        ]}
      />

      <Panel
        eyebrow="Research Tools"
        title="Export and inspection"
        description="Use CSV export for spreadsheet work, anomaly checks, or deeper internal analysis outside the UI."
      >
        <div className="form-actions">
          <a className="primary-button" href={exportHref}>
            Export current result set
          </a>
          <a className="secondary-button" href="/companies">
            Company coverage view
          </a>
        </div>
      </Panel>

      {projects.state === "empty" ? (
        <Panel
          eyebrow="No Matches"
          title="No projects matched the current filters"
          description="The route is healthy, but this filter combination returned no canonical projects."
        >
          <p className="panel-copy">Reset filters to return to the full database view.</p>
        </Panel>
      ) : null}

      <ProjectTable rows={safeItems} title="Canonical projects" />
    </>
  );
}
