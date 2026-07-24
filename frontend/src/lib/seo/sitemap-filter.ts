/** Sitemap visibility helpers — keep in sync with app/sitemap.ts. */

import { isReservedMerchSlug } from "@/lib/seo/merch-paths";

export type SitemapEventLike = {
  slug: string;
  visibility?: string | null;
};

export type SitemapHostLike = {
  username?: string | null;
};

export type SitemapFanLike = {
  username?: string | null;
};

export type SitemapSponsorLike = {
  slug?: string | null;
  verified?: boolean | null;
};

export type SitemapMerchLike = {
  slug?: string | null;
  indexable?: boolean | null;
};

export type SitemapBlogPostLike = {
  status?: string | null;
  category?: { slug?: string | null } | null;
  author?: { slug?: string | null } | null;
  tags?: Array<{ slug?: string | null }> | null;
  updated_at?: string | null;
  published_at?: string | null;
};

/** Paths that must never appear in the sitemap (prefix or exact). */
export const SITEMAP_FORBIDDEN_PATH_PREFIXES = [
  "/admin",
  "/dashboard",
  "/host",
  "/sponsor",
  "/connect",
  "/messages",
  "/staff",
  "/ambassador",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/checkout",
  "/team/invite",
  "/demo",
  "/account/appeal",
  "/api",
] as const;

export const SITEMAP_FORBIDDEN_EXACT_PATHS = new Set([
  "/events/search",
]);

/**
 * Only publicly listed events belong in the sitemap.
 * Unlisted + password_protected + approval_required are never included.
 */
export function filterListedEventsForSitemap<T extends SitemapEventLike>(
  events: T[],
): T[] {
  return events.filter((e) => isSitemapEligibleEvent(e));
}

export function isSitemapEligibleEvent(
  event: SitemapEventLike,
): boolean {
  if (!event.slug?.trim()) return false;
  const v = (event.visibility || "listed").trim().toLowerCase();
  return v === "listed";
}

export function isExcludedFromSitemap(
  visibility: string | null | undefined,
): boolean {
  if (!visibility) return false;
  return visibility.trim().toLowerCase() !== "listed";
}

/** Discover API is already active-only; guard empty usernames. */
export function isSitemapEligibleHost(host: SitemapHostLike): boolean {
  return Boolean(host.username?.trim());
}

export function filterHostsForSitemap<T extends SitemapHostLike>(hosts: T[]): T[] {
  return hosts.filter(isSitemapEligibleHost);
}

/**
 * Fan directory API already returns public + directory-opt-in + not admin-hidden.
 * Guard empty usernames only — never invent private/unlisted entries.
 */
export function isSitemapEligibleFan(fan: SitemapFanLike): boolean {
  return Boolean(fan.username?.trim());
}

export function filterFansForSitemap<T extends SitemapFanLike>(fans: T[]): T[] {
  return fans.filter(isSitemapEligibleFan);
}

/**
 * Sponsor directory API is active + public + verified.
 * Reject missing slug or explicitly unverified payloads.
 */
export function isSitemapEligibleSponsor(sponsor: SitemapSponsorLike): boolean {
  if (!sponsor.slug?.trim()) return false;
  if (sponsor.verified === false) return false;
  return true;
}

export function filterSponsorsForSitemap<T extends SitemapSponsorLike>(
  sponsors: T[],
): T[] {
  return sponsors.filter(isSitemapEligibleSponsor);
}

export function isSitemapEligibleMerch(item: SitemapMerchLike): boolean {
  if (!item.slug?.trim()) return false;
  if (isReservedMerchSlug(item.slug)) return false;
  return item.indexable !== false;
}

export function filterMerchForSitemap<T extends SitemapMerchLike>(items: T[]): T[] {
  return items.filter(isSitemapEligibleMerch);
}

export function isPublishedBlogPost(
  post: Pick<SitemapBlogPostLike, "status">,
): boolean {
  return (post.status || "").trim().toLowerCase() === "published";
}

/** Non-empty hub eligibility from published posts only. */
export function collectNonEmptyBlogHubSlugs(
  posts: SitemapBlogPostLike[],
): {
  categories: Set<string>;
  tags: Set<string>;
  authors: Set<string>;
} {
  const categories = new Set<string>();
  const tags = new Set<string>();
  const authors = new Set<string>();

  for (const post of posts) {
    if (!isPublishedBlogPost(post)) continue;
    const cat = post.category?.slug?.trim();
    if (cat) categories.add(cat);
    const author = post.author?.slug?.trim();
    if (author) authors.add(author);
    for (const tag of post.tags ?? []) {
      const slug = tag.slug?.trim();
      if (slug) tags.add(slug);
    }
  }

  return { categories, tags, authors };
}

export function isNonEmptyBlogHub(
  slug: string | null | undefined,
  nonEmpty: Set<string>,
): boolean {
  const s = slug?.trim();
  if (!s) return false;
  return nonEmpty.has(s);
}

/**
 * Parse entity timestamps for lastModified.
 * Returns undefined when no real entity date exists — never invent "now".
 */
export function sitemapLastModified(
  ...candidates: Array<string | Date | null | undefined>
): Date | undefined {
  for (const c of candidates) {
    if (c == null || c === "") continue;
    const d = c instanceof Date ? c : new Date(c);
    if (!Number.isNaN(d.getTime())) return d;
  }
  return undefined;
}

export function isForbiddenSitemapPath(pathOrUrl: string): boolean {
  let path = pathOrUrl.trim();
  // Faceted / token query strings never belong in sitemaps.
  if (path.includes("?")) return true;

  try {
    if (path.includes("://")) {
      const u = new URL(path);
      if (u.search) return true;
      path = u.pathname;
    }
  } catch {
    /* keep raw */
  }
  const bare = path.split("#")[0] || "/";
  const normalized = bare.startsWith("/") ? bare : `/${bare}`;

  if (SITEMAP_FORBIDDEN_EXACT_PATHS.has(normalized)) return true;

  for (const prefix of SITEMAP_FORBIDDEN_PATH_PREFIXES) {
    if (normalized === prefix || normalized.startsWith(`${prefix}/`)) {
      return true;
    }
  }

  // Nested checkout / claim / invite / token-style segments
  if (
    /\/checkout(\/|$)/i.test(normalized) ||
    /\/(claim|invite|token|reset|verify)(\/|$)/i.test(normalized) ||
    /\/tickets\/claim/i.test(normalized)
  ) {
    return true;
  }

  return false;
}

/** Relative paths for entity sitemap entries (privacy-filtered inputs only). */
export function buildEntitySitemapPaths(input: {
  hosts?: SitemapHostLike[];
  fans?: SitemapFanLike[];
  sponsors?: SitemapSponsorLike[];
  includeFansDirectory?: boolean;
  ambassadors?: boolean;
  blogHubs?: {
    categories?: string[];
    tags?: string[];
    authors?: string[];
    nonEmpty: {
      categories: Set<string>;
      tags: Set<string>;
      authors: Set<string>;
    };
  };
}): string[] {
  const paths: string[] = [];

  if (input.includeFansDirectory) {
    paths.push("/fans");
  }

  if (input.ambassadors) {
    paths.push(
      "/ambassadors",
      "/ambassadors/events",
      "/ambassadors/how-it-works",
    );
  }

  for (const host of filterHostsForSitemap(input.hosts ?? [])) {
    paths.push(`/u/${encodeURIComponent(host.username!.trim())}`);
  }

  for (const fan of filterFansForSitemap(input.fans ?? [])) {
    paths.push(`/f/${encodeURIComponent(fan.username!.trim())}`);
  }

  for (const sponsor of filterSponsorsForSitemap(input.sponsors ?? [])) {
    paths.push(`/sponsors/${encodeURIComponent(sponsor.slug!.trim())}`);
  }

  const hubs = input.blogHubs;
  if (hubs) {
    for (const slug of hubs.categories ?? []) {
      if (isNonEmptyBlogHub(slug, hubs.nonEmpty.categories)) {
        paths.push(`/blog/category/${encodeURIComponent(slug.trim())}`);
      }
    }
    for (const slug of hubs.tags ?? []) {
      if (isNonEmptyBlogHub(slug, hubs.nonEmpty.tags)) {
        paths.push(`/blog/tag/${encodeURIComponent(slug.trim())}`);
      }
    }
    for (const slug of hubs.authors ?? []) {
      if (isNonEmptyBlogHub(slug, hubs.nonEmpty.authors)) {
        paths.push(`/blog/author/${encodeURIComponent(slug.trim())}`);
      }
    }
  }

  return paths;
}
