import {
  formatLandingPath,
  isFormatHubKey,
} from "@/lib/discovery/format-landing";

/** Format a max ticket price for price-hub titles (e.g. 5000 → ₦5,000). */
export function formatMaxPriceLabel(maxPrice: number): string {
  return `₦${maxPrice.toLocaleString("en-NG")}`;
}

/** Short label for breadcrumbs / metadata (no trailing period). */
export function priceLandingTitle(maxPrice: number): string {
  return `Under ${formatMaxPriceLabel(maxPrice)}`;
}

export function priceLandingDescription(maxPrice: number): string {
  return `Tickets from free up to ${formatMaxPriceLabel(maxPrice)} — verified hosts, real seats, no marketplace clutter.`;
}

export function priceLandingPath(maxPrice: number): string {
  return `/events/under/${maxPrice}`;
}

/** Parse a URL segment into a positive integer max price, or null. */
export function parseMaxPriceParam(raw: string): number | null {
  if (!/^\d+$/.test(raw)) return null;
  const n = Number(raw);
  if (!Number.isFinite(n) || n <= 0 || n > 10_000_000) return null;
  return n;
}

/**
 * Rewrite legacy `/events?…` browse hrefs to dedicated taxonomy hubs.
 * Handles `max_price` and `event_format` when they are the sole filter.
 */
export function normalizeBrowseHref(href: string): string {
  try {
    const url = new URL(href, "https://padeya.local");
    if (url.pathname !== "/events") return href;
    const keys = [...url.searchParams.keys()];
    if (keys.length !== 1) return href;

    if (url.searchParams.has("max_price")) {
      const parsed = parseMaxPriceParam(
        url.searchParams.get("max_price") || "",
      );
      return parsed != null ? priceLandingPath(parsed) : href;
    }

    if (url.searchParams.has("event_format")) {
      const fmt = (url.searchParams.get("event_format") || "").toLowerCase();
      return isFormatHubKey(fmt) ? formatLandingPath(fmt) : href;
    }

    return href;
  } catch {
    return href;
  }
}
