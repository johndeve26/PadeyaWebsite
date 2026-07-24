import Link from "next/link";

import { Badge, Button, Container, Media } from "@/components/ui";

const PASSPORT_STATS = [
  { label: "Attended", value: "18" },
  { label: "Hosts", value: "7" },
  { label: "Badges", value: "5" },
] as const;

const BADGES = ["Checked in", "Weekend regular", "VIP night"] as const;

/** Fan loyalty storytelling — demo preview content only. */
export function HomeLoyalty() {
  return (
    <section className="relative overflow-hidden bg-ink py-12 text-paper sm:py-14">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,color-mix(in_srgb,var(--primary)_14%,transparent),transparent_45%),radial-gradient(circle_at_85%_70%,color-mix(in_srgb,var(--primary)_8%,transparent),transparent_40%)]"
      />
      <Container className="relative space-y-7">
        <div className="max-w-2xl space-y-3">
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-primary">
            Fan loyalty
          </p>
          <h2 className="text-balance text-2xl font-extrabold tracking-tight sm:text-3xl md:text-4xl">
            Turn attendees into fans who come back.
          </h2>
          <p className="text-base leading-relaxed text-paper/75 sm:text-lg">
            Fan Passport, Vault access, badges, follows, and ticket-holder
            content help fans keep a history with the hosts they love — not just
            a receipt from one night.
          </p>
          <p className="text-sm font-semibold text-paper/70">
            Every checked-in ticket strengthens the host’s Legacy and the fan’s
            Passport.
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-12 lg:gap-5">
          {/* Fan Passport preview */}
          <article className="flex flex-col overflow-hidden rounded-[var(--radius-xl)] border border-paper/10 bg-card text-foreground shadow-[var(--shadow)] dark:bg-surface-elevated lg:col-span-5">
            <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted-foreground">
                Fan Passport
              </p>
              <Badge tone="accent" size="sm">
                Example
              </Badge>
            </div>
            <div className="flex flex-1 flex-col gap-4 px-5 py-5">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-ink text-sm font-extrabold text-accent">
                  AO
                </div>
                <div className="min-w-0">
                  <p className="truncate font-extrabold text-foreground">
                    Ada Okoro
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Favorite host · DJ Maze
                  </p>
                </div>
              </div>

              <dl className="grid grid-cols-3 gap-2">
                {PASSPORT_STATS.map((stat) => (
                  <div
                    key={stat.label}
                    className="rounded-[var(--radius-sm)] bg-muted px-2 py-2.5 text-center"
                  >
                    <dd className="text-base font-extrabold tabular-nums">
                      {stat.value}
                    </dd>
                    <dt className="text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground">
                      {stat.label}
                    </dt>
                  </div>
                ))}
              </dl>

              <div className="space-y-2">
                <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
                  Recent check-in
                </p>
                <p className="text-sm font-semibold text-foreground">
                  Afrobeats Night Live · Lagos
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                {BADGES.map((badge) => (
                  <Badge key={badge} tone="outline" size="sm">
                    {badge}
                  </Badge>
                ))}
                <Badge tone="accent" size="sm">
                  Vault unlock
                </Badge>
              </div>

              <p className="text-sm leading-relaxed text-muted-foreground">
                Fans keep a record of events attended, hosts followed, badges
                earned, and VIP moments unlocked.
              </p>

              <div className="mt-auto pt-1">
                <Link href="/register" className="block">
                  <Button size="md" variant="dark" className="w-full">
                    Create account
                  </Button>
                </Link>
              </div>
            </div>
          </article>

          {/* Vault preview */}
          <article className="flex flex-col overflow-hidden rounded-[var(--radius-xl)] border border-paper/12 bg-[color-mix(in_srgb,var(--surface-dark)_72%,var(--ink))] lg:col-span-4">
            <div className="relative aspect-[16/10] overflow-hidden bg-ink">
              <Media
                src="/demo/hosts/djmaze-cover.svg"
                alt=""
                className="absolute inset-0 h-full w-full object-cover opacity-70"
              />
              <div
                aria-hidden
                className="absolute inset-0 bg-gradient-to-t from-ink via-ink/50 to-transparent"
              />
              <div className="absolute left-4 top-4 flex flex-wrap gap-2">
                <Badge tone="accent" size="sm">
                  Unlocked
                </Badge>
                <Badge tone="dark" size="sm">
                  Ticket-holder
                </Badge>
              </div>
              <div className="absolute bottom-4 left-4 right-4">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-accent">
                  Vault Access
                </p>
                <p className="mt-1 text-lg font-extrabold tracking-tight">
                  Exclusive host content fans unlock
                </p>
              </div>
            </div>
            <div className="flex flex-1 flex-col gap-3 px-5 py-5">
              <p className="text-sm leading-relaxed text-subtle-foreground">
                Hosts can reward followers, ticket holders, VIPs, and checked-in
                attendees with exclusive drops and early access.
              </p>
              <ul className="space-y-2 text-sm text-subtle-foreground">
                <li className="flex items-center justify-between gap-3 rounded-[var(--radius-sm)] border border-paper/10 px-3 py-2">
                  <span>Set recap drop</span>
                  <Badge tone="accent" size="sm">
                    Open
                  </Badge>
                </li>
                <li className="flex items-center justify-between gap-3 rounded-[var(--radius-sm)] border border-paper/10 px-3 py-2">
                  <span>VIP early access</span>
                  <Badge tone="outline" size="sm" className="border-paper/25 text-subtle-foreground">
                    Locked
                  </Badge>
                </li>
              </ul>
              <div className="mt-auto pt-1">
                <Link href="/@djmaze/vault" className="block">
                  <Button size="md" className="w-full">
                    Explore Vault
                  </Button>
                </Link>
              </div>
            </div>
          </article>

          {/* Badges / follow stack */}
          <div className="flex flex-col gap-4 lg:col-span-3">
            <article className="flex flex-1 flex-col rounded-[var(--radius-xl)] border border-paper/12 bg-paper/5 p-5 backdrop-blur-sm">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-accent">
                Badges
              </p>
              <h3 className="mt-2 text-lg font-extrabold tracking-tight">
                Badges that mean something
              </h3>
              <p className="mt-2 flex-1 text-sm leading-relaxed text-subtle-foreground">
                Badges come from real actions — buying tickets, checking in,
                attending repeatedly, and supporting hosts.
              </p>
              <Link href="/dashboard/badges" className="mt-4 block">
                <Button size="md" variant="outline-dark" className="w-full">
                  See badges
                </Button>
              </Link>
            </article>

            <article className="flex flex-1 flex-col rounded-[var(--radius-xl)] border border-accent/35 bg-[linear-gradient(160deg,color-mix(in_srgb,var(--primary)_16%,transparent),transparent_55%)] p-5">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-accent">
                Followed hosts
              </p>
              <h3 className="mt-2 text-lg font-extrabold tracking-tight">
                Stay close after the night
              </h3>
              <p className="mt-2 flex-1 text-sm leading-relaxed text-subtle-foreground">
                Follow hosts for upcoming events, Vault drops, and Legacy updates
                — without hunting for scattered links.
              </p>
              <Link href="/hosts" className="mt-4 block">
                <Button size="md" variant="outline-dark" className="w-full">
                  Follow hosts
                </Button>
              </Link>
            </article>
          </div>
        </div>
      </Container>
    </section>
  );
}
