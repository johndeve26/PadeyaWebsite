"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

import { Media } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { MemoryMedia } from "@/lib/types/memories";

const MemoryLightbox = dynamic(
  () =>
    import("@/components/memories/MemoryLightbox").then((m) => m.MemoryLightbox),
  { ssr: false },
);

type MemoryPhotoGridProps = {
  photos: MemoryMedia[];
  title?: string;
  emptyLabel?: string;
  className?: string;
};

export function MemoryPhotoGrid({
  photos,
  title,
  emptyLabel = "No photos yet.",
  className,
}: MemoryPhotoGridProps) {
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);

  if (!photos.length) {
    return (
      <p className="text-sm text-muted-foreground">{emptyLabel}</p>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      {title ? (
        <h3 className="text-sm font-extrabold uppercase tracking-[0.08em] text-muted-foreground">
          {title}
        </h3>
      ) : null}
      <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
        {photos.map((photo, i) => (
          <li key={photo.id}>
            <button
              type="button"
              className="group relative aspect-square w-full overflow-hidden rounded-xl bg-surface-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              onClick={() => {
                setIndex(i);
                setOpen(true);
              }}
              aria-label={photo.caption || "Open memory photo"}
            >
              <Media
                src={photo.thumbnail_url || photo.url}
                alt={photo.caption || ""}
                fill
                className="object-cover transition-transform duration-300 group-hover:scale-[1.03]"
                sizes="(max-width: 640px) 50vw, 25vw"
                loading={i < 4 ? "eager" : "lazy"}
              />
            </button>
          </li>
        ))}
      </ul>
      <MemoryLightbox
        photos={photos}
        index={index}
        open={open}
        onClose={() => setOpen(false)}
        onIndexChange={setIndex}
      />
    </div>
  );
}
