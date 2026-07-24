"use client";

import { useMemo } from "react";

import { EventRecommendationsSection } from "@/components/events/EventRecommendationsSection";
import { citySlugFromName } from "@/lib/discovery/slugify";
import type { EventItem } from "@/lib/types/events";

/** Personalized “More events you may like” on public event detail (signed-in only). */
export function EventDetailRecommendationsRail({ event }: { event: EventItem }) {
  const citySlug = event.city ? citySlugFromName(event.city) : undefined;

  const detailContext = useMemo(
    () => ({
      excludeEventId: event.id,
      contextEventId: event.id,
      category: event.category?.slug,
      city: citySlug,
      area: event.area ?? undefined,
      hostId: event.host_id,
    }),
    [event.id, event.category?.slug, citySlug, event.area, event.host_id],
  );

  return (
    <EventRecommendationsSection
      variant="detail"
      limit={6}
      surface="event_detail_recommended"
      title="More events you may like"
      seeAllHref="/events?sort=recommended"
      detailContext={detailContext}
    />
  );
}
