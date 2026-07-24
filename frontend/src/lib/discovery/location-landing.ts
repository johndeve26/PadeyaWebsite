import type { LocationKind } from "@/lib/taxonomy-api";
import { POPULAR_LOCATION_SHORTCUTS } from "@/lib/discovery/popular-locations";

export const LOCATION_LANDING_CATEGORIES = [
  { slug: "music", name: "Music" },
  { slug: "nightlife", name: "Nightlife" },
  { slug: "comedy", name: "Comedy" },
  { slug: "tech", name: "Tech" },
  { slug: "gospel", name: "Gospel" },
] as const;

export function locationLandingSubtext(
  locationName: string,
  opts?: { kind?: string; parentName?: string | null },
): string {
  const parent = opts?.parentName?.trim();
  if (opts?.kind === "area" && parent) {
    return `Neighborhood nights in ${locationName}, ${parent} — concerts, comedy, nightlife, and culture on Pàdéyá.`;
  }
  if (opts?.kind === "city") {
    return `The ${locationName} marketplace — verified events across neighborhoods, venues, and scenes.`;
  }
  if (opts?.kind === "state") {
    return `Browse ${locationName} by city and area — hosts, categories, and Pàdéyá Picks in one place.`;
  }
  if (opts?.kind === "country") {
    return `Explore ${locationName} state by state — cities, neighborhoods, and the nights worth showing up for.`;
  }
  return `Discover verified events, nightlife, concerts, comedy, tech meetups, and culture in ${locationName}.`;
}

export function categoryInLocationHref(
  kind: string,
  slug: string,
  categorySlug: string,
): string {
  if (kind === "city") return `/events/city/${slug}/${categorySlug}`;
  if (kind === "state") return `/events/state/${slug}/${categorySlug}`;
  const params = new URLSearchParams({
    location_kind: kind,
    location_slug: slug,
    category: categorySlug,
  });
  return `/events?${params.toString()}`;
}

type LocRef = { kind: string; slug: string; name: string };

/**
 * Related locations from the taxonomy tree: children → siblings → parent →
 * curated popular shortcuts (last resort, excluding current).
 */
export function relatedLocationCandidates(
  kind: LocationKind | string,
  slug: string,
  opts: {
    children?: LocRef[];
    siblings?: LocRef[];
    ancestors?: LocRef[];
  } = {},
): LocRef[] {
  const seen = new Set<string>([`${kind}:${slug}`]);
  const out: LocRef[] = [];

  function push(item: LocRef) {
    const key = `${item.kind}:${item.slug}`;
    if (seen.has(key)) return;
    seen.add(key);
    out.push(item);
  }

  for (const child of opts.children || []) push(child);
  for (const sibling of opts.siblings || []) push(sibling);

  const parent = [...(opts.ancestors || [])].reverse()[0];
  if (parent) push(parent);

  for (const item of POPULAR_LOCATION_SHORTCUTS) {
    push({ kind: item.kind, slug: item.slug, name: item.label });
  }

  return out.slice(0, 8);
}
