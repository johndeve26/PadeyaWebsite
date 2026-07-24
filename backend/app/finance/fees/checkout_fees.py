"""Apply configurable fees at checkout (server source of truth).

Discount order (default):
1. item subtotals
2. promo / merch discounts
3. buyer-paid service / platform fees (on post-discount merchandise)
4. buyer-paid processing fee (on post-discount merchandise + service fees)
5. final buyer total = merchandise_net + shipping + buyer fees

Host-paid fees never inflate the buyer total; they reduce host_net_estimate.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.finance.fees.constants import (
    FEE_KEY_BUYER_SERVICE,
    FEE_KEY_MERCH_COMMISSION,
    FEE_KEY_MERCH_FIXED,
    FEE_KEY_PAYMENT_PROCESSING,
    FEE_KEY_TICKET_COMMISSION,
    FEE_KEY_TICKET_FIXED,
    FEE_KEY_VAULT_COMMISSION,
    FEE_KEY_VAULT_FIXED,
)
from app.finance.fees.fee_calculation_service import FeeCalculationService
from app.finance.fees.money import apply_percentage, major_to_minor, minor_to_major, sum_minor
from app.finance.fees.schemas import CalculatedFeeLine, FeeBreakdown, ResolvedFeeSetting


def _q(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _compute_amount(
    base_minor: int,
    fee_type: str,
    percentage_value: Decimal | None,
    fixed_value: int | None,
) -> int:
    pct_part = 0
    fixed_part = 0
    if fee_type in {"percentage", "mixed"}:
        pct_part = apply_percentage(base_minor, percentage_value)
    if fee_type in {"fixed", "mixed"}:
        fixed_part = int(fixed_value or 0)
    return sum_minor(pct_part, fixed_part)


def _line_from_setting(
    setting: ResolvedFeeSetting,
    *,
    amount_minor: int,
) -> CalculatedFeeLine:
    return CalculatedFeeLine(
        fee_key=setting.fee_key,
        label=setting.label,
        category=setting.category,
        fee_type=setting.fee_type,
        percentage_value=setting.percentage_value,
        fixed_value=setting.fixed_value,
        payer=setting.payer,
        amount_minor=amount_minor,
        currency=setting.currency or "NGN",
        source=setting.source,
    )


@dataclass(frozen=True)
class CheckoutFeeResult:
    """Major-unit money totals for order persistence + API."""

    merchandise_net: Decimal
    shipping_amount: Decimal
    buyer_fee_total: Decimal
    host_fee_total: Decimal
    processing_fee_total: Decimal
    platform_revenue_total: Decimal
    host_net_estimate: Decimal
    final_total: Decimal
    breakdown: FeeBreakdown
    buyer_lines: list[CalculatedFeeLine]
    host_lines: list[CalculatedFeeLine]


def calculate_checkout_fees(
    db: Session,
    *,
    host_id: UUID,
    ticket_subtotal: Decimal,
    merch_subtotal: Decimal,
    ticket_discount: Decimal = Decimal("0"),
    merch_discount: Decimal = Decimal("0"),
    shipping_amount: Decimal = Decimal("0"),
    currency: str = "NGN",
    # When True (default), zero merchandise net → skip buyer service/processing
    # entirely (percentage and fixed), unless waive_buyer_fees_when_free is False.
    waive_buyer_fees_when_free: bool = True,
) -> CheckoutFeeResult:
    """Compute fees after discounts; return buyer total and host net estimate."""
    ticket_net = _q(max(Decimal("0"), Decimal(ticket_subtotal) - Decimal(ticket_discount)))
    merch_net = _q(max(Decimal("0"), Decimal(merch_subtotal) - Decimal(merch_discount)))
    shipping = _q(Decimal(shipping_amount or 0))
    merchandise_net = _q(ticket_net + merch_net)

    ticket_minor = major_to_minor(ticket_net, currency=currency)
    merch_minor = major_to_minor(merch_net, currency=currency)
    merchandise_minor = major_to_minor(merchandise_net, currency=currency)
    shipping_minor = major_to_minor(shipping, currency=currency)

    calc = FeeCalculationService(db)
    settings = {
        s.fee_key: s
        for s in calc.get_active_fee_settings(
            host_id,
            category=None,
            fee_keys=[
                FEE_KEY_TICKET_COMMISSION,
                FEE_KEY_TICKET_FIXED,
                FEE_KEY_MERCH_COMMISSION,
                FEE_KEY_MERCH_FIXED,
                FEE_KEY_BUYER_SERVICE,
                FEE_KEY_PAYMENT_PROCESSING,
            ],
        )
    }

    lines: list[CalculatedFeeLine] = []

    # Host commissions / fixed fees by product line
    for key, base in (
        (FEE_KEY_TICKET_COMMISSION, ticket_minor),
        (FEE_KEY_TICKET_FIXED, ticket_minor),
        (FEE_KEY_MERCH_COMMISSION, merch_minor),
        (FEE_KEY_MERCH_FIXED, merch_minor),
    ):
        setting = settings.get(key)
        if setting is None or not setting.enabled:
            continue
        # Fixed-only fees still apply on a zero line base (host cost of sale);
        # percentage of zero is zero.
        amount = _compute_amount(
            base,
            setting.fee_type,
            setting.percentage_value,
            setting.fixed_value,
        )
        if amount == 0 and setting.fee_type == "percentage":
            continue
        if amount == 0 and setting.fee_type == "mixed" and base == 0:
            # Only the fixed portion would apply; still compute.
            amount = _compute_amount(
                base, setting.fee_type, setting.percentage_value, setting.fixed_value
            )
        if amount == 0 and setting.fixed_value in (None, 0):
            continue
        lines.append(_line_from_setting(setting, amount_minor=amount))

    free_merchandise = merchandise_minor == 0
    skip_buyer = free_merchandise and waive_buyer_fees_when_free

    buyer_service_minor = 0
    if not skip_buyer:
        service = settings.get(FEE_KEY_BUYER_SERVICE)
        if service is not None and service.enabled:
            buyer_service_minor = _compute_amount(
                merchandise_minor,
                service.fee_type,
                service.percentage_value,
                service.fixed_value,
            )
            if buyer_service_minor > 0 or (
                service.fixed_value and service.fixed_value > 0 and merchandise_minor > 0
            ):
                if buyer_service_minor > 0:
                    lines.append(
                        _line_from_setting(service, amount_minor=buyer_service_minor)
                    )

    processing_minor = 0
    if not skip_buyer:
        processing = settings.get(FEE_KEY_PAYMENT_PROCESSING)
        if processing is not None and processing.enabled:
            # Processing base = merchandise + buyer service (before shipping),
            # matching "service then processing" order.
            proc_base = sum_minor(merchandise_minor, buyer_service_minor)
            processing_minor = _compute_amount(
                proc_base,
                processing.fee_type,
                processing.percentage_value,
                processing.fixed_value,
            )
            if processing_minor > 0:
                lines.append(
                    _line_from_setting(processing, amount_minor=processing_minor)
                )

    buyer_fees = 0
    host_fees = 0
    platform_absorbed = 0
    for line in lines:
        if line.payer == "buyer":
            buyer_fees = sum_minor(buyer_fees, line.amount_minor)
        elif line.payer == "host":
            host_fees = sum_minor(host_fees, line.amount_minor)
        else:
            platform_absorbed = sum_minor(platform_absorbed, line.amount_minor)

    # Buyer pays merchandise + shipping + buyer-paid fees only.
    final_minor = sum_minor(merchandise_minor, shipping_minor, buyer_fees)
    # Host earns merchandise + shipping − host fees (buyer fees stay with platform).
    host_net_minor = sum_minor(merchandise_minor, shipping_minor, -host_fees)
    if host_net_minor < 0:
        host_net_minor = 0
    platform_revenue_minor = sum_minor(host_fees, buyer_fees)

    breakdown = FeeBreakdown(
        currency=currency,
        base_amount_minor=merchandise_minor,
        lines=lines,
        buyer_fees_minor=buyer_fees,
        host_fees_minor=host_fees,
        platform_absorbed_minor=platform_absorbed,
        buyer_total_minor=final_minor,
        host_net_minor=host_net_minor,
    )

    return CheckoutFeeResult(
        merchandise_net=merchandise_net,
        shipping_amount=shipping,
        buyer_fee_total=_q(minor_to_major(buyer_fees, currency=currency)),
        host_fee_total=_q(minor_to_major(host_fees, currency=currency)),
        processing_fee_total=_q(minor_to_major(processing_minor, currency=currency)),
        platform_revenue_total=_q(
            minor_to_major(platform_revenue_minor, currency=currency)
        ),
        host_net_estimate=_q(minor_to_major(host_net_minor, currency=currency)),
        final_total=_q(minor_to_major(final_minor, currency=currency)),
        breakdown=breakdown,
        buyer_lines=[line for line in lines if line.payer == "buyer"],
        host_lines=[line for line in lines if line.payer == "host"],
    )


def calculate_vault_checkout_fees(
    db: Session,
    *,
    host_id: UUID,
    vault_subtotal: Decimal,
    currency: str = "NGN",
    waive_buyer_fees_when_free: bool = True,
) -> CheckoutFeeResult:
    """Vault unlock fees — same discount/fee ordering on a single line."""
    calc = FeeCalculationService(db)
    vault_net = _q(max(Decimal("0"), Decimal(vault_subtotal)))
    vault_minor = major_to_minor(vault_net, currency=currency)

    settings = {
        s.fee_key: s
        for s in calc.get_active_fee_settings(
            host_id,
            category=None,
            fee_keys=[
                FEE_KEY_VAULT_COMMISSION,
                FEE_KEY_VAULT_FIXED,
                FEE_KEY_BUYER_SERVICE,
                FEE_KEY_PAYMENT_PROCESSING,
            ],
        )
    }
    lines: list[CalculatedFeeLine] = []

    for key in (FEE_KEY_VAULT_COMMISSION, FEE_KEY_VAULT_FIXED):
        setting = settings.get(key)
        if setting is None or not setting.enabled:
            continue
        amount = _compute_amount(
            vault_minor, setting.fee_type, setting.percentage_value, setting.fixed_value
        )
        if amount == 0 and setting.fixed_value in (None, 0):
            continue
        lines.append(_line_from_setting(setting, amount_minor=amount))

    skip_buyer = vault_minor == 0 and waive_buyer_fees_when_free
    buyer_service_minor = 0
    if not skip_buyer:
        service = settings.get(FEE_KEY_BUYER_SERVICE)
        if service is not None and service.enabled:
            buyer_service_minor = _compute_amount(
                vault_minor, service.fee_type, service.percentage_value, service.fixed_value
            )
            if buyer_service_minor > 0:
                lines.append(_line_from_setting(service, amount_minor=buyer_service_minor))

    processing_minor = 0
    if not skip_buyer:
        processing = settings.get(FEE_KEY_PAYMENT_PROCESSING)
        if processing is not None and processing.enabled:
            proc_base = sum_minor(vault_minor, buyer_service_minor)
            processing_minor = _compute_amount(
                proc_base,
                processing.fee_type,
                processing.percentage_value,
                processing.fixed_value,
            )
            if processing_minor > 0:
                lines.append(
                    _line_from_setting(processing, amount_minor=processing_minor)
                )

    buyer_fees = sum(
        (line.amount_minor for line in lines if line.payer == "buyer"), start=0
    )
    host_fees = sum((line.amount_minor for line in lines if line.payer == "host"), start=0)
    platform_absorbed = sum(
        (line.amount_minor for line in lines if line.payer == "platform"), start=0
    )
    final_minor = sum_minor(vault_minor, buyer_fees)
    host_net_minor = max(0, sum_minor(vault_minor, -host_fees))
    platform_revenue_minor = sum_minor(host_fees, buyer_fees)

    breakdown = FeeBreakdown(
        currency=currency,
        base_amount_minor=vault_minor,
        lines=lines,
        buyer_fees_minor=buyer_fees,
        host_fees_minor=host_fees,
        platform_absorbed_minor=platform_absorbed,
        buyer_total_minor=final_minor,
        host_net_minor=host_net_minor,
    )
    return CheckoutFeeResult(
        merchandise_net=vault_net,
        shipping_amount=Decimal("0.00"),
        buyer_fee_total=_q(minor_to_major(buyer_fees, currency=currency)),
        host_fee_total=_q(minor_to_major(host_fees, currency=currency)),
        processing_fee_total=_q(minor_to_major(processing_minor, currency=currency)),
        platform_revenue_total=_q(
            minor_to_major(platform_revenue_minor, currency=currency)
        ),
        host_net_estimate=_q(minor_to_major(host_net_minor, currency=currency)),
        final_total=_q(minor_to_major(final_minor, currency=currency)),
        breakdown=breakdown,
        buyer_lines=[line for line in lines if line.payer == "buyer"],
        host_lines=[line for line in lines if line.payer == "host"],
    )


def persist_order_fee_result(
    db: Session,
    *,
    order_id: UUID,
    host_id: UUID,
    result: CheckoutFeeResult,
) -> None:
    FeeCalculationService(db).create_order_fee_snapshot(
        order_id, result.breakdown, host_id=host_id
    )


def buyer_facing_fee_breakdown(result: CheckoutFeeResult) -> list[dict]:
    """Public breakdown — buyer-paid lines only (no host commercial terms)."""
    rows: list[dict] = []
    for line in result.buyer_lines:
        rows.append(
            {
                "fee_key": line.fee_key,
                "label": line.label,
                "payer": line.payer,
                "amount": _q(minor_to_major(line.amount_minor, currency=line.currency)),
                "currency": line.currency,
            }
        )
    return rows
