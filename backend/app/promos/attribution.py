"""Per-item referral attribution: host and platform commissions may both apply."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events.models import Event
from app.payments.models import Order, OrderItem
from app.promos.constants import (
    APPLIES_TO_MERCH,
    APPLIES_TO_TICKETS,
    APPLIES_TO_TICKETS_AND_MERCH,
    CAMPAIGN_TYPE_EVENT_MERCH,
    CAMPAIGN_TYPE_EVENT_TICKETS,
    COMMISSION_TYPE_FLAT,
    COMMISSION_TYPE_PERCENTAGE,
    PAYER_HOST,
    PAYER_PLATFORM,
    PROGRAM_PLATFORM_WIDE,
    REFERRAL_SCOPE_PLATFORM,
)
from app.promos.models import Ambassador, AmbassadorCampaign
from app.promos.referral_programs import (
    ReferralProgram,
    ReferralProgramExclusion,
    ReferralProgramRule,
)


@dataclass(frozen=True)
class ItemAttributionWinner:
    """Winning enrollment for a single order item and payer scope."""

    ambassador: Ambassador
    order_item: OrderItem
    attribution_item_key: str
    product_type: str  # ticket | merchandise
    product_id: UUID | None
    payer_type: str
    winning_scope: str  # event | platform
    program_id: UUID | None
    campaign_id: UUID | None
    rule_id: UUID | None
    commission_mode: str  # percentage | fixed
    commission_rate: Decimal
    commission_type: str  # percentage | flat (v1 compute helper)
    hold_period_days: int
    max_commission_per_order: Decimal | None
    gross_item_amount: Decimal
    eligible_commission_base: Decimal


def attribution_item_key_for(item: OrderItem) -> str:
    return str(item.id)


def product_type_for_item(item: OrderItem) -> str | None:
    kind = getattr(item, "item_kind", "ticket") or "ticket"
    if kind == "ticket":
        return "ticket"
    if kind in {"merch", "bundle"}:
        return "merchandise"
    return None


def product_id_for_item(item: OrderItem) -> UUID | None:
    kind = getattr(item, "item_kind", "ticket") or "ticket"
    if kind == "ticket":
        return getattr(item, "ticket_type_id", None)
    return getattr(item, "merch_product_id", None) or getattr(item, "bundle_id", None)


def _campaign_covers_product(
    campaign: AmbassadorCampaign | None, product_type: str
) -> bool:
    if campaign is None:
        return product_type == "ticket"
    applies = getattr(campaign, "applies_to", None) or APPLIES_TO_TICKETS
    ctype = getattr(campaign, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS)
    if ctype == CAMPAIGN_TYPE_EVENT_MERCH or applies == APPLIES_TO_MERCH:
        return product_type == "merchandise"
    if applies == APPLIES_TO_TICKETS_AND_MERCH:
        return True
    return product_type == "ticket"


def _program_active(program: ReferralProgram) -> bool:
    if program.status != "active":
        return False
    now = datetime.now(UTC)
    if program.starts_at is not None and program.starts_at > now:
        return False
    if program.ends_at is not None and program.ends_at < now:
        return False
    return True


def _event_excluded(db: Session, *, program_id: UUID, event: Event) -> bool:
    row = db.scalar(
        select(ReferralProgramExclusion).where(
            ReferralProgramExclusion.program_id == program_id,
            (
                (ReferralProgramExclusion.event_id == event.id)
                | (ReferralProgramExclusion.host_id == event.host_id)
            ),
        )
    )
    return row is not None


def _codes_for_order(db: Session, order: Order) -> list[str]:
    codes: list[str] = []
    if order.referral_code:
        codes.append(order.referral_code.strip().lower())
    platform_code = getattr(order, "platform_referral_code", None)
    if platform_code:
        pc = platform_code.strip().lower()
        if pc and pc not in codes:
            codes.append(pc)
    if order.ambassador_id is not None:
        attached = db.get(Ambassador, order.ambassador_id)
        if attached is not None and attached.referral_code:
            c = attached.referral_code.strip().lower()
            if c not in codes:
                codes.append(c)
    return codes


def resolve_platform_for_item(
    db: Session,
    *,
    referral_code: str,
    event: Event,
    product_type: str,
    item: OrderItem,
) -> ItemAttributionWinner | None:
    code = referral_code.strip().lower()
    if not code:
        return None
    amb = db.scalar(
        select(Ambassador).where(
            Ambassador.referral_code == code,
            Ambassador.status == "active",
            Ambassador.program_kind == PROGRAM_PLATFORM_WIDE,
        )
    )
    if amb is None:
        return None
    return _platform_winner_from_ambassador(
        db, amb=amb, event=event, product_type=product_type, item=item
    )


def _platform_winner_from_ambassador(
    db: Session,
    *,
    amb: Ambassador,
    event: Event,
    product_type: str,
    item: OrderItem,
) -> ItemAttributionWinner | None:
    if amb.program_kind != PROGRAM_PLATFORM_WIDE or amb.program_id is None:
        return None
    program = db.get(ReferralProgram, amb.program_id)
    if program is None or program.scope != REFERRAL_SCOPE_PLATFORM:
        return None
    if not _program_active(program):
        return None
    if _event_excluded(db, program_id=program.id, event=event):
        return None

    rule_product = "merchandise" if product_type == "merchandise" else "ticket"
    rule = db.scalar(
        select(ReferralProgramRule).where(
            ReferralProgramRule.program_id == program.id,
            ReferralProgramRule.product_type == rule_product,
            ReferralProgramRule.is_active.is_(True),
        )
    )
    if rule is None:
        return None
    if rule.minimum_order_amount is not None:
        if Decimal(item.line_total) < Decimal(rule.minimum_order_amount):
            return None

    mode = "fixed" if rule.commission_mode == "fixed" else "percentage"
    commission_type = (
        COMMISSION_TYPE_FLAT if mode == "fixed" else COMMISSION_TYPE_PERCENTAGE
    )
    base = Decimal(item.line_total)
    return ItemAttributionWinner(
        ambassador=amb,
        order_item=item,
        attribution_item_key=attribution_item_key_for(item),
        product_type=product_type,
        product_id=product_id_for_item(item),
        payer_type=PAYER_PLATFORM,
        winning_scope="platform",
        program_id=program.id,
        campaign_id=None,
        rule_id=rule.id,
        commission_mode=mode,
        commission_rate=Decimal(rule.commission_value or 0),
        commission_type=commission_type,
        hold_period_days=int(program.hold_period_days or 7),
        max_commission_per_order=(
            Decimal(rule.maximum_commission_per_item)
            if rule.maximum_commission_per_item is not None
            else None
        ),
        gross_item_amount=base,
        eligible_commission_base=base,
    )


def _winner_from_event_for_item(
    db: Session,
    *,
    amb: Ambassador,
    product_type: str,
    item: OrderItem,
) -> ItemAttributionWinner | None:
    if amb.program_kind == PROGRAM_PLATFORM_WIDE:
        return None
    campaign = None
    if amb.campaign_id is not None:
        campaign = db.get(AmbassadorCampaign, amb.campaign_id)
        if campaign is not None and campaign.status not in {
            "public_open",
            "active",
        }:
            return None
        if not _campaign_covers_product(campaign, product_type):
            return None
    elif product_type != "ticket":
        return None

    from app.promos.commission import resolve_commission_rules

    rules = resolve_commission_rules(campaign, ambassador=amb)
    applies = rules["applies_to"]
    if product_type == "ticket" and applies == APPLIES_TO_MERCH:
        return None
    if product_type == "merchandise" and applies == APPLIES_TO_TICKETS:
        return None

    ctype = rules["commission_type"]
    mode = "fixed" if ctype == COMMISSION_TYPE_FLAT else "percentage"
    base = Decimal(item.line_total)
    return ItemAttributionWinner(
        ambassador=amb,
        order_item=item,
        attribution_item_key=attribution_item_key_for(item),
        product_type=product_type,
        product_id=product_id_for_item(item),
        payer_type=PAYER_HOST,
        winning_scope="event",
        program_id=getattr(amb, "program_id", None)
        or (campaign.program_id if campaign else None),
        campaign_id=amb.campaign_id,
        rule_id=None,
        commission_mode=mode,
        commission_rate=rules["commission_value"],
        commission_type=ctype,
        hold_period_days=rules["hold_period_days"],
        max_commission_per_order=rules["max_commission_per_order"],
        gross_item_amount=base,
        eligible_commission_base=base,
    )


def _host_enrollment_for_user(
    db: Session,
    *,
    user_id: UUID,
    event: Event,
    product_type: str,
    item: OrderItem,
) -> ItemAttributionWinner | None:
    """Active host/open enrollment for this user on the event covering product."""
    from app.promos.service import (
        PROGRAM_HOST_CURATED,
        PROGRAM_OPEN_EVENT,
        _ambassador_attribution_allowed,
    )

    rows = list(
        db.scalars(
            select(Ambassador).where(
                Ambassador.user_id == user_id,
                Ambassador.status == "active",
                Ambassador.program_kind.in_(
                    [PROGRAM_OPEN_EVENT, PROGRAM_HOST_CURATED]
                ),
                (
                    (Ambassador.event_id == event.id)
                    | (
                        (Ambassador.event_id.is_(None))
                        & (Ambassador.host_id == event.host_id)
                    )
                ),
            )
        ).all()
    )
    prefer_merch = product_type == "merchandise"
    ranked: list[Ambassador] = []
    for amb in rows:
        if not _ambassador_attribution_allowed(db, amb):
            continue
        if amb.campaign_id is not None:
            camp = db.get(AmbassadorCampaign, amb.campaign_id)
            if camp is None:
                continue
            ctype = getattr(camp, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS)
            if prefer_merch and ctype == CAMPAIGN_TYPE_EVENT_MERCH:
                ranked.insert(0, amb)
            elif not prefer_merch and ctype != CAMPAIGN_TYPE_EVENT_MERCH:
                ranked.insert(0, amb)
            else:
                ranked.append(amb)
        else:
            ranked.append(amb)
    for amb in ranked:
        win = _winner_from_event_for_item(
            db, amb=amb, product_type=product_type, item=item
        )
        if win is not None:
            return win
    return None


def _platform_enrollment_for_user(
    db: Session,
    *,
    user_id: UUID,
    event: Event,
    product_type: str,
    item: OrderItem,
) -> ItemAttributionWinner | None:
    from app.promos.service import _ambassador_attribution_allowed

    amb = db.scalar(
        select(Ambassador).where(
            Ambassador.user_id == user_id,
            Ambassador.status == "active",
            Ambassador.program_kind == PROGRAM_PLATFORM_WIDE,
        )
    )
    if amb is None or not _ambassador_attribution_allowed(db, amb):
        return None
    return _platform_winner_from_ambassador(
        db, amb=amb, event=event, product_type=product_type, item=item
    )


def resolve_attributions_for_item(
    db: Session,
    *,
    order: Order,
    item: OrderItem,
    event: Event,
    codes: list[str],
) -> list[ItemAttributionWinner]:
    """Return 0–2 winners: host-funded and/or platform-funded for this item.

    Dual commission applies when both scopes resolve (same user with both
    enrollments, or distinct codes for different ambassadors). Host enabling
    alone does not invent a host earner without an enrollment.
    """
    from app.promos.service import (
        _ambassador_attribution_allowed,
        resolve_ambassador_for_event,
    )

    product_type = product_type_for_item(item)
    if product_type is None:
        return []
    prefer_merch = product_type == "merchandise"

    host_win: ItemAttributionWinner | None = None
    for code in codes:
        amb = resolve_ambassador_for_event(
            db,
            referral_code=code,
            event=event,
            prefer_merch=prefer_merch,
        )
        if amb is None or not _ambassador_attribution_allowed(db, amb):
            continue
        win = _winner_from_event_for_item(
            db, amb=amb, product_type=product_type, item=item
        )
        if win is not None:
            host_win = win
            break

    plat_win: ItemAttributionWinner | None = None
    for code in codes:
        win = resolve_platform_for_item(
            db,
            referral_code=code,
            event=event,
            product_type=product_type,
            item=item,
        )
        if win is None:
            continue
        if not _ambassador_attribution_allowed(db, win.ambassador):
            continue
        plat_win = win
        break

    # Sibling enrollments: one username/platform (or host) link unlocks both pots
    # when the same user holds both enrollments.
    if plat_win is not None and host_win is None and plat_win.ambassador.user_id:
        host_win = _host_enrollment_for_user(
            db,
            user_id=plat_win.ambassador.user_id,
            event=event,
            product_type=product_type,
            item=item,
        )
    if host_win is not None and plat_win is None and host_win.ambassador.user_id:
        plat_win = _platform_enrollment_for_user(
            db,
            user_id=host_win.ambassador.user_id,
            event=event,
            product_type=product_type,
            item=item,
        )

    out: list[ItemAttributionWinner] = []
    if host_win is not None:
        out.append(host_win)
    if plat_win is not None:
        out.append(plat_win)
    return out


def resolve_winning_attribution_for_item(
    db: Session,
    *,
    order: Order,
    item: OrderItem,
    event: Event,
    codes: list[str],
) -> ItemAttributionWinner | None:
    """Back-compat: first winner (host preferred, then platform)."""
    winners = resolve_attributions_for_item(
        db, order=order, item=item, event=event, codes=codes
    )
    return winners[0] if winners else None


def resolve_winning_attributions_for_order(
    db: Session,
    *,
    order: Order,
) -> list[ItemAttributionWinner]:
    """Collect host and/or platform winners per eligible order item."""
    event = db.get(Event, order.event_id) if order.event_id else None
    if event is None:
        return []
    codes = _codes_for_order(db, order)
    if not codes:
        return []

    winners: list[ItemAttributionWinner] = []
    for item in list(order.items):
        winners.extend(
            resolve_attributions_for_item(
                db, order=order, item=item, event=event, codes=codes
            )
        )
    return winners


# Back-compat alias used by older call sites expecting slice winners
def resolve_platform_ambassador(
    db: Session,
    *,
    referral_code: str,
    event: Event,
    product_slice: str,
):
    """Legacy helper for checkout attach — returns first matching platform amb."""
    from types import SimpleNamespace

    product_type = "merchandise" if product_slice == "merch" else "ticket"
    code = referral_code.strip().lower()
    amb = db.scalar(
        select(Ambassador).where(
            Ambassador.referral_code == code,
            Ambassador.status == "active",
            Ambassador.program_kind == PROGRAM_PLATFORM_WIDE,
        )
    )
    if amb is None or amb.program_id is None:
        return None
    program = db.get(ReferralProgram, amb.program_id)
    if program is None or not _program_active(program):
        return None
    if _event_excluded(db, program_id=program.id, event=event):
        return None
    rule_product = "merchandise" if product_type == "merchandise" else "ticket"
    rule = db.scalar(
        select(ReferralProgramRule).where(
            ReferralProgramRule.program_id == program.id,
            ReferralProgramRule.product_type == rule_product,
            ReferralProgramRule.is_active.is_(True),
        )
    )
    if rule is None:
        return None
    return SimpleNamespace(
        ambassador=amb,
        product_slice=product_slice,
        payer_type=PAYER_PLATFORM,
        program_id=program.id,
        commission_type=(
            COMMISSION_TYPE_FLAT
            if rule.commission_mode == "fixed"
            else COMMISSION_TYPE_PERCENTAGE
        ),
        commission_value=Decimal(rule.commission_value or 0),
        hold_period_days=int(program.hold_period_days or 7),
        max_commission_per_order=(
            Decimal(rule.maximum_commission_per_item)
            if rule.maximum_commission_per_item is not None
            else None
        ),
        applies_to=(
            APPLIES_TO_MERCH if product_type == "merchandise" else APPLIES_TO_TICKETS
        ),
    )
