import type { Metadata } from "next";

import { HostsMarketplace } from "@/components/hosts/HostsMarketplace";
import { buildPageMetadata } from "@/lib/seo/site";
import type { HostDiscovery } from "@/lib/types/hosts-discovery";

export const metadata: Metadata = buildPageMetadata({
  title: "Hosts",
  description:
    "Discover Host Legacy Pages on Pàdéyá: verified event creators with upcoming nights, reviews, Vault, and ticketing history.",
  path: "/hosts",
});

export const revalidate = 180;

async function loadHosts(): Promise<HostDiscovery[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const apiPrefix = process.env.NEXT_PUBLIC_API_PREFIX ?? "/api/v1";
  try {
    // Next's patched fetch can ignore AbortSignal against a hung origin;
    // race a hard timeout so production builds never stall on localhost API.
    const res = await Promise.race([
      fetch(`${apiUrl}${apiPrefix}/legacy/discover/hosts`, {
        next: { revalidate: 180 },
      }),
      new Promise<null>((resolve) => {
        setTimeout(() => resolve(null), 5_000);
      }),
    ]);
    if (!res || !res.ok) return [];
    return (await res.json()) as HostDiscovery[];
  } catch {
    return [];
  }
}

export default async function HostsPage() {
  const hosts = await loadHosts();
  return <HostsMarketplace initialHosts={hosts} />;
}
