import { API_TIMEOUT_MS, withTimeoutRace } from "@/lib/api-timeouts";
import { isUpcomingEvent } from "@/lib/discovery/event-filters";
import { resolvePadeyaPicks } from "@/lib/discovery/padeya-picks";
import { diversifyHomepageEvents } from "@/lib/home/diversify-events";
import {
  fetchPadeyaPicksServer,
  fetchPublicEventsServer,
} from "@/lib/events/public-server";
import { DEFAULT_DISCOVERY_CITY } from "@/lib/discovery/default-market";
import type { EventItem } from "@/lib/types/events";

export type HomepagePublicData = {
  picks: EventItem[];
  placementEventIds: string[];
  /** Featured / diversified — default nearby section before geo. */
  featured: EventItem[];
  /** Soonest pool for weekend / free / VIP rails. */
  railPool: EventItem[];
  /** Default market city events (admin/env fallback). */
  defaultCityEvents: EventItem[];
  defaultCityLabel: string;
};

function emptyHomepageData(): HomepagePublicData {
  return {
    picks: [],
    placementEventIds: [],
    featured: [],
    railPool: [],
    defaultCityEvents: [],
    defaultCityLabel: DEFAULT_DISCOVERY_CITY.label,
  };
}

/**
 * Cached public homepage payload. No geolocation — nearby is client-enhanced.
 *
 * Bounded overall budget: if the API is slow/unavailable, render empty rails
 * (hero + CTAs still paint). Runtime ISR / revalidate can fill content later.
 */
export async function loadHomepagePublicData(): Promise<HomepagePublicData> {
  return withTimeoutRace(
    loadHomepagePublicDataInner(),
    API_TIMEOUT_MS.public + 2_000,
    emptyHomepageData,
  );
}

async function loadHomepagePublicDataInner(): Promise<HomepagePublicData> {
  const defaultCity = DEFAULT_DISCOVERY_CITY;
  const [adminPicks, featuredPool, soonestPool, cityPool] = await Promise.all([
    fetchPadeyaPicksServer("homepage"),
    fetchPublicEventsServer({ sort: "featured" }),
    fetchPublicEventsServer({ sort: "soonest" }),
    defaultCity.slug
      ? fetchPublicEventsServer({
          city: defaultCity.slug,
          location_kind: "city",
          location_slug: defaultCity.slug,
          sort: "featured",
        })
      : Promise.resolve([] as EventItem[]),
  ]);

  const upcomingFeatured = featuredPool.filter(isUpcomingEvent);
  const upcomingSoonest = soonestPool.filter(isUpcomingEvent);
  const upcomingCity = cityPool.filter(isUpcomingEvent);

  return {
    picks: resolvePadeyaPicks(adminPicks, upcomingFeatured, 2),
    placementEventIds: adminPicks.map((e) => e.id),
    featured: diversifyHomepageEvents(upcomingFeatured, 8),
    railPool: upcomingSoonest,
    defaultCityEvents: diversifyHomepageEvents(
      upcomingCity.length ? upcomingCity : upcomingFeatured,
      8,
    ),
    defaultCityLabel: defaultCity.label,
  };
}
