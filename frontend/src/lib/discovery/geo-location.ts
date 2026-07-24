/** Client discovery location preference (session / localStorage — not sent to server by default). */

export const DISCOVERY_LOCATION_KEY = "padeya.discovery.location";

export const NEARBY_RADIUS_OPTIONS = [5, 10, 25, 50, 100] as const;
export type NearbyRadiusKm = (typeof NEARBY_RADIUS_OPTIONS)[number];

export type DiscoveryLocation = {
  lat: number;
  lng: number;
  label: string;
  radiusKm: NearbyRadiusKm;
  source: "geo" | "manual" | "profile" | "url";
  savedAt: number;
};

export function formatDistanceLabel(
  km: number | null | undefined,
  approximate = false,
): string | null {
  if (km == null || !Number.isFinite(km)) return null;
  let label: string;
  if (km < 0.1) label = "Nearby";
  else if (km < 10) label = `${km.toFixed(1)} km away`;
  else label = `${Math.round(km)} km away`;
  return approximate && km >= 0.1 ? `About ${label}` : label;
}

/** Great-circle distance in kilometres (Haversine). */
export function haversineKm(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number,
): number {
  const r = 6371;
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const p1 = toRad(lat1);
  const p2 = toRad(lat2);
  const dPhi = toRad(lat2 - lat1);
  const dLmb = toRad(lng2 - lng1);
  const a =
    Math.sin(dPhi / 2) ** 2 +
    Math.cos(p1) * Math.cos(p2) * Math.sin(dLmb / 2) ** 2;
  return 2 * r * Math.asin(Math.min(1, Math.sqrt(a)));
}

export function readStoredDiscoveryLocation(): DiscoveryLocation | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(DISCOVERY_LOCATION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as DiscoveryLocation;
    if (
      typeof parsed?.lat !== "number" ||
      typeof parsed?.lng !== "number" ||
      !parsed.label
    ) {
      return null;
    }
    const radius = NEARBY_RADIUS_OPTIONS.includes(
      parsed.radiusKm as NearbyRadiusKm,
    )
      ? (parsed.radiusKm as NearbyRadiusKm)
      : 25;
    return { ...parsed, radiusKm: radius };
  } catch {
    return null;
  }
}

export function storeDiscoveryLocation(loc: DiscoveryLocation): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(DISCOVERY_LOCATION_KEY, JSON.stringify(loc));
}

export function clearStoredDiscoveryLocation(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(DISCOVERY_LOCATION_KEY);
}

export type GeolocationPermissionState = "granted" | "prompt" | "denied" | "unknown";

/** Best-effort Permissions API check — never throws; unknown when unsupported. */
export async function queryGeolocationPermission(): Promise<GeolocationPermissionState> {
  if (typeof navigator === "undefined" || !navigator.geolocation) {
    return "denied";
  }
  try {
    const permissions = navigator.permissions;
    if (!permissions?.query) return "unknown";
    const status = await permissions.query({
      name: "geolocation" as PermissionName,
    });
    if (status.state === "granted" || status.state === "prompt" || status.state === "denied") {
      return status.state;
    }
    return "unknown";
  } catch {
    return "unknown";
  }
}

export function requestBrowserGeolocation(): Promise<{
  lat: number;
  lng: number;
}> {
  return new Promise((resolve, reject) => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      reject(new Error("Location is not available in this browser."));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        resolve({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
        });
      },
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          reject(new Error("Location permission denied."));
        } else if (err.code === err.TIMEOUT) {
          reject(new Error("Location request timed out."));
        } else {
          reject(new Error("Could not read your location."));
        }
      },
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 60_000 },
    );
  });
}
