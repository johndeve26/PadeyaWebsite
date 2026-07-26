import type { Metadata } from "next";

import { ReferralLandingTracker } from "@/components/ambassadors/ReferralLandingTracker";
import { EventsMarketplaceClient } from "@/components/events/marketplace";
import {
  fetchCategoriesServer,
  fetchPublicEventsServer,
} from "@/lib/events/public-server";
import { buildHomeEvents } from "@/lib/marketplace-breadcrumbs";
import { EVENTS_FACET_CANONICAL_PATH } from "@/lib/seo/facet-policy";
import { HubJsonLd, hubPageMetadata } from "@/lib/seo/hub-page";

/**
 * ISR shell for /events.
 *
 * Do **not** read `searchParams` here — that forces `private, no-store` and
 * permanent Vercel MISS. Faceted URLs stay client-driven; middleware applies
 * noindex for facet query keys (SEO Phase 1B). Tracking-only params ignored.
 */
export const revalidate = 90;

export const metadata: Metadata = hubPageMetadata({
  title: "Events",
  description:
    "Discover events on Pàdéyá — search by city, category, date, and vibe. Verified tickets, QR check-in, and trusted hosts.",
  path: EVENTS_FACET_CANONICAL_PATH,
});

/**
 * SSR default public list. Near-me / facet filters enhance client-side after
 * hydration (never SSR exact GPS). See docs/PERFORMANCE_CACHING_AUDIT.md.
 */
export default async function EventsIndexPage() {
  const [events, categories] = await Promise.all([
    fetchPublicEventsServer(),
    fetchCategoriesServer(),
  ]);

  const crumbs = buildHomeEvents();
  return (
    <>
      <ReferralLandingTracker />
      <HubJsonLd
        name="Events on Pàdéyá"
        description="Find events on Pàdéyá — search by city, category, date, and vibe. Verified tickets with QR check-in."
        path="/events"
        crumbs={crumbs}
      />
      <EventsMarketplaceClient
        initialEvents={events}
        initialCategories={categories}
      />
    </>
  );
}
