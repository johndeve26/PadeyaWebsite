"use client";

import type { MemoryMedia } from "@/lib/types/memories";

import { MemoryMasonryGrid } from "./MemoryMasonryGrid";

type EventMemoriesGalleryProps = {
  eventId: string;
  hostDisplayName: string;
  hostMedia: MemoryMedia[];
  communityMedia: MemoryMedia[];
  hostCount?: number;
  communityCount?: number;
};

export function EventMemoriesGallery({
  eventId,
  hostDisplayName,
  hostMedia,
  communityMedia,
  hostCount,
  communityCount,
}: EventMemoriesGalleryProps) {
  const hostTotal = hostCount ?? hostMedia.length;
  const communityTotal = communityCount ?? communityMedia.length;

  return (
    <div className="space-y-10">
      <section className="space-y-4" aria-labelledby="host-memories-heading">
        <h2
          id="host-memories-heading"
          className="text-lg font-extrabold tracking-tight"
        >
          Host memories
          {hostTotal > 0 ? (
            <span className="ml-2 text-base font-semibold text-muted-foreground">
              · {hostTotal}
            </span>
          ) : null}
        </h2>
        <MemoryMasonryGrid
          photos={hostMedia}
          source="host"
          eventId={eventId}
          hostDisplayName={hostDisplayName}
          emptyLabel="The host has not added memory photos yet."
        />
      </section>

      <section className="space-y-4" aria-labelledby="community-memories-heading">
        <div className="space-y-1">
          <h2
            id="community-memories-heading"
            className="text-lg font-extrabold tracking-tight"
          >
            Community memories
            {communityTotal > 0 ? (
              <span className="ml-2 text-base font-semibold text-muted-foreground">
                · {communityTotal}
              </span>
            ) : null}
          </h2>
          <p className="text-sm text-muted-foreground">
            Photos from verified attendees. Private passports show as “Verified
            attendee” only.
          </p>
        </div>
        <MemoryMasonryGrid
          photos={communityMedia}
          source="community"
          eventId={eventId}
          emptyLabel="No community photos yet."
        />
      </section>
    </div>
  );
}
