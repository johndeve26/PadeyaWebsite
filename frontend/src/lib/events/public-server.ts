/**
 * Server-only public events fetches (ISR-tagged).
 * Checkout must never treat these as final availability truth.
 */

import { PUBLIC_REVALIDATE } from "@/lib/cache/public-revalidate";
import { fetchPublicJson } from "@/lib/cache/public-api";
import type { EventCategory, EventItem } from "@/lib/types/events";

export type PublicEventsServerFilters = {
  q?: string;
  category?: string;
  city?: string;
  location_kind?: string;
  location_slug?: string;
  weekend?: boolean;
  paid?: string;
  sort?: string;
};

function eventsQs(filters?: PublicEventsServerFilters): string {
  const params = new URLSearchParams();
  if (!filters) return "";
  if (filters.q) params.set("q", filters.q);
  if (filters.category) params.set("category", filters.category);
  if (filters.city) params.set("city", filters.city);
  if (filters.location_kind) params.set("location_kind", filters.location_kind);
  if (filters.location_slug) params.set("location_slug", filters.location_slug);
  if (filters.weekend) params.set("weekend", "true");
  if (filters.paid) params.set("paid", filters.paid);
  if (filters.sort) params.set("sort", filters.sort);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

const LIST_FETCH = {
  next: {
    revalidate: PUBLIC_REVALIDATE.eventsList,
    tags: ["events", "events-list"],
  },
};

const FEATURED_FETCH = {
  next: {
    revalidate: PUBLIC_REVALIDATE.featured,
    tags: ["events", "events-picks", "homepage"],
  },
};

/** Public marketplace list — filter params included in URL + Redis key. */
export async function fetchPublicEventsServer(
  filters?: PublicEventsServerFilters,
): Promise<EventItem[]> {
  const rows = await fetchPublicJson<EventItem[]>(
    `/events${eventsQs(filters)}`,
    LIST_FETCH,
  );
  return rows ?? [];
}

export async function fetchCategoriesServer(): Promise<EventCategory[]> {
  const rows = await fetchPublicJson<EventCategory[]>(
    "/events/categories",
    {
      next: {
        revalidate: PUBLIC_REVALIDATE.taxonomy,
        tags: ["events", "events-categories"],
      },
    },
  );
  return rows ?? [];
}

export async function fetchPadeyaPicksServer(
  context: string = "homepage",
): Promise<EventItem[]> {
  const qs = new URLSearchParams({ context });
  const rows = await fetchPublicJson<EventItem[]>(
    `/events/padeya-picks?${qs}`,
    FEATURED_FETCH,
  );
  return rows ?? [];
}
