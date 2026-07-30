"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { DiscoveryAdjacentSection } from "@/components/discovery/DiscoveryAdjacentSection";
import { DiscoveryBrowseSection } from "@/components/discovery/DiscoveryBrowseSection";
import { DiscoveryCollectionsSection } from "@/components/discovery/DiscoveryCollectionsSection";
import { Container } from "@/components/ui";
import {
  categoryBrowseVisuals,
  cityBrowseVisuals,
} from "@/lib/discovery/browse-images";
import { categoryStory, cityStory } from "@/lib/discovery/category-stories";
import { filterPublicEvents } from "@/lib/discovery/event-filters";
import { citySlugFromName } from "@/lib/discovery/slugify";
import { sortByEventCount } from "@/lib/discovery/sort-by-availability";
import type { EventCategory, EventItem } from "@/lib/types/events";
import {
  fetchTaxonomyCategories,
  fetchTaxonomyLocations,
  type TaxonomyCategory,
  type TaxonomyLocation,
} from "@/lib/taxonomy-api";

const FORMAT_LINKS = [
  { label: "In person", href: "/events/in-person", hint: "Venues and doors you can walk into." },
  { label: "Online", href: "/events/online", hint: "Streams and virtual rooms." },
  { label: "Hybrid", href: "/events/hybrid", hint: "In-room plus remote access." },
  { label: "Today", href: "/events/today", hint: "Happening within the next 24 hours." },
  { label: "Event map", href: "/events/map", hint: "Browse on the map view." },
] as const;

export function EventsMarketplaceBottomDiscovery({
  events,
  categories,
  activeCitySlug,
}: {
  events: EventItem[];
  categories: EventCategory[];
  /** When a city filter is active, category hubs use city × category paths. */
  activeCitySlug?: string;
}) {
  const [taxonomyCategories, setTaxonomyCategories] = useState<
    Map<string, TaxonomyCategory>
  >(new Map());
  const [taxonomyCities, setTaxonomyCities] = useState<
    Map<string, TaxonomyLocation>
  >(new Map());

  useEffect(() => {
    let alive = true;
    void Promise.all([
      fetchTaxonomyCategories(),
      fetchTaxonomyLocations({ kind: "city" }),
    ])
      .then(([cats, cities]) => {
        if (!alive) return;
        setTaxonomyCategories(new Map(cats.map((c) => [c.slug, c])));
        setTaxonomyCities(new Map(cities.map((c) => [c.slug, c])));
      })
      .catch(() => {
        if (!alive) return;
        setTaxonomyCategories(new Map());
        setTaxonomyCities(new Map());
      });
    return () => {
      alive = false;
    };
  }, []);

  const collectionCounts = useMemo(() => {
    const weekendCount = filterPublicEvents(events, { weekend: true }).length;
    const freeCount = filterPublicEvents(events, { paid: "free" }).length;
    const vipCount = events.filter((e) =>
      (e.ticket_types ?? []).some((t) =>
        ["vip", "vvip"].includes(String(t.type || "").toLowerCase()),
      ),
    ).length;
    return { weekendCount, freeCount, vipCount, total: events.length };
  }, [events]);

  const categoryCounts = useMemo(() => {
    const map = new Map<string, number>();
    for (const event of events) {
      const slug = event.category?.slug;
      if (!slug) continue;
      map.set(slug, (map.get(slug) ?? 0) + 1);
    }
    return map;
  }, [events]);

  const cityCounts = useMemo(() => {
    const map = new Map<string, number>();
    for (const event of events) {
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

  const cities = useMemo(() => {
    const names = new Set(
      events.map((e) => e.city).filter((c): c is string => Boolean(c)),
    );
    return [...names].sort((a, b) => {
      const ca = cityCounts.get(citySlugFromName(a)) ?? 0;
      const cb = cityCounts.get(citySlugFromName(b)) ?? 0;
      if (cb !== ca) return cb - ca;
      return a.localeCompare(b);
    });
  }, [events, cityCounts]);

  const browseCategoryItems = categoriesByAvailability.map((c) => {
    const story = categoryStory(c.slug, c.name, c.description);
    const visuals = categoryBrowseVisuals(
      c.slug,
      c.name,
      taxonomyCategories.get(c.slug),
    );
    return {
      name: c.name,
      slug: c.slug,
      href: activeCitySlug
        ? `/events/city/${activeCitySlug}/${c.slug}`
        : `/events/c/${c.slug}`,
      hint: story.hint,
      description: story.story,
      count: categoryCounts.get(c.slug),
      imageUrl: visuals.imageUrl,
      imageAlt: visuals.imageAlt,
      focalX: visuals.focalX,
      focalY: visuals.focalY,
    };
  });

  const browseCityItems = cities.slice(0, 12).map((name) => {
    const slug = citySlugFromName(name);
    const story = cityStory(slug, name);
    const visuals = cityBrowseVisuals(slug, name, taxonomyCities.get(slug));
    return {
      name,
      slug,
      href: `/events/city/${slug}`,
      hint: story.hint,
      description: story.story,
      count: cityCounts.get(slug),
      imageUrl: visuals.imageUrl,
      imageAlt: visuals.imageAlt,
      focalX: visuals.focalX,
      focalY: visuals.focalY,
    };
  });

  const adjacentLinks = useMemo(() => {
    const links: {
      label: string;
      href: string;
      hint?: string;
      eyebrow?: string;
      count?: number;
    }[] = [];
    for (const cat of categoriesByAvailability.slice(0, 4)) {
      links.push({
        eyebrow: "Category",
        label: cat.name,
        href: activeCitySlug
          ? `/events/city/${activeCitySlug}/${cat.slug}`
          : `/events/c/${cat.slug}`,
        hint: categoryStory(cat.slug, cat.name).hint,
        count: categoryCounts.get(cat.slug),
      });
    }
    if (!activeCitySlug) {
      const topCity = cities[0];
      if (topCity) {
        const slug = citySlugFromName(topCity);
        links.push({
          eyebrow: "City",
          label: topCity,
          href: `/events/city/${slug}`,
          hint: cityStory(slug, topCity).hint,
          count: cityCounts.get(slug),
        });
      }
    }
    links.push({
      eyebrow: "Collection",
      label: "Free events",
      href: "/events/free",
      hint: "Zero-ticket and free RSVP nights.",
      count: collectionCounts.freeCount,
    });
    links.push({
      eyebrow: "Hosts",
      label: "Meet verified hosts",
      href: "/hosts",
      hint: "Legacy Pages with reputation that compounds.",
    });
    return links;
  }, [
    categoriesByAvailability,
    activeCitySlug,
    cities,
    categoryCounts,
    cityCounts,
    collectionCounts.freeCount,
  ]);

  const collections = [
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
      hint: "City hubs and geo-friendly discovery paths.",
      cta: "View collection",
      curator: "Pàdéyá",
      coverTone: "light" as const,
    },
  ];

  if (!events.length && !categories.length) return null;

  return (
    <div className="mt-4 border-t border-border">
      <DiscoveryCollectionsSection
        title="Browse by scene"
        description="Weekend, free, VIP, and nearby — keep exploring without starting over."
        collections={collections}
      />

      {browseCategoryItems.length > 0 ? (
        <DiscoveryBrowseSection
          title="Browse by category"
          description="Music, comedy, tech, gospel, campus, and more — each with a dedicated hub on Pàdéyá."
          mode="category"
          items={browseCategoryItems}
          maxVisible={8}
          viewAllLabel="View all categories"
        />
      ) : null}

      {!activeCitySlug && browseCityItems.length > 0 ? (
        <DiscoveryBrowseSection
          title="Browse by city"
          description="Open a city hub to see what’s on near you."
          mode="city"
          items={browseCityItems}
          maxVisible={8}
          viewAllLabel="View all cities"
        />
      ) : null}

      <section
        aria-label="Browse by format"
        className="border-b border-border bg-card py-10 sm:py-12"
      >
        <Container className="space-y-5">
          <div className="max-w-2xl space-y-1.5">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
              Filters
            </p>
            <h2 className="text-xl font-extrabold tracking-tight text-foreground sm:text-2xl">
              More ways to narrow the list
            </h2>
            <p className="text-sm leading-relaxed text-muted-foreground sm:text-base">
              Format, timing, and map views — use these when you know how you want to experience
              the night.
            </p>
          </div>
          <ul className="flex flex-wrap gap-2">
            {FORMAT_LINKS.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  prefetch={false}
                  className="inline-flex min-h-10 items-center rounded-full border border-border bg-muted/50 px-4 text-sm font-semibold text-foreground transition hover:border-accent hover:bg-accent/10"
                  title={item.hint}
                >
                  {item.label}
                </Link>
              </li>
            ))}
            <li>
              <Link
                href="/events/location"
                prefetch={false}
                className="inline-flex min-h-10 items-center rounded-full border border-border bg-muted/50 px-4 text-sm font-semibold text-foreground transition hover:border-accent hover:bg-accent/10"
              >
                By location
              </Link>
            </li>
          </ul>
        </Container>
      </section>

      <DiscoveryAdjacentSection links={adjacentLinks} />
    </div>
  );
}
