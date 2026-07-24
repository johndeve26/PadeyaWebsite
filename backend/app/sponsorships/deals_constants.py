"""Sponsorship deal lifecycle constants."""

DEAL_STATUSES = frozenset(
    {
        "draft",
        "proposed",
        "accepted",
        "invoice_pending",
        "payment_pending",
        "paid",
        "active",
        "completed",
        "cancelled",
        "rejected",
        "expired",
    }
)

INVOICE_STATUSES = frozenset(
    {
        "draft",
        "issued",
        "payment_pending",
        "paid",
        "void",
        "overdue",
        "refunded",
    }
)

HOST_EDIT_STATUSES = frozenset({"draft", "proposed"})
SPONSOR_DECIDE_STATUSES = frozenset({"proposed"})
PAYABLE_INVOICE_STATUSES = frozenset({"issued", "payment_pending"})

PAYSTACK_REF_PREFIX = "PDY-SPN-"
