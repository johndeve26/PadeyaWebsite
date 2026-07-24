import { filterPublicEvents } from "@/lib/discovery/event-filters";
import type { EventItem } from "@/lib/types/events";

export const PADEYA_PICKS_TITLE = "Pàdéyá Picks";

/**
 * Prefer admin placement picks; fill remaining slots from featured/trending fallback.
 * Returns 0–2 events — callers should hide the section when empty.
 */
export function resolvePadeyaPicks(
  adminPicks: EventItem[],
  fallbackPool: EventItem[] = [],
  limit = 2,
): EventItem[] {
  const picked: EventItem[] = [];
  const seen = new Set<string>();

  for (const event of adminPicks) {
    if (!event?.id || seen.has(event.id)) continue;
    seen.add(event.id);
    picked.push(event);
    if (picked.length >= limit) return picked;
  }

  const fallback = filterPublicEvents(fallbackPool, { sort: "trending" });
  for (const event of fallback) {
    if (!event?.id || seen.has(event.id)) continue;
    seen.add(event.id);
    picked.push(event);
    if (picked.length >= limit) break;
  }

  return picked;
}
