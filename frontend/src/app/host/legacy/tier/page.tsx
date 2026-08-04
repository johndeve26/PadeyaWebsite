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
import { track } from "@/lib/analytics";
import { TrackedAction } from "@/lib/analytics-taxonomy";
import { ApiError } from "@/lib/api";
import { formatDate, formatDateTime, formatPercent } from "@/lib/format";
import { fetchMyTierProgress } from "@/lib/legacy-api";
import { legacyBandLabel, nextTierProgressCopy } from "@/lib/legacy-trust";
import type { TierProgress } from "@/lib/types/legacy";

export default function HostLegacyTierPage() {
  const [progress, setProgress] = useState<TierProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAllReqs, setShowAllReqs] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchMyTierProgress();
        if (active) {
          setProgress(data);
          track(TrackedAction.HOST_LEGACY_DASHBOARD_VIEW, {
            metadata: {
              tier_key: data.current_tier?.slug ?? undefined,
              provisional: data.is_provisional ?? false,
              location: "host_dashboard",
            },
          });
        }
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

  const nextCopy = nextTierProgressCopy(progress?.next_tier_summary);
  const exactScore = progress
    ? Number(progress.composite_score).toFixed(2)
    : null;
  const displayScore =
    progress?.display_score ??
    (progress ? Math.round(Number(progress.composite_score)) : null);
  const contributions = progress?.factor_contributions ?? [];
  const contributionTotal = contributions.reduce(
    (sum, row) => sum + Number(row.contribution),
    0,
  );
  const unmet = progress?.next_tier_summary?.unmet_requirements ?? [];
  const visibleUnmet = showAllReqs ? unmet : unmet.slice(0, 3);

  return (
    <LegacyStudioShell
      title="Tier progress"
      description="Legacy Score and tier from verified hosting activity. Owner self-actions are excluded."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/legacy">
            <Button size="sm" variant="ghost">
              How Legacy works
            </Button>
          </Link>
          <Link href="/host/reviews">
            <Button size="sm" variant="ghost">
              Reviews
            </Button>
          </Link>
        </div>
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
                    Legacy overview
                  </p>
                  <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
                    {progress.current_tier?.name ?? "New Host"}
                  </h2>
                  <div className="flex flex-wrap items-center gap-2">
                    {progress.current_tier?.slug ? (
                      <LegacyTierBadge tier={progress.current_tier.slug} />
                    ) : (
                      <LegacyTierBadge tier="new_host" />
                    )}
                    {progress.is_provisional ? (
                      <Badge tone="outline" className="border-paper/25 text-paper/80">
                        Provisional
                      </Badge>
                    ) : null}
                  </div>
                  <p className="text-base text-subtle-foreground">
                    Legacy Score{" "}
                    <span className="font-bold text-paper">
                      {exactScore} / 100
                    </span>
                    {displayScore != null ? (
                      <span className="text-paper/70">
                        {" "}
                        (public {displayScore})
                      </span>
                    ) : null}
                  </p>
                  {progress.last_recalculated_at ? (
                    <p className="text-sm text-subtle-foreground">
                      Last recalculated {formatDateTime(progress.last_recalculated_at)}
                    </p>
                  ) : null}
                </div>
                <div className="rounded-[var(--radius-lg)] border border-paper/15 bg-paper/5 px-4 py-3 text-right">
                  <p className="text-xs font-bold uppercase tracking-[0.12em] text-subtle-foreground">
                    Next tier
                  </p>
                  <p className="mt-1 text-xl font-extrabold">
                    {progress.is_top_tier
                      ? "Highest tier"
                      : (progress.next_tier?.name ?? "Max tier reached")}
                  </p>
                </div>
              </div>

              {!progress.is_top_tier ? (
                <div>
                  <div className="mb-2 flex justify-between text-sm">
                    <span className="text-subtle-foreground">Score progress</span>
                    <span className="font-bold text-accent">
                      {formatPercent(progress.progress_percentage)}
                    </span>
                  </div>
                  <div
                    className="h-3 overflow-hidden rounded-full bg-paper/10"
                    role="progressbar"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={Math.min(
                      100,
                      Number(progress.progress_percentage),
                    )}
                    aria-label="Score progress toward next tier"
                  >
                    <div
                      className="h-full rounded-full bg-accent transition-all motion-reduce:transition-none"
                      style={{
                        width: `${Math.min(100, Number(progress.progress_percentage))}%`,
                      }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-subtle-foreground">
                    Score progress and tier requirements are separate.
                  </p>
                </div>
              ) : (
                <p className="text-sm text-subtle-foreground">
                  You currently meet Pàdéyá’s highest configured Legacy requirements.
                  Maintain verified quality, consistency and responsible event operations.
                </p>
              )}
            </div>
          </section>

          {nextCopy && !progress.is_top_tier ? (
            <Card className="space-y-3">
              <h3 className="text-lg font-extrabold text-foreground">
                Next-tier progress
              </h3>
              <p className="text-sm font-bold text-heading">{nextCopy.title}</p>
              <p className="text-sm text-body">{nextCopy.body}</p>
              {visibleUnmet.length > 0 ? (
                <ul className="space-y-1.5 text-sm text-body">
                  {visibleUnmet.map((req) => (
                    <li key={req.key} className="flex gap-2">
                      <span aria-hidden className="text-primary">
                        •
                      </span>
                      <span>{req.message || req.label}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
              {unmet.length > 3 ? (
                <button
                  type="button"
                  className="text-sm font-semibold text-primary underline-offset-2 hover:underline"
                  onClick={() => {
                    setShowAllReqs((v) => !v);
                    track(TrackedAction.HOST_LEGACY_REQUIREMENTS_VIEW, {
                      metadata: { location: "host_dashboard" },
                    });
                  }}
                >
                  {showAllReqs ? "Show fewer requirements" : "View all requirements"}
                </button>
              ) : null}
            </Card>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2">
            <Card className="space-y-3">
              <h3 className="text-lg font-extrabold text-foreground">
                Requirements met
              </h3>
              {progress.requirements_met.length === 0 ? (
                <EmptyState
                  title="No requirements met yet"
                  description="Complete events and earn verified reviews to unlock the next tier."
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
            <h3 className="text-lg font-extrabold text-foreground">How to improve</h3>
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
            <p className="text-sm text-muted-foreground">
              Legacy is based on eligible verified activity. Owner self-actions are
              excluded. This protects the credibility of the score.
            </p>
          </Card>

          <Card className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-lg font-extrabold text-foreground">
                Factor breakdown
              </h3>
              <button
                type="button"
                className="text-sm font-semibold text-primary"
                onClick={() =>
                  track(TrackedAction.HOST_LEGACY_FACTOR_EXPAND, {
                    metadata: { location: "host_dashboard" },
                  })
                }
              >
                Authoritative contributions
              </button>
            </div>
            {contributions.length > 0 ? (
              <>
                <div className="hidden overflow-x-auto md:block">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead>
                      <tr className="border-b border-border text-muted-foreground">
                        <th className="py-2 pr-3 font-semibold">Factor</th>
                        <th className="py-2 pr-3 font-semibold">Score</th>
                        <th className="py-2 pr-3 font-semibold">Weight</th>
                        <th className="py-2 pr-3 font-semibold">Contribution</th>
                        <th className="py-2 font-semibold">What counts</th>
                      </tr>
                    </thead>
                    <tbody>
                      {contributions.map((row) => (
                        <tr key={row.key} className="border-b border-border/70">
                          <td className="py-2.5 pr-3 font-medium text-foreground">
                            {row.label}
                          </td>
                          <td className="py-2.5 pr-3 tabular-nums">
                            {row.normalized.toFixed(0)} / 100
                          </td>
                          <td className="py-2.5 pr-3 tabular-nums">
                            {row.weight_percent}%
                          </td>
                          <td className="py-2.5 pr-3 font-bold tabular-nums">
                            {row.contribution.toFixed(2)}
                          </td>
                          <td className="py-2.5 text-muted-foreground">
                            {row.raw_progress || row.what_counts}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr>
                        <td className="pt-3 font-bold" colSpan={3}>
                          Total
                        </td>
                        <td className="pt-3 font-extrabold tabular-nums">
                          {contributionTotal.toFixed(2)}
                        </td>
                        <td />
                      </tr>
                    </tfoot>
                  </table>
                </div>
                <div className="space-y-3 md:hidden">
                  {contributions.map((row) => (
                    <div
                      key={row.key}
                      className="rounded-[var(--radius-md)] border border-border px-3 py-3"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-bold text-foreground">{row.label}</p>
                        <p className="tabular-nums font-extrabold">
                          {row.contribution.toFixed(2)}
                        </p>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">
                        {row.normalized.toFixed(0)} / 100 · {row.weight_percent}% weight
                      </p>
                      <p className="mt-1 text-sm text-body">
                        {row.raw_progress || row.what_counts}
                      </p>
                    </div>
                  ))}
                  <p className="text-sm font-bold">
                    Total {contributionTotal.toFixed(2)}
                  </p>
                </div>
              </>
            ) : (
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
            )}
            {(progress.factor_bands?.length ?? 0) > 0 ? (
              <ul className="grid gap-2 sm:grid-cols-2">
                {progress.factor_bands!.map((band) => (
                  <li
                    key={band.key}
                    className="flex items-center justify-between rounded-[var(--radius-md)] bg-surface-muted px-3 py-2 text-sm"
                  >
                    <span>{band.label}</span>
                    <span className="font-bold">{legacyBandLabel(band.band)}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </Card>

          <Card className="space-y-3">
            <h3 className="text-lg font-extrabold text-foreground">Tier history</h3>
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
                        {Number(row.composite_score).toFixed(2)}
                      </p>
                      <p>{formatDate(row.created_at)}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      ) : null}
    </LegacyStudioShell>
  );
}
