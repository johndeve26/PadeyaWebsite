/**
 * Display-only Legacy trust helpers. Never recalculate composite scores here.
 */

import type {
  LegacyFactorBand,
  LegacyNextTierSummary,
  LegacyTrustSummary,
} from "@/lib/types/legacy";

const BAND_LABELS: Record<string, string> = {
  excellent: "Excellent",
  strong: "Strong",
  good: "Good",
  growing: "Growing",
  building: "Building history",
};

const PROVISIONAL_COPY: Record<string, string> = {
  limited_completed_events: "Fewer than 3 completed events",
  limited_verified_reviews: "Fewer than 5 verified reviews",
};

export function legacyBandLabel(band: string): string {
  return BAND_LABELS[band] ?? band;
}

export function provisionalReasonLabel(reason: string): string {
  return PROVISIONAL_COPY[reason] ?? "Limited verified history";
}

export function legacyScoreAriaLabel(opts: {
  displayScore: number;
  tierName: string;
  provisional?: boolean;
}): string {
  const base = `Legacy Score: ${opts.displayScore} out of 100. Current tier: ${opts.tierName}.`;
  return opts.provisional ? `${base} Provisional — building verified history.` : base;
}

export function nextTierProgressCopy(
  next: LegacyNextTierSummary | null | undefined,
): { title: string; body: string } | null {
  if (!next?.name) return null;

  if (next.state === "score_met_gates_remaining") {
    const remaining = next.gates_remaining;
    return {
      title: `Score requirement met`,
      body: `Your Legacy Score has reached the ${next.name} range. Meet ${remaining} remaining verified activity requirement${remaining === 1 ? "" : "s"} to unlock ${next.name}.`,
    };
  }

  if (next.score_requirement_met && next.gates_remaining === 0) {
    return {
      title: `${next.name} ready`,
      body: `Score and verified activity requirements for ${next.name} are met.`,
    };
  }

  const points = Math.max(0, Math.ceil(next.score_remaining));
  return {
    title:
      points > 0
        ? `${points} point${points === 1 ? "" : "s"} to ${next.name}`
        : `Activity requirements for ${next.name}`,
    body:
      points > 0
        ? `Score ${Math.round(Number(next.min_score) - Number(next.score_remaining))} / ${Math.round(next.min_score)}. Tier also requires verified activity gates.`
        : `${next.gates_remaining} verified activity requirement${next.gates_remaining === 1 ? "" : "s"} remaining.`,
  };
}

export function trustFromPageFallback(page: {
  composite_score?: string | number | null;
  legacy_status: string;
  tier?: { slug?: string; name?: string; description?: string | null; rank?: number } | null;
  stats: {
    completed_events?: number | null;
    tickets_sold: number;
    verified_checkins: number;
    average_verified_rating: string | number | null;
    review_count: number;
    followers: number;
    repeat_buyers_rate?: string | number | null;
  };
}): LegacyTrustSummary | null {
  if (page.composite_score == null) return null;
  const score = Number(page.composite_score);
  const display = Math.max(0, Math.min(100, Math.round(score)));
  return {
    score,
    display_score: display,
    tier: {
      key: page.tier?.slug ?? null,
      name: page.tier?.name ?? page.legacy_status,
      description: page.tier?.description ?? null,
      rank: page.tier?.rank ?? null,
    },
    legacy_status: page.legacy_status,
    is_provisional: false,
    provisional_reasons: [],
    headline: "Trusted and consistently verified",
    evidence: [],
    factor_bands: [],
    how_it_works_path: "/legacy",
  };
}

export function sortFactorBands(bands: LegacyFactorBand[]): LegacyFactorBand[] {
  return [...bands];
}
