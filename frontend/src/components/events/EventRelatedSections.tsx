"use client";

import { RelatedDiscoverySection } from "@/components/events/RelatedDiscoverySection";
import type { EventItem } from "@/lib/types/events";

/** Public event discovery block under the detail page. */
export function EventRelatedSections({
  event,
  allEvents,
}: {
  event: EventItem;
  allEvents: EventItem[];
}) {
  return <RelatedDiscoverySection event={event} allEvents={allEvents} />;
}
