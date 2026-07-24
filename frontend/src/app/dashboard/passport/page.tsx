"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { MerchProofSection } from "@/components/passport/MerchProofSection";
import { PassportStampGrid } from "@/components/passport/PassportStampGrid";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { fetchMyPassport } from "@/lib/passport-api";
import type { FanPassport } from "@/lib/types/passport";

function PassportStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--radius-md)] border border-paper/10 bg-paper/5 px-3 py-4">
      <p className="text-2xl font-extrabold tracking-tight text-accent sm:text-3xl">
        {value}
      </p>
      <p className="mt-1 text-xs font-bold uppercase tracking-[0.12em] text-subtle-foreground">
        {label}
      </p>
    </div>
  );
}

export default function FanPassportPage() {
  const [passport, setPassport] = useState<FanPassport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchMyPassport();
        if (active) setPassport(data);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load passport");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Fan Passport"
      title={passport ? `${passport.display_name}'s Passport` : "Fan Passport"}
      description="Your nights out, stamped. Attendance counts checked-in tickets only."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/dashboard/passport/settings">
            <Button variant="secondary">Passport settings</Button>
          </Link>
          <Link href="/dashboard/badges">
            <Button variant="ghost">Badges</Button>
          </Link>
          <Link href="/dashboard/tickets">
            <Button variant="ghost">Tickets</Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Could not load passport">
          {error}
        </Alert>
      ) : null}
      {!passport && !error ? <SkeletonLoader lines={5} /> : null}

      {passport ? (
        <div className="space-y-6">
          <section className="relative overflow-hidden rounded-[var(--radius-xl)] bg-ink px-5 py-8 text-paper shadow-[var(--shadow-strong)] sm:px-8 sm:py-10">
            <div aria-hidden className="padeya-hero-glow pointer-events-none absolute inset-0" />
            <div className="relative space-y-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-3">
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent">
                    Pàdéyá Fan Passport
                  </p>
                  <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
                    {passport.display_name}
                  </h2>
                  <p className="text-sm text-subtle-foreground">
                    {passport.username ? `@${passport.username}` : "Set a username in settings"}
                    {" · "}
                    Visibility: {passport.visibility}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {passport.is_superfan ? <Badge tone="accent">Superfan</Badge> : null}
                    <Badge tone="outline" className="border-paper/25 text-subtle-foreground">
                      {passport.completion_score ?? 0}% complete
                    </Badge>
                    {passport.visibility !== "private" && passport.share_path ? (
                      <Link href={passport.share_path}>
                        <Badge tone="accent">View public Passport</Badge>
                      </Link>
                    ) : null}
                  </div>
                </div>
                <Link href="/events">
                  <Button size="lg">Find tonight’s events</Button>
                </Link>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <PassportStat
                  label="Events attended"
                  value={String(passport.events_attended)}
                />
                <PassportStat
                  label="Hosts followed"
                  value={String(passport.hosts_followed)}
                />
                <PassportStat
                  label="Badges"
                  value={String(passport.badges_earned.length)}
                />
                <PassportStat
                  label="Reviews"
                  value={String(passport.reviews_written ?? 0)}
                />
                <PassportStat
                  label="Vault unlocks"
                  value={String(passport.vault_unlocks)}
                />
                <PassportStat
                  label="VIP nights"
                  value={String(passport.vip_purchases)}
                />
                <PassportStat
                  label="Cities"
                  value={String(passport.cities_explored ?? 0)}
                />
                <PassportStat
                  label="Tickets bought"
                  value={String(passport.tickets_bought)}
                />
              </div>
            </div>
          </section>

          <Card className="space-y-6">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-lg font-extrabold text-foreground">
                Passport stamps
              </h3>
              <Link href="/dashboard/badges">
                <Button size="sm" variant="ghost">
                  View collection
                </Button>
              </Link>
            </div>
            <PassportStampGrid badges={passport.badges_earned} embedded />
            <MerchProofSection
              badges={passport.badges_earned}
              summaries={passport.merch_proof_summaries}
              showEmpty
              embedded
            />
          </Card>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card className="space-y-4">
              <h3 className="text-lg font-extrabold text-foreground">Host loyalty</h3>
              {passport.loyalty.length === 0 ? (
                <EmptyState
                  title="No loyalty records yet"
                  description="Buy tickets and check in to build loyalty with hosts."
                />
              ) : (
                <ul className="divide-y divide-border">
                  {passport.loyalty.map((l) => (
                    <li
                      key={l.host_id}
                      className="flex justify-between gap-3 py-3.5"
                    >
                      <div>
                        <Link
                          href={`/@${l.host_username}`}
                          className="text-base font-bold text-foreground underline-offset-2 hover:underline"
                        >
                          {l.host_display_name}
                        </Link>
                        <p className="text-sm text-muted-foreground">
                          {l.check_ins} check-ins · {l.tickets_bought} tickets
                          {l.is_superfan ? " · Superfan" : ""}
                        </p>
                      </div>
                      {l.follows_host ? <Badge tone="accent">Following</Badge> : null}
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card className="space-y-4">
              <h3 className="text-lg font-extrabold text-foreground">Vault access</h3>
              <p className="text-base text-muted-foreground">
                {passport.vault_summary.paid_unlocks} paid unlocks ·{" "}
                {passport.vault_summary.pending_unlocks} pending
              </p>
              {passport.vault_summary.unlocked_item_titles.length > 0 ? (
                <ul className="space-y-2">
                  {passport.vault_summary.unlocked_item_titles.map((t) => (
                    <li
                      key={t}
                      className="rounded-[var(--radius-md)] bg-surface-inset px-3 py-2 text-sm font-semibold text-foreground"
                    >
                      {t}
                    </li>
                  ))}
                </ul>
              ) : (
                <EmptyState
                  title="No Vault unlocks yet"
                  description="Vault exclusives appear here after you unlock them by follow, ticket, VIP, or purchase."
                />
              )}
              <Link href="/dashboard/vault">
                <Button size="sm" variant="secondary">
                  Open Vault library
                </Button>
              </Link>
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card className="space-y-4">
              <h3 className="text-lg font-extrabold text-foreground">
                Attended events
              </h3>
              {passport.attended_events.length === 0 ? (
                <EmptyState
                  title="No checked-in events yet"
                  description="Refunded tickets do not count toward attendance."
                />
              ) : (
                <ul className="divide-y divide-border">
                  {passport.attended_events.map((e) => (
                    <li key={`${e.event_id}-${e.ticket_type_name}`} className="py-3.5">
                      <p className="text-base font-bold text-foreground">{e.title}</p>
                      <p className="text-sm text-muted-foreground">
                        {e.ticket_type_name}
                        {e.is_vip ? " · VIP" : ""} · {e.city || "—"}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card className="space-y-4">
              <h3 className="text-lg font-extrabold text-foreground">
                Upcoming tickets
              </h3>
              {passport.upcoming_tickets.length === 0 ? (
                <EmptyState
                  title="No upcoming tickets"
                  description="Browse events to grab your next night out."
                  action={
                    <Link href="/events">
                      <Button size="sm">Browse events</Button>
                    </Link>
                  }
                />
              ) : (
                <ul className="divide-y divide-border">
                  {passport.upcoming_tickets.map((e) => (
                    <li key={`${e.event_id}-up`} className="py-3.5">
                      <p className="text-base font-bold text-foreground">{e.title}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatDateTime(e.start_datetime)} · {e.ticket_type_name}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card className="space-y-2">
              <h3 className="text-lg font-extrabold text-foreground">
                Favorite categories
              </h3>
              <p className="text-base text-muted-foreground">
                {(passport.favorite_categories || []).length === 0
                  ? "Attend and check in to events to see your top categories."
                  : (passport.favorite_categories || []).join(" · ")}
              </p>
            </Card>
            <Card className="space-y-2">
              <h3 className="text-lg font-extrabold text-foreground">
                Favorite cities
              </h3>
              <p className="text-base text-muted-foreground">
                {(passport.favorite_cities || []).length === 0
                  ? "Checked-in nights in public cities appear here."
                  : (passport.favorite_cities || []).join(" · ")}
              </p>
            </Card>
          </div>

          <Card className="space-y-3">
            <h3 className="text-lg font-extrabold text-foreground">
              Followed hosts
            </h3>
            {passport.followed_hosts.length === 0 ? (
              <EmptyState
                title="No followed hosts yet"
                description="Follow hosts from Legacy Pages to keep their nights close."
                action={
                  <Link href="/hosts">
                    <Button size="sm">Browse hosts</Button>
                  </Link>
                }
              />
            ) : (
              <ul className="flex flex-wrap gap-2">
                {passport.followed_hosts.map((h) => (
                  <li key={h.host_id}>
                    <Link href={`/@${h.username}`}>
                      <Badge tone="outline">{h.display_name}</Badge>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      ) : null}
    </DashboardShell>
  );
}
