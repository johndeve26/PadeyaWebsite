"use client";

import Link from "next/link";

import { TaxonomyBrowseCard } from "@/components/discovery/TaxonomyBrowseCard";
import { RelatedDiscoveryEventCard } from "@/components/events/related/RelatedDiscoveryEventCard";
import {
  RelatedCategoryCard,
  RelatedCityCard,
  RelatedHostCard,
  RelatedHostsHubCard,
  RelatedMemoriesCard,
  RelatedVaultCard,
} from "@/components/events/related/RelatedDestinationCards";
import {
  discoveryPlaceLabel,
  rankRelatedEvents,
} from "@/lib/discovery/related-discovery";
import { browseImageForHref } from "@/lib/discovery/browse-images";
import { citySlugFromName } from "@/lib/discovery/slugify";
import type { EventItem } from "@/lib/types/events";

/**
 * Premium related discovery block for the public event detail page.
 * Groups events, host destinations, and scene hubs with clear hierarchy.
 */
export function RelatedDiscoverySection({
  event,
  allEvents,
}: {
  event: EventItem;
  allEvents: EventItem[];
}) {
  const related = rankRelatedEvents(event, allEvents, 6);
  const place = discoveryPlaceLabel(event);
  const citySlug = event.city ? citySlugFromName(event.city) : null;
  const hostSlug = event.host_slug;
  const hostName = event.host_display_name || "This host";
  const hostHref = hostSlug ? `/@${hostSlug}` : "/hosts";
  const vaultHref = hostSlug ? `/@${hostSlug}/vault` : null;
  const cityHref = citySlug ? `/events/city/${citySlug}` : "/events";
  const categoryHref = event.category
    ? citySlug
      ? `/events/city/${citySlug}/${event.category.slug}`
      : `/events/c/${event.category.slug}`
    : null;
  const hostsHref = "/hosts";

  const heading =
    place === "this scene"
      ? "Keep exploring this scene"
      : `Keep exploring ${place}`;

  const hasAnything =
    related.length > 0 || Boolean(hostSlug) || Boolean(citySlug) || Boolean(event.category);

  if (!hasAnything) {
    return (
      <section className="rounded-[var(--radius-xl)] border border-border bg-card p-6 sm:p-8 dark:bg-surface-elevated">
        <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-accent">
          Keep exploring
        </p>
        <h2 className="mt-2 text-2xl font-extrabold tracking-tight text-foreground">
          Continue exploring on Pàdéyá
        </h2>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
          Browse verified events and hosts across the marketplace.
        </p>
        <Link
          href="/events"
          className="mt-5 inline-flex text-sm font-extrabold uppercase tracking-wide text-foreground underline decoration-accent underline-offset-4"
        >
          All events
        </Link>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-[var(--radius-xl)] border border-border bg-[linear-gradient(165deg,var(--card)_0%,var(--surface)_55%,var(--muted)_100%)] shadow-[var(--shadow-soft)]">
      <div className="border-b border-border bg-surface-elevated/80 px-5 py-6 sm:px-8 sm:py-8">
        <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-accent">
          Keep exploring
        </p>
        <h2 className="mt-2 text-balance text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
          {heading}
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          More events, host pages, and discovery hubs connected to this event.
        </p>
      </div>

      <div className="space-y-10 px-5 py-7 sm:px-8 sm:py-9">
        {/* 1 — Related events */}
        {related.length > 0 ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-end justify-between gap-2">
              <div>
                <p className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-muted-foreground">
                  Related events
                </p>
                <h3 className="text-xl font-extrabold tracking-tight text-foreground">
                  More events you might like
                </h3>
              </div>
              {citySlug && event.city ? (
                <Link
                  href={cityHref}
                  className="text-xs font-extrabold uppercase tracking-wide text-foreground underline decoration-accent underline-offset-4"
                >
                  See all in {event.city}
                </Link>
              ) : (
                <Link
                  href="/events"
                  className="text-xs font-extrabold uppercase tracking-wide text-foreground underline decoration-accent underline-offset-4"
                >
                  Browse events
                </Link>
              )}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              {related.map((item) => (
                <RelatedDiscoveryEventCard key={item.event.id} item={item} />
              ))}
            </div>
          </div>
        ) : null}

        {/* 2 — Host discovery */}
        <div className="space-y-4">
          <div>
            <p className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-muted-foreground">
              Host
            </p>
            <h3 className="text-xl font-extrabold tracking-tight text-foreground">
              Explore the host
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {vaultHref
                ? `Legacy trust and exclusive Vault drops from ${hostName}.`
                : `Legacy trust and past nights from ${hostName}.`}
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <RelatedHostCard
              sourceEvent={event}
              hostName={hostName}
              href={hostHref}
            />
            {vaultHref ? (
              <RelatedVaultCard
                sourceEvent={event}
                hostName={hostName}
                href={vaultHref}
              />
            ) : (
              <RelatedMemoriesCard
                sourceEvent={event}
                hostName={hostName}
                href={hostHref}
              />
            )}
          </div>
        </div>

        {/* 3 — Scene hubs */}
        <div className="space-y-4">
          <div>
            <p className="text-[10px] font-extrabold uppercase tracking-[0.14em] text-muted-foreground">
              Discovery hubs
            </p>
            <h3 className="text-xl font-extrabold tracking-tight text-foreground">
              Browse by scene
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Jump into city and category hubs to keep discovering on Pàdéyá.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {event.city && citySlug ? (
              <RelatedCityCard city={event.city} href={cityHref} />
            ) : (
              <TaxonomyBrowseCard
                href="/events"
                eyebrow="Marketplace"
                title="Explore events"
                meta="Browse verified events, hosts, and trending categories on Pàdéyá."
                image={browseImageForHref("/events")}
                className="h-full min-h-[168px]"
              />
            )}
            {event.category && categoryHref && event.city ? (
              <RelatedCategoryCard
                categoryName={event.category.name}
                city={event.city}
                href={categoryHref}
              />
            ) : null}
            {event.category ? (
              <RelatedCategoryCard
                categoryName={event.category.name}
                href={`/events/c/${event.category.slug}`}
              />
            ) : null}
            <RelatedHostsHubCard city={event.city} href={hostsHref} />
          </div>
        </div>
      </div>
    </section>
  );
}
