"""Build public-safe pricing payload from enabled global fee settings."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.finance.fees.constants import (
    DEFAULT_FEE_CATEGORIES,
    DEFAULT_FEE_LABELS,
    DEFAULT_FEE_PAYERS,
    FEE_KEY_BUYER_SERVICE,
    FEE_KEY_MERCH_COMMISSION,
    FEE_KEY_MERCH_FIXED,
    FEE_KEY_PAYMENT_PROCESSING,
    FEE_KEY_REFUND,
    FEE_KEY_TICKET_COMMISSION,
    FEE_KEY_TICKET_FIXED,
    FEE_KEY_VAULT_COMMISSION,
    FEE_KEY_VAULT_FIXED,
)
from app.finance.fees.models import PlatformFeeSetting
from app.finance.fees.money import minor_to_major
from app.pricing.schemas import PublicPricingFeeRow, PublicPricingResponse

# Buyer-facing fees may publish rates on /pricing (also shown at checkout).
# Host commercial rates stay qualitative — exact values live in Host earnings.
PUBLIC_RATE_FEE_KEYS = frozenset(
    {
        FEE_KEY_BUYER_SERVICE,
        FEE_KEY_PAYMENT_PROCESSING,
        FEE_KEY_REFUND,
    }
)

PUBLIC_DESCRIPTIONS: dict[str, str] = {
    FEE_KEY_TICKET_COMMISSION: (
        "Commission on successful ticket sales, deducted from host earnings."
    ),
    FEE_KEY_TICKET_FIXED: (
        "Optional fixed fee per ticket sale, deducted from host earnings when configured."
    ),
    FEE_KEY_MERCH_COMMISSION: (
        "Commission on successful merch sales, deducted from host earnings."
    ),
    FEE_KEY_MERCH_FIXED: (
        "Optional fixed fee on merch sales, deducted from host earnings when configured."
    ),
    FEE_KEY_VAULT_COMMISSION: (
        "Commission on Vault unlocks, deducted from host earnings."
    ),
    FEE_KEY_VAULT_FIXED: (
        "Optional fixed fee on Vault unlocks, deducted from host earnings when configured."
    ),
    FEE_KEY_BUYER_SERVICE: (
        "Buyer platform / service fee paid by the buyer and shown before payment."
    ),
    FEE_KEY_PAYMENT_PROCESSING: (
        "Payment / fiat processing fee. Payer depends on configuration "
        "(often buyer; may be host or platform-absorbed)."
    ),
    FEE_KEY_REFUND: (
        "Refund handling fee when configured. Follows the Refund Policy on approved refunds."
    ),
}

APPEARS_AT: dict[str, list[str]] = {
    FEE_KEY_TICKET_COMMISSION: ["host_earnings", "admin_finance"],
    FEE_KEY_TICKET_FIXED: ["host_earnings", "admin_finance"],
    FEE_KEY_MERCH_COMMISSION: ["host_earnings", "admin_finance"],
    FEE_KEY_MERCH_FIXED: ["host_earnings", "admin_finance"],
    FEE_KEY_VAULT_COMMISSION: ["host_earnings", "admin_finance"],
    FEE_KEY_VAULT_FIXED: ["host_earnings", "admin_finance"],
    FEE_KEY_BUYER_SERVICE: ["checkout", "admin_finance"],
    FEE_KEY_PAYMENT_PROCESSING: ["checkout", "host_earnings", "admin_finance"],
    FEE_KEY_REFUND: ["checkout", "admin_finance"],
}

# Marketing category rows (always present, even with empty fee settings).
CATEGORY_SPECS: tuple[dict[str, object], ...] = (
    {
        "fee_key": "category_ticket_sales",
        "label": "Ticket sales",
        "category": "ticket",
        "payer": "host",
        "appears_at": ["host_earnings", "admin_finance"],
        "public_description": (
            "Pàdéyá may charge host commission and/or fixed fees on successful "
            "ticket sales. Deducted from host earnings — not added as a surprise "
            "buyer line for host commission."
        ),
        "related_keys": (FEE_KEY_TICKET_COMMISSION, FEE_KEY_TICKET_FIXED),
    },
    {
        "fee_key": "category_merch_sales",
        "label": "Merch sales",
        "category": "merch",
        "payer": "host",
        "appears_at": ["host_earnings", "admin_finance"],
        "public_description": (
            "Merch commissions and host-paid fixed fees are deducted from host "
            "earnings when merch sells."
        ),
        "related_keys": (FEE_KEY_MERCH_COMMISSION, FEE_KEY_MERCH_FIXED),
    },
    {
        "fee_key": "category_vault_sales",
        "label": "Vault sales",
        "category": "vault",
        "payer": "host",
        "appears_at": ["host_earnings", "admin_finance"],
        "public_description": (
            "Vault unlock commissions are deducted from host earnings when "
            "configured."
        ),
        "related_keys": (FEE_KEY_VAULT_COMMISSION, FEE_KEY_VAULT_FIXED),
    },
    {
        "fee_key": "category_buyer_service",
        "label": "Buyer platform / service fee",
        "category": "general",
        "payer": "buyer",
        "appears_at": ["checkout", "admin_finance"],
        "public_description": (
            "Buyer platform fee is paid by the buyer. It appears at checkout "
            "before payment and does not inflate host gross sales."
        ),
        "related_keys": (FEE_KEY_BUYER_SERVICE,),
    },
    {
        "fee_key": "category_payment_processing",
        "label": "Payment / fiat processing fee",
        "category": "payment",
        "payer": "buyer",
        "appears_at": ["checkout", "host_earnings", "admin_finance"],
        "public_description": (
            "Processing fees may apply depending on configuration. Buyer-paid "
            "lines show at checkout; host-paid lines reduce host net."
        ),
        "related_keys": (FEE_KEY_PAYMENT_PROCESSING,),
    },
    {
        "fee_key": "category_refund",
        "label": "Refund handling",
        "category": "refund",
        "payer": "buyer",
        "appears_at": ["checkout", "admin_finance"],
        "public_description": (
            "Refund handling follows the Refund Policy. Some partner or platform "
            "fees may be non-recoverable on reversal."
        ),
        "related_keys": (FEE_KEY_REFUND,),
    },
    {
        "fee_key": "category_high_volume",
        "label": "High-volume / custom host agreements",
        "category": "general",
        "payer": "host",
        "appears_at": ["host_earnings", "admin_finance"],
        "public_description": (
            "Festivals, venues, brands, schools, churches, communities, and "
            "high-volume hosts may receive custom rates. Custom terms appear in "
            "host finance tools when configured."
        ),
        "related_keys": (),
        "always_enabled": True,
    },
)

PUBLIC_NOTE = (
    "Fee settings are configurable by Pàdéyá admin and may differ by host, "
    "volume, product type, or commercial agreement. Exact host rates appear in "
    "Host earnings / finance — not as other hosts’ rates on this page. "
    "Order fee snapshots preserve the fee terms used at the time of sale."
)


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _now() -> datetime:
    return datetime.now(UTC)


def _is_effective(row: PlatformFeeSetting, at: datetime) -> bool:
    if not row.enabled:
        return False
    start = _aware(row.effective_from)
    if start > at:
        return False
    if row.effective_to is not None and _aware(row.effective_to) <= at:
        return False
    return True


def _q(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _format_display_rate(
    *,
    fee_type: str,
    percentage_value: Decimal | None,
    fixed_value_major: Decimal | None,
    currency: str,
) -> str | None:
    parts: list[str] = []
    if fee_type in {"percentage", "mixed"} and percentage_value is not None:
        parts.append(f"{_q(percentage_value)}%")
    if fee_type in {"fixed", "mixed"} and fixed_value_major is not None:
        if currency.upper() == "NGN":
            parts.append(f"₦{_q(fixed_value_major)}")
        else:
            parts.append(f"{_q(fixed_value_major)} {currency}")
    if not parts:
        return None
    return " + ".join(parts)


def _pick_active_globals(db: Session) -> dict[str, PlatformFeeSetting]:
    """Latest effective global setting per fee_key (no host overrides)."""
    at = _now()
    rows = list(
        db.scalars(
            select(PlatformFeeSetting).order_by(
                PlatformFeeSetting.fee_key.asc(),
                PlatformFeeSetting.effective_from.desc(),
            )
        ).all()
    )
    picked: dict[str, PlatformFeeSetting] = {}
    for row in rows:
        if row.fee_key in picked:
            continue
        if _is_effective(row, at):
            picked[row.fee_key] = row
    return picked


def _fee_row_from_setting(row: PlatformFeeSetting) -> PublicPricingFeeRow:
    rates_public = row.fee_key in PUBLIC_RATE_FEE_KEYS
    currency = row.currency or "NGN"
    fixed_major: Decimal | None = None
    if row.fixed_value is not None:
        fixed_major = _q(minor_to_major(int(row.fixed_value), currency=currency))

    percentage = row.percentage_value if rates_public else None
    fixed_out = fixed_major if rates_public else None
    display = (
        _format_display_rate(
            fee_type=row.fee_type,
            percentage_value=row.percentage_value,
            fixed_value_major=fixed_major,
            currency=currency,
        )
        if rates_public
        else "May vary"
    )

    return PublicPricingFeeRow(
        fee_key=row.fee_key,
        label=row.label or DEFAULT_FEE_LABELS.get(row.fee_key, row.fee_key),
        category=row.category
        or DEFAULT_FEE_CATEGORIES.get(row.fee_key, "general"),
        payer=row.payer or DEFAULT_FEE_PAYERS.get(row.fee_key, "host"),
        fee_type=row.fee_type,
        public_description=PUBLIC_DESCRIPTIONS.get(
            row.fee_key,
            "Configurable platform fee. Exact terms shown where they apply.",
        ),
        appears_at=list(APPEARS_AT.get(row.fee_key, ["admin_finance"])),
        configurable=True,
        may_vary_by_host=True,
        rates_public=rates_public,
        enabled=True,
        percentage_value=percentage,
        fixed_value_major=fixed_out,
        currency=currency,
        display_rate=display,
    )


def _fallback_fee_row(fee_key: str) -> PublicPricingFeeRow:
    payer = DEFAULT_FEE_PAYERS.get(fee_key, "host")
    rates_public = fee_key in PUBLIC_RATE_FEE_KEYS
    return PublicPricingFeeRow(
        fee_key=fee_key,
        label=DEFAULT_FEE_LABELS.get(fee_key, fee_key),
        category=DEFAULT_FEE_CATEGORIES.get(fee_key, "general"),
        payer=payer,
        fee_type=None,
        public_description=PUBLIC_DESCRIPTIONS.get(
            fee_key,
            "Configurable platform fee when enabled by Pàdéyá admin.",
        ),
        appears_at=list(APPEARS_AT.get(fee_key, ["admin_finance"])),
        configurable=True,
        may_vary_by_host=True,
        rates_public=rates_public,
        enabled=False,
        percentage_value=None,
        fixed_value_major=None,
        currency="NGN",
        display_rate="Configured when enabled" if rates_public else "May vary",
    )


def build_public_pricing(db: Session) -> PublicPricingResponse:
    active = _pick_active_globals(db)

    fee_keys_order = (
        FEE_KEY_TICKET_COMMISSION,
        FEE_KEY_TICKET_FIXED,
        FEE_KEY_MERCH_COMMISSION,
        FEE_KEY_MERCH_FIXED,
        FEE_KEY_VAULT_COMMISSION,
        FEE_KEY_VAULT_FIXED,
        FEE_KEY_BUYER_SERVICE,
        FEE_KEY_PAYMENT_PROCESSING,
        FEE_KEY_REFUND,
    )
    fees: list[PublicPricingFeeRow] = []
    for key in fee_keys_order:
        if key in active:
            fees.append(_fee_row_from_setting(active[key]))
        else:
            fees.append(_fallback_fee_row(key))

    categories: list[PublicPricingFeeRow] = []
    for spec in CATEGORY_SPECS:
        related = tuple(spec.get("related_keys") or ())  # type: ignore[arg-type]
        always = bool(spec.get("always_enabled"))
        related_active = [active[k] for k in related if k in active]
        enabled = always or bool(related_active)

        # Prefer buyer rate display from related buyer fee when public.
        display_rate = "May vary"
        percentage: Decimal | None = None
        fixed_major: Decimal | None = None
        currency = "NGN"
        fee_type: str | None = None
        rates_public = False
        for row in related_active:
            if row.fee_key in PUBLIC_RATE_FEE_KEYS:
                rates_public = True
                currency = row.currency or "NGN"
                fee_type = row.fee_type
                percentage = row.percentage_value
                if row.fixed_value is not None:
                    fixed_major = _q(
                        minor_to_major(int(row.fixed_value), currency=currency)
                    )
                display_rate = (
                    _format_display_rate(
                        fee_type=row.fee_type,
                        percentage_value=row.percentage_value,
                        fixed_value_major=fixed_major,
                        currency=currency,
                    )
                    or "Shown at checkout"
                )
                break
        if not related_active and not always:
            display_rate = "Configured when enabled"
        if always:
            display_rate = "Custom"

        categories.append(
            PublicPricingFeeRow(
                fee_key=str(spec["fee_key"]),
                label=str(spec["label"]),
                category=str(spec["category"]),
                payer=str(spec["payer"]),
                fee_type=fee_type,
                public_description=str(spec["public_description"]),
                appears_at=list(spec["appears_at"]),  # type: ignore[arg-type]
                configurable=True,
                may_vary_by_host=True,
                rates_public=rates_public,
                enabled=enabled,
                percentage_value=percentage if rates_public else None,
                fixed_value_major=fixed_major if rates_public else None,
                currency=currency,
                display_rate=display_rate,
            )
        )

    return PublicPricingResponse(
        currency="NGN",
        note=PUBLIC_NOTE,
        fees=fees,
        categories=categories,
    )
