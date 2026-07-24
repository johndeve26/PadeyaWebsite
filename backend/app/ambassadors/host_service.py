"""Host Ambassadors APIs (phase 10)."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ambassadors.audit import write_ambassador_audit
from app.ambassadors.service import (
    normalize_domain_campaign_type,
    serialize_campaign,
)
from app.events.service import get_event_by_id
from app.hosts.models import Host, HostProfile
from app.hosts.team_access import require_host_for_permission
from app.promos.ambassador_domain import (
    AmbassadorClick,
    AmbassadorConversion,
    AmbassadorParticipant,
    AmbassadorPayout,
)
from app.promos.constants import (
    DOMAIN_CAMPAIGN_STATUS_ACTIVE,
    DOMAIN_CAMPAIGN_STATUS_ENDED,
    DOMAIN_CAMPAIGN_STATUS_PAUSED,
    DOMAIN_CAMPAIGN_TYPE_EVENT,
    DOMAIN_CAMPAIGN_TYPE_MERCH,
    VISIBILITY_PUBLIC_OPEN,
    CAMPAIGN_VISIBILITIES,
)
from app.promos.models import AmbassadorCampaign
from app.users.models import User

HOST_OPEN_STATUSES = frozenset(
    {
        DOMAIN_CAMPAIGN_STATUS_ACTIVE,
        DOMAIN_CAMPAIGN_STATUS_PAUSED,
        "public_open",  # v1 rows
    }
)


def _q(amount: Decimal) -> Decimal:
    return Decimal(amount).quantize(Decimal("0.01"))


def _host_profile_id(db: Session, host_id: UUID) -> UUID | None:
    return db.scalar(
        select(HostProfile.id).where(HostProfile.host_id == host_id)
    )


def _acting_host(
    db: Session,
    *,
    user: User,
    host_id: UUID | None,
    permission: str | tuple[str, ...],
) -> Host:
    host, _ = require_host_for_permission(
        db, user=user, host_id=host_id, permission=permission
    )
    return host


def _assert_host_campaign(
    db: Session,
    *,
    user: User,
    campaign_id: UUID,
    host_id: UUID | None = None,
    permission: str | tuple[str, ...] = "ambassadors.view",
) -> tuple[AmbassadorCampaign, Host]:
    host = _acting_host(db, user=user, host_id=host_id, permission=permission)
    campaign = db.get(AmbassadorCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.host_id != host.id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if (campaign.source or "").lower() == "platform":
        raise HTTPException(
            status_code=403,
            detail="Platform campaigns are managed by Pàdéyá admin",
        )
    return campaign, host


def list_host_campaigns(
    db: Session, user: User, *, host_id: UUID | None = None
) -> list[dict]:
    host = _acting_host(
        db, user=user, host_id=host_id, permission="ambassadors.view"
    )
    rows = list(
        db.scalars(
            select(AmbassadorCampaign)
            .where(
                AmbassadorCampaign.host_id == host.id,
                AmbassadorCampaign.source != "platform",
            )
            .order_by(AmbassadorCampaign.created_at.desc())
        )
    )
    return [serialize_campaign(db, c) for c in rows]


def create_host_campaign(
    db: Session, *, user: User, payload, host_id: UUID | None = None
) -> dict:
    host = _acting_host(
        db,
        user=user,
        host_id=host_id,
        permission="ambassadors.create_campaigns",
    )
    campaign_type = normalize_domain_campaign_type(payload.campaign_type)

    if campaign_type in {DOMAIN_CAMPAIGN_TYPE_EVENT, DOMAIN_CAMPAIGN_TYPE_MERCH}:
        if payload.event_id is None:
            raise HTTPException(
                status_code=400,
                detail="event_id is required for event/merch campaigns",
            )
        event = get_event_by_id(db, payload.event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        if event.host_id != host.id:
            raise HTTPException(
                status_code=403, detail="You can only create campaigns for your events"
            )
        existing = db.scalar(
            select(AmbassadorCampaign).where(
                AmbassadorCampaign.event_id == event.id,
                AmbassadorCampaign.campaign_type.in_(
                    (
                        campaign_type,
                        "event_tickets"
                        if campaign_type == DOMAIN_CAMPAIGN_TYPE_EVENT
                        else "event_merch",
                    )
                ),
                AmbassadorCampaign.status.in_(tuple(HOST_OPEN_STATUSES)),
            )
        )
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="An open campaign of this type already exists for the event",
            )
    else:
        event = None

    visibility = (payload.visibility or VISIBILITY_PUBLIC_OPEN).strip().lower()
    if visibility not in CAMPAIGN_VISIBILITIES:
        raise HTTPException(status_code=400, detail="Invalid visibility")
    status = (payload.status or DOMAIN_CAMPAIGN_STATUS_ACTIVE).strip().lower()
    if status not in {
        "draft",
        DOMAIN_CAMPAIGN_STATUS_ACTIVE,
        DOMAIN_CAMPAIGN_STATUS_PAUSED,
        "public_open",
    }:
        raise HTTPException(status_code=400, detail="Invalid campaign status")

    try:
        rules = resolve_campaign_commission_input(
            campaign_type=(
                "event_merch"
                if campaign_type == DOMAIN_CAMPAIGN_TYPE_MERCH
                else "event_tickets"
            ),
            commission_type=payload.commission_type,
            commission_value=payload.commission_value,
            commission_percent=payload.commission_percent,
            applies_to=payload.applies_to,
            hold_period_days=payload.hold_period_days,
            payout_minimum=payload.payout_minimum,
            max_commission_per_order=payload.max_commission_per_order,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    campaign = AmbassadorCampaign(
        host_id=host.id,
        host_profile_id=_host_profile_id(db, host.id),
        event_id=payload.event_id,
        merch_product_id=payload.merch_product_id,
        name=payload.name.strip(),
        description=payload.description,
        status=status,
        visibility=visibility,
        source="host",
        created_by_user_id=user.id,
        campaign_type=campaign_type,
        commission_percent=rules["commission_percent"],
        commission_type=rules["commission_type"],
        commission_value=rules["commission_value"],
        applies_to=rules["applies_to"],
        hold_period_days=rules["hold_period_days"],
        cookie_window_days=int(payload.cookie_window_days or 30),
        payout_minimum=rules["payout_minimum"],
        max_commission_per_order=rules["max_commission_per_order"],
        allow_host_owner_commission=bool(
            getattr(payload, "allow_host_owner_commission", False)
        ),
        merch_included=campaign_type == DOMAIN_CAMPAIGN_TYPE_MERCH,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    db.add(campaign)
    db.flush()
    write_ambassador_audit(
        db,
        action="ambassadors.campaign_create",
        entity_type="ambassador_campaign",
        entity_id=campaign.id,
        actor_user_id=user.id,
        metadata={
            "campaign_type": campaign_type,
            "status": status,
            "visibility": visibility,
        },
    )
    db.commit()
    db.refresh(campaign)
    return serialize_campaign(db, campaign)


def get_host_campaign(
    db: Session,
    *,
    user: User,
    campaign_id: UUID,
    host_id: UUID | None = None,
) -> dict:
    campaign, _host = _assert_host_campaign(
        db,
        user=user,
        campaign_id=campaign_id,
        host_id=host_id,
        permission="ambassadors.view",
    )
    return serialize_campaign(db, campaign)


def update_host_campaign(
    db: Session,
    *,
    user: User,
    campaign_id: UUID,
    payload,
    host_id: UUID | None = None,
) -> dict:
    campaign, _host = _assert_host_campaign(
        db,
        user=user,
        campaign_id=campaign_id,
        host_id=host_id,
        permission="ambassadors.edit_campaigns",
    )
    if campaign.status in {DOMAIN_CAMPAIGN_STATUS_ENDED, "ended", "archived"}:
        raise HTTPException(status_code=400, detail="Ended campaigns cannot be edited")

    data = payload.model_dump(exclude_unset=True)
    commission_keys = {
        "commission_type",
        "commission_value",
        "commission_percent",
        "applies_to",
        "hold_period_days",
        "payout_minimum",
        "max_commission_per_order",
    }
    if commission_keys & data.keys():
        try:
            rules = resolve_campaign_commission_input(
                campaign_type=(
                    "event_merch"
                    if campaign.campaign_type
                    in {DOMAIN_CAMPAIGN_TYPE_MERCH, "event_merch"}
                    else "event_tickets"
                ),
                commission_type=data.get(
                    "commission_type", campaign.commission_type
                ),
                commission_value=data.get(
                    "commission_value",
                    data.get("commission_percent", campaign.commission_value),
                ),
                commission_percent=data.get(
                    "commission_percent", campaign.commission_percent
                ),
                applies_to=data.get("applies_to", campaign.applies_to),
                hold_period_days=data.get(
                    "hold_period_days", campaign.hold_period_days
                ),
                payout_minimum=data.get(
                    "payout_minimum", campaign.payout_minimum
                ),
                max_commission_per_order=data.get(
                    "max_commission_per_order",
                    campaign.max_commission_per_order,
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        for key, value in rules.items():
            if key in {
                "free_ticket_after_sales",
                "leaderboard_reward_enabled",
                "leaderboard_reward_description",
            }:
                continue
            setattr(campaign, key, value)

    for key, value in data.items():
        if key in commission_keys:
            continue
        if key == "visibility" and value not in CAMPAIGN_VISIBILITIES:
            raise HTTPException(status_code=400, detail="Invalid visibility")
        if key == "name" and isinstance(value, str):
            value = value.strip()
        setattr(campaign, key, value)

    write_ambassador_audit(
        db,
        action="ambassadors.campaign_update",
        entity_type="ambassador_campaign",
        entity_id=campaign.id,
        actor_user_id=user.id,
        metadata=data,
    )
    db.commit()
    db.refresh(campaign)
    return serialize_campaign(db, campaign)


def pause_host_campaign(
    db: Session,
    *,
    user: User,
    campaign_id: UUID,
    host_id: UUID | None = None,
) -> dict:
    campaign, _host = _assert_host_campaign(
        db,
        user=user,
        campaign_id=campaign_id,
        host_id=host_id,
        permission="ambassadors.pause_campaigns",
    )
    if campaign.status in {DOMAIN_CAMPAIGN_STATUS_ENDED, "ended", "archived"}:
        raise HTTPException(status_code=400, detail="Ended campaigns cannot be paused")
    campaign.status = DOMAIN_CAMPAIGN_STATUS_PAUSED
    write_ambassador_audit(
        db,
        action="ambassadors.campaign_pause",
        entity_type="ambassador_campaign",
        entity_id=campaign.id,
        actor_user_id=user.id,
    )
    db.commit()
    db.refresh(campaign)
    from app.ambassadors.notifications import notify_campaign_paused

    notify_campaign_paused(db, campaign=campaign)
    return serialize_campaign(db, campaign)


def end_host_campaign(
    db: Session,
    *,
    user: User,
    campaign_id: UUID,
    host_id: UUID | None = None,
) -> dict:
    campaign, _host = _assert_host_campaign(
        db,
        user=user,
        campaign_id=campaign_id,
        host_id=host_id,
        permission="ambassadors.pause_campaigns",
    )
    campaign.status = DOMAIN_CAMPAIGN_STATUS_ENDED
    write_ambassador_audit(
        db,
        action="ambassadors.campaign_end",
        entity_type="ambassador_campaign",
        entity_id=campaign.id,
        actor_user_id=user.id,
    )
    db.commit()
    db.refresh(campaign)
    from app.ambassadors.notifications import notify_campaign_ended

    notify_campaign_ended(db, campaign=campaign)
    return serialize_campaign(db, campaign)


def list_campaign_participants(
    db: Session,
    *,
    user: User,
    campaign_id: UUID,
    host_id: UUID | None = None,
) -> list[dict]:
    campaign, _host = _assert_host_campaign(
        db,
        user=user,
        campaign_id=campaign_id,
        host_id=host_id,
        permission=("ambassadors.view", "ambassadors.view_conversions"),
    )
    rows = list(
        db.scalars(
            select(AmbassadorParticipant)
            .where(AmbassadorParticipant.campaign_id == campaign.id)
            .order_by(AmbassadorParticipant.joined_at.desc())
        )
    )
    out: list[dict] = []
    for p in rows:
        user_row = db.get(User, p.user_id)
        from app.ambassadors.referral_click_stats import referral_click_metrics

        click_metrics = referral_click_metrics(db, participant_ids=[p.id])
        clicks = click_metrics["total_clicks"]
        unique_clicks = click_metrics["unique_clicks"]
        if clicks == 0:
            clicks = int(
                db.scalar(
                    select(func.count())
                    .select_from(AmbassadorClick)
                    .where(AmbassadorClick.participant_id == p.id)
                )
                or 0
            )
            unique_clicks = clicks
        conversions = list(
            db.scalars(
                select(AmbassadorConversion).where(
                    AmbassadorConversion.participant_id == p.id,
                    AmbassadorConversion.status != "reversed",
                )
            )
        )
        out.append(
            {
                "id": p.id,
                "campaign_id": p.campaign_id,
                "user_id": p.user_id,
                "ambassador_code": p.ambassador_code,
                "status": p.status,
                "joined_at": p.joined_at,
                "display_name": user_row.full_name if user_row else None,
                "clicks": clicks,
                "total_clicks": clicks,
                "unique_clicks": unique_clicks,
                "conversions": len(conversions),
                "commission_amount": _q(
                    sum((c.commission_amount for c in conversions), Decimal("0"))
                ),
            }
        )
    return out


def remove_participant(
    db: Session,
    *,
    user: User,
    participant_id: UUID,
    host_id: UUID | None = None,
) -> dict:
    host = _acting_host(
        db,
        user=user,
        host_id=host_id,
        permission="ambassadors.remove_participants",
    )
    participant = db.get(AmbassadorParticipant, participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    campaign = db.get(AmbassadorCampaign, participant.campaign_id)
    if campaign is None or campaign.host_id != host.id:
        raise HTTPException(status_code=404, detail="Participant not found")
    if (campaign.source or "").lower() == "platform":
        raise HTTPException(
            status_code=403,
            detail="Platform campaigns are managed by Pàdéyá admin",
        )
    participant.status = "removed"
    write_ambassador_audit(
        db,
        action="ambassadors.participant_removed",
        entity_type="ambassador_participant",
        entity_id=participant.id,
        actor_user_id=user.id,
        metadata={"campaign_id": str(campaign.id)},
    )
    db.commit()
    return {"message": "Participant removed"}


def host_analytics(
    db: Session, user: User, *, host_id: UUID | None = None
) -> dict:
    host = _acting_host(
        db, user=user, host_id=host_id, permission="ambassadors.view"
    )
    campaigns = list(
        db.scalars(
            select(AmbassadorCampaign).where(
                AmbassadorCampaign.host_id == host.id,
                AmbassadorCampaign.source != "platform",
            )
        )
    )
    campaign_ids = [c.id for c in campaigns]
    if not campaign_ids:
        zero = Decimal("0.00")
        return {
            "campaigns": 0,
            "active_participants": 0,
            "clicks": 0,
            "total_clicks": 0,
            "unique_clicks": 0,
            "conversions": 0,
            "commission_owed": zero,
            "commission_paid": zero,
        }
    active_participants = int(
        db.scalar(
            select(func.count())
            .select_from(AmbassadorParticipant)
            .where(
                AmbassadorParticipant.campaign_id.in_(campaign_ids),
                AmbassadorParticipant.status == "active",
            )
        )
        or 0
    )
    from app.ambassadors.referral_click_stats import referral_click_metrics

    click_metrics = referral_click_metrics(db, campaign_ids=campaign_ids)
    clicks = click_metrics["total_clicks"]
    unique_clicks = click_metrics["unique_clicks"]
    if clicks == 0:
        clicks = int(
            db.scalar(
                select(func.count())
                .select_from(AmbassadorClick)
                .where(AmbassadorClick.campaign_id.in_(campaign_ids))
            )
            or 0
        )
        unique_clicks = clicks
    conversions = list(
        db.scalars(
            select(AmbassadorConversion).where(
                AmbassadorConversion.campaign_id.in_(campaign_ids)
            )
        )
    )
    owed = _q(
        sum(
            (
                c.commission_amount
                for c in conversions
                if c.status in {"pending", "approved", "payable", "paid"}
            ),
            Decimal("0"),
        )
    )
    paid = _q(
        sum(
            (c.commission_amount for c in conversions if c.status == "paid"),
            Decimal("0"),
        )
    )
    return {
        "campaigns": len(campaigns),
        "active_participants": active_participants,
        "clicks": clicks,
        "total_clicks": clicks,
        "unique_clicks": unique_clicks,
        "conversions": len([c for c in conversions if c.status != "reversed"]),
        "commission_owed": owed,
        "commission_paid": paid,
    }


def list_host_payouts(
    db: Session, user: User, *, host_id: UUID | None = None
) -> list[dict]:
    """Payouts for ambassadors who participate in this host's campaigns."""
    host = _acting_host(
        db,
        user=user,
        host_id=host_id,
        permission=(
            "ambassadors.view_payouts",
            "ambassadors.view",
            "ambassadors.view_conversions",
        ),
    )
    campaign_ids = list(
        db.scalars(
            select(AmbassadorCampaign.id).where(
                AmbassadorCampaign.host_id == host.id,
                AmbassadorCampaign.source != "platform",
            )
        )
    )
    if not campaign_ids:
        return []
    profile_ids = list(
        db.scalars(
            select(AmbassadorParticipant.ambassador_profile_id).where(
                AmbassadorParticipant.campaign_id.in_(campaign_ids)
            ).distinct()
        )
    )
    if not profile_ids:
        return []
    rows = list(
        db.scalars(
            select(AmbassadorPayout)
            .where(AmbassadorPayout.ambassador_profile_id.in_(profile_ids))
            .order_by(AmbassadorPayout.created_at.desc())
        )
    )
    out: list[dict] = []
    for p in rows:
        u = db.get(User, p.user_id)
        out.append(
            {
                "id": p.id,
                "ambassador_profile_id": p.ambassador_profile_id,
                "user_id": p.user_id,
                "amount": p.amount,
                "status": p.status,
                "payout_method": p.payout_method,
                "notes": p.notes,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "display_name": u.full_name if u else None,
            }
        )
    return out
