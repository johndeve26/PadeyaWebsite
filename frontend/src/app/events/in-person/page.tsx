import { FormatLandingClient } from "@/components/discovery/FormatLandingClient";
import { formatHubMeta } from "@/lib/discovery/format-landing";
import { buildPriceTrail } from "@/lib/marketplace-breadcrumbs";
import { HubJsonLd, hubPageMetadata } from "@/lib/seo/hub-page";

const meta = formatHubMeta("public");

export const metadata = hubPageMetadata({
  title: `${meta.eyebrow} events`,
  description: meta.description,
  path: meta.path,
});

export default function InPersonEventsPage() {
  const crumbs = buildPriceTrail(`${meta.eyebrow} events`);
  return (
    <>
      <HubJsonLd
        name={`${meta.eyebrow} events`}
        description={meta.description}
        path={meta.path}
        crumbs={crumbs}
      />
      <FormatLandingClient formatKey="public" crumbs={crumbs} />
    </>
  );
}
