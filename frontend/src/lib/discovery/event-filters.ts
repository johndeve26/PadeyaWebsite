import { matchCitySlug } from "@/lib/discovery/slugify";
import type { EventItem, TicketType } from "@/lib/types/events";

export type SortKey =
  | "recommended"
  | "soonest"
  | "newest"
  | "featured"
  | "price_asc"
  | "price_desc"
  | "trending";

export type EventDiscoveryFilters = {
  q?: string;
  /** Category slug (`event.category?.slug`). */
  category?: string;
  /** City hub slug matched via `matchCitySlug`. */
  city?: string;
  /** When true, keep events whose start falls in `weekendWindow`. */
  weekend?: boolean;
  /** When true, keep events whose start is today (local calendar day). */
  today?: boolean;
  paid?: "free" | "paid" | "any";
  /** Keep events whose cheapest ticket is at least this amount (NGN). */
  min_price?: number;
  /** Keep events whose cheapest ticket is at most this amount (NGN). */
  max_price?: number;
  /** Matches `event.event_type` (e.g. online, hybrid, public). */
  event_format?: string;
  /** When true, keep secret-location style events. */
  secret_location?: boolean;
  /** When true, include events whose end time is already past. Default: upcoming only. */
  include_past?: boolean;
  sort?: SortKey;
};

/** True when the event has not ended yet (live or future). */
export function isUpcomingEvent(event: EventItem, nowMs = Date.now()): boolean {
  const end = Date.parse(event.end_datetime || event.start_datetime);
  return Number.isFinite(end) && end >= nowMs;
}

const FREE_KINDS = new Set(["free", "free_rsvp", "donation"]);
const VIP_KINDS = new Set(["vip", "vvip"]);

function ticketPrice(t: TicketType): number {
  const n = Number(t.price);
  return Number.isFinite(n) ? n : Number.POSITIVE_INFINITY;
}

/** Lowest finite ticket price, or null when there are no usable prices. */
export function minTicketPrice(event: EventItem): number | null {
  const types = event.ticket_types ?? [];
  if (!types.length) return null;
  const prices = types.map(ticketPrice).filter((n) => Number.isFinite(n));
  if (!prices.length) return null;
  return Math.min(...prices);
}

/** True when the cheapest public ticket is free (price ≤ 0 or free kinds). */
export function isFreeEvent(event: EventItem): boolean {
  const types = event.ticket_types ?? [];
  if (!types.length) return false;
  const min = minTicketPrice(event);
  if (min != null && min <= 0) return true;
  return types.some((t) => FREE_KINDS.has(String(t.type || "").toLowerCase()));
}

/** True when any ticket tier is VIP / VVIP. */
export function isVipEvent(event: EventItem): boolean {
  const types = event.ticket_types ?? [];
  return types.some((t) => VIP_KINDS.has(String(t.type || "").toLowerCase()));
}

function isSecretLocationEvent(event: EventItem): boolean {
  if (event.event_type === "secret_location") return true;
  const vis = event.location_visibility;
  return (
    vis === "hidden_until_payment" ||
    vis === "hidden_until_24h_before" ||
    vis === "hidden_until_manual_approval"
  );
}

/**
 * Upcoming Fri 00:00 → Sun 23:59:59.999 using local `Date`
 * (Africa/Lagos-approx when the runtime TZ is WAT).
 * If `now` is Fri–Sun, returns that weekend; otherwise the next one.
 */
export function weekendWindow(now: Date = new Date()): {
  start: Date;
  end: Date;
} {
  const day = now.getDay(); // 0=Sun … 5=Fri 6=Sat
  let daysToFriday: number;
  if (day === 5) daysToFriday = 0;
  else if (day === 6) daysToFriday = -1;
  else if (day === 0) daysToFriday = -2;
  else daysToFriday = 5 - day;

  const start = new Date(now);
  start.setDate(now.getDate() + daysToFriday);
  start.setHours(0, 0, 0, 0);

  const end = new Date(start);
  end.setDate(start.getDate() + 2);
  end.setHours(23, 59, 59, 999);

  return { start, end };
}

/** True when event start is on the same local calendar day as `now`. */
export function isTodayEvent(event: EventItem, now: Date = new Date()): boolean {
  const start = new Date(event.start_datetime);
  if (Number.isNaN(start.getTime())) return false;
  return (
    start.getFullYear() === now.getFullYear() &&
    start.getMonth() === now.getMonth() &&
    start.getDate() === now.getDate()
  );
}

function matchesQuery(event: EventItem, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  const vis = event.location_visibility || "full_public";
  const placeBits =
    vis === "full_public"
      ? [event.city, event.venue_name, event.public_location_label]
      : vis === "area_only"
        ? [event.city, event.public_location_label, event.location?.name]
        : vis === "online_only"
          ? [event.public_location_label, "online event"]
          : [event.public_location_label];
  const hay = [
    event.title,
    event.short_tagline,
    event.description,
    ...placeBits,
    event.category?.name,
    event.host_display_name,
    ...(event.discoverable_keywords ?? []),
    ...(event.hashtags ?? []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return hay.includes(needle);
}

function compareEvents(
  a: EventItem,
  b: EventItem,
  sort: SortKey,
): number {
  switch (sort) {
    case "newest": {
      const at = Date.parse(a.published_at || a.created_at);
      const bt = Date.parse(b.published_at || b.created_at);
      return (Number.isFinite(bt) ? bt : 0) - (Number.isFinite(at) ? at : 0);
    }
    case "featured": {
      if (a.featured !== b.featured) return a.featured ? -1 : 1;
      return (
        Date.parse(a.start_datetime) - Date.parse(b.start_datetime) ||
        a.title.localeCompare(b.title)
      );
    }
    case "price_asc":
    case "price_desc": {
      const ap = minTicketPrice(a);
      const bp = minTicketPrice(b);
      const av = ap == null ? Number.POSITIVE_INFINITY : ap;
      const bv = bp == null ? Number.POSITIVE_INFINITY : bp;
      const diff = sort === "price_asc" ? av - bv : bv - av;
      if (diff !== 0) return diff;
      return Date.parse(a.start_datetime) - Date.parse(b.start_datetime);
    }
    case "recommended":
    case "trending": {
      // Soft ranking: featured → soonest upcoming.
      if (a.featured !== b.featured) return a.featured ? -1 : 1;
      return Date.parse(a.start_datetime) - Date.parse(b.start_datetime);
    }
    case "soonest":
    default:
      return Date.parse(a.start_datetime) - Date.parse(b.start_datetime);
  }
}

/** Client-side filter + sort for public discovery lists. */
export function filterPublicEvents(
  events: EventItem[],
  filters: EventDiscoveryFilters = {},
): EventItem[] {
  const {
    q,
    category,
    city,
    weekend,
    today,
    paid = "any",
    min_price,
    max_price,
    event_format,
    secret_location,
    include_past = false,
    sort = "soonest",
  } = filters;

  const nowMs = Date.now();
  const now = new Date(nowMs);
  const window = weekend ? weekendWindow(now) : null;
  const minPrice =
    typeof min_price === "number" && Number.isFinite(min_price) && min_price >= 0
      ? min_price
      : null;
  const maxPrice =
    typeof max_price === "number" && Number.isFinite(max_price) && max_price >= 0
      ? max_price
      : null;

  const filtered = events.filter((event) => {
    if (!include_past && !isUpcomingEvent(event, nowMs)) return false;

    if (q && !matchesQuery(event, q)) return false;

    if (category) {
      const slug = event.category?.slug;
      if (!slug || slug !== category) return false;
    }

    if (city && !matchCitySlug(event.city, city)) return false;

    if (today && !isTodayEvent(event, now)) return false;

    if (window) {
      const start = Date.parse(event.start_datetime);
      if (
        !Number.isFinite(start) ||
        start < window.start.getTime() ||
        start > window.end.getTime()
      ) {
        return false;
      }
    }

    if (paid === "free" && !isFreeEvent(event)) return false;
    if (paid === "paid") {
      const min = minTicketPrice(event);
      if (min == null || min <= 0) return false;
    }

    if (minPrice != null) {
      const min = minTicketPrice(event);
      if (min == null || min < minPrice) return false;
    }

    if (maxPrice != null) {
      const min = minTicketPrice(event);
      if (min == null || min > maxPrice) return false;
    }

    if (event_format) {
      const format = String(event.event_type || "").toLowerCase();
      if (format !== event_format.toLowerCase()) return false;
    }

    if (secret_location === true && !isSecretLocationEvent(event)) {
      return false;
    }

    return true;
  });

  return [...filtered].sort((a, b) => compareEvents(a, b, sort));
}
