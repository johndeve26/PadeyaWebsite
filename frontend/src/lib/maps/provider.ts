/** Map provider abstraction — Google today; Mapbox/Leaflet can implement the same surface. */

import { hasGoogleMapsApiKey, loadGoogleMaps } from "@/lib/google-maps";
import type {
  MapBounds,
  MapLatLng,
  MapProviderKind,
  MapViewport,
} from "@/lib/maps/types";

export type MapController = {
  /** Underlying google.maps.Map (or null for other providers). */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  native: any;
  setCenter: (center: MapLatLng) => void;
  setZoom: (zoom: number) => void;
  fitBounds: (bounds: MapBounds, padding?: number) => void;
  getViewport: () => MapViewport;
  panTo: (center: MapLatLng) => void;
  destroy: () => void;
};

export type CreateMapOptions = {
  container: HTMLElement;
  center: MapLatLng;
  zoom?: number;
  onViewportChange?: (viewport: MapViewport) => void;
  onIdle?: (viewport: MapViewport) => void;
};

export function detectMapProvider(): MapProviderKind {
  if (typeof window === "undefined") return "none";
  return hasGoogleMapsApiKey() ? "google" : "none";
}

export async function createMapController(
  options: CreateMapOptions,
): Promise<MapController | null> {
  if (detectMapProvider() !== "google") return null;
  return createGoogleMapController(options);
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function readGoogleBounds(map: any): MapBounds | null {
  const b = map.getBounds?.();
  if (!b) return null;
  const ne = b.getNorthEast();
  const sw = b.getSouthWest();
  return {
    north: ne.lat(),
    south: sw.lat(),
    east: ne.lng(),
    west: sw.lng(),
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function viewportFrom(map: any): MapViewport {
  const c = map.getCenter?.();
  return {
    center: { lat: c?.lat?.() ?? 6.5244, lng: c?.lng?.() ?? 3.3792 },
    zoom: map.getZoom?.() ?? 11,
    bounds: readGoogleBounds(map),
  };
}

async function createGoogleMapController(
  options: CreateMapOptions,
): Promise<MapController> {
  await loadGoogleMaps();
  const g = window.google;
  if (!g?.maps?.Map) {
    throw new Error("Google Maps failed to load");
  }

  const map = new g.maps.Map(options.container, {
    center: options.center,
    zoom: options.zoom ?? 11,
    mapTypeControl: false,
    streetViewControl: false,
    fullscreenControl: false,
    clickableIcons: false,
    gestureHandling: "greedy",
    styles: GOOGLE_DARK_STYLE,
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const listeners: any[] = [];
  const emit = (kind: "change" | "idle") => {
    const vp = viewportFrom(map);
    if (kind === "change") options.onViewportChange?.(vp);
    else options.onIdle?.(vp);
  };

  listeners.push(g.maps.event.addListener(map, "bounds_changed", () => emit("change")));
  listeners.push(g.maps.event.addListener(map, "idle", () => emit("idle")));

  return {
    native: map,
    setCenter(center) {
      map.setCenter(center);
    },
    setZoom(zoom) {
      map.setZoom(zoom);
    },
    fitBounds(bounds, padding = 48) {
      map.fitBounds(
        {
          north: bounds.north,
          south: bounds.south,
          east: bounds.east,
          west: bounds.west,
        },
        padding,
      );
    },
    getViewport() {
      return viewportFrom(map);
    },
    panTo(center) {
      map.panTo(center);
    },
    destroy() {
      for (const l of listeners) {
        if (typeof l?.remove === "function") l.remove();
      }
    },
  };
}

/** Dark / ink map chrome aligned with Pàdéyá — accent markers drawn separately. */
export const GOOGLE_DARK_STYLE = [
  { elementType: "geometry", stylers: [{ color: "#1a1a1a" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#1a1a1a" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#8a8a8a" }] },
  {
    featureType: "administrative",
    elementType: "geometry.stroke",
    stylers: [{ color: "#2e2e2e" }],
  },
  { featureType: "poi", stylers: [{ visibility: "off" }] },
  {
    featureType: "road",
    elementType: "geometry",
    stylers: [{ color: "#2a2a2a" }],
  },
  {
    featureType: "road",
    elementType: "geometry.stroke",
    stylers: [{ color: "#222222" }],
  },
  { featureType: "transit", stylers: [{ visibility: "off" }] },
  {
    featureType: "water",
    elementType: "geometry",
    stylers: [{ color: "#0e0e0e" }],
  },
];
