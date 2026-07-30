"use client";

import { useEffect, useRef, useState } from "react";

import { Button, Media, Modal } from "@/components/ui";
import { track } from "@/lib/analytics";
import { TrackedAction } from "@/lib/analytics-taxonomy";
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
  const dialogContentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
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
      }
      if (e.key === "ArrowLeft" && photos.length > 1) {
        e.preventDefault();
        const prev = (index - 1 + photos.length) % photos.length;
        onIndexChange(prev);
        track(TrackedAction.MEMORY_LIGHTBOX_PREVIOUS, {
          targetEventId: eventId,
          entityType: "memory_media",
          entityId: photos[prev]?.id,
          metadata: { source, gallery_position: prev },
          immediate: true,
        });
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, index, photos, eventId, source, onClose, onIndexChange]);

  useEffect(() => {
    if (open && dialogContentRef.current) {
      dialogContentRef.current.focus();
    }
  }, [open, index]);

  if (!mounted || !open || !photo) return null;

  const attribution = memoryAttributionLabel(photo);
  const sourceBadge = memorySourceBadge(source, hostDisplayName);
  const alt = memoryAltText(photo);

  function goPrev() {
    const prev = (index - 1 + photos.length) % photos.length;
    onIndexChange(prev);
    track(TrackedAction.MEMORY_LIGHTBOX_PREVIOUS, {
      targetEventId: eventId,
      entityType: "memory_media",
      entityId: photos[prev]?.id,
      metadata: { source, gallery_position: prev },
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

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={photo.caption?.trim() || "Memory photo"}
      description={`${displayPosition} of ${totalCount}`}
      className="sm:max-w-3xl"
      footer={
        photos.length > 1 ? (
          <>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={goPrev}
            >
              Previous
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={goNext}
            >
              Next
            </Button>
          </>
        ) : undefined
      }
    >
      <div ref={dialogContentRef} tabIndex={-1} className="space-y-4 outline-none">
        <div
          className="relative w-full overflow-hidden rounded-xl bg-surface-muted"
          style={{
            aspectRatio:
              photo.width && photo.height
                ? `${photo.width} / ${photo.height}`
                : "4 / 3",
            maxHeight: "min(70vh, 720px)",
          }}
        >
          <Media
            src={photo.url}
            alt={alt}
            fill
            className="object-contain"
            sizes="(max-width: 1024px) 100vw, 960px"
            priority
            width={photo.width ?? undefined}
            height={photo.height ?? undefined}
          />
        </div>

        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
            {sourceBadge}
          </p>
          {photo.caption?.trim() ? (
            <p className="text-sm text-foreground">{photo.caption}</p>
          ) : null}
          {attribution ? (
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {attribution}
              {photo.verified_attendee ? " · Verified attendee" : ""}
            </p>
          ) : null}
        </div>

        <p className="text-xs text-muted-foreground">
          {displayPosition} of {totalCount} · Esc to close · Arrow keys to
          navigate
        </p>
      </div>
    </Modal>
  );
}
