"use client";

import { Media } from "@/components/ui/Media";
import type { MediaSizesPreset } from "@/lib/media-image";
import {
  fromMemoryMedia,
  getMediaCard,
  getMediaDisplay,
  getMediaFull,
  getMediaThumbnail,
  normalizePublicMedia,
} from "@/lib/public-media";
import type { MediaVariantIntent, PublicMedia } from "@/lib/types/public-media";

type DisplayVariant = Exclude<MediaVariantIntent, "og">;

const VARIANT_GETTERS = {
  thumbnail: getMediaThumbnail,
  card: getMediaCard,
  display: getMediaDisplay,
  full: getMediaFull,
} as const;

type PublicMediaImageProps = {
  media: PublicMedia | string;
  variant?: DisplayVariant;
  alt?: string;
  enlargeVariant?: "full" | "display";
  enlargeable?: boolean;
  sizes?: string | MediaSizesPreset;
  priority?: boolean;
  className?: string;
  fill?: boolean;
  width?: number;
  height?: number;
};

function resolveEnlargeSrc(
  media: PublicMedia,
  enlargeVariant: "full" | "display",
): string | null {
  const fullSrc = getMediaFull(media);
  const displaySrc = getMediaDisplay(media);
  const thumbSrc = getMediaThumbnail(media);

  let enlargeSrc =
    enlargeVariant === "full"
      ? fullSrc || displaySrc
      : displaySrc || fullSrc;

  if (enlargeSrc && thumbSrc && enlargeSrc === thumbSrc && (fullSrc || displaySrc)) {
    enlargeSrc = fullSrc || displaySrc;
  }

  return enlargeSrc;
}

export function PublicMediaImage({
  media: input,
  variant = "display",
  alt: altOverride,
  enlargeVariant = "full",
  enlargeable = true,
  sizes,
  priority,
  className,
  fill = true,
  width,
  height,
}: PublicMediaImageProps) {
  const media = normalizePublicMedia(input);
  if (!media) return null;

  const getter = VARIANT_GETTERS[variant];
  const src = getter(media);
  if (!src) return null;

  const alt = altOverride ?? media.alt ?? "";
  const enlargeSrc = enlargeable ? resolveEnlargeSrc(media, enlargeVariant) : null;

  return (
    <Media
      src={src}
      alt={alt}
      enlargeSrc={enlargeSrc}
      focalX={media.focal_x}
      focalY={media.focal_y}
      fill={fill}
      width={width ?? media.width ?? undefined}
      height={height ?? media.height ?? undefined}
      sizes={sizes}
      priority={priority}
      className={className}
      enlargeable={enlargeable}
    />
  );
}

export { fromMemoryMedia };
