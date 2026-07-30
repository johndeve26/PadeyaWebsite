"use client";

import { useRef } from "react";

import { Media } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  isFallbackMemoryArt,
  memoryAltText,
  memoryAttributionLabel,
  memoryImageSizes,
  memorySourceBadge,
  type MemoryGallerySource,
} from "@/lib/memories/gallery-utils";
import type { MemoryMedia } from "@/lib/types/memories";

type MemoryMasonryTileProps = {
  photo: MemoryMedia;
  source: MemoryGallerySource;
  rowSpan: number;
  index: number;
  hostDisplayName?: string;
  onOpen: (index: number, trigger: HTMLButtonElement) => void;
  priority?: boolean;
};

export function MemoryMasonryTile({
  photo,
  source,
  rowSpan,
  index,
  hostDisplayName,
  onOpen,
  priority = false,
}: MemoryMasonryTileProps) {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const imageSrc = photo.thumbnail_url || photo.url;
  const fallbackArt = isFallbackMemoryArt(imageSrc);
  const alt = memoryAltText(photo);
  const attribution = memoryAttributionLabel(photo);
  const badge = memorySourceBadge(source, hostDisplayName);
  const showCaption =
    !fallbackArt && photo.caption?.trim() && photo.caption.trim().length > 0;

  return (
    <li
      className="min-h-0"
      style={{ gridRowEnd: `span ${rowSpan}` }}
      data-memory-id={photo.id}
      data-memory-position={index}
    >
      <button
        ref={buttonRef}
        type="button"
        className={cn(
          "group relative h-full w-full overflow-hidden rounded-xl border border-border/60 bg-surface-muted",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
          "motion-reduce:transition-none",
        )}
        onClick={() => {
          if (buttonRef.current) onOpen(index, buttonRef.current);
        }}
        aria-label={alt}
      >
        <div className="relative h-full w-full">
          <Media
            src={imageSrc}
            alt={fallbackArt ? "" : alt}
            fill
            className={cn(
              "object-cover transition-transform duration-300 motion-reduce:transition-none",
              "group-hover:scale-[1.03] group-focus-visible:scale-[1.03]",
            )}
            sizes={memoryImageSizes()}
            loading={priority ? "eager" : "lazy"}
            priority={priority}
            width={photo.width ?? undefined}
            height={photo.height ?? undefined}
          />
        </div>

        <span
          className={cn(
            "absolute left-2 top-2 rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
            "bg-ink/70 text-paper backdrop-blur-sm",
            "opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-visible:opacity-100",
            "transition-opacity duration-200 motion-reduce:transition-none",
          )}
        >
          {badge}
        </span>

        <span
          className={cn(
            "absolute inset-0 bg-gradient-to-t from-ink/70 via-ink/10 to-transparent",
            "opacity-0 transition-opacity duration-200 motion-reduce:transition-none",
            "group-hover:opacity-100 group-focus-visible:opacity-100",
            "sm:opacity-0",
          )}
          aria-hidden
        />

        {(showCaption || attribution) ? (
          <span
            className={cn(
              "absolute inset-x-0 bottom-0 space-y-0.5 p-3 text-left",
              "opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-visible:opacity-100",
              "transition-opacity duration-200 motion-reduce:transition-none",
            )}
          >
            {showCaption ? (
              <span className="block text-sm font-semibold text-paper line-clamp-2">
                {photo.caption}
              </span>
            ) : null}
            {attribution ? (
              <span className="block text-xs font-medium text-paper/80">
                {attribution}
                {photo.verified_attendee ? " · Verified attendee" : ""}
              </span>
            ) : null}
          </span>
        ) : null}
      </button>
    </li>
  );
}
