/**
 * Canonical path helpers — strip tracking/referral query noise from SEO URLs.
 * Does not redirect; attribution can keep query params on the live request.
 */

const TRACKING_QUERY_KEYS = new Set([
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_term",
  "utm_content",
  "utm_id",
  "gclid",
  "fbclid",
  "msclkid",
  "ref",
  "referral",
  "ambassador",
  "amb",
  "code",
]);

/** Path only (leading slash), never includes query or hash. */
export function canonicalPathOnly(path: string): string {
  const raw = path.trim() || "/";
  try {
    // Support absolute or relative.
    if (raw.startsWith("http://") || raw.startsWith("https://")) {
      const u = new URL(raw);
      return u.pathname || "/";
    }
  } catch {
    // fall through
  }
  const noHash = raw.split("#")[0] || "/";
  const pathPart = noHash.split("?")[0] || "/";
  return pathPart.startsWith("/") ? pathPart : `/${pathPart}`;
}

/**
 * Drop tracking params from a path+query string. Non-tracking facets
 * (e.g. category on /events) are not rewritten here — hub pages own those
 * canonicals via static paths.
 */
export function stripTrackingSearchParams(pathWithOptionalQuery: string): string {
  const pathOnly = canonicalPathOnly(pathWithOptionalQuery);
  const qIndex = pathWithOptionalQuery.indexOf("?");
  if (qIndex === -1) return pathOnly;

  const params = new URLSearchParams(pathWithOptionalQuery.slice(qIndex + 1));
  let changed = false;
  for (const key of [...params.keys()]) {
    if (TRACKING_QUERY_KEYS.has(key.toLowerCase()) || key.toLowerCase().startsWith("utm_")) {
      params.delete(key);
      changed = true;
    }
  }
  if (!changed || [...params.keys()].length === 0) {
    return pathOnly;
  }
  // Phase 0A: still collapse to path-only for generic filter URLs that only
  // had tracking params. Remaining non-tracking params are dropped from
  // canonicals for /events list safety (canonical stays /events via callers).
  return pathOnly;
}
