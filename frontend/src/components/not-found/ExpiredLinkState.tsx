"use client";

import Link from "next/link";

import { Button, Container, Logo } from "@/components/ui";
import { brand } from "@/lib/brand";

/** Safe recovery UI for expired invites, payment, or ticket links (route still exists). */
export function ExpiredLinkState({
  title = "This link has expired",
  description = "This link is no longer valid. It may have expired, already been used, or been revoked. No payment or ticket details are shown here.",
  primaryHref = "/support",
  primaryLabel = "Contact support",
}: {
  title?: string;
  description?: string;
  primaryHref?: string;
  primaryLabel?: string;
}) {
  return (
    <main className="relative flex min-h-[70vh] items-center overflow-hidden bg-ink py-16 text-paper">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_50%_0%,color-mix(in_srgb,#8EF012_18%,transparent),transparent_60%)]"
      />
      <Container width="narrow" className="relative text-center">
        <div className="flex justify-center">
          <Logo variant="dark" height={36} />
        </div>
        <p
          className="mt-8 text-xs font-bold uppercase tracking-[0.16em]"
          style={{ color: brand.colors.green }}
        >
          Link
        </p>
        <h1 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
          {title}
        </h1>
        <p className="mx-auto mt-4 max-w-md text-base leading-relaxed text-paper/70">
          {description}
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link href={primaryHref}>
            <Button size="lg">{primaryLabel}</Button>
          </Link>
          <Link href="/dashboard">
            <Button size="lg" variant="outline-dark">
              Go to dashboard
            </Button>
          </Link>
          <Link href="/">
            <Button size="lg" variant="ghost-dark">
              Go home
            </Button>
          </Link>
        </div>
      </Container>
    </main>
  );
}
