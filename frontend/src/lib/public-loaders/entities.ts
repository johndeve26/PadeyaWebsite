/**
 * Request-scoped public entity loaders (React `cache`).
 *
 * Dedupes generateMetadata + page within one RSC render graph.
 * Not a cross-user persistent store — never put private/auth data here.
 */

import { cache } from "react";

import { PUBLIC_REVALIDATE } from "@/lib/cache/public-revalidate";
import { fetchPublicJson } from "@/lib/seo/public-fetch";
import type { EventItem } from "@/lib/types/events";
import type { LegacyPage } from "@/lib/types/legacy";
import type { MarketplaceProduct } from "@/lib/types/merch";
import type { FanPassportPublicPage } from "@/lib/types/passport";
import type { SponsorPublicProfile } from "@/lib/sponsor-profiles-api";

/** Test/dev counter — proves metadata+page share one loader invocation. */
export const publicLoaderCallCounts = {
  event: 0,
  legacy: 0,
  sponsor: 0,
  fan: 0,
  merch: 0,
};

export function resetPublicLoaderCallCounts(): void {
  publicLoaderCallCounts.event = 0;
  publicLoaderCallCounts.legacy = 0;
  publicLoaderCallCounts.sponsor = 0;
  publicLoaderCallCounts.fan = 0;
  publicLoaderCallCounts.merch = 0;
}

export const getPublicEventBySlug = cache(
  async (slug: string): Promise<EventItem | null> => {
    publicLoaderCallCounts.event += 1;
    const { data, status } = await fetchPublicJson<EventItem>(
      `/events/${encodeURIComponent(slug)}`,
      { revalidate: PUBLIC_REVALIDATE.eventDetail },
    );
    if (status === 404 || !data) return null;
    return data;
  },
);

export const getPublicLegacyByUsername = cache(
  async (username: string): Promise<LegacyPage | null> => {
    publicLoaderCallCounts.legacy += 1;
    const { data, status } = await fetchPublicJson<LegacyPage>(
      `/u/${encodeURIComponent(username)}/legacy`,
      { revalidate: PUBLIC_REVALIDATE.eventDetail },
    );
    if (status === 404 || !data) return null;
    if (data.status && data.status !== "active") return null;
    return data;
  },
);

export const getPublicSponsorBySlug = cache(
  async (slug: string): Promise<SponsorPublicProfile | null> => {
    publicLoaderCallCounts.sponsor += 1;
    const { data, status } = await fetchPublicJson<SponsorPublicProfile>(
      `/sponsors/public/${encodeURIComponent(slug)}`,
      { revalidate: PUBLIC_REVALIDATE.eventDetail },
    );
    if (status === 404 || !data) return null;
    return data;
  },
);

/**
 * Fan Passport public loader.
 *
 * PRIVATE → API 404.
 * PUBLIC / UNLISTED → fetched with **no-store** (HTML route is force-dynamic).
 * React `cache()` still dedupes metadata + page within one RSC request.
 * Directory ISR is purged separately via `/api/revalidate/fan`.
 */
export const getPublicFanPassport = cache(
  async (username: string): Promise<FanPassportPublicPage | null> => {
    publicLoaderCallCounts.fan += 1;
    const { data, status } = await fetchPublicJson<FanPassportPublicPage>(
      `/f/${encodeURIComponent(username)}`,
      { revalidate: false },
    );
    if (status === 404 || !data) return null;
    return data;
  },
);

export const getPublicMerchBySlug = cache(
  async (
    slug: string,
    hostSlug?: string,
  ): Promise<MarketplaceProduct | null> => {
    publicLoaderCallCounts.merch += 1;
    const params = new URLSearchParams();
    if (hostSlug) params.set("h", hostSlug);
    const suffix = params.size ? `?${params.toString()}` : "";
    const { data, status } = await fetchPublicJson<MarketplaceProduct>(
      `/merch/${encodeURIComponent(slug)}${suffix}`,
      { revalidate: 60 },
    );
    if (status === 404 || !data) return null;
    return data;
  },
);
