/**
 * Session-scoped geolocation consent helpers.
 * Declined → never re-prompt in the same browser session.
 * Precise GPS is only stored via storeDiscoveryLocation after explicit accept/manual save.
 */

export const GEO_DECLINED_SESSION_KEY = "padeya.discovery.geo_declined";

export function readGeoDeclinedSession(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.sessionStorage.getItem(GEO_DECLINED_SESSION_KEY) === "1";
  } catch {
    return false;
  }
}

export function markGeoDeclinedSession(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(GEO_DECLINED_SESSION_KEY, "1");
  } catch {
    // ignore quota / private mode
  }
}

export function clearGeoDeclinedSession(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(GEO_DECLINED_SESSION_KEY);
  } catch {
    // ignore
  }
}

/** Friendly copy when the user declines browser location. */
export const GEO_DECLINED_COPY = {
  eyebrow: "No location access? No problem.",
  message:
    "No problem — you can still browse events by city, date, or category.",
  chooseCity: "Choose a city to see events around that area.",
  browsePicks: "Browse Pàdéyá Picks while you decide.",
  chooseCityCta: "Choose your city",
  browseAll: "Browse all events",
  thisWeekend: "View this weekend",
  useSearch: "Use search",
} as const;
