import type { Metadata } from "next";

import { SponsorshipsMarketplaceClient } from "./SponsorshipsMarketplaceClient";
import {
  collectionPageJsonLd,
  JsonLdScript,
} from "@/lib/seo/jsonld";
import { sponsorshipsIndexMetadata } from "@/lib/seo/sponsor-metadata";
import { siteOrigin } from "@/lib/seo/site";

const INTRO =
  "Discover open sponsorship slots and partner with verified Pàdéyá hosts — brand placements, event activations, and measurable nightlife audiences.";

/**
 * Query filters (?host=, ?sponsor=) stay usable but must not create indexable URLs.
 */
export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}): Promise<Metadata> {
  const sp = await searchParams;
  const hasFacet = Boolean(sp.host || sp.sponsor || sp.q || sp.sort);
  const base = sponsorshipsIndexMetadata();
  if (!hasFacet) return base;
  return {
    ...base,
    robots: { index: false, follow: true },
  };
}

/**
 * Sponsorship marketplace — server metadata + crawlable intro;
 * filters/grid remain a client island.
 */
export default function SponsorshipsPage() {
  const origin = siteOrigin();
  return (
    <>
      <JsonLdScript
        data={collectionPageJsonLd({
          name: "Sponsorships on Pàdéyá",
          description: INTRO,
          path: "/sponsorships",
          origin,
        })}
      />
      <SponsorshipsMarketplaceClient />
    </>
  );
}
