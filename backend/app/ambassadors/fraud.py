"""Ambassadors fraud controls (phase 14).

- Self-referral blocked (buyer == ambassador user)
- Host-owner commission blocked unless campaign.allow_host_owner_commission
- Click spike flags (hashed IP/UA signals only — never raw IP)
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ambassadors.audit import write_ambassador_audit
from app.analytics.dimensions import hash_ip, hash_user_agent
from app.core.config import get_settings
from app.events.models import Event
from app.hosts.models import Host, HostProfile
from app.promos.ambassador_domain import (
    AmbassadorFraudFlag,
    AmbassadorParticipant,
)
from app.promos.referral_clicks import ReferralClick
from app.promos.models import Ambassador, AmbassadorCampaign


def request_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None


def hash_tracking_ip(ip: str | None) -> str | None:
    """Salted IP hash for fraud signals. Never store raw IP."""
    return hash_ip(ip)


def hash_tracking_ua(ua: str | None) -> str | None:
    """Salted UA hash for fraud signals. Prefer over raw UA."""
    return hash_user_agent(ua)


def hash_tracking_fingerprint(value: str | None) -> str | None:
    """Salted visitor fingerprint hash — never store raw fingerprint."""
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    secret = get_settings().secret_key
    return hashlib.sha256(f"{secret}|fp|{cleaned}".encode("utf-8")).hexdigest()[:64]


def is_self_referral(
    *, ambassador_user_id: UUID | None, buyer_user_id: UUID | None
) -> bool:
    return (
        ambassador_user_id is not None
        and buyer_user_id is not None
        and ambassador_user_id == buyer_user_id
    )


def campaign_host_id(
    db: Session, campaign: AmbassadorCampaign | None
) -> UUID | None:
    if campaign is None:
        return None
    host_id = getattr(campaign, "host_id", None)
    if host_id is None and getattr(campaign, "event_id", None):
        event = db.get(Event, campaign.event_id)
        host_id = event.host_id if event else None
    if host_id is None and getattr(campaign, "host_profile_id", None):
        profile = db.get(HostProfile, campaign.host_profile_id)
        host_id = profile.host_id if profile else None
    return host_id


def campaign_host_owner_user_id(
    db: Session, campaign: AmbassadorCampaign | None
) -> UUID | None:
    host_id = campaign_host_id(db, campaign)
    if host_id is None:
        return None
    host = db.get(Host, host_id)
    return host.user_id if host else None


def ambassador_host_owner_user_id(
    db: Session, ambassador: Ambassador | None
) -> UUID | None:
    if ambassador is None:
        return None
    if ambassador.campaign_id is not None:
        campaign = db.get(AmbassadorCampaign, ambassador.campaign_id)
        owner = campaign_host_owner_user_id(db, campaign)
        if owner is not None:
            return owner
    if ambassador.host_id is not None:
        host = db.get(Host, ambassador.host_id)
        return host.user_id if host else None
    if ambassador.event_id is not None:
        event = db.get(Event, ambassador.event_id)
        if event is not None and event.host_id is not None:
            host = db.get(Host, event.host_id)
            return host.user_id if host else None
    return None


def ambassador_campaign_host_id(
    db: Session, ambassador: Ambassador | None
) -> UUID | None:
    if ambassador is None:
        return None
    if ambassador.campaign_id is not None:
        campaign = db.get(AmbassadorCampaign, ambassador.campaign_id)
        host_id = campaign_host_id(db, campaign)
        if host_id is not None:
            return host_id
    if ambassador.host_id is not None:
        return ambassador.host_id
    if ambassador.event_id is not None:
        event = db.get(Event, ambassador.event_id)
        return event.host_id if event is not None else None
    return None


def host_owner_commission_allowed(campaign: AmbassadorCampaign | None) -> bool:
    if campaign is None:
        return False
    return bool(getattr(campaign, "allow_host_owner_commission", False))


def is_host_owner_participant(
    db: Session,
    *,
    user_id: UUID | None,
    campaign: AmbassadorCampaign | None = None,
    ambassador: Ambassador | None = None,
) -> bool:
    """True when user owns the campaign/ambassador host (not team/staff)."""
    if user_id is None:
        return False
    host_id: UUID | None = None
    if campaign is not None:
        host_id = campaign_host_id(db, campaign)
    elif ambassador is not None:
        host_id = ambassador_campaign_host_id(db, ambassador)
    if host_id is None:
        return False
    from app.hosts.fan_self_abuse import is_user_owner_of_host

    return is_user_owner_of_host(
        db, user_id=user_id, host_profile_id=host_id
    )


def assert_user_may_join_campaign(
    db: Session, *, user_id: UUID, campaign: AmbassadorCampaign
) -> None:
    """Block campaign host owner from joining unless explicitly allowed."""
    if not is_host_owner_participant(db, user_id=user_id, campaign=campaign):
        return
    if host_owner_commission_allowed(campaign):
        return
    raise HTTPException(
        status_code=403,
        detail=(
            "Campaign host owners cannot join as Ambassadors unless "
            "allow_host_owner_commission is enabled on the campaign"
        ),
    )


def commission_blocked_for_host_owner(
    db: Session,
    *,
    user_id: UUID | None,
    campaign: AmbassadorCampaign | None = None,
    ambassador: Ambassador | None = None,
) -> bool:
    """True when commission must not be created for this promoter."""
    if not is_host_owner_participant(
        db, user_id=user_id, campaign=campaign, ambassador=ambassador
    ):
        return False
    if campaign is not None:
        return not host_owner_commission_allowed(campaign)
    if ambassador is not None and ambassador.campaign_id is not None:
        camp = db.get(AmbassadorCampaign, ambassador.campaign_id)
        return not host_owner_commission_allowed(camp)
    # No campaign flag → default deny for host owners.
    return True


def maybe_flag_click_spike(
    db: Session,
    *,
    campaign_id: UUID,
    participant_id: UUID,
    ip_hash: str | None,
) -> AmbassadorFraudFlag | None:
    """Flag suspicious click volume for the same hashed IP + participant."""
    settings = get_settings()
    from app.runtime_settings import get_runtime_setting

    window = int(
        get_runtime_setting("ambassador_click_spike_window_seconds", db=db, settings=settings)
        or 300
    )
    threshold = int(
        get_runtime_setting("ambassador_click_spike_threshold", db=db, settings=settings)
        or 40
    )
    if threshold <= 0 or window <= 0:
        return None
    if not ip_hash:
        return None

    now = datetime.now(UTC)
    since = now - timedelta(seconds=window)
    count = int(
        db.scalar(
            select(func.count())
            .select_from(ReferralClick)
            .where(
                ReferralClick.participant_id == participant_id,
                ReferralClick.ip_hash == ip_hash,
                ReferralClick.created_at >= since,
                ReferralClick.is_duplicate_30s.is_(False),
            )
        )
        or 0
    )
    if count < threshold:
        return None

    # Dedupe open flags in the same window.
    existing = db.scalar(
        select(AmbassadorFraudFlag)
        .where(
            AmbassadorFraudFlag.flag_type == "click_spike",
            AmbassadorFraudFlag.participant_id == participant_id,
            AmbassadorFraudFlag.ip_hash == ip_hash,
            AmbassadorFraudFlag.status == "open",
            AmbassadorFraudFlag.window_start >= since,
        )
        .order_by(AmbassadorFraudFlag.created_at.desc())
    )
    if existing is not None:
        existing.click_count = count
        existing.window_end = now
        return existing

    flag = AmbassadorFraudFlag(
        flag_type="click_spike",
        campaign_id=campaign_id,
        participant_id=participant_id,
        ip_hash=ip_hash,
        click_count=count,
        window_start=since,
        window_end=now,
        status="open",
        details={
            "threshold": threshold,
            "window_seconds": window,
        },
    )
    db.add(flag)
    db.flush()
    write_ambassador_audit(
        db,
        action="ambassadors.fraud_flag_click_spike",
        entity_type="ambassador_fraud_flag",
        entity_id=flag.id,
        actor_user_id=None,
        metadata={
            "campaign_id": str(campaign_id),
            "participant_id": str(participant_id),
            "click_count": count,
            "threshold": threshold,
        },
    )
    from app.ambassadors.notifications import notify_admins_suspicious_activity

    notify_admins_suspicious_activity(db, flag=flag)
    return flag


def flag_suspicious_conversion(
    db: Session,
    *,
    actor_user_id: UUID | None,
    campaign_id: UUID | None,
    conversion_id: UUID,
    reason: str,
    host_id: UUID | None = None,
) -> dict[str, Any]:
    """Open a fraud flag for a suspicious conversion (host or admin)."""
    clean = (reason or "").strip()
    if len(clean) < 3:
        raise HTTPException(
            status_code=400, detail="Flag reason is required (min 3 characters)"
        )
    # Portable open-flag dedupe (JSON operators differ across dialects).
    existing: AmbassadorFraudFlag | None = None
    open_flags = list(
        db.scalars(
            select(AmbassadorFraudFlag).where(
                AmbassadorFraudFlag.flag_type == "suspicious_conversion",
                AmbassadorFraudFlag.status == "open",
                AmbassadorFraudFlag.campaign_id == campaign_id,
            )
        ).all()
    )
    for row in open_flags:
        details = row.details or {}
        if details.get("conversion_id") == str(conversion_id):
            existing = row
            break

    if existing is not None:
        details = dict(existing.details or {})
        details["reason"] = clean[:500]
        details["host_id"] = str(host_id) if host_id else details.get("host_id")
        existing.details = details
        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "flag_type": existing.flag_type,
            "campaign_id": existing.campaign_id,
            "status": existing.status,
            "details": existing.details or {},
            "created_at": existing.created_at,
        }

    flag = AmbassadorFraudFlag(
        flag_type="suspicious_conversion",
        campaign_id=campaign_id,
        participant_id=None,
        status="open",
        details={
            "conversion_id": str(conversion_id),
            "reason": clean[:500],
            "host_id": str(host_id) if host_id else None,
            "flagged_by_user_id": str(actor_user_id) if actor_user_id else None,
        },
    )
    db.add(flag)
    db.flush()
    write_ambassador_audit(
        db,
        action="ambassadors.fraud_flag_suspicious_conversion",
        entity_type="ambassador_fraud_flag",
        entity_id=flag.id,
        actor_user_id=actor_user_id,
        metadata={
            "conversion_id": str(conversion_id),
            "campaign_id": str(campaign_id) if campaign_id else None,
        },
    )
    from app.ambassadors.notifications import notify_admins_suspicious_activity

    notify_admins_suspicious_activity(db, flag=flag)
    db.commit()
    db.refresh(flag)
    return {
        "id": flag.id,
        "flag_type": flag.flag_type,
        "campaign_id": flag.campaign_id,
        "status": flag.status,
        "details": flag.details or {},
        "created_at": flag.created_at,
    }


def maybe_flag_inflated_click_ratio(
    db: Session,
    *,
    campaign_id: UUID,
    participant_id: UUID,
) -> AmbassadorFraudFlag | None:
    """Soft flag when total clicks far exceed unique visitors (24h window)."""
    from app.ambassadors.referral_click_stats import referral_click_metrics

    metrics = referral_click_metrics(
        db, participant_ids=[participant_id], since=datetime.now(UTC) - timedelta(hours=24)
    )
    total = metrics["total_clicks"]
    unique = metrics["unique_clicks"]
    if total < 25:
        return None
    if unique <= 0:
        ratio = 0.0
    else:
        ratio = unique / total
    if ratio >= 0.35:
        return None

    existing = db.scalar(
        select(AmbassadorFraudFlag)
        .where(
            AmbassadorFraudFlag.flag_type == "click_inflation_suspect",
            AmbassadorFraudFlag.participant_id == participant_id,
            AmbassadorFraudFlag.status == "open",
        )
        .order_by(AmbassadorFraudFlag.created_at.desc())
    )
    if existing is not None:
        existing.click_count = total
        existing.details = {
            **(existing.details or {}),
            "total_clicks": total,
            "unique_clicks": unique,
            "unique_ratio": round(ratio, 3),
        }
        return existing

    flag = AmbassadorFraudFlag(
        flag_type="click_inflation_suspect",
        campaign_id=campaign_id,
        participant_id=participant_id,
        ip_hash=None,
        click_count=total,
        window_start=datetime.now(UTC) - timedelta(hours=24),
        window_end=datetime.now(UTC),
        status="open",
        details={
            "total_clicks": total,
            "unique_clicks": unique,
            "unique_ratio": round(ratio, 3),
            "note": "High total clicks with low unique visitors — review only",
        },
    )
    db.add(flag)
    db.flush()
    return flag


def list_fraud_flags(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    q = select(AmbassadorFraudFlag).order_by(AmbassadorFraudFlag.created_at.desc())
    if status:
        q = q.where(AmbassadorFraudFlag.status == status)
    rows = db.scalars(q.offset(offset).limit(limit)).all()
    out: list[dict[str, Any]] = []
    for row in rows:
        code = None
        if row.participant_id:
            participant = db.get(AmbassadorParticipant, row.participant_id)
            code = participant.ambassador_code if participant else None
        out.append(
            {
                "id": row.id,
                "flag_type": row.flag_type,
                "campaign_id": row.campaign_id,
                "participant_id": row.participant_id,
                "ambassador_code": code,
                "ip_hash": row.ip_hash,
                "click_count": row.click_count,
                "window_start": row.window_start,
                "window_end": row.window_end,
                "status": row.status,
                "details": row.details or {},
                "created_at": row.created_at,
            }
        )
    return out
