"use client";

import { useEffect, useState } from "react";

import { Button, Media, Modal } from "@/components/ui";
import type { MemoryMedia } from "@/lib/types/memories";

type MemoryLightboxProps = {
  photos: MemoryMedia[];
  index: number;
  open: boolean;
  onClose: () => void;
  onIndexChange: (index: number) => void;
};

export function MemoryLightbox({
  photos,
  index,
  open,
  onClose,
  onIndexChange,
}: MemoryLightboxProps) {
  const photo = photos[index];
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") {
        onIndexChange((index + 1) % photos.length);
      }
      if (e.key === "ArrowLeft") {
        onIndexChange((index - 1 + photos.length) % photos.length);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, index, photos.length, onClose, onIndexChange]);

  if (!mounted || !open || !photo) return null;

  const attribution =
    photo.uploader_role === "fan"
      ? photo.attribution?.trim() || "Verified attendee"
      : null;

  return (
    <Modal open={open} onClose={onClose} title="Memory photo">
      <div className="space-y-4">
        <div className="relative aspect-[4/3] w-full overflow-hidden rounded-xl bg-surface-muted">
          <Media
            src={photo.url}
            alt={photo.caption || "Event memory"}
            fill
            className="object-contain"
            sizes="(max-width: 1024px) 100vw, 960px"
            priority
          />
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            {photo.caption ? (
              <p className="text-sm text-foreground">{photo.caption}</p>
            ) : null}
            {attribution ? (
              <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {attribution}
                {photo.verified_attendee ? " · Verified attendee" : ""}
              </p>
            ) : null}
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={photos.length < 2}
              onClick={() =>
                onIndexChange((index - 1 + photos.length) % photos.length)
              }
            >
              Previous
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={photos.length < 2}
              onClick={() => onIndexChange((index + 1) % photos.length)}
            >
              Next
            </Button>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          {index + 1} / {photos.length} · Esc to close
        </p>
      </div>
    </Modal>
  );
}
