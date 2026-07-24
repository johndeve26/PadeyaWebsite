/**
 * Faceted navigation / index-bloat policy (Phase 1B).
 *
 * Curated landings (/events/c/*, /events/city/*, weekend, free, vip, …) may index.
 * Arbitrary /events?filter=… combinations canonicalize to /events and are noindex.
 */

/** Query keys that make /events a filter/search result surface (noindex). */
export const EVENTS_FACET_QUERY_KEYS = [
  "q",
  "sort",
  "category",
  "city",
  "area",
  "state",
  "country",
  "price",
  "date",
  "free",
  "vip",
  "online",
  "paid",
  "weekend",
  "location_kind",
  "location_slug",
  "view",
  "near",
  "lat",
  "lng",
  "radius",
  "type",
  "host",
] as const;

const FACET_SET = new Set<string>(
  EVENTS_FACET_QUERY_KEYS.map((k) => k.toLowerCase()),
);

function isTrackingParam(key: string): boolean {
  const k = key.toLowerCase();
  return (
    k.startsWith("utm_") ||
    k === "ref" ||
    k === "gclid" ||
    k === "fbclid" ||
    k === "msclkid"
  );
}

function paramPresent(
  value: string | string[] | undefined | null,
): boolean {
  if (value == null) return false;
  if (Array.isArray(value)) return value.some((v) => String(v).trim() !== "");
  return String(value).trim() !== "";
}

/**
 * True when /events has filter/search query params that must not create
 * indexable duplicate URLs. Tracking-only params do not trigger noindex.
 */
export function hasEventsFacetQuery(
  searchParams:
    | Record<string, string | string[] | undefined>
    | URLSearchParams
    | null
    | undefined,
): boolean {
  if (!searchParams) return false;

  if (searchParams instanceof URLSearchParams) {
    for (const key of searchParams.keys()) {
      if (isTrackingParam(key)) continue;
      if (FACET_SET.has(key.toLowerCase()) && paramPresent(searchParams.get(key))) {
        return true;
      }
    }
    return false;
  }

  for (const [key, value] of Object.entries(searchParams)) {
    if (isTrackingParam(key)) continue;
    if (FACET_SET.has(key.toLowerCase()) && paramPresent(value)) return true;
  }
  return false;
}

/** Canonical parent for all /events marketplace query variants. */
export const EVENTS_FACET_CANONICAL_PATH = "/events";

/**
 * /events/search is a legacy duplicate surface — never index; consolidate to /events.
 */
export function eventsSearchPageMetadataPolicy(): {
  path: string;
  canonicalPath: string;
  noIndex: boolean;
} {
  return {
    path: "/events/search",
    canonicalPath: EVENTS_FACET_CANONICAL_PATH,
    noIndex: true,
  };
}
