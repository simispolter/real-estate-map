import { MapFirstProjectBrowser } from "@/components/dashboard/map-first-project-browser";
import { Panel } from "@/components/ui/panel";
import { getFiltersMetadata, getMapProjects, logServerPageTiming } from "@/lib/api";

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
    city: getSingle(params.city),
    company_id: getSingle(params.company_id),
    project_business_type: getSingle(params.project_business_type),
    government_program_type: getSingle(params.government_program_type),
    project_urban_renewal_type: getSingle(params.project_urban_renewal_type),
    permit_status: getSingle(params.permit_status),
    location_confidence: getSingle(params.location_confidence),
    selected_project_id: getSingle(params.selected_project_id),
    map_lat: getSingle(params.map_lat),
    map_lng: getSingle(params.map_lng),
    map_zoom: getSingle(params.map_zoom),
    view: getSingle(params.view),
  };

  const [metadata, mapResults] = await Promise.all([getFiltersMetadata(), getMapProjects(filters)]);
  const mapFeatures = Array.isArray(mapResults.item.features) ? mapResults.item.features : [];
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  logServerPageTiming("/projects", startedAt, {
    filters: Object.values(filters).filter(Boolean).length,
    map_features: mapFeatures.length,
    mapped: mapResults.item.meta.projectsWithCoordinates,
  });

  if (mapResults.state === "error") {
    return (
      <Panel
        eyebrow="Map-first browsing"
        title="The public map is temporarily unavailable"
        description="The route stayed stable, but the public map payload could not be loaded."
      >
        <p className="panel-copy">
          Check the API container, then refresh. The public product now depends on the map payload as its primary discovery surface.
        </p>
      </Panel>
    );
  }

  return (
    <MapFirstProjectBrowser
      apiBaseUrl={apiBaseUrl}
      initialFilters={filters}
      mapData={mapResults.item}
      metadata={metadata}
    />
  );
}
