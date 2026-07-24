"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  useEffect,
  useMemo,
  useState,
  useTransition,
  type ReactNode,
} from "react";

import { ActiveFilters } from "@/components/discovery/ActiveFilters";
import { DiscoveryAdjacentSection } from "@/components/discovery/DiscoveryAdjacentSection";
import { DiscoveryBrowseSection } from "@/components/discovery/DiscoveryBrowseSection";
import { DiscoveryCollectionsSection } from "@/components/discovery/DiscoveryCollectionsSection";
import { DiscoveryHubHero } from "@/components/discovery/DiscoveryHubHero";
import { EmptyDiscoveryState } from "@/components/discovery/EmptyDiscoveryState";
import { HeroDiscoverySearch } from "@/components/discovery/HeroDiscoverySearch";
import type { LocationFilterValue } from "@/components/discovery/LocationFilterBar";
import { PadeyaPicksSection } from "@/components/discovery/PadeyaPicksSection";
import { SearchResultsHeader } from "@/components/discovery/SearchResultsHeader";
import { SortSelect } from "@/components/discovery/SortSelect";
import { HomeCardCarousel } from "@/components/home/HomeCardCarousel";
import { MarketplaceBreadcrumbs } from "@/components/layout/MarketplaceBreadcrumbs";
import { TaxonomyEventCard } from "@/components/taxonomy/TaxonomyEventCard";
import { Button, Container, Select, SkeletonCard } from "@/components/ui";
import type { BreadcrumbItem } from "@/components/ui/Breadcrumb";
import {
  categoryStory,
  cityStory,
} from "@/lib/discovery/category-stories";
import {
  EVENT_LISTING_CAROUSEL_SLIDE,
  EVENT_LISTING_GRID_MARKETPLACE,
} from "@/lib/discovery/event-listing-layout";
import {
  filterPublicEvents,
  type EventDiscoveryFilters,
  type SortKey,
} from "@/lib/discovery/event-filters";
import type { HubKind } from "@/lib/discovery/hub-kind";
import { resolvePadeyaPicks } from "@/lib/discovery/padeya-picks";
import { citySlugFromName } from "@/lib/discovery/slugify";
import { sortByEventCount } from "@/lib/discovery/sort-by-availability";
import {
  fetchPadeyaPicks,
  type PadeyaPicksQuery,
} from "@/lib/placements-api";
import type { EventCategory, EventItem } from "@/lib/types/events";
import type { LocationKind, TaxonomyLocation } from "@/lib/taxonomy-api";
import { locationHubPath } from "@/lib/taxonomy-api";

export type DiscoveryHeroProps = {
  title: string;
  description: string;
  ctaLabel?: string;
  ctaHref?: string;
  secondaryCtaLabel?: string;
  secondaryCtaHref?: string;
  eyebrow?: string;
};

const SORT_OPTIONS: SortKey[] = [
  "soonest",
  "newest",
  "featured",
  "trending",
  "price_asc",
  "price_desc",
];

function parseSort(raw: string | null): SortKey {
  if (raw && SORT_OPTIONS.includes(raw as SortKey)) return raw as SortKey;
  return "soonest";
}

export function EventDiscoveryView({
  crumbs,
  hero,
  heroProps,
  events,
  categories,
  loading,
  error,
  initial,
  locked,
  hubKind = "all",
  showCategoryNav = true,
  showCityNav = true,
  locationChildren = [],
  locationKind,
  locationSlug,
  locationName,
  picksQuery,
  picksTitle,
}: {
  crumbs: BreadcrumbItem[];
  /** @deprecated Prefer heroProps so hero search can share filter state. */
  hero?: ReactNode;
  heroProps?: DiscoveryHeroProps;
  events: EventItem[] | null;
  categories: EventCategory[];
  loading?: boolean;
  error?: string | null;
  initial?: Partial<EventDiscoveryFilters>;
  locked?: Partial<
    Pick<
      EventDiscoveryFilters,
      "category" | "city" | "weekend" | "paid" | "event_format" | "secret_location"
    >
  >;
  hubKind?: HubKind;
  showCategoryNav?: boolean;
  showCityNav?: boolean;
  locationChildren?: TaxonomyLocation[];
  locationKind?: string | null;
  locationSlug?: string | null;
  locationName?: string | null;
  picksQuery?: PadeyaPicksQuery;
  picksTitle?: string;
}) {
  const router = useRouter();
  const pathname = usePathname() || "/events";
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();
  const [padeyaPicks, setPadeyaPicks] = useState<EventItem[]>([]);
  const [refineOpen, setRefineOpen] = useState(false);

  const locationFilterValue: LocationFilterValue = useMemo(() => {
    const kind = (searchParams.get("location_kind") ||
      locationKind ||
      "") as LocationKind;
    const slug = searchParams.get("location_slug") || locationSlug || "";
    if (!kind || !slug) return null;
    return {
      kind,
      slug,
      name: locationName || slug.replace(/-/g, " "),
    };
  }, [searchParams, locationKind, locationSlug, locationName]);

  const resolvedPicksQuery: PadeyaPicksQuery = useMemo(() => {
    if (picksQuery) return picksQuery;
    const kind = locationFilterValue?.kind;
    const slug = locationFilterValue?.slug;
    if (kind && slug) {
      return {
        context: `${kind}_page`,
        location_kind: kind,
        location_slug: slug,
      };
    }
    return { context: "events_page" };
  }, [picksQuery, locationFilterValue?.kind, locationFilterValue?.slug]);
  const picksQueryKey = JSON.stringify(resolvedPicksQuery);

  useEffect(() => {
    void fetchPadeyaPicks(resolvedPicksQuery)
      .then(setPadeyaPicks)
      .catch(() => setPadeyaPicks([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- keyed by serialized query
  }, [picksQueryKey]);

  function setLocationFilter(next: LocationFilterValue) {
    const params = new URLSearchParams(searchParams.toString());
    if (!next) {
      params.delete("location_kind");
      params.delete("location_slug");
      params.delete("city");
    } else {
      params.set("location_kind", next.kind);
      params.set("location_slug", next.slug);
      // Prefer taxonomy cascade over legacy free-text city facet.
      params.delete("city");
    }
    const qs = params.toString();
    startTransition(() => {
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    });
  }

  const [q, setQ] = useState(
    () => searchParams.get("q") || initial?.q || "",
  );
  const [categoryState, setCategory] = useState(
    () =>
      locked?.category ||
      searchParams.get("category") ||
      initial?.category ||
      "all",
  );
  const [cityState, setCity] = useState(
    () => locked?.city || searchParams.get("city") || initial?.city || "all",
  );
  const [sort, setSort] = useState<SortKey>(() =>
    parseSort(searchParams.get("sort") || initial?.sort || null),
  );
  const [paidState, setPaid] = useState<"any" | "free" | "paid">(
    () =>
      (locked?.paid as "free" | "paid" | undefined) ||
      (searchParams.get("paid") as "free" | "paid" | null) ||
      initial?.paid ||
      "any",
  );
  const [eventFormatState, setEventFormat] = useState(
    () =>
      locked?.event_format ||
      searchParams.get("event_format") ||
      initial?.event_format ||
      "all",
  );
  const [secretOnlyState, setSecretOnly] = useState(
    () =>
      locked?.secret_location === true ||
      searchParams.get("secret_location") === "1" ||
      initial?.secret_location === true,
  );
  const [weekendState, setWeekend] = useState(
    () =>
      locked?.weekend === true ||
      searchParams.get("weekend") === "1" ||
      initial?.weekend === true,
  );
  const [maxPriceState, setMaxPrice] = useState<number | null>(() => {
    const raw = searchParams.get("max_price");
    if (!raw) return null;
    const n = Number(raw);
    return Number.isFinite(n) && n >= 0 ? n : null;
  });

  const category = locked?.category || categoryState;
  const city = locked?.city || cityState;
  const paid = locked?.paid || paidState;
  const eventFormat = locked?.event_format || eventFormatState;
  const secretOnly =
    locked?.secret_location === true ? true : secretOnlyState;
  const weekend = locked?.weekend === true ? true : weekendState;
  const maxPrice = maxPriceState;

  useEffect(() => {
    const params = new URLSearchParams();
    if (q.trim()) params.set("q", q.trim());
    if (!locked?.category && category !== "all") params.set("category", category);
    // Preserve taxonomy cascade; only write legacy city when cascade is idle.
    if (locationFilterValue) {
      params.set("location_kind", locationFilterValue.kind);
      params.set("location_slug", locationFilterValue.slug);
    } else if (!locked?.city && city !== "all") {
      params.set("city", city);
    }
    if (!locked?.paid && paid !== "any") params.set("paid", paid);
    if (maxPrice != null) params.set("max_price", String(maxPrice));
    if (weekend) params.set("weekend", "1");
    if (!locked?.event_format && eventFormat !== "all") {
      params.set("event_format", eventFormat);
    }
    if (secretOnly && !locked?.secret_location) params.set("secret_location", "1");
    if (sort !== "soonest") params.set("sort", sort);
    const qs = params.toString();
    const next = qs ? `${pathname}?${qs}` : pathname;
    const currentQs = searchParams.toString();
    const current = currentQs ? `${pathname}?${currentQs}` : pathname;
    if (next !== current) {
      startTransition(() => {
        router.replace(next, { scroll: false });
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional: write URL from filter state only
  }, [
    q,
    category,
    city,
    paid,
    maxPrice,
    sort,
    eventFormat,
    secretOnly,
    weekend,
    locked?.category,
    locked?.city,
    locked?.paid,
    locked?.event_format,
    locked?.secret_location,
    pathname,
    router,
    locationFilterValue?.kind,
    locationFilterValue?.slug,
  ]);

  const cities = useMemo(() => {
    const set = new Set(
      (events ?? []).map((e) => e.city).filter((c): c is string => Boolean(c)),
    );
    return Array.from(set).sort();
  }, [events]);

  const filtered = useMemo(() => {
    if (!events) return [];
    return filterPublicEvents(events, {
      q,
      category: category === "all" ? undefined : category,
      city: city === "all" ? undefined : city,
      weekend: weekend || undefined,
      paid,
      max_price: maxPrice ?? undefined,
      event_format: eventFormat === "all" ? undefined : eventFormat,
      secret_location: secretOnly || locked?.secret_location || undefined,
      sort,
    });
  }, [
    events,
    q,
    category,
    city,
    paid,
    maxPrice,
    sort,
    eventFormat,
    secretOnly,
    weekend,
    locked?.secret_location,
  ]);

  const featured = useMemo(
    () => resolvePadeyaPicks(padeyaPicks, events ?? [], 2),
    [padeyaPicks, events],
  );

  const placementEventIds = useMemo(
    () => padeyaPicks.map((e) => e.id),
    [padeyaPicks],
  );

  const featuredIds = useMemo(
    () => new Set(featured.map((e) => e.id)),
    [featured],
  );

  const results = useMemo(
    () => filtered.filter((e) => !featuredIds.has(e.id)),
    [filtered, featuredIds],
  );

  const active = useMemo(() => {
    const chips: { id: string; label: string; locked?: boolean }[] = [];
    if (q.trim()) chips.push({ id: "q", label: `“${q.trim()}”` });
    if (category !== "all") {
      const name =
        categories.find((c) => c.slug === category)?.name ?? category;
      chips.push({
        id: "category",
        label: name,
        locked: Boolean(locked?.category),
      });
    }
    if (locationFilterValue) {
      chips.push({
        id: "location",
        label: locationFilterValue.name,
        locked: Boolean(
          locationKind &&
            locationSlug &&
            hubKind !== "all" &&
            hubKind !== "location_index",
        ),
      });
    } else if (city !== "all") {
      const label =
        cities.find((c) => citySlugFromName(c) === city) ?? city;
      chips.push({
        id: "city",
        label,
        locked: Boolean(locked?.city),
      });
    }
    if (paid !== "any") {
      chips.push({
        id: "paid",
        label: paid === "free" ? "Free" : "Paid",
        locked: Boolean(locked?.paid),
      });
    }
    if (maxPrice != null) {
      chips.push({
        id: "max_price",
        label: `Under ₦${maxPrice.toLocaleString("en-NG")}`,
      });
    }
    if (weekend) {
      chips.push({
        id: "weekend",
        label: "This weekend",
        locked: Boolean(locked?.weekend),
      });
    }
    if (eventFormat !== "all") {
      chips.push({
        id: "event_format",
        label: eventFormat.replaceAll("_", " "),
        locked: Boolean(locked?.event_format),
      });
    }
    if (secretOnly || locked?.secret_location) {
      chips.push({
        id: "secret_location",
        label: "Secret location",
        locked: Boolean(locked?.secret_location),
      });
    }
    return chips;
  }, [
    q,
    category,
    city,
    paid,
    maxPrice,
    eventFormat,
    secretOnly,
    categories,
    cities,
    locked,
    weekend,
    locationFilterValue,
    locationKind,
    locationSlug,
    hubKind,
  ]);

  function clearFilter(id: string) {
    if (id === "q") setQ("");
    if (id === "category" && !locked?.category) setCategory("all");
    if (id === "city" && !locked?.city) setCity("all");
    if (id === "location") setLocationFilter(null);
    if (id === "paid" && !locked?.paid) setPaid("any");
    if (id === "max_price") setMaxPrice(null);
    if (id === "event_format" && !locked?.event_format) setEventFormat("all");
    if (id === "secret_location" && !locked?.secret_location) setSecretOnly(false);
    if (id === "weekend" && !locked?.weekend) setWeekend(false);
  }

  function clearAllFilters() {
    setQ("");
    if (!locked?.category) setCategory("all");
    if (!locked?.city) setCity("all");
    if (hubKind === "all" || hubKind === "location_index") {
      setLocationFilter(null);
    }
    if (!locked?.paid) setPaid("any");
    setMaxPrice(null);
    if (!locked?.event_format) setEventFormat("all");
    if (!locked?.secret_location) setSecretOnly(false);
    if (!locked?.weekend) setWeekend(false);
  }

  function scrollToResults() {
    document
      .getElementById("results")
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function openRefine() {
    setRefineOpen(true);
    scrollToResults();
  }

  const hierarchyTitle =
    locked?.category && locked?.city
      ? "Related experiences nearby"
      : locked?.category
        ? "Cities hosting this experience"
        : locked?.city
          ? "Start with the kind of experience you want"
          : "Start with the kind of experience you want";

  const hierarchyDescription =
    locked?.category && locked?.city
      ? "Jump to related categories without leaving this city."
      : locked?.category
        ? "Open a city hub to see this category in context."
      : locked?.city
        ? "Pick a category to narrow what’s on in this city."
        : "Nightlife, comedy, tech, gospel, campus, and more — each with a clearer path in.";

  const showCollections =
    hubKind === "all" ||
    hubKind === "category" ||
    hubKind === "city" ||
    hubKind === "city_category";

  const collectionCounts = useMemo(() => {
    const list = events ?? [];
    const weekendCount = filterPublicEvents(list, { weekend: true }).length;
    const freeCount = filterPublicEvents(list, { paid: "free" }).length;
    const vipCount = list.filter((e) =>
      (e.ticket_types ?? []).some((t) =>
        ["vip", "vvip"].includes(String(t.type || "").toLowerCase()),
      ),
    ).length;
    return { weekendCount, freeCount, vipCount, total: list.length };
  }, [events]);

  const collections =
    hubKind === "all"
      ? [
          {
            label: "This weekend",
            href: "/events/this-weekend",
            hint: "Friday through Sunday — nights already on the calendar.",
            cta: "View collection",
            count: collectionCounts.weekendCount,
            curator: "Pàdéyá",
            coverTone: "dark" as const,
          },
          {
            label: "Free",
            href: "/events/free",
            hint: "Zero-ticket and free RSVP experiences worth showing up for.",
            cta: "View collection",
            count: collectionCounts.freeCount,
            curator: "Pàdéyá",
            coverTone: "accent" as const,
          },
          {
            label: "VIP",
            href: "/events/vip",
            hint: "VIP and VVIP tiers for rooms that go deeper than general entry.",
            cta: "View collection",
            count: collectionCounts.vipCount,
            curator: "Pàdéyá",
            coverTone: "dark" as const,
          },
          {
            label: "Near me",
            href: "/events/near-me",
            hint: "Start with city hubs while precise geo discovery rolls out.",
            cta: "View collection",
            curator: "Pàdéyá",
            coverTone: "light" as const,
          },
        ]
      : [
          {
            label: "This weekend",
            href: "/events/this-weekend",
            hint: "Friday through Sunday — nights already on the calendar.",
            cta: "View collection",
            count: collectionCounts.weekendCount,
            curator: "Pàdéyá",
          },
          {
            label: "Free",
            href: "/events/free",
            hint: "Zero-ticket and free RSVP experiences worth showing up for.",
            cta: "View collection",
            count: collectionCounts.freeCount,
            curator: "Pàdéyá",
          },
          {
            label: "VIP",
            href: "/events/vip",
            hint: "VIP and VVIP tiers for rooms that go deeper than general entry.",
            cta: "View collection",
            count: collectionCounts.vipCount,
            curator: "Pàdéyá",
          },
          {
            label: "All events",
            href: "/events",
            hint: "Return to the full marketplace and start fresh.",
            cta: "Open marketplace",
            count: collectionCounts.total,
            curator: "Pàdéyá",
          },
        ];

  const categoryCounts = useMemo(() => {
    const map = new Map<string, number>();
    for (const event of events ?? []) {
      const slug = event.category?.slug;
      if (!slug) continue;
      map.set(slug, (map.get(slug) ?? 0) + 1);
    }
    return map;
  }, [events]);

  const cityCounts = useMemo(() => {
    const map = new Map<string, number>();
    for (const event of events ?? []) {
      if (!event.city) continue;
      const slug = citySlugFromName(event.city);
      map.set(slug, (map.get(slug) ?? 0) + 1);
    }
    return map;
  }, [events]);

  const categoriesByAvailability = useMemo(
    () => sortByEventCount(categories, categoryCounts),
    [categories, categoryCounts],
  );

  const citiesByAvailability = useMemo(() => {
    return [...cities].sort((a, b) => {
      const ca = cityCounts.get(citySlugFromName(a)) ?? 0;
      const cb = cityCounts.get(citySlugFromName(b)) ?? 0;
      if (cb !== ca) return cb - ca;
      return a.localeCompare(b);
    });
  }, [cities, cityCounts]);

  const adjacentLinks = useMemo(() => {
    const links: {
      label: string;
      href: string;
      hint?: string;
      eyebrow?: string;
    }[] = [];
    if (locked?.category && !locked?.city) {
      for (const c of citiesByAvailability.slice(0, 4)) {
        const slug = citySlugFromName(c);
        links.push({
          eyebrow: "City × category",
          label: `${c} · ${categories.find((x) => x.slug === locked.category)?.name || locked.category}`,
          href: `/events/city/${slug}/${locked.category}`,
          hint: cityStory(slug, c).hint,
        });
      }
    } else if (locked?.city && !locked?.category) {
      for (const cat of categoriesByAvailability.slice(0, 4)) {
        links.push({
          eyebrow: "Popular combination",
          label: `${cat.name} in ${locked.city}`,
          href: `/events/city/${locked.city}/${cat.slug}`,
          hint: categoryStory(cat.slug, cat.name).hint,
        });
      }
    } else if (locked?.city && locked?.category) {
      links.push({
        eyebrow: "City",
        label: "All events in this city",
        href: `/events/city/${locked.city}`,
        hint: cityStory(locked.city).hint,
      });
      links.push({
        eyebrow: "Category",
        label: "All events in this category",
        href: `/events/c/${locked.category}`,
        hint: categoryStory(locked.category).hint,
      });
      links.push({
        eyebrow: "Collection",
        label: "This weekend",
        href: "/events/this-weekend",
        hint: "Friday through Sunday across the marketplace.",
      });
    } else {
      for (const cat of categoriesByAvailability.slice(0, 3)) {
        links.push({
          eyebrow: "Category",
          label: cat.name,
          href: `/events/c/${cat.slug}`,
          hint: categoryStory(cat.slug, cat.name).hint,
        });
      }
      links.push({
        eyebrow: "City",
        label: "Lagos",
        href: "/events/city/lagos",
        hint: cityStory("lagos").hint,
      });
      links.push({
        eyebrow: "Popular combination",
        label: "Nightlife in Lagos",
        href: "/events/city/lagos/nightlife",
        hint: "A high-intent city × category path.",
      });
      links.push({
        eyebrow: "Hosts",
        label: "Meet verified hosts",
        href: "/hosts",
        hint: "Legacy Pages with reputation that compounds.",
      });
    }
    return links;
  }, [locked, citiesByAvailability, categories, categoriesByAvailability]);

  const browseCategoryItems = categoriesByAvailability.slice(0, 16).map((c) => {
    const story = categoryStory(c.slug, c.name, c.description);
    return {
      name: c.name,
      slug: c.slug,
      href: locked?.city
        ? `/events/city/${locked.city}/${c.slug}`
        : `/events/c/${c.slug}`,
      hint: story.hint,
      description: story.story,
      count: categoryCounts.get(c.slug),
    };
  });

  const browseCityItems = citiesByAvailability.slice(0, 12).map((c) => {
    const slug = citySlugFromName(c);
    const story = cityStory(slug, c);
    return {
      name: c,
      slug,
      href: locked?.category
        ? `/events/city/${slug}/${locked.category}`
        : `/events/city/${slug}`,
      hint: story.hint,
      description: story.story,
      count: cityCounts.get(slug),
    };
  });

  const resultsSubtitle = useMemo(() => {
    const n = filtered.length;
    const catName =
      category !== "all"
        ? categories.find((c) => c.slug === category)?.name || category
        : null;
    const cityLabel =
      locationFilterValue?.name ||
      (city !== "all"
        ? cities.find((c) => citySlugFromName(c) === city) || city
        : null);
    if (n === 0) return "No events match — try another location or category.";
    const countLabel = `${n.toLocaleString()} verified`;
    if (cityLabel && catName) {
      return `Showing ${countLabel} ${catName} events in ${cityLabel}`;
    }
    if (cityLabel) {
      return `Showing ${countLabel} events in ${cityLabel}`;
    }
    if (catName) {
      return `Showing ${countLabel} ${catName} events`;
    }
    if (weekend) {
      return `Showing ${countLabel} weekend events`;
    }
    return `Showing ${countLabel} events`;
  }, [
    filtered.length,
    category,
    city,
    categories,
    cities,
    weekend,
    locationFilterValue,
  ]);

  const showHeroSearch = Boolean(heroProps);
  const cityOptions = useMemo(
    () =>
      citiesByAvailability.map((name) => ({
        slug: citySlugFromName(name),
        name,
      })),
    [citiesByAvailability],
  );

  const childBrowseItems = locationChildren.map((child) => ({
    name: child.name,
    slug: child.slug,
    href: locationHubPath(child.kind, child.slug),
    hint: child.kind,
    description: `${child.kind} on Pàdéyá`,
  }));

  const browseCategoryItemsSelected = browseCategoryItems.map((item) => ({
    ...item,
    selected: category !== "all" && item.slug === category,
  }));

  return (
    <main className="bg-background pb-20 sm:pb-0">
      <MarketplaceBreadcrumbs items={crumbs} />
      {heroProps ? (
        <DiscoveryHubHero
          {...heroProps}
          search={
            showHeroSearch ? (
              <HeroDiscoverySearch
                values={{
                  q,
                  category,
                  city,
                  weekend,
                }}
                onChange={(next) => {
                  if (next.q !== undefined) setQ(next.q);
                  if (next.category !== undefined && !locked?.category) {
                    setCategory(next.category);
                  }
                  if (next.city !== undefined && !locked?.city) {
                    setCity(next.city);
                    if (next.city === "all") setLocationFilter(null);
                  }
                  if (next.weekend !== undefined && !locked?.weekend) {
                    setWeekend(next.weekend);
                  }
                }}
                onSearch={scrollToResults}
                categories={categoriesByAvailability}
                cities={cityOptions}
                events={events ?? []}
                lockedCategory={Boolean(locked?.category)}
                lockedCity={Boolean(locked?.city)}
                lockedWeekend={Boolean(locked?.weekend)}
              />
            ) : undefined
          }
        />
      ) : (
        hero
      )}

      {childBrowseItems.length > 0 ? (
        <DiscoveryBrowseSection
          title={`Explore in ${locationName || "this place"}`}
          description="Drill into the next level of the location tree."
          mode="city"
          items={childBrowseItems}
          maxVisible={8}
        />
      ) : null}

      {showCategoryNav && !locked?.category ? (
        <DiscoveryBrowseSection
          title={hierarchyTitle}
          description={hierarchyDescription}
          mode="category"
          items={browseCategoryItemsSelected}
          maxVisible={8}
          viewAllLabel="View all categories"
        />
      ) : null}
      {showCategoryNav && locked?.category && !locked?.city ? (
        <DiscoveryBrowseSection
          title={hierarchyTitle}
          description={hierarchyDescription}
          mode="city"
          items={browseCityItems}
          maxVisible={8}
        />
      ) : null}
      {showCityNav && locked?.city && !locked?.category ? (
        <DiscoveryBrowseSection
          title={hierarchyTitle}
          description={hierarchyDescription}
          mode="category"
          items={browseCategoryItemsSelected}
          maxVisible={8}
          viewAllLabel="View all categories"
        />
      ) : null}
      {locked?.category && locked?.city ? (
        <DiscoveryBrowseSection
          title={hierarchyTitle}
          description={hierarchyDescription}
          mode="category"
          items={browseCategoryItemsSelected}
          maxVisible={8}
          viewAllLabel="View all categories"
        />
      ) : null}

      {!loading && featured.length > 0 ? (
        <PadeyaPicksSection
          events={featured}
          title="Pàdéyá Picks"
          eyebrow={
            picksTitle &&
            picksTitle !== "Pàdéyá Picks" &&
            picksTitle !== "Global Pàdéyá Picks"
              ? picksTitle.replace(/\s*Pàdéyá Picks\s*$/i, "").trim() ||
                undefined
              : locationName || undefined
          }
          layout="spotlight"
          analytics={{
            placementContext: resolvedPicksQuery.context || "events_page",
            placementEventIds,
            category:
              locked?.category && locked.category !== "all"
                ? locked.category
                : categoryState !== "all"
                  ? categoryState
                  : undefined,
            ...(locationFilterValue?.kind === "country"
              ? { country: locationFilterValue.name }
              : locationFilterValue?.kind === "state"
                ? { state: locationFilterValue.name }
                : locationFilterValue?.kind === "city"
                  ? { city: locationFilterValue.name }
                  : locationFilterValue?.kind === "area"
                    ? { area: locationFilterValue.name }
                    : locationKind === "country"
                      ? { country: locationName || undefined }
                      : locationKind === "state"
                        ? { state: locationName || undefined }
                        : locationKind === "city"
                          ? { city: locationName || undefined }
                          : locationKind === "area"
                            ? { area: locationName || undefined }
                            : {}),
          }}
        />
      ) : null}

      <section
        id="results"
        className="scroll-mt-28 border-t border-border bg-background py-10 sm:py-12"
        aria-label="Event results"
      >
        <Container className="space-y-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <SearchResultsHeader
              title="What’s on next"
              count={filtered.length}
              subtitle={resultsSubtitle}
            />
            <div className="flex flex-wrap items-end gap-3">
              <SortSelect
                value={sort}
                onChange={(v) => setSort(v as SortKey)}
                className="min-w-[11rem]"
                options={[
                  { value: "soonest", label: "Soonest" },
                  { value: "newest", label: "Newest" },
                  { value: "featured", label: "Featured" },
                  { value: "trending", label: "Trending" },
                  { value: "price_asc", label: "Price · low to high" },
                  { value: "price_desc", label: "Price · high to low" },
                ]}
              />
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="sm:hidden"
                onClick={() => setRefineOpen((v) => !v)}
              >
                Refine{active.length ? ` · ${active.length}` : ""}
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="hidden sm:inline-flex"
                onClick={() => setRefineOpen((v) => !v)}
              >
                {refineOpen ? "Hide refine" : "Refine"}
              </Button>
            </div>
          </div>

          <ActiveFilters
            items={active}
            onRemove={clearFilter}
            onClearAll={clearAllFilters}
          />

          {refineOpen ? (
            <div
              id="refine"
              className="grid gap-3 rounded-[var(--radius-lg)] border border-border bg-muted p-4 sm:grid-cols-2 lg:grid-cols-4"
            >
              {!locationFilterValue ? (
                <Select
                  label="City"
                  value={city}
                  disabled={Boolean(locked?.city)}
                  onChange={(e) => setCity(e.target.value)}
                >
                  <option value="all">All cities</option>
                  {citiesByAvailability.map((c) => (
                    <option key={c} value={citySlugFromName(c)}>
                      {c}
                    </option>
                  ))}
                </Select>
              ) : null}
              <Select
                label="Price"
                value={paid}
                disabled={Boolean(locked?.paid)}
                onChange={(e) =>
                  setPaid(e.target.value as "any" | "free" | "paid")
                }
              >
                <option value="any">Any price</option>
                <option value="free">Free</option>
                <option value="paid">Paid</option>
              </Select>
              <Select
                label="Format"
                value={eventFormat}
                disabled={Boolean(locked?.event_format)}
                onChange={(e) => setEventFormat(e.target.value)}
              >
                <option value="all">Any format</option>
                <option value="public">In person</option>
                <option value="online">Online</option>
                <option value="hybrid">Hybrid</option>
                <option value="secret_location">Secret location</option>
              </Select>
              {!locked?.category ? (
                <Select
                  label="Category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                >
                  <option value="all">All categories</option>
                  {categoriesByAvailability.map((c) => (
                    <option key={c.id} value={c.slug}>
                      {c.name}
                    </option>
                  ))}
                </Select>
              ) : null}
            </div>
          ) : (
            <div id="refine" className="sr-only" aria-hidden />
          )}

          {error ? <p className="text-sm text-danger">{error}</p> : null}

          {loading || events === null ? (
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </div>
          ) : filtered.length === 0 ? (
            <EmptyDiscoveryState
              title="No events match"
              description="Try another location or category, or clear filters to see what’s on across Pàdéyá."
              onClearFilters={clearAllFilters}
              suggestedCategories={categoriesByAvailability
                .slice(0, 5)
                .map((c) => ({
                  name: c.name,
                  href: `/events/c/${c.slug}`,
                }))}
              nearbyHref="/events"
            />
          ) : (
            <HomeCardCarousel
              label="Discovery events"
              until="sm"
              desktopGridClassName={EVENT_LISTING_GRID_MARKETPLACE}
              slideClassName={EVENT_LISTING_CAROUSEL_SLIDE}
            >
              {(results.length ? results : filtered).map((event, index) => (
                <div
                  key={event.id}
                  className="padeya-section-enter min-w-0 h-full"
                  style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}
                >
                  <TaxonomyEventCard event={event} />
                </div>
              ))}
            </HomeCardCarousel>
          )}
        </Container>
      </section>

      {showCollections ? (
        <DiscoveryCollectionsSection
          title={
            hubKind === "all"
              ? "Browse by scene"
              : "Jump to another useful path"
          }
          description={
            hubKind === "all"
              ? "Weekend, free, VIP, and nearby — keep exploring without starting over."
              : "Move between weekend, free, VIP, and the full marketplace without losing context."
          }
          collections={collections}
        />
      ) : null}

      <DiscoveryAdjacentSection
        links={adjacentLinks.map((link) => ({
          ...link,
          count:
            link.eyebrow === "Category"
              ? categoryCounts.get(
                  categories.find((c) => link.href.endsWith(`/c/${c.slug}`))
                    ?.slug || "",
                )
              : undefined,
        }))}
      />

      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-card/95 p-3 shadow-[var(--shadow-strong)] backdrop-blur-md dark:bg-surface-elevated/95 sm:hidden">
        <Container className="flex items-center gap-2 !px-0">
          <Button
            type="button"
            variant="secondary"
            className="min-h-11 flex-1"
            onClick={openRefine}
          >
            Refine{active.length ? ` · ${active.length}` : ""}
          </Button>
          <Button
            type="button"
            variant="primary"
            className="padeya-btn-ripple min-h-11 flex-1"
            onClick={scrollToResults}
          >
            {filtered.length} events
          </Button>
        </Container>
      </div>
    </main>
  );
}
