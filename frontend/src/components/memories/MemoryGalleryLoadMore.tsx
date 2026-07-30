"use client";

import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";

type MemoryGalleryLoadMoreProps = {
  remaining: number;
  onLoadMore: () => void;
  className?: string;
  announceId?: string;
};

export function MemoryGalleryLoadMore({
  remaining,
  onLoadMore,
  className,
  announceId,
}: MemoryGalleryLoadMoreProps) {
  if (remaining <= 0) return null;

  return (
    <div className={cn("flex flex-col items-center gap-2 pt-2", className)}>
      <Button type="button" variant="secondary" size="sm" onClick={onLoadMore}>
        Load more ({remaining} remaining)
      </Button>
      {announceId ? (
        <p id={announceId} className="sr-only" aria-live="polite" />
      ) : null}
    </div>
  );
}
