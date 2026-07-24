"use client";

import { Badge, SectionHeader } from "@/components/ui";
import type { FanBadge } from "@/lib/types/passport";

import { stampSourceForBadge } from "./badge-source";
import { PassportStampCard } from "./PassportStampCard";

type Props = {
  badges: FanBadge[];
  summaries?: string[];
  /** Show empty state (dashboard only). Public pages should hide when empty. */
  showEmpty?: boolean;
  /** Hide section chrome when nested in another card. */
  embedded?: boolean;
};

function parseHostsSupported(summaries: string[]): number | null {
  for (const line of summaries) {
    const m = line.match(/from (\d+) host/i);
    if (m) return Number(m[1]);
  }
  return null;
}

function parseDropsSupported(summaries: string[]): number | null {
  for (const line of summaries) {
    const m = line.match(/Supported (\d+) event merch drop/i);
    if (m) return Number(m[1]);
  }
  return null;
}

export function MerchProofSection({
  badges,
  summaries = [],
  showEmpty = false,
  embedded = false,
}: Props) {
  const merchBadges = badges.filter((b) => stampSourceForBadge(b) === "Merch");
  const hasProof = merchBadges.length > 0 || summaries.length > 0;

  if (!hasProof) {
    if (!showEmpty) return null;
    return (
      <section className="space-y-3">
        {embedded ? null : (
          <SectionHeader
            eyebrow="Merch"
            title="Merch collected"
            description="Merch proof is shown as badges and safe summaries only."
          />
        )}
        <p className="text-sm text-muted-foreground">
          Official merch support will appear here after verified purchases.
        </p>
      </section>
    );
  }

  const hosts = parseHostsSupported(summaries);
  const drops = parseDropsSupported(summaries);
  const latest = merchBadges[0] ?? null;

  return (
    <section className="space-y-4">
      {embedded ? null : (
        <SectionHeader
          eyebrow="Merch"
          title="Merch collected"
          description="Official event merch this fan has supported on Pàdéyá. Merch proof is shown as badges and safe summaries only."
        />
      )}
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-[var(--radius-lg)] border border-border bg-card px-4 py-4">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Merch stamps
          </p>
          <p className="mt-2 text-2xl font-extrabold text-foreground">
            {merchBadges.length}
          </p>
        </div>
        <div className="rounded-[var(--radius-lg)] border border-border bg-card px-4 py-4">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Hosts supported
          </p>
          <p className="mt-2 text-2xl font-extrabold text-foreground">
            {hosts ?? "—"}
          </p>
        </div>
        <div className="rounded-[var(--radius-lg)] border border-border bg-card px-4 py-4">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
            Event drops
          </p>
          <p className="mt-2 text-2xl font-extrabold text-foreground">
            {drops ?? "—"}
          </p>
        </div>
      </div>

      {latest ? (
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="accent" size="sm">
            Latest merch stamp
          </Badge>
          <span className="text-sm font-bold text-foreground">{latest.name}</span>
        </div>
      ) : null}

      {merchBadges.length > 0 ? (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {merchBadges.slice(0, 6).map((badge) => (
            <li key={badge.id}>
              <PassportStampCard badge={badge} emphasized />
            </li>
          ))}
        </ul>
      ) : null}

      {summaries.length > 0 ? (
        <ul className="space-y-1 text-sm text-muted-foreground">
          {summaries.map((line) => (
            <li key={line}>· {line}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
