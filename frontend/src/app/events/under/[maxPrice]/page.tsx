import { notFound } from "next/navigation";

import { PriceLandingClient } from "@/components/discovery/PriceLandingClient";
import {
  parseMaxPriceParam,
  priceLandingDescription,
  priceLandingPath,
  priceLandingTitle,
} from "@/lib/discovery/price-landing";
import { buildPriceTrail } from "@/lib/marketplace-breadcrumbs";
import { HubJsonLd, hubPageMetadata } from "@/lib/seo/hub-page";

type Props = { params: Promise<{ maxPrice: string }> };

export async function generateMetadata({ params }: Props) {
  const { maxPrice: raw } = await params;
  const maxPrice = parseMaxPriceParam(raw);
  if (maxPrice == null) return {};
  const title = priceLandingTitle(maxPrice);
  return hubPageMetadata({
    title,
    description: priceLandingDescription(maxPrice),
    path: priceLandingPath(maxPrice),
  });
}

export default async function UnderPriceHubPage({ params }: Props) {
  const { maxPrice: raw } = await params;
  const maxPrice = parseMaxPriceParam(raw);
  if (maxPrice == null) notFound();

  const title = priceLandingTitle(maxPrice);
  const description = priceLandingDescription(maxPrice);
  const crumbs = buildPriceTrail(title);

  return (
    <>
      <HubJsonLd
        name={title}
        description={description}
        path={priceLandingPath(maxPrice)}
        crumbs={crumbs}
      />
      <PriceLandingClient maxPrice={maxPrice} crumbs={crumbs} />
    </>
  );
}
