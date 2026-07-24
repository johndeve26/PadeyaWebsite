/**
 * Pàdéyá SEO environment + canonical origin policy (Phase 0A).
 *
 * Production canonical domain is always https://padeya.com for public SEO.
 * Non-production environments must never be indexed.
 *
 * Production indexing is allowed when we have a clear production signal and
 * no hard non-production signal. Missing APP_ENV alone must NOT noindex a
 * production Node/Vercel deploy.
 */

/** Live brand origin — the only production SEO canonical. */
export const LIVE_SITE_ORIGIN = "https://padeya.com";
export const LIVE_SITE_HOST = "padeya.com";

export type SeoEnvInput = {
  appEnv?: string | null;
  vercelEnv?: string | null;
  nodeEnv?: string | null;
  siteUrl?: string | null;
  nextPublicSiteUrl?: string | null;
};

const NON_PRODUCTION_APP_ENVS = new Set([
  "development",
  "dev",
  "staging",
  "stage",
  "test",
  "testing",
  "preview",
  "local",
]);

function norm(value: string | null | undefined): string {
  return (value || "").trim().toLowerCase();
}

/** Read process env into a snapshot (server/edge/browser). */
export function readSeoEnv(): SeoEnvInput {
  return {
    appEnv: process.env.APP_ENV ?? process.env.NEXT_PUBLIC_APP_ENV ?? null,
    vercelEnv: process.env.VERCEL_ENV ?? null,
    nodeEnv: process.env.NODE_ENV ?? null,
    siteUrl: process.env.SITE_URL ?? null,
    nextPublicSiteUrl: process.env.NEXT_PUBLIC_SITE_URL ?? null,
  };
}

/**
 * Hosts that must never become production canonicals
 * (localhost, previews, tunnels, legacy staging hosts).
 */
export function isForbiddenCanonicalHost(hostname: string): boolean {
  const host = hostname.trim().toLowerCase().replace(/\.$/, "");
  if (
    host === "localhost" ||
    host === "127.0.0.1" ||
    host === "0.0.0.0" ||
    host === "[::1]" ||
    host.endsWith(".local")
  ) {
    return true;
  }
  if (host.endsWith(".smartlancedesigns.com")) {
    return true;
  }
  if (host.endsWith(".vercel.app")) return true;
  if (host.endsWith(".onrender.com")) return true;
  if (host.endsWith(".trycloudflare.com")) return true;
  if (
    host.endsWith(".ngrok-free.dev") ||
    host.endsWith(".ngrok-free.app") ||
    host.endsWith(".ngrok.app") ||
    host.endsWith(".ngrok.io")
  ) {
    return true;
  }
  return false;
}

/**
 * Valid production SEO origin: https + padeya.com (www normalized away).
 * Explicit overrides only accepted when they pass this check.
 */
export function isValidProductionCanonicalOrigin(origin: string): boolean {
  try {
    const u = new URL(origin);
    if (u.protocol !== "https:") return false;
    const host = u.hostname.toLowerCase();
    if (host !== LIVE_SITE_HOST && host !== `www.${LIVE_SITE_HOST}`) {
      return false;
    }
    if (u.username || u.password) return false;
    return true;
  } catch {
    return false;
  }
}

function stripTrailingSlash(origin: string): string {
  return origin.replace(/\/$/, "");
}

/**
 * True only for real production SEO environments.
 *
 * Hard blocks (never production):
 * - VERCEL_ENV = preview | development
 * - APP_ENV in non-production set
 * - NODE_ENV = development
 *
 * Allowed (production):
 * - APP_ENV = production
 * - VERCEL_ENV = production
 * - NODE_ENV = production with APP_ENV unset/empty and VERCEL_ENV unset or production
 */
export function isProductionSeoEnvironment(env: SeoEnvInput = readSeoEnv()): boolean {
  const vercel = norm(env.vercelEnv);
  const app = norm(env.appEnv);
  const node = norm(env.nodeEnv);

  if (vercel === "preview" || vercel === "development") return false;
  if (app && NON_PRODUCTION_APP_ENVS.has(app)) return false;
  if (node === "development") return false;

  if (app === "production") return true;
  if (vercel === "production") return true;

  // Production Node build without APP_ENV — do not accidental-noindex.
  if (node === "production" && !app) return true;

  return false;
}

/**
 * Client-safe production SEO signal for optional GA4.
 * Prefer NEXT_PUBLIC_APP_ENV on staging/preview so the browser bundle cannot
 * mistake a production Node build for an indexable/analytics-allowed env.
 */
export function isClientProductionSeoEnvironment(
  env: {
    NEXT_PUBLIC_APP_ENV?: string | null;
    APP_ENV?: string | null;
    VERCEL_ENV?: string | null;
    NEXT_PUBLIC_VERCEL_ENV?: string | null;
    NODE_ENV?: string | null;
  } = process.env,
): boolean {
  return isProductionSeoEnvironment({
    appEnv: env.NEXT_PUBLIC_APP_ENV ?? env.APP_ENV ?? null,
    vercelEnv: env.VERCEL_ENV ?? env.NEXT_PUBLIC_VERCEL_ENV ?? null,
    nodeEnv: env.NODE_ENV ?? null,
  });
}

/** Whether search engines should index this deployment. */
export function shouldIndexEnvironment(env: SeoEnvInput = readSeoEnv()): boolean {
  return isProductionSeoEnvironment(env);
}

/**
 * Canonical origin for metadataBase, alternates.canonical, sitemap, robots, JSON-LD.
 * Always https://padeya.com in practice; optional validated override only in production.
 */
export function getCanonicalSiteOrigin(env: SeoEnvInput = readSeoEnv()): string {
  const configured = stripTrailingSlash(
    (env.nextPublicSiteUrl || env.siteUrl || "").trim(),
  );

  if (configured && isValidProductionCanonicalOrigin(configured)) {
    // Normalize www → apex.
    try {
      const u = new URL(configured);
      u.hostname = LIVE_SITE_HOST;
      u.hash = "";
      u.search = "";
      return stripTrailingSlash(u.origin);
    } catch {
      return LIVE_SITE_ORIGIN;
    }
  }

  // Reject forbidden / misconfigured URLs — never leak preview/tunnel/localhost.
  if (configured) {
    try {
      const host = new URL(configured).hostname;
      if (isForbiddenCanonicalHost(host)) {
        return LIVE_SITE_ORIGIN;
      }
    } catch {
      return LIVE_SITE_ORIGIN;
    }
  }

  // Non-production and invalid overrides still use the live brand origin for SEO
  // surfaces (pages are noindex outside production).
  return LIVE_SITE_ORIGIN;
}

/** Header value for non-indexable responses. */
export const X_ROBOTS_NOINDEX = "noindex, nofollow";

export function robotsMetaForEnvironment(
  env: SeoEnvInput = readSeoEnv(),
): { index: boolean; follow: boolean } {
  if (shouldIndexEnvironment(env)) {
    return { index: true, follow: true };
  }
  return { index: false, follow: false };
}
