"use client";

import Link from "next/link";
import { useEffect, useId, useState } from "react";

import { LegacyTierBadge } from "@/components/ui/LegacyTierBadge";
import { track } from "@/lib/analytics";
import { TrackedAction } from "@/lib/analytics-taxonomy";
import { cn } from "@/lib/cn";
import {
  legacyBandLabel,
  legacyScoreAriaLabel,
  nextTierProgressCopy,
  provisionalReasonLabel,
} from "@/lib/legacy-trust";
import type { LegacyTrustSummary } from "@/lib/types/legacy";

const BAND_TONE: Record<string, string> = {
  excellent: "text-primary",
  strong: "text-heading",
  good: "text-body",
  growing: "text-muted-foreground",
  building: "text-muted-foreground",
};

function ScoreBar({
  value,
  marker,
  label,
}: {
  value: number;
  marker?: number | null;
  label: string;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  const mark = marker != null ? Math.max(0, Math.min(100, marker)) : null;
  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
          {label}
        </p>
        <p className="text-sm font-semibold tabular-nums text-heading">
          {clamped} / 100
        </p>
      </div>
      <div
        className="relative h-2.5 overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={clamped}
        aria-label={label}
      >
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-500 motion-reduce:transition-none"
          style={{ width: `${clamped}%` }}
        />
        {mark != null ? (
          <span
            aria-hidden
            className="absolute top-1/2 h-4 w-0.5 -translate-y-1/2 bg-ink/70 dark:bg-paper/80"
            style={{ left: `${mark}%` }}
            title={`Next tier from ${mark}`}
          />
        ) : null}
      </div>
    </div>
  );
}

export function LegacyTrustSummaryCard({
  trust,
  location = "public_profile",
  className,
}: {
  trust: LegacyTrustSummary;
  location?: string;
  className?: string;
}) {
  const detailsId = useId();
  const [factorsOpen, setFactorsOpen] = useState(false);
  const [allReqsOpen, setAllReqsOpen] = useState(false);
  const tierName = trust.tier.name ?? trust.legacy_status;
  const nextCopy = nextTierProgressCopy(trust.next_tier);
  const howPath = trust.how_it_works_path || "/legacy";

  useEffect(() => {
    track(TrackedAction.LEGACY_SUMMARY_VIEW, {
      metadata: {
        tier_key: trust.tier.key ?? undefined,
        provisional: trust.is_provisional,
        location,
      },
    });
  }, [trust.tier.key, trust.is_provisional, location]);

  const visibleReqs = allReqsOpen
    ? trust.next_tier?.unmet_requirements ?? []
    : (trust.next_tier?.unmet_requirements ?? []).slice(0, 3);

  return (
    <section
      className={cn(
        "overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow-soft)] dark:bg-surface-elevated",
        className,
      )}
      aria-label={legacyScoreAriaLabel({
        displayScore: trust.display_score,
        tierName,
        provisional: trust.is_provisional,
      })}
    >
      <div className="space-y-5 p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-2">
            <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-muted-foreground">
              Pàdéyá Legacy
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <LegacyTierBadge tier={trust.tier.key || tierName} />
              {trust.is_provisional ? (
                <span className="inline-flex items-center rounded-full bg-muted px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground ring-1 ring-inset ring-border">
                  Provisional
                </span>
              ) : null}
            </div>
          </div>
          <Link
            href={howPath}
            className="text-sm font-semibold text-primary underline-offset-2 hover:underline"
            onClick={() =>
              track(TrackedAction.LEGACY_HOW_IT_WORKS_CLICK, {
                metadata: {
                  tier_key: trust.tier.key ?? undefined,
                  location,
                },
              })
            }
          >
            How Legacy works
          </Link>
        </div>

        <div className="space-y-1">
          <p className="text-sm font-semibold text-muted-foreground">Legacy Score</p>
          <p className="text-4xl font-extrabold tracking-tight text-heading tabular-nums sm:text-5xl">
            {trust.display_score}
            <span className="text-2xl font-bold text-muted-foreground"> / 100</span>
          </p>
          <p className="text-sm text-body">{trust.headline}</p>
          {trust.is_provisional ? (
            <p className="text-sm text-muted-foreground">
              This score may change more quickly as additional verified activity is
              recorded.
              {trust.provisional_reasons.length
                ? ` (${trust.provisional_reasons.map(provisionalReasonLabel).join("; ")})`
                : ""}
            </p>
          ) : null}
        </div>

        <ScoreBar
          value={trust.display_score}
          marker={
            trust.next_tier && !trust.is_top_tier
              ? Math.round(trust.next_tier.min_score)
              : null
          }
          label="Score progress"
        />

        {trust.evidence.length > 0 ? (
          <div>
            <p className="mb-3 text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
              Supporting proof
            </p>
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {trust.evidence.map((item) => (
                <div
                  key={item.key}
                  className="rounded-[var(--radius-md)] bg-surface-muted px-3 py-2.5 dark:bg-ink/40"
                >
                  <dt className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
                    {item.label}
                  </dt>
                  <dd className="mt-1 text-lg font-extrabold tabular-nums text-heading">
                    {item.display}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        ) : null}

        {trust.is_top_tier ? (
          <div className="rounded-[var(--radius-md)] border border-border bg-surface-muted px-4 py-3 dark:bg-ink/30">
            <p className="text-sm font-bold text-heading">Highest Legacy tier</p>
            <p className="mt-1 text-sm text-body">
              This host currently meets Pàdéyá’s highest configured Legacy requirements.
            </p>
          </div>
        ) : null}

        {!trust.is_top_tier && trust.next_tier && nextCopy ? (
          <div
            className="space-y-3 rounded-[var(--radius-md)] border border-border bg-surface-muted px-4 py-3 dark:bg-ink/30"
            onFocus={() =>
              track(TrackedAction.LEGACY_NEXT_TIER_VIEW, {
                metadata: {
                  tier_key: trust.next_tier?.key ?? undefined,
                  location,
                },
              })
            }
          >
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                Next-tier progress
              </p>
              <p className="mt-1 text-sm font-bold text-heading">{nextCopy.title}</p>
              <p className="mt-1 text-sm text-body">{nextCopy.body}</p>
            </div>
            {visibleReqs.length > 0 ? (
              <ul className="space-y-1.5 text-sm text-body">
                {visibleReqs.map((req) => (
                  <li key={req.key} className="flex gap-2">
                    <span aria-hidden className="text-primary">
                      •
                    </span>
                    <span>{req.message || req.label}</span>
                  </li>
                ))}
              </ul>
            ) : null}
            {(trust.next_tier.additional_requirements_count ?? 0) > 0 ||
            (trust.next_tier.unmet_requirements?.length ?? 0) > 3 ? (
              <button
                type="button"
                className="text-sm font-semibold text-primary underline-offset-2 hover:underline"
                onClick={() => setAllReqsOpen((v) => !v)}
              >
                {allReqsOpen ? "Show fewer requirements" : "View all requirements"}
              </button>
            ) : null}
            <p className="text-xs text-muted-foreground">
              Score progress and tier requirements are separate — score alone does not
              unlock the next tier.
            </p>
          </div>
        ) : null}

        {trust.factor_bands.length > 0 ? (
          <div>
            <button
              type="button"
              className="flex w-full items-center justify-between gap-3 text-left text-sm font-bold text-heading"
              aria-expanded={factorsOpen}
              aria-controls={detailsId}
              onClick={() => {
                const next = !factorsOpen;
                setFactorsOpen(next);
                if (next) {
                  track(TrackedAction.LEGACY_DETAILS_OPEN, {
                    metadata: {
                      tier_key: trust.tier.key ?? undefined,
                      location,
                    },
                  });
                }
              }}
            >
              What shapes this score?
              <span className="text-muted-foreground" aria-hidden>
                {factorsOpen ? "−" : "+"}
              </span>
            </button>
            {factorsOpen ? (
              <ul id={detailsId} className="mt-3 space-y-2">
                {trust.factor_bands.map((band) => (
                  <li
                    key={band.key}
                    className="flex items-center justify-between gap-3 border-b border-border/70 py-2 last:border-0"
                  >
                    <span className="text-sm text-body">{band.label}</span>
                    <span
                      className={cn(
                        "text-sm font-bold",
                        BAND_TONE[band.band] ?? "text-heading",
                      )}
                    >
                      {legacyBandLabel(band.band)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}

        {trust.last_recalculated_at ? (
          <p className="text-xs text-muted-foreground">
            Last updated{" "}
            <time dateTime={trust.last_recalculated_at}>
              {new Date(trust.last_recalculated_at).toLocaleDateString(undefined, {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </time>
          </p>
        ) : null}
      </div>
    </section>
  );
}
