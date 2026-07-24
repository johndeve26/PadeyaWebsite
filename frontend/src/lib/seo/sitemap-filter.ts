/** Sitemap visibility helpers — keep in sync with app/sitemap.ts. */

export type SitemapEventLike = {
  slug: string;
  visibility?: string | null;
};

/** Only publicly listed events belong in the sitemap. */
export function filterListedEventsForSitemap<T extends SitemapEventLike>(
  events: T[],
): T[] {
  return events.filter((e) => !e.visibility || e.visibility === "listed");
}

export function isExcludedFromSitemap(visibility: string | null | undefined): boolean {
  if (!visibility) return false;
  return visibility !== "listed";
}
