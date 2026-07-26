import { fetchPublicJson } from "@/lib/cache/public-api";
import { PUBLIC_REVALIDATE } from "@/lib/cache/public-revalidate";
import type { EventMemory, MemoryAlbumsResponse } from "@/lib/types/memories";

export async function fetchMemoryAlbumsServer(
  limit = 24,
): Promise<MemoryAlbumsResponse> {
  const data = await fetchPublicJson<MemoryAlbumsResponse>(
    `/memories/albums?limit=${limit}`,
    {
      next: {
        revalidate: PUBLIC_REVALIDATE.eventsList,
        tags: ["memories", "memories-albums"],
      },
    },
  );
  return data ?? { items: [], next_cursor: null };
}

export async function fetchMemoryBySlugServer(
  slug: string,
): Promise<EventMemory | null> {
  return fetchPublicJson<EventMemory>(
    `/memories/events/${encodeURIComponent(slug)}`,
    {
      next: {
        revalidate: PUBLIC_REVALIDATE.eventDetail,
        tags: ["memories", `memories-${slug}`, `event-${slug}`],
      },
    },
  );
}
