"""Finance enumerations and policy catalog."""

REFUND_POLICY_TYPES = (
    "no_refunds",
    "refund_until_7_days_before",
    "refund_until_24_hours_before",
    "partial_refund_only",
    "cancelled_event_only",
    "admin_controlled",
    "custom",
)

DEFAULT_REFUND_POLICY = "admin_controlled"

REFUND_REQUEST_STATUSES = (
    "requested",
    "under_review",
    "approved",
    "rejected",
    "cancelled",
    "completed",
)

PAYOUT_STATUSES = (
    "requested",
    "under_review",
    "approved",
    "rejected",
    "paid",
    "cancelled",
)

LEDGER_ENTRY_TYPES = (
    "sale_credit",
    "refund_debit",
    "payout_hold",
    "payout_release",
    "payout_paid",
    "vault_sale",
    "adjustment",
)

# Append-only platform journal (separate from host `ledger_entries`).
PLATFORM_LEDGER_ENTRY_TYPES = (
    "buyer_payment",
    "ticket_revenue",
    "merch_revenue",
    "vault_revenue",
    "buyer_platform_fee",
    "host_commission",
    "processing_fee",
    "refund",
    "chargeback",
    "ambassador_reward",
    "host_payout",
    "adjustment",
)

PLATFORM_LEDGER_DIRECTIONS = ("debit", "credit")


LEDGER_DIRECTIONS = ("credit", "debit")
