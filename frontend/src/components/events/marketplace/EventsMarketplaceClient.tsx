"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  useTransition,
} from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { EmptyDiscoveryState } from "@/components/discovery/EmptyDiscoveryState";
import { EventRecommendationsSection } from "@/components/events/EventRecommendationsSection";
import {
  EventsFilterBar,
  type EventsFilterValues,
} from "@/components/events/marketplace/EventsFilterBar";
import { EventsFilterDrawer } from "@/components/events/marketplace/EventsFilterDrawer";
import { EventsMarketplaceBottomDiscovery } from "@/components/events/marketplace/EventsMarketplaceBottomDiscovery";
import { EventsResults } from "@/components/events/marketplace/EventsResults";
import { EventsResultsToolbar } from "@/components/events/marketplace/EventsResultsToolbar";
import { EventsSearchHero } from "@/components/events/marketplace/EventsSearchHero";
import { Button, Container, SkeletonCard } from "@/components/ui";
import { timeoutOrErrorMessage } from "@/lib/api-timeouts";
import { useDiscoveryLocation } from "@/hooks/useDiscoveryLocation";
import type { SortKey } from "@/lib/discovery/event-filters";
import {
  NEARBY_RADIUS_OPTIONS,
  type NearbyRadiusKm,
} from "@/lib/discovery/geo-location";
import { citySlugFromName } from "@/lib/discovery/slugify";
import {
  DEFAULT_PRICE_BOUND_MAX,
  EVENTS_PAGE_SIZE,
  clampEventsViewForViewport,
  EVENTS_LG_MEDIA_QUERY,
  computePriceBoundMax,
  enrichMarketplaceEventsWithDistance,
  filterMarketplaceEvents,
  parseDatePreset,
  parseEventsView,
  parsePriceParam,
  parseSortKey,
  sortMarketplaceByProximity,
  storeEventsView,
  type DatePreset,
  type EventsViewMode,
} from "@/lib/events/marketplace-listing";
import { fetchCategories, fetchEventRecommendations, fetchPublicEvents } from "@/lib/events-api";
import type { EventCategory, EventItem } from "@/lib/types/events";

function parseRadius(raw: string | null): NearbyRadiusKm {
  const n = Number(raw);
  return NEARBY_RADIUS_OPTIONS.includes(n as NearbyRadiusKm)
    ? (n as NearbyRadiusKm)
    : 25;
}

function EventsMarketplaceInner({
  initialEvents = null,
  initialCategories = [],
}: {
  initialEvents?: EventItem[] | null;
  initialCategories?: EventCategory[];
}) {
  const router = useRouter();
  const pathname = usePathname() || "/events";
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const [recRank, setRecRank] = useState<Map<string, number>>(() => new Map());
  const [, startTransition] = useTransition();
  const {
    location,
    hydrated,
    declined,
    requestNearMe,
    autoLocateIfAllowed,
    setManual,
    clearLocation,
  } = useDiscoveryLocation();

  const [events, setEvents] = useState<EventItem[] | null>(
    initialEvents ?? null,
  );
  const [categories, setCategories] = useState<EventCategory[]>(
    initialCategories,
  );
  const [error, setError] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [visibleCount, setVisibleCount] = useState(EVENTS_PAGE_SIZE);

  const [city, setCity] = useState(() => {
    const locSlug = searchParams.get("location_slug");
    if (searchParams.get("location_kind") === "city" && locSlug) return locSlug;
    return searchParams.get("city") || "all";
  });
  const [date, setDate] = useState<DatePreset>(() => {
    if (searchParams.get("weekend") === "1") return "this-weekend";
    return parseDatePreset(searchParams.get("date"));
  });
  const [priceMin, setPriceMin] = useState(() => {
    const n = parsePriceParam(searchParams.get("price_min"));
    return n ?? 0;
  });
  const [priceMax, setPriceMax] = useState(() => {
    const n = parsePriceParam(searchParams.get("price_max"));
    return n ?? DEFAULT_PRICE_BOUND_MAX;
  });
  const hadUrlPriceMax = useRef(
    parsePriceParam(searchParams.get("price_max")) != null,
  );
  const didExpandDefaultMax = useRef(false);
  const [sort, setSort] = useState<SortKey>(() =>
    parseSortKey(searchParams.get("sort")),
  );
  const [view, setView] = useState<EventsViewMode>(() =>
    parseEventsView(searchParams.get("view")),
  );

  // List/map are desktop-only — fall back to grid on mobile (incl. ?view=list|map links).
  useEffect(() => {
    const mq = window.matchMedia(EVENTS_LG_MEDIA_QUERY);
    const sync = () => {
      setView((current) => {
        const clamped = clampEventsViewForViewport(current, mq.matches);
        return clamped === current ? current : clamped;
      });
    };
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  /** Proximity sort only when consented location is active — never after decline. */
  const proximityActive = Boolean(location) && city === "all" && !declined;

  // Seed location from URL, or quietly reuse stored / already-granted geo.
  // Never prompt after a declined session; near=1 exits gracefully.
  useEffect(() => {
    if (!hydrated) return;
    const lat = Number(searchParams.get("lat"));
    const lng = Number(searchParams.get("lng"));
    const t = window.setTimeout(() => {
      if (Number.isFinite(lat) && Number.isFinite(lng)) {
        setManual({
          lat,
          lng,
          label: searchParams.get("location_label") || "Selected location",
          radiusKm: parseRadius(searchParams.get("radius")),
        });
        return;
      }
      if (searchParams.get("near") === "1") {
        if (declined) {
          clearLocation();
          return;
        }
        void (async () => {
          try {
            await requestNearMe();
          } catch {
            clearLocation();
          }
        })();
        return;
      }
      void autoLocateIfAllowed();
    }, 0);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- seed location once on hydrate
  }, [hydrated]);

  // Hydrate from SSR — skip client fetch when the server already provided the list.
  useEffect(() => {
    if (!hydrated) return;
    if (initialEvents != null) return;
    let cancelled = false;
    async function load() {
      setError(null);
      try {
        const [cats, rows] = await Promise.all([
          fetchCategories(),
          fetchPublicEvents(),
        ]);
        if (cancelled) return;
        setCategories(cats);
        setEvents(rows);
      } catch (err) {
        if (!cancelled) {
          setError(timeoutOrErrorMessage(err, "Failed to load events"));
          setEvents([]);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [hydrated, initialEvents]);

  useEffect(() => {
    if (!user || sort !== "recommended") {
      setRecRank(new Map());
      return;
    }
    let cancelled = false;
    void fetchEventRecommendations({ limit: 60, mode: "recommended" })
      .then((res) => {
        if (cancelled) return;
        const next = new Map<string, number>();
        res.events.forEach((row, index) => {
          next.set(row.event.id, row.score * 1000 - index);
        });
        setRecRank(next);
      })
      .catch(() => {
        if (!cancelled) setRecRank(new Map());
      });
    return () => {
      cancelled = true;
    };
  }, [user, sort]);

  const geoNotice =
    declined && searchParams.get("near") === "1"
      ? "No problem — you can still browse events by city, date, or category."
      : null;

  const rankedEvents = useMemo(() => {
    if (!events) return null;
    if (!proximityActive || !location) return events;
    return enrichMarketplaceEventsWithDistance(
      events,
      location.lat,
      location.lng,
    );
  }, [events, proximityActive, location]);

  const cities = useMemo(() => {
    const set = new Set(
      (rankedEvents ?? []).map((e) => e.city).filter((c): c is string => Boolean(c)),
    );
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [rankedEvents]);

  const cityOptions = useMemo(
    () =>
      cities.map((name) => ({
        name,
        slug: citySlugFromName(name),
      })),
    [cities],
  );

  const dataPriceBoundMax = useMemo(
    () => computePriceBoundMax(rankedEvents ?? []),
    [rankedEvents],
  );
  // Before events load, keep the slider ceiling at least as high as URL/state values
  // so we don't clamp away shared links.
  const priceBoundMax =
    rankedEvents == null
      ? Math.max(DEFAULT_PRICE_BOUND_MAX, priceMin, priceMax)
      : dataPriceBoundMax;

  const rangeMin = Math.min(priceMin, priceMax);
  const rangeMax = Math.max(priceMin, priceMax);

  useEffect(() => {
    const params = new URLSearchParams();
    if (city !== "all" && !proximityActive) {
      params.set("city", city);
      params.set("location_kind", "city");
      params.set("location_slug", city);
    }
    if (date !== "any") params.set("date", date);
    if (date === "this-weekend") params.set("weekend", "1");
    if (rangeMin > 0) params.set("price_min", String(rangeMin));
    if (rangeMax < priceBoundMax) params.set("price_max", String(rangeMax));
    if (sort !== "recommended") params.set("sort", sort);
    if (view !== "grid") params.set("view", view);
    if (proximityActive && location) {
      params.set("lat", String(location.lat));
      params.set("lng", String(location.lng));
      params.set("radius", String(location.radiusKm));
      if (location.label) params.set("location_label", location.label);
    }

    const qs = params.toString();
    const next = qs ? `${pathname}?${qs}` : pathname;
    const currentQs = searchParams.toString();
    const current = currentQs ? `${pathname}?${currentQs}` : pathname;
    if (next !== current) {
      startTransition(() => {
        router.replace(next, { scroll: false });
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- sync URL from listing state
  }, [
    city,
    date,
    rangeMin,
    rangeMax,
    priceBoundMax,
    sort,
    view,
    proximityActive,
    location,
    pathname,
    router,
  ]);

  // Clamp selection into the data-driven ceiling once listing data is available.
  useEffect(() => {
    if (rankedEvents == null) return;
    queueMicrotask(() => {
      setPriceMin((prev) => Math.min(Math.max(0, prev), dataPriceBoundMax));
      setPriceMax((prev) => Math.min(Math.max(prev, 0), dataPriceBoundMax));
    });
  }, [rankedEvents, dataPriceBoundMax]);

  // Once listing data arrives, expand the fallback max unless URL already set price_max.
  useEffect(() => {
    if (rankedEvents == null || didExpandDefaultMax.current) return;
    didExpandDefaultMax.current = true;
    if (hadUrlPriceMax.current) return;
    queueMicrotask(() => setPriceMax(dataPriceBoundMax));
  }, [rankedEvents, dataPriceBoundMax]);

  const filtered = useMemo(() => {
    if (!rankedEvents) return [];
    const preferProximity = proximityActive && sort === "recommended";
    let rows = filterMarketplaceEvents(rankedEvents, {
      city: proximityActive ? undefined : city === "all" ? undefined : city,
      date,
      sort: preferProximity ? "soonest" : sort === "recommended" ? "soonest" : sort,
      min_price: rangeMin,
      max_price: rangeMax,
    });
    if (preferProximity) {
      rows = sortMarketplaceByProximity(rows);
    } else if (sort === "recommended" && user && recRank.size > 0) {
      rows = [...rows].sort(
        (a, b) => (recRank.get(b.id) ?? -1) - (recRank.get(a.id) ?? -1),
      );
    }
    return rows;
  }, [
    rankedEvents,
    city,
    rangeMin,
    rangeMax,
    date,
    sort,
    proximityActive,
    user,
    recRank,
  ]);

  const filterKey = [
    city,
    date,
    rangeMin,
    rangeMax,
    sort,
    proximityActive,
    location?.lat,
    location?.radiusKm,
  ].join("|");
  const [appliedFilterKey, setAppliedFilterKey] = useState(filterKey);
  if (appliedFilterKey !== filterKey) {
    setAppliedFilterKey(filterKey);
    setVisibleCount(EVENTS_PAGE_SIZE);
  }

  const visible =
    view === "calendar" || view === "map" ? filtered : filtered.slice(0, visibleCount);

  function patchFilters(patch: Partial<EventsFilterValues>) {
    if (patch.city !== undefined) setCity(patch.city);
    if (patch.date !== undefined) setDate(patch.date);
    if (patch.priceMin !== undefined) setPriceMin(patch.priceMin);
    if (patch.priceMax !== undefined) setPriceMax(patch.priceMax);
  }

  function clearAllFilters() {
    setCity("all");
    setDate("any");
    setPriceMin(0);
    setPriceMax(priceBoundMax);
    setSort("recommended");
    setVisibleCount(EVENTS_PAGE_SIZE);
  }

  function onViewChange(next: EventsViewMode) {
    setView(next);
    storeEventsView(next);
  }

  const filterValues: EventsFilterValues = {
    city,
    date,
    priceMin: rangeMin,
    priceMax: rangeMax,
  };

  return (
    <main className="min-h-screen bg-background pb-24 lg:pb-0">
      <EventsSearchHero />

      {user ? (
        <Container className="pt-6 sm:pt-8">
          <EventRecommendationsSection
            variant="rail"
            limit={8}
            surface="events_recommended_rail"
            title="Recommended for you"
            seeAllHref="/events?sort=recommended"
          />
        </Container>
      ) : null}

      <Container className="space-y-6 py-6 sm:space-y-8 sm:py-10">
        <div className="rounded-[var(--radius-lg)] border border-border bg-card p-3 shadow-[var(--shadow-soft)] dark:bg-surface-elevated sm:p-4">
          <EventsFilterBar
            values={filterValues}
            onChange={patchFilters}
            cities={cityOptions}
            priceBoundMax={priceBoundMax}
          />

          <div className="min-w-0 lg:mt-4 lg:border-t lg:border-border lg:pt-3">
            <EventsResultsToolbar
              total={filtered.length}
              visible={visible.length}
              loading={rankedEvents === null}
              sort={sort}
              onSortChange={setSort}
              view={view}
              onViewChange={onViewChange}
            />
          </div>
        </div>

        <section id="results" className="scroll-mt-24 space-y-5">
          {geoNotice ? (
            <div className="rounded-[var(--radius-lg)] border border-border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
              <p className="font-semibold text-foreground">
                No location access? No problem.
              </p>
              <p className="mt-1">{geoNotice}</p>
              <p className="mt-2">
                Choose a city in filters, or{" "}
                <Link
                  href="/events/this-weekend"
                  className="font-semibold text-foreground underline-offset-2 hover:underline"
                >
                  view this weekend
                </Link>
                .
              </p>
            </div>
          ) : null}

          {error ? (
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-sm text-danger">{error}</p>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => {
                  setError(null);
                  void (async () => {
                    try {
                      const [cats, rows] = await Promise.all([
                        fetchCategories(),
                        fetchPublicEvents(),
                      ]);
                      setCategories(cats);
                      setEvents(rows);
                    } catch (err) {
                      setError(
                        timeoutOrErrorMessage(err, "Failed to load events"),
                      );
                      setEvents([]);
                    }
                  })();
                }}
              >
                Retry
              </Button>
            </div>
          ) : null}

          {sort === "recommended" && !user ? (
            <p className="text-sm text-muted-foreground">
              Sign in to sort by personalized recommendations. Showing the global
              marketplace order for now.
            </p>
          ) : null}

          {rankedEvents === null ? (
            <div className="space-y-5">
              <div className="h-48 animate-pulse rounded-[var(--radius-xl)] bg-muted" />
              <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <SkeletonCard key={i} />
                ))}
              </div>
            </div>
          ) : view === "map" ? (
            <EventsResults
              events={visible}
              calendarEvents={filtered}
              view={view}
              hasLocationFilter={
                proximityActive || (city !== "all" && Boolean(city))
              }
              hasMore={false}
              onShowMore={() => undefined}
              userLocation={
                location
                  ? { lat: location.lat, lng: location.lng }
                  : null
              }
              mapFilters={{
                city: proximityActive || city === "all" ? undefined : city,
                price:
                  rangeMax === 0
                    ? "free"
                    : rangeMin > 0
                      ? "paid"
                      : "any",
                lat: location?.lat,
                lng: location?.lng,
                radius_km: location?.radiusKm,
              }}
              onOpenFilters={() => setDrawerOpen(true)}
            />
          ) : filtered.length === 0 ? (
            <EmptyDiscoveryState
              title="No events found"
              description="Try another location, date, or price."
              onClearFilters={clearAllFilters}
              nearbyHref="/events"
              suggestedCategories={categories.slice(0, 5).map((c) => ({
                name: c.name,
                href: `/events/c/${c.slug}`,
              }))}
            />
          ) : (
            <EventsResults
              events={visible}
              calendarEvents={filtered}
              view={view}
              hasLocationFilter={
                proximityActive || (city !== "all" && Boolean(city))
              }
              hasMore={
                view !== "calendar" && visible.length < filtered.length
              }
              onShowMore={() =>
                setVisibleCount((n) => n + EVENTS_PAGE_SIZE)
              }
              dateFilterActive={date !== "any"}
              onClearDateFilter={() => setDate("any")}
            />
          )}
        </section>
      </Container>

      {rankedEvents !== null ? (
        <EventsMarketplaceBottomDiscovery
          events={rankedEvents}
          categories={categories}
          activeCitySlug={
            !proximityActive && city !== "all" ? city : undefined
          }
        />
      ) : null}

      <EventsFilterDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        values={filterValues}
        onChange={patchFilters}
        cities={cityOptions}
        priceBoundMax={priceBoundMax}
        onApply={() => setDrawerOpen(false)}
        onClear={() => {
          clearAllFilters();
          setDrawerOpen(false);
        }}
      />

      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-card/95 p-3 shadow-[var(--shadow-strong)] backdrop-blur-md dark:bg-surface-elevated/95 lg:hidden">
        <Container className="flex items-center gap-2 !px-0">
          <Button
            type="button"
            variant="secondary"
            className="min-h-11 flex-1"
            onClick={() => setDrawerOpen(true)}
          >
            Filters
          </Button>
          <Button
            type="button"
            className="min-h-11 flex-1"
            onClick={() =>
              document
                .getElementById("results")
                ?.scrollIntoView({ behavior: "smooth", block: "start" })
            }
          >
            {filtered.length} events
          </Button>
        </Container>
      </div>
    </main>
  );
}

/** Focused /events marketplace — search, filters, results. No landing rails. */
export function EventsMarketplaceClient({
  initialEvents = null,
  initialCategories = [],
}: {
  initialEvents?: EventItem[] | null;
  initialCategories?: EventCategory[];
} = {}) {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-background">
          <Container className="py-16 text-sm text-muted-foreground">
            Loading events…
          </Container>
        </main>
      }
    >
      <EventsMarketplaceInner
        initialEvents={initialEvents}
        initialCategories={initialCategories}
      />
    </Suspense>
  );
}
