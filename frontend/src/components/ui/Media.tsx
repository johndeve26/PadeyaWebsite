import Image from "next/image";
import type { CSSProperties } from "react";

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
};

/**
 * Public media renderer — prefers next/image for optimizable hosts,
 * falls back to <img> for SVG / unknown remotes (no SSRF-style wildcards).
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
}: MediaProps) {
  const resolved = resolveMediaUrl(src);
  if (!resolved) return null;

  const resolvedSizes = resolveMediaSizes(sizes) ?? "100vw";
  const eager = priority || loading === "eager";
  // `cn` only joins, so emitting the default alongside a caller's `object-*`
  // utility ties on specificity and Tailwind's later `object-cover` rule wins.
  const imgClass = cn(
    "h-full w-full",
    !OBJECT_FIT_CLASS.test(className) && "object-cover",
    className,
  );

  if (isSvgMediaSrc(resolved) || !isOptimizableMediaSrc(resolved)) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- SVG / unlisted hosts
      <img
        src={resolved}
        alt={alt}
        className={imgClass}
        style={style}
        loading={eager ? "eager" : "lazy"}
        fetchPriority={priority ? "high" : "auto"}
        decoding="async"
        width={width}
        height={height}
      />
    );
  }

  if (!fill && width && height) {
    return (
      <Image
        src={resolved}
        alt={alt}
        width={width}
        height={height}
        className={imgClass}
        style={style}
        sizes={resolvedSizes}
        priority={priority}
        loading={priority ? undefined : eager ? "eager" : "lazy"}
        // Avoid blank cards when CDN Content-Type is wrong (octet-stream).
        unoptimized={
          resolved.startsWith("http") || resolved.startsWith("/media/")
        }
      />
    );
  }

  return (
    <Image
      src={resolved}
      alt={alt}
      fill
      className={imgClass}
      style={style}
      sizes={resolvedSizes}
      priority={priority}
      loading={priority ? undefined : eager ? "eager" : "lazy"}
      unoptimized={
        resolved.startsWith("http") || resolved.startsWith("/media/")
      }
    />
  );
}
