import { DiscoveryHubClient } from "@/components/discovery/DiscoveryHubClient";
import { HubJsonLd, hubPageMetadata } from "@/lib/seo/hub-page";

export const metadata = hubPageMetadata({
  title: "Events by Location",
  description:
    "Browse Pàdéyá events by country, state, city, and neighborhood.",
  path: "/events/location",
});

export default function EventsByLocationIndexPage() {
  const crumbs = [
    { label: "Home", href: "/" },
    { label: "Events", href: "/events" },
    { label: "Locations" },
  ];

  return (
    <>
      <HubJsonLd
        name="Events by Location"
        description="Browse Pàdéyá events by country, state, city, and neighborhood."
        path="/events/location"
        crumbs={crumbs}
      />
      <DiscoveryHubClient kind="location_index" />
    </>
  );
}
