import type { BreadcrumbItem } from "@/components/ui/Breadcrumb";

import { SPONSORSHIP_MARKETPLACE_PATH } from "@/lib/sponsor-marketplace-paths";

const HOME: BreadcrumbItem = { label: "Home", href: "/" };
const EVENTS: BreadcrumbItem = { label: "Events", href: "/events" };
const HOSTS: BreadcrumbItem = { label: "Hosts", href: "/hosts" };
const SPONSORS: BreadcrumbItem = { label: "Sponsors", href: SPONSORSHIP_MARKETPLACE_PATH };

function current(label: string): BreadcrumbItem {
  return { label };
}

export function buildHomeEvents(): BreadcrumbItem[] {
  return [HOME, current("Events")];
}

export function buildCategoryTrail(
  categoryName: string,
  categorySlug: string,
): BreadcrumbItem[] {
  void categorySlug;
  return [HOME, EVENTS, current(categoryName || categorySlug)];
}

export function buildCityTrail(
  cityName: string,
  citySlug: string,
): BreadcrumbItem[] {
  void citySlug;
  return [HOME, EVENTS, current(cityName || citySlug)];
}

/**
 * Location hub trail: Home > Events > Nigeria > Lagos > Lekki
 * Collapses adjacent same-name nodes (e.g. Lagos state + Lagos city → one Lagos).
 */
export function buildLocationTrail(
  ancestors: { name: string; kind: string; slug: string }[],
  currentLoc: { name: string; kind: string; slug: string },
): BreadcrumbItem[] {
  const chain = [...ancestors, currentLoc];
  const items: BreadcrumbItem[] = [HOME, EVENTS];

  for (let i = 0; i < chain.length; i += 1) {
    const node = chain[i];
    const next = chain[i + 1];
    const label = node.name || node.slug;
    // Prefer the deeper node when state/city share a public label (Lagos).
    if (
      next &&
      (next.name || next.slug).toLowerCase() === label.toLowerCase()
    ) {
      continue;
    }
    const isLast = i === chain.length - 1;
    if (isLast) {
      items.push(current(label));
    } else {
      items.push({
        label,
        href: `/events/${node.kind}/${node.slug}`,
      });
    }
  }

  return items;
}

/** Home > Events > Lagos > Nightlife */
export function buildCityCategoryTrail(
  cityName: string,
  citySlug: string,
  categoryName: string,
  categorySlug: string,
): BreadcrumbItem[] {
  return [
    HOME,
    EVENTS,
    { label: cityName || citySlug, href: `/events/city/${citySlug}` },
    current(categoryName || categorySlug),
  ];
}

/** Home > Events > Lagos > Nightlife (state × category). */
export function buildStateCategoryTrail(
  stateName: string,
  stateSlug: string,
  categoryName: string,
  categorySlug: string,
): BreadcrumbItem[] {
  return [
    HOME,
    EVENTS,
    { label: stateName || stateSlug, href: `/events/state/${stateSlug}` },
    current(categoryName || categorySlug),
  ];
}

/** Home > Events > Nigeria > Lagos > Lekki > Nightlife > Event title */
export function buildEventTrail(opts: {
  title: string;
  slug: string;
  city?: string | null;
  citySlug?: string | null;
  categoryName?: string | null;
  categorySlug?: string | null;
  location?: {
    kind: string;
    slug: string;
    name: string;
    ancestors?: { kind: string; slug: string; name: string }[];
  } | null;
}): BreadcrumbItem[] {
  if (opts.location?.kind && opts.location.slug) {
    const trail = buildLocationTrail(opts.location.ancestors || [], {
      name: opts.location.name,
      kind: opts.location.kind,
      slug: opts.location.slug,
    });
    // Make current location a link; event title is the leaf.
    const last = trail[trail.length - 1];
    if (last && !last.href) {
      last.href = `/events/${opts.location.kind}/${opts.location.slug}`;
    }
    if (opts.categoryName && opts.categorySlug) {
      const loc = opts.location;
      const href =
        loc.kind === "city"
          ? `/events/city/${loc.slug}/${opts.categorySlug}`
          : loc.kind === "state"
            ? `/events/state/${loc.slug}/${opts.categorySlug}`
            : `/events/c/${opts.categorySlug}`;
      trail.push({ label: opts.categoryName, href });
    }
    trail.push(current(opts.title || opts.slug));
    return trail;
  }

  const items: BreadcrumbItem[] = [HOME, EVENTS];

  if (opts.city && opts.citySlug) {
    items.push({
      label: opts.city,
      href: `/events/city/${opts.citySlug}`,
    });
  }

  if (opts.categoryName && opts.categorySlug) {
    const href = opts.citySlug
      ? `/events/city/${opts.citySlug}/${opts.categorySlug}`
      : `/events/c/${opts.categorySlug}`;
    items.push({ label: opts.categoryName, href });
  }

  items.push(current(opts.title || opts.slug));
  return items;
}

export function buildHostTrail(
  displayName: string,
  username: string,
): BreadcrumbItem[] {
  return [HOME, HOSTS, current(displayName || username)];
}

export function buildVaultTrail(
  displayName: string,
  username: string,
  itemTitle?: string | null,
): BreadcrumbItem[] {
  const hostHref = `/u/${username}`;
  const items: BreadcrumbItem[] = [
    HOME,
    HOSTS,
    { label: displayName || username, href: hostHref },
  ];

  if (itemTitle) {
    items.push({ label: "Vault", href: `${hostHref}/vault` });
    items.push(current(itemTitle));
  } else {
    items.push(current("Vault"));
  }

  return items;
}

export function buildMemoryTrail(
  displayName: string,
  username: string,
  eventTitle: string,
): BreadcrumbItem[] {
  return [
    HOME,
    HOSTS,
    { label: displayName || username, href: `/u/${username}` },
    { label: "Memories", href: `/u/${username}/memories` },
    current(eventTitle),
  ];
}

export function buildSponsorsTrail(opts?: {
  hosts?: boolean;
}): BreadcrumbItem[] {
  if (opts?.hosts) {
    return [HOME, SPONSORS, current("Hosts")];
  }
  return [HOME, current("Sponsors")];
}

export type DiscoveryTrailKind = "weekend" | "free" | "vip" | "near_me";

const DISCOVERY_LABELS: Record<DiscoveryTrailKind, string> = {
  weekend: "This weekend",
  free: "Free events",
  vip: "VIP",
  near_me: "Near me",
};

export function buildDiscoveryTrail(kind: DiscoveryTrailKind): BreadcrumbItem[] {
  return [HOME, EVENTS, current(DISCOVERY_LABELS[kind])];
}

/** Home > Events > Under ₦5,000 / In-person events / … */
export function buildPriceTrail(title: string): BreadcrumbItem[] {
  return [HOME, EVENTS, current(title)];
}

/** Alias for non-price collection hubs (format, etc.). */
export const buildCollectionTrail = buildPriceTrail;
