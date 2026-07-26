import { CollectionLandingClient } from "@/components/discovery/CollectionLandingClient";
import { buildHomeEvents } from "@/lib/marketplace-breadcrumbs";
import { HubJsonLd, hubPageMetadata } from "@/lib/seo/hub-page";

const title = "What’s on today.";
const description =
  "Tonight and today on Pàdéyá: verified events already on the calendar.";
const path = "/events/today";

export const metadata = hubPageMetadata({
  title: "Today’s events",
  description,
  path,
});

export default function TodayEventsPage() {
  const crumbs = [...buildHomeEvents(), { label: "Today", href: path }];
  return (
    <>
      <HubJsonLd
        name="Today’s events"
        description={description}
        path={path}
        crumbs={crumbs}
      />
      <CollectionLandingClient
        crumbs={crumbs}
        basePath={path}
        filters={{ today: true }}
        copy={{
          eyebrow: "Today",
          title,
          description,
          heroImage: "/brand/browse/when-weekend.svg",
          sectionEyebrow: "Featured",
          sectionTitle: "Happening today",
          sectionTitleWeekend: "Happening today",
          sectionDescription: "Verified tickets for events starting today.",
          emptyTitle: "Nothing listed for today yet",
          emptyTitleWeekend: "Nothing listed for today yet",
          emptyDescription: "Check this weekend, or browse all upcoming events.",
          citySectionTitle: "Today by city",
          cityCountSuffix: "today",
          hideWeekendToggle: true,
          jumpInTitle: "Pick a path",
          jumpInDescription: "Weekend nights, free entries, or the full list.",
          secondaryAction: {
            href: "/events/this-weekend",
            label: "This weekend",
          },
          ctaTitle: "Hosting tonight?",
          ctaDescription:
            "Publish, sell, and check guests in with Pàdéyá Host tools.",
        }}
      />
    </>
  );
}
