import Link from "next/link";

import {
  Badge,
  Button,
  Container,
  LegacyTierBadge,
  Media,
} from "@/components/ui";

/** Demo preview content only — not live API metrics. */
const PROOF_POINTS = [
  "Verified attendee reviews",
  "Past event history",
  "Legacy tier progress",
  "Vault and memories",
  "Sponsor-ready proof",
] as const;

const STATS = [
  { label: "Events", value: "42" },
  { label: "Check-ins", value: "1.2k" },
  { label: "Rating", value: "4.8" },
] as const;

/** Editorial Legacy showcase — demo assets only. */
export function HomeLegacyShowcase() {
  return (
    <section className="bg-background py-12 sm:py-14">
      <Container className="grid items-center gap-8 lg:grid-cols-2 lg:gap-12 xl:gap-14">
        <div className="space-y-5">
          <div className="space-y-3">
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
              Legacy Page
            </p>
            <h2 className="max-w-xl text-balance text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl md:text-4xl">
              Every event should build your reputation.
            </h2>
            <p className="max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
              Pàdéyá turns checked-in tickets, verified reviews, past events,
              Vault drops, and event memories into a public Legacy Page that
              helps hosts earn trust long after the night ends.
            </p>
          </div>

          <ul className="grid gap-2 sm:grid-cols-2">
            {PROOF_POINTS.map((point) => (
              <li
                key={point}
                className="flex items-start gap-2.5 text-sm font-semibold text-foreground"
              >
                <span
                  aria-hidden
                  className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent"
                />
                {point}
              </li>
            ))}
          </ul>

          <div className="flex flex-col gap-3 pt-1 sm:flex-row sm:flex-wrap">
            <Link href="/@djmaze" className="w-full sm:w-auto">
              <Button size="lg" variant="dark" className="w-full sm:w-auto">
                View Legacy example
              </Button>
            </Link>
            <Link href="/host/onboarding" className="w-full sm:w-auto">
              <Button size="lg" variant="secondary" className="w-full sm:w-auto">
                Start building Legacy
              </Button>
            </Link>
          </div>
        </div>

        <article className="overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow)] dark:bg-surface-elevated">
          <div className="relative aspect-[16/9] overflow-hidden bg-ink">
            <Media
              src="/demo/hosts/djmaze-cover.svg"
              alt=""
              className="absolute inset-0 h-full w-full object-cover object-[center_20%]"
            />
            <div
              aria-hidden
              className="absolute inset-0 bg-gradient-to-t from-ink via-ink/30 to-transparent"
            />
            <div className="absolute left-4 top-4">
              <Badge tone="dark" size="sm">
                Example preview
              </Badge>
            </div>
            <div className="absolute bottom-3 left-4 right-4 flex flex-wrap gap-2">
              <Badge tone="accent" size="sm">
                Vault active
              </Badge>
              <Badge tone="outline" size="sm" className="border-paper/30 text-paper">
                Sponsor-ready
              </Badge>
            </div>
          </div>

          <div className="space-y-4 px-5 py-5 sm:px-6 sm:py-6">
            <div className="flex items-start gap-3.5">
              <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-full border-2 border-paper bg-ink shadow-[var(--shadow-soft)] ring-2 ring-accent/50 sm:h-16 sm:w-16">
                <Media
                  src="/demo/hosts/djmaze-avatar.svg"
                  alt=""
                  className="h-full w-full object-cover"
                />
              </div>
              <div className="min-w-0 flex-1 space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-xl font-extrabold tracking-tight text-foreground">
                    DJ Maze
                  </h3>
                  <Badge tone="accent" size="sm">
                    Verified
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  @djmaze · Lagos · Nightlife & music
                </p>
                <LegacyTierBadge tier="Certified" />
              </div>
            </div>

            <dl className="grid grid-cols-3 gap-2">
              {STATS.map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-[var(--radius-sm)] border border-border bg-muted/60 px-2.5 py-2.5 text-center"
                >
                  <dd className="text-base font-extrabold tabular-nums text-foreground">
                    {stat.value}
                  </dd>
                  <dt className="mt-0.5 text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
                    {stat.label}
                  </dt>
                </div>
              ))}
            </dl>

            <div className="rounded-[var(--radius-sm)] border border-border bg-muted/40 px-3.5 py-3">
              <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
                Next event
              </p>
              <p className="mt-1 text-sm font-semibold text-foreground">
                Afrobeats Night Live
              </p>
              <p className="text-sm text-muted-foreground">Fri, Jul 25 · 8:00 PM</p>
            </div>

            <figure className="rounded-[var(--radius-sm)] border border-dashed border-border px-3.5 py-3">
              <blockquote className="text-sm leading-relaxed text-foreground/90">
                “Door was tight, set was fire — checked in on Pàdéyá and the
                room felt legit.”
              </blockquote>
              <figcaption className="mt-2 text-[11px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
                Verified attendee review
              </figcaption>
            </figure>

            <Link href="/@djmaze" className="block">
              <Button className="w-full" variant="dark" size="lg">
                View Legacy Page
              </Button>
            </Link>
          </div>
        </article>
      </Container>

      <Container className="pt-8 sm:pt-10">
        <p className="max-w-3xl text-center text-sm font-semibold leading-relaxed text-muted-foreground sm:mx-auto sm:text-base">
          Hosts build Legacy. Fans build Passport history.{" "}
          <span className="text-foreground">Pàdéyá connects both.</span>
        </p>
      </Container>
    </section>
  );
}
