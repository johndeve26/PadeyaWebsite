import type { Metadata } from "next";

import { ReferralLandingTracker } from "@/components/ambassadors/ReferralLandingTracker";
import { EventsMarketplaceClient } from "@/components/events/marketplace";
import {
  fetchCategoriesServer,
  fetchPublicEventsServer,
  type PublicEventsServerFilters,
} from "@/lib/events/public-server";
import { buildHomeEvents } from "@/lib/marketplace-breadcrumbs";
import {
  EVENTS_FACET_CANONICAL_PATH,
  hasEventsFacetQuery,
} from "@/lib/seo/facet-policy";
import { HubJsonLd, hubPageMetadata } from "@/lib/seo/hub-page";

/** ISR — aligns with PUBLIC_REVALIDATE.eventsList (must be a literal for Next). */
export const revalidate = 90;

/**
 * Faceted /events?… URLs stay usable in the UI but canonicalize to /events
 * and are noindex when filter/search params are present (tracking-only OK).
 */
export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}): Promise<Metadata> {
  const sp = await searchParams;
  return hubPageMetadata({
    title: "Events",
    description:
      "Discover events on Pàdéyá — search by city, category, date, and vibe. Verified tickets, QR check-in, and trusted hosts.",
    path: EVENTS_FACET_CANONICAL_PATH,
    noIndex: hasEventsFacetQuery(sp),
  });
}

/**
 * SSR public list for default + non-geo URL filters (city/category/date/weekend).
 *
 * Near-me (lat/lng/radius/near=1) stays client-side after browser consent.
 * We intentionally do NOT SSR nearby with precise GPS — avoids caching or
 * leaking exact coordinates. See docs/PERFORMANCE_CACHING_AUDIT.md.
 */
function filtersFromSearchParams(
  sp: Record<string, string | string[] | undefined>,
): PublicEventsServerFilters {
  const one = (key: string) => {
    const v = sp[key];
    return Array.isArray(v) ? v[0] : v;
  };

  const filters: PublicEventsServerFilters = {};
  const q = one("q");
  const category = one("category");
  const city = one("city");
  const location_kind = one("location_kind");
  const location_slug = one("location_slug");
  const paid = one("paid");
  const sort = one("sort");
  const weekend = one("weekend");

  if (q) filters.q = q;
  if (category) filters.category = category;
  if (city) filters.city = city;
  if (location_kind) filters.location_kind = location_kind;
  if (location_slug) filters.location_slug = location_slug;
  if (paid) filters.paid = paid;
  if (sort) filters.sort = sort;
  if (weekend === "1" || weekend === "true") filters.weekend = true;
  return filters;
}

function hasGeoParams(sp: Record<string, string | string[] | undefined>): boolean {
  const one = (key: string) => {
    const v = sp[key];
    return Array.isArray(v) ? v[0] : v;
  };
  return Boolean(one("lat") || one("lng") || one("near") === "1");
}

export default async function EventsIndexPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  const filters = filtersFromSearchParams(sp);
  // Geo mode: still SSR the unfiltered public list as a safe shell; client
  // enhances proximity after consent (never SSR exact GPS nearby).
  const listFilters = hasGeoParams(sp) ? {} : filters;

  const [events, categories] = await Promise.all([
    fetchPublicEventsServer(listFilters),
    fetchCategoriesServer(),
  ]);

  const crumbs = buildHomeEvents();
  return (
    <>
      <ReferralLandingTracker />
      <HubJsonLd
        name="Events on Pàdéyá"
        description="Find events on Pàdéyá — search by city, category, date, and vibe. Verified tickets with QR check-in."
        path="/events"
        crumbs={crumbs}
      />
      <EventsMarketplaceClient
        initialEvents={events}
        initialCategories={categories}
      />
    </>
  );
}
