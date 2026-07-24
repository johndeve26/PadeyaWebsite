"use client";

import { CollectionLandingClient } from "@/components/discovery/CollectionLandingClient";
import type { BreadcrumbItem } from "@/components/ui/Breadcrumb";
import { collectionBrowseImage } from "@/lib/discovery/browse-images";
import {
  formatMaxPriceLabel,
  priceLandingDescription,
  priceLandingPath,
} from "@/lib/discovery/price-landing";

export function PriceLandingClient({
  maxPrice,
  crumbs,
}: {
  maxPrice: number;
  crumbs: BreadcrumbItem[];
}) {
  const path = priceLandingPath(maxPrice);
  const priceLabel = formatMaxPriceLabel(maxPrice);

  return (
    <CollectionLandingClient
      crumbs={crumbs}
      basePath={path}
      filters={{ max_price: maxPrice }}
      copy={{
        eyebrow: "Price",
        title: `Nights under ${priceLabel}.`,
        description: priceLandingDescription(maxPrice),
        heroImage: collectionBrowseImage(path),
        sectionEyebrow: "Featured",
        sectionTitle: `Upcoming under ${priceLabel}`,
        sectionTitleWeekend: `This weekend under ${priceLabel}`,
        sectionDescription: `Cheapest public ticket is ${priceLabel} or less — including free.`,
        emptyTitle: `No events under ${priceLabel} yet`,
        emptyTitleWeekend: `No weekend events under ${priceLabel} yet`,
        emptyDescription:
          "Check back soon, or browse free events and VIP nights.",
        citySectionTitle: `Under ${priceLabel} by city`,
        cityCountSuffix: `under ${priceLabel}`,
        secondaryAction: { href: "/events/free", label: "Free only" },
        jumpInTitle: "Fit the budget",
        jumpInDescription:
          "Weekend only, free nights, or the full marketplace.",
        ctaTitle: "Need a different price band?",
        ctaDescription:
          "From free RSVPs to VIP tables — find the night that fits.",
      }}
    />
  );
}
