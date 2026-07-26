import type { SortKey } from "@/lib/discovery/event-filters";
import type { NearbyRadiusKm } from "@/lib/discovery/geo-location";

import type { DatePreset, EventsViewMode } from "./marketplace-listing";

export type EventsLocationUrlState = {
  lat: number;
  lng: number;
  radiusKm: NearbyRadiusKm | number;
  label?: string | null;
};

export type EventsUrlSyncState = {
  city: string;
  date: DatePreset;
  priceMin: number;
  priceMax: number;
  priceBoundMax: number;
  /** Deep-link or user-changed price — never default slider ceiling alone. */
  syncPriceToUrl: boolean;
  sort: SortKey;
  view: EventsViewMode;
  proximityActive: boolean;
  /** Deep-link or explicit near-me — never silent autoLocate / stored-only. */
  syncLocationToUrl: boolean;
  location: EventsLocationUrlState | null;
};

type SearchParamsLike = {
  get(name: string): string | null;
};

/**
 * Parse lat/lng query params. Missing params must not become 0
 * (`Number(null) === 0` was writing lat=0&lng=0 on bare /events).
 */
export function parseLatLngSearchParams(
  searchParams: SearchParamsLike,
): { lat: number; lng: number } | null {
  const latRaw = searchParams.get("lat");
  const lngRaw = searchParams.get("lng");
  if (latRaw == null || latRaw === "" || lngRaw == null || lngRaw === "") {
    return null;
  }
  const lat = Number(latRaw);
  const lng = Number(lngRaw);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  // Null Island placeholder — never treat as a real deep link.
  if (lat === 0 && lng === 0) return null;
  return { lat, lng };
}

/** Build listing query string from intentional filter state only. */
export function buildEventsListingSearchParams(
  state: EventsUrlSyncState,
): URLSearchParams {
  const params = new URLSearchParams();
  if (state.city !== "all" && !state.proximityActive) {
    params.set("city", state.city);
    params.set("location_kind", "city");
    params.set("location_slug", state.city);
  }
  if (state.date !== "any") params.set("date", state.date);
  if (state.date === "this-weekend") params.set("weekend", "1");
  if (state.syncPriceToUrl) {
    if (state.priceMin > 0) params.set("price_min", String(state.priceMin));
    if (state.priceMax < state.priceBoundMax) {
      params.set("price_max", String(state.priceMax));
    }
  }
  if (state.sort !== "recommended") params.set("sort", state.sort);
  if (state.view !== "grid") params.set("view", state.view);
  if (
    state.syncLocationToUrl &&
    state.proximityActive &&
    state.location &&
    !(state.location.lat === 0 && state.location.lng === 0)
  ) {
    params.set("lat", String(state.location.lat));
    params.set("lng", String(state.location.lng));
    params.set("radius", String(state.location.radiusKm));
    if (state.location.label) {
      params.set("location_label", state.location.label);
    }
  }
  return params;
}

export function buildEventsListingHref(
  pathname: string,
  state: EventsUrlSyncState,
): string {
  const qs = buildEventsListingSearchParams(state).toString();
  return qs ? `${pathname}?${qs}` : pathname;
}
