"use client";

import type { Map as MapboxMap, Marker } from "mapbox-gl";
import { useEffect, useRef, useState } from "react";

type Props = {
  lat: number | null;
  lng: number | null;
  fallbackLat?: number | null;
  fallbackLng?: number | null;
  qualityLabel: string;
  onChange: (next: { lat: number; lng: number }) => void;
};

const DEFAULT_CENTER: [number, number] = [34.85, 31.95];

export function AdminLocationMapPicker({ fallbackLat, fallbackLng, lat, lng, onChange, qualityLabel }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const markerRef = useRef<Marker | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "fallback">("loading");
  const token = process.env.NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN ?? "";

  useEffect(() => {
    if (!token || !containerRef.current) {
      setStatus("fallback");
      return;
    }

    let disposed = false;
    let mapboxglModule: typeof import("mapbox-gl").default;

    async function setup() {
      try {
        const module = await import("mapbox-gl");
        if (disposed || !containerRef.current) {
          return;
        }

        mapboxglModule = module.default;
        mapboxglModule.accessToken = token;

        const center: [number, number] =
          typeof lng === "number" && typeof lat === "number"
            ? [lng, lat]
            : typeof fallbackLng === "number" && typeof fallbackLat === "number"
              ? [fallbackLng, fallbackLat]
              : DEFAULT_CENTER;

        const map = new mapboxglModule.Map({
          container: containerRef.current,
          style: "mapbox://styles/mapbox/light-v11",
          center,
          zoom: typeof lng === "number" && typeof lat === "number" ? 15 : 11,
          attributionControl: false,
        });
        map.addControl(new mapboxglModule.NavigationControl({ visualizePitch: false }), "top-right");

        const marker = new mapboxglModule.Marker({
          color: "#0f6c7b",
          draggable: true,
        })
          .setLngLat(center)
          .addTo(map);

        marker.on("dragend", () => {
          const position = marker.getLngLat();
          onChange({ lat: position.lat, lng: position.lng });
        });

        map.on("click", (event) => {
          marker.setLngLat(event.lngLat);
          onChange({ lat: event.lngLat.lat, lng: event.lngLat.lng });
        });

        mapRef.current = map;
        markerRef.current = marker;
        map.on("load", () => {
          if (!disposed) {
            setStatus("ready");
          }
        });
      } catch {
        if (!disposed) {
          setStatus("fallback");
        }
      }
    }

    void setup();

    return () => {
      disposed = true;
      markerRef.current?.remove();
      markerRef.current = null;
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [token]);

  useEffect(() => {
    const marker = markerRef.current;
    const map = mapRef.current;
    if (!marker || !map) {
      return;
    }

    const center: [number, number] =
      typeof lng === "number" && typeof lat === "number"
        ? [lng, lat]
        : typeof fallbackLng === "number" && typeof fallbackLat === "number"
          ? [fallbackLng, fallbackLat]
          : DEFAULT_CENTER;

    marker.setLngLat(center);
    map.easeTo({ center, duration: 0, zoom: typeof lng === "number" && typeof lat === "number" ? 15 : 11 });
  }, [fallbackLat, fallbackLng, lat, lng]);

  return (
    <div className="admin-location-map-shell">
      <div className="admin-location-map-toolbar">
        <strong>הצבה על המפה</strong>
        <span className="tag">{qualityLabel}</span>
      </div>
      {status === "fallback" ? (
        <div className="admin-location-map-fallback">
          <strong>המפה האינטראקטיבית אינה זמינה כרגע.</strong>
          <p className="panel-copy">
            אפשר להמשיך לשמור כתובת ונתוני מיקום. לאחר הגדרת `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN` תופיע כאן מפה עם סמן לגרירה.
          </p>
        </div>
      ) : (
        <div className="admin-location-map-stage">
          <div className="admin-location-map-canvas" ref={containerRef} />
          {status === "loading" ? (
            <div className="admin-location-map-loading">
              <strong>טוען מפה אינטראקטיבית</strong>
              <p className="panel-copy">אפשר ללחוץ על המפה או לגרור את הסמן כדי לדייק את המיקום.</p>
            </div>
          ) : null}
        </div>
      )}
      <p className="panel-copy">לחצו על המפה או גררו את הסמן כדי לכוונן את המיקום. השמירה תעדכן גם את המפה הציבורית.</p>
    </div>
  );
}
