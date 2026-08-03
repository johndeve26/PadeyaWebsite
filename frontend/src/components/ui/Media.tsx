"use client";

import Image from "next/image";
import type { CSSProperties, ReactNode } from "react";

import { enlargeableAttrs } from "@/components/media/ImageLightbox";
import { cn } from "@/lib/cn";
import {
  isOptimizableMediaSrc,
  isSvgMediaSrc,
  resolveMediaSizes,
  type MediaSizesPreset,
} from "@/lib/media-image";
import { resolveMediaUrl } from "@/lib/media";

const OBJECT_FIT_CLASS =
  /(?:^|\s)object-(contain|cover|fill|none|scale-down)(?:\s|$)/;

type MediaProps = {
  src: string;
  alt?: string;
  className?: string;
  style?: CSSProperties;
  /**
   * LCP / above-fold only. Never set on marketplace card grids.
   * Implies eager loading + fetchPriority high via next/image.
   */
  priority?: boolean;
  /** Layout-accurate sizes string or preset key. */
  sizes?: string | MediaSizesPreset;
  /** Default lazy unless priority. */
  loading?: "lazy" | "eager";
  /**
   * next/image `fill` (parent must be positioned + sized).
   * Default true — matches existing absolute/h-full card & hero usage.
   */
  fill?: boolean;
  width?: number;
  height?: number;
  /**
   * Click to enlarge (WhatsApp/TikTok-style). Default true for content photos.
   * Set false for decorative images or when a domain lightbox already handles open.
   */
  enlargeable?: boolean;
  /** Full-res URL for lightbox when preview src is a smaller variant. */
  enlargeSrc?: string | null;
  focalX?: number | null;
  focalY?: number | null;
};

function maybeEnlargeableWrap(
  node: ReactNode,
  options: {
    enlargeable: boolean;
    fill: boolean;
    src: string;
    alt: string;
    enlargeSrc?: string | null;
  },
) {
  if (!options.enlargeable) return node;
  const attrs = enlargeableAttrs(options.src, options.alt, options.enlargeSrc);
  if (!attrs) return node;
  return (
    <span
      className={cn(
        options.fill ? "absolute inset-0 block" : "contents",
        "cursor-zoom-in",
      )}
      {...attrs}
    >
      {node}
    </span>
  );
}

/**
 * Public media renderer — prefers next/image for optimizable hosts,
 * falls back to <img> for SVG / unknown remotes (no SSRF-style wildcards).
 * Enlargeable by default via ImageLightboxProvider.
 */
export function Media({
  src,
  alt = "",
  className = "",
  style,
  priority = false,
  sizes,
  loading,
  fill = true,
  width,
  height,
  enlargeable = true,
  enlargeSrc,
  focalX,
  focalY,
}: MediaProps) {
  const resolved = resolveMediaUrl(src);
  if (!resolved) return null;

  const resolvedSizes = resolveMediaSizes(sizes) ?? "100vw";
  const eager = priority || loading === "eager";
  const objectPosition =
    focalX != null || focalY != null
      ? `${(focalX ?? 0.5) * 100}% ${(focalY ?? 0.5) * 100}%`
      : undefined;
  const mergedStyle: CSSProperties | undefined = objectPosition
    ? { ...style, objectPosition }
    : style;
  const imgClass = cn(
    "h-full w-full",
    !OBJECT_FIT_CLASS.test(className) && "object-cover",
    className,
  );

  let node: ReactNode;

  if (isSvgMediaSrc(resolved) || !isOptimizableMediaSrc(resolved)) {
    node = (
      // eslint-disable-next-line @next/next/no-img-element -- SVG / unlisted hosts
      <img
        src={resolved}
        alt={alt}
        className={imgClass}
        style={mergedStyle}
        loading={eager ? "eager" : "lazy"}
        fetchPriority={priority ? "high" : "auto"}
        decoding="async"
        width={width}
        height={height}
      />
    );
  } else if (!fill && width && height) {
    node = (
      <Image
        src={resolved}
        alt={alt}
        width={width}
        height={height}
        className={imgClass}
        style={mergedStyle}
        sizes={resolvedSizes}
        priority={priority}
        loading={priority ? undefined : eager ? "eager" : "lazy"}
        unoptimized={
          resolved.startsWith("http") || resolved.startsWith("/media/")
        }
      />
    );
  } else {
    node = (
      <Image
        src={resolved}
        alt={alt}
        fill
        className={imgClass}
        style={mergedStyle}
        sizes={resolvedSizes}
        priority={priority}
        loading={priority ? undefined : eager ? "eager" : "lazy"}
        unoptimized={
          resolved.startsWith("http") || resolved.startsWith("/media/")
        }
      />
    );
  }

  return maybeEnlargeableWrap(node, {
    enlargeable,
    fill,
    src: resolved,
    alt,
    enlargeSrc,
  });
}
