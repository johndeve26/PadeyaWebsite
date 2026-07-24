"use client";

import { useEffect } from "react";

import { EventMapPreviewCard } from "@/components/events/map/EventMapPreviewCard";
import { cn } from "@/lib/cn";
import type { MapEventPin } from "@/lib/maps/types";

export function MapMobileBottomSheet({
  event,
  open,
  onClose,
  onSelect,
  className = "",
}: {
  event: MapEventPin | null;
  open: boolean;
  onClose: () => void;
  onSelect?: (id: string) => void;
  className?: string;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open || !event) return null;

  return (
    <div
      className={cn(
        "pointer-events-none absolute inset-x-0 bottom-0 z-20 px-3 pb-3",
        className,
      )}
    >
      <div
        role="dialog"
        aria-label={event.title}
        className="pointer-events-auto mx-auto max-w-lg padeya-section-enter"
      >
        <div className="mb-2 flex justify-center">
          <button
            type="button"
            onClick={onClose}
            className="h-1.5 w-10 rounded-full bg-paper/35 dark:bg-paper/40"
            aria-label="Dismiss event preview"
          />
        </div>
        <EventMapPreviewCard
          event={event}
          selected
          onSelect={onSelect}
          className="shadow-[var(--shadow-soft)] backdrop-blur-md dark:bg-ink/95"
        />
      </div>
    </div>
  );
}
