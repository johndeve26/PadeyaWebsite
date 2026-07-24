import Link from "next/link";
import { type ReactNode } from "react";

import { Button, HeroSection, Logo } from "@/components/ui";
import { brand } from "@/lib/brand";
import { cn } from "@/lib/cn";

export function DiscoveryHubHero({
  title,
  description,
  ctaLabel = "Explore events",
  ctaHref = "#browse",
  secondaryCtaLabel,
  secondaryCtaHref,
  eyebrow = "Discover",
  className = "",
  search,
  backgroundSrc = brand.heroImage,
}: {
  title: string;
  description: string;
  ctaLabel?: string;
  ctaHref?: string;
  secondaryCtaLabel?: string;
  secondaryCtaHref?: string;
  eyebrow?: string;
  className?: string;
  /** Optional search panel rendered into the hero for discovery without scroll. */
  search?: ReactNode;
  /** Taxonomy-specific art when available; falls back to brand hero. */
  backgroundSrc?: string;
}) {
  return (
    <HeroSection
      minHeight={search ? "default" : "compact"}
      backgroundSrc={backgroundSrc}
      backgroundAlt=""
      className={cn("border-b border-paper/10", className)}
      atmosphere
    >
      <Logo
        variant="dark"
        height={40}
        href="/"
        className="padeya-hero-brand drop-shadow-[0_2px_20px_rgb(0_0_0_/0.5)]"
      />
      <div className="padeya-hero-brand max-w-3xl space-y-5 sm:space-y-6">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent">
          {eyebrow}
        </p>
        <h1 className="text-balance text-3xl font-extrabold leading-tight tracking-tight [text-shadow:0_2px_28px_rgb(0_0_0_/_0.55)] sm:text-4xl md:text-[3.15rem] md:leading-[1.05]">
          {title}
        </h1>
        <p className="max-w-2xl text-pretty text-base leading-relaxed text-subtle-foreground sm:text-lg md:text-xl">
          {description}
        </p>
        <div className="flex flex-col gap-3 pt-1 sm:flex-row sm:flex-wrap">
          <Link href={ctaHref} className="w-full sm:w-auto">
            <Button
              size="lg"
              variant="primary"
              className="padeya-btn-ripple w-full sm:w-auto"
            >
              {ctaLabel}
            </Button>
          </Link>
          {secondaryCtaLabel && secondaryCtaHref ? (
            <Link href={secondaryCtaHref} className="w-full sm:w-auto">
              <Button
                size="lg"
                variant="outline-dark"
                className="padeya-btn-micro w-full sm:w-auto"
              >
                {secondaryCtaLabel}
              </Button>
            </Link>
          ) : null}
        </div>
      </div>
      {search ? (
        <div className="padeya-hero-brand w-full max-w-5xl pt-2 sm:pt-4">
          {search}
        </div>
      ) : null}
    </HeroSection>
  );
}
