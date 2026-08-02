"use client";

import { useEffect, useRef, useState } from "react";
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

  const [mounted, setMounted] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);

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
      if (e.key === "ArrowRight" && photos.length > 1) {
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
      if (e.key === "ArrowLeft" && photos.length > 1) {
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
  }, [open, index, photos, eventId, source, onClose, onIndexChange]);

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

  if (!mounted || !open || !photo) return null;

  const attribution = memoryAttributionLabel(photo);
  const sourceBadge = memorySourceBadge(source, hostDisplayName);
  const alt = memoryAltText(photo);
  const title = photo.caption?.trim() || "Memory photo";

  const panel = (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-label={title}
      tabIndex={-1}
      className="fixed inset-0 z-[100] flex flex-col bg-ink/95 text-paper outline-none backdrop-blur-sm"
    >
      <button
        type="button"
        aria-label="Close photo"
        className="absolute inset-0 z-0 cursor-zoom-out"
        onClick={onClose}
      />

      <header className="relative z-10 flex shrink-0 items-start justify-between gap-4 px-4 py-4 sm:px-6">
        <div className="min-w-0 space-y-1">
          <p className="text-xs font-bold uppercase tracking-wide text-paper/60">
            {sourceBadge}
            <span className="mx-2 text-paper/30">·</span>
            {displayPosition} of {totalCount}
          </p>
          {photo.caption?.trim() ? (
            <p className="truncate text-sm font-semibold text-paper sm:text-base">
              {photo.caption}
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

      <div className="relative z-10 flex min-h-0 flex-1 items-center justify-center px-3 pb-4 sm:px-10">
        {photos.length > 1 ? (
          <button
            type="button"
            aria-label="Previous photo"
            onClick={goPrev}
            className={cn(
              "absolute left-2 top-1/2 z-20 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full",
              "bg-paper/10 text-lg text-paper transition hover:bg-paper/20 sm:left-4 sm:h-12 sm:w-12",
            )}
          >
            ‹
          </button>
        ) : null}

        <div
          className="relative z-10 flex h-full max-h-[min(82dvh,900px)] w-full max-w-[min(96vw,1200px)] items-center justify-center"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Full-resolution enlarge — avoid next/image fill constraints in lightbox */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={photo.url}
            alt={alt}
            width={photo.width ?? undefined}
            height={photo.height ?? undefined}
            className="max-h-[min(82dvh,900px)] max-w-full object-contain shadow-[0_20px_60px_rgb(0_0_0_/_0.45)]"
            draggable={false}
          />
        </div>

        {photos.length > 1 ? (
          <button
            type="button"
            aria-label="Next photo"
            onClick={goNext}
            className={cn(
              "absolute right-2 top-1/2 z-20 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full",
              "bg-paper/10 text-lg text-paper transition hover:bg-paper/20 sm:right-4 sm:h-12 sm:w-12",
            )}
          >
            ›
          </button>
        ) : null}
      </div>

      <footer className="relative z-10 shrink-0 space-y-1 px-4 pb-5 pt-1 text-center sm:px-6">
        {attribution ? (
          <p className="text-xs font-semibold uppercase tracking-wide text-paper/70">
            {attribution}
            {photo.verified_attendee ? " · Verified attendee" : ""}
          </p>
        ) : null}
        <p className="text-xs text-paper/45">
          Esc to close
          {photos.length > 1 ? " · Arrow keys to navigate" : ""}
        </p>
      </footer>
    </div>
  );

  return createPortal(panel, document.body);
}
