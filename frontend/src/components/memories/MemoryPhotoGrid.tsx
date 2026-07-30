"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import type { MemoryMedia } from "@/lib/types/memories";

import { MemoryGalleryEmptyState } from "./MemoryGalleryEmptyState";

const MemoryMasonryGrid = dynamic(
  () =>
    import("@/components/memories/MemoryMasonryGrid").then(
      (m) => m.MemoryMasonryGrid,
    ),
  { ssr: false },
);

type MemoryPhotoGridProps = {
  photos: MemoryMedia[];
  title?: string;
  emptyLabel?: string;
  className?: string;
  eventId?: string;
  source?: "host" | "community";
  hostDisplayName?: string;
};

/**
 * Masonry gallery wrapper — preserves the MemoryPhotoGrid export for callers.
 */
export function MemoryPhotoGrid({
  photos,
  title,
  emptyLabel = "No photos yet.",
  className,
  eventId = "",
  source = "host",
  hostDisplayName,
}: MemoryPhotoGridProps) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setReady(true);
  }, []);

  if (!photos.length) {
    return (
      <div className={className}>
        {title ? (
          <h3 className="mb-3 text-sm font-extrabold uppercase tracking-[0.08em] text-muted-foreground">
            {title}
          </h3>
        ) : null}
        <MemoryGalleryEmptyState message={emptyLabel} />
      </div>
    );
  }

  return (
    <div className={className}>
      {title ? (
        <h3 className="mb-3 text-sm font-extrabold uppercase tracking-[0.08em] text-muted-foreground">
          {title}
        </h3>
      ) : null}
      {ready ? (
        <MemoryMasonryGrid
          photos={photos}
          source={source}
          eventId={eventId}
          hostDisplayName={hostDisplayName}
          emptyLabel={emptyLabel}
        />
      ) : (
        <MemoryGalleryEmptyState message="Loading gallery…" />
      )}
    </div>
  );
}
