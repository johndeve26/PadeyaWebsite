"use client";

import Link from "next/link";

import { PadeyaPicksSection } from "@/components/discovery/PadeyaPicksSection";
import {
  Button,
  Container,
  EmptyState,
  SectionHeader,
  SkeletonCard,
} from "@/components/ui";
import type { EventItem } from "@/lib/types/events";

export function HomePadeyaPicks({
  initialEvents = null,
  placementEventIds = [],
}: {
  /** Server-resolved picks — avoids client waterfall on first paint. */
  initialEvents?: EventItem[] | null;
  placementEventIds?: string[];
} = {}) {
  if (initialEvents === null) {
    return (
      <section className="bg-background py-8 sm:py-10">
        <Container className="grid gap-4 sm:grid-cols-2">
          <SkeletonCard />
          <SkeletonCard />
        </Container>
      </section>
    );
  }

  if (!initialEvents.length) {
    return (
      <section className="bg-background py-8 sm:py-10">
        <Container className="space-y-5">
          <SectionHeader
            variant="display"
            eyebrow="Pàdéyá Picks"
            title="Editor’s picks"
            description="Curated nights from the marketplace. Check back as hosts publish."
          />
          <EmptyState
            title="No picks yet"
            description="Explore the full event marketplace while we feature upcoming nights."
            action={
              <Link href="/events">
                <Button variant="secondary">Explore events</Button>
              </Link>
            }
          />
        </Container>
      </section>
    );
  }

  return (
    <PadeyaPicksSection
      events={initialEvents}
      layout="equal"
      analytics={{
        placementContext: "homepage",
        placementEventIds,
      }}
    />
  );
}
