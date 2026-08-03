/**
 * Pure helpers for public /ambassadors CTA state + Overview labeling.
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
};

export type ProgramSignal = {
  status: string;
  scope?: string;
  scope_badge?: string;
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
