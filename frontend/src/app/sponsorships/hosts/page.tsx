import type { Metadata } from "next";

import { SponsorHostsMarketplace } from "./SponsorHostsMarketplace";
import {
  collectionPageJsonLd,
  JsonLdScript,
} from "@/lib/seo/jsonld";
import { sponsorshipHostsIndexMetadata } from "@/lib/seo/sponsor-metadata";
import { siteOrigin } from "@/lib/seo/site";
import type { SponsorHost } from "@/lib/types/sponsorships";

export const metadata: Metadata = sponsorshipHostsIndexMetadata();

export const revalidate = 30;

const INTRO =
  "Browse verified Pàdéyá hosts with event history, checked-in attendance, Legacy reputation, and open sponsorship slots.";

async function loadSponsorHosts(): Promise<SponsorHost[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const apiPrefix = process.env.NEXT_PUBLIC_API_PREFIX ?? "/api/v1";
  try {
    const res = await Promise.race([
      fetch(`${apiUrl}${apiPrefix}/sponsorships/public/hosts`, {
        next: { revalidate: 30 },
      }),
      new Promise<null>((resolve) => {
        setTimeout(() => resolve(null), 5_000);
      }),
    ]);
    if (!res || !res.ok) return [];
    return (await res.json()) as SponsorHost[];
  } catch {
    return [];
  }
}

export default async function SponsorHostsPage() {
  const hosts = await loadSponsorHosts();
  const origin = siteOrigin();
  return (
    <>
      <JsonLdScript
        data={collectionPageJsonLd({
          name: "Hosts open to sponsorship",
          description: INTRO,
          path: "/sponsorships/hosts",
          origin,
        })}
      />
      <SponsorHostsMarketplace initialHosts={hosts} />
    </>
  );
}
