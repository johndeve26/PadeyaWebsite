import type { EventItem } from "@/lib/types/events";
import { getGoogleMapsApiKey } from "@/lib/google-maps";

/** Try to pull lat/lng from common Google Maps share / place URLs. */
export function parseMapsUrlCoords(url: string): {
  latitude: string;
  longitude: string;
} | null {
  const raw = url.trim();
  if (!raw) return null;
  try {
    const at = raw.match(/@(-?\d+\.?\d*),(-?\d+\.?\d*)/);
    if (at) return { latitude: at[1], longitude: at[2] };
    const q = raw.match(/[?&]q=(-?\d+\.?\d*),(-?\d+\.?\d*)/);
    if (q) return { latitude: q[1], longitude: q[2] };
    const ll = raw.match(/[?&]ll=(-?\d+\.?\d*),(-?\d+\.?\d*)/);
    if (ll) return { latitude: ll[1], longitude: ll[2] };
    const dest = raw.match(/destination=(-?\d+\.?\d*)%2C(-?\d+\.?\d*)/i);
    if (dest) return { latitude: dest[1], longitude: dest[2] };
  } catch {
    return null;
  }
  return null;
}

/**
 * Embed URL for public event maps.
 * Uses Maps Embed API when NEXT_PUBLIC_GOOGLE_MAPS_API_KEY is set; otherwise keyless fallback.
 */
export function mapEmbedSrc(lat: string, lng: string, zoom = 14): string {
  const key = getGoogleMapsApiKey();
  if (key) {
    const q = encodeURIComponent(`${lat},${lng}`);
    return (
      `https://www.google.com/maps/embed/v1/place?key=${encodeURIComponent(key)}` +
      `&q=${q}&zoom=${zoom}`
    );
  }
  return `https://maps.google.com/maps?q=${encodeURIComponent(`${lat},${lng}`)}&z=${zoom}&output=embed`;
}

export function eventMapMode(
  event: Pick<EventItem, "location_map_mode" | "location_visibility">,
): "exact" | "approximate" | "none" {
  if (event.location_visibility === "online_only") return "none";
  const mode = event.location_map_mode;
  if (mode === "exact" || mode === "approximate" || mode === "none") return mode;
  return "none";
}
