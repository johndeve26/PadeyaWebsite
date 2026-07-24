import {
  filterPublicEvents,
  isVipEvent,
  minTicketPrice,
  weekendWindow,
  type EventDiscoveryFilters,
  type SortKey,
} from "@/lib/discovery/event-filters";
import {
  formatDistanceLabel,
  haversineKm,
} from "@/lib/discovery/geo-location";
import { ticketAvailabilityLabel } from "@/lib/discovery/marketplace-groups";
import type { EventItem } from "@/lib/types/events";

function parseCoord(value: string | number | null | undefined): number | null {
  if (value == null || value === "") return null;
  const n = typeof value === "number" ? value : Number(String(value).trim());
  return Number.isFinite(n) ? n : null;
}

/** Privacy-safe discovery point for client-side distance sort (mirrors public map). */
export function eventDiscoveryCoords(
  event: EventItem,
): { lat: number; lng: number; approximate: boolean } | null {
  const mapLat = parseCoord(event.map_latitude);
  const mapLng = parseCoord(event.map_longitude);
  if (mapLat != null && mapLng != null) {
    return {
      lat: mapLat,
      lng: mapLng,
      approximate: event.location_map_mode === "approximate",
    };
  }
  const approxLat = parseCoord(event.approximate_latitude);
  const approxLng = parseCoord(event.approximate_longitude);
  if (approxLat != null && approxLng != null) {
    return { lat: approxLat, lng: approxLng, approximate: true };
  }
  const lat = parseCoord(event.latitude);
  const lng = parseCoord(event.longitude);
  if (lat != null && lng != null) {
    return { lat, lng, approximate: false };
  }
  return null;
}

/** Attach distance_km for nearest-first sort — does not filter by radius. */
export function enrichMarketplaceEventsWithDistance(
  events: EventItem[],
  lat: number,
  lng: number,
): EventItem[] {
  return events.map((event) => {
    const point = eventDiscoveryCoords(event);
    if (!point) {
      return {
        ...event,
        distance_km: null,
        distance_label: null,
        distance_is_approximate: false,
      };
    }
    const dist = haversineKm(lat, lng, point.lat, point.lng);
    const rounded = dist < 10 ? Math.round(dist * 10) / 10 : Math.round(dist);
    return {
      ...event,
      distance_km: rounded,
      distance_is_approximate: point.approximate,
      distance_label: formatDistanceLabel(rounded, point.approximate),
    };
  });
}

/** Nearest-first; events without coords last; ties break by soonest start. */
export function sortMarketplaceByProximity(events: EventItem[]): EventItem[] {
  return [...events].sort((a, b) => {
    const da = a.distance_km ?? Number.POSITIVE_INFINITY;
    const db = b.distance_km ?? Number.POSITIVE_INFINITY;
    if (da !== db) return da - db;
    return Date.parse(a.start_datetime) - Date.parse(b.start_datetime);
  });
}

export type EventsViewMode = "grid" | "list" | "calendar" | "map";

/** Tailwind `lg` — list/map switcher + clampEventsViewForViewport. */
export const EVENTS_LG_MEDIA_QUERY = "(min-width: 1024px)";

/** List + map need desktop split layout — hidden from mobile switcher. */
export const EVENTS_DESKTOP_ONLY_VIEWS: EventsViewMode[] = ["list", "map"];

export function isDesktopOnlyEventsView(view: EventsViewMode): boolean {
  return EVENTS_DESKTOP_ONLY_VIEWS.includes(view);
}

/** Fall back to grid on viewports below lg (matches EventMapView / filter bar). */
export function clampEventsViewForViewport(
  view: EventsViewMode,
  isLgUp: boolean,
): EventsViewMode {
  if (isLgUp || !isDesktopOnlyEventsView(view)) return view;
  return "grid";
}
export type DatePreset = "any" | "today" | "this-weekend" | "this-week";
export type AccessFilter =
  | "any"
  | "tickets"
  | "online"
  | "in_person"
  | "vip";

export const EVENTS_PAGE_SIZE = 12;
export const EVENTS_VIEW_STORAGE_KEY = "padeya.events.view";
/** Fallback slider ceiling when no ticket prices are available (NGN). */
export const DEFAULT_PRICE_BOUND_MAX = 500;

/** Absolute max for the marketplace price range slider from listing data. */
export function computePriceBoundMax(
  events: EventItem[],
  fallback = DEFAULT_PRICE_BOUND_MAX,
): number {
  let highest = 0;
  for (const event of events) {
    const min = minTicketPrice(event);
    if (min != null && min > highest) highest = min;
  }
  if (highest <= 0) return fallback;
  return Math.max(fallback, Math.ceil(highest));
}

/** Step size for the marketplace price range slider. */
export function priceRangeStep(boundMax: number): number {
  if (boundMax <= 1_000) return 50;
  if (boundMax <= 10_000) return 100;
  if (boundMax <= 50_000) return 500;
  return 1_000;
}

export function parsePriceParam(raw: string | null | undefined): number | null {
  if (raw == null || raw === "") return null;
  const n = Number(raw);
  return Number.isFinite(n) && n >= 0 ? n : null;
}

export const EVENTS_SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "recommended", label: "Recommended" },
  { value: "soonest", label: "Soonest" },
  { value: "newest", label: "Newest" },
  { value: "price_asc", label: "Price low to high" },
  { value: "price_desc", label: "Price high to low" },
  { value: "trending", label: "Most popular" },
];

export function parseEventsView(raw: string | null | undefined): EventsViewMode {
  if (raw === "list" || raw === "calendar" || raw === "grid" || raw === "map") {
    return raw;
  }
  if (raw === "compact") return "list";
  return "grid";
}

export function readStoredEventsView(): EventsViewMode | null {
  if (typeof window === "undefined") return null;
  try {
    return parseEventsView(window.localStorage.getItem(EVENTS_VIEW_STORAGE_KEY));
  } catch {
    return null;
  }
}

export function storeEventsView(view: EventsViewMode) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(EVENTS_VIEW_STORAGE_KEY, view);
  } catch {
    /* ignore */
  }
}

export function parseSortKey(raw: string | null | undefined): SortKey {
  const allowed = EVENTS_SORT_OPTIONS.map((o) => o.value);
  if (raw && allowed.includes(raw as SortKey)) return raw as SortKey;
  if (raw === "featured") return "recommended";
  return "recommended";
}

export function parseDatePreset(raw: string | null | undefined): DatePreset {
  if (raw === "today" || raw === "this-week" || raw === "any") return raw;
  if (raw === "this-weekend" || raw === "weekend") return "this-weekend";
  return "any";
}

function startOfDay(d: Date): Date {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

function endOfDay(d: Date): Date {
  const x = new Date(d);
  x.setHours(23, 59, 59, 999);
  return x;
}

function thisWeekWindow(now = new Date()): { start: Date; end: Date } {
  const day = now.getDay(); // 0 Sun
  const start = startOfDay(now);
  start.setDate(now.getDate() - day);
  const end = endOfDay(now);
  end.setDate(start.getDate() + 6);
  return { start, end };
}

function matchesDatePreset(event: EventItem, preset: DatePreset): boolean {
  if (preset === "any") return true;
  const t = Date.parse(event.start_datetime);
  if (!Number.isFinite(t)) return false;
  const now = new Date();
  if (preset === "today") {
    return t >= startOfDay(now).getTime() && t <= endOfDay(now).getTime();
  }
  if (preset === "this-weekend") {
    const { start, end } = weekendWindow(now);
    return t >= start.getTime() && t <= end.getTime();
  }
  if (preset === "this-week") {
    const { start, end } = thisWeekWindow(now);
    return t >= start.getTime() && t <= end.getTime();
  }
  return true;
}

function matchesAccess(event: EventItem, access: AccessFilter): boolean {
  if (access === "any") return true;
  const format = String(event.event_type || "").toLowerCase();
  if (access === "online") return format === "online";
  if (access === "in_person") {
    return format === "public" || format === "in_person" || format === "hybrid" || !format;
  }
  if (access === "vip") return isVipEvent(event);
  if (access === "tickets") {
    const label = ticketAvailabilityLabel(event);
    return label !== "Sold out";
  }
  return true;
}

function matchesHost(event: EventItem, host: string): boolean {
  const needle = host.trim().toLowerCase().replace(/^@/, "");
  if (!needle) return true;
  const hay = [
    event.host_display_name,
    event.host_slug,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return hay.includes(needle);
}

export type MarketplaceListingFilters = EventDiscoveryFilters & {
  date?: DatePreset;
  access?: AccessFilter;
  host?: string;
};

/** Filter + sort for the /events marketplace listing. */
export function filterMarketplaceEvents(
  events: EventItem[],
  filters: MarketplaceListingFilters,
): EventItem[] {
  const date = filters.date || "any";
  const access = filters.access || "any";
  const host = filters.host || "";

  // weekend flag still supported via date preset
  const base = filterPublicEvents(events, {
    ...filters,
    weekend: date === "this-weekend" ? true : filters.weekend,
  });

  return base.filter(
    (event) =>
      matchesDatePreset(event, date) &&
      matchesAccess(event, access) &&
      matchesHost(event, host),
  );
}
