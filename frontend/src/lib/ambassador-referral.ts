/**
 * Ambassador referral capture: ?ref= / ?amb=, 30-day cookie, last-click wins.
 * Explicit checkout code always beats cookie/link when placing an order.
 */

import { publicShareOrigin } from "@/lib/seo/site";

export const AMBASSADOR_REFERRAL_COOKIE_DAYS = 30;
export const AMBASSADOR_REFERRAL_COOKIE = "padeya_amb_ref_v1";

export type ReferralAttributionSource = "explicit" | "link" | "cookie";

type RefEntry = { code: string; at: number };
type RefStore = Record<string, RefEntry>;

function readStore(): RefStore {
  if (typeof document === "undefined") return {};
  const raw = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${AMBASSADOR_REFERRAL_COOKIE}=`))
    ?.split("=")
    .slice(1)
    .join("=");
  if (!raw) return {};
  try {
    const parsed = JSON.parse(decodeURIComponent(raw)) as RefStore;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeStore(store: RefStore): void {
  if (typeof document === "undefined") return;
  const maxAge = AMBASSADOR_REFERRAL_COOKIE_DAYS * 24 * 60 * 60;
  const value = encodeURIComponent(JSON.stringify(store));
  document.cookie = `${AMBASSADOR_REFERRAL_COOKIE}=${value}; path=/; max-age=${maxAge}; SameSite=Lax`;
}

export function normalizeAmbassadorCode(raw: string | null | undefined): string {
  return (raw || "").trim().toLowerCase();
}

/** Read ref from URL — supports ?ref= and ?amb= (amb aliases ref). */
export function readAmbassadorCodeFromSearchParams(
  searchParams: URLSearchParams | { get: (key: string) => string | null },
): string {
  const ref = normalizeAmbassadorCode(searchParams.get("ref"));
  if (ref) return ref;
  return normalizeAmbassadorCode(searchParams.get("amb"));
}

/** Last-click: store/overwrite cookie for this event key (slug or id). */
export function captureAmbassadorReferral(
  eventKey: string,
  code: string,
): string | null {
  const normalized = normalizeAmbassadorCode(code);
  if (!eventKey || !normalized) return null;
  const store = readStore();
  store[eventKey] = { code: normalized, at: Date.now() };
  writeStore(store);
  return normalized;
}

export function getAmbassadorReferralCookie(eventKey: string): string | null {
  if (!eventKey) return null;
  const entry = readStore()[eventKey];
  if (!entry?.code) return null;
  const ageMs = Date.now() - (entry.at || 0);
  const maxMs = AMBASSADOR_REFERRAL_COOKIE_DAYS * 24 * 60 * 60 * 1000;
  if (ageMs > maxMs) return null;
  return normalizeAmbassadorCode(entry.code);
}

/**
 * Checkout attribution precedence:
 * 1. Explicit code typed at checkout
 * 2. URL ?ref= / ?amb= (also refreshes cookie — last click)
 * 3. Cookie within 30 days
 */
export function resolveCheckoutReferral(input: {
  eventKey: string;
  urlCode?: string | null;
  explicitCode?: string | null;
}): { code: string | null; source: ReferralAttributionSource | null } {
  const explicit = normalizeAmbassadorCode(input.explicitCode);
  if (explicit) {
    return { code: explicit, source: "explicit" };
  }
  const fromUrl = normalizeAmbassadorCode(input.urlCode);
  if (fromUrl) {
    captureAmbassadorReferral(input.eventKey, fromUrl);
    return { code: fromUrl, source: "link" };
  }
  const fromCookie = getAmbassadorReferralCookie(input.eventKey);
  if (fromCookie) {
    return { code: fromCookie, source: "cookie" };
  }
  return { code: null, source: null };
}

export function buildAmbassadorEventLink(
  slug: string,
  code: string,
  opts?: { origin?: string; merch?: boolean },
): string {
  const display = normalizeAmbassadorCode(code);
  const path = opts?.merch
    ? `/events/${slug}/merch?ref=${display}`
    : `/events/${slug}?ref=${display}`;
  const origin = opts?.origin;
  if (origin) return `${origin.replace(/\/$/, "")}${path}`;
  if (typeof window !== "undefined") return `${window.location.origin}${path}`;
  return path;
}

/**
 * Full shareable referral URL. Prefers the event landing page when a slug
 * exists; otherwise falls back to site root with `?ref=`.
 * Always uses the public live origin (not localhost) unless an explicit
 * non-local origin is passed.
 */
export function buildAmbassadorReferralLink(
  code: string,
  opts?: {
    slug?: string | null;
    merch?: boolean;
    origin?: string;
  },
): string {
  const explicit = opts?.origin?.replace(/\/$/, "") || "";
  const origin =
    explicit && !/localhost|127\.0\.0\.1/i.test(explicit)
      ? explicit
      : publicShareOrigin();
  const slug = (opts?.slug || "").trim();
  if (slug) {
    return buildAmbassadorEventLink(slug, code, {
      origin,
      merch: opts?.merch,
    });
  }
  const display = normalizeAmbassadorCode(code);
  return `${origin}/events?ref=${display}`;
}

export function formatAmbassadorCodeDisplay(code: string): string {
  return normalizeAmbassadorCode(code).toUpperCase();
}
