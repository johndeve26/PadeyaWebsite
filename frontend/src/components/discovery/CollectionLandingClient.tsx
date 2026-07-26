"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { DiscoveryHubHero } from "@/components/discovery/DiscoveryHubHero";
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
import { brand } from "@/lib/brand";
import {
  EVENT_LISTING_CAROUSEL_SLIDE,
  EVENT_LISTING_GRID_DISCOVERY,
} from "@/lib/discovery/event-listing-layout";
import { cityBrowseImage } from "@/lib/discovery/browse-images";
import {
  filterPublicEvents,
  type EventDiscoveryFilters,
  weekendWindow,
} from "@/lib/discovery/event-filters";
import { citySlugFromName } from "@/lib/discovery/slugify";
import { sortByEventCount } from "@/lib/discovery/sort-by-availability";
import { fetchPublicEvents } from "@/lib/events-api";
import type { EventItem } from "@/lib/types/events";

function eventInWeekend(event: EventItem, now = new Date()): boolean {
  const { start, end } = weekendWindow(now);
  const t = new Date(event.start_datetime).getTime();
  return t >= start.getTime() && t <= end.getTime();
}

export type CollectionLandingCopy = {
  eyebrow: string;
  title: string;
  description: string;
  sectionEyebrow: string;
  sectionTitle: string;
  sectionTitleWeekend: string;
  sectionDescription: string;
  emptyTitle: string;
  emptyTitleWeekend: string;
  emptyDescription: string;
  citySectionTitle: string;
  /** Suffix after the city event count, e.g. "free" → "3 free". */
  cityCountSuffix: string;
  /** Extra secondary action next to weekend toggle (optional). */
  secondaryAction?: { href: string; label: string };
  /** When true, hide the weekend toggle (hub is already weekend-only). */
  hideWeekendToggle?: boolean;
  /** Taxonomy art for the hero plane. */
  heroImage?: string;
  jumpInTitle?: string;
  jumpInDescription?: string;
  ctaTitle?: string;
  ctaDescription?: string;
};

function CollectionLandingInner({
  crumbs,
  basePath,
  filters,
  copy,
  fetchFilters,
  match,
}: {
  crumbs: BreadcrumbItem[];
  basePath: string;
  filters: EventDiscoveryFilters;
  copy: CollectionLandingCopy;
  fetchFilters?: Parameters<typeof fetchPublicEvents>[0];
  match?: (event: EventItem) => boolean;
}) {
  const searchParams = useSearchParams();
  const weekendOnly =
    !copy.hideWeekendToggle && searchParams.get("weekend") === "1";

  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const filterKey = JSON.stringify(filters);
  const fetchKey = JSON.stringify(fetchFilters ?? {});

  useEffect(() => {
    let alive = true;
    void fetchPublicEvents(fetchFilters)
      .then((rows) => {
        if (!alive) return;
        let next = filterPublicEvents(rows, filters);
        if (match) next = next.filter(match);
        setEvents(next);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterKey, fetchKey, match]);

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
    return new Set(events.map((e) => e.host_id).filter(Boolean)).size;
  }, [events]);

  const cityLinks = useMemo(() => {
    if (!events) return [];
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
    return sortByEventCount(
      items,
      new Map(items.map((i) => [i.slug, i.count])),
    ).slice(0, 12);
  }, [events]);

  const eventCount = events?.length ?? 0;
  const featuredDescription =
    events === null
      ? copy.sectionDescription
      : eventCount === 0
        ? copy.sectionDescription
        : `${eventCount} upcoming · ${hostCount} ${hostCount === 1 ? "host" : "hosts"}. ${copy.sectionDescription}`;

  return (
    <main className="min-w-0 overflow-x-clip bg-background">
      <MarketplaceBreadcrumbs items={crumbs} />
      <DiscoveryHubHero
        eyebrow={copy.eyebrow}
        title={copy.title}
        description={copy.description}
        ctaLabel="See what’s on"
        ctaHref="#events"
        secondaryCtaLabel="All events"
        secondaryCtaHref="/events"
        backgroundSrc={copy.heroImage || brand.heroImage}
      />

      <Container className="space-y-14 py-10 sm:py-14">
        <section className="space-y-6" aria-label="Jump in">
          <SectionHeader
            eyebrow="Jump in"
            title={copy.jumpInTitle || "Refine this collection"}
            description={
              copy.jumpInDescription ||
              "Tighten the list before you scroll: weekend energy, or a related path."
            }
          />
          <div className="flex max-w-3xl flex-col gap-3 rounded-[var(--radius-lg)] border border-border bg-muted p-4 sm:flex-row sm:flex-wrap sm:items-center sm:p-5">
            {!copy.hideWeekendToggle ? (
              weekendOnly ? (
                <Link href={`${basePath}#events`}>
                  <Button variant="secondary" size="md">
                    Show all dates
                  </Button>
                </Link>
              ) : (
                <Link href={`${basePath}?weekend=1#events`}>
                  <Button variant="primary" size="md">
                    This weekend only
                  </Button>
                </Link>
              )
            ) : null}
            {copy.secondaryAction ? (
              <Link href={copy.secondaryAction.href}>
                <Button variant="secondary" size="md">
                  {copy.secondaryAction.label}
                </Button>
              </Link>
            ) : null}
            <Link href="/events">
              <Button variant="ghost" size="md">
                All of Pàdéyá
              </Button>
            </Link>
          </div>
        </section>

        <section
          id="events"
          aria-label={copy.title}
          className="scroll-mt-24 space-y-6"
        >
          <SectionHeader
            eyebrow={copy.sectionEyebrow}
            title={weekendOnly ? copy.sectionTitleWeekend : copy.sectionTitle}
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
              title={weekendOnly ? copy.emptyTitleWeekend : copy.emptyTitle}
              description={copy.emptyDescription}
            />
          ) : (
            <HomeCardCarousel
              label={copy.sectionTitle}
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

        {cityLinks.length > 0 ? (
          <section
            aria-label={`${copy.title} by city`}
            className="space-y-6"
          >
            <SectionHeader
              eyebrow="Where it’s on"
              title={copy.citySectionTitle}
              description="Cities with nights in this collection right now."
            />
            <ul className="grid auto-rows-fr gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 xl:grid-cols-4">
              {cityLinks.map((city) => (
                <li key={city.slug} className="h-full">
                  <TaxonomyBrowseCard
                    href={`/events/city/${city.slug}`}
                    title={city.name}
                    meta={`${city.count} ${copy.cityCountSuffix}`}
                    image={cityBrowseImage(city.slug)}
                    className="h-full"
                  />
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </Container>

      <CTASection
        tone="accent"
        title={copy.ctaTitle || "Looking for a different night?"}
        description={
          copy.ctaDescription ||
          "Browse every verified event on Pàdéyá, or start hosting your own."
        }
        actions={
          <>
            <Link href="/events">
              <Button size="lg" variant="dark">
                Browse all events
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

export function CollectionLandingClient(props: {
  crumbs: BreadcrumbItem[];
  basePath: string;
  filters: EventDiscoveryFilters;
  copy: CollectionLandingCopy;
  fetchFilters?: Parameters<typeof fetchPublicEvents>[0];
  match?: (event: EventItem) => boolean;
}) {
  return (
    <Suspense
      fallback={
        <main className="bg-background">
          <Container className="py-16 text-sm text-muted-foreground">
            Loading {props.copy.title}…
          </Container>
        </main>
      }
    >
      <CollectionLandingInner {...props} />
    </Suspense>
  );
}
