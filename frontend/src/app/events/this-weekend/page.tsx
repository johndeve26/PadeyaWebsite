import { CollectionLandingClient } from "@/components/discovery/CollectionLandingClient";
import { buildDiscoveryTrail } from "@/lib/marketplace-breadcrumbs";
import { HubJsonLd, hubPageMetadata } from "@/lib/seo/hub-page";

const title = "What’s on this weekend.";
const description =
  "Friday through Sunday on Pàdéyá — verified nights already on the calendar.";
const path = "/events/this-weekend";

export const metadata = hubPageMetadata({
  title: "This weekend",
  description,
  path,
});

export default function ThisWeekendPage() {
  const crumbs = buildDiscoveryTrail("weekend");
  return (
    <>
      <HubJsonLd
        name="This weekend"
        description={description}
        path={path}
        crumbs={crumbs}
      />
      <CollectionLandingClient
        crumbs={crumbs}
        basePath={path}
        filters={{ weekend: true }}
        fetchFilters={{ weekend: true }}
        copy={{
          eyebrow: "This weekend",
          title,
          description,
          heroImage: "/brand/browse/when-weekend.svg",
          sectionEyebrow: "Featured",
          sectionTitle: "Weekend nights to watch",
          sectionTitleWeekend: "Weekend nights to watch",
          sectionDescription:
            "Verified tickets for nights happening Friday through Sunday.",
          emptyTitle: "Nothing listed for this weekend yet",
          emptyTitleWeekend: "Nothing listed for this weekend yet",
          emptyDescription: "Check back soon, or browse all upcoming events.",
          citySectionTitle: "This weekend by city",
          cityCountSuffix: "this weekend",
          hideWeekendToggle: true,
          jumpInTitle: "Pick a path",
          jumpInDescription: "Free nights, VIP, or the full marketplace.",
          secondaryAction: { href: "/events/free", label: "Free only" },
          ctaTitle: "Hosting this weekend?",
          ctaDescription:
            "Sell tickets, build Legacy, and own the room before Friday hits.",
        }}
      />
    </>
  );
}
