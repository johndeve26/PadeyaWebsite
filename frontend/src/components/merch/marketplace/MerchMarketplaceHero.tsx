"use client";

import Link from "next/link";

import { Button, Container, Logo } from "@/components/ui";
import { brand } from "@/lib/brand";

const VALUE_CHIPS = [
  { label: "Event add-ons", href: "/merch?type=event_addon#catalog" },
  { label: "Host shops", href: "#host-shops" },
  { label: "Vault drops", href: "/merch/vault" },
] as const;

type Props = {
  catalogHref?: string;
};

export function MerchMarketplaceHero({ catalogHref = "#catalog" }: Props) {
  return (
    <section className="relative overflow-hidden bg-ink text-paper">
      <div
        aria-hidden
        className="padeya-hero-glow pointer-events-none absolute inset-0 opacity-90"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -right-24 top-0 h-72 w-72 rounded-full bg-primary/15 blur-3xl sm:h-[22rem] sm:w-[22rem]"
      />
      <Container className="relative z-[1] py-12 sm:py-16 md:py-20">
        <Logo
          variant="dark"
          priority
          height={44}
          href={undefined}
          className="padeya-hero-brand drop-shadow-[0_2px_24px_rgb(0_0_0_/0.55)]"
        />
        <p className="padeya-hero-brand mt-4 text-xs font-bold uppercase tracking-[0.2em] text-primary">
          Merch marketplace · {brand.name}
        </p>
        <div className="mt-3 max-w-3xl space-y-4 sm:space-y-5">
          <h1 className="padeya-hero-brand text-balance text-[1.75rem] font-extrabold leading-[1.12] tracking-tight [text-shadow:0_2px_28px_rgb(0_0_0_/_0.55)] sm:text-4xl md:text-5xl">
            Wear the memory.
          </h1>
          <p className="max-w-xl text-pretty text-base leading-relaxed text-paper/75 sm:text-lg">
            The {brand.name} merch marketplace — host shops, event add-ons,
            post-event drops, and Vault exclusives in one place. Shop the night,
            take it home.
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            {VALUE_CHIPS.map((chip) => (
              <Link
                key={chip.label}
                href={chip.href}
                className="rounded-full border border-paper/20 bg-paper/5 px-3 py-1.5 text-xs font-bold text-paper/90 transition hover:border-primary/50 hover:text-primary"
              >
                {chip.label}
              </Link>
            ))}
          </div>
          <div className="flex flex-col gap-3 pt-1 sm:flex-row sm:flex-wrap">
            <Link href={catalogHref} className="w-full sm:w-auto">
              <Button size="lg" className="padeya-btn-micro w-full sm:w-auto">
                Shop merch
              </Button>
            </Link>
            <Link href="/merch/drops" className="w-full sm:w-auto">
              <Button
                size="lg"
                variant="outline-dark"
                className="padeya-btn-micro w-full sm:w-auto"
              >
                Explore drops
              </Button>
            </Link>
            <Link href="/host/merchandise/new" className="w-full sm:w-auto">
              <Button
                size="lg"
                variant="ghost"
                className="padeya-btn-micro w-full text-paper hover:bg-paper/10 sm:w-auto"
              >
                Create merch
              </Button>
            </Link>
          </div>
        </div>
      </Container>
    </section>
  );
}
