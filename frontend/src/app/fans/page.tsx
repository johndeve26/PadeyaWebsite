import type { Metadata } from "next";

import { FansDirectory } from "@/components/passport/FansDirectory";
import { fetchPublicJson } from "@/lib/cache/public-api";
import { PUBLIC_REVALIDATE } from "@/lib/cache/public-revalidate";
import { buildPageMetadata } from "@/lib/seo/site";
import type { FanDirectoryList } from "@/lib/types/passport";

export const metadata: Metadata = buildPageMetadata({
  title: "Fans · Fan Passport",
  description:
    "Discover public Fan Passports on Pàdéyá: fans who attend verified events, follow hosts, earn badges, and optionally use Fan Connect.",
  path: "/fans",
});

export const revalidate = 180;

async function loadDirectory(): Promise<FanDirectoryList> {
  const data = await fetchPublicJson<FanDirectoryList>("/fans?limit=24", {
    next: {
      revalidate: PUBLIC_REVALIDATE.profiles,
      tags: ["fans", "fan-directory"],
    },
  });
  return data ?? { items: [], total: 0, page: 1, limit: 24 };
}

export default async function FansDirectoryPage() {
  const directory = await loadDirectory();
  return (
    <FansDirectory
      initialItems={directory.items}
      initialTotal={directory.total}
    />
  );
}
