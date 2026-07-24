"""Demo-only sponsorship slot seeding — bypasses runtime permission checks."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.demo.models import DemoEntityMarker
from app.hosts.models import Host, HostVerification
from app.sponsorships.models import HostSponsorshipSettings, SponsorshipSlot
from app.sponsorships.service import get_or_create_settings


def _mark_slot(db: Session, host_slug: str, title: str, slot_id: UUID) -> None:
    key = f"{host_slug}:{title}"
    existing = db.scalar(
        select(DemoEntityMarker.id).where(
            DemoEntityMarker.entity_type == "sponsorship_slot",
            DemoEntityMarker.entity_key == key,
        )
    )
    if existing is None:
        db.add(
            DemoEntityMarker(
                entity_type="sponsorship_slot",
                entity_key=key,
                entity_id=str(slot_id),
            )
        )


def _host_is_verified(db: Session, host_id: UUID) -> bool:
    latest = db.scalars(
        select(HostVerification)
        .where(HostVerification.host_id == host_id)
        .order_by(HostVerification.created_at.desc())
        .limit(1)
    ).first()
    return latest is not None and latest.status == "verified"


def _host_accepts_sponsors(db: Session, host_id: UUID) -> bool:
    settings = db.scalar(
        select(HostSponsorshipSettings).where(
            HostSponsorshipSettings.host_id == host_id
        )
    )
    if settings is None:
        return False
    return bool(settings.accepting_sponsors)


def create_demo_sponsorship_slot(
    db: Session,
    *,
    host: Host,
    title: str,
    slot_type: str,
    description: str,
    price: Decimal,
    event_id: UUID | None = None,
    status: str = "published",
    moderation_status: str = "approved",
) -> SponsorshipSlot | None:
    """Create a valid sponsorship slot row for demo seed only.

    Validates host/product rules but does not invoke runtime service permissions,
    audit logs, or per-row commits.
    """
    if host.status != "active":
        return None
    if status == "published":
        if not _host_is_verified(db, host.id):
            return None
        if not _host_accepts_sponsors(db, host.id):
            return None
        if moderation_status in {"removed"}:
            return None

    existing_id = db.scalar(
        select(SponsorshipSlot.id).where(
            SponsorshipSlot.host_id == host.id,
            SponsorshipSlot.title == title,
        )
    )
    if existing_id is not None:
        return db.get(SponsorshipSlot, existing_id)

    published_at = datetime.now(UTC) if status == "published" else None
    slot = SponsorshipSlot(
        host_id=host.id,
        event_id=event_id,
        slot_type=slot_type,
        title=title.strip(),
        description=description.strip(),
        price=Decimal(price).quantize(Decimal("0.01")),
        currency="NGN",
        status=status if status in {"draft", "published", "disabled"} else "draft",
        moderation_status=moderation_status,
        published_at=published_at,
    )
    db.add(slot)
    db.flush()
    _mark_slot(db, host.slug or str(host.id), title, slot.id)
    return slot


def ensure_demo_host_sponsorship_settings(
    db: Session,
    *,
    host: Host,
    accepting_sponsors: bool,
    contact_email: str | None,
    pitch: str | None,
) -> HostSponsorshipSettings:
    settings = get_or_create_settings(db, host.id)
    settings.accepting_sponsors = accepting_sponsors
    settings.pitch = pitch
    settings.contact_email = contact_email
    db.flush()
    return settings


def count_demo_published_slots(db: Session, host_ids: list[UUID]) -> int:
    if not host_ids:
        return 0
    return int(
        db.scalar(
            select(func.count())
            .select_from(SponsorshipSlot)
            .where(
                SponsorshipSlot.host_id.in_(host_ids),
                SponsorshipSlot.status == "published",
                SponsorshipSlot.moderation_status != "removed",
            )
        )
        or 0
    )
