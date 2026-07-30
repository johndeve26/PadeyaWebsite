import { cn } from "@/lib/cn";
import {
  MASONRY_ROW_HEIGHT,
  masonryColumnCount,
  masonryGap,
  masonryRowSpan,
  memoryAspectRatio,
} from "@/lib/memories/gallery-utils";

type MemoryGallerySkeletonProps = {
  count?: number;
  className?: string;
};

const SKELETON_ASPECTS = [1.2, 0.75, 1, 1.5, 0.65, 1.1];

export function MemoryGallerySkeleton({
  count = 6,
  className,
}: MemoryGallerySkeletonProps) {
  const containerWidth = 1024;
  const columns = masonryColumnCount(containerWidth);
  const gap = masonryGap(containerWidth);
  const columnWidth =
    (containerWidth - gap * (columns - 1)) / columns;

  return (
    <ul
      className={cn(
        "grid w-full motion-reduce:animate-none",
        className,
      )}
      style={{
        gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
        gridAutoRows: `${MASONRY_ROW_HEIGHT}px`,
        gap: `${gap}px`,
      }}
      aria-busy="true"
      aria-label="Loading memories"
    >
      {Array.from({ length: count }, (_, i) => {
        const aspect = memoryAspectRatio(
          1000,
          1000 * SKELETON_ASPECTS[i % SKELETON_ASPECTS.length],
        );
        const span = masonryRowSpan(columnWidth, aspect, gap);
        return (
          <li
            key={i}
            style={{ gridRowEnd: `span ${span}` }}
            className="min-h-0 overflow-hidden rounded-xl"
          >
            <div
              className="h-full w-full animate-pulse rounded-xl bg-surface-muted motion-reduce:animate-none"
            />
          </li>
        );
      })}
    </ul>
  );
}
