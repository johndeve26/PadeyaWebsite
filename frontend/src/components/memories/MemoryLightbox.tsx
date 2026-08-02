"use client";

import {
  useEffect,
  useRef,
  useState,
  type TouchEvent as ReactTouchEvent,
} from "react";
import { createPortal } from "react-dom";

import { track } from "@/lib/analytics";
import { TrackedAction } from "@/lib/analytics-taxonomy";
import { cn } from "@/lib/cn";
import {
  memoryAltText,
  memoryAttributionLabel,
  memorySourceBadge,
  type MemoryGallerySource,
} from "@/lib/memories/gallery-utils";
import type { MemoryMedia } from "@/lib/types/memories";

type MemoryLightboxProps = {
  photos: MemoryMedia[];
  index: number;
  open: boolean;
  source: MemoryGallerySource;
  eventId: string;
  hostDisplayName?: string;
  onClose: () => void;
  onIndexChange: (index: number) => void;
};

const MAX_DOTS = 16;

function ChevronLeftIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className={className}
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function ChevronRightIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className={className}
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M9 18l6-6-6-6" />
    </svg>
  );
}

export function MemoryLightbox({
  photos,
  index,
  open,
  source,
  eventId,
  hostDisplayName,
  onClose,
  onIndexChange,
}: MemoryLightboxProps) {
  const photo = photos[index];
  const totalCount = photos.length;
  const displayPosition = index + 1;
  const isCarousel = photos.length > 1;

  const [mounted, setMounted] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const touchStartX = useRef<number | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (!isCarousel) return;
      if (e.key === "ArrowRight") {
        e.preventDefault();
        const next = (index + 1) % photos.length;
        onIndexChange(next);
        track(TrackedAction.MEMORY_LIGHTBOX_NEXT, {
          targetEventId: eventId,
          entityType: "memory_media",
          entityId: photos[next]?.id,
          metadata: { source, gallery_position: next },
          immediate: true,
        });
        return;
      }
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        const prevIdx = (index - 1 + photos.length) % photos.length;
        onIndexChange(prevIdx);
        track(TrackedAction.MEMORY_LIGHTBOX_PREVIOUS, {
          targetEventId: eventId,
          entityType: "memory_media",
          entityId: photos[prevIdx]?.id,
          metadata: { source, gallery_position: prevIdx },
          immediate: true,
        });
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [
    open,
    isCarousel,
    index,
    photos,
    eventId,
    source,
    onClose,
    onIndexChange,
  ]);

  useEffect(() => {
    if (open && dialogRef.current) {
      dialogRef.current.focus();
    }
  }, [open, index]);

  function goPrev() {
    const prevIdx = (index - 1 + photos.length) % photos.length;
    onIndexChange(prevIdx);
    track(TrackedAction.MEMORY_LIGHTBOX_PREVIOUS, {
      targetEventId: eventId,
      entityType: "memory_media",
      entityId: photos[prevIdx]?.id,
      metadata: { source, gallery_position: prevIdx },
      immediate: true,
    });
  }

  function goNext() {
    const next = (index + 1) % photos.length;
    onIndexChange(next);
    track(TrackedAction.MEMORY_LIGHTBOX_NEXT, {
      targetEventId: eventId,
      entityType: "memory_media",
      entityId: photos[next]?.id,
      metadata: { source, gallery_position: next },
      immediate: true,
    });
  }

  function goTo(nextIndex: number) {
    if (nextIndex === index) return;
    const forward =
      nextIndex > index || (index === photos.length - 1 && nextIndex === 0);
    onIndexChange(nextIndex);
    track(
      forward
        ? TrackedAction.MEMORY_LIGHTBOX_NEXT
        : TrackedAction.MEMORY_LIGHTBOX_PREVIOUS,
      {
        targetEventId: eventId,
        entityType: "memory_media",
        entityId: photos[nextIndex]?.id,
        metadata: { source, gallery_position: nextIndex },
        immediate: true,
      },
    );
  }

  function onTouchStart(e: ReactTouchEvent) {
    touchStartX.current = e.changedTouches[0]?.clientX ?? null;
  }

  function onTouchEnd(e: ReactTouchEvent) {
    if (!isCarousel || touchStartX.current == null) return;
    const endX = e.changedTouches[0]?.clientX;
    if (endX == null) return;
    const delta = endX - touchStartX.current;
    touchStartX.current = null;
    if (Math.abs(delta) < 48) return;
    if (delta < 0) goNext();
    else goPrev();
  }

  if (!mounted || !open || !photo) return null;

  const attribution = memoryAttributionLabel(photo);
  const sourceBadge = memorySourceBadge(source, hostDisplayName);
  const alt = memoryAltText(photo);
  const title = photo.caption?.trim() || "Memory photo";
  const showDots = isCarousel && totalCount <= MAX_DOTS;

  const navButtonClass = cn(
    "absolute top-1/2 z-20 flex -translate-y-1/2 items-center justify-center",
    "h-12 w-12 rounded-full border border-paper/25 bg-ink/70 text-paper shadow-[0_8px_24px_rgb(0_0_0_/_0.45)]",
    "backdrop-blur-sm transition hover:border-primary hover:bg-primary hover:text-primary-foreground",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary sm:h-14 sm:w-14",
  );

  const panel = (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-label={title}
      aria-roledescription={isCarousel ? "carousel" : undefined}
      tabIndex={-1}
      className="fixed inset-0 z-[100] flex flex-col bg-ink/95 text-paper outline-none backdrop-blur-sm"
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
    >
      <button
        type="button"
        aria-label="Close photo"
        className="absolute inset-0 z-0 cursor-zoom-out"
        onClick={onClose}
      />

      <header className="relative z-10 flex shrink-0 items-start justify-between gap-4 px-4 py-4 sm:px-6">
        <div className="min-w-0 space-y-2">
          <p className="text-xs font-bold uppercase tracking-wide text-paper/60">
            {sourceBadge}
          </p>
          {photo.caption?.trim() ? (
            <p className="truncate text-sm font-semibold text-paper sm:text-base">
              {photo.caption}
            </p>
          ) : null}
          {isCarousel ? (
            <p className="inline-flex flex-wrap items-center gap-x-2 gap-y-1 rounded-full border border-paper/20 bg-paper/10 px-3 py-1 text-xs font-bold uppercase tracking-[0.08em] text-paper">
              <span className="text-primary">Carousel</span>
              <span className="text-paper/35">·</span>
              Photo {displayPosition} of {totalCount}
              <span className="font-semibold normal-case tracking-normal text-paper/55">
                · swipe or use arrows
              </span>
            </p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-paper/10 text-xl leading-none text-paper transition hover:bg-paper/20"
        >
          ×
        </button>
      </header>

      <div
        className="relative z-10 flex min-h-0 flex-1 items-center justify-center px-14 pb-2 sm:px-20"
        role={isCarousel ? "group" : undefined}
        aria-roledescription={isCarousel ? "slide" : undefined}
        aria-label={
          isCarousel ? `Photo ${displayPosition} of ${totalCount}` : undefined
        }
      >
        {isCarousel ? (
          <button
            type="button"
            aria-label="Previous photo"
            onClick={goPrev}
            className={cn(navButtonClass, "left-2 sm:left-4")}
          >
            <ChevronLeftIcon className="h-6 w-6 sm:h-7 sm:w-7" />
          </button>
        ) : null}

        <div
          className="relative z-10 flex h-full max-h-[min(72dvh,820px)] w-full max-w-[min(96vw,1200px)] items-center justify-center"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Full-resolution enlarge — avoid next/image fill constraints in lightbox */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={photo.url}
            alt={alt}
            width={photo.width ?? undefined}
            height={photo.height ?? undefined}
            className="max-h-[min(72dvh,820px)] max-w-full object-contain shadow-[0_20px_60px_rgb(0_0_0_/_0.45)]"
            draggable={false}
          />
        </div>

        {isCarousel ? (
          <button
            type="button"
            aria-label="Next photo"
            onClick={goNext}
            className={cn(navButtonClass, "right-2 sm:right-4")}
          >
            <ChevronRightIcon className="h-6 w-6 sm:h-7 sm:w-7" />
          </button>
        ) : null}
      </div>

      <footer className="relative z-10 shrink-0 space-y-3 px-4 pb-5 pt-2 text-center sm:px-6">
        {isCarousel ? (
          <div className="flex flex-col items-center gap-3">
            {showDots ? (
              <div
                role="tablist"
                aria-label="Photo carousel"
                className="flex max-w-full flex-wrap items-center justify-center gap-1"
              >
                {photos.map((item, i) => (
                  <button
                    key={item.id}
                    type="button"
                    role="tab"
                    aria-selected={i === index}
                    aria-label={`Go to photo ${i + 1} of ${totalCount}`}
                    onClick={() => goTo(i)}
                    className="inline-flex h-9 w-9 items-center justify-center rounded-full"
                  >
                    <span
                      aria-hidden
                      className={cn(
                        "rounded-full transition-all",
                        i === index
                          ? "h-2 w-6 bg-primary"
                          : "h-2 w-2 bg-paper/35 hover:bg-paper/60",
                      )}
                    />
                  </button>
                ))}
              </div>
            ) : (
              <div
                className="mx-auto h-1.5 w-full max-w-xs overflow-hidden rounded-full bg-paper/15"
                role="progressbar"
                aria-valuemin={1}
                aria-valuemax={totalCount}
                aria-valuenow={displayPosition}
                aria-label={`Photo ${displayPosition} of ${totalCount}`}
              >
                <div
                  className="h-full rounded-full bg-primary transition-[width] duration-200"
                  style={{
                    width: `${(displayPosition / totalCount) * 100}%`,
                  }}
                />
              </div>
            )}

            <div className="flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={goPrev}
                className="inline-flex items-center gap-1.5 rounded-full border border-paper/20 bg-paper/10 px-3.5 py-2 text-xs font-bold uppercase tracking-[0.06em] text-paper transition hover:border-primary hover:text-primary"
              >
                <ChevronLeftIcon className="h-4 w-4" />
                Prev
              </button>
              <span className="min-w-[4.5rem] text-sm font-semibold tabular-nums text-paper/80">
                {displayPosition} / {totalCount}
              </span>
              <button
                type="button"
                onClick={goNext}
                className="inline-flex items-center gap-1.5 rounded-full border border-paper/20 bg-paper/10 px-3.5 py-2 text-xs font-bold uppercase tracking-[0.06em] text-paper transition hover:border-primary hover:text-primary"
              >
                Next
                <ChevronRightIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
        ) : null}

        {attribution ? (
          <p className="text-xs font-semibold uppercase tracking-wide text-paper/70">
            {attribution}
            {photo.verified_attendee ? " · Verified attendee" : ""}
          </p>
        ) : null}
        <p className="text-xs text-paper/45">
          Esc to close
          {isCarousel ? " · Arrow keys or swipe to browse" : ""}
        </p>
      </footer>
    </div>
  );

  return createPortal(panel, document.body);
}
