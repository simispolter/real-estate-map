"use client";

import type { FiltersMetadata, MapFeatureItem, MapProjectsResponse } from "@real-estat-map/shared";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useEffect, useState, useTransition } from "react";

import { ProjectMapboxSurface } from "@/components/dashboard/project-mapbox-surface";
import { Tag } from "@/components/ui/tag";
import {
  formatCurrency,
  formatDate,
  formatEnumLabel,
  formatLocationQuality,
  formatNumber,
  formatOriginBadgeLabel,
  formatPercent,
} from "@/lib/format";

type BrowserFilters = {
  city?: string;
  company_id?: string;
  project_business_type?: string;
  government_program_type?: string;
  project_urban_renewal_type?: string;
  permit_status?: string;
  location_confidence?: string;
  selected_project_id?: string;
  map_lat?: string;
  map_lng?: string;
  map_zoom?: string;
  view?: string;
};

type DraftFilters = {
  city: string;
  company_id: string;
  project_business_type: string;
  government_program_type: string;
  project_urban_renewal_type: string;
  permit_status: string;
  location_confidence: string;
};

function hasRenderablePoint(feature: MapFeatureItem) {
  return (
    (feature.geometry &&
      typeof feature.geometry.type === "string" &&
      feature.geometry.type === "Point" &&
      Array.isArray(feature.geometry.coordinates) &&
      feature.geometry.coordinates.length >= 2) ||
    (typeof feature.properties.centerLat === "number" && typeof feature.properties.centerLng === "number")
  );
}

function qualityTone(locationQuality: string) {
  if (locationQuality === "exact") {
    return "accent" as const;
  }
  if (locationQuality === "unknown") {
    return "warning" as const;
  }
  return "default" as const;
}

function originTags(feature: MapFeatureItem) {
  const values: Array<"reported" | "manual" | "inferred"> = [];
  if (feature.properties.reportedCount > 0) {
    values.push("reported");
  }
  if (feature.properties.manualCount > 0) {
    values.push("manual");
  }
  if (feature.properties.inferredCount > 0) {
    values.push("inferred");
  }
  return values;
}

function buildSearchParams(filters: DraftFilters) {
  const next = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) {
      next.set(key, value);
    }
  }
  return next;
}

function buildShareSearchParams(filters: DraftFilters, selectedProjectId: string | null, viewMode: string, viewState: { lat: number | null; lng: number | null; zoom: number | null }) {
  const next = buildSearchParams(filters);
  if (selectedProjectId) {
    next.set("selected_project_id", selectedProjectId);
  }
  if (viewMode !== "map") {
    next.set("view", viewMode);
  }
  if (typeof viewState.lat === "number" && typeof viewState.lng === "number" && typeof viewState.zoom === "number") {
    next.set("map_lat", viewState.lat.toFixed(6));
    next.set("map_lng", viewState.lng.toFixed(6));
    next.set("map_zoom", viewState.zoom.toFixed(2));
  }
  return next;
}

function normalizeDraftFilters(filters: BrowserFilters): DraftFilters {
  return {
    city: filters.city ?? "",
    company_id: filters.company_id ?? "",
    project_business_type: filters.project_business_type ?? "",
    government_program_type: filters.government_program_type ?? "",
    project_urban_renewal_type: filters.project_urban_renewal_type ?? "",
    permit_status: filters.permit_status ?? "",
    location_confidence: filters.location_confidence ?? "",
  };
}

function toNumber(value?: string) {
  if (!value) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function locationExplanation(value: string) {
  if (value === "exact") {
    return "Marker is tied to an exact point from a reported or manually corrected location.";
  }
  if (value === "approximate") {
    return "Marker is close to the project footprint, but not claimed as an exact point.";
  }
  if (value === "city-only") {
    return "Marker uses a city centroid fallback for discovery, not a street-level location.";
  }
  return "The project has weak location data and may not appear precisely on the map.";
}

export function MapFirstProjectBrowser({
  apiBaseUrl,
  initialFilters,
  mapData,
  metadata,
}: {
  apiBaseUrl: string;
  initialFilters: BrowserFilters;
  mapData: MapProjectsResponse;
  metadata: FiltersMetadata;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [draftFilters, setDraftFilters] = useState<DraftFilters>(normalizeDraftFilters(initialFilters));
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(initialFilters.selected_project_id ?? null);
  const [hoveredProjectId, setHoveredProjectId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState(initialFilters.view === "list" ? "list" : "map");
  const [viewState, setViewState] = useState({
    lat: toNumber(initialFilters.map_lat),
    lng: toNumber(initialFilters.map_lng),
    zoom: toNumber(initialFilters.map_zoom),
  });
  const [visibleProjectIds, setVisibleProjectIds] = useState<string[] | null>(null);
  const activeFilters = normalizeDraftFilters(initialFilters);
  const activeFiltersQuery = buildSearchParams(activeFilters).toString();

  useEffect(() => {
    setDraftFilters(normalizeDraftFilters(initialFilters));
    setSelectedProjectId(initialFilters.selected_project_id ?? null);
    setViewMode(initialFilters.view === "list" ? "list" : "map");
    setViewState({
      lat: toNumber(initialFilters.map_lat),
      lng: toNumber(initialFilters.map_lng),
      zoom: toNumber(initialFilters.map_zoom),
    });
  }, [
    initialFilters.city,
    initialFilters.company_id,
    initialFilters.location_confidence,
    initialFilters.government_program_type,
    initialFilters.map_lat,
    initialFilters.map_lng,
    initialFilters.map_zoom,
    initialFilters.permit_status,
    initialFilters.project_business_type,
    initialFilters.project_urban_renewal_type,
    initialFilters.selected_project_id,
    initialFilters.view,
  ]);

  useEffect(() => {
    const next = buildShareSearchParams(activeFilters, selectedProjectId, viewMode, viewState);
    const query = next.toString();
    window.history.replaceState({}, "", query ? `${pathname}?${query}` : pathname);
  }, [activeFiltersQuery, pathname, selectedProjectId, viewMode, viewState]);

  const features = Array.isArray(mapData.features) ? mapData.features : [];
  const visibleIdSet = visibleProjectIds ? new Set(visibleProjectIds) : null;
  const panelFeatures = features.filter((feature) => {
    if (visibleIdSet === null) {
      return true;
    }
    if (!hasRenderablePoint(feature)) {
      return true;
    }
    return visibleIdSet.has(feature.properties.projectId);
  });
  const selectedFeature =
    features.find((feature) => feature.properties.projectId === selectedProjectId) ??
    panelFeatures[0] ??
    features[0] ??
    null;
  const visibleProjectsCount = visibleIdSet ? panelFeatures.length : features.length;
  const preciseProjectsCount = features.filter((feature) =>
    ["exact", "approximate"].includes(feature.properties.locationQuality),
  ).length;
  const cityOnlyProjectsCount = features.filter((feature) => feature.properties.locationQuality === "city-only").length;
  const hiddenWithoutMap = features.filter((feature) => !hasRenderablePoint(feature)).length;
  const returnToParams = buildShareSearchParams(activeFilters, selectedProjectId, viewMode, viewState).toString();
  const exportFilters = buildSearchParams(activeFilters);
  const exportHref = `${apiBaseUrl}/api/v1/projects/export.csv${exportFilters.toString() ? `?${exportFilters.toString()}` : ""}`;
  const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN ?? "";
  const hasMapboxToken = mapboxToken.trim().length > 0;
  const noPreciseLocations = preciseProjectsCount === 0 && features.length > 0;

  function navigateWithFilters(nextFilters: DraftFilters) {
    setSelectedProjectId(null);
    setVisibleProjectIds(null);
    setViewState({ lat: null, lng: null, zoom: null });
    const nextParams = buildSearchParams(nextFilters);
    startTransition(() => {
      router.replace(nextParams.toString() ? `${pathname}?${nextParams.toString()}` : pathname, { scroll: false });
    });
  }

  function handleFilterSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    navigateWithFilters(draftFilters);
  }

  function handleReset() {
    const empty = normalizeDraftFilters({});
    setDraftFilters(empty);
    navigateWithFilters(empty);
  }

  function detailHref(projectId: string) {
    const params = new URLSearchParams();
    params.set("return_to", `${pathname}${returnToParams ? `?${returnToParams}` : ""}`);
    return `/projects/${projectId}?${params.toString()}`;
  }

  return (
    <div className="map-first-stack">
      <section className="map-first-header">
        <div className="map-first-heading">
          <div>
            <p className="eyebrow">Map-first public discovery</p>
            <h2>Browse residential public-company projects from the map first</h2>
          </div>
          <p className="panel-copy">
            Filters, selection, and map state stay shareable in the URL. Location quality and provenance cues stay visible while the interface favors fast geographic browsing.
          </p>
        </div>
        <div className="tag-row">
          <Tag tone="accent">{`${features.length} filtered projects`}</Tag>
          <Tag>{`${visibleProjectsCount} visible in panel`}</Tag>
          <Tag>{`${preciseProjectsCount} exact or approximate`}</Tag>
          <Tag>{`${cityOnlyProjectsCount} city-only`}</Tag>
        </div>
      </section>

      <form className="map-search-bar" onSubmit={handleFilterSubmit}>
        <label className="map-search-field">
          <span>City search</span>
          <input
            list="project-city-options"
            onChange={(event) => setDraftFilters((current) => ({ ...current, city: event.target.value }))}
            placeholder="Search city"
            type="text"
            value={draftFilters.city}
          />
          <datalist id="project-city-options">
            {metadata.cities.map((city) => (
              <option key={city} value={city} />
            ))}
          </datalist>
        </label>

        <label className="map-search-field">
          <span>Company</span>
          <select
            onChange={(event) => setDraftFilters((current) => ({ ...current, company_id: event.target.value }))}
            value={draftFilters.company_id}
          >
            <option value="">All companies</option>
            {metadata.companies.map((company) => (
              <option key={company.id ?? company.label} value={company.id ?? ""}>
                {company.label}
              </option>
            ))}
          </select>
        </label>

        <label className="map-search-field">
          <span>Business type</span>
          <select
            onChange={(event) => setDraftFilters((current) => ({ ...current, project_business_type: event.target.value }))}
            value={draftFilters.project_business_type}
          >
            <option value="">All</option>
            {metadata.projectBusinessTypes.map((value) => (
              <option key={value} value={value}>
                {formatEnumLabel(value)}
              </option>
            ))}
          </select>
        </label>

        <label className="map-search-field">
          <span>Government program</span>
          <select
            onChange={(event) => setDraftFilters((current) => ({ ...current, government_program_type: event.target.value }))}
            value={draftFilters.government_program_type}
          >
            <option value="">All</option>
            {metadata.governmentProgramTypes.map((value) => (
              <option key={value} value={value}>
                {formatEnumLabel(value)}
              </option>
            ))}
          </select>
        </label>

        <label className="map-search-field">
          <span>Urban renewal</span>
          <select
            onChange={(event) => setDraftFilters((current) => ({ ...current, project_urban_renewal_type: event.target.value }))}
            value={draftFilters.project_urban_renewal_type}
          >
            <option value="">All</option>
            {metadata.projectUrbanRenewalTypes.map((value) => (
              <option key={value} value={value}>
                {formatEnumLabel(value)}
              </option>
            ))}
          </select>
        </label>

        <label className="map-search-field">
          <span>Permit status</span>
          <select
            onChange={(event) => setDraftFilters((current) => ({ ...current, permit_status: event.target.value }))}
            value={draftFilters.permit_status}
          >
            <option value="">All</option>
            {metadata.permitStatuses.map((value) => (
              <option key={value} value={value}>
                {formatEnumLabel(value)}
              </option>
            ))}
          </select>
        </label>

        <label className="map-search-field">
          <span>Location quality</span>
          <select
            onChange={(event) => setDraftFilters((current) => ({ ...current, location_confidence: event.target.value }))}
            value={draftFilters.location_confidence}
          >
            <option value="">All</option>
            {metadata.locationConfidences.map((value) => (
              <option key={value} value={value}>
                {formatLocationQuality(value)}
              </option>
            ))}
          </select>
        </label>

        <div className="map-search-actions">
          <button className="primary-button" disabled={isPending} type="submit">
            {isPending ? "Updating..." : "Apply filters"}
          </button>
          <button className="secondary-button" onClick={handleReset} type="button">
            Clear filters
          </button>
          <a className="filter-reset" href={exportHref}>
            Export CSV
          </a>
        </div>
      </form>

      <section className="map-browser-meta">
        <div className="map-browser-counters">
          <Tag tone="accent">{`${features.length} results`}</Tag>
          <Tag>{`${preciseProjectsCount} precise-ish markers`}</Tag>
          <Tag>{`${cityOnlyProjectsCount} city-only fallbacks`}</Tag>
          {!hasMapboxToken ? <Tag tone="warning">List-first fallback mode</Tag> : null}
          {noPreciseLocations ? <Tag tone="warning">City-level browsing mode</Tag> : null}
        </div>
        <div className="map-view-toggle" aria-label="Map or list view">
          <button
            className={viewMode === "map" ? "map-view-toggle-active" : ""}
            onClick={() => setViewMode("map")}
            type="button"
          >
            Map
          </button>
          <button
            className={viewMode === "list" ? "map-view-toggle-active" : ""}
            onClick={() => setViewMode("list")}
            type="button"
          >
            List
          </button>
        </div>
      </section>

      <section className={viewMode === "list" ? "map-browser-shell map-browser-shell-list" : "map-browser-shell"}>
        <div className={viewMode === "list" ? "map-browser-stage map-browser-stage-hidden" : "map-browser-stage"}>
          <div className="map-browser-toolbar">
            <div className="map-legend-row">
              <span className="map-legend-chip map-legend-chip-accent">Regular development</span>
              <span className="map-legend-chip">Government program</span>
              <span className="map-legend-chip map-legend-chip-warning">Urban renewal</span>
            </div>
            <div className="map-legend-row">
              <span className="map-legend-chip map-legend-chip-accent">Exact</span>
              <span className="map-legend-chip">Approximate</span>
              <span className="map-legend-chip">City-only</span>
              <span className="map-legend-chip map-legend-chip-warning">Unknown</span>
            </div>
          </div>
          <ProjectMapboxSurface
            features={features}
            hoveredProjectId={hoveredProjectId}
            noPreciseLocations={noPreciseLocations}
            onHoveredProjectChange={setHoveredProjectId}
            onSelectedProjectChange={setSelectedProjectId}
            onViewStateChange={setViewState}
            onVisibleProjectsChange={setVisibleProjectIds}
            selectedProjectId={selectedProjectId}
            token={mapboxToken}
            viewState={viewState}
          />
          <div className="map-browser-legend">
            <p className="panel-copy">
              Colors signal project type, while ring treatment and badges explain location quality. City-only projects stay selectable, but their marker represents a city centroid fallback rather than a precise site.
            </p>
            {hiddenWithoutMap > 0 ? (
              <p className="panel-copy">
                {hiddenWithoutMap} filtered projects do not have renderable coordinates yet and remain available in the side panel for list-first research.
              </p>
            ) : null}
          </div>
        </div>

        <aside className="map-browser-panel">
          <div className="map-panel-header">
            <div>
              <p className="eyebrow">Visible projects</p>
              <h3>{viewMode === "list" ? "Integrated list mode" : "Map-synced panel"}</h3>
            </div>
            <p className="panel-copy">
              {viewMode === "list"
                ? "Review the same filtered projects in a list-first workflow without losing selection or URL state."
                : "Cards reflect the current map viewport and keep city-only projects visible for discovery."}
            </p>
          </div>

          {selectedFeature ? (
            <section className="map-selected-summary">
              <div className="section-stack">
                <div>
                  <p className="eyebrow">Selected project</p>
                  <h3>{selectedFeature.properties.canonicalName}</h3>
                </div>
                <p className="panel-copy">
                  <Link className="inline-link" href={`/companies/${selectedFeature.properties.companyId}`}>
                    {selectedFeature.properties.companyName}
                  </Link>
                  {" | "}
                  {selectedFeature.properties.city ?? "Unknown city"}
                  {selectedFeature.properties.neighborhood ? ` | ${selectedFeature.properties.neighborhood}` : ""}
                </p>
                <div className="tag-row">
                  <Tag>{formatEnumLabel(selectedFeature.properties.projectBusinessType)}</Tag>
                  <Tag>{selectedFeature.properties.projectStatus ? formatEnumLabel(selectedFeature.properties.projectStatus) : "Status n/a"}</Tag>
                  <Tag tone={qualityTone(selectedFeature.properties.locationQuality)}>
                    {formatLocationQuality(selectedFeature.properties.locationQuality)}
                  </Tag>
                  {originTags(selectedFeature).map((origin) => (
                    <Tag key={`${selectedFeature.properties.projectId}-${origin}`}>
                      {formatOriginBadgeLabel(origin)}
                    </Tag>
                  ))}
                </div>
                <p className="panel-copy">
                  {selectedFeature.properties.addressSummary ?? "Address summary unavailable."}
                </p>
                <p className="panel-copy">{locationExplanation(selectedFeature.properties.locationQuality)}</p>
                <div className="map-card-stats">
                  <div>
                    <strong>Total units</strong>
                    <span>{formatNumber(selectedFeature.properties.totalUnits)}</span>
                  </div>
                  <div>
                    <strong>Sold / unsold</strong>
                    <span>
                      {formatNumber(selectedFeature.properties.soldUnitsCumulative)} / {formatNumber(selectedFeature.properties.unsoldUnits)}
                    </span>
                  </div>
                  <div>
                    <strong>Avg price per sqm</strong>
                    <span>{formatCurrency(selectedFeature.properties.avgPricePerSqmCumulative)}</span>
                  </div>
                  <div>
                    <strong>Gross margin</strong>
                    <span>{formatPercent(selectedFeature.properties.grossMarginExpectedPct)}</span>
                  </div>
                </div>
                <div className="form-actions">
                  <Link className="primary-button" href={detailHref(selectedFeature.properties.projectId)}>
                    Open project page
                  </Link>
                  <button className="secondary-button" onClick={() => setSelectedProjectId(null)} type="button">
                    Clear selection
                  </button>
                </div>
              </div>
            </section>
          ) : (
            <div className="empty-state">
              <strong>No project is selected.</strong>
              <p className="panel-copy">Click a marker or a card to inspect a project quickly.</p>
            </div>
          )}

          <div className="map-project-card-list">
            {panelFeatures.length > 0 ? (
              panelFeatures.map((feature) => {
                const isSelected = selectedFeature?.properties.projectId === feature.properties.projectId;
                const isHovered = hoveredProjectId === feature.properties.projectId;
                return (
                  <article
                    className={
                      isSelected
                        ? "map-project-card map-project-card-active"
                        : isHovered
                          ? "map-project-card map-project-card-hover"
                          : "map-project-card"
                    }
                    key={feature.properties.projectId}
                    onClick={() => setSelectedProjectId(feature.properties.projectId)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedProjectId(feature.properties.projectId);
                      }
                    }}
                    onMouseEnter={() => setHoveredProjectId(feature.properties.projectId)}
                    onMouseLeave={() => setHoveredProjectId(null)}
                    role="button"
                    tabIndex={0}
                  >
                    <div className="map-project-card-header">
                      <div>
                        <strong>{feature.properties.canonicalName}</strong>
                        <p className="panel-copy">
                          {feature.properties.companyName}
                          {" | "}
                          {feature.properties.city ?? "Unknown city"}
                          {feature.properties.neighborhood ? ` | ${feature.properties.neighborhood}` : ""}
                        </p>
                      </div>
                      <Tag tone={qualityTone(feature.properties.locationQuality)}>
                        {formatLocationQuality(feature.properties.locationQuality)}
                      </Tag>
                    </div>

                    <div className="tag-row">
                      <Tag>{formatEnumLabel(feature.properties.projectBusinessType)}</Tag>
                      {feature.properties.permitStatus ? <Tag>{formatEnumLabel(feature.properties.permitStatus)}</Tag> : null}
                      {originTags(feature).map((origin) => (
                        <Tag key={`${feature.properties.projectId}-${origin}-card`}>{formatOriginBadgeLabel(origin)}</Tag>
                      ))}
                    </div>

                    <div className="map-card-stats">
                      <div>
                        <strong>Total units</strong>
                        <span>{formatNumber(feature.properties.totalUnits)}</span>
                      </div>
                      <div>
                        <strong>Sold / unsold</strong>
                        <span>
                          {formatNumber(feature.properties.soldUnitsCumulative)} / {formatNumber(feature.properties.unsoldUnits)}
                        </span>
                      </div>
                      <div>
                        <strong>Avg price / sqm</strong>
                        <span>{formatCurrency(feature.properties.avgPricePerSqmCumulative)}</span>
                      </div>
                      <div>
                        <strong>Snapshot</strong>
                        <span>{formatDate(feature.properties.latestSnapshotDate)}</span>
                      </div>
                    </div>

                    <p className="panel-copy">
                      {feature.properties.addressSummary ??
                        (feature.properties.cityOnly ? "City-centroid display only" : "No address summary available")}
                    </p>

                    <div className="form-actions">
                      <Link className="inline-link" href={detailHref(feature.properties.projectId)}>
                        Open detail
                      </Link>
                      <Link className="inline-link" href={`/companies/${feature.properties.companyId}`}>
                        Company
                      </Link>
                    </div>
                  </article>
                );
              })
            ) : (
              <div className="empty-state">
                <strong>No projects matched the current map view.</strong>
                <p className="panel-copy">Clear filters or switch to list mode to review the full filtered set.</p>
              </div>
            )}
          </div>
        </aside>
      </section>
    </div>
  );
}
