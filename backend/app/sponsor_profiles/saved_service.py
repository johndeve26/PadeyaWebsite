"""Sponsor saved hosts, events, and sponsorship slots."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.events.models import Event
from app.hosts.models import Host, HostProfile
from app.sponsor_profiles.constants import SAVED_ITEM_TYPES
from app.sponsor_profiles.saved_schemas import (
    SponsorSavedItemCreate,
    SponsorSavedItemNoteUpdate,
)
from app.sponsor_profiles.service import require_sponsor_access
from app.sponsorships.models import Sponsor, SponsorSavedItem, SponsorshipSlot
from app.sponsorships.service import _is_publicly_visible, host_is_verified
from app.users.models import User


def _member_role(db: Session, sponsor: Sponsor, user_id: uuid.UUID) -> str | None:
    if sponsor.owner_user_id == user_id:
        return "owner"
    from app.sponsorships.models import SponsorTeamMember

    row = db.scalar(
        select(SponsorTeamMember).where(
            SponsorTeamMember.sponsor_id == sponsor.id,
            SponsorTeamMember.user_id == user_id,
            SponsorTeamMember.status == "active",
            SponsorTeamMember.removed_at.is_(None),
        )
    )
    return row.role if row else None


def require_sponsor_can_save(
    db: Session, *, user: User, sponsor_id: uuid.UUID
) -> Sponsor:
    sponsor, perms = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    role = _member_role(db, sponsor, user.id)
    can = perms.get("sponsors.save_items") and role in {
        "owner",
        "admin",
        "campaign_manager",
    }
    if not can:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot save items for this sponsor workspace",
        )
    return sponsor


def _validate_save_target(db: Session, *, item_type: str, item_id: uuid.UUID) -> None:
    if item_type == "host":
        host = db.get(Host, item_id)
        if host is None or host.status != "active":
            raise HTTPException(status_code=404, detail="Host not found")
        if not host_is_verified(db, host.id):
            raise HTTPException(status_code=400, detail="Host is not publicly available")
        return
    if item_type == "event":
        event = db.get(Event, item_id)
        if event is None or event.status != "published":
            raise HTTPException(status_code=404, detail="Event not found")
        return
    if item_type == "sponsorship_slot":
        slot = db.get(SponsorshipSlot, item_id)
        if slot is None or not _is_publicly_visible(db, slot):
            raise HTTPException(status_code=404, detail="Sponsorship slot not found")
        return
    raise HTTPException(status_code=400, detail="Invalid item_type")


def _enrich_item(db: Session, row: SponsorSavedItem) -> dict[str, Any]:
    available = False
    title: str | None = None
    subtitle: str | None = None
    href: str | None = None
    sort_host_name: str | None = None
    sort_event_date: datetime | None = None

    if row.item_type == "host":
        host = db.get(Host, row.item_id)
        if host and host.status == "active" and host_is_verified(db, host.id):
            available = True
            title = host.display_name
            sort_host_name = host.display_name.lower()
            profile = db.scalar(
                select(HostProfile).where(HostProfile.host_id == host.id)
            )
            subtitle = profile.city if profile and profile.city else None
            href = f"/u/{host.slug}"
    elif row.item_type == "event":
        event = db.get(Event, row.item_id)
        if event and event.status == "published":
            available = True
            title = event.title
            sort_event_date = event.start_datetime
            subtitle = event.slug
            href = f"/events/{event.slug}"
            host = db.get(Host, event.host_id)
            if host:
                sort_host_name = host.display_name.lower()
    elif row.item_type == "sponsorship_slot":
        slot = db.get(SponsorshipSlot, row.item_id)
        if slot and _is_publicly_visible(db, slot):
            available = True
            title = slot.title
            host = db.get(Host, slot.host_id)
            if host:
                subtitle = host.display_name
                sort_host_name = host.display_name.lower()
            href = "/sponsors#open-slots"
            if slot.event_id:
                event = db.get(Event, slot.event_id)
                if event:
                    sort_event_date = event.start_datetime

    return {
        "id": row.id,
        "sponsor_id": row.sponsor_id,
        "item_type": row.item_type,
        "item_id": row.item_id,
        "note": row.note,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "available": available,
        "title": title if available else None,
        "subtitle": subtitle if available else None,
        "href": href if available else None,
        "sort_host_name": sort_host_name,
        "sort_event_date": sort_event_date,
    }


def list_saved_items(
    db: Session,
    *,
    user: User,
    sponsor_id: uuid.UUID,
    item_type: str | None = None,
    sort: str = "newest",
) -> dict[str, Any]:
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    q = select(SponsorSavedItem).where(SponsorSavedItem.sponsor_id == sponsor.id)
    if item_type and item_type in SAVED_ITEM_TYPES:
        q = q.where(SponsorSavedItem.item_type == item_type)
    rows = list(db.scalars(q))
    enriched = [_enrich_item(db, r) for r in rows]
    if sort == "host_name":
        enriched.sort(key=lambda x: (x.get("sort_host_name") or "", x["created_at"]))
    elif sort == "event_date":
        enriched.sort(
            key=lambda x: (
                x.get("sort_event_date") or datetime.min.replace(tzinfo=UTC),
                x["created_at"],
            ),
            reverse=True,
        )
    else:
        enriched.sort(key=lambda x: x["created_at"], reverse=True)

    total = len(enriched)
    return {"items": enriched, "total": total, "saved_count": total}


def create_saved_item(
    db: Session,
    *,
    user: User,
    sponsor_id: uuid.UUID,
    payload: SponsorSavedItemCreate,
) -> dict[str, Any]:
    sponsor = require_sponsor_can_save(db, user=user, sponsor_id=sponsor_id)
    _validate_save_target(db, item_type=payload.item_type, item_id=payload.item_id)

    existing = db.scalar(
        select(SponsorSavedItem).where(
            SponsorSavedItem.sponsor_id == sponsor.id,
            SponsorSavedItem.item_type == payload.item_type,
            SponsorSavedItem.item_id == payload.item_id,
        )
    )
    if existing:
        if payload.note is not None:
            existing.note = payload.note
        db.flush()
        write_audit_log(
            db,
            action="sponsors.saved.upsert",
            actor_user_id=user.id,
            resource_type="sponsor_saved_item",
            resource_id=str(existing.id),
            details={"item_type": payload.item_type, "item_id": str(payload.item_id)},
        )
        db.commit()
        db.refresh(existing)
        return _enrich_item(db, existing)

    row = SponsorSavedItem(
        sponsor_id=sponsor.id,
        saved_by_user_id=user.id,
        item_type=payload.item_type,
        item_id=payload.item_id,
        note=payload.note,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="sponsors.saved.create",
        actor_user_id=user.id,
        resource_type="sponsor_saved_item",
        resource_id=str(row.id),
        details={"item_type": payload.item_type, "item_id": str(payload.item_id)},
    )
    db.commit()
    db.refresh(row)
    return _enrich_item(db, row)


def update_saved_note(
    db: Session,
    *,
    user: User,
    sponsor_id: uuid.UUID,
    saved_id: uuid.UUID,
    payload: SponsorSavedItemNoteUpdate,
) -> dict[str, Any]:
    sponsor = require_sponsor_can_save(db, user=user, sponsor_id=sponsor_id)
    row = db.get(SponsorSavedItem, saved_id)
    if row is None or row.sponsor_id != sponsor.id:
        raise HTTPException(status_code=404, detail="Saved item not found")
    row.note = payload.note
    write_audit_log(
        db,
        action="sponsors.saved.note",
        actor_user_id=user.id,
        resource_type="sponsor_saved_item",
        resource_id=str(row.id),
        details={},
    )
    db.commit()
    db.refresh(row)
    return _enrich_item(db, row)


def delete_saved_item(
    db: Session, *, user: User, sponsor_id: uuid.UUID, saved_id: uuid.UUID
) -> None:
    sponsor = require_sponsor_can_save(db, user=user, sponsor_id=sponsor_id)
    row = db.get(SponsorSavedItem, saved_id)
    if row is None or row.sponsor_id != sponsor.id:
        raise HTTPException(status_code=404, detail="Saved item not found")
    item_type = row.item_type
    item_id = row.item_id
    db.delete(row)
    write_audit_log(
        db,
        action="sponsors.saved.delete",
        actor_user_id=user.id,
        resource_type="sponsor_saved_item",
        resource_id=str(saved_id),
        details={"item_type": item_type, "item_id": str(item_id)},
    )
    db.commit()


def list_saved_item_keys(
    db: Session, *, sponsor_id: uuid.UUID, item_type: str | None = None
) -> list[dict[str, str]]:
    q = select(SponsorSavedItem).where(SponsorSavedItem.sponsor_id == sponsor_id)
    if item_type:
        q = q.where(SponsorSavedItem.item_type == item_type)
    rows = list(db.scalars(q))
    return [
        {"item_type": r.item_type, "item_id": str(r.item_id), "saved_id": str(r.id)}
        for r in rows
    ]
