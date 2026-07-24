import { CollectionLandingClient } from "@/components/discovery/CollectionLandingClient";
import { buildDiscoveryTrail } from "@/lib/marketplace-breadcrumbs";
import { HubJsonLd, hubPageMetadata } from "@/lib/seo/hub-page";

const title = "Nights that cost nothing.";
const description =
  "Free and RSVP events on Pàdéyá — still verified hosts, still real tickets.";
const path = "/events/free";

export const metadata = hubPageMetadata({
  title: "Free events",
  description,
  path,
});

export default function FreeEventsPage() {
  const crumbs = buildDiscoveryTrail("free");
  return (
    <>
      <HubJsonLd
        name="Free events"
        description={description}
        path={path}
        crumbs={crumbs}
      />
      <CollectionLandingClient
        crumbs={crumbs}
        basePath={path}
        filters={{ paid: "free" }}
        fetchFilters={{ paid: "free" }}
        copy={{
          eyebrow: "Free",
          title,
          description,
          heroImage: "/brand/browse/price-free.svg",
          sectionEyebrow: "Featured",
          sectionTitle: "Free nights to watch",
          sectionTitleWeekend: "This weekend · free",
          sectionDescription:
            "RSVP and free-entry nights — still verified hosts and real tickets.",
          emptyTitle: "No free events yet",
          emptyTitleWeekend: "No free weekend events yet",
          emptyDescription: "Check back soon, or browse under ₦5,000 nights.",
          citySectionTitle: "Free events by city",
          cityCountSuffix: "free",
          secondaryAction: {
            href: "/events/under/5000",
            label: "Under ₦5,000",
          },
          jumpInTitle: "Stay in budget",
          jumpInDescription:
            "Weekend only, or step up to nights under ₦5,000.",
          ctaTitle: "Ready to host a free night?",
          ctaDescription:
            "Sell tickets, build Legacy, and grow an audience that shows up.",
        }}
      />
    </>
  );
}
