"""Domain Ambassadors payment attribution + conversion finalize/refund.

Commission conversions are created only after backend-verified payment
(Paystack webhook / free-order finalize). Frontend success pages never call this.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ambassadors.audit import write_ambassador_audit
from app.events.models import Event
from app.payments.models import Order
from app.promos.ambassador_domain import (
    AmbassadorAttribution,
    AmbassadorConversion,
    AmbassadorParticipant,
)
from app.promos.commission import (
    compute_commission_owed,
    filter_units_and_revenue,
)
from app.promos.constants import (
    APPLIES_TO_MERCH,
    APPLIES_TO_TICKETS,
    APPLIES_TO_TICKETS_AND_MERCH,
    ATTRIBUTION_SOURCE_CODE,
    ATTRIBUTION_SOURCE_LINK,
    REFERRAL_SOURCE_EXPLICIT,
    REFERRAL_SOURCES,
)
from app.promos.models import Ambassador, AmbassadorCampaign
from app.users.models import User


def _q(amount: Decimal) -> Decimal:
    return Decimal(amount).quantize(Decimal("0.01"))


def _dedupe_key(
    *,
    conversion_type: str,
    order_id: UUID,
    participant_id: UUID,
    campaign_id: UUID,
) -> str:
    """Unique per campaign + participant + order + conversion type."""
    return f"{conversion_type}:{order_id}:{participant_id}:{campaign_id}"


def resolve_participant_for_event(
    db: Session,
    *,
    referral_code: str,
    event: Event,
    prefer_merch: bool = False,
) -> AmbassadorParticipant | None:
    code = referral_code.strip().lower()
    if not code:
        return None
    campaign_ids = list(
        db.scalars(
            select(AmbassadorCampaign.id).where(
                AmbassadorCampaign.event_id == event.id
            )
        )
    )
    if not campaign_ids:
        return None
    rows = list(
        db.scalars(
            select(AmbassadorParticipant).where(
                AmbassadorParticipant.ambassador_code == code,
                AmbassadorParticipant.status == "active",
                AmbassadorParticipant.campaign_id.in_(campaign_ids),
            )
        )
    )
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0]

    def _score(p: AmbassadorParticipant) -> tuple[int, datetime]:
        campaign = db.get(AmbassadorCampaign, p.campaign_id)
        ctype = (campaign.campaign_type if campaign else "") or ""
        merchish = ctype in {"merch", "event_merch"}
        if prefer_merch:
            type_score = 0 if merchish else 1
        else:
            type_score = 0 if not merchish else 1
        return (type_score, p.joined_at or datetime.now(UTC))

    rows.sort(key=_score)
    return rows[0]


def _attribution_usable(
    db: Session,
    *,
    attribution_id: UUID,
    event: Event,
    buyer_user_id: UUID,
) -> AmbassadorAttribution | None:
    row = db.get(AmbassadorAttribution, attribution_id)
    if row is None:
        return None
    expires = row.expires_at
    if expires is not None:
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if datetime.now(UTC) > expires:
            return None
    participant = db.get(AmbassadorParticipant, row.participant_id)
    if participant is None or participant.status != "active":
        return None
    if participant.user_id == buyer_user_id:
        return None
    campaign = db.get(AmbassadorCampaign, row.campaign_id)
    if campaign is None:
        return None
    if campaign.event_id is not None and campaign.event_id != event.id:
        return None
    from app.ambassadors.fraud import commission_blocked_for_host_owner

    if commission_blocked_for_host_owner(
        db, user_id=participant.user_id, campaign=campaign
    ):
        return None
    return row


def attach_domain_attribution_to_order(
    db: Session,
    *,
    order: Order,
    event: Event,
    buyer: User,
    referral_code: str | None,
    referral_source: str | None,
    attribution_id: UUID | None = None,
    session_id: str | None = None,
) -> None:
    """Bind domain participant during checkout (pending order). No commission yet."""
    source = (
        referral_source
        if referral_source in REFERRAL_SOURCES
        else REFERRAL_SOURCE_EXPLICIT
        if referral_code
        else "link"
    )

    # Explicit checkout code never overwritten by later cookie/link attach.
    existing_source = getattr(order, "referral_attribution_source", None)
    if (
        getattr(order, "ambassador_participant_id", None) is not None
        and existing_source == REFERRAL_SOURCE_EXPLICIT
        and source != REFERRAL_SOURCE_EXPLICIT
    ):
        return

    participant: AmbassadorParticipant | None = None
    attribution: AmbassadorAttribution | None = None

    if attribution_id is not None:
        attribution = _attribution_usable(
            db,
            attribution_id=attribution_id,
            event=event,
            buyer_user_id=buyer.id,
        )
        if attribution is not None:
            participant = db.get(
                AmbassadorParticipant, attribution.participant_id
            )

    if participant is None and referral_code:
        prefer_merch = any(
            getattr(item, "item_kind", "ticket") in {"merch", "bundle"}
            for item in order.items
        ) and not any(
            getattr(item, "item_kind", "ticket") == "ticket" for item in order.items
        )
        participant = resolve_participant_for_event(
            db,
            referral_code=referral_code,
            event=event,
            prefer_merch=prefer_merch,
        )

    # Bridge: v1 ambassador code → domain participant with same code.
    if participant is None and getattr(order, "ambassador_id", None):
        amb = db.get(Ambassador, order.ambassador_id)
        if amb is not None and amb.referral_code:
            participant = resolve_participant_for_event(
                db,
                referral_code=amb.referral_code,
                event=event,
                prefer_merch=False,
            )

    if participant is None:
        return
    if participant.user_id == buyer.id:
        return

    from app.ambassadors.fraud import commission_blocked_for_host_owner

    campaign = db.get(AmbassadorCampaign, participant.campaign_id)
    if commission_blocked_for_host_owner(
        db, user_id=participant.user_id, campaign=campaign
    ):
        return

    order.ambassador_participant_id = participant.id
    order.referral_code = participant.ambassador_code
    order.referral_attribution_source = source

    if attribution is not None:
        order.ambassador_attribution_id = attribution.id
    elif session_id:
        # Persist a checkout attribution row for audit / cookie window.
        campaign = db.get(AmbassadorCampaign, participant.campaign_id)
        cookie_days = int(
            getattr(campaign, "cookie_window_days", 30) if campaign else 30
        )
        from datetime import timedelta

        attr_source = (
            ATTRIBUTION_SOURCE_CODE
            if source == REFERRAL_SOURCE_EXPLICIT
            else ATTRIBUTION_SOURCE_LINK
        )
        attribution = AmbassadorAttribution(
            campaign_id=participant.campaign_id,
            participant_id=participant.id,
            user_id=buyer.id,
            session_id=session_id,
            event_id=event.id,
            merch_product_id=getattr(campaign, "merch_product_id", None)
            if campaign
            else None,
            source=attr_source,
            expires_at=datetime.now(UTC) + timedelta(days=max(1, cookie_days)),
        )
        db.add(attribution)
        db.flush()
        order.ambassador_attribution_id = attribution.id

    write_ambassador_audit(
        db,
        action="ambassadors.order_attributed",
        entity_type="order",
        entity_id=order.id,
        actor_user_id=buyer.id,
        metadata={
            "participant_id": str(participant.id),
            "campaign_id": str(participant.campaign_id),
            "referral_source": source,
            "pending": True,
        },
    )


def _line_totals(order: Order) -> tuple[int, int, Decimal, Decimal]:
    tickets = 0
    merch = 0
    ticket_rev = Decimal("0")
    merch_rev = Decimal("0")
    for item in order.items:
        kind = getattr(item, "item_kind", "ticket")
        qty = int(item.quantity or 0)
        total = Decimal(item.line_total or 0)
        if kind == "ticket":
            tickets += qty
            ticket_rev += total
        elif kind in {"merch", "bundle"}:
            merch += qty
            merch_rev += total
    return tickets, merch, ticket_rev, merch_rev


def _create_conversion_if_needed(
    db: Session,
    *,
    order: Order,
    participant: AmbassadorParticipant,
    campaign: AmbassadorCampaign,
    conversion_type: str,
    tickets_sold: int,
    merch_units: int,
    commissionable_revenue: Decimal,
    rules: dict,
) -> AmbassadorConversion | None:
    if commissionable_revenue <= 0 and tickets_sold <= 0 and merch_units <= 0:
        return None

    key = _dedupe_key(
        conversion_type=conversion_type,
        order_id=order.id,
        participant_id=participant.id,
        campaign_id=campaign.id,
    )
    existing = db.scalar(
        select(AmbassadorConversion).where(AmbassadorConversion.dedupe_key == key)
    )
    if existing is not None:
        return existing

    commission = compute_commission_owed(
        commission_type=rules["commission_type"],
        commission_value=rules["commission_value"],
        applies_to=rules["applies_to"],
        tickets_sold=tickets_sold,
        merch_units=merch_units,
        commissionable_revenue=commissionable_revenue,
        max_commission_per_order=rules["max_commission_per_order"],
    )
    # Flat merch uses applies_to=merch on a ticket-only conversion_type path —
    # recompute with the conversion's scoped applies when split.
    scoped_applies = (
        APPLIES_TO_TICKETS
        if conversion_type == "ticket"
        else APPLIES_TO_MERCH
    )
    if rules["applies_to"] == APPLIES_TO_TICKETS_AND_MERCH:
        commission = compute_commission_owed(
            commission_type=rules["commission_type"],
            commission_value=rules["commission_value"],
            applies_to=scoped_applies,
            tickets_sold=tickets_sold if conversion_type == "ticket" else 0,
            merch_units=merch_units if conversion_type == "merch" else 0,
            commissionable_revenue=commissionable_revenue,
            max_commission_per_order=rules["max_commission_per_order"],
        )

    now = datetime.now(UTC)
    conversion = AmbassadorConversion(
        campaign_id=campaign.id,
        participant_id=participant.id,
        buyer_user_id=order.buyer_user_id,
        order_id=order.id,
        merch_order_id=order.id if conversion_type == "merch" else None,
        conversion_type=conversion_type,
        gross_amount=_q(commissionable_revenue),
        eligible_amount=_q(commissionable_revenue),
        commission_amount=commission,
        status="approved",
        dedupe_key=key,
        verified_at=now,
    )
    try:
        with db.begin_nested():
            db.add(conversion)
            db.flush()
    except IntegrityError:
        # Concurrent webhook — unique dedupe_key already won.
        return db.scalar(
            select(AmbassadorConversion).where(
                AmbassadorConversion.dedupe_key == key
            )
        )

    write_ambassador_audit(
        db,
        action="ambassadors.conversion_created",
        entity_type="ambassador_conversion",
        entity_id=conversion.id,
        actor_user_id=order.buyer_user_id,
        metadata={
            "order_id": str(order.id),
            "conversion_type": conversion_type,
            "commission_amount": str(commission),
            "dedupe_key": key,
            "verified": True,
        },
    )
    return conversion


def finalize_ambassador_conversions(db: Session, *, order: Order) -> list[AmbassadorConversion]:
    """Create domain conversions after verified payment only. Idempotent."""
    if order.status != "paid":
        return []

    participant_id = getattr(order, "ambassador_participant_id", None)
    if participant_id is None:
        # Late bridge from referral_code if checkout only set v1 ambassador.
        if order.referral_code:
            event = db.get(Event, order.event_id)
            if event is not None:
                participant = resolve_participant_for_event(
                    db, referral_code=order.referral_code, event=event
                )
                if participant is not None and participant.user_id != order.buyer_user_id:
                    order.ambassador_participant_id = participant.id
                    participant_id = participant.id
        if participant_id is None:
            return []

    participant = db.get(AmbassadorParticipant, participant_id)
    if participant is None or participant.status in {"removed", "blocked"}:
        return []
    if participant.user_id == order.buyer_user_id:
        return []

    campaign = db.get(AmbassadorCampaign, participant.campaign_id)
    if campaign is None:
        return []

    from app.ambassadors.fraud import commission_blocked_for_host_owner

    if commission_blocked_for_host_owner(
        db, user_id=participant.user_id, campaign=campaign
    ):
        return []

    rules = {
        "commission_type": getattr(campaign, "commission_type", None) or "percentage",
        "commission_value": Decimal(
            getattr(campaign, "commission_value", None)
            or campaign.commission_percent
            or 0
        ),
        "applies_to": getattr(campaign, "applies_to", None) or APPLIES_TO_TICKETS,
        "max_commission_per_order": getattr(
            campaign, "max_commission_per_order", None
        ),
    }
    tickets_raw, merch_raw, ticket_rev, merch_rev = _line_totals(order)
    applies = rules["applies_to"]

    created: list[AmbassadorConversion] = []

    if applies in {APPLIES_TO_TICKETS, APPLIES_TO_TICKETS_AND_MERCH}:
        t_sold, _m, _tr, _mr, revenue = filter_units_and_revenue(
            applies_to=APPLIES_TO_TICKETS,
            tickets_sold=tickets_raw,
            merch_units=0,
            ticket_revenue=ticket_rev,
            merch_revenue=Decimal("0"),
        )
        row = _create_conversion_if_needed(
            db,
            order=order,
            participant=participant,
            campaign=campaign,
            conversion_type="ticket",
            tickets_sold=t_sold,
            merch_units=0,
            commissionable_revenue=revenue,
            rules=rules,
        )
        if row is not None:
            created.append(row)

    if applies in {APPLIES_TO_MERCH, APPLIES_TO_TICKETS_AND_MERCH}:
        _t, m_units, _tr, _mr, revenue = filter_units_and_revenue(
            applies_to=APPLIES_TO_MERCH,
            tickets_sold=0,
            merch_units=merch_raw,
            ticket_revenue=Decimal("0"),
            merch_revenue=merch_rev,
        )
        row = _create_conversion_if_needed(
            db,
            order=order,
            participant=participant,
            campaign=campaign,
            conversion_type="merch",
            tickets_sold=0,
            merch_units=m_units,
            commissionable_revenue=revenue,
            rules=rules,
        )
        if row is not None:
            created.append(row)

    if created:
        from app.ambassadors.notifications import on_domain_conversions_created

        on_domain_conversions_created(
            db,
            participant=participant,
            campaign=campaign,
            created=created,
        )
    return created


def reverse_conversions_for_order(
    db: Session,
    *,
    order_id: UUID,
    reason: str,
    actor_user_id: UUID | None = None,
) -> list[AmbassadorConversion]:
    """Reverse all domain conversions for a refunded/cancelled order. Idempotent."""
    rows = list(
        db.scalars(
            select(AmbassadorConversion).where(
                or_(
                    AmbassadorConversion.order_id == order_id,
                    AmbassadorConversion.merch_order_id == order_id,
                )
            )
        )
    )
    now = datetime.now(UTC)
    reversed_rows: list[AmbassadorConversion] = []
    for conversion in rows:
        if conversion.status == "reversed":
            reversed_rows.append(conversion)
            continue
        previous = conversion.status
        conversion.status = "reversed"
        conversion.refunded_at = now
        write_ambassador_audit(
            db,
            action="ambassadors.conversion_reversed",
            entity_type="ambassador_conversion",
            entity_id=conversion.id,
            actor_user_id=actor_user_id,
            metadata={
                "previous_status": previous,
                "reason": (reason or "Order refunded")[:500],
                "order_id": str(order_id),
                "commission_amount": str(conversion.commission_amount),
                "system": True,
            },
        )
        reversed_rows.append(conversion)
    return reversed_rows
