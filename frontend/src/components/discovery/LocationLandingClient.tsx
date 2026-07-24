"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { LocationLandingHero } from "@/components/discovery/LocationLandingHero";
import { LocationPageViewTracker } from "@/components/analytics/LocationPageViewTracker";
import { MarketplaceBreadcrumbs } from "@/components/layout/MarketplaceBreadcrumbs";
import { PadeyaPicksSection } from "@/components/discovery/PadeyaPicksSection";
import { RelatedLocations } from "@/components/discovery/RelatedLocations";
import { TaxonomyBrowseCard } from "@/components/discovery/TaxonomyBrowseCard";
import { HomeCardCarousel } from "@/components/home/HomeCardCarousel";
import { TaxonomyEventCard } from "@/components/taxonomy/TaxonomyEventCard";
import {
  Button,
  Container,
  CTASection,
  EmptyState,
  HostCard,
  SectionHeader,
  SkeletonCard,
} from "@/components/ui";
import type { BreadcrumbItem } from "@/components/ui/Breadcrumb";
import type { LocationAnalyticsMeta } from "@/lib/analytics";
import { categoryBrowseImage } from "@/lib/discovery/browse-images";
import {
  categoryInLocationHref,
  LOCATION_LANDING_CATEGORIES,
  locationLandingSubtext,
  relatedLocationCandidates,
} from "@/lib/discovery/location-landing";
import { sortByEventCount } from "@/lib/discovery/sort-by-availability";
import { weekendWindow } from "@/lib/discovery/event-filters";
import { resolveHostMedia } from "@/lib/legacy-presentation";
import {
  fetchCategories,
  fetchPublicEvents,
} from "@/lib/events-api";
import {
  fetchPadeyaPicks,
} from "@/lib/placements-api";
import { resolvePadeyaPicks } from "@/lib/discovery/padeya-picks";
import type { EventCategory, EventItem } from "@/lib/types/events";
import {
  locationHubPath,
  type TaxonomyLocation,
} from "@/lib/taxonomy-api";

function eventInWeekend(event: EventItem, now = new Date()): boolean {
  const { start, end } = weekendWindow(now);
  const t = new Date(event.start_datetime).getTime();
  return t >= start.getTime() && t <= end.getTime();
}

function locationAnalyticsMeta(
  kind: string,
  name: string,
  ancestors: TaxonomyLocation[],
): LocationAnalyticsMeta {
  const byKind: Record<string, string> = {};
  for (const loc of ancestors) {
    byKind[loc.kind] = loc.name;
  }
  byKind[kind] = name;
  return {
    country: byKind.country,
    state: byKind.state,
    city: byKind.city,
    area: byKind.area,
  };
}

function picksContextForLanding(
  kind: string,
  slug: string,
  ancestors: TaxonomyLocation[],
): {
  query: {
    context: string;
    location_kind?: string;
    location_slug?: string;
  };
  titleName: string;
} | null {
  if (
    kind === "country" ||
    kind === "state" ||
    kind === "city" ||
    kind === "area"
  ) {
    return {
      query: {
        context: `${kind}_page`,
        location_kind: kind,
        location_slug: slug,
      },
      titleName: "",
    };
  }
  void ancestors;
  return null;
}

function LocationLandingInner({
  kind,
  slug,
  name,
  crumbs,
  childLocations = [],
  siblingLocations = [],
  ancestors = [],
}: {
  kind: string;
  slug: string;
  name: string;
  crumbs: BreadcrumbItem[];
  childLocations?: TaxonomyLocation[];
  siblingLocations?: TaxonomyLocation[];
  ancestors?: TaxonomyLocation[];
}) {
  const searchParams = useSearchParams();
  const weekendOnly = searchParams.get("weekend") === "1";

  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [categories, setCategories] = useState<EventCategory[]>([]);
  const [picks, setPicks] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const picksCtx = useMemo(
    () => picksContextForLanding(kind, slug, ancestors),
    [kind, slug, ancestors],
  );
  const picksQueryKey = picksCtx ? JSON.stringify(picksCtx.query) : "";

  useEffect(() => {
    let alive = true;
    void Promise.all([
      fetchPublicEvents({ location_kind: kind, location_slug: slug }),
      fetchCategories(),
      picksCtx
        ? fetchPadeyaPicks(picksCtx.query)
        : Promise.resolve([] as EventItem[]),
    ])
      .then(([rows, cats, padeyaPicks]) => {
        if (!alive) return;
        setEvents(rows);
        setCategories(cats);
        setPicks(padeyaPicks);
      })
      .catch((err) => {
        if (alive) {
          setError(err instanceof Error ? err.message : "Failed to load");
        }
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- keyed by serialized picks query
  }, [kind, slug, picksQueryKey]);

  const gridEvents = useMemo(() => {
    const rows = events ?? [];
    if (!weekendOnly) return rows;
    return rows.filter((e) => eventInWeekend(e));
  }, [events, weekendOnly]);

  const locationPicks = useMemo(
    () => resolvePadeyaPicks(picks, events ?? [], 2),
    [picks, events],
  );

  const placementEventIds = useMemo(
    () => picks.map((e) => e.id),
    [picks],
  );

  const locationMeta = useMemo(
    () => locationAnalyticsMeta(kind, name, ancestors),
    [kind, name, ancestors],
  );

  const pageViewKind =
    kind === "country" ||
    kind === "state" ||
    kind === "city" ||
    kind === "area"
      ? kind
      : null;

  const picksEyebrow = picksCtx
    ? (picksCtx.titleName || name)
    : name;

  const hostMap = useMemo(() => {
    const map = new Map<
      string,
      { hostId: string; slug: string; name: string; city: string | null }
    >();
    for (const event of events ?? []) {
      if (!event.host_slug && !event.host_id) continue;
      const key = event.host_slug || event.host_id;
      if (map.has(key)) continue;
      map.set(key, {
        hostId: event.host_id,
        slug: event.host_slug || event.host_id,
        name: event.host_display_name || event.host_slug || "Host",
        city: event.city,
      });
    }
    return map;
  }, [events]);

  const featuredHosts = useMemo(() => {
    return Array.from(hostMap.values()).slice(0, 6);
  }, [hostMap]);

  const categoryCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const event of events ?? []) {
      const s = event.category?.slug;
      if (!s) continue;
      counts.set(s, (counts.get(s) || 0) + 1);
    }
    return counts;
  }, [events]);

  const landingCategories = useMemo(
    () => sortByEventCount(LOCATION_LANDING_CATEGORIES, categoryCounts),
    [categoryCounts],
  );

  const activeCategoryCount = useMemo(() => {
    return new Set(
      (events ?? [])
        .map((e) => e.category?.slug)
        .filter((s): s is string => Boolean(s)),
    ).size;
  }, [events]);

  const related = useMemo(
    () =>
      relatedLocationCandidates(kind, slug, {
        children: childLocations.map((c) => ({
          kind: c.kind,
          slug: c.slug,
          name: c.name,
        })),
        siblings: siblingLocations.map((c) => ({
          kind: c.kind,
          slug: c.slug,
          name: c.name,
        })),
        ancestors: ancestors.map((a) => ({
          kind: a.kind,
          slug: a.slug,
          name: a.name,
        })),
      }),
    [kind, slug, childLocations, siblingLocations, ancestors],
  );

  const parentName = ancestors.length
    ? ancestors[ancestors.length - 1]?.name
    : null;
  const heroDescription = locationLandingSubtext(name, {
    kind,
    parentName,
  });

  const basePath = locationHubPath(kind, slug);

  const eventCount = events?.length ?? 0;
  const featuredDescription =
    events === null
      ? "Verified tickets, real hosts, and privacy-safe location labels."
      : `${eventCount} upcoming · ${hostMap.size} ${hostMap.size === 1 ? "host" : "hosts"} · ${activeCategoryCount} ${activeCategoryCount === 1 ? "scene" : "scenes"}.`;

  return (
    <main className="min-w-0 overflow-x-clip bg-background">
      {pageViewKind ? (
        <LocationPageViewTracker kind={pageViewKind} {...locationMeta} />
      ) : null}
      <MarketplaceBreadcrumbs items={crumbs} />
      <LocationLandingHero
        kind={kind}
        slug={slug}
        name={name}
        description={heroDescription}
      />

      <Container className="space-y-10 py-8 sm:space-y-12 sm:py-12">
        <section className="space-y-4 sm:space-y-5" aria-label="Jump in">
          <SectionHeader
            variant="display"
            eyebrow="Jump in"
            title={`Open ${name}`}
            description="Weekend energy, a scene, or the full marketplace."
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
              <Link href="#browse" className="min-w-0 sm:w-auto">
                <Button
                  variant="secondary"
                  size="lg"
                  className="w-full sm:w-auto"
                >
                  Browse scenes
                </Button>
              </Link>
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
          aria-label={`Events in ${name}`}
          className="scroll-mt-24 space-y-4 sm:space-y-5"
        >
          <SectionHeader
            variant="display"
            eyebrow="Featured"
            title={
              weekendOnly
                ? `This weekend in ${name}`
                : `Nights to watch in ${name}`
            }
            description={featuredDescription}
          />

          {error ? (
            <EmptyState title="Events unavailable" description={error} />
          ) : events === null ? (
            <HomeCardCarousel
              label={`Loading events in ${name}`}
              until="sm"
              desktopGridClassName="sm:grid-cols-2 lg:grid-cols-3"
              slideClassName="w-[min(82vw,19.5rem)]"
            >
              {Array.from({ length: 6 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </HomeCardCarousel>
          ) : gridEvents.length === 0 ? (
            <EmptyState
              title={
                weekendOnly
                  ? `No weekend events in ${name} yet`
                  : `No published events in ${name} yet`
              }
              description="Check back soon, or browse a related place below."
            />
          ) : (
            <HomeCardCarousel
              label={`Events in ${name}`}
              until="sm"
              desktopGridClassName="sm:grid-cols-2 lg:grid-cols-3"
              slideClassName="w-[min(82vw,19.5rem)]"
            >
              {gridEvents.map((event) => (
                <TaxonomyEventCard
                  key={event.id}
                  event={event}
                  className="h-full"
                />
              ))}
            </HomeCardCarousel>
          )}
        </section>

        <section
          id="browse"
          aria-label={`Browse by category in ${name}`}
          className="scroll-mt-24 space-y-6"
        >
          <SectionHeader
            eyebrow="Scenes"
            title={`Browse by interest in ${name}`}
            description="Jump into the scenes that define nights out here."
          />
          <ul className="grid auto-rows-fr gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 xl:grid-cols-5">
            {landingCategories.map((cat) => {
              const count = categoryCounts.get(cat.slug) ?? 0;
              const label =
                categories.find((c) => c.slug === cat.slug)?.name || cat.name;
              return (
                <li key={cat.slug} className="h-full">
                  <TaxonomyBrowseCard
                    href={categoryInLocationHref(kind, slug, cat.slug)}
                    title={label}
                    meta={
                      count > 0 ? `${count} upcoming` : "Browse category"
                    }
                    image={categoryBrowseImage(cat.slug)}
                    className="h-full"
                  />
                </li>
              );
            })}
          </ul>
        </section>

        {featuredHosts.length > 0 ? (
          <section
            aria-label={`Featured hosts in ${name}`}
            className="space-y-6"
          >
            <SectionHeader
              eyebrow="Featured"
              title={`Hosts to watch in ${name}`}
              description="Verified creators with public Legacy Pages you can explore now."
              action={
                <Link href="/hosts">
                  <Button variant="secondary" size="md">
                    Meet hosts
                  </Button>
                </Link>
              }
            />
            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {featuredHosts.map((host) => {
                const media = resolveHostMedia(host.slug);
                return (
                  <li key={host.hostId} className="h-full">
                    <HostCard
                      displayName={host.name}
                      username={host.slug}
                      city={host.city || name}
                      avatarUrl={media.avatarUrl}
                      verified
                      href={`/@${host.slug}`}
                    />
                  </li>
                );
              })}
            </ul>
          </section>
        ) : null}
      </Container>

      {locationPicks.length > 0 ? (
        <PadeyaPicksSection
          events={locationPicks}
          eyebrow={picksEyebrow}
          layout="spotlight"
          analytics={{
            placementContext:
              picksCtx?.query.context || `${kind}_page`,
            placementEventIds,
            ...locationMeta,
          }}
        />
      ) : null}

      <RelatedLocations locations={related} />

      <CTASection
        tone="accent"
        title={`Hosting in ${name}?`}
        description="Sell tickets, build Legacy, and own your audience on Pàdéyá."
        actions={
          <Link href="/host/onboarding">
            <Button size="lg" variant="dark">
              Start host onboarding
            </Button>
          </Link>
        }
      />
    </main>
  );
}

export function LocationLandingClient(props: {
  kind: string;
  slug: string;
  name: string;
  crumbs: BreadcrumbItem[];
  childLocations?: TaxonomyLocation[];
  siblingLocations?: TaxonomyLocation[];
  ancestors?: TaxonomyLocation[];
}) {
  return (
    <Suspense
      fallback={
        <main className="bg-background">
          <Container className="py-16 text-sm text-muted-foreground">
            Loading {props.name}…
          </Container>
        </main>
      }
    >
      <LocationLandingInner {...props} />
    </Suspense>
  );
}
