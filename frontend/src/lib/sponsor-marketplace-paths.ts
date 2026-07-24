/** Public sponsorship marketplace URLs (opportunities), distinct from `/sponsor` workspace and `/sponsors/{slug}` brand profiles. */

export const SPONSORSHIP_MARKETPLACE_PATH = "/sponsorships";
export const SPONSORSHIP_HOSTS_PATH = "/sponsorships/hosts";
export const SPONSORSHIP_OPEN_SLOTS_HASH = "#open-slots";

export function sponsorshipMarketplaceUrl(hostUsername?: string | null): string {
  const base = SPONSORSHIP_MARKETPLACE_PATH;
  if (!hostUsername?.trim()) return `${base}${SPONSORSHIP_OPEN_SLOTS_HASH}`;
  const user = hostUsername.replace(/^@/, "").toLowerCase();
  return `${base}?host=${encodeURIComponent(user)}${SPONSORSHIP_OPEN_SLOTS_HASH}`;
}

export function sponsorBrandProfilePath(slug: string): string {
  return `/sponsors/${slug}`;
}

/** Public marketplace + hosts listing (not brand profile at `/sponsors/{slug}`). */
export function isPublicSponsorshipMarketplacePath(pathname: string): boolean {
  if (
    pathname === SPONSORSHIP_MARKETPLACE_PATH ||
    pathname.startsWith(`${SPONSORSHIP_MARKETPLACE_PATH}/`)
  ) {
    return true;
  }
  return pathname === "/sponsors" || pathname === "/sponsors/hosts";
}

/** Verified sponsor brand page at `/sponsors/{slug}`. */
export function isPublicSponsorBrandProfilePath(pathname: string): boolean {
  return /^\/sponsors\/[^/]+$/.test(pathname);
}
