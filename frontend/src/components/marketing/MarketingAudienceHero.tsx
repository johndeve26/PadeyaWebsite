import Link from "next/link";
import type { ReactNode } from "react";

import { Button, HeroSection, Logo } from "@/components/ui";
import { brand } from "@/lib/brand";

type Cta = {
  href: string;
  label: string;
};

type MarketingAudienceHeroProps = {
  eyebrow: string;
  headline: string;
  support: string;
  primary: Cta;
  secondary: Cta;
  /** Quiet trust line under CTAs (e.g. verified events · QR tickets). */
  trustLine?: string;
  /** Optional third action (e.g. tertiary text link). */
  tertiary?: ReactNode;
};

/** Full-bleed audience marketing hero — one composition, brand-first. */
export function MarketingAudienceHero({
  eyebrow,
  headline,
  support,
  primary,
  secondary,
  trustLine,
  tertiary,
}: MarketingAudienceHeroProps) {
  return (
    <HeroSection
      minHeight="tall"
      backgroundSrc={brand.heroImage}
      backgroundAlt=""
    >
      <Logo
        variant="dark"
        priority
        height={52}
        href={undefined}
        className="padeya-hero-brand drop-shadow-[0_2px_24px_rgb(0_0_0_/0.55)]"
      />
      <p className="padeya-hero-brand text-xs font-bold uppercase tracking-[0.2em] text-primary">
        {eyebrow}
      </p>
      <div className="max-w-3xl space-y-5 sm:space-y-6">
        <h1 className="padeya-hero-brand text-balance text-[2rem] font-extrabold leading-[1.1] tracking-tight [text-shadow:0_2px_28px_rgb(0_0_0_/_0.55)] sm:text-5xl sm:leading-[1.08] md:text-6xl md:leading-[1.05] lg:text-[4rem]">
          {headline}
        </h1>
        <p className="max-w-xl text-pretty text-base leading-relaxed text-paper/75 sm:text-lg md:text-xl">
          {support}
        </p>
        <div className="flex flex-col gap-3 pt-1 sm:flex-row sm:flex-wrap">
          <Link href={primary.href} className="w-full sm:w-auto">
            <Button size="lg" className="padeya-btn-micro w-full sm:w-auto">
              {primary.label}
            </Button>
          </Link>
          <Link href={secondary.href} className="w-full sm:w-auto">
            <Button
              size="lg"
              variant="outline-dark"
              className="padeya-btn-micro w-full sm:w-auto"
            >
              {secondary.label}
            </Button>
          </Link>
        </div>
        {trustLine ? (
          <p className="text-sm font-semibold tracking-wide text-paper/55 sm:text-[0.95rem]">
            {trustLine}
          </p>
        ) : null}
        {tertiary ? <div className="pt-0.5">{tertiary}</div> : null}
      </div>
    </HeroSection>
  );
}
