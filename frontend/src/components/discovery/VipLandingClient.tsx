"use client";

import { CollectionLandingClient } from "@/components/discovery/CollectionLandingClient";
import type { BreadcrumbItem } from "@/components/ui/Breadcrumb";
import { isVipEvent } from "@/lib/discovery/event-filters";

const title = "Tables, tiers, and VIP access.";
const description =
  "Nights with VIP or VVIP tickets. Upgrade at checkout when the room goes deeper.";
const path = "/events/vip";

export function VipLandingClient({ crumbs }: { crumbs: BreadcrumbItem[] }) {
  return (
    <CollectionLandingClient
      crumbs={crumbs}
      basePath={path}
      filters={{}}
      match={isVipEvent}
      copy={{
        eyebrow: "VIP",
        title,
        description,
        heroImage: "/brand/browse/price-vip.svg",
        sectionEyebrow: "Featured",
        sectionTitle: "VIP nights to watch",
        sectionTitleWeekend: "This weekend · VIP",
        sectionDescription:
          "Events that offer VIP or VVIP tiers. Browse, then upgrade at checkout.",
        emptyTitle: "No VIP nights listed yet",
        emptyTitleWeekend: "No VIP nights this weekend yet",
        emptyDescription: "Check back soon, or browse all events on Pàdéyá.",
        citySectionTitle: "VIP nights by city",
        cityCountSuffix: "with VIP",
        jumpInTitle: "Raise the stakes",
        jumpInDescription: "Weekend only, or browse every verified night.",
        ctaTitle: "Hosting a VIP night?",
        ctaDescription:
          "Sell tiers, fill tables, and build a Legacy people remember.",
      }}
    />
  );
}
