"""Open Event Ambassadors demo seed (DJ Maze · Afrobeats Night Live).

Idempotent. Creates a public_open campaign, three fan participants with fixed
codes, funnel clicks, pending checkouts, and verified ticket/merch conversions
across pending / payable / reversed commission states for leaderboard QA.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.demo.constants import (
    DEMO_EMAIL_DOMAIN,
    DEMO_EVENT_SLUG_PREFIX,
    OPEN_AMBASSADOR_CAMPAIGN_NAME,
    OPEN_AMBASSADOR_EVENT_KEY,
    OPEN_AMBASSADOR_PARTICIPANTS,
)
from app.demo.models import DemoEntityMarker
from app.events.models import Event, TicketType
from app.hosts.models import Host
from app.merch.models import EventMerchProduct, EventMerchVariant
from app.payments.models import Order, Payment
from app.payments.schemas import CheckoutAnswerIn, OrderCreate, OrderItemCreate
from app.payments.service import create_order, get_order_by_id
from app.payments.webhook import finalize_successful_payment
from app.promos.ambassador_domain import (
    AmbassadorAttribution,
    AmbassadorClick,
    AmbassadorConversion,
    AmbassadorParticipant,
    AmbassadorProfile,
)
from app.promos.admin_service import get_or_create_platform_settings
from app.promos.constants import (
    AMBASSADOR_TERMS_VERSION,
    APPLIES_TO_TICKETS_AND_MERCH,
    COMMISSION_TYPE_PERCENTAGE,
)
from app.promos.models import (
    Ambassador,
    AmbassadorCampaign,
    AmbassadorSale,
    PromoClick,
)
from app.promos.service import PROGRAM_OPEN_EVENT
from app.users.models import User
from app.users.service import get_user_by_email

MARKER_TYPE = "open_ambassadors"
CAMPAIGN_MARKER_KEY = "afrobeats-night-ambassador-drive"

# Buyers must not be the ambassadors (self-referral blocked).
_LEDGER: list[dict[str, Any]] = [
    # Tolu — leaderboard lead
    {
        "key": "tolu-checkout",
        "code": "toluafro",
        "buyer": f"fan5@{DEMO_EMAIL_DOMAIN}",
        "kind": "checkout",
    },
    {
        "key": "tolu-ticket-pending",
        "code": "toluafro",
        "buyer": f"fan6@{DEMO_EMAIL_DOMAIN}",
        "kind": "ticket",
        "v1_status": "attributed",
        "domain_status": "pending",
    },
    {
        "key": "tolu-ticket-payable",
        "code": "toluafro",
        "buyer": f"fan7@{DEMO_EMAIL_DOMAIN}",
        "kind": "ticket",
        "v1_status": "approved",
        "domain_status": "payable",
    },
    {
        "key": "tolu-merch-payable",
        "code": "toluafro",
        "buyer": f"fan8@{DEMO_EMAIL_DOMAIN}",
        "kind": "merch",
        "v1_status": "approved",
        "domain_status": "payable",
    },
    # Amaka
    {
        "key": "amaka-checkout",
        "code": "amaka20",
        "buyer": f"fan9@{DEMO_EMAIL_DOMAIN}",
        "kind": "checkout",
    },
    {
        "key": "amaka-ticket-pending",
        "code": "amaka20",
        "buyer": f"fan10@{DEMO_EMAIL_DOMAIN}",
        "kind": "ticket",
        "v1_status": "attributed",
        "domain_status": "pending",
    },
    {
        "key": "amaka-merch-reversed",
        "code": "amaka20",
        "buyer": f"fan11@{DEMO_EMAIL_DOMAIN}",
        "kind": "merch",
        "v1_status": "reversed",
        "domain_status": "reversed",
    },
    # Chidi
    {
        "key": "chidi-ticket-pending",
        "code": "chidilive",
        "buyer": f"fan12@{DEMO_EMAIL_DOMAIN}",
        "kind": "ticket",
        "v1_status": "attributed",
        "domain_status": "pending",
    },
    {
        "key": "chidi-ticket-payable",
        "code": "chidilive",
        "buyer": f"buyer@{DEMO_EMAIL_DOMAIN}",
        "kind": "ticket",
        "v1_status": "approved",
        "domain_status": "payable",
    },
]


def _now() -> datetime:
    return datetime.now(UTC)


def _mark(
    db: Session,
    entity_key: str,
    entity_id: Any = None,
    **meta: Any,
) -> None:
    existing = db.scalar(
        select(DemoEntityMarker).where(
            DemoEntityMarker.entity_type == MARKER_TYPE,
            DemoEntityMarker.entity_key == entity_key,
        )
    )
    if existing:
        if entity_id is not None:
            existing.entity_id = str(entity_id)
        if meta:
            existing.meta = {**(existing.meta or {}), **meta}
        return
    db.add(
        DemoEntityMarker(
            entity_type=MARKER_TYPE,
            entity_key=entity_key,
            entity_id=str(entity_id) if entity_id is not None else None,
            meta=meta or None,
        )
    )


def _marked(db: Session, entity_key: str) -> bool:
    return (
        db.scalar(
            select(DemoEntityMarker).where(
                DemoEntityMarker.entity_type == MARKER_TYPE,
                DemoEntityMarker.entity_key == entity_key,
            )
        )
        is not None
    )


def _safe(db: Session, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return None


def _checkout_answers(event: Event, *, buyer_index: int = 0) -> list[CheckoutAnswerIn]:
    answers: list[CheckoutAnswerIn] = []
    for question in list(event.checkout_questions or []):
        if getattr(question, "status", "active") != "active" or not question.required:
            continue
        if question.type == "phone":
            value: str | list[str] = f"+234802{buyer_index:07d}"[:14]
        elif question.type == "email":
            value = f"amb-buyer{buyer_index}@{DEMO_EMAIL_DOMAIN}"
        elif question.type == "dropdown":
            opts = list(question.options or [])
            value = opts[buyer_index % len(opts)] if opts else "Pàdéyá browse"
        elif question.type == "checkbox":
            opts = list(question.options or [])
            value = [opts[0]] if opts else ["None"]
        else:
            value = "Demo ambassador referral buyer"
        answers.append(CheckoutAnswerIn(question_id=question.id, value=value))
    return answers


def _resolve_event(db: Session, events: dict[str, Event]) -> Event | None:
    event = events.get(OPEN_AMBASSADOR_EVENT_KEY)
    if event is None:
        slug = f"{DEMO_EVENT_SLUG_PREFIX}{OPEN_AMBASSADOR_EVENT_KEY}"
        event = db.scalar(select(Event).where(Event.slug == slug))
    if event is None:
        return None
    return db.scalar(
        select(Event)
        .where(Event.id == event.id)
        .options(
            selectinload(Event.ticket_types),
            selectinload(Event.checkout_questions),
        )
    )


def _ensure_campaign(
    db: Session, *, host: Host, event: Event, owner: User
) -> AmbassadorCampaign:
    campaign = db.scalar(
        select(AmbassadorCampaign).where(
            AmbassadorCampaign.event_id == event.id,
            AmbassadorCampaign.name == OPEN_AMBASSADOR_CAMPAIGN_NAME,
        )
    )
    if campaign is None:
        campaign = db.scalar(
            select(AmbassadorCampaign).where(
                AmbassadorCampaign.event_id == event.id,
                AmbassadorCampaign.campaign_type == "event_tickets",
                AmbassadorCampaign.status.in_(("public_open", "paused")),
            )
        )
    if campaign is None:
        campaign = AmbassadorCampaign(
            host_id=host.id,
            event_id=event.id,
            name=OPEN_AMBASSADOR_CAMPAIGN_NAME,
            status="public_open",
            visibility="public_open",
            source="host",
            created_by_user_id=owner.id,
            campaign_type="event_tickets",
            commission_percent=Decimal("10.00"),
            commission_type=COMMISSION_TYPE_PERCENTAGE,
            commission_value=Decimal("10.00"),
            applies_to=APPLIES_TO_TICKETS_AND_MERCH,
            hold_period_days=7,
            cookie_window_days=30,
            leaderboard_reward_enabled=True,
            leaderboard_reward_description="Top Afrobeats promoter wins a VIP upgrade",
            merch_included=True,
            allow_host_owner_commission=False,
        )
        db.add(campaign)
        db.flush()
    else:
        campaign.name = OPEN_AMBASSADOR_CAMPAIGN_NAME
        campaign.status = "public_open"
        campaign.visibility = "public_open"
        campaign.commission_percent = Decimal("10.00")
        campaign.commission_type = COMMISSION_TYPE_PERCENTAGE
        campaign.commission_value = Decimal("10.00")
        campaign.applies_to = APPLIES_TO_TICKETS_AND_MERCH
        campaign.merch_included = True
        campaign.leaderboard_reward_enabled = True
        if not campaign.leaderboard_reward_description:
            campaign.leaderboard_reward_description = (
                "Top Afrobeats promoter wins a VIP upgrade"
            )

    event.open_ambassadors_enabled = True
    event.open_ambassador_commission_percent = campaign.commission_percent
    settings = get_or_create_platform_settings(db)
    settings.enabled = True
    _mark(db, CAMPAIGN_MARKER_KEY, campaign.id, event_slug=event.slug)
    db.flush()
    return campaign


def _ensure_participant(
    db: Session,
    *,
    campaign: AmbassadorCampaign,
    event: Event,
    user: User,
    display_name: str,
    code: str,
) -> tuple[Ambassador, AmbassadorParticipant]:
    code = code.lower().strip()
    now = _now()

    ambassador = db.scalar(
        select(Ambassador).where(
            Ambassador.campaign_id == campaign.id,
            Ambassador.user_id == user.id,
            Ambassador.program_kind == PROGRAM_OPEN_EVENT,
        )
    )
    if ambassador is None:
        clash = db.scalar(
            select(Ambassador).where(
                Ambassador.campaign_id == campaign.id,
                Ambassador.referral_code == code,
            )
        )
        if clash is not None and clash.user_id != user.id:
            code = f"{code}x"
        ambassador = Ambassador(
            host_id=event.host_id,
            event_id=event.id,
            campaign_id=campaign.id,
            program_kind=PROGRAM_OPEN_EVENT,
            user_id=user.id,
            referral_code=code,
            display_name=display_name[:160],
            email=user.email,
            status="active",
            commission_rate_percent=campaign.commission_value,
            terms_accepted_at=now,
            terms_version=AMBASSADOR_TERMS_VERSION,
        )
        db.add(ambassador)
        db.flush()
    else:
        ambassador.referral_code = code
        ambassador.display_name = display_name[:160]
        ambassador.status = "active"
        ambassador.commission_rate_percent = campaign.commission_value
        if ambassador.terms_accepted_at is None:
            ambassador.terms_accepted_at = now
            ambassador.terms_version = AMBASSADOR_TERMS_VERSION

    profile = db.scalar(
        select(AmbassadorProfile).where(AmbassadorProfile.user_id == user.id)
    )
    if profile is None:
        profile = AmbassadorProfile(
            user_id=user.id,
            status="active",
            public_code_base=code[:8],
            terms_accepted_at=now,
        )
        db.add(profile)
        db.flush()
    else:
        profile.status = "active"
        if profile.terms_accepted_at is None:
            profile.terms_accepted_at = now
        if not profile.public_code_base:
            profile.public_code_base = code[:8]

    participant = db.scalar(
        select(AmbassadorParticipant).where(
            AmbassadorParticipant.campaign_id == campaign.id,
            AmbassadorParticipant.ambassador_profile_id == profile.id,
        )
    )
    if participant is None:
        clash = db.scalar(
            select(AmbassadorParticipant).where(
                AmbassadorParticipant.campaign_id == campaign.id,
                AmbassadorParticipant.ambassador_code == code,
            )
        )
        use_code = code if clash is None else f"{code}x"
        participant = AmbassadorParticipant(
            campaign_id=campaign.id,
            ambassador_profile_id=profile.id,
            user_id=user.id,
            ambassador_code=use_code,
            status="active",
            joined_at=now,
        )
        db.add(participant)
        db.flush()
    else:
        participant.ambassador_code = code
        participant.status = "active"
        if participant.user_id != user.id:
            participant.user_id = user.id

    # Keep v1 + domain codes aligned for dual-write checkout.
    ambassador.referral_code = participant.ambassador_code
    _mark(
        db,
        f"participant:{participant.ambassador_code}",
        participant.id,
        ambassador_id=str(ambassador.id),
    )
    db.flush()
    return ambassador, participant


def _ensure_clicks(
    db: Session,
    *,
    event: Event,
    campaign: AmbassadorCampaign,
    ambassador: Ambassador,
    participant: AmbassadorParticipant,
    target: int,
) -> int:
    created = 0
    v1_count = int(
        db.scalar(
            select(func.count())
            .select_from(PromoClick)
            .where(PromoClick.ambassador_id == ambassador.id)
        )
        or 0
    )
    domain_count = int(
        db.scalar(
            select(func.count())
            .select_from(AmbassadorClick)
            .where(AmbassadorClick.participant_id == participant.id)
        )
        or 0
    )
    landing = f"/events/{event.slug}?ref={ambassador.referral_code}"
    for i in range(max(0, target - v1_count)):
        db.add(
            PromoClick(
                ambassador_id=ambassador.id,
                event_id=event.id,
                landing_path=landing,
                ip_hash=f"demo-amb-{ambassador.referral_code}-{v1_count + i}",
                user_agent_hash=f"demo-ua-{ambassador.referral_code}",
            )
        )
        created += 1
    for i in range(max(0, target - domain_count)):
        db.add(
            AmbassadorClick(
                campaign_id=campaign.id,
                participant_id=participant.id,
                event_id=event.id,
                session_id=f"demo-sess-{participant.ambassador_code}-{domain_count + i}",
                ip_hash=f"demo-amb-{participant.ambassador_code}-{domain_count + i}",
                user_agent_hash=f"demo-ua-{participant.ambassador_code}",
                landing_url=landing,
                referrer_url="https://demo.padeye.test/share",
            )
        )
        created += 1
    if created:
        db.flush()
    return created


def _ga_ticket(event: Event) -> TicketType | None:
    types = list(event.ticket_types or [])
    preferred = [
        t
        for t in types
        if t.status == "active"
        and t.type in {"regular", "early_bird", "vip", "vvip", "free", "free_rsvp"}
    ]
    pool = preferred or [t for t in types if t.status == "active"]
    for t in pool:
        # Reserve headroom for ambassador demo ledger orders.
        if t.quantity is not None and (t.quantity - (t.quantity_sold or 0)) < 12:
            t.quantity = (t.quantity_sold or 0) + 24
        if t.quantity is None or (t.quantity_sold or 0) < t.quantity:
            return t
    return pool[0] if pool else None


def _merch_variant(db: Session, event: Event) -> EventMerchVariant | None:
    products = list(
        db.scalars(
            select(EventMerchProduct)
            .where(
                EventMerchProduct.event_id == event.id,
                EventMerchProduct.archived_at.is_(None),
            )
            .options(selectinload(EventMerchProduct.variants))
        ).all()
    )
    for product in products:
        for variant in product.variants or []:
            if getattr(variant, "status", "active") == "sold_out":
                continue
            inv = getattr(variant, "inventory_count", None)
            sold = getattr(variant, "quantity_sold", 0) or 0
            if inv is not None and sold >= inv:
                continue
            return variant
    return None


def _pay_order(db: Session, order: Order, buyer: User) -> Order | None:
    order = get_order_by_id(db, order.id)
    if order is None:
        return None
    if order.status == "paid":
        return order
    if order.total_amount <= 0:
        return order
    payment = Payment(
        order_id=order.id,
        provider="paystack",
        reference=order.reference,
        amount=order.total_amount,
        currency=order.currency,
        status="pending",
    )
    db.add(payment)
    db.flush()
    finalize_successful_payment(
        db,
        order=order,
        payment=payment,
        provider_payment_id=f"demo_amb_{order.reference}",
        raw_payload={"demo": True, "ambassador": True, "reference": order.reference},
        actor_user_id=buyer.id,
    )
    return get_order_by_id(db, order.id)


def _apply_commission_statuses(
    db: Session,
    *,
    order: Order,
    v1_status: str | None,
    domain_status: str | None,
) -> None:
    now = _now()
    sale = db.scalar(
        select(AmbassadorSale).where(AmbassadorSale.order_id == order.id)
    )
    if sale is not None and v1_status:
        sale.status = v1_status
        if v1_status == "reversed":
            sale.reversed_at = now
            sale.reversal_reason = "Demo refund / reversed commission sample"
        elif v1_status == "approved":
            sale.reward_status_updated_at = now
            # Past hold so host payable summary includes this row.
            sale.hold_until = now - timedelta(days=1)

    conversions = list(
        db.scalars(
            select(AmbassadorConversion).where(
                (AmbassadorConversion.order_id == order.id)
                | (AmbassadorConversion.merch_order_id == order.id)
            )
        ).all()
    )
    for row in conversions:
        if not domain_status:
            continue
        row.status = domain_status
        if domain_status == "reversed":
            row.refunded_at = now
        elif domain_status in {"approved", "payable", "pending"}:
            row.verified_at = row.verified_at or now
    db.flush()


def _ensure_attribution(
    db: Session,
    *,
    campaign: AmbassadorCampaign,
    participant: AmbassadorParticipant,
    event: Event,
    buyer: User | None,
    session_suffix: str,
) -> AmbassadorAttribution:
    session_id = f"demo-attr-{participant.ambassador_code}-{session_suffix}"
    existing = db.scalar(
        select(AmbassadorAttribution).where(
            AmbassadorAttribution.session_id == session_id
        )
    )
    if existing is not None:
        return existing
    row = AmbassadorAttribution(
        campaign_id=campaign.id,
        participant_id=participant.id,
        user_id=buyer.id if buyer else None,
        session_id=session_id,
        event_id=event.id,
        source="link",
        expires_at=_now() + timedelta(days=30),
    )
    db.add(row)
    db.flush()
    return row


def _seed_ledger_row(
    db: Session,
    *,
    event: Event,
    campaign: AmbassadorCampaign,
    by_code: dict[str, tuple[Ambassador, AmbassadorParticipant]],
    spec: dict[str, Any],
) -> bool:
    key = str(spec["key"])
    if _marked(db, f"ledger:{key}"):
        return False

    pair = by_code.get(str(spec["code"]))
    if pair is None:
        return False
    ambassador, participant = pair
    buyer = get_user_by_email(db, str(spec["buyer"]))
    if buyer is None:
        return False

    kind = str(spec["kind"])
    if kind == "checkout":
        attr = _ensure_attribution(
            db,
            campaign=campaign,
            participant=participant,
            event=event,
            buyer=buyer,
            session_suffix=key,
        )
        ticket = _ga_ticket(event)
        if ticket is None:
            _mark(db, f"ledger:{key}", attr.id, kind="checkout_attr_only")
            return True
        order = _safe(
            db,
            create_order,
            db,
            user=buyer,
            payload=OrderCreate(
                event_id=event.id,
                items=[OrderItemCreate(ticket_type_id=ticket.id, quantity=1)],
                checkout_answers=_checkout_answers(event, buyer_index=hash(key) % 90),
                referral_code=ambassador.referral_code,
                ambassador_attribution_id=attr.id,
            ),
        )
        if order is None:
            return False
        _mark(
            db,
            f"ledger:{key}",
            order.id,
            kind="checkout",
            code=ambassador.referral_code,
        )
        return True

    items: list[OrderItemCreate] = []
    if kind == "ticket":
        ticket = _ga_ticket(event)
        if ticket is None:
            return False
        items.append(OrderItemCreate(ticket_type_id=ticket.id, quantity=1))
    elif kind == "merch":
        variant = _merch_variant(db, event)
        if variant is None:
            # Fall back to a ticket so the ledger still demos commission states.
            ticket = _ga_ticket(event)
            if ticket is None:
                return False
            items.append(OrderItemCreate(ticket_type_id=ticket.id, quantity=1))
            kind = "ticket"
        else:
            items.append(
                OrderItemCreate(
                    item_kind="merch",
                    merch_variant_id=variant.id,
                    quantity=1,
                )
            )
    else:
        return False

    attr = _ensure_attribution(
        db,
        campaign=campaign,
        participant=participant,
        event=event,
        buyer=buyer,
        session_suffix=key,
    )
    order = _safe(
        db,
        create_order,
        db,
        user=buyer,
        payload=OrderCreate(
            event_id=event.id,
            items=items,
            checkout_answers=_checkout_answers(event, buyer_index=hash(key) % 90),
            referral_code=ambassador.referral_code,
            ambassador_attribution_id=attr.id,
            fulfillment_method="pickup" if kind == "merch" else None,
        ),
    )
    if order is None:
        return False

    paid = _safe(db, _pay_order, db, order, buyer)
    if paid is None:
        return False

    _apply_commission_statuses(
        db,
        order=paid,
        v1_status=spec.get("v1_status"),
        domain_status=spec.get("domain_status"),
    )
    _mark(
        db,
        f"ledger:{key}",
        paid.id,
        kind=kind,
        code=ambassador.referral_code,
        v1_status=spec.get("v1_status"),
        domain_status=spec.get("domain_status"),
    )
    return True


def seed_demo_open_ambassadors(
    db: Session,
    *,
    users: dict[str, User],
    hosts: dict[str, Host],
    events: dict[str, Event],
) -> dict[str, int]:
    """Seed Afrobeats Night open Ambassadors campaign + demo funnel ledger."""
    counts = {
        "open_ambassador_campaigns": 0,
        "open_ambassador_participants": 0,
        "open_ambassador_clicks": 0,
        "open_ambassador_ledger_rows": 0,
    }

    host = hosts.get("djmaze")
    if host is None:
        return counts
    owner = users.get(f"host@{DEMO_EMAIL_DOMAIN}") or db.get(User, host.user_id)
    if owner is None:
        return counts

    event = _resolve_event(db, events)
    if event is None or event.status not in {"published", "paused"}:
        return counts

    campaign = _ensure_campaign(db, host=host, event=event, owner=owner)
    counts["open_ambassador_campaigns"] = 1

    by_code: dict[str, tuple[Ambassador, AmbassadorParticipant]] = {}
    for spec in OPEN_AMBASSADOR_PARTICIPANTS:
        email = str(spec["email"])
        user = users.get(email) or get_user_by_email(db, email)
        if user is None:
            continue
        ambassador, participant = _ensure_participant(
            db,
            campaign=campaign,
            event=event,
            user=user,
            display_name=str(spec["display_name"]),
            code=str(spec["code"]),
        )
        by_code[str(spec["code"]).lower()] = (ambassador, participant)
        counts["open_ambassador_participants"] += 1
        counts["open_ambassador_clicks"] += _ensure_clicks(
            db,
            event=event,
            campaign=campaign,
            ambassador=ambassador,
            participant=participant,
            target=int(spec.get("clicks") or 5),
        )

    db.commit()

    # Reload event after commits from create_order paths.
    event = _resolve_event(db, events) or event
    for spec in _LEDGER:
        if _seed_ledger_row(
            db,
            event=event,
            campaign=campaign,
            by_code=by_code,
            spec=spec,
        ):
            counts["open_ambassador_ledger_rows"] += 1
            try:
                db.commit()
            except Exception:
                db.rollback()

    db.commit()
    return counts
