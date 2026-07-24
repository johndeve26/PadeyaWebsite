"use client";

import Link from "next/link";

import { Button, Container, Logo } from "@/components/ui";
import { brand } from "@/lib/brand";

type SystemErrorExperienceProps = {
  code?: string;
  title: string;
  description: string;
  primaryHref?: string;
  primaryLabel?: string;
  secondaryHref?: string;
  secondaryLabel?: string;
  /** When true, use fixed ink surface (global-error has no theme providers). */
  ink?: boolean;
};

/** Premium recovery UI for error / unauthorized / fatal pages. */
export function SystemErrorExperience({
  code,
  title,
  description,
  primaryHref = "/",
  primaryLabel = "Back to home",
  secondaryHref = "/support",
  secondaryLabel = "Contact support",
  ink = false,
}: SystemErrorExperienceProps) {
  const shell = ink
    ? "min-h-screen bg-ink text-paper"
    : "min-h-[70vh] bg-background text-foreground";
  const muted = ink ? "text-paper/70" : "text-muted-foreground";
  const heading = ink ? "text-paper" : "text-heading";

  return (
    <main className={shell}>
      <Container className="flex flex-col items-center py-16 text-center sm:py-24">
        <Logo variant={ink ? "dark" : "auto"} height={32} />
        {code ? (
          <p
            className="mt-8 text-sm font-bold uppercase tracking-[0.2em]"
            style={{ color: brand.colors.green }}
          >
            {code}
          </p>
        ) : null}
        <h1 className={`mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl ${heading}`}>
          {title}
        </h1>
        <p className={`mt-4 max-w-md text-base leading-relaxed ${muted}`}>
          {description}
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link href={primaryHref}>
            <Button size="lg" variant={ink ? "primary" : "primary"}>
              {primaryLabel}
            </Button>
          </Link>
          <Link href={secondaryHref}>
            <Button size="lg" variant={ink ? "outline-dark" : "secondary"}>
              {secondaryLabel}
            </Button>
          </Link>
        </div>
      </Container>
    </main>
  );
}
