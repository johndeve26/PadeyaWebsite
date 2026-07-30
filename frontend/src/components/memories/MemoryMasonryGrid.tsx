"use client";

import dynamic from "next/dynamic";
import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";

import { track } from "@/lib/analytics";
import { TrackedAction } from "@/lib/analytics-taxonomy";
import { cn } from "@/lib/cn";
import {
  INITIAL_PHOTOS_BATCH,
  LOAD_MORE_BATCH,
  MASONRY_ROW_HEIGHT,
  clampVisibleCount,
  masonryColumnCount,
  masonryGap,
  masonryRowSpan,
  memoryAspectRatio,
  type MemoryGallerySource,
} from "@/lib/memories/gallery-utils";
import type { MemoryMedia } from "@/lib/types/memories";

import { MemoryGalleryEmptyState } from "./MemoryGalleryEmptyState";
import { MemoryGalleryLoadMore } from "./MemoryGalleryLoadMore";
import { MemoryMasonryTile } from "./MemoryMasonryTile";

const MemoryLightbox = dynamic(
  () =>
    import("@/components/memories/MemoryLightbox").then((m) => m.MemoryLightbox),
  { ssr: false },
);

type MemoryMasonryGridProps = {
  photos: MemoryMedia[];
  source: MemoryGallerySource;
  eventId: string;
  hostDisplayName?: string;
  emptyLabel?: string;
  className?: string;
  initialBatch?: number;
};

type LayoutState = {
  columns: number;
  gap: number;
  columnWidth: number;
};

function computeLayout(containerWidth: number): LayoutState {
  const columns = masonryColumnCount(containerWidth);
  const gap = masonryGap(containerWidth);
  const columnWidth =
    columns > 0
      ? (containerWidth - gap * (columns - 1)) / columns
      : containerWidth;
  return { columns, gap, columnWidth };
}

export function MemoryMasonryGrid({
  photos,
  source,
  eventId,
  hostDisplayName,
  emptyLabel = "No photos yet.",
  className,
  initialBatch = INITIAL_PHOTOS_BATCH,
}: MemoryMasonryGridProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const impressedRef = useRef<Set<string>>(new Set());
  const loadAnnounceId = useId();

  const [layout, setLayout] = useState<LayoutState>({
    columns: 4,
    gap: 16,
    columnWidth: 240,
  });
  const [visibleCount, setVisibleCount] = useState(
    Math.min(initialBatch, photos.length),
  );
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState(0);
  const [returnFocusEl, setReturnFocusEl] = useState<HTMLElement | null>(null);

  const visiblePhotos = useMemo(
    () => photos.slice(0, visibleCount),
    [photos, visibleCount],
  );
  const remaining = photos.length - visibleCount;

  const rowSpans = useMemo(
    () =>
      visiblePhotos.map((photo) =>
        masonryRowSpan(
          layout.columnWidth,
          memoryAspectRatio(photo.width, photo.height),
          layout.gap,
        ),
      ),
    [visiblePhotos, layout],
  );

  const measure = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const width = el.clientWidth;
    if (width <= 0) return;
    setLayout(computeLayout(width));
  }, []);

  useEffect(() => {
    measure();
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => measure());
    ro.observe(el);
    return () => ro.disconnect();
  }, [measure]);

  useEffect(() => {
    setVisibleCount(Math.min(initialBatch, photos.length));
    impressedRef.current.clear();
  }, [photos, initialBatch]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof IntersectionObserver === "undefined") return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          const id = entry.target.getAttribute("data-memory-id");
          const position = entry.target.getAttribute("data-memory-position");
          if (!id || impressedRef.current.has(id)) continue;
          impressedRef.current.add(id);
          track(TrackedAction.MEMORY_IMPRESSION, {
            targetEventId: eventId,
            entityType: "memory_media",
            entityId: id,
            metadata: {
              source,
              gallery_position: position ? Number(position) : undefined,
            },
          });
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.5, rootMargin: "0px" },
    );

    const tiles = el.querySelectorAll("[data-memory-id]");
    tiles.forEach((tile) => observer.observe(tile));

    return () => observer.disconnect();
  }, [visiblePhotos, eventId, source]);

  function openLightbox(index: number, trigger: HTMLButtonElement) {
    setReturnFocusEl(trigger);
    setLightboxIndex(index);
    setLightboxOpen(true);
    const photo = photos[index];
    if (photo) {
      track(TrackedAction.MEMORY_OPEN, {
        targetEventId: eventId,
        entityType: "memory_media",
        entityId: photo.id,
        metadata: {
          source,
          gallery_position: index,
        },
        immediate: true,
      });
    }
  }

  function closeLightbox() {
    setLightboxOpen(false);
    if (returnFocusEl) {
      requestAnimationFrame(() => {
        returnFocusEl.focus();
        setReturnFocusEl(null);
      });
    }
  }

  function handleLoadMore() {
    const next = clampVisibleCount(photos.length, visibleCount, LOAD_MORE_BATCH);
    setVisibleCount(next);
    track(TrackedAction.MEMORY_LOAD_MORE, {
      targetEventId: eventId,
      metadata: {
        source,
        visible_count: next,
        total_count: photos.length,
      },
      immediate: true,
    });
    const announce = document.getElementById(loadAnnounceId);
    if (announce) {
      announce.textContent = `Loaded ${next - visibleCount} more memories. ${next} of ${photos.length} visible.`;
    }
  }

  if (!photos.length) {
    return <MemoryGalleryEmptyState message={emptyLabel} className={className} />;
  }

  return (
    <div ref={containerRef} className={cn("w-full", className)}>
      <ul
        className="grid w-full"
        style={{
          gridTemplateColumns: `repeat(${layout.columns}, minmax(0, 1fr))`,
          gridAutoRows: `${MASONRY_ROW_HEIGHT}px`,
          gap: `${layout.gap}px`,
        }}
        aria-label={
          source === "host" ? "Host memories gallery" : "Community memories gallery"
        }
      >
        {visiblePhotos.map((photo, index) => (
          <MemoryMasonryTile
            key={photo.id}
            photo={photo}
            source={source}
            rowSpan={rowSpans[index] ?? 1}
            index={index}
            hostDisplayName={hostDisplayName}
            onOpen={openLightbox}
            priority={index < 4}
          />
        ))}
      </ul>

      <MemoryGalleryLoadMore
        remaining={remaining}
        onLoadMore={handleLoadMore}
        announceId={loadAnnounceId}
      />

      <MemoryLightbox
        photos={photos}
        index={lightboxIndex}
        open={lightboxOpen}
        source={source}
        eventId={eventId}
        hostDisplayName={hostDisplayName}
        onClose={closeLightbox}
        onIndexChange={setLightboxIndex}
      />
    </div>
  );
}
