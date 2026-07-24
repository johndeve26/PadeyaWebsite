/** Admin user flag catalog — keep in sync with backend `app.users.flag_constants`. */

export const USER_FLAG_TYPES = [
  "suspicious_payment_activity",
  "refund_abuse",
  "ticket_resale_risk",
  "chargeback_risk",
  "spam",
  "harassment",
  "fake_profile",
  "impersonation_risk",
  "event_safety_risk",
  "fraud_review",
  "policy_violation",
  "under_review",
  "trusted_user",
  "vip_support",
  "manual_watchlist",
] as const;

export type UserFlagType = (typeof USER_FLAG_TYPES)[number];

export const USER_FLAG_TYPE_LABELS: Record<UserFlagType, string> = {
  suspicious_payment_activity: "Suspicious payment activity",
  refund_abuse: "Refund abuse",
  ticket_resale_risk: "Ticket resale risk",
  chargeback_risk: "Chargeback risk",
  spam: "Spam",
  harassment: "Harassment",
  fake_profile: "Fake profile",
  impersonation_risk: "Impersonation risk",
  event_safety_risk: "Event safety risk",
  fraud_review: "Fraud review",
  policy_violation: "Policy violation",
  under_review: "Under review",
  trusted_user: "Trusted user",
  vip_support: "VIP support",
  manual_watchlist: "Manual watchlist",
};

export const USER_FLAG_SEVERITIES = [
  "low",
  "medium",
  "high",
  "critical",
] as const;

export type UserFlagSeverity = (typeof USER_FLAG_SEVERITIES)[number];

export const USER_FLAG_STATUSES = ["active", "resolved", "dismissed"] as const;

export type UserFlagStatus = (typeof USER_FLAG_STATUSES)[number];
