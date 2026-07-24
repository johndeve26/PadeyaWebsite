import Image from "next/image";
import Link from "next/link";
import { type ReactNode } from "react";

import { Badge, Button, Container } from "@/components/ui";
import { headerDarkSurfaceProps } from "@/components/layout/headerSurface";
import { cn } from "@/lib/cn";

export function SponsorHero({
  eyebrow = "Sponsors",
  title,
  description,
  primaryCta,
  secondaryCta,
  stats,
  backgroundSrc,
  className = "",
  compact = false,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  primaryCta?: { href: string; label: string };
  secondaryCta?: { href: string; label: string };
  stats?: ReactNode;
  backgroundSrc?: string;
  className?: string;
  compact?: boolean;
}) {
  return (
    <section
      {...headerDarkSurfaceProps}
      className={cn("relative z-0 overflow-hidden bg-ink text-paper", className)}
    >
      {backgroundSrc ? (
        <Image
          src={backgroundSrc}
          alt=""
          fill
          priority
          sizes="100vw"
          className="object-cover object-center opacity-35 saturate-[0.85]"
        />
      ) : null}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-gradient-to-br from-ink via-ink/95 to-ink"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink via-transparent to-ink/40"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -left-20 top-1/3 h-64 w-64 rounded-full bg-accent/15 blur-3xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -right-16 bottom-0 h-56 w-56 rounded-full bg-accent/10 blur-3xl"
      />

      <Container
        className={cn(
          "relative space-y-7",
          compact ? "py-12 sm:py-14" : "py-14 sm:py-20",
        )}
      >
        <div className="flex max-w-3xl flex-col justify-center gap-4">
          <Badge tone="accent" className="w-fit uppercase tracking-[0.14em]">
            {eyebrow}
          </Badge>
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl sm:leading-[1.05] md:text-[3.25rem]">
            {title}
          </h1>
          <p className="max-w-2xl text-base leading-relaxed text-subtle-foreground sm:text-lg">
            {description}
          </p>
          {(primaryCta || secondaryCta) && (
            <div className="flex flex-wrap gap-3 pt-1">
              {primaryCta ? (
                <Link href={primaryCta.href}>
                  <Button size="lg">{primaryCta.label}</Button>
                </Link>
              ) : null}
              {secondaryCta ? (
                <Link href={secondaryCta.href}>
                  <Button size="lg" variant="outline-dark">
                    {secondaryCta.label}
                  </Button>
                </Link>
              ) : null}
            </div>
          )}
        </div>
        {stats ? <div className="pt-1">{stats}</div> : null}
      </Container>
    </section>
  );
}
