"use client";

import type { MapFeatureItem } from "@real-estat-map/shared";
import type { GeoJSONSource, LngLatBoundsLike, Map as MapboxMap } from "mapbox-gl";
import { useEffect, useRef, useState } from "react";

type ViewState = {
  lat: number | null;
  lng: number | null;
  zoom: number | null;
};

type PointFeature = {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number];
  };
  properties: {
    projectId: string;
    canonicalName: string;
    companyName: string;
    companyId: string;
    city: string | null;
    projectBusinessType: string;
    locationQuality: string;
    hasCoordinates: boolean;
  };
};

function toPointFeature(feature: MapFeatureItem): PointFeature | null {
  const pointGeometry =
    feature.geometry &&
    typeof feature.geometry.type === "string" &&
    feature.geometry.type === "Point" &&
    Array.isArray(feature.geometry.coordinates) &&
    feature.geometry.coordinates.length >= 2
      ? feature.geometry.coordinates
      : null;

  const fallbackPoint =
    typeof feature.properties.centerLng === "number" && typeof feature.properties.centerLat === "number"
      ? [feature.properties.centerLng, feature.properties.centerLat]
      : null;

  const coordinates = pointGeometry ?? fallbackPoint;
  if (!coordinates || typeof coordinates[0] !== "number" || typeof coordinates[1] !== "number") {
    return null;
  }

  return {
    type: "Feature",
    geometry: {
      type: "Point",
      coordinates: [coordinates[0], coordinates[1]],
    },
    properties: {
      projectId: feature.properties.projectId,
      canonicalName: feature.properties.canonicalName,
      companyName: feature.properties.companyName,
      companyId: feature.properties.companyId,
      city: feature.properties.city,
      projectBusinessType: feature.properties.projectBusinessType,
      locationQuality: feature.properties.locationQuality,
      hasCoordinates: feature.properties.hasCoordinates,
    },
  };
}

function buildFeatureCollection(features: MapFeatureItem[]) {
  return {
    type: "FeatureCollection" as const,
    features: features
      .map((feature) => toPointFeature(feature))
      .filter((feature): feature is PointFeature => feature !== null),
  };
}

function getFallbackView(pointFeatures: PointFeature[]): { center: [number, number]; zoom: number } {
  if (pointFeatures.length === 0) {
    return { center: [34.85, 31.95], zoom: 7.1 };
  }

  const lngs = pointFeatures.map((feature) => feature.geometry.coordinates[0]);
  const lats = pointFeatures.map((feature) => feature.geometry.coordinates[1]);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);

  return {
    center: [(minLng + maxLng) / 2, (minLat + maxLat) / 2],
    zoom: 8.6,
  };
}

function getSelectedCollection(features: MapFeatureItem[], projectId: string | null) {
  if (!projectId) {
    return { type: "FeatureCollection" as const, features: [] as PointFeature[] };
  }

  const feature = features.find((item) => item.properties.projectId === projectId);
  const pointFeature = feature ? toPointFeature(feature) : null;
  return {
    type: "FeatureCollection" as const,
    features: pointFeature ? [pointFeature] : [],
  };
}

function getHoveredCollection(features: MapFeatureItem[], projectId: string | null) {
  if (!projectId) {
    return { type: "FeatureCollection" as const, features: [] as PointFeature[] };
  }

  const feature = features.find((item) => item.properties.projectId === projectId);
  const pointFeature = feature ? toPointFeature(feature) : null;
  return {
    type: "FeatureCollection" as const,
    features: pointFeature ? [pointFeature] : [],
  };
}

function fitMapToProjects(map: MapboxMap, pointFeatures: PointFeature[]) {
  if (pointFeatures.length === 0) {
    return;
  }

  if (pointFeatures.length === 1) {
    map.jumpTo({
      center: pointFeatures[0].geometry.coordinates,
      zoom: 11.5,
    });
    return;
  }

  const bounds = pointFeatures.reduce(
    (memo, feature) => memo.extend(feature.geometry.coordinates),
    new mapboxgl.LngLatBounds(
      pointFeatures[0].geometry.coordinates,
      pointFeatures[0].geometry.coordinates,
    ),
  );
  map.fitBounds(bounds as LngLatBoundsLike, { padding: 56, duration: 0, maxZoom: 12.5 });
}

let mapboxgl: typeof import("mapbox-gl").default;

export function ProjectMapboxSurface({
  features,
  hoveredProjectId,
  noPreciseLocations,
  selectedProjectId,
  token,
  viewState,
  onHoveredProjectChange,
  onSelectedProjectChange,
  onViewStateChange,
  onVisibleProjectsChange,
}: {
  features: MapFeatureItem[];
  hoveredProjectId: string | null;
  noPreciseLocations: boolean;
  selectedProjectId: string | null;
  token?: string | null;
  viewState: ViewState;
  onHoveredProjectChange: (projectId: string | null) => void;
  onSelectedProjectChange: (projectId: string | null) => void;
  onViewStateChange: (nextState: ViewState) => void;
  onVisibleProjectsChange: (projectIds: string[] | null) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const pointFeaturesRef = useRef<PointFeature[]>([]);
  const [mapStatus, setMapStatus] = useState<"loading" | "ready" | "fallback">("loading");
  const pointFeatures = buildFeatureCollection(features).features;

  useEffect(() => {
    pointFeaturesRef.current = pointFeatures;
  }, [pointFeatures]);

  useEffect(() => {
    onVisibleProjectsChange(pointFeatures.map((feature) => feature.properties.projectId));
  }, [features, onVisibleProjectsChange, pointFeatures]);

  useEffect(() => {
    if (!token || !containerRef.current) {
      setMapStatus("fallback");
      return;
    }

    let disposed = false;

    async function setupMap() {
      try {
        const module = await import("mapbox-gl");
        if (disposed || !containerRef.current) {
          return;
        }

        mapboxgl = module.default;
        mapboxgl.accessToken = token;

        const initialView = getFallbackView(pointFeatures);
        const map = new mapboxgl.Map({
          container: containerRef.current,
          style: "mapbox://styles/mapbox/light-v11",
          center:
            typeof viewState.lng === "number" && typeof viewState.lat === "number"
              ? [viewState.lng, viewState.lat]
              : initialView.center,
          zoom: typeof viewState.zoom === "number" ? viewState.zoom : initialView.zoom,
          attributionControl: false,
        });

        map.addControl(new mapboxgl.NavigationControl({ visualizePitch: false }), "top-right");
        mapRef.current = map;

        map.on("load", () => {
          if (disposed) {
            return;
          }

          map.addSource("projects", {
            type: "geojson",
            data: buildFeatureCollection(features),
            cluster: true,
            clusterMaxZoom: 12,
            clusterRadius: 44,
          });
          map.addSource("selected-project", {
            type: "geojson",
            data: getSelectedCollection(features, selectedProjectId),
          });
          map.addSource("hovered-project", {
            type: "geojson",
            data: getHoveredCollection(features, hoveredProjectId),
          });

          map.addLayer({
            id: "project-clusters",
            type: "circle",
            source: "projects",
            filter: ["has", "point_count"],
            paint: {
              "circle-color": "#244f62",
              "circle-opacity": 0.82,
              "circle-radius": ["step", ["get", "point_count"], 18, 12, 22, 30, 28],
              "circle-stroke-width": 1.5,
              "circle-stroke-color": "#f6f1e9",
            },
          });
          map.addLayer({
            id: "project-cluster-count",
            type: "symbol",
            source: "projects",
            filter: ["has", "point_count"],
            layout: {
              "text-field": ["get", "point_count_abbreviated"],
              "text-font": ["Open Sans Bold"],
              "text-size": 12,
            },
            paint: {
              "text-color": "#f8f5ef",
            },
          });
          map.addLayer({
            id: "project-points",
            type: "circle",
            source: "projects",
            filter: ["!", ["has", "point_count"]],
            paint: {
              "circle-color": [
                "match",
                ["get", "projectBusinessType"],
                "govt_program",
                "#c07b2f",
                "urban_renewal",
                "#9b4d32",
                "#0f6c7b",
              ],
              "circle-radius": [
                "match",
                ["get", "locationQuality"],
                "exact",
                8,
                "approximate",
                7,
                "city-only",
                6,
                5,
              ],
              "circle-stroke-width": [
                "match",
                ["get", "locationQuality"],
                "exact",
                2,
                "approximate",
                2,
                "city-only",
                1.5,
                1.5,
              ],
              "circle-stroke-color": [
                "match",
                ["get", "locationQuality"],
                "exact",
                "#f8f5ef",
                "approximate",
                "#7a4a12",
                "city-only",
                "#5f6e7c",
                "#1d2731",
              ],
              "circle-opacity": [
                "match",
                ["get", "locationQuality"],
                "city-only",
                0.72,
                "unknown",
                0.56,
                0.92,
              ],
            },
          });
          map.addLayer({
            id: "project-hover-ring",
            type: "circle",
            source: "hovered-project",
            paint: {
              "circle-radius": 12,
              "circle-color": "rgba(0,0,0,0)",
              "circle-stroke-width": 2,
              "circle-stroke-color": "#1d2731",
            },
          });
          map.addLayer({
            id: "project-selected-ring",
            type: "circle",
            source: "selected-project",
            paint: {
              "circle-radius": 15,
              "circle-color": "rgba(0,0,0,0)",
              "circle-stroke-width": 3,
              "circle-stroke-color": "#f04d23",
            },
          });

          map.on("click", "project-clusters", (event) => {
            const clusterFeature = event.features?.[0];
            if (!clusterFeature) {
              return;
            }
            const clusterId = Number(clusterFeature.properties?.cluster_id);
            const source = map.getSource("projects") as GeoJSONSource | undefined;
            if (!source || Number.isNaN(clusterId)) {
              return;
            }
            source.getClusterExpansionZoom(clusterId, (error, zoom) => {
              if (
                error ||
                typeof zoom !== "number" ||
                !clusterFeature.geometry ||
                clusterFeature.geometry.type !== "Point"
              ) {
                return;
              }
              map.easeTo({
                center: clusterFeature.geometry.coordinates as [number, number],
                zoom,
                duration: 500,
              });
            });
          });

          map.on("click", "project-points", (event) => {
            const clicked = event.features?.[0]?.properties;
            if (!clicked || typeof clicked.projectId !== "string") {
              return;
            }
            onSelectedProjectChange(clicked.projectId);
          });

          map.on("mouseenter", "project-points", (event) => {
            map.getCanvas().style.cursor = "pointer";
            const hovered = event.features?.[0]?.properties;
            onHoveredProjectChange(hovered && typeof hovered.projectId === "string" ? hovered.projectId : null);
          });

          map.on("mouseleave", "project-points", () => {
            map.getCanvas().style.cursor = "";
            onHoveredProjectChange(null);
          });

          map.on("moveend", () => {
            const bounds = map.getBounds();
            if (!bounds) {
              return;
            }
            const visibleIds = pointFeaturesRef.current
              .filter((feature) =>
                bounds.contains([feature.geometry.coordinates[0], feature.geometry.coordinates[1]]),
              )
              .map((feature) => feature.properties.projectId);
            onVisibleProjectsChange(visibleIds);
            onViewStateChange({
              lat: map.getCenter().lat,
              lng: map.getCenter().lng,
              zoom: map.getZoom(),
            });
          });

          if (typeof viewState.lng !== "number" || typeof viewState.lat !== "number" || typeof viewState.zoom !== "number") {
            fitMapToProjects(map, pointFeatures);
          }

          setMapStatus("ready");
        });
      } catch {
        if (!disposed) {
          setMapStatus("fallback");
        }
      }
    }

    void setupMap();

    return () => {
      disposed = true;
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [token]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) {
      return;
    }

    const projectsSource = map.getSource("projects") as GeoJSONSource | undefined;
    if (projectsSource) {
      projectsSource.setData(buildFeatureCollection(features));
    }
    const selectedSource = map.getSource("selected-project") as GeoJSONSource | undefined;
    if (selectedSource) {
      selectedSource.setData(getSelectedCollection(features, selectedProjectId));
    }
    const hoveredSource = map.getSource("hovered-project") as GeoJSONSource | undefined;
    if (hoveredSource) {
      hoveredSource.setData(getHoveredCollection(features, hoveredProjectId));
    }
  }, [features, hoveredProjectId, selectedProjectId]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) {
      return;
    }
    if (typeof viewState.lng === "number" && typeof viewState.lat === "number" && typeof viewState.zoom === "number") {
      return;
    }
    fitMapToProjects(map, pointFeatures);
  }, [pointFeatures, viewState.lat, viewState.lng, viewState.zoom]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded() || !selectedProjectId) {
      return;
    }

    const selectedFeature = features.find((feature) => feature.properties.projectId === selectedProjectId);
    const pointFeature = selectedFeature ? toPointFeature(selectedFeature) : null;
    if (!pointFeature) {
      return;
    }

    map.easeTo({
      center: pointFeature.geometry.coordinates,
      duration: 500,
      essential: true,
      zoom: Math.max(map.getZoom(), 11),
    });
  }, [features, selectedProjectId]);

  if (features.length === 0) {
    return (
      <div className="map-surface-stack">
        <div className="mapbox-shell mapbox-shell-static">
          <div className="map-surface-notice">
            <strong>No projects match the current map view.</strong>
            <p className="panel-copy">
              Adjust the active filters or reset the view to restore projects in both the map area and the side panel.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (pointFeatures.length === 0) {
    return (
      <div className="map-surface-stack">
        <div className="mapbox-shell mapbox-shell-static">
          <div className="map-surface-notice">
            <strong>This filtered result set does not yet have renderable points.</strong>
            <p className="panel-copy">
              The side panel remains the main discovery surface for now, and projects can still be opened directly into their detail pages.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (mapStatus === "fallback") {
    return (
      <div className="map-surface-stack">
        <div className="mapbox-shell mapbox-shell-static">
          <div className="map-surface-notice">
            <strong>Interactive map is not enabled in this environment.</strong>
            <p className="panel-copy">
              The public browser stays usable in list mode, with the same filters, selection state, and project detail flow.
            </p>
            <p className="panel-copy">
              Add `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN` to turn on the full map. {pointFeatures.length} of {features.length} filtered projects currently have displayable coordinates.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="map-surface-stack">
      {noPreciseLocations ? (
        <div className="map-surface-inline-note">
          <strong>City-level browsing mode is active.</strong>
          <p className="panel-copy">
            This filtered result set currently relies on city-centroid fallback locations. The map still helps you scan geography, but the side panel remains the primary research surface until more exact or approximate points are available.
          </p>
        </div>
      ) : null}
      <div className="mapbox-shell">
        <div className="mapbox-canvas" ref={containerRef} />
        {mapStatus === "loading" ? (
          <div className="mapbox-loading">
            <strong>Loading interactive map</strong>
            <p className="panel-copy">Preparing markers, clustering, and the current viewport.</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
