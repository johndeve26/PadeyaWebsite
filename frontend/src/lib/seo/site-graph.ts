/**
 * Sitewide Organization + WebSite JSON-LD graph (Phase 1A).
 *
 * Stable IDs always use the production origin so entity pages can reference
 * them without inventing duplicate Pàdéyá Organization nodes.
 */

import { brand } from "@/lib/brand";
import { LIVE_SITE_ORIGIN } from "@/lib/seo/env-policy";

export const ORGANIZATION_ID = `${LIVE_SITE_ORIGIN}/#organization`;
export const WEBSITE_ID = `${LIVE_SITE_ORIGIN}/#website`;

/**
 * Public event keyword search that actually works without auth:
 * `GET /events?q=` (SSR + public API).
 *
 * Intentionally NOT `/events/search?q=` — that route ignores `q`.
 */
export const EVENTS_SEARCH_ACTION_TEMPLATE = `${LIVE_SITE_ORIGIN}/events?q={search_term_string}`;

type SocialSameAsEnv = {
  NEXT_PUBLIC_SOCIAL_SAME_AS?: string | null;
};

/** Optional comma-separated public social profile URLs (never fabricate). */
export function configuredOrganizationSameAs(
  env: SocialSameAsEnv = process.env as SocialSameAsEnv,
): string[] {
  const raw = (env.NEXT_PUBLIC_SOCIAL_SAME_AS || "").trim();
  if (!raw) return [];
  const urls: string[] = [];
  for (const part of raw.split(",")) {
    const u = part.trim();
    if (!/^https:\/\//i.test(u)) continue;
    try {
      const parsed = new URL(u);
      if (parsed.protocol !== "https:") continue;
      urls.push(parsed.href);
    } catch {
      /* skip invalid */
    }
  }
  return [...new Set(urls)];
}

export function organizationJsonLd(
  env: SocialSameAsEnv = process.env as SocialSameAsEnv,
): Record<string, unknown> {
  const logoUrl = `${LIVE_SITE_ORIGIN}${brand.logos.light}`;
  const org: Record<string, unknown> = {
    "@type": "Organization",
    "@id": ORGANIZATION_ID,
    name: brand.name,
    url: LIVE_SITE_ORIGIN,
    description: brand.tagline,
    logo: {
      "@type": "ImageObject",
      url: logoUrl,
    },
  };

  const sameAs = configuredOrganizationSameAs(env);
  if (sameAs.length) org.sameAs = sameAs;

  return org;
}

export type WebsiteJsonLdOptions = {
  /** When true, attach SearchAction for public `/events?q=` search. Default true. */
  includeSearchAction?: boolean;
};

export function websiteJsonLd(
  opts: WebsiteJsonLdOptions = {},
): Record<string, unknown> {
  const includeSearchAction = opts.includeSearchAction !== false;
  const site: Record<string, unknown> = {
    "@type": "WebSite",
    "@id": WEBSITE_ID,
    name: brand.name,
    url: LIVE_SITE_ORIGIN,
    publisher: { "@id": ORGANIZATION_ID },
  };

  if (includeSearchAction) {
    site.potentialAction = {
      "@type": "SearchAction",
      target: {
        "@type": "EntryPoint",
        urlTemplate: EVENTS_SEARCH_ACTION_TEMPLATE,
      },
      "query-input": "required name=search_term_string",
    };
  }

  return site;
}

/** Single root-level @graph: Organization + WebSite (+ optional SearchAction). */
export function siteGraphJsonLd(
  opts: WebsiteJsonLdOptions & { env?: SocialSameAsEnv } = {},
): Record<string, unknown> {
  return {
    "@context": "https://schema.org",
    "@graph": [
      organizationJsonLd(opts.env),
      websiteJsonLd({ includeSearchAction: opts.includeSearchAction }),
    ],
  };
}

/** Reference node for CollectionPage / FAQ isPartOf — avoid duplicate WebSite entities. */
export function websiteIdRef(): { "@id": string } {
  return { "@id": WEBSITE_ID };
}

export function organizationIdRef(): { "@id": string } {
  return { "@id": ORGANIZATION_ID };
}
