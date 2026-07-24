/** Account status + restriction codes — sync with backend account_status_constants. */

export const ACCOUNT_STATUSES = [
  "active",
  "under_review",
  "restricted",
  "suspended",
  "banned",
  "deleted",
] as const;

export type AccountStatus = (typeof ACCOUNT_STATUSES)[number];

export const ACCOUNT_STATUS_LABELS: Record<AccountStatus, string> = {
  active: "Active",
  under_review: "Under review",
  restricted: "Restricted",
  suspended: "Suspended",
  banned: "Banned",
  deleted: "Deleted",
};

/** Writable global status transitions (activity keys use POST/PATCH restrictions). */
export const ACCOUNT_STATUS_TRANSITIONS: Record<string, AccountStatus[]> = {
  active: ["under_review", "restricted", "suspended", "banned"],
  under_review: ["active", "restricted", "suspended", "banned"],
  restricted: ["active", "under_review", "suspended", "banned"],
  suspended: ["active"],
  banned: ["active"],
};

export const ACCOUNT_RESTRICTION_GROUPS = [
  {
    id: "personal",
    label: "Personal / buyer",
    codes: [
      "cannot_buy_tickets",
      "cannot_buy_merch",
      "cannot_checkout",
      "cannot_transfer_tickets",
      "cannot_request_refunds",
      "cannot_submit_reviews",
      "cannot_edit_passport",
      "cannot_use_vault",
    ],
  },
  {
    id: "community",
    label: "Community",
    codes: [
      "cannot_message",
      "cannot_use_fan_connect",
      "cannot_follow_hosts",
      "cannot_follow_fans",
      "cannot_report_users",
    ],
  },
  {
    id: "host",
    label: "Host",
    codes: [
      "cannot_create_events",
      "cannot_publish_events",
      "cannot_manage_events",
      "cannot_manage_tickets",
      "cannot_scan_tickets",
      "cannot_manage_merch",
      "cannot_fulfill_merch",
      "cannot_invite_host_team",
      "cannot_manage_sponsorships",
      "cannot_manage_host_ambassadors",
      "cannot_view_host_finance",
    ],
  },
  {
    id: "ambassador",
    label: "Ambassador",
    codes: [
      "cannot_join_ambassador_campaigns",
      "cannot_promote_events",
      "cannot_receive_ambassador_rewards",
      "cannot_request_ambassador_payouts",
    ],
  },
  {
    id: "account",
    label: "Account / security",
    codes: [
      "force_password_reset",
      "require_email_verification",
      "require_support_review",
      "read_only_account",
    ],
  },
  {
    id: "admin",
    label: "Admin / support",
    codes: ["cannot_access_admin", "cannot_access_support_tools"],
  },
] as const;

export const ACCOUNT_RESTRICTIONS = ACCOUNT_RESTRICTION_GROUPS.flatMap(
  (group) => [...group.codes],
) as unknown as readonly [
  "cannot_buy_tickets",
  "cannot_buy_merch",
  "cannot_checkout",
  "cannot_transfer_tickets",
  "cannot_request_refunds",
  "cannot_submit_reviews",
  "cannot_edit_passport",
  "cannot_use_vault",
  "cannot_message",
  "cannot_use_fan_connect",
  "cannot_follow_hosts",
  "cannot_follow_fans",
  "cannot_report_users",
  "cannot_create_events",
  "cannot_publish_events",
  "cannot_manage_events",
  "cannot_manage_tickets",
  "cannot_scan_tickets",
  "cannot_manage_merch",
  "cannot_fulfill_merch",
  "cannot_invite_host_team",
  "cannot_manage_sponsorships",
  "cannot_manage_host_ambassadors",
  "cannot_view_host_finance",
  "cannot_join_ambassador_campaigns",
  "cannot_promote_events",
  "cannot_receive_ambassador_rewards",
  "cannot_request_ambassador_payouts",
  "force_password_reset",
  "require_email_verification",
  "require_support_review",
  "read_only_account",
  "cannot_access_admin",
  "cannot_access_support_tools",
];

export type AccountRestriction = (typeof ACCOUNT_RESTRICTIONS)[number];

export const ACCOUNT_RESTRICTION_SET = new Set<string>(ACCOUNT_RESTRICTIONS);

export const ACCOUNT_RESTRICTION_LABELS: Record<AccountRestriction, string> = {
  cannot_buy_tickets: "Cannot buy tickets",
  cannot_buy_merch: "Cannot buy merch",
  cannot_checkout: "Cannot checkout",
  cannot_transfer_tickets: "Cannot transfer tickets",
  cannot_request_refunds: "Cannot request refunds",
  cannot_submit_reviews: "Cannot submit reviews",
  cannot_edit_passport: "Cannot edit passport",
  cannot_use_vault: "Cannot use Vault",
  cannot_message: "Cannot message",
  cannot_use_fan_connect: "Cannot use Fan Connect",
  cannot_follow_hosts: "Cannot follow hosts",
  cannot_follow_fans: "Cannot follow fans",
  cannot_report_users: "Cannot report users",
  cannot_create_events: "Cannot create events",
  cannot_publish_events: "Cannot publish events",
  cannot_manage_events: "Cannot manage events",
  cannot_manage_tickets: "Cannot manage tickets",
  cannot_scan_tickets: "Cannot scan tickets",
  cannot_manage_merch: "Cannot manage merch",
  cannot_fulfill_merch: "Cannot fulfill merch",
  cannot_invite_host_team: "Cannot invite host team",
  cannot_manage_sponsorships: "Cannot manage sponsorships",
  cannot_manage_host_ambassadors: "Cannot manage host ambassadors",
  cannot_view_host_finance: "Cannot view host finance",
  cannot_join_ambassador_campaigns: "Cannot join ambassador campaigns",
  cannot_promote_events: "Cannot promote events",
  cannot_receive_ambassador_rewards: "Cannot receive ambassador rewards",
  cannot_request_ambassador_payouts: "Cannot request ambassador payouts",
  force_password_reset: "Force password reset",
  require_email_verification: "Require email verification",
  require_support_review: "Require support review",
  read_only_account: "Read-only account",
  cannot_access_admin: "Cannot access admin",
  cannot_access_support_tools: "Cannot access support tools",
};

/** Legacy stored code → current catalog codes. */
const LEGACY_RESTRICTION_MAP: Record<string, AccountRestriction[]> = {
  cannot_promote_as_ambassador: ["cannot_join_ambassador_campaigns"],
};

/** All cannot_* activity codes + read_only_account (excludes force/require flags). */
export const FULL_SUSPENSION_RESTRICTIONS: AccountRestriction[] =
  ACCOUNT_RESTRICTIONS.filter(
    (code) =>
      code.startsWith("cannot_") || code === "read_only_account",
  );

export type RestrictionPresetId =
  | "messaging"
  | "buyer"
  | "host"
  | "ambassador"
  | "read_only"
  | "full_suspension";

export type RestrictionPreset = {
  id: RestrictionPresetId;
  label: string;
  description: string;
  codes: readonly AccountRestriction[];
  /** When true, save restrictions then set status=suspended. */
  alsoSuspend?: boolean;
};

export const RESTRICTION_PRESETS: readonly RestrictionPreset[] = [
  {
    id: "messaging",
    label: "Messaging",
    description: "Block messaging and Fan Connect.",
    codes: ["cannot_message", "cannot_use_fan_connect"],
  },
  {
    id: "buyer",
    label: "Buyer",
    description: "Block ticket/merch purchase and transfers.",
    codes: [
      "cannot_buy_tickets",
      "cannot_buy_merch",
      "cannot_checkout",
      "cannot_transfer_tickets",
    ],
  },
  {
    id: "host",
    label: "Host",
    description: "Block hosting, scanning, merch, and team ops.",
    codes: [
      "cannot_create_events",
      "cannot_publish_events",
      "cannot_manage_events",
      "cannot_scan_tickets",
      "cannot_manage_merch",
      "cannot_invite_host_team",
      "cannot_manage_sponsorships",
      "cannot_manage_host_ambassadors",
    ],
  },
  {
    id: "ambassador",
    label: "Ambassador",
    description: "Block campaigns, promos, rewards, and payouts.",
    codes: [
      "cannot_join_ambassador_campaigns",
      "cannot_promote_events",
      "cannot_receive_ambassador_rewards",
      "cannot_request_ambassador_payouts",
    ],
  },
  {
    id: "read_only",
    label: "Read-only account",
    description: "Block writes; viewing still allowed.",
    codes: ["read_only_account"],
  },
  {
    id: "full_suspension",
    label: "Emergency: full account block",
    description:
      "Emergency only — applies all major activity restrictions and suspends login. Prefer selective presets above.",
    codes: FULL_SUSPENSION_RESTRICTIONS,
    alsoSuspend: true,
  },
];

/** Normalize stored codes (legacy → current) and drop unknowns. */
export function normalizeAccountRestrictions(
  codes: readonly string[] | null | undefined,
): AccountRestriction[] {
  const out = new Set<AccountRestriction>();
  for (const raw of codes || []) {
    const mapped = LEGACY_RESTRICTION_MAP[raw];
    if (mapped) {
      for (const code of mapped) out.add(code);
      continue;
    }
    if (ACCOUNT_RESTRICTION_SET.has(raw)) {
      out.add(raw as AccountRestriction);
    }
  }
  return ACCOUNT_RESTRICTIONS.filter((code) => out.has(code));
}

export function restrictionLabel(code: string): string {
  if (code in ACCOUNT_RESTRICTION_LABELS) {
    return ACCOUNT_RESTRICTION_LABELS[code as AccountRestriction];
  }
  if (code === "cannot_promote_as_ambassador") {
    return ACCOUNT_RESTRICTION_LABELS.cannot_join_ambassador_campaigns;
  }
  return code.replaceAll("_", " ");
}

/** Merge preset codes onto the current draft (enable only — does not clear others). */
export function mergeRestrictionPreset(
  current: readonly string[],
  presetCodes: readonly AccountRestriction[],
): AccountRestriction[] {
  const set = new Set(normalizeAccountRestrictions(current));
  for (const code of presetCodes) set.add(code);
  return ACCOUNT_RESTRICTIONS.filter((code) => set.has(code));
}

/** Active keys from history rows and/or derived `account_restrictions`. */
export function activeRestrictionKeysFromDetail(detail: {
  account_restrictions?: readonly string[] | null;
  user_restrictions?: readonly {
    restriction_key: string;
    status: string;
  }[] | null;
  moderation?: {
    restrictions?: readonly string[] | null;
    user_restrictions?: readonly {
      restriction_key: string;
      status: string;
    }[] | null;
  } | null;
}): AccountRestriction[] {
  const history =
    detail.user_restrictions ?? detail.moderation?.user_restrictions ?? null;
  if (history && history.length > 0) {
    return normalizeAccountRestrictions(
      history
        .filter((row) => row.status === "active")
        .map((row) => row.restriction_key),
    );
  }
  if (detail.account_restrictions?.length) {
    return normalizeAccountRestrictions(detail.account_restrictions);
  }
  // Moderation.restrictions may mix codes and human labels — keep known codes only.
  return normalizeAccountRestrictions(detail.moderation?.restrictions ?? []);
}

export function restrictionHistoryRows(detail: {
  user_restrictions?: readonly {
    id: string;
    restriction_key: string;
    status: string;
    reason: string;
    internal_note?: string | null;
    starts_at: string;
    ends_at?: string | null;
    created_at: string;
    revoked_at?: string | null;
  }[] | null;
  moderation?: {
    user_restrictions?: readonly {
      id: string;
      restriction_key: string;
      status: string;
      reason: string;
      internal_note?: string | null;
      starts_at: string;
      ends_at?: string | null;
      created_at: string;
      revoked_at?: string | null;
    }[] | null;
  } | null;
}) {
  return (
    detail.user_restrictions ?? detail.moderation?.user_restrictions ?? []
  );
}

export function restrictionCategoryLabel(key: string): string {
  for (const group of ACCOUNT_RESTRICTION_GROUPS) {
    if ((group.codes as readonly string[]).includes(key)) return group.label;
  }
  return "Other";
}

/**
 * Display status for badges/copy:
 * - Suspended / Banned win
 * - Else any active restriction → Restricted
 * - Else Under review if applicable
 * - Else Active
 */
export function deriveDisplayAccountStatus(input: {
  accountStatus?: string | null;
  isActive?: boolean;
  underReview?: boolean;
  activeRestrictionCount?: number;
}): AccountStatus {
  const raw = (input.accountStatus || "").toLowerCase();
  if (raw === "banned" || raw === "deleted") {
    return raw as AccountStatus;
  }
  if (raw === "suspended" || input.isActive === false) {
    return "suspended";
  }
  const count = input.activeRestrictionCount;
  if (typeof count === "number") {
    if (count > 0) return "restricted";
  } else if (raw === "restricted") {
    return "restricted";
  }
  if (raw === "under_review" || input.underReview) {
    return "under_review";
  }
  return "active";
}

export type RestrictionDurationId =
  | "24h"
  | "7d"
  | "30d"
  | "indefinite"
  | "custom";

export const RESTRICTION_DURATION_OPTIONS: readonly {
  id: RestrictionDurationId;
  label: string;
}[] = [
  { id: "24h", label: "24 hours" },
  { id: "7d", label: "7 days" },
  { id: "30d", label: "30 days" },
  { id: "indefinite", label: "Indefinite" },
  { id: "custom", label: "Custom date" },
];

/** Resolve ends_at ISO string from duration UI (null = indefinite). */
export function endsAtFromDuration(
  id: RestrictionDurationId,
  customLocal?: string,
): string | null {
  if (id === "indefinite") return null;
  if (id === "custom") {
    const trimmed = customLocal?.trim();
    if (!trimmed) return null;
    const date = new Date(trimmed);
    return Number.isNaN(date.getTime()) ? null : date.toISOString();
  }
  const hours =
    id === "24h" ? 24 : id === "7d" ? 24 * 7 : id === "30d" ? 24 * 30 : 0;
  return new Date(Date.now() + hours * 60 * 60 * 1000).toISOString();
}

export function formatAdminActor(row: {
  created_by_admin_id: string;
  created_by_email?: string | null;
  created_by_name?: string | null;
}): string {
  if (row.created_by_name?.trim()) return row.created_by_name.trim();
  if (row.created_by_email?.trim()) return row.created_by_email.trim();
  const id = row.created_by_admin_id || "";
  return id ? `${id.slice(0, 8)}…` : "—";
}
