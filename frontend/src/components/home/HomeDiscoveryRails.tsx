"use client";

import Link from "next/link";

import { EventRail } from "@/components/events/discovery/EventRail";
import { Button, Container, EventCard, SkeletonCard } from "@/components/ui";
import { buildMarketplaceGroups } from "@/lib/discovery/marketplace-groups";
import type { EventItem } from "@/lib/types/events";

const RAIL_ORDER = ["weekend"] as const;

const RAIL_META: Record<
  (typeof RAIL_ORDER)[number],
  { title: string; href: string }
> = {
  weekend: { title: "This weekend", href: "/events/this-weekend" },
};

/**
 * Homepage discovery rail — This weekend only.
 * Hydrated from SSR public pool (no client fetch on first paint).
 */
export function HomeDiscoveryRails({
  initialEvents = null,
}: {
  initialEvents?: EventItem[] | null;
} = {}) {
  if (initialEvents === null) {
    return (
      <section className="bg-ink py-10 sm:py-12">
        <Container className="space-y-8">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="space-y-4">
              <div className="h-7 w-40 animate-pulse rounded bg-paper/10" />
              <div className="flex gap-4 overflow-hidden">
                {Array.from({ length: 4 }).map((__, j) => (
                  <div key={j} className="w-[15.5rem] shrink-0">
                    <SkeletonCard />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </Container>
      </section>
    );
  }

  const groups = buildMarketplaceGroups(initialEvents, { limit: 10 }).filter(
    (g) => (RAIL_ORDER as readonly string[]).includes(g.id),
  );

  if (!groups.length) return null;

  return (
    <section className="bg-ink py-10 sm:py-12">
      <Container className="space-y-10 sm:space-y-12">
        {groups.map((group) => {
          const meta = RAIL_META[group.id as (typeof RAIL_ORDER)[number]];
          if (!meta) return null;
          return (
            <EventRail
              key={group.id}
              label={meta.title}
              title={meta.title}
              description={group.description}
              tone="dark"
              action={
                <Link href={meta.href} className="hidden sm:inline-flex">
                  <Button variant="outline-dark" size="sm">
                    View all
                  </Button>
                </Link>
              }
            >
              {group.events.map((event, index) => (
                <EventCard
                  key={event.id}
                  event={event}
                  listContext="homepage_featured"
                  cardPosition={index}
                />
              ))}
            </EventRail>
          );
        })}
      </Container>
    </section>
  );
}
