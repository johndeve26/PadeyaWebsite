"""Fee catalog: keys, categories, payers, and types."""

from __future__ import annotations

FEE_CATEGORIES = (
    "ticket",
    "merch",
    "vault",
    "payment",
    "refund",
    "sponsorship",
    "general",
)

FEE_TYPES = ("percentage", "fixed", "mixed")

FEE_PAYERS = ("buyer", "host", "platform")

FEE_SOURCES = ("global", "host_override")

# Canonical fee keys for supported (and reserved) revenue streams.
FEE_KEY_TICKET_COMMISSION = "ticket_commission"
FEE_KEY_TICKET_FIXED = "ticket_fixed_fee"
FEE_KEY_BUYER_SERVICE = "buyer_service_fee"
FEE_KEY_MERCH_COMMISSION = "merch_commission"
FEE_KEY_MERCH_FIXED = "merch_fixed_fee"
FEE_KEY_VAULT_COMMISSION = "vault_commission"
FEE_KEY_VAULT_FIXED = "vault_fixed_fee"
FEE_KEY_PAYMENT_PROCESSING = "payment_processing_fee"
FEE_KEY_REFUND = "refund_fee"
FEE_KEY_SPONSORSHIP_MARKETPLACE = "sponsorship_marketplace_fee"

FEE_KEYS = (
    FEE_KEY_TICKET_COMMISSION,
    FEE_KEY_TICKET_FIXED,
    FEE_KEY_BUYER_SERVICE,
    FEE_KEY_MERCH_COMMISSION,
    FEE_KEY_MERCH_FIXED,
    FEE_KEY_VAULT_COMMISSION,
    FEE_KEY_VAULT_FIXED,
    FEE_KEY_PAYMENT_PROCESSING,
    FEE_KEY_REFUND,
    FEE_KEY_SPONSORSHIP_MARKETPLACE,
)

# Default payer by fee key (product invariants).
DEFAULT_FEE_PAYERS: dict[str, str] = {
    FEE_KEY_TICKET_COMMISSION: "host",
    FEE_KEY_TICKET_FIXED: "host",
    FEE_KEY_BUYER_SERVICE: "buyer",
    FEE_KEY_MERCH_COMMISSION: "host",
    FEE_KEY_MERCH_FIXED: "host",
    FEE_KEY_VAULT_COMMISSION: "host",
    FEE_KEY_VAULT_FIXED: "host",
    FEE_KEY_PAYMENT_PROCESSING: "buyer",
    FEE_KEY_REFUND: "buyer",
    FEE_KEY_SPONSORSHIP_MARKETPLACE: "host",
}

DEFAULT_FEE_CATEGORIES: dict[str, str] = {
    FEE_KEY_TICKET_COMMISSION: "ticket",
    FEE_KEY_TICKET_FIXED: "ticket",
    FEE_KEY_BUYER_SERVICE: "general",
    FEE_KEY_MERCH_COMMISSION: "merch",
    FEE_KEY_MERCH_FIXED: "merch",
    FEE_KEY_VAULT_COMMISSION: "vault",
    FEE_KEY_VAULT_FIXED: "vault",
    FEE_KEY_PAYMENT_PROCESSING: "payment",
    FEE_KEY_REFUND: "refund",
    FEE_KEY_SPONSORSHIP_MARKETPLACE: "sponsorship",
}

DEFAULT_FEE_LABELS: dict[str, str] = {
    FEE_KEY_TICKET_COMMISSION: "Ticket commission",
    FEE_KEY_TICKET_FIXED: "Ticket fixed fee",
    FEE_KEY_BUYER_SERVICE: "Buyer platform / service fee",
    FEE_KEY_MERCH_COMMISSION: "Merch commission",
    FEE_KEY_MERCH_FIXED: "Merch fixed fee",
    FEE_KEY_VAULT_COMMISSION: "Vault commission",
    FEE_KEY_VAULT_FIXED: "Vault fixed fee",
    FEE_KEY_PAYMENT_PROCESSING: "Payment / fiat processing fee",
    FEE_KEY_REFUND: "Refund fee",
    FEE_KEY_SPONSORSHIP_MARKETPLACE: "Sponsorship marketplace fee",
}

# Category → fee keys used when calculating that product line.
TICKET_FEE_KEYS = (
    FEE_KEY_TICKET_COMMISSION,
    FEE_KEY_TICKET_FIXED,
    FEE_KEY_BUYER_SERVICE,
    FEE_KEY_PAYMENT_PROCESSING,
)

MERCH_FEE_KEYS = (
    FEE_KEY_MERCH_COMMISSION,
    FEE_KEY_MERCH_FIXED,
    FEE_KEY_BUYER_SERVICE,
    FEE_KEY_PAYMENT_PROCESSING,
)

VAULT_FEE_KEYS = (
    FEE_KEY_VAULT_COMMISSION,
    FEE_KEY_VAULT_FIXED,
    FEE_KEY_BUYER_SERVICE,
    FEE_KEY_PAYMENT_PROCESSING,
)

# Ambassador payouts deduct from host net in a later phase; calculation APIs
# accept an optional ambassador_deduction_minor so callers stay aware.
AMBASSADOR_DEDUCTION_AWARE = True

PERMISSION_VIEW_FEES = "admin.finance.view_fees"
PERMISSION_MANAGE_FEES = "admin.finance.manage_fees"
PERMISSION_MANAGE_HOST_OVERRIDES = "admin.finance.manage_host_overrides"
