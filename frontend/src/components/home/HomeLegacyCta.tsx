import Link from "next/link";

import { Button, Container, SectionHeader } from "@/components/ui";

const POINTS = [
  "Public Legacy Page at /@username",
  "Upcoming events and Vault teasers",
  "Verified reviews from checked-in fans",
  "Sponsorship-ready host presence",
] as const;

/** Product Legacy CTA — no invented demo stats or fake event cards. */
export function HomeLegacyCta() {
  return (
    <section className="bg-muted py-10 sm:py-12">
      <Container>
        <div className="grid items-stretch gap-6 sm:gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:gap-10">
          <div className="flex flex-col justify-center space-y-5 sm:space-y-6">
            <SectionHeader
              variant="display"
              eyebrow="Host Legacy"
              title="A public page for hosts who keep showing up."
              description="Legacy Pages are where fans follow creators, see what’s next, and trust the history behind the night — not a disposable flyer."
            />

            <ul className="grid gap-2.5 sm:grid-cols-2 sm:gap-3">
              {POINTS.map((p) => (
                <li
                  key={p}
                  className="flex gap-2.5 rounded-[var(--radius-md)] border border-border/80 bg-card/80 px-3.5 py-3 text-sm text-foreground shadow-[var(--shadow-soft)] dark:bg-surface-elevated/90 sm:text-[0.95rem]"
                >
                  <span
                    className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-extrabold text-primary-text"
                    aria-hidden
                  >
                    ✓
                  </span>
                  <span className="leading-snug">{p}</span>
                </li>
              ))}
            </ul>

            <div className="flex flex-col gap-3 pt-0.5 sm:flex-row sm:flex-wrap">
              <Link href="/hosts" className="w-full sm:w-auto">
                <Button size="lg" className="w-full sm:w-auto">
                  Browse hosts
                </Button>
              </Link>
              <Link href="/host/legacy" className="w-full sm:w-auto">
                <Button
                  size="lg"
                  variant="secondary"
                  className="w-full sm:w-auto"
                >
                  Manage your Legacy
                </Button>
              </Link>
            </div>
          </div>

          <aside className="relative overflow-hidden rounded-[var(--radius-xl)] border border-ink bg-ink p-6 text-paper shadow-[var(--shadow)] sm:p-8 lg:flex lg:flex-col lg:justify-center">
            <div
              aria-hidden
              className="padeya-hero-glow pointer-events-none absolute inset-0 opacity-85"
            />
            <div
              aria-hidden
              className="padeya-grain pointer-events-none absolute inset-0 opacity-30"
            />
            <div
              aria-hidden
              className="pointer-events-none absolute -right-10 -top-12 h-40 w-40 rounded-full bg-primary/20 blur-3xl"
            />
            <div className="relative space-y-3 sm:space-y-4">
              <p className="inline-flex items-center gap-2.5 text-xs font-bold uppercase tracking-[0.18em] text-primary">
                <span
                  aria-hidden
                  className="inline-block h-[3px] w-6 shrink-0 rounded-[1px] bg-primary"
                />
                Why it matters
              </p>
              <p className="font-display text-2xl font-extrabold tracking-tight [text-shadow:0_2px_24px_rgb(0_0_0_/0.45)] sm:text-3xl">
                Reputation you can link.
              </p>
              <p className="max-w-md text-sm leading-relaxed text-paper/75 sm:text-base">
                Sponsors, collaborators, and fans land on one URL that shows real
                nights — with tools to grow Ambassadors, merch, and Vault around
                the same brand.
              </p>
            </div>
          </aside>
        </div>
      </Container>
    </section>
  );
}
