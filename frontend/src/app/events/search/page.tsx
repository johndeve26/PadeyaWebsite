import { ReferralLandingTracker } from "@/components/ambassadors/ReferralLandingTracker";
import { EventsMarketplaceClient } from "@/components/events/marketplace";
import { buildHomeEvents } from "@/lib/marketplace-breadcrumbs";
import { HubJsonLd, hubPageMetadata } from "@/lib/seo/hub-page";

export const metadata = hubPageMetadata({
  title: "Search events",
  description:
    "Search events on Pàdéyá by keyword, city, category, and date filters.",
  path: "/events/search",
});

export default function EventsSearchPage() {
  const crumbs = [
    ...buildHomeEvents(),
    { label: "Search", href: "/events/search" },
  ];
  return (
    <>
      <ReferralLandingTracker />
      <HubJsonLd
        name="Search events on Pàdéyá"
        description="Search events on Pàdéyá by keyword, city, category, and date filters."
        path="/events/search"
        crumbs={crumbs}
      />
      <EventsMarketplaceClient />
    </>
  );
}
