"""Admin user flag catalog — types, severity, and lifecycle statuses."""

from __future__ import annotations

# Active = open moderation concern. Soft-close only (no hard delete).
FLAG_STATUS_ACTIVE = "active"
FLAG_STATUS_RESOLVED = "resolved"
FLAG_STATUS_DISMISSED = "dismissed"
FLAG_STATUSES = frozenset(
    {FLAG_STATUS_ACTIVE, FLAG_STATUS_RESOLVED, FLAG_STATUS_DISMISSED}
)

FLAG_SEVERITY_LOW = "low"
FLAG_SEVERITY_MEDIUM = "medium"
FLAG_SEVERITY_HIGH = "high"
FLAG_SEVERITY_CRITICAL = "critical"
FLAG_SEVERITIES = frozenset(
    {
        FLAG_SEVERITY_LOW,
        FLAG_SEVERITY_MEDIUM,
        FLAG_SEVERITY_HIGH,
        FLAG_SEVERITY_CRITICAL,
    }
)

FLAG_TYPES: tuple[str, ...] = (
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
)
FLAG_TYPE_SET = frozenset(FLAG_TYPES)

# Human labels for admin UI / docs (optional consumers).
FLAG_TYPE_LABELS: dict[str, str] = {
    "suspicious_payment_activity": "Suspicious payment activity",
    "refund_abuse": "Refund abuse",
    "ticket_resale_risk": "Ticket resale risk",
    "chargeback_risk": "Chargeback risk",
    "spam": "Spam",
    "harassment": "Harassment",
    "fake_profile": "Fake profile",
    "impersonation_risk": "Impersonation risk",
    "event_safety_risk": "Event safety risk",
    "fraud_review": "Fraud review",
    "policy_violation": "Policy violation",
    "under_review": "Under review",
    "trusted_user": "Trusted user",
    "vip_support": "VIP support",
    "manual_watchlist": "Manual watchlist",
}
