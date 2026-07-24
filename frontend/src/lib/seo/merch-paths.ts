/**
 * Merch URL classification — hubs vs product detail (`/merch/[slug]`).
 * Keep in sync with `frontend/src/app/merch/*` static routes.
 */

/** First path segment under `/merch/` that is never a product slug. */
export const RESERVED_MERCH_PATH_SEGMENTS = [
  "drops",
  "vault",
  "hosts",
] as const;

const RESERVED = new Set(
  RESERVED_MERCH_PATH_SEGMENTS.map((s) => s.toLowerCase()),
);

function normalizePathname(pathname: string): string {
  const raw = (pathname || "").trim();
  if (!raw) return "";
  try {
    if (raw.includes("://")) {
      return new URL(raw).pathname.replace(/\/+$/, "") || "/";
    }
  } catch {
    /* treat as path */
  }
  const p = raw.startsWith("/") ? raw : `/${raw}`;
  return p.replace(/\/+$/, "") || "/";
}

export function isReservedMerchSlug(slug: string | null | undefined): boolean {
  const s = (slug || "").trim().toLowerCase();
  return Boolean(s) && RESERVED.has(s);
}

/**
 * True for merch landing/hub/collection routes (not Product detail).
 * Includes `/merch`, `/merch-guide`, `/merch/drops`, `/merch/vault`, `/merch/hosts…`.
 */
export function isMerchHubPath(pathname: string): boolean {
  const p = normalizePathname(pathname).toLowerCase();
  if (p === "/merch" || p === "/merch-guide") return true;
  if (p === "/merch/hosts" || p.startsWith("/merch/hosts/")) return true;
  const m = p.match(/^\/merch\/([^/]+)$/);
  if (m && isReservedMerchSlug(m[1])) return true;
  return false;
}

/**
 * True for marketplace product detail paths: `/merch/{productSlug}`
 * where `{productSlug}` is not a reserved hub segment.
 */
export function isMerchProductPath(pathname: string): boolean {
  const p = normalizePathname(pathname);
  const m = p.match(/^\/merch\/([^/]+)$/i);
  if (!m?.[1]) return false;
  return !isReservedMerchSlug(m[1]);
}

/** First sitemap URL that is a real product detail page. */
export function pickMerchProductUrl(urls: string[]): string | null {
  for (const u of urls) {
    try {
      if (isMerchProductPath(new URL(u).pathname)) return u;
    } catch {
      /* skip */
    }
  }
  return null;
}

export type MerchProductSampleDecision =
  | { action: "check"; url: string }
  | { action: "skip"; message: string }
  | { action: "fail"; message: string };

/**
 * Non-strict: skip/warn when no product inventory.
 * Strict: fail clearly (launch inventory expected) — never blame a hub.
 */
export function decideMerchProductSample(
  productUrl: string | null | undefined,
  strict: boolean,
): MerchProductSampleDecision {
  if (productUrl) return { action: "check", url: productUrl };
  if (strict) {
    return {
      action: "fail",
      message: "No public indexable merch Product URL found",
    };
  }
  return {
    action: "skip",
    message:
      "No public indexable merch product available for Product JSON-LD sample",
  };
}
