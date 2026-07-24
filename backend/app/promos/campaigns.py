"""Host ambassador campaign lifecycle and reporting."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.events.models import Event
from app.events.service import assert_can_manage_event, get_event_by_id
from app.hosts.service import require_user_host
from app.promos.commission import (
    resolve_campaign_commission_input,
    sale_is_past_hold,
)
from app.promos.constants import (
    CAMPAIGN_TYPE_EVENT_MERCH,
    CAMPAIGN_TYPE_EVENT_TICKETS,
    CAMPAIGN_TYPE_LABELS,
    CAMPAIGN_TYPES_V1,
    COMMISSION_TYPE_PERCENTAGE,
    DEFAULT_HOLD_PERIOD_DAYS,
)
from app.promos.models import (
    Ambassador,
    AmbassadorCampaign,
    AmbassadorSale,
    PromoClick,
)
from app.promos.schemas import AmbassadorCampaignCreate, AmbassadorCampaignUpdate
from app.users.models import User

STATUS_PUBLIC_OPEN = "public_open"
STATUS_PAUSED = "paused"
STATUS_ENDED = "ended"
LIVE_STATUSES = {STATUS_PUBLIC_OPEN}
OPEN_STATUSES = {STATUS_PUBLIC_OPEN, STATUS_PAUSED}


def normalize_campaign_type(raw: str | None) -> str:
    value = (raw or CAMPAIGN_TYPE_EVENT_TICKETS).strip().lower()
    if value not in CAMPAIGN_TYPES_V1:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid campaign type. v1 supports event_tickets "
                "(Event Ambassador) and event_merch (Event Merch Ambassador)"
            ),
        )
    return value


def merch_included_for_type(campaign_type: str) -> bool:
    return campaign_type == CAMPAIGN_TYPE_EVENT_MERCH


def default_campaign_name(event_title: str, campaign_type: str) -> str:
    label = CAMPAIGN_TYPE_LABELS.get(campaign_type, "Ambassadors")
    return f"{event_title} · {label}"[:200]


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _q(amount: Decimal) -> Decimal:
    from decimal import ROUND_HALF_UP

    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def campaign_is_live(campaign: AmbassadorCampaign, *, now: datetime | None = None) -> bool:
    if campaign.status != STATUS_PUBLIC_OPEN:
        return False
    current = now or datetime.now(UTC)
    if campaign.starts_at is not None and current < _aware(campaign.starts_at):
        return False
    if campaign.ends_at is not None and current > _aware(campaign.ends_at):
        return False
    return True


def list_live_campaigns_for_event(
    db: Session, *, event_id: UUID
) -> list[AmbassadorCampaign]:
    rows = list(
        db.scalars(
            select(AmbassadorCampaign).where(
                AmbassadorCampaign.event_id == event_id,
                AmbassadorCampaign.status == STATUS_PUBLIC_OPEN,
            )
        )
    )
    now = datetime.now(UTC)
    live = [c for c in rows if campaign_is_live(c, now=now)]
    order = {CAMPAIGN_TYPE_EVENT_TICKETS: 0, CAMPAIGN_TYPE_EVENT_MERCH: 1}
    live.sort(
        key=lambda c: order.get(
            getattr(c, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS), 9
        )
    )
    return live


def get_live_campaign_for_event(
    db: Session,
    *,
    event_id: UUID,
    campaign_type: str | None = None,
) -> AmbassadorCampaign | None:
    live = list_live_campaigns_for_event(db, event_id=event_id)
    if not live:
        return None
    if campaign_type:
        wanted = normalize_campaign_type(campaign_type)
        for campaign in live:
            if getattr(campaign, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS) == wanted:
                return campaign
        return None
    # Prefer Event Ambassador (tickets) for legacy callers.
    return live[0]


def _sync_event_open_flags(db: Session, campaign: AmbassadorCampaign) -> None:
    """Enable event open-ambassadors when any campaign type for the event is live."""
    event = db.get(Event, campaign.event_id)
    if event is None:
        return
    live = list_live_campaigns_for_event(db, event_id=campaign.event_id)
    event.open_ambassadors_enabled = bool(live)
    if live:
        tickets = next(
            (
                c
                for c in live
                if getattr(c, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS)
                == CAMPAIGN_TYPE_EVENT_TICKETS
            ),
            live[0],
        )
        event.open_ambassador_commission_percent = tickets.commission_percent


def _campaign_stats(db: Session, campaign: AmbassadorCampaign) -> dict:
    ambassadors = list(
        db.scalars(
            select(Ambassador).where(Ambassador.campaign_id == campaign.id)
        )
    )
    active = [a for a in ambassadors if a.status == "active"]
    ids = [a.id for a in ambassadors]
    clicks = 0
    unique_clicks = 0
    sales: list[AmbassadorSale] = []
    if ids:
        from app.ambassadors.referral_click_stats import ambassador_click_bundle

        click_bundle = ambassador_click_bundle(db, ambassador_ids=ids)
        clicks = click_bundle["total_clicks"]
        unique_clicks = click_bundle["unique_clicks"]
        sales = list(
            db.scalars(
                select(AmbassadorSale).where(AmbassadorSale.ambassador_id.in_(ids))
            )
        )
    counted = [s for s in sales if s.status != "reversed"]
    tickets = sum(s.tickets_sold for s in counted)
    merch = sum(getattr(s, "merch_units_sold", 0) or 0 for s in counted)
    revenue = sum((s.revenue_amount for s in counted), Decimal("0"))
    commission = sum((s.commission_owed for s in counted), Decimal("0"))
    approved = sum(
        (s.commission_owed for s in counted if s.status in {"approved", "paid"}),
        Decimal("0"),
    )
    payable = sum(
        (
            s.commission_owed
            for s in counted
            if s.status == "approved"
            or (s.status == "attributed" and sale_is_past_hold(s))
        ),
        Decimal("0"),
    )
    paid = sum(
        (s.commission_owed for s in counted if s.status == "paid"),
        Decimal("0"),
    )
    conversion = (
        _q(
            Decimal(len(counted))
            / Decimal(unique_clicks if unique_clicks > 0 else clicks)
            * 100
        )
        if (unique_clicks or clicks)
        else Decimal("0")
    )
    return {
        "active_ambassadors": len(active),
        "total_ambassadors": len(ambassadors),
        "clicks": clicks,
        "total_clicks": clicks,
        "unique_clicks": unique_clicks,
        "confirmed_sales": len(counted),
        "tickets_sold": tickets,
        "merch_units_sold": merch,
        "revenue_generated": _q(revenue),
        "conversion_rate": conversion,
        "commission_owed": _q(commission),
        "estimated_earnings": _q(commission),
        "approved_earnings": _q(approved),
        "payable_earnings": _q(payable),
        "paid_earnings": _q(paid),
    }


def serialize_campaign(db: Session, campaign: AmbassadorCampaign) -> dict:
    event = db.get(Event, campaign.event_id)
    stats = _campaign_stats(db, campaign)
    ctype = getattr(campaign, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS)
    return {
        "id": campaign.id,
        "host_id": campaign.host_id,
        "event_id": campaign.event_id,
        "name": campaign.name,
        "status": campaign.status,
        "source": getattr(campaign, "source", "host") or "host",
        "created_by_user_id": getattr(campaign, "created_by_user_id", None),
        "campaign_type": ctype,
        "campaign_type_label": CAMPAIGN_TYPE_LABELS.get(ctype, ctype),
        "commission_percent": campaign.commission_percent,
        "commission_type": getattr(
            campaign, "commission_type", COMMISSION_TYPE_PERCENTAGE
        )
        or COMMISSION_TYPE_PERCENTAGE,
        "commission_value": getattr(
            campaign, "commission_value", campaign.commission_percent
        ),
        "applies_to": getattr(campaign, "applies_to", None)
        or ("merch" if ctype == CAMPAIGN_TYPE_EVENT_MERCH else "tickets"),
        "hold_period_days": int(
            getattr(campaign, "hold_period_days", DEFAULT_HOLD_PERIOD_DAYS)
            or DEFAULT_HOLD_PERIOD_DAYS
        ),
        "payout_minimum": getattr(campaign, "payout_minimum", None),
        "max_commission_per_order": getattr(
            campaign, "max_commission_per_order", None
        ),
        "free_ticket_after_sales": getattr(
            campaign, "free_ticket_after_sales", None
        ),
        "leaderboard_reward_enabled": bool(
            getattr(campaign, "leaderboard_reward_enabled", False)
        ),
        "leaderboard_reward_description": getattr(
            campaign, "leaderboard_reward_description", None
        ),
        "allow_host_owner_commission": bool(
            getattr(campaign, "allow_host_owner_commission", False)
        ),
        "merch_included": campaign.merch_included,
        "starts_at": campaign.starts_at,
        "ends_at": campaign.ends_at,
        "created_at": campaign.created_at,
        "updated_at": campaign.updated_at,
        "event_title": event.title if event else None,
        "event_slug": event.slug if event else None,
        "is_live": campaign_is_live(campaign),
        **stats,
    }


def list_host_campaigns(db: Session, user: User) -> list[dict]:
    host = require_user_host(db, user)
    rows = db.scalars(
        select(AmbassadorCampaign)
        .where(AmbassadorCampaign.host_id == host.id)
        .order_by(AmbassadorCampaign.created_at.desc())
    ).all()
    return [serialize_campaign(db, c) for c in rows]


def get_host_campaign(db: Session, *, user: User, campaign_id: UUID) -> dict:
    host = require_user_host(db, user)
    campaign = db.get(AmbassadorCampaign, campaign_id)
    if campaign is None or campaign.host_id != host.id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return serialize_campaign(db, campaign)


def get_event_campaign(db: Session, *, user: User, event_id: UUID) -> dict | None:
    host = require_user_host(db, user)
    event = get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    assert_can_manage_event(db, user, event, host)
    rows = list_event_open_campaigns(db, event_id=event.id)
    if not rows:
        return None
    return serialize_campaign(db, rows[0])


def list_event_open_campaigns(
    db: Session, *, event_id: UUID
) -> list[AmbassadorCampaign]:
    rows = list(
        db.scalars(
            select(AmbassadorCampaign)
            .where(
                AmbassadorCampaign.event_id == event_id,
                AmbassadorCampaign.status.in_(tuple(OPEN_STATUSES)),
            )
            .order_by(AmbassadorCampaign.created_at.desc())
        )
    )
    order = {CAMPAIGN_TYPE_EVENT_TICKETS: 0, CAMPAIGN_TYPE_EVENT_MERCH: 1}
    rows.sort(
        key=lambda c: (
            0 if c.status == STATUS_PUBLIC_OPEN else 1,
            order.get(getattr(c, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS), 9),
        )
    )
    return rows


def create_campaign(
    db: Session, *, user: User, payload: AmbassadorCampaignCreate
) -> dict:
    host = require_user_host(db, user)
    event = get_event_by_id(db, payload.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    assert_can_manage_event(db, user, event, host)

    campaign_type = normalize_campaign_type(
        getattr(payload, "campaign_type", None)
    )
    existing = db.scalar(
        select(AmbassadorCampaign).where(
            AmbassadorCampaign.event_id == event.id,
            AmbassadorCampaign.campaign_type == campaign_type,
            AmbassadorCampaign.status.in_(tuple(OPEN_STATUSES)),
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"This event already has an active or paused "
                f"{CAMPAIGN_TYPE_LABELS.get(campaign_type, campaign_type)} campaign"
            ),
        )

    status = payload.status or STATUS_PUBLIC_OPEN
    if status not in {STATUS_PUBLIC_OPEN, STATUS_PAUSED}:
        raise HTTPException(status_code=400, detail="Invalid campaign status")

    try:
        rules = resolve_campaign_commission_input(
            campaign_type=campaign_type,
            commission_type=getattr(payload, "commission_type", None),
            commission_value=getattr(payload, "commission_value", None),
            commission_percent=payload.commission_percent,
            applies_to=getattr(payload, "applies_to", None),
            hold_period_days=getattr(payload, "hold_period_days", None),
            payout_minimum=getattr(payload, "payout_minimum", None),
            max_commission_per_order=getattr(
                payload, "max_commission_per_order", None
            ),
            free_ticket_after_sales=getattr(
                payload, "free_ticket_after_sales", None
            ),
            leaderboard_reward_enabled=getattr(
                payload, "leaderboard_reward_enabled", None
            ),
            leaderboard_reward_description=getattr(
                payload, "leaderboard_reward_description", None
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    merch_included = merch_included_for_type(campaign_type)
    campaign = AmbassadorCampaign(
        host_id=host.id,
        event_id=event.id,
        name=payload.name.strip()
        or default_campaign_name(event.title, campaign_type),
        status=status,
        source="host",
        created_by_user_id=user.id,
        campaign_type=campaign_type,
        commission_percent=rules["commission_percent"],
        commission_type=rules["commission_type"],
        commission_value=rules["commission_value"],
        applies_to=rules["applies_to"],
        hold_period_days=rules["hold_period_days"],
        payout_minimum=rules["payout_minimum"],
        max_commission_per_order=rules["max_commission_per_order"],
        free_ticket_after_sales=rules["free_ticket_after_sales"],
        leaderboard_reward_enabled=rules["leaderboard_reward_enabled"],
        leaderboard_reward_description=rules["leaderboard_reward_description"],
        allow_host_owner_commission=bool(
            getattr(payload, "allow_host_owner_commission", False)
        ),
        merch_included=merch_included,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    db.add(campaign)
    db.flush()
    _sync_event_open_flags(db, campaign)
    write_audit_log(
        db,
        action="ambassadors.campaign_create",
        actor_user_id=user.id,
        resource_type="ambassador_campaign",
        resource_id=str(campaign.id),
        details={
            "event_id": str(event.id),
            "status": campaign.status,
            "campaign_type": campaign_type,
            "commission_type": campaign.commission_type,
            "commission_value": str(campaign.commission_value),
            "commission_percent": str(campaign.commission_percent),
            "applies_to": campaign.applies_to,
            "merch_included": campaign.merch_included,
        },
    )
    db.commit()
    db.refresh(campaign)
    return serialize_campaign(db, campaign)


def update_campaign(
    db: Session,
    *,
    user: User,
    campaign_id: UUID,
    payload: AmbassadorCampaignUpdate,
) -> dict:
    host = require_user_host(db, user)
    campaign = db.get(AmbassadorCampaign, campaign_id)
    if campaign is None or campaign.host_id != host.id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == STATUS_ENDED:
        raise HTTPException(status_code=400, detail="Ended campaigns cannot be edited")

    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in {
        STATUS_PUBLIC_OPEN,
        STATUS_PAUSED,
        STATUS_ENDED,
    }:
        raise HTTPException(status_code=400, detail="Invalid campaign status")

    commission_keys = {
        "commission_type",
        "commission_value",
        "commission_percent",
        "applies_to",
        "hold_period_days",
        "payout_minimum",
        "max_commission_per_order",
        "free_ticket_after_sales",
        "leaderboard_reward_enabled",
        "leaderboard_reward_description",
    }
    if commission_keys & data.keys():
        # Prefer explicit commission_value; legacy percent-only updates win over
        # the stored commission_value so hosts can still PATCH commission_percent.
        if "commission_value" in data:
            next_value = data["commission_value"]
        elif "commission_percent" in data:
            next_value = data["commission_percent"]
        else:
            next_value = getattr(campaign, "commission_value", None)
        try:
            rules = resolve_campaign_commission_input(
                campaign_type=getattr(
                    campaign, "campaign_type", CAMPAIGN_TYPE_EVENT_TICKETS
                ),
                commission_type=data.get(
                    "commission_type",
                    getattr(campaign, "commission_type", COMMISSION_TYPE_PERCENTAGE),
                ),
                commission_value=next_value,
                commission_percent=data.get(
                    "commission_percent", campaign.commission_percent
                ),
                applies_to=data.get(
                    "applies_to", getattr(campaign, "applies_to", None)
                ),
                hold_period_days=data.get(
                    "hold_period_days",
                    getattr(campaign, "hold_period_days", DEFAULT_HOLD_PERIOD_DAYS),
                ),
                payout_minimum=data.get(
                    "payout_minimum", getattr(campaign, "payout_minimum", None)
                ),
                max_commission_per_order=data.get(
                    "max_commission_per_order",
                    getattr(campaign, "max_commission_per_order", None),
                ),
                free_ticket_after_sales=data.get(
                    "free_ticket_after_sales",
                    getattr(campaign, "free_ticket_after_sales", None),
                ),
                leaderboard_reward_enabled=data.get(
                    "leaderboard_reward_enabled",
                    getattr(campaign, "leaderboard_reward_enabled", False),
                ),
                leaderboard_reward_description=data.get(
                    "leaderboard_reward_description",
                    getattr(campaign, "leaderboard_reward_description", None),
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        for key, value in rules.items():
            setattr(campaign, key, value)
            data[key] = value

    for key, value in data.items():
        if key in commission_keys:
            continue
        if key == "name" and isinstance(value, str):
            value = value.strip()
        setattr(campaign, key, value)
    _sync_event_open_flags(db, campaign)
    write_audit_log(
        db,
        action="ambassadors.campaign_update",
        actor_user_id=user.id,
        resource_type="ambassador_campaign",
        resource_id=str(campaign.id),
        details=data,
    )
    db.commit()
    db.refresh(campaign)
    return serialize_campaign(db, campaign)


def pause_campaign(db: Session, *, user: User, campaign_id: UUID) -> dict:
    result = update_campaign(
        db,
        user=user,
        campaign_id=campaign_id,
        payload=AmbassadorCampaignUpdate(status=STATUS_PAUSED),
    )
    campaign = db.get(AmbassadorCampaign, campaign_id)
    if campaign is not None:
        from app.ambassadors.notifications import notify_campaign_paused

        notify_campaign_paused(db, campaign=campaign)
    return result


def resume_campaign(db: Session, *, user: User, campaign_id: UUID) -> dict:
    return update_campaign(
        db,
        user=user,
        campaign_id=campaign_id,
        payload=AmbassadorCampaignUpdate(status=STATUS_PUBLIC_OPEN),
    )


def end_campaign(db: Session, *, user: User, campaign_id: UUID) -> dict:
    result = update_campaign(
        db,
        user=user,
        campaign_id=campaign_id,
        payload=AmbassadorCampaignUpdate(status=STATUS_ENDED),
    )
    campaign = db.get(AmbassadorCampaign, campaign_id)
    if campaign is not None:
        from app.ambassadors.notifications import notify_campaign_ended

        notify_campaign_ended(db, campaign=campaign)
    return result


def remove_campaign_ambassador(
    db: Session, *, user: User, campaign_id: UUID, ambassador_id: UUID
) -> None:
    host = require_user_host(db, user)
    campaign = db.get(AmbassadorCampaign, campaign_id)
    if campaign is None or campaign.host_id != host.id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    ambassador = db.get(Ambassador, ambassador_id)
    if (
        ambassador is None
        or ambassador.campaign_id != campaign.id
        or ambassador.host_id != host.id
    ):
        raise HTTPException(status_code=404, detail="Ambassador not found in campaign")
    ambassador.status = "removed"
    write_audit_log(
        db,
        action="ambassadors.campaign_remove",
        actor_user_id=user.id,
        resource_type="ambassador",
        resource_id=str(ambassador.id),
        details={
            "campaign_id": str(campaign.id),
            "event_id": str(campaign.event_id),
            "referral_code": ambassador.referral_code,
        },
    )
    db.commit()


def campaign_leaderboard(
    db: Session, *, user: User, campaign_id: UUID, limit: int = 50
) -> list[dict]:
    host = require_user_host(db, user)
    campaign = db.get(AmbassadorCampaign, campaign_id)
    if campaign is None or campaign.host_id != host.id:
        raise HTTPException(status_code=404, detail="Campaign not found")

    ambassadors = list(
        db.scalars(
            select(Ambassador).where(Ambassador.campaign_id == campaign.id)
        )
    )
    rows: list[dict] = []
    for amb in ambassadors:
        clicks = int(
            db.scalar(
                select(func.count())
                .select_from(PromoClick)
                .where(PromoClick.ambassador_id == amb.id)
            )
            or 0
        )
        sales = list(
            db.scalars(
                select(AmbassadorSale).where(AmbassadorSale.ambassador_id == amb.id)
            )
        )
        counted = [s for s in sales if s.status != "reversed"]
        tickets = sum(s.tickets_sold for s in counted)
        merch = sum(getattr(s, "merch_units_sold", 0) or 0 for s in counted)
        revenue = sum((s.revenue_amount for s in counted), Decimal("0"))
        commission = sum((s.commission_owed for s in counted), Decimal("0"))
        conversion = (
            _q(Decimal(len(counted)) / Decimal(clicks) * 100)
            if clicks
            else Decimal("0")
        )
        rows.append(
            {
                "ambassador_id": amb.id,
                "display_name": amb.display_name,
                "referral_code": amb.referral_code,
                "status": amb.status,
                "clicks": clicks,
                "confirmed_sales": len(counted),
                "tickets_sold": tickets,
                "merch_units_sold": merch,
                "revenue_generated": _q(revenue),
                "conversion_rate": conversion,
                "commission_owed": _q(commission),
            }
        )
    rows.sort(key=lambda r: (r["revenue_generated"], r["clicks"]), reverse=True)
    return rows[:limit]
