import { VipLandingClient } from "@/components/discovery/VipLandingClient";
import { buildDiscoveryTrail } from "@/lib/marketplace-breadcrumbs";
import { HubJsonLd, hubPageMetadata } from "@/lib/seo/hub-page";

const title = "VIP nights";
const description =
  "Events with VIP or VVIP tiers on Pàdéyá — tables, upgrades, and premium access.";
const path = "/events/vip";

export const metadata = hubPageMetadata({
  title,
  description,
  path,
});

export default function VipEventsPage() {
  const crumbs = buildDiscoveryTrail("vip");
  return (
    <>
      <HubJsonLd
        name={title}
        description={description}
        path={path}
        crumbs={crumbs}
      />
      <VipLandingClient crumbs={crumbs} />
    </>
  );
}
