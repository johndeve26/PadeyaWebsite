/** Pure helpers for related rails (Wave 0 live queries). */

import type { EventItem } from "@/lib/types/events";

export type RelatedEventGroups = {
  byHost: EventItem[];
  byCategory: EventItem[];
  byCity: EventItem[];
  byVibe: EventItem[];
};

export function groupRelatedEvents(
  event: EventItem,
  allEvents: EventItem[],
  limit = 4,
): RelatedEventGroups {
  const others = allEvents.filter((r) => r.id !== event.id);
  const byHost = others.filter((r) => r.host_id === event.host_id).slice(0, limit);
  const byCategory = others
    .filter(
      (r) =>
        event.category_id &&
        r.category_id === event.category_id &&
        r.host_id !== event.host_id,
    )
    .slice(0, limit);
  const byCity = others
    .filter(
      (r) =>
        event.city &&
        r.city === event.city &&
        r.host_id !== event.host_id &&
        r.category_id !== event.category_id,
    )
    .slice(0, limit);
  const byVibe = event.vibe
    ? others
        .filter(
          (r) =>
            r.vibe &&
            r.vibe.toLowerCase() === event.vibe!.toLowerCase(),
        )
        .slice(0, limit)
    : [];

  return { byHost, byCategory, byCity, byVibe };
}
