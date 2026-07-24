"use client";

import Link from "next/link";

import { Button, Container, Logo } from "@/components/ui";
import { brand } from "@/lib/brand";

/** Friendly state when an event listing is gone but the route still exists. */
export function EventUnavailableState({
  description = "This event is no longer available on Pàdéyá. It may have ended, been unpublished, or removed by the host.",
}: {
  description?: string;
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
          Event
        </p>
        <h1 className="mt-3 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">
          This event is no longer available
        </h1>
        <p className="mx-auto mt-4 max-w-md text-base leading-relaxed text-paper/70">
          {description}
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link href="/events">
            <Button size="lg">Explore events</Button>
          </Link>
          <Link href="/hosts">
            <Button
              size="lg"
              variant="secondary"
              className="border-paper/20 bg-paper/5 text-paper hover:bg-paper/10"
            >
              Explore hosts
            </Button>
          </Link>
          <Link href="/">
            <Button size="lg" variant="ghost" className="text-paper/80">
              Go home
            </Button>
          </Link>
        </div>
      </Container>
    </main>
  );
}
