import {
  isFreeEvent,
  isUpcomingEvent,
  isVipEvent,
  minTicketPrice,
  weekendWindow,
} from "@/lib/discovery/event-filters";
import type { EventItem } from "@/lib/types/events";

export type MarketplaceGroup = {
  id: string;
  title: string;
  description: string;
  events: EventItem[];
};

function remainingTickets(event: EventItem): number | null {
  const types = event.ticket_types ?? [];
  if (!types.length) return null;
  let remaining = 0;
  let hasQty = false;
  for (const t of types) {
    if (typeof t.quantity !== "number") continue;
    hasQty = true;
    const sold = t.quantity_sold ?? 0;
    const reserved = t.quantity_reserved ?? 0;
    remaining += Math.max(0, t.quantity - sold - reserved);
  }
  return hasQty ? remaining : null;
}

function isSellingFast(event: EventItem): boolean {
  const remaining = remainingTickets(event);
  if (remaining == null) return false;
  if (remaining <= 0) return false;
  return remaining < 40;
}

function isThisWeekend(event: EventItem, now = new Date()): boolean {
  const { start, end } = weekendWindow(now);
  const t = Date.parse(event.start_datetime);
  return Number.isFinite(t) && t >= start.getTime() && t <= end.getTime();
}

function publishedRecently(event: EventItem, now = new Date()): boolean {
  const raw = event.published_at || event.created_at;
  const t = Date.parse(raw);
  if (!Number.isFinite(t)) return false;
  return now.getTime() - t < 1000 * 60 * 60 * 24 * 14;
}

/**
 * Client-side discovery rails from the loaded events list.
 * Groups with zero items are omitted by the caller.
 */
export function buildMarketplaceGroups(
  events: EventItem[],
  opts?: { excludeIds?: ReadonlySet<string>; limit?: number },
): MarketplaceGroup[] {
  const exclude = opts?.excludeIds ?? new Set<string>();
  const limit = opts?.limit ?? 8;
  const pool = events.filter((e) => !exclude.has(e.id) && isUpcomingEvent(e));
  if (!pool.length) return [];

  const definitions: {
    id: string;
    title: string;
    description: string;
    pick: (list: EventItem[]) => EventItem[];
  }[] = [
    {
      id: "weekend",
      title: "Trending this weekend",
      description: "Friday through Sunday — nights already on the calendar.",
      pick: (list) =>
        list
          .filter((e) => isThisWeekend(e))
          .sort(
            (a, b) =>
              Number(b.featured) - Number(a.featured) ||
              Date.parse(a.start_datetime) - Date.parse(b.start_datetime),
          ),
    },
    {
      id: "selling-fast",
      title: "Selling fast",
      description: "Limited remaining tickets — grab a spot while you can.",
      pick: (list) =>
        list
          .filter(isSellingFast)
          .sort((a, b) => {
            const ar = remainingTickets(a) ?? 999;
            const br = remainingTickets(b) ?? 999;
            return ar - br;
          }),
    },
    {
      id: "recent",
      title: "Recently added",
      description: "Fresh listings hosts just put on Pàdéyá.",
      pick: (list) =>
        list
          .filter((e) => publishedRecently(e))
          .sort(
            (a, b) =>
              Date.parse(b.published_at || b.created_at) -
              Date.parse(a.published_at || a.created_at),
          ),
    },
    {
      id: "free",
      title: "Free events",
      description: "Zero-ticket and free RSVP experiences worth showing up for.",
      pick: (list) =>
        list
          .filter(isFreeEvent)
          .sort(
            (a, b) =>
              Date.parse(a.start_datetime) - Date.parse(b.start_datetime),
          ),
    },
    {
      id: "padeya-picks",
      title: "Pàdéyá Picks",
      description: "Featured experiences selected by Pàdéyá.",
      pick: (list) =>
        list
          .filter((e) => e.featured)
          .sort(
            (a, b) =>
              Date.parse(a.start_datetime) - Date.parse(b.start_datetime),
          ),
    },
    {
      id: "vip",
      title: "VIP nights",
      description: "VIP and VVIP tiers for rooms that go deeper.",
      pick: (list) =>
        list
          .filter(isVipEvent)
          .sort((a, b) => {
            const ap = minTicketPrice(a) ?? 0;
            const bp = minTicketPrice(b) ?? 0;
            return bp - ap;
          }),
    },
  ];

  const used = new Set<string>();
  const groups: MarketplaceGroup[] = [];

  for (const def of definitions) {
    const picked = def
      .pick(pool)
      .filter((e) => !used.has(e.id))
      .slice(0, limit);
    if (!picked.length) continue;
    for (const e of picked) used.add(e.id);
    groups.push({
      id: def.id,
      title: def.title,
      description: def.description,
      events: picked,
    });
  }

  return groups;
}

export function ticketAvailabilityLabel(event: EventItem): string | null {
  const remaining = remainingTickets(event);
  if (remaining == null) return null;
  if (remaining <= 0) return "Sold out";
  if (remaining < 40) return `${remaining} left`;
  return null;
}
