import Link from "next/link";

import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  SPONSORSHIP_HOSTS_PATH,
} from "@/lib/sponsor-marketplace-paths";

export function SponsorCTA({
  title = "Ready to shortlist verified hosts?",
  description = "Explore sponsor-ready creators, compare opportunities, and start with an inquiry.",
  primaryCta = { href: SPONSORSHIP_HOSTS_PATH, label: "Browse hosts" },
  secondaryCta = { href: "#open-slots", label: "View slots" },
  className = "",
}: {
  title?: string;
  description?: string;
  primaryCta?: { href: string; label: string };
  secondaryCta?: { href: string; label: string };
  className?: string;
}) {
  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-[var(--radius-xl)] border border-border bg-ink px-6 py-8 text-paper sm:px-8 sm:py-9",
        className,
      )}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-accent/70 to-transparent"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -right-16 top-0 h-40 w-40 rounded-full bg-accent/15 blur-3xl"
      />
      <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-xl space-y-2">
          <h2 className="text-2xl font-extrabold tracking-tight sm:text-[1.75rem]">
            {title}
          </h2>
          <p className="text-sm leading-relaxed text-subtle-foreground sm:text-base">
            {description}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link href={primaryCta.href}>
            <Button size="lg">{primaryCta.label}</Button>
          </Link>
          <Link href={secondaryCta.href}>
            <Button size="lg" variant="outline-dark">
              {secondaryCta.label}
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
}
