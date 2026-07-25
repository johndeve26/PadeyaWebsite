import type { Metadata } from "next";

import { brand } from "@/lib/brand";
import { canonicalPathOnly } from "@/lib/seo/canonical-path";
import {
  getCanonicalSiteOrigin,
  isForbiddenCanonicalHost,
  LIVE_SITE_ORIGIN,
  readSeoEnv,
  robotsMetaForEnvironment,
  shouldIndexEnvironment,
  type SeoEnvInput,
} from "@/lib/seo/env-policy";
import {
  INDEXABLE_ROBOTS,
  NOINDEX_FOLLOW_ROBOTS,
  NOINDEX_ROBOTS,
} from "@/lib/seo/noindex";
import { resolveOgImageUrl } from "@/lib/seo/public-asset";
import { buildSiteVerificationMetadata } from "@/lib/seo/verification";

/** Default share card dimensions (WhatsApp / Facebook recommended). */
const DEFAULT_OG_IMAGE = {
  path: "/brand/padeya-og.png",
  width: 1200,
  height: 630,
  type: "image/png",
} as const;

export {
  getCanonicalSiteOrigin,
  isForbiddenCanonicalHost,
  isProductionSeoEnvironment,
  isValidProductionCanonicalOrigin,
  LIVE_SITE_ORIGIN,
  LIVE_SITE_HOST,
  readSeoEnv,
  robotsMetaForEnvironment,
  shouldIndexEnvironment,
  X_ROBOTS_NOINDEX,
} from "@/lib/seo/env-policy";

export {
  INDEXABLE_ROBOTS,
  NOINDEX_FOLLOW_ROBOTS,
  NOINDEX_ROBOTS,
  privateAreaMetadata,
} from "@/lib/seo/noindex";

function isLocalOrigin(origin: string): boolean {
  try {
    return isForbiddenCanonicalHost(new URL(origin).hostname);
  } catch {
    return /localhost|127\.0\.0\.1/i.test(origin);
  }
}

function originFromApiUrl(apiUrl: string): string | null {
  try {
    const u = new URL(apiUrl);
    if (isForbiddenCanonicalHost(u.hostname)) return null;
    if (u.hostname.startsWith("api.")) {
      u.hostname = u.hostname.slice(4);
    }
    if (isForbiddenCanonicalHost(u.hostname)) return null;
    return u.origin;
  } catch {
    return null;
  }
}

/**
 * SEO / sitemap / robots / metadataBase origin.
 * Always production-safe (https://padeya.com) — never localhost or preview hosts.
 */
export function siteOrigin(env?: SeoEnvInput): string {
  return getCanonicalSiteOrigin(env ?? readSeoEnv());
}

/**
 * Public origin for shareable links (referral, OG in the browser).
 * Prefers configured non-forbidden site URL, then non-forbidden window origin,
 * then API-derived origin, then the live brand domain.
 */
export function publicShareOrigin(): string {
  const configured = (
    process.env.NEXT_PUBLIC_SITE_URL ||
    process.env.SITE_URL ||
    ""
  ).replace(/\/$/, "");
  if (configured && !isLocalOrigin(configured)) {
    try {
      if (!isForbiddenCanonicalHost(new URL(configured).hostname)) {
        return configured;
      }
    } catch {
      /* fall through */
    }
  }

  if (typeof window !== "undefined") {
    const current = window.location.origin;
    if (current && !isLocalOrigin(current)) {
      try {
        if (!isForbiddenCanonicalHost(new URL(current).hostname)) {
          return current;
        }
      } catch {
        /* fall through */
      }
    }
  }

  const fromApi = originFromApiUrl(
    process.env.NEXT_PUBLIC_API_URL?.trim() || "",
  );
  if (fromApi) return fromApi;

  return LIVE_SITE_ORIGIN;
}

export function absoluteUrl(path: string, env?: SeoEnvInput): string {
  const p = canonicalPathOnly(path);
  return `${siteOrigin(env)}${p}`;
}

export function defaultOgImage(env?: SeoEnvInput): string {
  return absoluteUrl(DEFAULT_OG_IMAGE.path, env);
}

export function buildPageMetadata(opts: {
  title: string;
  description: string;
  path: string;
  image?: string | null;
  noIndex?: boolean;
  /**
   * When noIndex is set for a public duplicate/filter URL, keep follow
   * (default true). Private callers should use `privateAreaMetadata` /
   * `NOINDEX_ROBOTS` instead.
   */
  noIndexFollow?: boolean;
  env?: SeoEnvInput;
}): Metadata {
  const env = opts.env ?? readSeoEnv();
  const path = canonicalPathOnly(opts.path);
  const url = absoluteUrl(path, env);
  // WhatsApp/iMessage ignore SVG OG images — fall back to brand raster card.
  const custom = resolveOgImageUrl(opts.image);
  const image = custom || defaultOgImage(env);
  const usingDefault = !custom;
  const envBlocksIndex = !shouldIndexEnvironment(env);
  const noIndex = Boolean(opts.noIndex) || envBlocksIndex;
  const ogImage = usingDefault
    ? {
        url: image,
        width: DEFAULT_OG_IMAGE.width,
        height: DEFAULT_OG_IMAGE.height,
        type: DEFAULT_OG_IMAGE.type,
      }
    : { url: image };

  // Never set `robots: undefined` — Next.js merge treats the key as present and
  // clears parent root robots (wiping production index,follow).
  let robots: Metadata["robots"] = INDEXABLE_ROBOTS;
  if (noIndex) {
    // Soft public duplicates (facets) may opt into follow; default is nofollow
    // for private/unlisted/password and non-production environments.
    robots =
      !envBlocksIndex && opts.noIndexFollow === true
        ? NOINDEX_FOLLOW_ROBOTS
        : NOINDEX_ROBOTS;
  }

  return {
    title: opts.title,
    description: opts.description,
    alternates: { canonical: url },
    robots,
    openGraph: {
      title: opts.title,
      description: opts.description,
      url,
      siteName: brand.name,
      images: [ogImage],
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: opts.title,
      description: opts.description,
      images: [image],
    },
  };
}

/** Root-layout robots + metadataBase + optional Search Console verification. */
export function rootSeoMetadataFields(env: SeoEnvInput = readSeoEnv()): Pick<
  Metadata,
  "metadataBase" | "robots" | "verification"
> {
  const origin = getCanonicalSiteOrigin(env);
  const verification = buildSiteVerificationMetadata();
  return {
    metadataBase: new URL(`${origin}/`),
    robots: robotsMetaForEnvironment(env),
    ...(verification ? { verification } : {}),
  };
}
