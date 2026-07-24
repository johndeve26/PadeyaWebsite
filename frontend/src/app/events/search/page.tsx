import { ReferralLandingTracker } from "@/components/ambassadors/ReferralLandingTracker";
import { EventsMarketplaceClient } from "@/components/events/marketplace";
import { buildHomeEvents } from "@/lib/marketplace-breadcrumbs";
import { eventsSearchPageMetadataPolicy } from "@/lib/seo/facet-policy";
import { HubJsonLd, hubPageMetadata } from "@/lib/seo/hub-page";

const searchPolicy = eventsSearchPageMetadataPolicy();

const baseMeta = hubPageMetadata({
  title: "Search events",
  description:
    "Search events on Pàdéyá by keyword, city, category, and date filters.",
  path: searchPolicy.path,
  canonicalPath: searchPolicy.canonicalPath,
  noIndex: searchPolicy.noIndex,
});

/**
 * Legacy search surface — never index; follow allowed; canonical → /events.
 * SearchAction targets `/events?q=` (working public search), not this route.
 */
export const metadata = {
  ...baseMeta,
  robots: { index: false, follow: true },
};

export default function EventsSearchPage() {
  const crumbs = [
    ...buildHomeEvents(),
    { label: "Search", href: "/events" },
  ];
  return (
    <>
      <ReferralLandingTracker />
      <HubJsonLd
        name="Search events on Pàdéyá"
        description="Search events on Pàdéyá by keyword, city, category, and date filters."
        path="/events"
        crumbs={crumbs}
      />
      <EventsMarketplaceClient />
    </>
  );
}
