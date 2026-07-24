"""Admin Ambassadors APIs (phase 10)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ambassadors.audit import write_ambassador_audit
from app.ambassadors.service import serialize_campaign
from app.promos.ambassador_domain import (
    AmbassadorConversion,
    AmbassadorParticipant,
    AmbassadorPayout,
    AmbassadorProfile,
)
from app.promos.models import AmbassadorCampaign
from app.users.models import User


def list_admin_profiles(
    db: Session, *, q: str | None = None, limit: int = 100, offset: int = 0
) -> list[dict]:
    stmt = select(AmbassadorProfile).order_by(AmbassadorProfile.created_at.desc())
    rows = list(db.scalars(stmt.offset(offset).limit(limit)).all())
    out: list[dict] = []
    needle = (q or "").strip().lower()
    for profile in rows:
        user = db.get(User, profile.user_id)
        if needle:
            hay = " ".join(
                [
                    (user.email or "") if user else "",
                    (user.full_name or "") if user else "",
                    str(profile.id),
                ]
            ).lower()
            if needle not in hay:
                continue
        active = int(
            db.scalar(
                select(func.count())
                .select_from(AmbassadorParticipant)
                .where(
                    AmbassadorParticipant.ambassador_profile_id == profile.id,
                    AmbassadorParticipant.status == "active",
                )
            )
            or 0
        )
        out.append(
            {
                "profile_id": profile.id,
                "user_id": profile.user_id,
                "status": profile.status,
                "email": user.email if user else None,
                "full_name": user.full_name if user else None,
                "participants_active": active,
                "created_at": profile.created_at,
            }
        )
    return out


def list_admin_campaigns(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    stmt = select(AmbassadorCampaign).order_by(AmbassadorCampaign.created_at.desc())
    if status:
        stmt = stmt.where(AmbassadorCampaign.status == status)
    rows = list(db.scalars(stmt.offset(offset).limit(limit)).all())
    return [serialize_campaign(db, c) for c in rows]


def list_admin_conversions(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    stmt = select(AmbassadorConversion).order_by(
        AmbassadorConversion.created_at.desc()
    )
    if status:
        stmt = stmt.where(AmbassadorConversion.status == status)
    rows = list(db.scalars(stmt.offset(offset).limit(limit)).all())
    out: list[dict] = []
    for c in rows:
        participant = db.get(AmbassadorParticipant, c.participant_id)
        campaign = db.get(AmbassadorCampaign, c.campaign_id)
        out.append(
            {
                "id": c.id,
                "campaign_id": c.campaign_id,
                "participant_id": c.participant_id,
                "buyer_user_id": c.buyer_user_id,
                "order_id": c.order_id,
                "conversion_type": c.conversion_type,
                "gross_amount": c.gross_amount,
                "eligible_amount": c.eligible_amount,
                "commission_amount": c.commission_amount,
                "status": c.status,
                "dedupe_key": c.dedupe_key,
                "verified_at": c.verified_at,
                "refunded_at": c.refunded_at,
                "created_at": c.created_at,
                "ambassador_code": (
                    participant.ambassador_code if participant else None
                ),
                "campaign_name": campaign.name if campaign else None,
            }
        )
    return out


def list_admin_payouts(
    db: Session,
    *,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    stmt = select(AmbassadorPayout).order_by(AmbassadorPayout.created_at.desc())
    if status:
        stmt = stmt.where(AmbassadorPayout.status == status)
    rows = list(db.scalars(stmt.offset(offset).limit(limit)).all())
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


def block_participant(
    db: Session,
    *,
    admin: User,
    participant_id: UUID,
    reason: str | None = None,
) -> dict:
    participant = db.get(AmbassadorParticipant, participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    participant.status = "blocked"
    profile = db.get(AmbassadorProfile, participant.ambassador_profile_id)
    write_ambassador_audit(
        db,
        action="ambassadors.participant_blocked",
        entity_type="ambassador_participant",
        entity_id=participant.id,
        actor_user_id=admin.id,
        metadata={
            "reason": reason,
            "profile_id": str(participant.ambassador_profile_id),
            "profile_status": profile.status if profile else None,
        },
    )
    db.commit()
    db.refresh(participant)
    return {
        "id": participant.id,
        "campaign_id": participant.campaign_id,
        "ambassador_profile_id": participant.ambassador_profile_id,
        "user_id": participant.user_id,
        "ambassador_code": participant.ambassador_code,
        "status": participant.status,
        "joined_at": participant.joined_at,
        "campaign_name": None,
        "event_title": None,
        "event_slug": None,
    }


def reverse_conversion(
    db: Session,
    *,
    admin: User,
    conversion_id: UUID,
    reason: str,
) -> dict:
    conversion = db.get(AmbassadorConversion, conversion_id)
    if conversion is None:
        raise HTTPException(status_code=404, detail="Conversion not found")
    if conversion.status == "reversed":
        # Idempotent
        pass
    else:
        conversion.status = "reversed"
        conversion.refunded_at = datetime.now(UTC)
        write_ambassador_audit(
            db,
            action="ambassadors.conversion_reversed",
            entity_type="ambassador_conversion",
            entity_id=conversion.id,
            actor_user_id=admin.id,
            metadata={
                "reason": reason[:500],
                "dedupe_key": conversion.dedupe_key,
                "commission_amount": str(conversion.commission_amount),
            },
        )
        db.commit()
        db.refresh(conversion)

    participant = db.get(AmbassadorParticipant, conversion.participant_id)
    campaign = db.get(AmbassadorCampaign, conversion.campaign_id)
    return {
        "id": conversion.id,
        "campaign_id": conversion.campaign_id,
        "participant_id": conversion.participant_id,
        "buyer_user_id": conversion.buyer_user_id,
        "order_id": conversion.order_id,
        "conversion_type": conversion.conversion_type,
        "gross_amount": conversion.gross_amount,
        "eligible_amount": conversion.eligible_amount,
        "commission_amount": conversion.commission_amount,
        "status": conversion.status,
        "dedupe_key": conversion.dedupe_key,
        "verified_at": conversion.verified_at,
        "refunded_at": conversion.refunded_at,
        "created_at": conversion.created_at,
        "ambassador_code": participant.ambassador_code if participant else None,
        "campaign_name": campaign.name if campaign else None,
    }
