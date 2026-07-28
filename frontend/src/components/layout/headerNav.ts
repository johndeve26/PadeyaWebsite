/** Shared public header nav config + active-path helpers. */

import {
  isPublicSponsorBrandProfilePath,
  isPublicSponsorshipMarketplacePath,
  SPONSORSHIP_MARKETPLACE_PATH,
} from "@/lib/sponsor-marketplace-paths";

export type NavLink = {
  href: string;
  label: string;
  description?: string;
};

export const PUBLIC_NAV = [
  { href: "/events", label: "Events" },
  { href: "/hosts", label: "Hosts" },
  { href: "/fans", label: "Fans" },
  { href: "/memories", label: "Memories" },
  { href: SPONSORSHIP_MARKETPLACE_PATH, label: "Sponsors" },
  { href: "/merch", label: "Shop" },
] as const;

/** Learn column — educational / marketing. */
export const RESOURCES_LEARN: readonly NavLink[] = [
  { href: "/blog", label: "Blog", description: "Stories and product updates" },
  { href: "/help", label: "Help", description: "Guides and how-tos" },
  { href: "/faq", label: "FAQ", description: "Common questions" },
  { href: "/for-fans", label: "For Fans", description: "How fans use Pàdéyá" },
  {
    href: "/for-hosts",
    label: "For Hosts",
    description: "Host tools and workflows",
  },
] as const;

/** Support & Safety column. */
export const RESOURCES_SUPPORT: readonly NavLink[] = [
  { href: "/support", label: "Support", description: "Get help from our team" },
  { href: "/safety", label: "Safety", description: "Stay safe at events" },
  { href: "/report", label: "Report", description: "Flag an issue" },
  { href: "/contact", label: "Contact", description: "Reach Pàdéyá" },
  {
    href: "/community-guidelines",
    label: "Community Guidelines",
    description: "How we keep nights respectful",
  },
] as const;

/** Platform column. */
export const RESOURCES_PLATFORM: readonly NavLink[] = [
  { href: "/pricing", label: "Pricing", description: "Fees and plans" },
  {
    href: "/merch-guide",
    label: "Merch Guide",
    description: "Formats, drops, and pickup",
  },
  {
    href: "/host/onboarding",
    label: "Become a host",
    description: "Start hosting on Pàdéyá",
  },
  {
    href: SPONSORSHIP_MARKETPLACE_PATH,
    label: "Sponsorships",
    description: "Brand partnerships",
  },
  {
    href: "/ambassadors",
    label: "Ambassador",
    description: "Earn by sharing events",
  },
] as const;

export const RESOURCES_FEATURED = {
  title: "Sell more than tickets",
  description:
    "Event add-ons, host shops, post-event drops, and Vault exclusives — merch formats built for hosts.",
  cta: { href: "/merch", label: "Explore Merch" },
} as const;

/**
 * Flat Resources list for active-state checks and smoke tests.
 * Shop (`/merch`) is intentionally excluded — it is a top-level nav item.
 */
export const RESOURCES_NAV: readonly NavLink[] = [
  ...RESOURCES_LEARN,
  ...RESOURCES_SUPPORT,
  ...RESOURCES_PLATFORM,
] as const;

/** Mobile “Learn” group. */
export const MOBILE_LEARN_NAV: readonly NavLink[] = [
  { href: "/blog", label: "Blog" },
  { href: "/help", label: "Help" },
  { href: "/faq", label: "FAQ" },
  { href: "/for-fans", label: "For Fans" },
  { href: "/for-hosts", label: "For Hosts" },
  { href: "/merch-guide", label: "Merch Guide" },
] as const;

/** Mobile “Support” group. */
export const MOBILE_SUPPORT_NAV: readonly NavLink[] = [
  { href: "/support", label: "Support" },
  { href: "/safety", label: "Safety" },
  { href: "/report", label: "Report" },
  { href: "/contact", label: "Contact" },
] as const;

/** @deprecated Prefer RESOURCES_* / MOBILE_* groups */
export const AUDIENCE_MARKETING_NAV = [
  { href: "/for-hosts", label: "For Hosts" },
  { href: "/for-fans", label: "For Fans" },
  { href: "/merch-guide", label: "Merch Guide" },
] as const;

export type PublicNavHref = (typeof PUBLIC_NAV)[number]["href"];

export function isNavLinkActive(href: string, pathname: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function isPublicNavActive(href: string, pathname: string): boolean {
  switch (href) {
    case "/events":
      return pathname === "/events" || pathname.startsWith("/events/");
    case "/hosts":
      return (
        pathname === "/hosts" ||
        pathname.startsWith("/hosts/") ||
        pathname.startsWith("/u/") ||
        pathname.startsWith("/@")
      );
    case "/fans":
      return (
        pathname === "/fans" ||
        pathname.startsWith("/fans/") ||
        pathname.startsWith("/f/")
      );
    case "/memories":
      return (
        pathname === "/memories" ||
        pathname.startsWith("/memories/") ||
        /^\/events\/[^/]+\/memories(?:\/|$)/.test(pathname)
      );
    case SPONSORSHIP_MARKETPLACE_PATH:
      return (
        isPublicSponsorshipMarketplacePath(pathname) ||
        isPublicSponsorBrandProfilePath(pathname)
      );
    case "/merch":
      // Shop marketplace only — never `/merch-guide`
      return pathname === "/merch" || pathname.startsWith("/merch/");
    default:
      return isNavLinkActive(href, pathname);
  }
}

/** Paths that highlight the Resources trigger (not Shop `/merch`). */
const RESOURCES_ACTIVE_PREFIXES = [
  "/blog",
  "/help",
  "/support",
  "/faq",
  "/pricing",
  "/safety",
  "/contact",
  "/for-hosts",
  "/for-fans",
  "/report",
  "/community-guidelines",
  "/merch-guide",
] as const;

export function isResourcesNavActive(pathname: string): boolean {
  return RESOURCES_ACTIVE_PREFIXES.some((prefix) => isNavLinkActive(prefix, pathname));
}

export function isPersonalPath(pathname: string): boolean {
  return (
    pathname === "/dashboard" ||
    pathname.startsWith("/dashboard/") ||
    pathname === "/connect" ||
    pathname.startsWith("/connect/")
  );
}

export function isHostWorkspacePath(pathname: string): boolean {
  return pathname === "/host" || pathname.startsWith("/host/");
}

export function isAdminPath(pathname: string): boolean {
  return pathname === "/admin" || pathname.startsWith("/admin/");
}
