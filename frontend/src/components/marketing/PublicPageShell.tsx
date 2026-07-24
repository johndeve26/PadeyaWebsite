import Link from "next/link";
import type { ReactNode } from "react";

import { Button, Container } from "@/components/ui";
import { brand } from "@/lib/brand";

type PublicPageShellProps = {
  eyebrow?: string;
  title: string;
  description: string;
  children?: ReactNode;
  actions?: ReactNode;
  narrow?: boolean;
};

/** Shared premium shell for public marketing / trust pages. */
export function PublicPageShell({
  eyebrow = brand.name,
  title,
  description,
  children,
  actions,
  narrow = false,
}: PublicPageShellProps) {
  return (
    <div className="relative overflow-hidden bg-background text-foreground">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_color-mix(in_srgb,var(--primary)_16%,transparent),_transparent_55%),linear-gradient(180deg,var(--surface-muted),var(--background))]"
      />
      <Container
        width={narrow ? "narrow" : "default"}
        className="py-12 sm:py-16 lg:py-20"
      >
        <header className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-bold uppercase tracking-[0.16em] text-primary">
            {eyebrow}
          </p>
          <h1 className="mt-3 font-display text-4xl font-extrabold tracking-tight text-heading sm:text-5xl">
            {title}
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            {description}
          </p>
          {actions ? (
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              {actions}
            </div>
          ) : null}
        </header>
        {children ? <div className="mt-12 sm:mt-14">{children}</div> : null}
      </Container>
    </div>
  );
}

export function PublicCtaPair({
  primaryHref,
  primaryLabel,
  secondaryHref,
  secondaryLabel,
}: {
  primaryHref: string;
  primaryLabel: string;
  secondaryHref: string;
  secondaryLabel: string;
}) {
  return (
    <>
      <Link href={primaryHref}>
        <Button size="lg">{primaryLabel}</Button>
      </Link>
      <Link href={secondaryHref}>
        <Button size="lg" variant="secondary">
          {secondaryLabel}
        </Button>
      </Link>
    </>
  );
}
