"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { CategoryLandingHero } from "@/components/discovery/CategoryLandingHero";
import { PadeyaPicksSection } from "@/components/discovery/PadeyaPicksSection";
import { TaxonomyBrowseCard } from "@/components/discovery/TaxonomyBrowseCard";
import { HomeCardCarousel } from "@/components/home/HomeCardCarousel";
import { MarketplaceBreadcrumbs } from "@/components/layout/MarketplaceBreadcrumbs";
import { TaxonomyEventCard } from "@/components/taxonomy/TaxonomyEventCard";
import {
  Button,
  Container,
  CTASection,
  EmptyState,
  SectionHeader,
  SkeletonCard,
} from "@/components/ui";
import type { BreadcrumbItem } from "@/components/ui/Breadcrumb";
import { cityBrowseImage } from "@/lib/discovery/browse-images";
import {
  EVENT_LISTING_CAROUSEL_SLIDE,
  EVENT_LISTING_GRID_DISCOVERY,
} from "@/lib/discovery/event-listing-layout";
import { weekendWindow } from "@/lib/discovery/event-filters";
import { citySlugFromName } from "@/lib/discovery/slugify";
import { sortByEventCount } from "@/lib/discovery/sort-by-availability";
import { resolvePadeyaPicks } from "@/lib/discovery/padeya-picks";
import { fetchPublicEvents } from "@/lib/events-api";
import { fetchPadeyaPicks } from "@/lib/placements-api";
import type { EventItem } from "@/lib/types/events";

function eventInWeekend(event: EventItem, now = new Date()): boolean {
  const { start, end } = weekendWindow(now);
  const t = new Date(event.start_datetime).getTime();
  return t >= start.getTime() && t <= end.getTime();
}

function CategoryLandingInner({
  categorySlug,
  categoryName,
  categoryDescription,
  crumbs,
  citySlug,
  cityName,
  locationKind,
  locationSlug,
  locationName,
}: {
  categorySlug: string;
  categoryName: string;
  categoryDescription?: string;
  crumbs: BreadcrumbItem[];
  citySlug?: string;
  cityName?: string;
  locationKind?: string;
  locationSlug?: string;
  locationName?: string;
}) {
  const searchParams = useSearchParams();
  const weekendOnly = searchParams.get("weekend") === "1";

  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [picks, setPicks] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const placeName = cityName || locationName;
  const lockedToPlace = Boolean(citySlug || (locationKind && locationSlug));

  const picksQuery = useMemo(() => {
    if (citySlug) {
      return {
        context: "city_category_page" as const,
        location_kind: "city",
        location_slug: citySlug,
        category: categorySlug,
      };
    }
    return {
      context: "category_page" as const,
      category: categorySlug,
    };
  }, [categorySlug, citySlug]);

  const picksQueryKey = JSON.stringify(picksQuery);

  useEffect(() => {
    let alive = true;
    const filters: Parameters<typeof fetchPublicEvents>[0] = {
      category: categorySlug,
    };
    if (citySlug) {
      filters.location_kind = "city";
      filters.location_slug = citySlug;
      filters.city = citySlug;
    } else if (locationKind && locationSlug) {
      filters.location_kind = locationKind;
      filters.location_slug = locationSlug;
    }

    void Promise.all([
      fetchPublicEvents(filters),
      fetchPadeyaPicks(picksQuery).catch(() => [] as EventItem[]),
    ])
      .then(([rows, padeyaPicks]) => {
        if (!alive) return;
        setEvents(rows);
        setPicks(padeyaPicks);
        setError(null);
      })
      .catch((err) => {
        if (!alive) return;
        setError(err instanceof Error ? err.message : "Failed to load");
        setEvents([]);
      });

    return () => {
      alive = false;
    };
  }, [categorySlug, citySlug, locationKind, locationSlug, picksQueryKey, picksQuery]);

  const gridEvents = useMemo(() => {
    if (!events) return [];
    const rows = weekendOnly
      ? events.filter((e) => eventInWeekend(e))
      : events;
    return [...rows].sort(
      (a, b) =>
        new Date(a.start_datetime).getTime() -
        new Date(b.start_datetime).getTime(),
    );
  }, [events, weekendOnly]);

  const hostCount = useMemo(() => {
    if (!events) return 0;
    const ids = new Set<string>();
    for (const e of events) {
      if (e.host_id) ids.add(e.host_id);
    }
    return ids.size;
  }, [events]);

  const cityLinks = useMemo(() => {
    if (lockedToPlace || !events) return [];
    const counts = new Map<string, { name: string; count: number }>();
    for (const e of events) {
      const city = e.city?.trim();
      if (!city) continue;
      const slug = citySlugFromName(city);
      const prev = counts.get(slug);
      if (prev) prev.count += 1;
      else counts.set(slug, { name: city, count: 1 });
    }
    const items = [...counts.entries()].map(([slug, v]) => ({
      slug,
      name: v.name,
      count: v.count,
    }));
    return sortByEventCount(items, new Map(items.map((i) => [i.slug, i.count])));
  }, [events, lockedToPlace]);

  const categoryPicks = useMemo(() => {
    if (!events) return [];
    return resolvePadeyaPicks(picks, events, 2);
  }, [events, picks]);

  const placementEventIds = useMemo(
    () => categoryPicks.map((e) => e.id),
    [categoryPicks],
  );

  const basePath = citySlug
    ? `/events/city/${citySlug}/${categorySlug}`
    : locationKind && locationSlug
      ? `/events/${locationKind}/${locationSlug}/${categorySlug}`
      : `/events/c/${categorySlug}`;

  const headingScope = placeName
    ? `${categoryName} in ${placeName}`
    : categoryName;

  const eventCount = events?.length ?? 0;
  const featuredDescription =
    events === null
      ? "Verified tickets, real hosts, and privacy-safe location labels."
      : eventCount === 0
        ? "Verified tickets, real hosts, and privacy-safe location labels."
        : `${eventCount} upcoming · ${hostCount} ${hostCount === 1 ? "host" : "hosts"}. Verified tickets and privacy-safe location labels.`;

  return (
    <main className="min-w-0 overflow-x-clip bg-background">
      <MarketplaceBreadcrumbs items={crumbs} />
      <CategoryLandingHero
        slug={categorySlug}
        name={categoryName}
        description={categoryDescription}
        cityName={cityName}
        citySlug={citySlug}
        locationName={locationName}
        locationKind={locationKind}
        locationSlug={locationSlug}
      />

      <Container className="space-y-14 py-10 sm:py-14">
        <section className="space-y-4 sm:space-y-5" aria-label="Jump in">
          <SectionHeader
            variant="display"
            eyebrow="Jump in"
            title={placeName ? `Refine ${headingScope}` : `Refine ${categoryName}`}
            description="Weekend energy, or open the full marketplace."
          />
          <div className="rounded-[var(--radius-xl)] border border-border bg-card p-4 shadow-[var(--shadow-soft)] dark:bg-surface-elevated sm:p-5">
            <div className="grid gap-2.5 sm:flex sm:flex-wrap sm:gap-3">
              {weekendOnly ? (
                <Link href={`${basePath}#events`} className="min-w-0 sm:w-auto">
                  <Button
                    variant="secondary"
                    size="lg"
                    className="w-full sm:w-auto"
                  >
                    Show all dates
                  </Button>
                </Link>
              ) : (
                <Link
                  href={`${basePath}?weekend=1#events`}
                  className="min-w-0 sm:w-auto"
                >
                  <Button size="lg" className="w-full sm:w-auto">
                    This weekend only
                  </Button>
                </Link>
              )}
              {placeName && citySlug ? (
                <Link
                  href={`/events/city/${citySlug}`}
                  className="min-w-0 sm:w-auto"
                >
                  <Button
                    variant="secondary"
                    size="lg"
                    className="w-full sm:w-auto"
                  >
                    All {placeName}
                  </Button>
                </Link>
              ) : null}
              <Link href="/events" className="min-w-0 sm:w-auto">
                <Button variant="ghost" size="lg" className="w-full sm:w-auto">
                  All of Pàdéyá
                </Button>
              </Link>
            </div>
          </div>
        </section>

        <section
          id="events"
          aria-label={`${headingScope} events`}
          className="scroll-mt-24 space-y-6"
        >
          <SectionHeader
            eyebrow="Featured"
            title={
              weekendOnly
                ? `This weekend · ${headingScope}`
                : `${headingScope} to watch`
            }
            description={featuredDescription}
          />

          {error ? (
            <EmptyState title="Events unavailable" description={error} />
          ) : events === null ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          ) : gridEvents.length === 0 ? (
            <EmptyState
              title={
                weekendOnly
                  ? `No weekend ${categoryName.toLowerCase()} events yet`
                  : `No published ${categoryName.toLowerCase()} events yet`
              }
              description={
                placeName
                  ? `Check back soon, or browse all ${placeName} events.`
                  : "Check back soon, or browse a city where this interest is live."
              }
            />
          ) : (
            <HomeCardCarousel
              label={`${categoryName} events`}
              until="sm"
              desktopGridClassName={EVENT_LISTING_GRID_DISCOVERY}
              slideClassName={EVENT_LISTING_CAROUSEL_SLIDE}
            >
              {gridEvents.map((event) => (
                <div key={event.id} className="h-full min-w-0">
                  <TaxonomyEventCard event={event} className="h-full" />
                </div>
              ))}
            </HomeCardCarousel>
          )}
        </section>
      </Container>

      {categoryPicks.length > 0 ? (
        <PadeyaPicksSection
          events={categoryPicks}
          title={
            placeName
              ? `${placeName} ${categoryName} Pàdéyá Picks`
              : `${categoryName} Pàdéyá Picks`
          }
          eyebrow={headingScope}
          layout="spotlight"
          analytics={{
            placementContext: picksQuery.context,
            placementEventIds,
            city: cityName,
            category: categoryName,
          }}
        />
      ) : null}

      {cityLinks.length > 0 ? (
        <Container className="space-y-6 py-10 sm:py-14">
          <SectionHeader
            eyebrow="Where it’s on"
            title={`${categoryName} by city`}
            description="Jump into the cities where this interest is live right now."
          />
          <ul className="grid auto-rows-fr gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 xl:grid-cols-4">
            {cityLinks.map((city) => (
              <li key={city.slug} className="h-full">
                <TaxonomyBrowseCard
                  href={`/events/city/${city.slug}/${categorySlug}`}
                  title={city.name}
                  meta={`${city.count} upcoming`}
                  image={cityBrowseImage(city.slug)}
                  className="h-full"
                />
              </li>
            ))}
          </ul>
        </Container>
      ) : null}

      <CTASection
        tone="accent"
        title={`Into ${categoryName.toLowerCase()}?`}
        description="Follow hosts who run these nights — or start hosting your own."
        actions={
          <>
            <Link href="/hosts">
              <Button size="lg" variant="dark">
                Meet hosts
              </Button>
            </Link>
            <Link href="/host/onboarding">
              <Button size="lg" variant="secondary">
                Become a host
              </Button>
            </Link>
          </>
        }
      />
    </main>
  );
}

export function CategoryLandingClient(props: {
  categorySlug: string;
  categoryName: string;
  categoryDescription?: string;
  crumbs: BreadcrumbItem[];
  citySlug?: string;
  cityName?: string;
  locationKind?: string;
  locationSlug?: string;
  locationName?: string;
}) {
  return (
    <Suspense
      fallback={
        <main className="bg-background">
          <Container className="py-16 text-sm text-muted-foreground">
            Loading {props.categoryName}…
          </Container>
        </main>
      }
    >
      <CategoryLandingInner {...props} />
    </Suspense>
  );
}
