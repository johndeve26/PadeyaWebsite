import type { MemoryMedia } from "@/lib/types/memories";

/** CSS grid masonry row unit (px). */
export const MASONRY_ROW_HEIGHT = 8;

export const MASONRY_DEFAULT_ASPECT = 4 / 3;
export const MASONRY_MAX_ASPECT = 2.5;
export const MASONRY_MIN_ASPECT = 0.4;

export const INITIAL_PHOTOS_BATCH = 12;
export const LOAD_MORE_BATCH = 12;

export type MemoryGallerySource = "host" | "community";

export function memoryAspectRatio(
  width?: number | null,
  height?: number | null,
): number {
  if (width && height && width > 0 && height > 0) {
    const ratio = height / width;
    return Math.min(MASONRY_MAX_ASPECT, Math.max(MASONRY_MIN_ASPECT, ratio));
  }
  return MASONRY_DEFAULT_ASPECT;
}

/**
 * Older memory rows never recorded width/height, so the 4:3 default used to
 * shape their cell and crop wide artwork. Fall back to the decoded size the
 * browser reports for those.
 */
export function resolveMemoryAspect(
  width?: number | null,
  height?: number | null,
  measured?: number | null,
): number {
  if (width && height && width > 0 && height > 0) {
    return memoryAspectRatio(width, height);
  }
  if (measured && measured > 0) {
    return Math.min(MASONRY_MAX_ASPECT, Math.max(MASONRY_MIN_ASPECT, measured));
  }
  return MASONRY_DEFAULT_ASPECT;
}

/** Responsive column count — min card width ~180–220px. */
export function masonryColumnCount(containerWidth: number): number {
  if (containerWidth < 320) return 1;
  if (containerWidth < 480) return 2;
  if (containerWidth < 768) return 2;
  if (containerWidth < 1024) return 3;
  if (containerWidth < 1280) return 4;
  return containerWidth >= 1440 ? 5 : 4;
}

export function masonryGap(containerWidth: number): number {
  if (containerWidth < 640) return 12;
  if (containerWidth < 1024) return 16;
  return 18;
}

export function masonryRowSpan(
  columnWidth: number,
  aspectRatio: number,
  gap: number,
): number {
  const imageHeight = columnWidth * aspectRatio;
  return Math.max(
    1,
    Math.round((imageHeight + gap) / (MASONRY_ROW_HEIGHT + gap)),
  );
}

export function memoryAltText(photo: MemoryMedia): string {
  const caption = photo.caption?.trim();
  if (caption) return caption;
  if (photo.uploader_role === "fan") {
    return "Community memory photo";
  }
  return "Host memory photo";
}

export function memoryAttributionLabel(photo: MemoryMedia): string | null {
  if (photo.uploader_role === "fan") {
    return photo.attribution?.trim() || "Verified attendee";
  }
  return null;
}

export function memorySourceBadge(
  source: MemoryGallerySource,
  hostDisplayName?: string,
): string {
  if (source === "host") {
    return hostDisplayName ? `From ${hostDisplayName}` : "Host memory";
  }
  return "Community memory";
}

export function memoryImageSizes(): string {
  return "(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw";
}

/** Demo SVG placeholders include baked-in titles — avoid duplicate overlays. */
export function isFallbackMemoryArt(src: string): boolean {
  const lower = src.toLowerCase();
  return (
    lower.includes("/demo/memories/") ||
    lower.endsWith(".svg") ||
    lower.includes(".svg?")
  );
}

export function clampVisibleCount(
  total: number,
  visible: number,
  batch: number = LOAD_MORE_BATCH,
): number {
  if (visible >= total) return total;
  return Math.min(total, visible + batch);
}
