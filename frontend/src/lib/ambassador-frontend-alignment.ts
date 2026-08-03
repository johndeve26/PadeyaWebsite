/**
 * Pure helpers for public /ambassadors CTA state + dual-commission copy checks.
 * Kept free of React so vitest can run without Testing Library.
 */

export type PublicEnrollmentState =
  | "signed_out"
  | "loading"
  | "not_enrolled"
  | "host_only"
  | "platform_only"
  | "both"
  | "inactive";

export type EnrollmentSignals = {
  enrollments_active: number;
  has_platform_enrollment?: boolean;
  has_host_enrollment?: boolean;
  scopes?: string[];
  primary_referral_link_path?: string | null;
};

export type ProgramSignal = {
  status: string;
  scope?: string;
  scope_badge?: string;
  referral_link_path?: string | null;
};

export function resolvePublicEnrollmentState(
  signedIn: boolean,
  authLoading: boolean,
  summary: EnrollmentSignals | null,
  programs: ProgramSignal[],
): PublicEnrollmentState {
  if (authLoading) return "loading";
  if (!signedIn) return "signed_out";
  if (!summary) return "not_enrolled";
  const active = programs.filter((p) => p.status === "active");
  const hasPlatform =
    Boolean(summary.has_platform_enrollment) ||
    active.some((p) => p.scope === "platform" || p.scope_badge === "Platform");
  const hasHost =
    Boolean(summary.has_host_enrollment) ||
    active.some((p) => p.scope !== "platform" && p.scope_badge !== "Platform");
  if (summary.enrollments_active <= 0 && active.length === 0) {
    return "not_enrolled";
  }
  if (active.length === 0 && summary.enrollments_active > 0) {
    return "inactive";
  }
  if (hasPlatform && hasHost) return "both";
  if (hasPlatform) return "platform_only";
  if (hasHost) return "host_only";
  return "not_enrolled";
}

/** Prefer backend-provided platform link — never invent from client username. */
export function resolveOwnPlatformLinkPath(
  summary: EnrollmentSignals | null,
  programs: ProgramSignal[],
): string | null {
  if (summary?.primary_referral_link_path) {
    return summary.primary_referral_link_path;
  }
  const platform = programs.find(
    (p) =>
      p.status === "active" &&
      (p.scope === "platform" || p.scope_badge === "Platform") &&
      p.referral_link_path,
  );
  return platform?.referral_link_path ?? null;
}

export function enrollmentScopeAnalytics(
  state: PublicEnrollmentState,
): "none" | "platform" | "host" | "both" | "inactive" | "signed_out" | "loading" {
  if (state === "signed_out") return "signed_out";
  if (state === "loading") return "loading";
  if (state === "not_enrolled") return "none";
  if (state === "platform_only") return "platform";
  if (state === "host_only") return "host";
  if (state === "both") return "both";
  return "inactive";
}

export function adminEnrollmentScopeLabel(programKind: string): string {
  return programKind === "platform_wide" ? "Pàdéyá-wide" : "Host campaign";
}

export function overviewArrangementHint(
  platformPrograms: number,
  hostCampaigns: number,
): string {
  return `${platformPrograms} Pàdéyá programs · ${hostCampaigns} host campaigns`;
}

export function overviewCommissionHint(
  hostFunded: string,
  platformFunded: string,
): string {
  return `${hostFunded} host-funded · ${platformFunded} Pàdéyá-funded`;
}

export function platformWideCoverageCopy(): string {
  return "By default across events and merch — no host opt-in required";
}

export function hostCampaignCoverageCopy(): string {
  return "Only after the host enables Ambassadors for that event";
}

/** Copy invariants for dual-commission landing — used by unit tests. */
export const DUAL_COMMISSION_COPY = {
  heroSupport:
    "Enrol in Pàdéyá-wide programs or partner with event hosts through eligible campaigns. Share your referral link, promote covered tickets and merchandise, and track host-funded and Pàdéyá-funded earnings from one connected dashboard.",
  heroDisclaimer:
    "Programs and campaigns apply only when you are actively enrolled and the purchase meets their eligibility rules. When both scopes apply, separate host-funded and Pàdéyá-funded earnings may be recorded.",
  dualEarningsTitle: "Fair and transparent earnings",
  dualEarningsSr:
    "An eligible purchase may create one host-funded earning and one separate Pàdéyá-funded earning when the same ambassador is enrolled in both eligible scopes.",
  usernameExample: "padeya.com/r/yourusername",
  settlementNote:
    "Pàdéyá-wide commission does not reduce the event host’s settlement.",
  hostEnrollmentRequired:
    "A live campaign alone does not create an earning. You must be enrolled.",
} as const;

const FORBIDDEN_SINGLE_WINNER_PHRASES = [
  "takes priority",
  "host campaign wins",
  "one winner",
  "only one referral commission",
  "only one commission",
  "fallback",
] as const;

export function assertNoSingleWinnerWording(text: string): boolean {
  const lower = text.toLowerCase();
  return !FORBIDDEN_SINGLE_WINNER_PHRASES.some((p) => lower.includes(p));
}
