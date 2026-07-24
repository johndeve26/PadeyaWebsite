/** Ranked related events for the public event detail discovery section (FE-only). */

import { isUpcomingEvent } from "@/lib/discovery/event-filters";
import type { EventItem } from "@/lib/types/events";

export type RelatedRelationship =
  | "same_host"
  | "same_city"
  | "same_category"
  | "similar_vibe";

export type RankedRelatedEvent = {
  event: EventItem;
  relationship: RelatedRelationship;
  badge: string;
};

const HIDDEN_STATUSES = new Set([
  "draft",
  "pending_review",
  "rejected",
  "cancelled",
  "archived",
]);

const HIDDEN_VISIBILITY = new Set(["unlisted", "password_protected"]);

export function isPublicDiscoverableEvent(event: EventItem): boolean {
  if (HIDDEN_STATUSES.has(event.status)) return false;
  const visibility = event.visibility || "listed";
  if (HIDDEN_VISIBILITY.has(String(visibility))) return false;
  return true;
}

function badgeFor(rel: RelatedRelationship): string {
  switch (rel) {
    case "same_host":
      return "Same host";
    case "same_city":
      return "Same city";
    case "same_category":
      return "Same category";
    case "similar_vibe":
      return "Similar vibe";
  }
}

/**
 * Prefer host → city → category → vibe. Dedupes by event id.
 * Does not include the source event.
 */
export function rankRelatedEvents(
  source: EventItem,
  allEvents: EventItem[],
  limit = 6,
): RankedRelatedEvent[] {
  const pool = allEvents.filter(
    (e) =>
      e.id !== source.id &&
      isPublicDiscoverableEvent(e) &&
      isUpcomingEvent(e),
  );
  const ranked: RankedRelatedEvent[] = [];
  const seen = new Set<string>();

  function push(items: EventItem[], relationship: RelatedRelationship) {
    for (const event of items) {
      if (seen.has(event.id) || ranked.length >= limit) continue;
      seen.add(event.id);
      ranked.push({
        event,
        relationship,
        badge: badgeFor(relationship),
      });
    }
  }

  push(
    pool.filter((e) => e.host_id === source.host_id),
    "same_host",
  );
  push(
    pool.filter(
      (e) =>
        Boolean(source.city) &&
        e.city === source.city &&
        e.host_id !== source.host_id,
    ),
    "same_city",
  );
  push(
    pool.filter(
      (e) =>
        Boolean(source.category_id) &&
        e.category_id === source.category_id &&
        e.host_id !== source.host_id,
    ),
    "same_category",
  );
  if (source.vibe) {
    const vibe = source.vibe.toLowerCase();
    push(
      pool.filter(
        (e) => e.vibe && e.vibe.toLowerCase() === vibe && e.host_id !== source.host_id,
      ),
      "similar_vibe",
    );
  }

  return ranked;
}

export function discoveryPlaceLabel(event: EventItem): string {
  return (
    event.city ||
    (event.location?.kind === "city" || event.location?.kind === "area"
      ? event.location.name
      : null) ||
    "this scene"
  );
}

export function lowestTicketPrice(event: EventItem): number | null {
  const prices = (event.ticket_types ?? [])
    .filter((t) => t.visibility !== "hidden" && t.status !== "inactive")
    .map((t) => Number(t.price))
    .filter((n) => Number.isFinite(n));
  if (!prices.length) return null;
  return Math.min(...prices);
}
