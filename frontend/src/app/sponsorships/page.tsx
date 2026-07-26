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
 * Static metadata — facet noindex for ?host=&sponsor=&q=&sort= is applied in
 * middleware so this route stays ISR-cacheable.
 */
export const metadata: Metadata = sponsorshipsIndexMetadata();

export const revalidate = 120;

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
