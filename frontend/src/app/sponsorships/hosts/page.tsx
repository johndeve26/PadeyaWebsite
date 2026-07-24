import { SponsorHostsMarketplace } from "./SponsorHostsMarketplace";

import type { SponsorHost } from "@/lib/types/sponsorships";

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
  return <SponsorHostsMarketplace initialHosts={hosts} />;
}
