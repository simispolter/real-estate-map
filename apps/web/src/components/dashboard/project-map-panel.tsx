"use client";

import type {
  ExternalLayerFeatureItem,
  ExternalLayerSummary,
  MapExternalLayersResponse,
  MapFeatureItem,
  MapProjectsResponse,
} from "@real-estat-map/shared";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { Panel } from "@/components/ui/panel";
import { Tag } from "@/components/ui/tag";

const EMPTY_MAP_DATA: MapProjectsResponse = {
  features: [],
  meta: {
    availableProjects: 0,
    projectsWithCoordinates: 0,
    locationQualityBreakdown: {},
    geometryTypeBreakdown: {},
    cityOnlyProjects: 0,
  },
};

const EMPTY_EXTERNAL_LAYERS: MapExternalLayersResponse = {
  features: [],
  meta: {
    selectedLayers: 0,
    selectedRecords: 0,
    layerBreakdown: {},
  },
};

function qualityTone(locationQuality: string) {
  if (locationQuality === "exact") {
    return "accent" as const;
  }
  if (locationQuality === "unknown") {
    return "warning" as const;
  }
  return "default" as const;
}

function pointFill(locationQuality: string) {
  if (locationQuality === "exact") {
    return "#0f6c7b";
  }
  if (locationQuality === "approximate") {
    return "#c07b2f";
  }
  return "#6f7d89";
}

function toPoint(feature: MapFeatureItem) {
  const geometry = feature.geometry;
  if (!geometry || geometry.type !== "Point" || !Array.isArray(geometry.coordinates) || geometry.coordinates.length < 2) {
    return null;
  }
  const [lng, lat] = geometry.coordinates;
  if (typeof lng !== "number" || typeof lat !== "number") {
    return null;
  }
  return { lng, lat };
}

function toOverlayPoint(feature: ExternalLayerFeatureItem) {
  const geometry = feature.geometry;
  if (!geometry || geometry.type !== "Point" || !Array.isArray(geometry.coordinates) || geometry.coordinates.length < 2) {
    return null;
  }
  const [lng, lat] = geometry.coordinates;
  if (typeof lng !== "number" || typeof lat !== "number") {
    return null;
  }
  return { lng, lat };
}

function layerColor(layerId: string) {
  const palette = ["#7b5f2a", "#8d3e2f", "#245a68", "#566c2b", "#7c4f84"];
  const value = layerId.split("").reduce((sum, char) => sum + char.charCodeAt(0), 0);
  return palette[value % palette.length];
}

function setSelectedProjectId(
  pathname: string,
  searchParams: Readonly<URLSearchParams>,
  router: ReturnType<typeof useRouter>,
  projectId: string | null,
) {
  const next = new URLSearchParams(searchParams.toString());
  if (projectId) {
    next.set("selected_project_id", projectId);
  } else {
    next.delete("selected_project_id");
  }
  const query = next.toString();
  router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
}

function setSelectedLayers(
  pathname: string,
  searchParams: Readonly<URLSearchParams>,
  router: ReturnType<typeof useRouter>,
  layerIds: string[],
) {
  const next = new URLSearchParams(searchParams.toString());
  if (layerIds.length > 0) {
    next.set("layers", layerIds.join(","));
  } else {
    next.delete("layers");
  }
  const query = next.toString();
  router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
}

export function ProjectMapPanel({
  state,
  mapData,
  selectedProjectId,
  layers,
  externalLayers,
  selectedLayerIds,
}: {
  state: "ready" | "empty" | "error";
  mapData: MapProjectsResponse;
  selectedProjectId?: string | null;
  layers: ExternalLayerSummary[];
  externalLayers: MapExternalLayersResponse;
  selectedLayerIds: string[];
}) {
  const safeMapData = mapData ?? EMPTY_MAP_DATA;
  const safeExternalLayers = externalLayers ?? EMPTY_EXTERNAL_LAYERS;
  const features = Array.isArray(safeMapData.features) ? safeMapData.features : [];
  const overlayFeatures = Array.isArray(safeExternalLayers.features) ? safeExternalLayers.features : [];
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();

  const selectedFeature =
    features.find((feature) => feature.properties.projectId === selectedProjectId) ?? features[0] ?? null;

  const pointFeatures = features
    .map((feature) => {
      const point = toPoint(feature);
      return point ? { feature, point } : null;
    })
    .filter((value): value is { feature: MapFeatureItem; point: { lng: number; lat: number } } => value !== null);

  const lngValues = pointFeatures.map((entry) => entry.point.lng);
  const latValues = pointFeatures.map((entry) => entry.point.lat);
  const overlayPoints = overlayFeatures
    .map((feature) => {
      const point = toOverlayPoint(feature);
      return point ? { feature, point } : null;
    })
    .filter(
      (value): value is { feature: ExternalLayerFeatureItem; point: { lng: number; lat: number } } => value !== null,
    );
  const overlayLngValues = overlayPoints.map((entry) => entry.point.lng);
  const overlayLatValues = overlayPoints.map((entry) => entry.point.lat);
  const allLngValues = [...lngValues, ...overlayLngValues];
  const allLatValues = [...latValues, ...overlayLatValues];
  const minLng = allLngValues.length > 0 ? Math.min(...allLngValues) : 34.6;
  const maxLng = allLngValues.length > 0 ? Math.max(...allLngValues) : 35.0;
  const minLat = allLatValues.length > 0 ? Math.min(...allLatValues) : 31.8;
  const maxLat = allLatValues.length > 0 ? Math.max(...allLatValues) : 32.4;

  function scaleLng(lng: number) {
    const spread = Math.max(maxLng - minLng, 0.01);
    return 28 + ((lng - minLng) / spread) * 304;
  }

  function scaleLat(lat: number) {
    const spread = Math.max(maxLat - minLat, 0.01);
    return 232 - ((lat - minLat) / spread) * 184;
  }

  return (
    <Panel
      eyebrow="Map Surface"
      title="Spatial research panel"
      description="Geometry-aware research surface with project markers, URL-linked selection, and toggleable external layers."
      actions={
        <div className="tag-row">
          <Tag tone="accent">{`${safeMapData.meta.projectsWithCoordinates} mapped`}</Tag>
          <Tag>{`${safeMapData.meta.cityOnlyProjects} city-only`}</Tag>
          <Tag>{`${safeExternalLayers.meta.selectedRecords} overlay records`}</Tag>
        </div>
      }
    >
      <div className="map-layer-toolbar">
        {layers.length > 0 ? (
          layers.map((layer) => {
            const enabled = selectedLayerIds.includes(layer.id);
            return (
              <button
                key={layer.id}
                className={enabled ? "map-layer-toggle map-layer-toggle-active" : "map-layer-toggle"}
                onClick={() =>
                  setSelectedLayers(
                    pathname,
                    searchParams,
                    router,
                    enabled
                      ? selectedLayerIds.filter((value) => value !== layer.id)
                      : [...selectedLayerIds, layer.id],
                  )
                }
                type="button"
              >
                {layer.layerName}
              </button>
            );
          })
        ) : (
          <span className="muted-copy">No external layers are currently published.</span>
        )}
      </div>

      <div className="map-panel-grid">
        <div className="map-canvas-card">
          <div className="map-legend">
            <Tag tone="accent">exact</Tag>
            <Tag>approximate</Tag>
            <Tag>city-only</Tag>
            <Tag tone="warning">unknown</Tag>
            <Tag>external layers</Tag>
          </div>
          {pointFeatures.length > 0 ? (
            <svg className="map-surface-svg" role="img" viewBox="0 0 360 260">
              <rect x="0" y="0" width="360" height="260" rx="24" fill="rgba(255,255,255,0.88)" />
              {[60, 120, 180, 240, 300].map((x) => (
                <line key={`x-${x}`} x1={x} y1="18" x2={x} y2="242" stroke="rgba(15,108,123,0.08)" />
              ))}
              {[56, 104, 152, 200].map((y) => (
                <line key={`y-${y}`} x1="18" y1={y} x2="342" y2={y} stroke="rgba(15,108,123,0.08)" />
              ))}
              {overlayPoints.map(({ feature, point }) => (
                <rect
                  key={`${feature.properties.layerId}-${feature.properties.externalRecordId}`}
                  fill={layerColor(feature.properties.layerId)}
                  height="10"
                  opacity="0.8"
                  rx="2"
                  transform={`rotate(45 ${scaleLng(point.lng)} ${scaleLat(point.lat)})`}
                  width="10"
                  x={scaleLng(point.lng) - 5}
                  y={scaleLat(point.lat) - 5}
                />
              ))}
              {pointFeatures.map(({ feature, point }) => {
                const selected = selectedFeature?.properties.projectId === feature.properties.projectId;
                return (
                  <g key={feature.properties.projectId}>
                    <circle
                      cx={scaleLng(point.lng)}
                      cy={scaleLat(point.lat)}
                      fill={pointFill(feature.properties.locationQuality)}
                      opacity={selected ? 1 : 0.82}
                      r={selected ? 9 : 6}
                      stroke={selected ? "#1d2731" : "rgba(29,39,49,0.24)"}
                      strokeWidth={selected ? 2 : 1}
                      onClick={() =>
                        setSelectedProjectId(pathname, searchParams, router, feature.properties.projectId)
                      }
                    />
                  </g>
                );
              })}
            </svg>
          ) : (
            <div className="empty-state">
              <strong>No precise coordinates are available in this result set yet.</strong>
              <p className="panel-copy">
                City-only projects are still listed and selectable below so research can continue while geocoding improves.
              </p>
            </div>
          )}
          <div className="map-meta-grid">
            {Object.entries(safeMapData.meta.locationQualityBreakdown ?? {}).map(([label, count]) => (
              <span key={label} className="map-meta-pill">
                {label}: {String(count)}
              </span>
            ))}
            {Object.entries(safeMapData.meta.geometryTypeBreakdown ?? {}).map(([label, count]) => (
              <span key={label} className="map-meta-pill">
                {label}: {String(count)}
              </span>
            ))}
            {Object.entries(safeExternalLayers.meta.layerBreakdown ?? {}).map(([label, count]) => (
              <span key={`overlay-${label}`} className="map-meta-pill">
                {label}: {String(count)}
              </span>
            ))}
          </div>
        </div>

        <div className="map-selection-card section-stack">
          {selectedFeature ? (
            <>
              <div>
                <p className="eyebrow">Selected Project</p>
                <h3>{selectedFeature.properties.canonicalName}</h3>
                <p className="panel-copy">
                  {selectedFeature.properties.companyName} | {selectedFeature.properties.city ?? "Unknown city"}
                </p>
              </div>
              <div className="tag-row">
                <Tag tone={qualityTone(selectedFeature.properties.locationQuality)}>
                  {selectedFeature.properties.locationQuality}
                </Tag>
                <Tag>{selectedFeature.properties.geometryType}</Tag>
                <Tag>{selectedFeature.properties.geometryIsManual ? "manual" : selectedFeature.properties.isSourceDerived ? "source" : "derived"}</Tag>
                <Tag>{selectedFeature.properties.projectBusinessType}</Tag>
              </div>
              <p className="panel-copy">
                {selectedFeature.properties.addressSummary ??
                  (selectedFeature.properties.cityOnly ? "City-level only location" : "No address summary")}
              </p>
              <div className="form-actions">
                <Link className="primary-button" href={`/projects/${selectedFeature.properties.projectId}`}>
                  Open detail
                </Link>
                <button
                  className="secondary-button"
                  onClick={() => setSelectedProjectId(pathname, searchParams, router, null)}
                  type="button"
                >
                  Clear selection
                </button>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <strong>No project is selected.</strong>
              <p className="panel-copy">Choose a marker or list row to inspect the current research surface.</p>
            </div>
          )}
        </div>
      </div>

      {state === "error" ? (
        <div className="empty-state">
          <strong>Map data is temporarily unavailable.</strong>
          <p className="panel-copy">The project table is still available while the map API recovers.</p>
        </div>
      ) : null}

      {state === "empty" ? (
        <div className="empty-state">
          <strong>No map results matched the current filters.</strong>
          <p className="panel-copy">Clear filters or adjust the research view to restore projects.</p>
        </div>
      ) : null}

      {features.length > 0 ? (
        <div className="map-results-list">
          {features.map((feature) => {
            const selected = selectedFeature?.properties.projectId === feature.properties.projectId;
            return (
              <button
                key={feature.properties.projectId}
                className={selected ? "map-result-card map-result-card-active" : "map-result-card"}
                onClick={() => setSelectedProjectId(pathname, searchParams, router, feature.properties.projectId)}
                type="button"
              >
                <div>
                  <strong>{feature.properties.canonicalName}</strong>
                  <p className="panel-copy">
                    {feature.properties.companyName} | {feature.properties.city ?? "Unknown city"}
                  </p>
                </div>
                <div className="tag-row">
                  <Tag tone={qualityTone(feature.properties.locationQuality)}>{feature.properties.locationQuality}</Tag>
                  <Tag>{feature.properties.geometryType}</Tag>
                  <Tag>{feature.properties.geometryIsManual ? "manual" : feature.properties.isSourceDerived ? "source" : "derived"}</Tag>
                  <Tag>{feature.properties.hasCoordinates ? "mapped" : "city-only"}</Tag>
                </div>
                <p className="panel-copy">
                  {feature.properties.addressSummary ??
                    (feature.properties.cityOnly ? "City-level fallback geometry" : "No address summary")}
                </p>
              </button>
            );
          })}
        </div>
      ) : null}

      {overlayFeatures.length > 0 ? (
        <div className="map-results-list">
          {overlayFeatures.slice(0, 8).map((feature) => (
            <div className="map-result-card" key={`${feature.properties.layerId}-${feature.properties.externalRecordId}`}>
              <div>
                <strong>{feature.properties.label ?? feature.properties.externalRecordId}</strong>
                <p className="panel-copy">
                  {feature.properties.layerName} | {feature.properties.city ?? "No city"}
                </p>
              </div>
              <div className="tag-row">
                <Tag>{feature.properties.sourceName}</Tag>
                <Tag>{`${feature.properties.relationCount} relations`}</Tag>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </Panel>
  );
}
