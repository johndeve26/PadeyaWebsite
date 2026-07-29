"""Sponsorship marketplace business logic — isolated from core payments."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.events.models import Event
from app.hosts.models import Host, HostVerification
from app.hosts.team_access import require_host_for_permission
from app.sponsorships.constants import SLOT_STATUSES, SLOT_TYPE_LABELS
from app.sponsorships.models import (
    HostSponsorshipSettings,
    Sponsor,
    SponsorshipAnalytics,
    SponsorshipInquiry,
    SponsorshipPlacement,
    SponsorshipSlot,
)
from app.sponsorships.schemas import (
    HostSponsorshipSettingsUpdate,
    SponsorshipInquiryCreate,
    SponsorshipInquiryUpdate,
    SponsorshipModerateRequest,
    SponsorshipPlacementCreate,
    SponsorshipSlotCreate,
    SponsorshipSlotUpdate,
)
from app.users.models import User
from app.users.service import user_has_permission


def host_is_verified(db: Session, host_id: UUID) -> bool:
    latest = db.scalars(
        select(HostVerification)
        .where(HostVerification.host_id == host_id)
        .order_by(HostVerification.created_at.desc())
        .limit(1)
    ).first()
    return latest is not None and latest.status == "verified"


def _require_manage_slots(db: Session, *, user: User):
    return require_host_for_permission(
        db, user=user, host_id=None, permission="sponsors.manage_slots"
    )


def _require_view_slots(db: Session, *, user: User):
    return require_host_for_permission(
        db,
        user=user,
        host_id=None,
        permission=("sponsors.view", "sponsors.manage_slots"),
    )


def _require_view_inquiries(db: Session, *, user: User):
    return require_host_for_permission(
        db,
        user=user,
        host_id=None,
        permission=(
            "sponsors.view",
            "sponsors.reply",
            "sponsors.accept_or_reject",
        ),
    )


def get_or_create_settings(db: Session, host_id: UUID) -> HostSponsorshipSettings:
    row = db.scalar(
        select(HostSponsorshipSettings).where(HostSponsorshipSettings.host_id == host_id)
    )
    if row is None:
        row = HostSponsorshipSettings(host_id=host_id, accepting_sponsors=True)
        db.add(row)
        db.flush()
    return row


def _invalidate_public_sponsorship_cache(*, slot_id: UUID | None = None) -> None:
    """Drop cached public marketplace lists after slot/host visibility changes."""
    from app.core.cache import cache_delete, cache_key

    cache_delete(cache_key("sponsorships", "slots"))
    cache_delete(cache_key("sponsorships", "hosts"))
    if slot_id is not None:
        cache_delete(cache_key("sponsorships", "slot", str(slot_id)))


def serialize_slot(db: Session, slot: SponsorshipSlot) -> dict:
    host = db.get(Host, slot.host_id)
    event = db.get(Event, slot.event_id) if slot.event_id else None
    return {
        "id": slot.id,
        "host_id": slot.host_id,
        "event_id": slot.event_id,
        "slot_type": slot.slot_type,
        "slot_type_label": SLOT_TYPE_LABELS.get(
                slot.slot_type,
                slot.slot_type.replace("_", " ").title(),
            ),
        "title": slot.title,
        "description": slot.description,
        "price": slot.price,
        "currency": slot.currency,
        "status": slot.status,
        "moderation_status": slot.moderation_status,
        "host_display_name": host.display_name if host else None,
        "host_username": host.slug if host else None,
        "host_verified": host_is_verified(db, slot.host_id),
        "event_title": event.title if event else None,
        "published_at": slot.published_at,
        "created_at": slot.created_at,
        "updated_at": slot.updated_at,
    }


def _is_publicly_visible(db: Session, slot: SponsorshipSlot) -> bool:
    if slot.status != "published":
        return False
    if slot.moderation_status in {"removed"}:
        return False
    if not host_is_verified(db, slot.host_id):
        return False
    settings = get_or_create_settings(db, slot.host_id)
    if not settings.accepting_sponsors:
        return False
    host = db.get(Host, slot.host_id)
    if host is None or host.status != "active":
        return False
    return True


def get_host_settings(db: Session, user: User) -> dict:
    host, _ = _require_view_slots(db, user=user)
    settings = get_or_create_settings(db, host.id)
    db.commit()
    return {
        "host_id": host.id,
        "accepting_sponsors": settings.accepting_sponsors,
        "contact_email": settings.contact_email,
        "pitch": settings.pitch,
        "audience_notes": settings.audience_notes,
    }


def update_host_settings(
    db: Session, *, user: User, payload: HostSponsorshipSettingsUpdate
) -> dict:
    host, _ = _require_manage_slots(db, user=user)
    settings = get_or_create_settings(db, host.id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(settings, key, value)
    write_audit_log(
        db,
        action="sponsorships.settings_update",
        actor_user_id=user.id,
        resource_type="host_sponsorship_settings",
        resource_id=str(settings.id),
        details=data,
    )
    db.commit()
    db.refresh(settings)
    if "accepting_sponsors" in data:
        _invalidate_public_sponsorship_cache()
    return {
        "host_id": host.id,
        "accepting_sponsors": settings.accepting_sponsors,
        "contact_email": settings.contact_email,
        "pitch": settings.pitch,
        "audience_notes": settings.audience_notes,
    }


def create_slot(db: Session, *, user: User, payload: SponsorshipSlotCreate) -> dict:
    host, _ = _require_manage_slots(db, user=user)

    if payload.event_id is not None:
        event = db.get(Event, payload.event_id)
        if event is None or event.host_id != host.id:
            raise HTTPException(status_code=404, detail="Event not found")

    status_value = payload.status or "draft"
    if status_value == "published":
        if not host_is_verified(db, host.id):
            raise HTTPException(
                status_code=400,
                detail="Only verified hosts can publish sponsorship slots",
            )

    slot = SponsorshipSlot(
        host_id=host.id,
        event_id=payload.event_id,
        slot_type=payload.slot_type,
        title=payload.title.strip(),
        description=payload.description.strip(),
        price=Decimal(payload.price).quantize(Decimal("0.01")),
        currency=(payload.currency or "NGN").upper(),
        status=status_value if status_value in {"draft", "published"} else "draft",
        moderation_status="none",
        published_at=datetime.now(UTC) if status_value == "published" else None,
    )
    db.add(slot)
    db.flush()
    write_audit_log(
        db,
        action="sponsorships.slot_create",
        actor_user_id=user.id,
        resource_type="sponsorship_slot",
        resource_id=str(slot.id),
        details={"status": slot.status, "slot_type": slot.slot_type},
    )
    db.commit()
    db.refresh(slot)
    if slot.status == "published":
        _invalidate_public_sponsorship_cache(slot_id=slot.id)
    return serialize_slot(db, slot)


def update_slot(
    db: Session, *, user: User, slot_id: UUID, payload: SponsorshipSlotUpdate
) -> dict:
    host, _ = _require_manage_slots(db, user=user)
    slot = db.get(SponsorshipSlot, slot_id)
    if slot is None or slot.host_id != host.id:
        raise HTTPException(status_code=404, detail="Sponsorship slot not found")

    data = payload.model_dump(exclude_unset=True)
    if "event_id" in data and data["event_id"] is not None:
        event = db.get(Event, data["event_id"])
        if event is None or event.host_id != host.id:
            raise HTTPException(status_code=404, detail="Event not found")

    if "status" in data and data["status"] is not None:
        if data["status"] not in SLOT_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid slot status")

    if data.get("status") == "published":
        if not host_is_verified(db, host.id):
            raise HTTPException(
                status_code=400,
                detail="Only verified hosts can publish sponsorship slots",
            )
        if slot.moderation_status == "removed":
            raise HTTPException(
                status_code=400,
                detail="This listing was disabled by moderation",
            )
        if slot.published_at is None:
            slot.published_at = datetime.now(UTC)

    # Publishing does not approve events — slots are independent of event approval
    for key, value in data.items():
        if key == "price" and value is not None:
            setattr(slot, key, Decimal(value).quantize(Decimal("0.01")))
        elif key == "title" and value is not None:
            setattr(slot, key, value.strip())
        elif key == "description" and value is not None:
            setattr(slot, key, value.strip())
        else:
            setattr(slot, key, value)

    write_audit_log(
        db,
        action="sponsorships.slot_update",
        actor_user_id=user.id,
        resource_type="sponsorship_slot",
        resource_id=str(slot.id),
        details=data,
    )
    db.commit()
    db.refresh(slot)
    _invalidate_public_sponsorship_cache(slot_id=slot.id)
    return serialize_slot(db, slot)


def list_host_slots(db: Session, user: User) -> list[dict]:
    host, _ = _require_view_slots(db, user=user)
    rows = db.scalars(
        select(SponsorshipSlot)
        .where(SponsorshipSlot.host_id == host.id)
        .order_by(SponsorshipSlot.created_at.desc())
    ).all()
    return [serialize_slot(db, s) for s in rows]


def list_public_slots(db: Session) -> list[dict]:
    rows = db.scalars(
        select(SponsorshipSlot)
        .where(
            SponsorshipSlot.status == "published",
            SponsorshipSlot.moderation_status != "removed",
        )
        .order_by(SponsorshipSlot.published_at.desc())
    ).all()
    return [serialize_slot(db, s) for s in rows if _is_publicly_visible(db, s)]


def get_public_slot(db: Session, slot_id: UUID) -> dict:
    slot = db.get(SponsorshipSlot, slot_id)
    if slot is None or not _is_publicly_visible(db, slot):
        raise HTTPException(status_code=404, detail="Sponsorship slot not found")
    return serialize_slot(db, slot)


def list_sponsor_hosts(db: Session) -> list[dict]:
    hosts = db.scalars(select(Host).where(Host.status == "active")).all()
    out: list[dict] = []
    for host in hosts:
        if not host_is_verified(db, host.id):
            continue
        settings = get_or_create_settings(db, host.id)
        if not settings.accepting_sponsors:
            continue
        open_slots = int(
            db.scalar(
                select(func.count())
                .select_from(SponsorshipSlot)
                .where(
                    SponsorshipSlot.host_id == host.id,
                    SponsorshipSlot.status == "published",
                    SponsorshipSlot.moderation_status != "removed",
                )
            )
            or 0
        )
        profile = host.profile
        out.append(
            {
                "host_id": host.id,
                "display_name": host.display_name,
                "username": host.slug,
                "verified": True,
                "city": profile.city if profile else None,
                "bio": profile.bio if profile else None,
                "accepting_sponsors": settings.accepting_sponsors,
                "pitch": settings.pitch,
                "open_slots": open_slots,
            }
        )
    out.sort(key=lambda h: h["open_slots"], reverse=True)
    db.commit()  # persist any auto-created settings
    return out


def _upsert_sponsor_from_inquiry(
    db: Session, *, payload: SponsorshipInquiryCreate, user: User | None
) -> Sponsor:
    existing = db.scalar(
        select(Sponsor).where(
            Sponsor.contact_email == str(payload.contact_email).lower()
        )
    )
    if existing:
        existing.company_name = payload.company_name.strip()
        existing.display_name = payload.company_name.strip()
        existing.contact_name = payload.contact_name.strip()
        if payload.website:
            existing.website = payload.website
            existing.website_url = payload.website
        if user:
            if existing.user_id is None:
                existing.user_id = user.id
            if existing.owner_user_id is None:
                existing.owner_user_id = user.id
        return existing

    display = payload.company_name.strip()
    sponsor = Sponsor(
        user_id=user.id if user else None,
        owner_user_id=user.id if user else None,
        company_name=display,
        display_name=display,
        contact_name=payload.contact_name.strip(),
        contact_email=str(payload.contact_email).lower(),
        website=payload.website,
        website_url=payload.website,
        status="active",
        verification_status="unverified",
        visibility="private",
        onboarding_status="legacy",
        sponsor_type="other",
    )
    db.add(sponsor)
    db.flush()
    return sponsor


def submit_inquiry(
    db: Session,
    *,
    slot_id: UUID,
    payload: SponsorshipInquiryCreate,
    user: User | None = None,
) -> dict:
    slot = db.get(SponsorshipSlot, slot_id)
    if slot is None or not _is_publicly_visible(db, slot):
        raise HTTPException(status_code=404, detail="Sponsorship slot not found")

    sponsor = _upsert_sponsor_from_inquiry(db, payload=payload, user=user)
    if user:
        from app.sponsor_profiles.service import list_owned_sponsors

        owned = list_owned_sponsors(db, user.id)
        if owned:
            primary = max(owned, key=lambda s: s.created_at)
            sponsor = primary
            primary.company_name = payload.company_name.strip()
            primary.display_name = payload.company_name.strip()
            primary.contact_name = payload.contact_name.strip()
            if payload.website:
                primary.website = payload.website
                primary.website_url = payload.website
    if payload.sponsor_id is not None and user:
        from app.sponsor_profiles.service import require_sponsor_access

        chosen, _ = require_sponsor_access(
            db,
            user=user,
            sponsor_id=payload.sponsor_id,
            permission="sponsors.view_inquiries",
        )
        sponsor = chosen
    campaign_id = payload.campaign_id
    if campaign_id is not None:
        from app.sponsor_profiles.campaign_service import validate_inquiry_campaign

        validate_inquiry_campaign(
            db, sponsor_id=sponsor.id, campaign_id=campaign_id
        )
    inquiry = SponsorshipInquiry(
        slot_id=slot.id,
        sponsor_id=sponsor.id,
        campaign_id=campaign_id,
        company_name=payload.company_name.strip(),
        contact_name=payload.contact_name.strip(),
        contact_email=str(payload.contact_email).lower(),
        website=payload.website,
        message=payload.message.strip(),
        proposed_budget=(
            Decimal(payload.proposed_budget).quantize(Decimal("0.01"))
            if payload.proposed_budget is not None
            else None
        ),
        status="new",
    )
    db.add(inquiry)
    db.flush()
    write_audit_log(
        db,
        action="sponsorships.inquiry_submit",
        actor_user_id=user.id if user else None,
        resource_type="sponsorship_inquiry",
        resource_id=str(inquiry.id),
        details={
            "slot_id": str(slot.id),
            "company_name": inquiry.company_name,
            "contact_email": inquiry.contact_email,
        },
    )
    from app.email.service import enqueue_template
    from app.hosts.models import Host
    from app.users.models import User as UserModel

    host = db.get(Host, slot.host_id)
    host_name = host.display_name if host and host.display_name else "the host"
    enqueue_template(
        db,
        template="sponsor_inquiry_confirmation",
        to=inquiry.contact_email,
        recipient_user_id=user.id if user else None,
        dedupe_key=f"sponsor_inquiry:{inquiry.id}:confirmation",
        context={"host_name": host_name, "brand_name": inquiry.company_name},
    )
    from app.notifications.service import notify_user

    if user is not None:
        notify_user(
            db,
            user_id=user.id,
            kind="sponsor.inquiry_received",
            title="Sponsorship inquiry sent",
            body=f"Your inquiry to {host_name} was received on Pàdéyá.",
            link_path="/sponsorships",
            dedupe_key=f"sponsor_inquiry:{inquiry.id}:sponsor.notif",
        )
    if host is not None:
        host_user = db.get(UserModel, host.user_id)
        if host_user is not None:
            if host_user.email:
                enqueue_template(
                    db,
                    template="sponsor_inquiry_host_alert",
                    to=host_user.email,
                    recipient_user_id=host_user.id,
                    dedupe_key=f"sponsor_inquiry:{inquiry.id}:host_alert",
                    context={"brand_name": inquiry.company_name, "host_name": host_name},
                )
            notify_user(
                db,
                user_id=host_user.id,
                kind="sponsor.inquiry_host",
                title="New sponsor inquiry on Pàdéyá",
                body=f"{inquiry.company_name} sent a sponsorship inquiry.",
                link_path="/host/sponsorships",
                dedupe_key=f"sponsor_inquiry:{inquiry.id}:host.notif",
            )
    from app.email.admin_triggers import admin_notify_sponsor_inquiry

    admin_notify_sponsor_inquiry(
        db,
        inquiry_id=inquiry.id,
        host_name=host_name,
        brand_name=inquiry.company_name,
    )
    db.commit()
    db.refresh(inquiry)
    return _serialize_inquiry(db, inquiry)


def _serialize_inquiry(db: Session, inquiry: SponsorshipInquiry) -> dict:
    slot = db.get(SponsorshipSlot, inquiry.slot_id)
    return {
        "id": inquiry.id,
        "slot_id": inquiry.slot_id,
        "sponsor_id": inquiry.sponsor_id,
        "campaign_id": inquiry.campaign_id,
        "company_name": inquiry.company_name,
        "contact_name": inquiry.contact_name,
        "contact_email": inquiry.contact_email,
        "website": inquiry.website,
        "message": inquiry.message,
        "proposed_budget": inquiry.proposed_budget,
        "status": inquiry.status,
        "host_note": inquiry.host_note,
        "slot_title": slot.title if slot else None,
        "created_at": inquiry.created_at,
        "updated_at": inquiry.updated_at,
    }


def list_host_inquiries(db: Session, user: User) -> list[dict]:
    host, _ = _require_view_inquiries(db, user=user)
    rows = db.scalars(
        select(SponsorshipInquiry)
        .join(SponsorshipSlot, SponsorshipSlot.id == SponsorshipInquiry.slot_id)
        .where(SponsorshipSlot.host_id == host.id)
        .order_by(SponsorshipInquiry.created_at.desc())
    ).all()
    return [_serialize_inquiry(db, r) for r in rows]


def update_inquiry(
    db: Session, *, user: User, inquiry_id: UUID, payload: SponsorshipInquiryUpdate
) -> dict:
    if payload.status in {"accepted", "declined"}:
        permission: str | tuple[str, ...] = (
            "sponsors.accept_or_reject",
            "sponsors.manage_slots",
        )
    else:
        permission = (
            "sponsors.reply",
            "sponsors.accept_or_reject",
            "sponsors.manage_slots",
        )
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission=permission
    )
    inquiry = db.get(SponsorshipInquiry, inquiry_id)
    if inquiry is None:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    slot = db.get(SponsorshipSlot, inquiry.slot_id)
    if slot is None or slot.host_id != host.id:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    inquiry.status = payload.status
    if payload.host_note is not None:
        inquiry.host_note = payload.host_note
    write_audit_log(
        db,
        action="sponsorships.inquiry_update",
        actor_user_id=user.id,
        resource_type="sponsorship_inquiry",
        resource_id=str(inquiry.id),
        details={"status": payload.status},
    )
    from app.email.service import enqueue_template
    from app.notifications.service import notify_user

    sponsor_user_id = None
    if inquiry.sponsor_id is not None:
        sponsor = db.get(Sponsor, inquiry.sponsor_id)
        if sponsor is not None:
            sponsor_user_id = sponsor.user_id

    enqueue_template(
        db,
        template="sponsor_inquiry_status_update",
        to=inquiry.contact_email,
        recipient_user_id=sponsor_user_id,
        dedupe_key=f"sponsor_inquiry:{inquiry.id}:status:{payload.status}",
        context={"inquiry_status": payload.status},
    )
    if sponsor_user_id is not None:
        notify_user(
            db,
            user_id=sponsor_user_id,
            kind="sponsor.inquiry_status",
            title="Sponsorship inquiry update",
            body=f"Your inquiry was marked {payload.status} on Pàdéyá.",
            link_path="/sponsorships",
            dedupe_key=f"sponsor_inquiry:{inquiry.id}:status.notif:{payload.status}",
        )
    db.commit()
    db.refresh(inquiry)
    return _serialize_inquiry(db, inquiry)


def create_placement(
    db: Session, *, user: User, payload: SponsorshipPlacementCreate
) -> dict:
    host, _ = _require_manage_slots(db, user=user)
    slot = db.get(SponsorshipSlot, payload.slot_id)
    if slot is None or slot.host_id != host.id:
        raise HTTPException(status_code=404, detail="Slot not found")
    sponsor = db.get(Sponsor, payload.sponsor_id)
    if sponsor is None:
        raise HTTPException(status_code=404, detail="Sponsor not found")

    placement = SponsorshipPlacement(
        slot_id=slot.id,
        sponsor_id=sponsor.id,
        inquiry_id=payload.inquiry_id,
        status=payload.status,
        asset_url=payload.asset_url,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    db.add(placement)
    db.flush()
    analytics = SponsorshipAnalytics(placement_id=placement.id)
    db.add(analytics)
    write_audit_log(
        db,
        action="sponsorships.placement_create",
        actor_user_id=user.id,
        resource_type="sponsorship_placement",
        resource_id=str(placement.id),
        details={"slot_id": str(slot.id), "sponsor_id": str(sponsor.id)},
    )
    db.commit()
    db.refresh(placement)
    return _serialize_placement(db, placement)


def _serialize_placement(db: Session, placement: SponsorshipPlacement) -> dict:
    slot = db.get(SponsorshipSlot, placement.slot_id)
    sponsor = db.get(Sponsor, placement.sponsor_id)
    analytics = db.scalar(
        select(SponsorshipAnalytics).where(
            SponsorshipAnalytics.placement_id == placement.id
        )
    )
    return {
        "id": placement.id,
        "slot_id": placement.slot_id,
        "sponsor_id": placement.sponsor_id,
        "inquiry_id": placement.inquiry_id,
        "status": placement.status,
        "asset_url": placement.asset_url,
        "starts_at": placement.starts_at,
        "ends_at": placement.ends_at,
        "company_name": sponsor.company_name if sponsor else None,
        "slot_title": slot.title if slot else None,
        "analytics": (
            {
                "placement_id": analytics.placement_id,
                "impressions": analytics.impressions,
                "clicks": analytics.clicks,
                "inquiries_attributed": analytics.inquiries_attributed,
            }
            if analytics
            else None
        ),
        "created_at": placement.created_at,
    }


def list_host_placements(db: Session, user: User) -> list[dict]:
    host, _ = _require_view_slots(db, user=user)
    rows = db.scalars(
        select(SponsorshipPlacement)
        .join(SponsorshipSlot, SponsorshipSlot.id == SponsorshipPlacement.slot_id)
        .where(SponsorshipSlot.host_id == host.id)
        .order_by(SponsorshipPlacement.created_at.desc())
    ).all()
    return [_serialize_placement(db, r) for r in rows]


def record_placement_impression(db: Session, placement_id: UUID) -> dict:
    analytics = db.scalar(
        select(SponsorshipAnalytics).where(
            SponsorshipAnalytics.placement_id == placement_id
        )
    )
    if analytics is None:
        raise HTTPException(status_code=404, detail="Placement analytics not found")
    analytics.impressions += 1
    db.commit()
    db.refresh(analytics)
    return {
        "placement_id": analytics.placement_id,
        "impressions": analytics.impressions,
        "clicks": analytics.clicks,
        "inquiries_attributed": analytics.inquiries_attributed,
    }


def record_placement_click(db: Session, placement_id: UUID) -> dict:
    analytics = db.scalar(
        select(SponsorshipAnalytics).where(
            SponsorshipAnalytics.placement_id == placement_id
        )
    )
    if analytics is None:
        raise HTTPException(status_code=404, detail="Placement analytics not found")
    analytics.clicks += 1
    db.commit()
    db.refresh(analytics)
    return {
        "placement_id": analytics.placement_id,
        "impressions": analytics.impressions,
        "clicks": analytics.clicks,
        "inquiries_attributed": analytics.inquiries_attributed,
    }


def list_admin_slots(db: Session, user: User) -> list[dict]:
    if not user_has_permission(user, "sponsorships.moderate") and not user_has_permission(
        user, "admin.full_access"
    ):
        raise HTTPException(status_code=403, detail="Not allowed")
    rows = db.scalars(
        select(SponsorshipSlot).order_by(SponsorshipSlot.created_at.desc()).limit(200)
    ).all()
    return [serialize_slot(db, s) for s in rows]


def moderate_slot(
    db: Session,
    *,
    user: User,
    slot_id: UUID,
    payload: SponsorshipModerateRequest,
) -> dict:
    if not user_has_permission(user, "sponsorships.moderate") and not user_has_permission(
        user, "admin.full_access"
    ):
        raise HTTPException(status_code=403, detail="Not allowed")

    slot = db.get(SponsorshipSlot, slot_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="Slot not found")

    now = datetime.now(UTC)
    if payload.action == "flag":
        slot.moderation_status = "flagged"
    elif payload.action == "approve":
        slot.moderation_status = "approved"
    elif payload.action == "disable":
        slot.status = "disabled"
        slot.moderation_status = "flagged"
    elif payload.action == "remove":
        slot.status = "disabled"
        slot.moderation_status = "removed"
    else:
        raise HTTPException(status_code=400, detail="Unsupported action")

    slot.moderation_note = payload.note
    slot.moderated_by_user_id = user.id
    slot.moderated_at = now
    write_audit_log(
        db,
        action=f"sponsorships.moderate.{payload.action}",
        actor_user_id=user.id,
        resource_type="sponsorship_slot",
        resource_id=str(slot.id),
        details={"note": payload.note, "status": slot.status},
    )
    db.commit()
    db.refresh(slot)
    _invalidate_public_sponsorship_cache(slot_id=slot.id)
    return serialize_slot(db, slot)
