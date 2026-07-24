"use client";

import { useEffect, useRef } from "react";

import {
  eventMapMarkerIcon,
  eventMapMarkerLabel,
  resolveMarkerTone,
} from "@/components/events/map/EventMapMarker";
import { cn } from "@/lib/cn";
import { hasGoogleMapsApiKey } from "@/lib/google-maps";
import { clusterMapPins } from "@/lib/maps/cluster";
import {
  createMapController,
  type MapController,
} from "@/lib/maps/provider";
import type { MapBounds, MapEventPin, MapLatLng, MapViewport } from "@/lib/maps/types";

const DEFAULT_CENTER: MapLatLng = { lat: 6.5244, lng: 3.3792 };

export function EventMap({
  events,
  selectedId,
  center,
  zoom = 11,
  className = "",
  onSelect,
  onViewportIdle,
  onReady,
  controllerRef,
}: {
  events: MapEventPin[];
  selectedId: string | null;
  center?: MapLatLng;
  zoom?: number;
  className?: string;
  onSelect: (id: string) => void;
  onViewportIdle?: (viewport: MapViewport) => void;
  onReady?: (controller: MapController) => void;
  controllerRef?: React.MutableRefObject<MapController | null>;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapController | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const markersRef = useRef<any[]>([]);
  const selectedRef = useRef(selectedId);
  const eventsRef = useRef(events);
  selectedRef.current = selectedId;
  eventsRef.current = events;

  useEffect(() => {
    const el = containerRef.current;
    if (!el || !hasGoogleMapsApiKey()) return;
    let cancelled = false;

    void (async () => {
      try {
        const controller = await createMapController({
          container: el,
          center: center ?? DEFAULT_CENTER,
          zoom,
          onIdle: (vp) => onViewportIdle?.(vp),
        });
        if (cancelled || !controller) return;
        mapRef.current = controller;
        if (controllerRef) controllerRef.current = controller;
        onReady?.(controller);
        syncMarkers(controller, eventsRef.current, selectedRef.current);
      } catch {
        // Empty/unavailable state rendered below when no map.
      }
    })();

    return () => {
      cancelled = true;
      clearMarkers();
      mapRef.current?.destroy();
      mapRef.current = null;
      if (controllerRef) controllerRef.current = null;
    };
    // Intentionally mount-once; viewport + markers sync via later effects.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const controller = mapRef.current;
    if (!controller) return;
    syncMarkers(controller, events, selectedId);
    // syncMarkers closes over onSelect + refs; intentional on pin/selection change only.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- marker sync
  }, [events, selectedId]);

  useEffect(() => {
    if (!center || !mapRef.current) return;
    mapRef.current.panTo(center);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- pan when coords change
  }, [center?.lat, center?.lng]);

  function clearMarkers() {
    for (const m of markersRef.current) {
      m.setMap?.(null);
    }
    markersRef.current = [];
  }

  function syncMarkers(
    controller: MapController,
    pins: MapEventPin[],
    selected: string | null,
  ) {
    const g = window.google;
    const map = controller.native;
    if (!g?.maps?.Marker || !map) return;

    clearMarkers();
    const zoom = controller.getViewport().zoom;
    const { singles, clusters } = clusterMapPins(pins, zoom);

    for (const pin of singles) {
      const tone = resolveMarkerTone({
        selected: pin.id === selected,
        approximate: pin.location_map_mode === "approximate",
      });
      const marker = new g.maps.Marker({
        map,
        position: pin.position,
        title: pin.title,
        zIndex: pin.id === selected ? 1000 : 1,
        icon: eventMapMarkerIcon({ tone, maps: g.maps }),
        label: eventMapMarkerLabel(
          pin.is_free ? "Free" : pin.price_label?.replace(/^From\s+/i, "") || "●",
          tone,
        ),
      });
      marker.addListener("click", () => onSelect(pin.id));
      markersRef.current.push(marker);
    }

    for (const cluster of clusters) {
      const tone = resolveMarkerTone({ cluster: true });
      const marker = new g.maps.Marker({
        map,
        position: cluster.position,
        title: `${cluster.count} events`,
        zIndex: 500,
        icon: eventMapMarkerIcon({ tone, maps: g.maps }),
        label: eventMapMarkerLabel(String(cluster.count), tone),
      });
      marker.addListener("click", () => {
        const nextZoom = Math.min(18, (controller.getViewport().zoom || 11) + 2);
        controller.setCenter(cluster.position);
        controller.setZoom(nextZoom);
        if (cluster.eventIds[0]) onSelect(cluster.eventIds[0]);
      });
      markersRef.current.push(marker);
    }
  }

  if (!hasGoogleMapsApiKey()) {
    return (
      <div
        className={cn(
          "flex h-full min-h-[16rem] items-center justify-center rounded-[var(--radius-xl)] border border-border bg-ink px-6 text-center",
          className,
        )}
      >
        <div className="max-w-sm space-y-2">
          <p className="text-sm font-bold text-paper">Map unavailable</p>
          <p className="text-sm text-paper/70">
            Add{" "}
            <code className="text-primary">NEXT_PUBLIC_GOOGLE_MAPS_API_KEY</code>{" "}
            to enable the interactive map. Browse the list while you set it up.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn(
        "h-full min-h-[16rem] w-full overflow-hidden rounded-[var(--radius-xl)] border border-border bg-ink",
        className,
      )}
      role="application"
      aria-label="Events map"
    />
  );
}

export function boundsFromPins(pins: MapEventPin[]): MapBounds | null {
  const coords = pins
    .map((p) => {
      const lat = Number(p.latitude);
      const lng = Number(p.longitude);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
      return { lat, lng };
    })
    .filter((c): c is MapLatLng => c != null);
  if (!coords.length) return null;
  let north = -90;
  let south = 90;
  let east = -180;
  let west = 180;
  for (const c of coords) {
    north = Math.max(north, c.lat);
    south = Math.min(south, c.lat);
    east = Math.max(east, c.lng);
    west = Math.min(west, c.lng);
  }
  if (north === south) {
    north += 0.05;
    south -= 0.05;
  }
  if (east === west) {
    east += 0.05;
    west -= 0.05;
  }
  return { north, south, east, west };
}
