"""Ambassador commission calculation and refund reversal."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.promos.constants import (
    APPLIES_TO_MERCH,
    APPLIES_TO_TICKETS,
    APPLIES_TO_V1,
    CAMPAIGN_TYPE_EVENT_MERCH,
    COMMISSION_TYPE_FLAT,
    COMMISSION_TYPE_PERCENTAGE,
    COMMISSION_TYPE_REWARD_ONLY,
    COMMISSION_TYPES_V1,
    DEFAULT_HOLD_PERIOD_DAYS,
)
from app.promos.models import Ambassador, AmbassadorCampaign, AmbassadorSale


def _q(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def default_applies_to(campaign_type: str) -> str:
    if campaign_type == CAMPAIGN_TYPE_EVENT_MERCH:
        return APPLIES_TO_MERCH
    return APPLIES_TO_TICKETS


def normalize_commission_type(raw: str | None) -> str:
    value = (raw or COMMISSION_TYPE_PERCENTAGE).strip().lower()
    if value not in COMMISSION_TYPES_V1:
        raise ValueError(
            "commission_type must be percentage, flat, or reward_only"
        )
    return value


def normalize_applies_to(raw: str | None, *, campaign_type: str) -> str:
    if raw is None or not str(raw).strip():
        return default_applies_to(campaign_type)
    value = str(raw).strip().lower()
    if value not in APPLIES_TO_V1:
        raise ValueError(
            "applies_to must be tickets, merch, or tickets_and_merch"
        )
    return value


def resolve_commission_rules(
    campaign: AmbassadorCampaign | None,
    *,
    ambassador: Ambassador,
) -> dict:
    """Effective rules for a sale (campaign preferred, ambassador snapshot fallback)."""
    if campaign is not None:
        ctype = getattr(campaign, "commission_type", None) or COMMISSION_TYPE_PERCENTAGE
        value = getattr(campaign, "commission_value", None)
        if value is None:
            value = campaign.commission_percent
        applies = getattr(campaign, "applies_to", None) or default_applies_to(
            getattr(campaign, "campaign_type", "event_tickets")
        )
        hold_days = int(getattr(campaign, "hold_period_days", 7) or 7)
        max_cap = getattr(campaign, "max_commission_per_order", None)
        payout_min = getattr(campaign, "payout_minimum", None)
        free_after = getattr(campaign, "free_ticket_after_sales", None)
    else:
        ctype = COMMISSION_TYPE_PERCENTAGE
        value = ambassador.commission_rate_percent
        applies = APPLIES_TO_TICKETS
        hold_days = 7
        max_cap = None
        payout_min = None
        free_after = None
    return {
        "commission_type": ctype,
        "commission_value": Decimal(value or 0),
        "applies_to": applies,
        "hold_period_days": max(0, hold_days),
        "max_commission_per_order": (
            Decimal(max_cap) if max_cap is not None else None
        ),
        "payout_minimum": Decimal(payout_min) if payout_min is not None else None,
        "free_ticket_after_sales": free_after,
    }


def filter_units_and_revenue(
    *,
    applies_to: str,
    tickets_sold: int,
    merch_units: int,
    ticket_revenue: Decimal,
    merch_revenue: Decimal,
) -> tuple[int, int, Decimal, Decimal, Decimal]:
    """Return tickets, merch_units, ticket_rev, merch_rev, commissionable_revenue."""
    if applies_to == APPLIES_TO_TICKETS:
        return tickets_sold, 0, ticket_revenue, Decimal("0"), ticket_revenue
    if applies_to == APPLIES_TO_MERCH:
        return 0, merch_units, Decimal("0"), merch_revenue, merch_revenue
    # tickets_and_merch
    total = ticket_revenue + merch_revenue
    return tickets_sold, merch_units, ticket_revenue, merch_revenue, total


def compute_commission_owed(
    *,
    commission_type: str,
    commission_value: Decimal,
    applies_to: str,
    tickets_sold: int,
    merch_units: int,
    commissionable_revenue: Decimal,
    max_commission_per_order: Decimal | None,
) -> Decimal:
    if commission_type == COMMISSION_TYPE_REWARD_ONLY:
        owed = Decimal("0")
    elif commission_type == COMMISSION_TYPE_FLAT:
        if applies_to == APPLIES_TO_TICKETS:
            owed = Decimal(commission_value) * Decimal(tickets_sold)
        elif applies_to == APPLIES_TO_MERCH:
            # Flat per merch order (one credit if any merch units).
            owed = (
                Decimal(commission_value)
                if merch_units > 0
                else Decimal("0")
            )
        else:
            per_tickets = Decimal(commission_value) * Decimal(tickets_sold)
            per_merch_order = (
                Decimal(commission_value) if merch_units > 0 else Decimal("0")
            )
            owed = per_tickets + per_merch_order
    else:
        # percentage
        owed = commissionable_revenue * (
            Decimal(commission_value) / Decimal("100")
        )

    owed = _q(owed)
    if max_commission_per_order is not None:
        owed = min(owed, _q(Decimal(max_commission_per_order)))
    return owed


def hold_until_for_sale(*, hold_period_days: int, now: datetime | None = None) -> datetime:
    current = now or datetime.now(UTC)
    return current + timedelta(days=max(0, hold_period_days))


def resolve_campaign_commission_input(
    *,
    campaign_type: str,
    commission_type: str | None = None,
    commission_value: Decimal | None = None,
    commission_percent: Decimal | None = None,
    applies_to: str | None = None,
    hold_period_days: int | None = None,
    payout_minimum: Decimal | None = None,
    max_commission_per_order: Decimal | None = None,
    free_ticket_after_sales: int | None = None,
    leaderboard_reward_enabled: bool | None = None,
    leaderboard_reward_description: str | None = None,
) -> dict:
    """Normalize create/update commission fields; keeps commission_percent in sync."""
    ctype = normalize_commission_type(commission_type)
    applies = normalize_applies_to(applies_to, campaign_type=campaign_type)

    if ctype == COMMISSION_TYPE_REWARD_ONLY:
        value = Decimal("0")
        percent = Decimal("0")
    elif ctype == COMMISSION_TYPE_FLAT:
        if commission_value is None:
            raise ValueError("commission_value is required for flat commission")
        value = Decimal(commission_value)
        if value < 0:
            raise ValueError("commission_value must be >= 0")
        percent = Decimal("0")
    else:
        # percentage — prefer commission_value, fall back to legacy percent
        if commission_value is not None:
            value = Decimal(commission_value)
        elif commission_percent is not None:
            value = Decimal(commission_percent)
        else:
            value = Decimal("5.00")
        if value < 0 or value > 100:
            raise ValueError("percentage commission_value must be between 0 and 100")
        percent = value

    hold = (
        DEFAULT_HOLD_PERIOD_DAYS
        if hold_period_days is None
        else int(hold_period_days)
    )
    if hold < 0:
        raise ValueError("hold_period_days must be >= 0")

    if payout_minimum is not None and Decimal(payout_minimum) < 0:
        raise ValueError("payout_minimum must be >= 0")
    if max_commission_per_order is not None and Decimal(max_commission_per_order) < 0:
        raise ValueError("max_commission_per_order must be >= 0")
    if free_ticket_after_sales is not None and int(free_ticket_after_sales) < 1:
        raise ValueError("free_ticket_after_sales must be >= 1 when set")

    desc = None
    if leaderboard_reward_description is not None:
        desc = str(leaderboard_reward_description).strip()[:500] or None

    return {
        "commission_type": ctype,
        "commission_value": _q(value),
        "commission_percent": _q(percent),
        "applies_to": applies,
        "hold_period_days": hold,
        "payout_minimum": (
            _q(Decimal(payout_minimum)) if payout_minimum is not None else None
        ),
        "max_commission_per_order": (
            _q(Decimal(max_commission_per_order))
            if max_commission_per_order is not None
            else None
        ),
        "free_ticket_after_sales": (
            int(free_ticket_after_sales)
            if free_ticket_after_sales is not None
            else None
        ),
        "leaderboard_reward_enabled": bool(leaderboard_reward_enabled or False),
        "leaderboard_reward_description": desc,
    }


def sale_is_past_hold(sale: AmbassadorSale, *, now: datetime | None = None) -> bool:
    current = now or datetime.now(UTC)
    hold = getattr(sale, "hold_until", None)
    if hold is None:
        return True
    if hold.tzinfo is None:
        hold = hold.replace(tzinfo=UTC)
    return current >= hold


def reverse_ambassador_sale_for_order(
    db: Session,
    *,
    order_id: UUID,
    reason: str,
    actor_user_id: UUID | None = None,
) -> AmbassadorSale | None:
    """Reverse commission for refunded/cancelled orders. Idempotent."""
    sale = db.scalar(
        select(AmbassadorSale).where(AmbassadorSale.order_id == order_id)
    )
    if sale is None:
        return None
    if sale.status == "reversed":
        return sale

    previous = sale.status
    now = datetime.now(UTC)
    sale.status = "reversed"
    sale.reversed_at = now
    sale.reversed_by_user_id = actor_user_id
    sale.reversal_reason = (reason or "Order refunded/cancelled")[:500]
    sale.reward_status_updated_at = now
    sale.reward_status_updated_by_user_id = actor_user_id
    write_audit_log(
        db,
        action="ambassadors.sale_reversed",
        actor_user_id=actor_user_id,
        resource_type="ambassador_sale",
        resource_id=str(sale.id),
        details={
            "previous_status": previous,
            "reason": sale.reversal_reason,
            "order_id": str(order_id),
            "commission_owed": str(sale.commission_owed),
            "system": True,
        },
    )
    return sale


def maybe_grant_free_ticket_reward(
    db: Session, *, ambassador: Ambassador, campaign: AmbassadorCampaign | None
) -> None:
    """Mark free-ticket eligibility after X confirmed (non-reversed) sales."""
    if campaign is None:
        return
    threshold = getattr(campaign, "free_ticket_after_sales", None)
    if threshold is None or int(threshold) <= 0:
        return
    if getattr(ambassador, "free_ticket_earned_at", None) is not None:
        return
    count = int(
        db.scalar(
            select(func.count())
            .select_from(AmbassadorSale)
            .where(
                AmbassadorSale.ambassador_id == ambassador.id,
                AmbassadorSale.status != "reversed",
            )
        )
        or 0
    )
    if count >= int(threshold):
        ambassador.free_ticket_earned_at = datetime.now(UTC)
        write_audit_log(
            db,
            action="ambassadors.free_ticket_earned",
            actor_user_id=ambassador.user_id,
            resource_type="ambassador",
            resource_id=str(ambassador.id),
            details={
                "campaign_id": str(campaign.id),
                "threshold": int(threshold),
                "confirmed_sales": count,
            },
        )
