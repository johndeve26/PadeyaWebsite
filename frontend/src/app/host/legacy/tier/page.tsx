"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { LegacyStudioShell } from "@/components/legacy/studio/LegacyStudioShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  LegacyTierBadge,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDate, formatPercent } from "@/lib/format";
import { fetchMyTierProgress } from "@/lib/legacy-api";
import type { TierProgress } from "@/lib/types/legacy";

export default function HostLegacyTierPage() {
  const [progress, setProgress] = useState<TierProgress | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchMyTierProgress();
        if (active) setProgress(data);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Unable to load tier progress");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <LegacyStudioShell
      title="Tier progress"
      description="Named Legacy tiers from verified ratings, completed events, tickets, and check-ins."
      actions={
        <Link href="/host/reviews">
          <Button size="sm" variant="ghost">
            Reviews
          </Button>
        </Link>
      }
    >
        {error ? (
          <Alert tone="danger" title="Could not load tier">
            {error}
          </Alert>
        ) : null}
        {!progress && !error ? <SkeletonLoader lines={5} /> : null}

        {progress ? (
          <div className="space-y-6">
            <section className="relative overflow-hidden rounded-[var(--radius-xl)] bg-ink px-5 py-8 text-paper shadow-[var(--shadow-strong)] sm:px-8 sm:py-10">
              <div aria-hidden className="padeya-hero-glow pointer-events-none absolute inset-0" />
              <div className="relative space-y-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="space-y-3">
                    <p className="text-xs font-bold uppercase tracking-[0.16em] text-accent">
                      Current tier
                    </p>
                    <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
                      {progress.current_tier?.name ?? "New Host"}
                    </h2>
                    {progress.current_tier?.slug ? (
                      <LegacyTierBadge tier={progress.current_tier.slug} />
                    ) : (
                      <LegacyTierBadge tier="new_host" />
                    )}
                    <p className="text-base text-subtle-foreground">
                      Score {Number(progress.composite_score).toFixed(1)} / 100
                    </p>
                  </div>
                  <div className="rounded-[var(--radius-lg)] border border-paper/15 bg-paper/5 px-4 py-3 text-right">
                    <p className="text-xs font-bold uppercase tracking-[0.12em] text-subtle-foreground">
                      Next tier
                    </p>
                    <p className="mt-1 text-xl font-extrabold">
                      {progress.next_tier?.name ?? "Max tier reached"}
                    </p>
                  </div>
                </div>
                <div>
                  <div className="mb-2 flex justify-between text-sm">
                    <span className="text-subtle-foreground">Progress to next tier</span>
                    <span className="font-bold text-accent">
                      {formatPercent(progress.progress_percentage)}
                    </span>
                  </div>
                  <div className="h-3 overflow-hidden rounded-full bg-paper/10">
                    <div
                      className="h-full rounded-full bg-accent transition-all"
                      style={{
                        width: `${Math.min(100, Number(progress.progress_percentage))}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            </section>

            <div className="grid gap-4 md:grid-cols-2">
              <Card className="space-y-3">
                <h3 className="text-lg font-extrabold text-foreground">
                  Requirements met
                </h3>
                {progress.requirements_met.length === 0 ? (
                  <EmptyState
                    title="No requirements met yet"
                    description="Complete events and earn reviews to unlock the next tier."
                  />
                ) : (
                  progress.requirements_met.map((item) => (
                    <div
                      key={item.key}
                      className="flex justify-between gap-3 text-sm sm:text-base"
                    >
                      <span className="text-foreground">{item.label}</span>
                      <Badge tone="accent">
                        {item.current}/{item.required}
                      </Badge>
                    </div>
                  ))
                )}
              </Card>
              <Card className="space-y-3">
                <h3 className="text-lg font-extrabold text-foreground">
                  Still needed
                </h3>
                {progress.requirements_remaining.length === 0 ? (
                  <EmptyState
                    title="All requirements cleared"
                    description="You have met every hard requirement for the next tier."
                  />
                ) : (
                  progress.requirements_remaining.map((item) => (
                    <div
                      key={item.key}
                      className="flex justify-between gap-3 text-sm sm:text-base"
                    >
                      <span>{item.label}</span>
                      <span className="font-semibold text-muted-foreground">
                        {item.current}/{item.required}
                      </span>
                    </div>
                  ))
                )}
              </Card>
            </div>

            <Card className="space-y-3 border-accent/40 bg-[linear-gradient(135deg,color-mix(in_srgb,var(--primary)_10%,transparent),transparent_55%)]">
              <h3 className="text-lg font-extrabold text-foreground">
                Suggested actions
              </h3>
              <ul className="space-y-2">
                {progress.suggested_actions.map((action) => (
                  <li
                    key={action}
                    className="flex gap-2 text-base text-muted-foreground"
                  >
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                    {action}
                  </li>
                ))}
              </ul>
            </Card>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card className="space-y-3">
                <h3 className="text-lg font-extrabold text-foreground">
                  Score factors
                </h3>
                <div className="grid gap-2 sm:grid-cols-2">
                  {Object.entries(progress.factor_scores).map(([key, value]) => (
                    <div
                      key={key}
                      className="flex justify-between rounded-[var(--radius-md)] bg-muted px-3 py-2 text-sm"
                    >
                      <span className="capitalize text-muted-foreground">
                        {key.replaceAll("_", " ")}
                      </span>
                      <span className="font-bold text-foreground">
                        {Number(value).toFixed(1)}
                      </span>
                    </div>
                  ))}
                </div>
              </Card>

              <Card className="space-y-3">
                <h3 className="text-lg font-extrabold text-foreground">
                  Tier history
                </h3>
                {progress.history.length === 0 ? (
                  <EmptyState
                    title="No tier history yet"
                    description="Tier changes appear here as your Legacy score grows."
                  />
                ) : (
                  <div className="space-y-2">
                    {progress.history.map((row) => (
                      <div
                        key={row.id}
                        className="flex flex-wrap items-center justify-between gap-2 border-b border-border py-2 text-sm last:border-0"
                      >
                        <div>
                          <p className="font-bold text-foreground">
                            {row.previous_tier_slug ?? "—"} → {row.tier_slug}
                          </p>
                          <p className="text-muted-foreground">{row.reason}</p>
                        </div>
                        <div className="text-right text-muted-foreground">
                          <p className="font-semibold">
                            {Number(row.composite_score).toFixed(1)}
                          </p>
                          <p>{formatDate(row.created_at)}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          </div>
        ) : null}
    </LegacyStudioShell>
  );
}
