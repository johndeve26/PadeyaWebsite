"""Private shipping addresses + zone fee calculation."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.sensitive import decrypt_sensitive, encrypt_sensitive
from app.merch.models import MerchShippingAddress, MerchShippingZone
from app.payments.models import Order
from app.users.models import User


def create_shipping_address(
    db: Session,
    *,
    order: Order,
    buyer: User,
    recipient_name: str,
    phone: str,
    line1: str,
    line2: str | None,
    city: str,
    state: str,
    country: str,
    postal_code: str | None = None,
    notes: str | None = None,
) -> MerchShippingAddress:
    if not recipient_name.strip() or not phone.strip() or not line1.strip():
        raise HTTPException(status_code=400, detail="Shipping address is incomplete")
    if not city.strip() or not state.strip() or not country.strip():
        raise HTTPException(status_code=400, detail="City, state, and country are required")

    row = MerchShippingAddress(
        order_id=order.id,
        buyer_user_id=buyer.id,
        recipient_name_enc=encrypt_sensitive(recipient_name.strip()),
        phone_enc=encrypt_sensitive(phone.strip()),
        line1_enc=encrypt_sensitive(line1.strip()),
        line2_enc=encrypt_sensitive(line2.strip()) if line2 and line2.strip() else None,
        notes_enc=encrypt_sensitive(notes.strip()) if notes and notes.strip() else None,
        city=city.strip()[:80],
        state=state.strip()[:80],
        country=country.strip()[:80],
        postal_code=(postal_code or "").strip()[:32] or None,
    )
    db.add(row)
    db.flush()
    order.shipping_address_id = row.id
    return row


def decrypt_address_for_staff(row: MerchShippingAddress) -> dict[str, str | None]:
    """Host/desk only — never used in public serializers or analytics."""
    return {
        "recipient_name": decrypt_sensitive(row.recipient_name_enc),
        "phone": decrypt_sensitive(row.phone_enc),
        "line1": decrypt_sensitive(row.line1_enc),
        "line2": decrypt_sensitive(row.line2_enc) if row.line2_enc else None,
        "notes": decrypt_sensitive(row.notes_enc) if row.notes_enc else None,
        "city": row.city,
        "state": row.state,
        "country": row.country,
        "postal_code": row.postal_code,
    }


def public_shipping_hint(row: MerchShippingAddress | None) -> dict[str, str | None] | None:
    """Safe summary for buyer UI — city/state/country only, no street/phone."""
    if row is None:
        return None
    return {
        "city": row.city,
        "state": row.state,
        "country": row.country,
        # Never expose encrypted fields or phone.
        "recipient_name": None,
        "phone": None,
        "line1": None,
        "line2": None,
        "notes": None,
        "postal_code": None,
    }


def match_shipping_zone(
    db: Session,
    *,
    host_id: uuid.UUID,
    event_id: uuid.UUID | None,
    country: str,
    state: str,
    city: str,
) -> MerchShippingZone | None:
    zones = list(
        db.scalars(
            select(MerchShippingZone).where(
                MerchShippingZone.host_id == host_id,
                MerchShippingZone.status == "active",
            )
        )
    )
    country_l = country.strip().lower()
    state_l = state.strip().lower()
    city_l = city.strip().lower()
    best: MerchShippingZone | None = None
    best_score = -1
    for z in zones:
        if event_id is not None and z.event_id is not None and z.event_id != event_id:
            continue
        if z.country.strip().lower() != country_l:
            continue
        score = 1
        if z.state:
            if z.state.strip().lower() != state_l:
                continue
            score += 1
        if z.city:
            if z.city.strip().lower() != city_l:
                continue
            score += 1
        if score > best_score:
            best = z
            best_score = score
    return best


def compute_shipping_fee(
    db: Session,
    *,
    host_id: uuid.UUID,
    event_id: uuid.UUID | None,
    country: str,
    state: str,
    city: str,
) -> Decimal:
    """Charge zone flat fee when the host has active zones; otherwise ₦0.

    When zones exist, destination must match or checkout is rejected.
    """
    active = list(
        db.scalars(
            select(MerchShippingZone).where(
                MerchShippingZone.host_id == host_id,
                MerchShippingZone.status == "active",
            )
        )
    )
    relevant = [
        z
        for z in active
        if event_id is None or z.event_id is None or z.event_id == event_id
    ]
    if not relevant:
        return Decimal("0.00")

    zone = match_shipping_zone(
        db,
        host_id=host_id,
        event_id=event_id,
        country=country,
        state=state,
        city=city,
    )
    if zone is None:
        raise HTTPException(
            status_code=400,
            detail="Shipping is not available to this location",
        )
    return Decimal(zone.flat_fee)


ZONE_STATUSES = frozenset({"active", "inactive", "archived"})


def serialize_zone(row: MerchShippingZone) -> dict:
    """Host-safe zone payload — never includes buyer addresses."""
    return {
        "id": row.id,
        "name": row.name,
        "country": row.country,
        "state": row.state,
        "city": row.city,
        "flat_fee": row.flat_fee,
        "currency": row.currency,
        "event_id": row.event_id,
        "status": row.status,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def list_host_zones(db: Session, *, host_id: uuid.UUID) -> list[MerchShippingZone]:
    return list(
        db.scalars(
            select(MerchShippingZone)
            .where(MerchShippingZone.host_id == host_id)
            .order_by(MerchShippingZone.created_at.desc())
        )
    )


def _get_host_zone(
    db: Session, *, host_id: uuid.UUID, zone_id: uuid.UUID
) -> MerchShippingZone:
    row = db.get(MerchShippingZone, zone_id)
    if row is None or row.host_id != host_id:
        raise HTTPException(status_code=404, detail="Shipping zone not found")
    return row


def upsert_zone(
    db: Session,
    *,
    host_id: uuid.UUID,
    name: str,
    country: str,
    state: str | None,
    city: str | None,
    flat_fee: Decimal,
    event_id: uuid.UUID | None = None,
    zone_id: uuid.UUID | None = None,
) -> MerchShippingZone:
    if zone_id:
        row = _get_host_zone(db, host_id=host_id, zone_id=zone_id)
    else:
        row = MerchShippingZone(host_id=host_id)
        db.add(row)
    row.name = name.strip()[:120]
    row.country = country.strip()[:80]
    row.state = (state or "").strip()[:80] or None
    row.city = (city or "").strip()[:80] or None
    row.flat_fee = Decimal(flat_fee)
    row.event_id = event_id
    row.status = "active"
    db.flush()
    return row


def update_zone(
    db: Session,
    *,
    host_id: uuid.UUID,
    zone_id: uuid.UUID,
    name: str | None = None,
    country: str | None = None,
    state: str | None = None,
    city: str | None = None,
    flat_fee: Decimal | None = None,
    event_id: uuid.UUID | None = None,
    clear_event_id: bool = False,
    status: str | None = None,
) -> MerchShippingZone:
    """Partial update for a host-owned zone. Archived zones stay out of checkout."""
    row = _get_host_zone(db, host_id=host_id, zone_id=zone_id)
    if name is not None:
        cleaned = name.strip()
        if not cleaned:
            raise HTTPException(status_code=400, detail="Name is required")
        row.name = cleaned[:120]
    if country is not None:
        cleaned = country.strip()
        if not cleaned:
            raise HTTPException(status_code=400, detail="Country is required")
        row.country = cleaned[:80]
    if state is not None:
        row.state = state.strip()[:80] or None
    if city is not None:
        row.city = city.strip()[:80] or None
    if flat_fee is not None:
        if Decimal(flat_fee) < 0:
            raise HTTPException(status_code=400, detail="flat_fee must be >= 0")
        row.flat_fee = Decimal(flat_fee)
    if clear_event_id:
        row.event_id = None
    elif event_id is not None:
        row.event_id = event_id
    if status is not None:
        cleaned_status = status.strip().lower()
        if cleaned_status not in ZONE_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"status must be one of: {', '.join(sorted(ZONE_STATUSES))}",
            )
        row.status = cleaned_status
    db.flush()
    return row


def archive_zone(
    db: Session, *, host_id: uuid.UUID, zone_id: uuid.UUID
) -> MerchShippingZone:
    """Soft-archive: excluded from new checkout fee matching; past orders unchanged."""
    return update_zone(
        db, host_id=host_id, zone_id=zone_id, status="archived"
    )
