import type { Metadata } from "next";

import { MemoriesHubClient } from "@/components/memories/MemoriesHubClient";
import { HubJsonLd, hubPageMetadata } from "@/lib/seo/hub-page";
import { fetchMemoryAlbumsServer } from "@/lib/memories/public-server";

/**
 * ISR hub for /memories.
 * Do not read server searchParams — keep CDN-cacheable like /events.
 */
export const revalidate = 120;

export const metadata: Metadata = hubPageMetadata({
  title: "Memories",
  description:
    "Relive nights on Pàdéyá: event photo albums shared by hosts and verified attendees.",
  path: "/memories",
});

export default async function MemoriesHubPage() {
  const albums = await fetchMemoryAlbumsServer(24);

  return (
    <>
      <HubJsonLd
        name="Event Memories on Pàdéyá"
        description="Relive nights on Pàdéyá: photo albums from hosts and verified attendees."
        path="/memories"
        crumbs={[
          { label: "Home", href: "/" },
          { label: "Memories" },
        ]}
      />
      <MemoriesHubClient albums={albums.items} />
    </>
  );
}
