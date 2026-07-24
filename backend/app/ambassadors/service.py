"""Public / user / event / tracking Ambassadors services (phase 10)."""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ambassadors.audit import write_ambassador_audit
from app.ambassadors.fraud import (
    assert_user_may_join_campaign,
    hash_tracking_fingerprint,
    hash_tracking_ip,
    hash_tracking_ua,
    maybe_flag_click_spike,
)
from app.events.models import Event
from app.events.service import get_event_by_id, get_event_by_slug
from app.hosts.models import Host
from app.promos.ambassador_domain import (
    AmbassadorAttribution,
    AmbassadorClick,
    AmbassadorConversion,
    AmbassadorParticipant,
    AmbassadorProfile,
)
from app.promos.commission import resolve_campaign_commission_input
from app.promos.constants import (
    AMBASSADOR_TERMS_VERSION,
    ATTRIBUTION_SOURCES,
    DEFAULT_COOKIE_WINDOW_DAYS,
    DOMAIN_CAMPAIGN_STATUS_ACTIVE,
    DOMAIN_CAMPAIGN_TYPE_EVENT,
    DOMAIN_CAMPAIGN_TYPE_MERCH,
    VISIBILITY_PUBLIC_OPEN,
)
from app.promos.models import AmbassadorCampaign
from app.users.models import User

JOINABLE_STATUSES = frozenset({"active", "public_open"})
OPEN_VISIBILITIES = frozenset({VISIBILITY_PUBLIC_OPEN})


def _q(amount: Decimal) -> Decimal:
    return Decimal(amount).quantize(Decimal("0.01"))


def _campaign_in_window(campaign: AmbassadorCampaign, *, now: datetime) -> bool:
    starts = campaign.starts_at
    ends = campaign.ends_at
    if starts is not None:
        if starts.tzinfo is None:
            starts = starts.replace(tzinfo=UTC)
        if now < starts:
            return False
    if ends is not None:
        if ends.tzinfo is None:
            ends = ends.replace(tzinfo=UTC)
        if now > ends:
            return False
    return True


def campaign_is_joinable(campaign: AmbassadorCampaign, *, now: datetime | None = None) -> bool:
    current = now or datetime.now(UTC)
    visibility = getattr(campaign, "visibility", VISIBILITY_PUBLIC_OPEN) or VISIBILITY_PUBLIC_OPEN
    if visibility not in OPEN_VISIBILITIES:
        return False
    if campaign.status not in JOINABLE_STATUSES:
        return False
    return _campaign_in_window(campaign, now=current)


def serialize_campaign(db: Session, campaign: AmbassadorCampaign) -> dict:
    event = db.get(Event, campaign.event_id) if campaign.event_id else None
    return {
        "id": campaign.id,
        "name": campaign.name,
        "description": getattr(campaign, "description", None),
        "campaign_type": campaign.campaign_type,
        "status": campaign.status,
        "visibility": getattr(campaign, "visibility", VISIBILITY_PUBLIC_OPEN)
        or VISIBILITY_PUBLIC_OPEN,
        "commission_type": campaign.commission_type,
        "commission_value": campaign.commission_value,
        "applies_to": campaign.applies_to,
        "hold_period_days": campaign.hold_period_days,
        "cookie_window_days": int(
            getattr(campaign, "cookie_window_days", DEFAULT_COOKIE_WINDOW_DAYS)
            or DEFAULT_COOKIE_WINDOW_DAYS
        ),
        "event_id": campaign.event_id,
        "event_title": event.title if event else None,
        "event_slug": event.slug if event else None,
        "merch_product_id": getattr(campaign, "merch_product_id", None),
        "starts_at": campaign.starts_at,
        "ends_at": campaign.ends_at,
        "is_joinable": campaign_is_joinable(campaign),
        "allow_host_owner_commission": bool(
            getattr(campaign, "allow_host_owner_commission", False)
        ),
        "created_at": campaign.created_at,
        "updated_at": campaign.updated_at,
    }


def get_or_create_profile(db: Session, user: User) -> AmbassadorProfile:
    profile = db.scalar(
        select(AmbassadorProfile).where(AmbassadorProfile.user_id == user.id)
    )
    if profile is not None:
        return profile
    profile = AmbassadorProfile(user_id=user.id, status="active")
    db.add(profile)
    db.flush()
    write_ambassador_audit(
        db,
        action="ambassadors.profile_created",
        entity_type="ambassador_profile",
        entity_id=profile.id,
        actor_user_id=user.id,
    )
    return profile


def _assert_user_can_join(db: Session, user: User, profile: AmbassadorProfile) -> None:
    from app.users.restrictions import assert_can_promote_as_ambassador

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is not active")
    assert_can_promote_as_ambassador(db, user)
    if profile.status in {"suspended", "blocked"}:
        raise HTTPException(
            status_code=403, detail="Your Ambassadors profile cannot join campaigns"
        )


def _normalize_domain_campaign_type(raw: str | None) -> str:
    value = (raw or DOMAIN_CAMPAIGN_TYPE_EVENT).strip().lower()
    mapping = {
        "event": DOMAIN_CAMPAIGN_TYPE_EVENT,
        "event_tickets": DOMAIN_CAMPAIGN_TYPE_EVENT,
        "merch": DOMAIN_CAMPAIGN_TYPE_MERCH,
        "event_merch": DOMAIN_CAMPAIGN_TYPE_MERCH,
        "host": "host",
        "platform": "platform",
    }
    if value not in mapping:
        raise HTTPException(
            status_code=400,
            detail="campaign_type must be event, merch, host, or platform",
        )
    return mapping[value]


def _code_taken(db: Session, *, campaign_id: UUID, code: str) -> bool:
    return (
        db.scalar(
            select(AmbassadorParticipant).where(
                AmbassadorParticipant.campaign_id == campaign_id,
                AmbassadorParticipant.ambassador_code == code,
            )
        )
        is not None
    )


def _generate_ambassador_code(
    db: Session, *, campaign_id: UUID, user: User
) -> str:
    base = re.sub(r"[^a-z0-9]", "", (user.full_name or "amb").lower())[:8] or "amb"
    for _ in range(12):
        suffix = secrets.token_hex(2)
        code = f"{base}{suffix}"
        if not _code_taken(db, campaign_id=campaign_id, code=code):
            return code
    raise HTTPException(status_code=500, detail="Could not allocate ambassador code")


def _resolve_join_campaign(
    db: Session,
    *,
    campaign_id: UUID | None,
    event_id: UUID | None,
    event: Event | None = None,
) -> AmbassadorCampaign:
    if campaign_id is not None:
        campaign = db.get(AmbassadorCampaign, campaign_id)
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if not campaign_is_joinable(campaign):
            raise HTTPException(status_code=400, detail="Campaign is not open to join")
        return campaign

    target_event = event
    if target_event is None and event_id is not None:
        target_event = get_event_by_id(db, event_id)
    if target_event is None:
        raise HTTPException(
            status_code=400, detail="campaign_id or event_id is required"
        )

    rows = list(
        db.scalars(
            select(AmbassadorCampaign).where(
                AmbassadorCampaign.event_id == target_event.id,
                AmbassadorCampaign.status.in_(tuple(JOINABLE_STATUSES)),
            )
        )
    )
    joinable = [c for c in rows if campaign_is_joinable(c)]
    if not joinable:
        raise HTTPException(
            status_code=400, detail="Ambassadors is not enabled for this event"
        )
    # Prefer event-type campaign, then any joinable.
    for c in joinable:
        if c.campaign_type in {DOMAIN_CAMPAIGN_TYPE_EVENT, "event_tickets"}:
            return c
    return joinable[0]


def list_eligible_events(db: Session) -> list[dict]:
    from app.promos.admin_service import is_ambassadors_feature_enabled

    if not is_ambassadors_feature_enabled(db):
        return []

    campaigns = list(
        db.scalars(
            select(AmbassadorCampaign).where(
                AmbassadorCampaign.event_id.is_not(None),
                AmbassadorCampaign.status.in_(tuple(JOINABLE_STATUSES)),
            )
        )
    )
    out: list[dict] = []
    seen_events: set[UUID] = set()
    for campaign in campaigns:
        if not campaign_is_joinable(campaign) or campaign.event_id is None:
            continue
        if campaign.event_id in seen_events:
            continue
        event = db.get(Event, campaign.event_id)
        if event is None or event.status != "published":
            continue
        host = db.get(Host, event.host_id) if event.host_id else None
        seen_events.add(event.id)
        out.append(
            {
                "id": event.id,
                "title": event.title,
                "slug": event.slug,
                "city": event.city,
                "start_datetime": event.start_datetime,
                "banner_url": getattr(event, "banner_url", None),
                "host_display_name": host.display_name if host else None,
                "campaign_id": campaign.id,
                "campaign_type": campaign.campaign_type,
                "commission_type": campaign.commission_type,
                "commission_value": campaign.commission_value,
                "visibility": getattr(campaign, "visibility", VISIBILITY_PUBLIC_OPEN),
            }
        )
    out.sort(key=lambda r: r["start_datetime"])
    return out


def join_campaign(
    db: Session,
    *,
    user: User,
    accept_terms: bool,
    campaign_id: UUID | None = None,
    event_id: UUID | None = None,
    event: Event | None = None,
) -> dict:
    if not accept_terms:
        raise HTTPException(
            status_code=400, detail="You must accept Ambassador terms to join"
        )
    profile = get_or_create_profile(db, user)
    _assert_user_can_join(db, user, profile)
    campaign = _resolve_join_campaign(
        db, campaign_id=campaign_id, event_id=event_id, event=event
    )
    assert_user_may_join_campaign(db, user_id=user.id, campaign=campaign)

    existing = db.scalar(
        select(AmbassadorParticipant).where(
            AmbassadorParticipant.campaign_id == campaign.id,
            AmbassadorParticipant.ambassador_profile_id == profile.id,
        )
    )
    now = datetime.now(UTC)
    if existing is not None:
        if existing.status == "blocked":
            raise HTTPException(
                status_code=403, detail="You are blocked from this campaign"
            )
        existing.status = "active"
        existing.joined_at = now
        profile.terms_accepted_at = now
        write_ambassador_audit(
            db,
            action="ambassadors.participant_rejoined",
            entity_type="ambassador_participant",
            entity_id=existing.id,
            actor_user_id=user.id,
            metadata={"campaign_id": str(campaign.id)},
        )
        db.commit()
        db.refresh(existing)
        from app.ambassadors.notifications import notify_ambassador_joined

        notify_ambassador_joined(
            db,
            user=user,
            event_id=campaign.event_id,
            campaign=campaign,
            enrollment_id=existing.id,
        )
        return _serialize_participant(db, existing)

    code = _generate_ambassador_code(db, campaign_id=campaign.id, user=user)
    participant = AmbassadorParticipant(
        campaign_id=campaign.id,
        ambassador_profile_id=profile.id,
        user_id=user.id,
        ambassador_code=code,
        status="active",
        joined_at=now,
    )
    profile.terms_accepted_at = now
    if not profile.public_code_base:
        profile.public_code_base = code[:8]
    db.add(participant)
    db.flush()
    write_ambassador_audit(
        db,
        action="ambassadors.participant_joined",
        entity_type="ambassador_participant",
        entity_id=participant.id,
        actor_user_id=user.id,
        metadata={
            "campaign_id": str(campaign.id),
            "ambassador_code": code,
            "terms_version": AMBASSADOR_TERMS_VERSION,
        },
    )
    db.commit()
    db.refresh(participant)
    from app.ambassadors.notifications import notify_ambassador_joined

    notify_ambassador_joined(
        db,
        user=user,
        event_id=campaign.event_id,
        campaign=campaign,
        enrollment_id=participant.id,
    )
    return _serialize_participant(db, participant)


def _serialize_participant(db: Session, participant: AmbassadorParticipant) -> dict:
    campaign = db.get(AmbassadorCampaign, participant.campaign_id)
    event = None
    if campaign and campaign.event_id:
        event = db.get(Event, campaign.event_id)
    return {
        "id": participant.id,
        "campaign_id": participant.campaign_id,
        "ambassador_profile_id": participant.ambassador_profile_id,
        "user_id": participant.user_id,
        "ambassador_code": participant.ambassador_code,
        "status": participant.status,
        "joined_at": participant.joined_at,
        "campaign_name": campaign.name if campaign else None,
        "event_title": event.title if event else None,
        "event_slug": event.slug if event else None,
    }


def get_my_profile(db: Session, user: User) -> dict:
    profile = get_or_create_profile(db, user)
    db.commit()
    db.refresh(profile)
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "status": profile.status,
        "public_code_base": profile.public_code_base,
        "terms_accepted_at": profile.terms_accepted_at,
        "created_at": profile.created_at,
    }


def list_my_campaigns(db: Session, user: User) -> list[dict]:
    rows = list(
        db.scalars(
            select(AmbassadorParticipant)
            .where(
                AmbassadorParticipant.user_id == user.id,
                AmbassadorParticipant.status.in_(("active", "paused")),
            )
            .order_by(AmbassadorParticipant.joined_at.desc())
        )
    )
    return [_serialize_participant(db, r) for r in rows]


def list_my_links(db: Session, user: User) -> list[dict]:
    rows = list(
        db.scalars(
            select(AmbassadorParticipant).where(
                AmbassadorParticipant.user_id == user.id,
                AmbassadorParticipant.status == "active",
            )
        )
    )
    out: list[dict] = []
    for p in rows:
        campaign = db.get(AmbassadorCampaign, p.campaign_id)
        event = (
            db.get(Event, campaign.event_id)
            if campaign and campaign.event_id
            else None
        )
        slug = event.slug if event else None
        event_path = f"/events/{slug}?ref={p.ambassador_code}" if slug else None
        merch_path = (
            f"/events/{slug}/merch?ref={p.ambassador_code}" if slug else None
        )
        out.append(
            {
                "participant_id": p.id,
                "campaign_id": p.campaign_id,
                "ambassador_code": p.ambassador_code,
                "event_id": event.id if event else None,
                "event_slug": slug,
                "event_path": event_path,
                "merch_path": merch_path,
                "share_url_path": event_path,
            }
        )
    return out


def my_earnings(db: Session, user: User) -> dict:
    participant_ids = list(
        db.scalars(
            select(AmbassadorParticipant.id).where(
                AmbassadorParticipant.user_id == user.id
            )
        )
    )
    if not participant_ids:
        zero = Decimal("0.00")
        return {
            "confirmed_conversions": 0,
            "pending_amount": zero,
            "approved_amount": zero,
            "payable_amount": zero,
            "paid_amount": zero,
            "reversed_amount": zero,
            "gross_eligible": zero,
        }
    rows = list(
        db.scalars(
            select(AmbassadorConversion).where(
                AmbassadorConversion.participant_id.in_(participant_ids)
            )
        )
    )
    def _sum(statuses: set[str]) -> Decimal:
        return _q(
            sum(
                (r.commission_amount for r in rows if r.status in statuses),
                Decimal("0"),
            )
        )

    active = [r for r in rows if r.status != "reversed"]
    return {
        "confirmed_conversions": len(active),
        "pending_amount": _sum({"pending"}),
        "approved_amount": _sum({"approved", "payable", "paid"}),
        "payable_amount": _sum({"payable", "approved"}),
        "paid_amount": _sum({"paid"}),
        "reversed_amount": _sum({"reversed"}),
        "gross_eligible": _q(
            sum((r.eligible_amount for r in active), Decimal("0"))
        ),
    }


def get_public_campaign(db: Session, campaign_id: UUID) -> dict:
    campaign = db.get(AmbassadorCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    # Public detail for joinable campaigns, or any non-private for discovery.
    visibility = getattr(campaign, "visibility", VISIBILITY_PUBLIC_OPEN)
    if visibility == "private" and not campaign_is_joinable(campaign):
        raise HTTPException(status_code=404, detail="Campaign not found")
    return serialize_campaign(db, campaign)


def event_ambassador_status(
    db: Session, *, slug: str, user: User | None
) -> dict:
    from app.promos.admin_service import is_ambassadors_feature_enabled

    event = get_event_by_slug(db, slug)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    platform_on = is_ambassadors_feature_enabled(db)
    campaigns = list(
        db.scalars(
            select(AmbassadorCampaign).where(
                AmbassadorCampaign.event_id == event.id
            )
        )
    )
    joinable = [c for c in campaigns if campaign_is_joinable(c)]
    primary = joinable[0] if joinable else None
    joined = False
    participant_id = None
    code = None
    if user is not None and primary is not None:
        participant = db.scalar(
            select(AmbassadorParticipant).where(
                AmbassadorParticipant.campaign_id == primary.id,
                AmbassadorParticipant.user_id == user.id,
                AmbassadorParticipant.status == "active",
            )
        )
        if participant is not None:
            joined = True
            participant_id = participant.id
            code = participant.ambassador_code
    return {
        "event_id": event.id,
        "event_slug": event.slug,
        "enabled": bool(platform_on and primary is not None),
        "campaign_id": primary.id if primary else None,
        "campaign_type": primary.campaign_type if primary else None,
        "commission_type": primary.commission_type if primary else None,
        "commission_value": primary.commission_value if primary else None,
        "joined": joined,
        "participant_id": participant_id,
        "ambassador_code": code,
        "terms_version": AMBASSADOR_TERMS_VERSION,
    }


def join_event_by_slug(db: Session, *, user: User, slug: str, accept_terms: bool) -> dict:
    event = get_event_by_slug(db, slug)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return join_campaign(
        db,
        user=user,
        accept_terms=accept_terms,
        event=event,
        event_id=event.id,
    )


def event_ambassador_link(db: Session, *, user: User, slug: str) -> dict:
    event = get_event_by_slug(db, slug)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    campaign_ids = list(
        db.scalars(
            select(AmbassadorCampaign.id).where(
                AmbassadorCampaign.event_id == event.id
            )
        )
    )
    if not campaign_ids:
        raise HTTPException(
            status_code=404,
            detail="You are not an ambassador for this event — join first",
        )
    participant = db.scalar(
        select(AmbassadorParticipant)
        .where(
            AmbassadorParticipant.user_id == user.id,
            AmbassadorParticipant.status == "active",
            AmbassadorParticipant.campaign_id.in_(campaign_ids),
        )
        .order_by(AmbassadorParticipant.joined_at.desc())
    )
    if participant is None:
        raise HTTPException(
            status_code=404,
            detail="You are not an ambassador for this event — join first",
        )
    code = participant.ambassador_code
    return {
        "event_id": event.id,
        "event_slug": event.slug,
        "campaign_id": participant.campaign_id,
        "participant_id": participant.id,
        "ambassador_code": code,
        "event_path": f"/events/{event.slug}?ref={code}",
        "merch_path": f"/events/{event.slug}/merch?ref={code}",
    }


def _find_participant_by_code(
    db: Session,
    *,
    code: str,
    campaign_id: UUID | None,
    event_id: UUID | None,
) -> AmbassadorParticipant | None:
    stmt = select(AmbassadorParticipant).where(
        AmbassadorParticipant.ambassador_code == code,
        AmbassadorParticipant.status == "active",
    )
    if campaign_id is not None:
        stmt = stmt.where(AmbassadorParticipant.campaign_id == campaign_id)
    participant = db.scalar(stmt)
    if participant is not None:
        return participant
    if event_id is None:
        return None
    campaign_ids = list(
        db.scalars(
            select(AmbassadorCampaign.id).where(
                AmbassadorCampaign.event_id == event_id
            )
        )
    )
    if not campaign_ids:
        return None
    return db.scalar(
        select(AmbassadorParticipant).where(
            AmbassadorParticipant.ambassador_code == code,
            AmbassadorParticipant.status == "active",
            AmbassadorParticipant.campaign_id.in_(campaign_ids),
        )
    )


def track_click(
    db: Session,
    *,
    payload,
    user: User | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict:
    from app.ambassadors.referral_tracking import ReferralTrackingService

    result = ReferralTrackingService.record_domain_track_click(
        db,
        payload=payload,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if result.get("click_id"):
        write_ambassador_audit(
            db,
            action="ambassadors.click_tracked",
            entity_type="referral_click",
            entity_id=result["click_id"],
            actor_user_id=user.id if user else None,
            metadata={
                "participant_id": str(result["participant_id"])
                if result.get("participant_id")
                else None,
                "campaign_id": str(result["campaign_id"])
                if result.get("campaign_id")
                else None,
            },
        )
        db.commit()
    return result


def track_checkout_started(
    db: Session,
    *,
    payload,
    user: User | None = None,
) -> dict:
    if not payload.ambassador_code and not payload.campaign_id:
        raise HTTPException(
            status_code=400,
            detail="ambassador_code or campaign_id is required",
        )
    participant = None
    if payload.ambassador_code:
        participant = _find_participant_by_code(
            db,
            code=payload.ambassador_code,
            campaign_id=payload.campaign_id,
            event_id=payload.event_id,
        )
    if participant is None and payload.campaign_id and user is not None:
        # Fall back to caller's active participation on the campaign.
        participant = db.scalar(
            select(AmbassadorParticipant).where(
                AmbassadorParticipant.campaign_id == payload.campaign_id,
                AmbassadorParticipant.user_id == user.id,
                AmbassadorParticipant.status == "active",
            )
        )
    if participant is None:
        raise HTTPException(status_code=404, detail="Ambassador attribution not found")

    campaign = db.get(AmbassadorCampaign, participant.campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    source = (payload.source or "code").strip().lower()
    if source not in ATTRIBUTION_SOURCES:
        source = "code"
    cookie_days = int(
        getattr(campaign, "cookie_window_days", DEFAULT_COOKIE_WINDOW_DAYS)
        or DEFAULT_COOKIE_WINDOW_DAYS
    )
    expires = datetime.now(UTC) + timedelta(days=cookie_days)
    attribution = AmbassadorAttribution(
        campaign_id=campaign.id,
        participant_id=participant.id,
        user_id=user.id if user else None,
        session_id=payload.session_id,
        event_id=payload.event_id or campaign.event_id,
        merch_product_id=payload.merch_product_id or campaign.merch_product_id,
        source=source,
        expires_at=expires,
    )
    db.add(attribution)
    db.flush()
    write_ambassador_audit(
        db,
        action="ambassadors.checkout_started",
        entity_type="ambassador_attribution",
        entity_id=attribution.id,
        actor_user_id=user.id if user else None,
        metadata={
            "participant_id": str(participant.id),
            "campaign_id": str(campaign.id),
            "source": source,
        },
    )
    db.commit()
    return {
        "ok": True,
        "click_id": None,
        "attribution_id": attribution.id,
        "participant_id": participant.id,
        "campaign_id": campaign.id,
        "expires_at": expires,
    }


# Re-export for host_service campaign type normalization
normalize_domain_campaign_type = _normalize_domain_campaign_type
resolve_campaign_commission_input_fn = resolve_campaign_commission_input
