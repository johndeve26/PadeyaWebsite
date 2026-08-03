"""Admin Ambassadors: global settings, campaigns, conversions, rewards."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.events.models import Event
from app.events.service import get_event_by_id
from app.hosts.models import Host
from app.promos.campaigns import (
    OPEN_STATUSES,
    STATUS_ENDED,
    STATUS_PAUSED,
    STATUS_PUBLIC_OPEN,
    _sync_event_open_flags,
    campaign_is_live,
    default_campaign_name,
    merch_included_for_type,
    normalize_campaign_type,
    serialize_campaign,
)
from app.promos.constants import CAMPAIGN_TYPE_LABELS
from app.promos.models import (
    Ambassador,
    AmbassadorCampaign,
    AmbassadorPlatformSettings,
    AmbassadorSale,
    PromoClick,
)
from app.promos.schemas import AmbassadorCampaignCreate
from app.users.lifecycle_service import set_ambassadors_blocked
from app.users.models import User

SOURCE_HOST = "host"
SOURCE_PLATFORM = "platform"
SALE_ACTIVE = {"attributed", "approved", "paid"}
SETTINGS_ROW_ID = 1


def get_or_create_platform_settings(db: Session) -> AmbassadorPlatformSettings:
    row = db.get(AmbassadorPlatformSettings, SETTINGS_ROW_ID)
    if row is not None:
        return row
    row = AmbassadorPlatformSettings(id=SETTINGS_ROW_ID, enabled=True)
    db.add(row)
    db.flush()
    return row


def is_ambassadors_feature_enabled(db: Session) -> bool:
    return bool(get_or_create_platform_settings(db).enabled)


def get_platform_settings(db: Session) -> dict:
    row = get_or_create_platform_settings(db)
    return {
        "enabled": row.enabled,
        "updated_at": row.updated_at,
        "updated_by_user_id": row.updated_by_user_id,
    }


def set_platform_enabled(
    db: Session, *, admin: User, enabled: bool
) -> dict:
    row = get_or_create_platform_settings(db)
    row.enabled = enabled
    row.updated_by_user_id = admin.id
    row.updated_at = datetime.now(UTC)
    write_audit_log(
        db,
        action="ambassadors.platform_settings_update",
        actor_user_id=admin.id,
        resource_type="ambassador_platform_settings",
        resource_id=str(row.id),
        details={"enabled": enabled},
    )
    db.commit()
    db.refresh(row)
    return get_platform_settings(db)


def list_all_campaigns(
    db: Session,
    *,
    status: str | None = None,
    source: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    stmt = select(AmbassadorCampaign).order_by(AmbassadorCampaign.created_at.desc())
    if status:
        stmt = stmt.where(AmbassadorCampaign.status == status)
    if source:
        stmt = stmt.where(AmbassadorCampaign.source == source)
    rows = list(db.scalars(stmt.offset(offset).limit(limit)).all())
    out = []
    for campaign in rows:
        data = serialize_campaign(db, campaign)
        host = db.get(Host, campaign.host_id)
        data["source"] = getattr(campaign, "source", SOURCE_HOST) or SOURCE_HOST
        data["created_by_user_id"] = getattr(campaign, "created_by_user_id", None)
        data["host_display_name"] = host.display_name if host else None
        out.append(data)
    return out


def create_platform_campaign(
    db: Session, *, admin: User, payload: AmbassadorCampaignCreate
) -> dict:
    event = get_event_by_id(db, payload.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

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

    from app.promos.commission import resolve_campaign_commission_input

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
        host_id=event.host_id,
        event_id=event.id,
        name=payload.name.strip()
        or default_campaign_name(event.title, campaign_type),
        status=status,
        source=SOURCE_PLATFORM,
        created_by_user_id=admin.id,
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
        actor_user_id=admin.id,
        resource_type="ambassador_campaign",
        resource_id=str(campaign.id),
        details={
            "event_id": str(event.id),
            "status": campaign.status,
            "source": SOURCE_PLATFORM,
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
    data = serialize_campaign(db, campaign)
    data["source"] = SOURCE_PLATFORM
    data["created_by_user_id"] = admin.id
    return data


def admin_pause_campaign(
    db: Session, *, admin: User, campaign_id: UUID, reason: str | None = None
) -> dict:
    campaign = db.get(AmbassadorCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == STATUS_ENDED:
        raise HTTPException(status_code=400, detail="Ended campaigns cannot be paused")
    campaign.status = STATUS_PAUSED
    _sync_event_open_flags(db, campaign)
    write_audit_log(
        db,
        action="ambassadors.campaign_admin_pause",
        actor_user_id=admin.id,
        resource_type="ambassador_campaign",
        resource_id=str(campaign.id),
        details={"reason": (reason or "").strip() or None},
    )
    db.commit()
    db.refresh(campaign)
    data = serialize_campaign(db, campaign)
    data["source"] = getattr(campaign, "source", SOURCE_HOST)
    return data


def admin_resume_campaign(db: Session, *, admin: User, campaign_id: UUID) -> dict:
    campaign = db.get(AmbassadorCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == STATUS_ENDED:
        raise HTTPException(status_code=400, detail="Ended campaigns cannot be resumed")
    campaign.status = STATUS_PUBLIC_OPEN
    _sync_event_open_flags(db, campaign)
    write_audit_log(
        db,
        action="ambassadors.campaign_admin_resume",
        actor_user_id=admin.id,
        resource_type="ambassador_campaign",
        resource_id=str(campaign.id),
        details={},
    )
    db.commit()
    db.refresh(campaign)
    data = serialize_campaign(db, campaign)
    data["source"] = getattr(campaign, "source", SOURCE_HOST)
    return data


def list_admin_ambassadors(
    db: Session,
    *,
    q: str | None = None,
    status: str | None = None,
    blocked_only: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    stmt = (
        select(Ambassador, User)
        .outerjoin(User, User.id == Ambassador.user_id)
        .order_by(Ambassador.created_at.desc())
    )
    if status:
        stmt = stmt.where(Ambassador.status == status)
    if blocked_only:
        stmt = stmt.where(User.ambassadors_blocked.is_(True))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Ambassador.display_name.ilike(like),
                Ambassador.referral_code.ilike(like),
                Ambassador.email.ilike(like),
                User.email.ilike(like),
            )
        )
    rows = list(db.execute(stmt.offset(offset).limit(limit)).all())
    out: list[dict] = []
    for amb, user in rows:
        event = db.get(Event, amb.event_id) if amb.event_id else None
        out.append(
            {
                "id": amb.id,
                "host_id": amb.host_id,
                "event_id": amb.event_id,
                "campaign_id": amb.campaign_id,
                "user_id": amb.user_id,
                "program_id": getattr(amb, "program_id", None),
                "program_kind": amb.program_kind,
                "referral_code": amb.referral_code,
                "display_name": amb.display_name,
                "email": amb.email or (user.email if user else None),
                "status": amb.status,
                "commission_rate_percent": amb.commission_rate_percent,
                "created_at": amb.created_at,
                "event_title": event.title if event else None,
                "ambassadors_blocked": bool(
                    getattr(user, "ambassadors_blocked", False) if user else False
                ),
            }
        )
    return out


def admin_block_ambassador_user(
    db: Session, *, admin: User, ambassador_id: UUID, blocked: bool
) -> dict:
    amb = db.get(Ambassador, ambassador_id)
    if amb is None:
        raise HTTPException(status_code=404, detail="Ambassador not found")
    if amb.user_id is None:
        raise HTTPException(
            status_code=400,
            detail="This ambassador has no linked user account to block",
        )
    set_ambassadors_blocked(
        db, admin=admin, user_id=amb.user_id, blocked=blocked
    )
    user = db.get(User, amb.user_id)
    return {
        "ambassador_id": amb.id,
        "user_id": amb.user_id,
        "ambassadors_blocked": bool(
            getattr(user, "ambassadors_blocked", False) if user else blocked
        ),
    }


def _serialize_conversion(db: Session, sale: AmbassadorSale) -> dict:
    from app.ambassadors.rewards import serialize_conversion

    return serialize_conversion(db, sale, include_order_refs=True)


def list_conversions(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    from app.ambassadors.rewards import serialize_conversion

    stmt = select(AmbassadorSale).order_by(AmbassadorSale.created_at.desc())
    if status:
        stmt = stmt.where(AmbassadorSale.status == status)
    rows = list(db.scalars(stmt.offset(offset).limit(limit)).all())
    return [serialize_conversion(db, s, include_order_refs=True) for s in rows]


def reverse_conversion(
    db: Session, *, admin: User, sale_id: UUID, reason: str
) -> dict:
    from app.ambassadors.rewards import reverse_conversion as shared_reverse

    return shared_reverse(db, actor=admin, sale_id=sale_id, reason=reason)


def set_conversion_reward_status(
    db: Session,
    *,
    admin: User,
    sale_id: UUID,
    status: str,
    reason: str | None = None,
    payout_reference: str | None = None,
    payout_note: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    from app.ambassadors.rewards import set_conversion_reward_status as shared_set

    return shared_set(
        db,
        actor=admin,
        sale_id=sale_id,
        status=status,
        reason=reason,
        payout_reference=payout_reference,
        payout_note=payout_note,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def reports_summary(db: Session) -> dict:
    settings = get_platform_settings(db)
    campaigns = list(db.scalars(select(AmbassadorCampaign)).all())
    ambassadors = list(db.scalars(select(Ambassador)).all())
    sales = list(db.scalars(select(AmbassadorSale)).all())
    from app.ambassadors.referral_click_stats import referral_click_metrics

    click_metrics = referral_click_metrics(db)
    clicks = click_metrics["total_clicks"]
    unique_clicks = click_metrics["unique_clicks"]
    if clicks == 0:
        clicks = int(db.scalar(select(func.count()).select_from(PromoClick)) or 0)
        unique_clicks = clicks

    active_sales = [s for s in sales if s.status in SALE_ACTIVE]
    reversed_sales = [s for s in sales if s.status == "reversed"]
    approved = [s for s in sales if s.status in {"approved", "paid"}]
    payable = [s for s in sales if s.status == "approved"]
    paid = [s for s in sales if s.status == "paid"]

    def _sum(rows: list[AmbassadorSale], field: str) -> Decimal:
        return sum((getattr(r, field) for r in rows), Decimal("0")).quantize(
            Decimal("0.01")
        )

    return {
        "feature_enabled": settings["enabled"],
        "campaigns_total": len(campaigns),
        "campaigns_live": sum(1 for c in campaigns if campaign_is_live(c)),
        "campaigns_paused": sum(1 for c in campaigns if c.status == STATUS_PAUSED),
        "campaigns_platform": sum(
            1 for c in campaigns if getattr(c, "source", SOURCE_HOST) == SOURCE_PLATFORM
        ),
        "ambassadors_total": len(ambassadors),
        "ambassadors_active": sum(1 for a in ambassadors if a.status == "active"),
        "clicks": clicks,
        "total_clicks": clicks,
        "unique_clicks": unique_clicks,
        "conversions_total": len(sales),
        "conversions_active": len(active_sales),
        "conversions_reversed": len(reversed_sales),
        "revenue_generated": _sum(active_sales, "revenue_amount"),
        "commission_owed": _sum(active_sales, "commission_owed"),
        "estimated_earnings": _sum(active_sales, "commission_owed"),
        "approved_earnings": _sum(approved, "commission_owed"),
        "payable_earnings": _sum(payable, "commission_owed"),
        "paid_earnings": _sum(paid, "commission_owed"),
    }
