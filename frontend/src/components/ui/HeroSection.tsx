import Image from "next/image";
import { type ReactNode } from "react";

import { headerDarkSurfaceProps } from "@/components/layout/headerSurface";
import { cn } from "@/lib/cn";
import { isSvgMediaSrc } from "@/lib/media-image";

import { Container } from "./Container";

export function HeroSection({
  children,
  className = "",
  minHeight = "default",
  grain = true,
  backgroundSrc,
  backgroundAlt = "",
  backgroundFocalX = 0.5,
  backgroundFocalY = 0.5,
  atmosphere = false,
}: {
  children: ReactNode;
  className?: string;
  minHeight?: "default" | "tall" | "compact";
  grain?: boolean;
  /** Full-bleed background image (e.g. brand hero art). */
  backgroundSrc?: string;
  backgroundAlt?: string;
  /** Normalized focal point for object-position (0–1). */
  backgroundFocalX?: number;
  backgroundFocalY?: number;
  /** Soft aurora / particles / beams for discovery heroes. */
  atmosphere?: boolean;
}) {
  const objectPosition = `${Math.round(Math.min(1, Math.max(0, backgroundFocalX)) * 100)}% ${Math.round(Math.min(1, Math.max(0, backgroundFocalY)) * 100)}%`;
  const height =
    minHeight === "tall"
      ? "min-h-[min(78vh,820px)]"
      : minHeight === "compact"
        ? "min-h-[42vh]"
        : "min-h-[min(68vh,720px)]";

  // SVG + CDN/media uploads: skip the optimizer so bad CDN Content-Types
  // cannot blank the hero (which left only the green aurora visible).
  const skipOptimize =
    Boolean(backgroundSrc) &&
    (isSvgMediaSrc(backgroundSrc!) ||
      backgroundSrc!.startsWith("http") ||
      backgroundSrc!.startsWith("/media/"));

  return (
    <section
      {...headerDarkSurfaceProps}
      className={cn(
        "relative min-w-0 overflow-hidden bg-ink text-paper",
        className,
      )}
    >
      {backgroundSrc ? (
        <>
          <Image
            src={backgroundSrc}
            alt={backgroundAlt}
            fill
            // Next.js 16: use `preload` + high fetch priority for LCP heroes.
            preload
            fetchPriority="high"
            sizes="100vw"
            unoptimized={skipOptimize}
            className={cn(
              "object-cover padeya-hero-media",
              atmosphere && "padeya-discovery-parallax",
            )}
            style={{ objectPosition }}
          />
          {/* Left-weighted scrim so brand + copy stay readable on busy art */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-gradient-to-r from-ink via-ink/75 to-ink/35"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink/80 via-transparent to-ink/40"
          />
        </>
      ) : (
        <div aria-hidden className="padeya-hero-glow pointer-events-none absolute inset-0" />
      )}
      {atmosphere ? (
        <>
          <div
            aria-hidden
            className="padeya-discovery-aurora pointer-events-none absolute inset-0"
          />
          <div
            aria-hidden
            className="padeya-discovery-beams pointer-events-none absolute inset-0"
          />
          <div
            aria-hidden
            className="padeya-discovery-particles pointer-events-none absolute inset-0"
          />
        </>
      ) : null}
      {grain ? (
        <div
          aria-hidden
          className={cn(
            "padeya-grain pointer-events-none absolute inset-0",
            backgroundSrc ? "opacity-30" : "opacity-60",
          )}
        />
      ) : null}
      <Container
        className={cn(
          "relative flex flex-col justify-center gap-5 py-12 sm:gap-6 sm:py-16",
          height,
        )}
      >
        {children}
      </Container>
    </section>
  );
}
