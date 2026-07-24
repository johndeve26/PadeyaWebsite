"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { EventDiscoveryView } from "@/components/discovery/EventDiscoveryView";
import { Container } from "@/components/ui";
import {
  categoryStory,
  cityStory,
} from "@/lib/discovery/category-stories";
import type { EventDiscoveryFilters } from "@/lib/discovery/event-filters";
import type { HubKind } from "@/lib/discovery/hub-kind";
import {
  formatLandingPath,
  isFormatHubKey,
} from "@/lib/discovery/format-landing";
import {
  parseMaxPriceParam,
  priceLandingPath,
} from "@/lib/discovery/price-landing";
import { fetchCategories, fetchPublicEvents } from "@/lib/events-api";
import {
  buildCategoryTrail,
  buildCityCategoryTrail,
  buildCityTrail,
  buildDiscoveryTrail,
  buildHomeEvents,
  buildLocationTrail,
  buildStateCategoryTrail,
} from "@/lib/marketplace-breadcrumbs";
import type { EventCategory, EventItem } from "@/lib/types/events";
import type { TaxonomyLocation } from "@/lib/taxonomy-api";

export type { HubKind };

function DiscoveryHubInner({
  kind,
  categorySlug,
  categoryName,
  categoryDescription,
  citySlug,
  cityName,
  locationKind,
  locationSlug,
  locationName,
  locationAncestors = [],
  locationChildren = [],
}: {
  kind: HubKind;
  categorySlug?: string;
  categoryName?: string;
  categoryDescription?: string;
  citySlug?: string;
  cityName?: string;
  locationKind?: string;
  locationSlug?: string;
  locationName?: string;
  locationAncestors?: TaxonomyLocation[];
  locationChildren?: TaxonomyLocation[];
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlLocKind = searchParams.get("location_kind");
  const urlLocSlug = searchParams.get("location_slug");
  const urlMaxPrice = searchParams.get("max_price");
  const urlEventFormat = searchParams.get("event_format");

  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [categories, setCategories] = useState<EventCategory[]>([]);
  const [error, setError] = useState<string | null>(null);

  const effectiveLocKind =
    locationKind || (kind === "all" ? urlLocKind || undefined : undefined);
  const effectiveLocSlug =
    locationSlug || (kind === "all" ? urlLocSlug || undefined : undefined);

  /** Legacy `/events?max_price=` / `?event_format=` → dedicated hubs. */
  const legacyHubRedirect = (() => {
    if (kind !== "all") return null;
    const keys = [...searchParams.keys()];
    const weekend = searchParams.get("weekend");
    const onlyPrimary =
      keys.length === 1 ||
      (keys.length === 2 && searchParams.has("weekend"));
    if (!onlyPrimary) return null;

    let target: string | null = null;
    if (urlMaxPrice) {
      const parsed = parseMaxPriceParam(urlMaxPrice);
      if (parsed != null) target = priceLandingPath(parsed);
    } else if (urlEventFormat) {
      const fmt = urlEventFormat.toLowerCase();
      if (isFormatHubKey(fmt)) target = formatLandingPath(fmt);
    }
    if (!target) return null;
    return weekend === "1" ? `${target}?weekend=1` : target;
  })();

  useEffect(() => {
    if (!legacyHubRedirect) return;
    router.replace(legacyHubRedirect);
  }, [legacyHubRedirect, router]);

  useEffect(() => {
    if (legacyHubRedirect) return;
    const filters: Parameters<typeof fetchPublicEvents>[0] = {};
    if (
      (kind === "category" || kind === "city_category" || kind === "state_category") &&
      categorySlug
    ) {
      filters.category = categorySlug;
    }
    if (kind === "city" && citySlug) {
      filters.location_kind = "city";
      filters.location_slug = citySlug;
      filters.city = citySlug;
    } else if (kind === "city_category" && citySlug) {
      filters.location_kind = "city";
      filters.location_slug = citySlug;
      filters.city = citySlug;
    } else if (kind === "country" && locationSlug) {
      filters.location_kind = "country";
      filters.location_slug = locationSlug;
    } else if (
      (kind === "state" || kind === "state_category") &&
      locationSlug
    ) {
      filters.location_kind = "state";
      filters.location_slug = locationSlug;
    } else if (kind === "area" && locationSlug) {
      filters.location_kind = "area";
      filters.location_slug = locationSlug;
    } else if (kind === "all" && effectiveLocKind && effectiveLocSlug) {
      filters.location_kind = effectiveLocKind;
      filters.location_slug = effectiveLocSlug;
    }
    if (kind === "weekend") filters.weekend = true;
    if (kind === "free") filters.paid = "free";

    void Promise.all([fetchPublicEvents(filters), fetchCategories()])
      .then(([rows, cats]) => {
        setEvents(rows);
        setCategories(cats);
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load"),
      );
  }, [
    kind,
    categorySlug,
    citySlug,
    locationSlug,
    locationKind,
    effectiveLocKind,
    effectiveLocSlug,
    legacyHubRedirect,
  ]);

  if (legacyHubRedirect) {
    return (
      <main className="bg-background">
        <Container className="py-16 text-sm text-muted-foreground">
          Opening collection…
        </Container>
      </main>
    );
  }

  const resolvedCategoryName =
    categoryName ||
    categories.find((c) => c.slug === categorySlug)?.name ||
    categorySlug ||
    "";

  let crumbs = buildHomeEvents();
  let heroTitle = "Discover events worth showing up for.";
  let heroDescription =
    "Browse verified experiences by city, category, and vibe — from nightlife and concerts to comedy, campus events, tech meetups, and culture.";
  let heroEyebrow = "Events marketplace";
  let heroCtaLabel = "Explore this weekend";
  let heroCtaHref = "/events/this-weekend";
  let heroSecondaryLabel: string | undefined = "See what’s on";
  let heroSecondaryHref: string | undefined = "#results";
  let initial: Partial<EventDiscoveryFilters> = {};
  let locked: Partial<EventDiscoveryFilters> = {};

  if (kind === "category" && categorySlug) {
    const story = categoryStory(
      categorySlug,
      resolvedCategoryName,
      categoryDescription,
    );
    crumbs = buildCategoryTrail(resolvedCategoryName, categorySlug);
    heroTitle = `${resolvedCategoryName} events on Pàdéyá`;
    heroDescription = categoryDescription || story.story;
    heroEyebrow = "Category";
    heroCtaLabel = "Browse experiences";
    heroCtaHref = "#browse";
    heroSecondaryLabel = "See what’s on";
    heroSecondaryHref = "#results";
    locked = { category: categorySlug };
    initial = { category: categorySlug };
  } else if (kind === "city" && citySlug) {
    const label = cityName || citySlug;
    const story = cityStory(citySlug, label);
    crumbs = buildCityTrail(label, citySlug);
    heroTitle = `What’s on in ${label}`;
    heroDescription = story.story;
    heroEyebrow = "City";
    heroCtaLabel = "Browse categories";
    heroCtaHref = "#browse";
    heroSecondaryLabel = "See what’s on";
    heroSecondaryHref = "#results";
    locked = { city: citySlug };
    initial = { city: citySlug };
  } else if (kind === "city_category" && citySlug && categorySlug) {
    const cLabel = cityName || citySlug;
    const story = categoryStory(
      categorySlug,
      resolvedCategoryName,
      categoryDescription,
    );
    crumbs = buildCityCategoryTrail(
      cLabel,
      citySlug,
      resolvedCategoryName,
      categorySlug,
    );
    heroTitle = `${resolvedCategoryName} in ${cLabel}`;
    heroDescription =
      categoryDescription ||
      `${story.story.replace(/\.$/, "")} — focused on ${cLabel}.`;
    heroEyebrow = "City · Category";
    heroCtaLabel = "See Pàdéyá Picks";
    heroCtaHref = "#results";
    heroSecondaryLabel = "All events";
    heroSecondaryHref = "/events";
    locked = { city: citySlug, category: categorySlug };
    initial = { city: citySlug, category: categorySlug };
  } else if (
    (kind === "country" || kind === "state" || kind === "area") &&
    locationSlug
  ) {
    const label = locationName || locationSlug;
    crumbs = buildLocationTrail(
      locationAncestors.map((a) => ({
        name: a.name,
        kind: a.kind,
        slug: a.slug,
      })),
      {
        name: label,
        kind: locationKind || kind,
        slug: locationSlug,
      },
    );
    heroTitle = `Events in ${label}`;
    heroDescription = `Discover verified experiences in ${label} on Pàdéyá — drill into areas, categories, and weekends.`;
    heroEyebrow =
      kind === "country" ? "Country" : kind === "state" ? "State" : "Area";
    heroCtaLabel = "Browse places";
    heroCtaHref = "#browse";
    heroSecondaryLabel = "See what’s on";
    heroSecondaryHref = "#results";
  } else if (kind === "state_category" && locationSlug && categorySlug) {
    const label = locationName || locationSlug;
    crumbs = buildStateCategoryTrail(
      label,
      locationSlug,
      resolvedCategoryName,
      categorySlug,
    );
    heroTitle = `${resolvedCategoryName} events in ${label}`;
    heroDescription = `Browse ${resolvedCategoryName.toLowerCase()} nights in ${label} on Pàdéyá.`;
    heroEyebrow = "State · Category";
    heroCtaLabel = "See what’s on";
    heroCtaHref = "#results";
    locked = { category: categorySlug };
    initial = { category: categorySlug };
  } else if (kind === "location_index") {
    crumbs = [
      { label: "Home", href: "/" },
      { label: "Events", href: "/events" },
      { label: "Locations" },
    ];
    heroTitle = "Events by Location";
    heroDescription =
      "Explore Pàdéyá by country, state, city, and neighborhood — the same hierarchy hosts use to place nights.";
    heroEyebrow = "Locations";
    heroCtaLabel = "Start with Nigeria";
    heroCtaHref = "/events/country/nigeria";
    heroSecondaryLabel = "All events";
    heroSecondaryHref = "/events";
  } else if (kind === "weekend") {
    crumbs = buildDiscoveryTrail("weekend");
    heroTitle = "This weekend on Pàdéyá";
    heroDescription =
      "Friday through Sunday — refine by city and category without losing your place.";
    heroEyebrow = "Collection";
    heroCtaLabel = "See what’s on";
    heroCtaHref = "#results";
    heroSecondaryLabel = "All events";
    heroSecondaryHref = "/events";
    locked = { weekend: true };
    initial = { weekend: true };
  } else if (kind === "free") {
    crumbs = buildDiscoveryTrail("free");
    heroTitle = "Free events worth showing up for";
    heroDescription =
      "Zero-ticket and free RSVP nights — still organized by city and category.";
    heroEyebrow = "Collection";
    heroCtaLabel = "See what’s on";
    heroCtaHref = "#results";
    heroSecondaryLabel = "All events";
    heroSecondaryHref = "/events";
    locked = { paid: "free" };
    initial = { paid: "free" };
  } else if (kind === "vip") {
    crumbs = buildDiscoveryTrail("vip");
    heroTitle = "VIP nights with clear tiers";
    heroDescription =
      "Events with VIP or VVIP tickets — browse, then refine by city and category.";
    heroEyebrow = "Collection";
    heroCtaLabel = "See what’s on";
    heroCtaHref = "#results";
    heroSecondaryLabel = "All events";
    heroSecondaryHref = "/events";
  } else if (kind === "near_me") {
    crumbs = buildDiscoveryTrail("near_me");
    heroTitle = "Start near you";
    heroDescription =
      "Precise geo discovery is coming. Use city hubs meanwhile — Lagos is a strong start.";
    heroEyebrow = "Collection";
    heroCtaLabel = "Browse Lagos";
    heroCtaHref = "/events/city/lagos";
    heroSecondaryLabel = "All events";
    heroSecondaryHref = "/events";
  }

  return (
    <EventDiscoveryView
      crumbs={crumbs}
      heroProps={{
        title: heroTitle,
        description: heroDescription,
        eyebrow: heroEyebrow,
        ctaHref: heroCtaHref,
        ctaLabel: heroCtaLabel,
        secondaryCtaHref: heroSecondaryHref,
        secondaryCtaLabel: heroSecondaryLabel,
      }}
      hubKind={kind}
      events={
        kind === "vip" && events
          ? events.filter((e) =>
              (e.ticket_types ?? []).some((t) =>
                ["vip", "vvip"].includes(String(t.type || "").toLowerCase()),
              ),
            )
          : kind === "near_me"
            ? []
            : events
      }
      categories={categories}
      loading={events === null && kind !== "near_me"}
      error={error}
      initial={initial}
      locked={locked}
      locationChildren={locationChildren}
      locationKind={effectiveLocKind || locationKind}
      locationSlug={effectiveLocSlug || locationSlug}
      locationName={locationName}
      picksQuery={(() => {
        if (kind === "category" && categorySlug) {
          return { context: "category_page", category: categorySlug };
        }
        if (kind === "city_category" && citySlug && categorySlug) {
          return {
            context: "city_category_page",
            location_kind: "city",
            location_slug: citySlug,
            category: categorySlug,
          };
        }
        if (kind === "city" && citySlug) {
          return {
            context: "city_page",
            location_kind: "city",
            location_slug: citySlug,
          };
        }
        if (kind === "country" && locationSlug) {
          return {
            context: "country_page",
            location_kind: "country",
            location_slug: locationSlug,
          };
        }
        if (kind === "state" && locationSlug) {
          return {
            context: "state_page",
            location_kind: "state",
            location_slug: locationSlug,
          };
        }
        if (kind === "area" && locationSlug) {
          return {
            context: "area_page",
            location_kind: "area",
            location_slug: locationSlug,
          };
        }
        if (kind === "state_category" && categorySlug) {
          return { context: "category_page", category: categorySlug };
        }
        return { context: "events_page" };
      })()}
      picksTitle={(() => {
        if (kind === "category" && resolvedCategoryName) {
          return `${resolvedCategoryName} Pàdéyá Picks`;
        }
        if (kind === "city_category" && citySlug && resolvedCategoryName) {
          return `${cityName || citySlug} ${resolvedCategoryName} Pàdéyá Picks`;
        }
        if (
          (kind === "city" ||
            kind === "country" ||
            kind === "state" ||
            kind === "area") &&
          (locationName || cityName || locationSlug || citySlug)
        ) {
          return `${locationName || cityName || locationSlug || citySlug} Pàdéyá Picks`;
        }
        if (kind === "state_category" && resolvedCategoryName) {
          return `${resolvedCategoryName} Pàdéyá Picks`;
        }
        return "Global Pàdéyá Picks";
      })()}
    />
  );
}

export function DiscoveryHubClient(props: {
  kind: HubKind;
  categorySlug?: string;
  categoryName?: string;
  categoryDescription?: string;
  citySlug?: string;
  cityName?: string;
  locationKind?: string;
  locationSlug?: string;
  locationName?: string;
  locationAncestors?: TaxonomyLocation[];
  locationChildren?: TaxonomyLocation[];
}) {
  return (
    <Suspense
      fallback={
        <main className="bg-background">
          <Container className="py-16 text-sm text-muted-foreground">
            Loading discovery…
          </Container>
        </main>
      }
    >
      <DiscoveryHubInner {...props} />
    </Suspense>
  );
}
