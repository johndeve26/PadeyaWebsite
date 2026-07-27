/**
 * Authoritative redirect map for production domain + legacy URL migrations.
 *
 * Canonical origin: https://padeya.com
 * www.padeya.com → https://padeya.com (pathname + query preserved by Next.js)
 *
 * Rules:
 * - Only map known legacy URLs with a clear replacement (no catch-all 404 → /).
 * - Keep WordPress membership redirects separate from in-app product aliases.
 * - Do not canonicalize media.padeya.com (R2) here.
 */

import { LIVE_SITE_ORIGIN } from "./env-policy";

export const WWW_HOST = "www.padeya.com";

export type PathRedirect = {
  source: string;
  destination: string;
  permanent: boolean;
};

/**
 * Old WordPress / membership plugin URLs → current App Router routes.
 * Classification: A (direct replacement exists).
 */
export const WORDPRESS_LEGACY_REDIRECTS: readonly PathRedirect[] = [
  {
    source: "/member-register",
    destination: "/register",
    permanent: true,
  },
  {
    source: "/member-register/:path*",
    destination: "/register",
    permanent: true,
  },
  {
    source: "/member-login",
    destination: "/login",
    permanent: true,
  },
  {
    source: "/member-login/:path*",
    destination: "/login",
    permanent: true,
  },
] as const;

/**
 * In-app path aliases (renames / consolidations) — not WordPress.
 * Classification: A (current product route moved).
 */
export const PRODUCT_PATH_REDIRECTS: readonly PathRedirect[] = [
  { source: "/host/dashboard", destination: "/host", permanent: true },
  { source: "/host/dashboard/:path*", destination: "/host", permanent: true },
  {
    source: "/host/events/:id/merch",
    destination: "/host/events/:id/merchandise",
    permanent: true,
  },
  {
    source: "/host/settings/notifications",
    destination: "/dashboard/settings/notifications",
    permanent: true,
  },
  {
    source: "/dashboard/merch",
    destination: "/dashboard/merchandise",
    permanent: true,
  },
  {
    source: "/dashboard/merch/:path*",
    destination: "/dashboard/merchandise/:path*",
    permanent: true,
  },
  {
    source: "/dashboard/passport/edit",
    destination: "/dashboard/passport/settings",
    permanent: true,
  },
  {
    source: "/dashboard/ambassadors",
    destination: "/dashboard/ambassador",
    permanent: true,
  },
  {
    source: "/dashboard/ambassadors/:path*",
    destination: "/dashboard/ambassador/:path*",
    permanent: true,
  },
  { source: "/sponsors", destination: "/sponsorships", permanent: true },
  {
    source: "/sponsors/hosts",
    destination: "/sponsorships/hosts",
    permanent: true,
  },
  {
    source: "/admin/sponsors",
    destination: "/admin/sponsorships",
    permanent: true,
  },
  {
    source: "/admin/sponsors/:path*",
    destination: "/admin/sponsorships/:path*",
    permanent: true,
  },
  { source: "/guides", destination: "/blog", permanent: true },
  { source: "/guides/:path*", destination: "/blog/:path*", permanent: true },
] as const;

/**
 * Known old paths intentionally left as 404/410 (no safe 1:1 replacement).
 * Classification: C — permanently removed / not equivalent.
 * Do NOT add homepage redirects for these.
 */
export const LEGACY_NO_REDIRECT_PATHS = [
  "/wp-admin",
  "/wp-login.php",
  "/wp-content",
  "/xmlrpc.php",
  "/wp-json",
  "/my-account",
  "/wishlist",
  "/membership",
  "/members",
  "/events-old",
  "/blog-old",
  "/sample-page",
  "/feed",
  "/rss",
] as const;

/** Canonical destinations that must never be listed as legacy sources. */
export const CANONICAL_AUTH_PATHS = ["/login", "/register"] as const;

/**
 * Next.js `redirects()` entries for www → apex.
 * Query strings are preserved by the Next.js redirect runtime.
 * Do not duplicate this in middleware (avoids extra hops / loops).
 */
export function wwwToApexRedirects() {
  return [
    {
      source: "/:path*",
      has: [{ type: "host" as const, value: WWW_HOST }],
      destination: `${LIVE_SITE_ORIGIN}/:path*`,
      permanent: true,
    },
    {
      // `/:path*` alone can miss bare `/` depending on matcher — keep explicit.
      source: "/",
      has: [{ type: "host" as const, value: WWW_HOST }],
      destination: `${LIVE_SITE_ORIGIN}/`,
      permanent: true,
    },
  ];
}

/** Full redirect list for next.config.ts */
export function buildAppRedirects() {
  return [
    ...wwwToApexRedirects(),
    ...PRODUCT_PATH_REDIRECTS.map((r) => ({ ...r })),
    ...WORDPRESS_LEGACY_REDIRECTS.map((r) => ({ ...r })),
  ];
}

/** Exact path sources from WordPress legacy map (no `:path*` wildcards). */
export function wordpressLegacyExactSources(): string[] {
  return WORDPRESS_LEGACY_REDIRECTS.map((r) => r.source).filter(
    (s) => !s.includes(":"),
  );
}
