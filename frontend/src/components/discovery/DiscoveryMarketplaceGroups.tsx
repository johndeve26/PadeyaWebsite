"use client";

import Link from "next/link";

import { HomeCardCarousel } from "@/components/home/HomeCardCarousel";
import { TaxonomyEventCard } from "@/components/taxonomy/TaxonomyEventCard";
import { Container } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  EVENT_LISTING_CAROUSEL_SLIDE,
  EVENT_LISTING_GRID_DISCOVERY,
} from "@/lib/discovery/event-listing-layout";
import type { MarketplaceGroup } from "@/lib/discovery/marketplace-groups";

/**
 * Discovery groupings — snap carousel on mobile, grid from sm.
 */
export function DiscoveryMarketplaceGroups({
  groups,
  className = "",
}: {
  groups: MarketplaceGroup[];
  className?: string;
}) {
  if (!groups.length) return null;

  return (
    <section
      aria-label="Discovery collections"
      className={cn(
        "border-b border-border bg-card py-12 sm:py-14",
        className,
      )}
    >
      <Container className="space-y-10">
        {groups.map((group, groupIndex) => (
          <div
            key={group.id}
            className="padeya-section-enter space-y-4"
            style={{ animationDelay: `${Math.min(groupIndex, 4) * 60}ms` }}
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div className="max-w-2xl space-y-1.5">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
                  Discover
                </p>
                <h2 className="text-xl font-extrabold tracking-tight text-foreground sm:text-2xl">
                  {group.title}
                </h2>
                <p className="text-sm leading-relaxed text-muted-foreground sm:text-base">
                  {group.description}
                </p>
              </div>
              <Link
                href={
                  group.id === "weekend"
                    ? "/events/this-weekend"
                    : group.id === "free"
                      ? "/events/free"
                      : group.id === "vip"
                        ? "/events/vip"
                        : "#results"
                }
                className="text-sm font-bold text-foreground underline-offset-4 hover:underline"
              >
                View all →
              </Link>
            </div>
            <HomeCardCarousel
              label={group.title}
              until="sm"
              desktopGridClassName={EVENT_LISTING_GRID_DISCOVERY}
              slideClassName={EVENT_LISTING_CAROUSEL_SLIDE}
            >
              {group.events.map((event) => (
                <div key={event.id} className="min-w-0 h-full">
                  <TaxonomyEventCard event={event} compact />
                </div>
              ))}
            </HomeCardCarousel>
          </div>
        ))}
      </Container>
    </section>
  );
}
