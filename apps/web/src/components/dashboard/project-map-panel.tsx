import type { MapProjectsResponse } from "@real-estat-map/shared";

import { Panel } from "@/components/ui/panel";
import { Tag } from "@/components/ui/tag";

const EMPTY_MAP_DATA: MapProjectsResponse = {
  features: [],
  meta: {
    availableProjects: 0,
    projectsWithCoordinates: 0,
    locationQualityBreakdown: {},
  },
};

export function ProjectMapPanel({
  state,
  mapData,
}: {
  state: "ready" | "empty" | "error";
  mapData: MapProjectsResponse;
}) {
  const safeMapData = mapData ?? EMPTY_MAP_DATA;
  const previewItems = safeMapData.features.slice(0, 6);

  return (
    <Panel
      eyebrow="Map Surface"
      title="Location research panel"
      description="This panel consumes the real map-layer API now while keeping a clean adapter boundary for future Mapbox rendering."
      actions={<Tag tone="warning">Map adapter only</Tag>}
    >
      <div className="map-placeholder">
        <div className="map-grid" aria-hidden="true" />
        <div className="map-callout">
          <h3>Location quality breakdown</h3>
          <p className="panel-copy">
            {safeMapData.meta.availableProjects} projects in the current result set,{" "}
            {safeMapData.meta.projectsWithCoordinates} with coordinates or better-than-city precision.
          </p>
          <div className="tag-row">
            {Object.entries(safeMapData.meta.locationQualityBreakdown ?? {}).map(([label, count]) => (
              <Tag
                key={label}
                tone={label === "exact" ? "accent" : label === "unknown" ? "warning" : "default"}
              >
                {`${label}: ${String(count)}`}
              </Tag>
            ))}
          </div>
        </div>
      </div>

      {state === "error" ? (
        <div className="empty-state">
          <strong>Map data is temporarily unavailable.</strong>
          <p className="panel-copy">The panel stayed stable, but the backend map layer did not load.</p>
        </div>
      ) : null}

      {state === "empty" ? (
        <div className="empty-state">
          <strong>No map results matched the current filters.</strong>
          <p className="panel-copy">Try resetting filters to restore the research set.</p>
        </div>
      ) : null}

      {previewItems.length > 0 ? (
        <div className="callout-list">
          {previewItems.map((feature) => (
            <div key={feature.properties.projectId} className="callout-item">
              <strong>{feature.properties.canonicalName}</strong>
              <p className="panel-copy">
                {feature.properties.companyName} | {feature.properties.city ?? "Unknown city"}
              </p>
              <div className="tag-row">
                <Tag
                  tone={
                    feature.properties.locationQuality === "exact"
                      ? "accent"
                      : feature.properties.locationQuality === "unknown"
                        ? "warning"
                        : "default"
                  }
                >
                  {feature.properties.locationQuality}
                </Tag>
                <Tag>{feature.geometry ? "coordinates available" : "city-level only"}</Tag>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </Panel>
  );
}
