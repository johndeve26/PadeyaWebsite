"""Merch pickup QR — typ=padeya.merch.pickup (never ticket QR)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.merch.constants import MERCH_QR_TYP
from app.merch.fulfillment import (
    _assert_pickup_allowed,
    _record_fulfillment_event,
    update_fulfillment_status,
)
from app.merch.models import EventMerchVariant, MerchFulfillment
from app.users.models import User


def hash_merch_qr_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


def create_merch_pickup_qr_payload(
    *,
    fulfillment_id: UUID | str,
    event_id: UUID | str | None,
    pickup_code: str,
    jti: str,
    expires_days: int = 365,
) -> str:
    """Signed merch pickup token — distinct from padeya.ticket.qr."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "typ": MERCH_QR_TYP,
        "fid": str(fulfillment_id),
        "code": pickup_code,
        "eid": str(event_id) if event_id else None,
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(days=expires_days),
    }
    return jwt.encode(payload, settings.effective_qr_secret, algorithm="HS256")


def decode_merch_pickup_qr_payload(token: str) -> dict[str, Any]:
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.effective_qr_secret,
        algorithms=["HS256"],
    )
    if payload.get("typ") != MERCH_QR_TYP:
        raise jwt.InvalidTokenError("Invalid merch QR token type")
    return payload


def issue_pickup_qr_for_fulfillment(db: Session, fulfillment: MerchFulfillment) -> str:
    """Generate signed QR + store hash. Returns token for buyer display only."""
    jti = secrets.token_urlsafe(24)
    token = create_merch_pickup_qr_payload(
        fulfillment_id=fulfillment.id,
        event_id=fulfillment.event_id,
        pickup_code=fulfillment.pickup_code,
        jti=jti,
    )
    fulfillment.pickup_qr_token_hash = hash_merch_qr_jti(jti)
    db.flush()
    return token


def buyer_qr_token_if_eligible(db: Session, fulfillment: MerchFulfillment) -> str | None:
    """Re-issue display token when paid and not cancelled/picked up. No address data."""
    if fulfillment.status in {"cancelled", "fulfilled"}:
        return None
    if (fulfillment.fulfillment_method or "pickup") != "pickup":
        return None
    jti = secrets.token_urlsafe(24)
    token = create_merch_pickup_qr_payload(
        fulfillment_id=fulfillment.id,
        event_id=fulfillment.event_id,
        pickup_code=fulfillment.pickup_code,
        jti=jti,
    )
    # First issue stores hash; later display tokens validate via pickup code match on scan.
    if not fulfillment.pickup_qr_token_hash:
        fulfillment.pickup_qr_token_hash = hash_merch_qr_jti(jti)
        db.flush()
    return token


def scan_merch_pickup(
    db: Session,
    *,
    user: User,
    event_id: UUID,
    token: str | None = None,
    pickup_code: str | None = None,
) -> dict:
    """Staff desk scan — rejects ticket QR types; marks picked up server-side."""
    from app.events.models import Event
    from app.teams.permissions import can_scan_merch_pickup, merch_scan_denial_reason
    from app.teams.scan_audit import write_desk_scan_audit

    event = db.get(Event, event_id)
    host_id = event.host_id if event is not None else None
    allowed = host_id is not None and can_scan_merch_pickup(
        db, user_id=user.id, host_profile_id=host_id, event_id=event_id
    )

    if not allowed:
        reason = (
            merch_scan_denial_reason(db, user.id, host_id, event_id)
            if host_id is not None
            else "Event not found"
        )
        write_desk_scan_audit(
            db,
            actor_user_id=user.id,
            host_profile_id=host_id,
            event_id=event_id,
            action="merch.scan_pickup",
            result="denied",
            denial_reason=reason or "Not allowed to fulfill merch",
        )
        db.commit()
        raise HTTPException(
            status_code=403,
            detail=reason or "Not allowed to fulfill merch",
        )

    row: MerchFulfillment | None = None
    if token:
        try:
            payload = decode_merch_pickup_qr_payload(token)
        except jwt.InvalidTokenError as exc:
            write_desk_scan_audit(
                db,
                actor_user_id=user.id,
                host_profile_id=host_id,
                event_id=event_id,
                action="merch.scan_pickup",
                result="invalid",
                denial_reason="Invalid merch pickup QR",
            )
            db.commit()
            raise HTTPException(
                status_code=400,
                detail="Invalid merch pickup QR (ticket QR is not accepted here)",
            ) from exc
        fid = payload.get("fid")
        if not fid:
            raise HTTPException(status_code=400, detail="Merch QR missing fulfillment id")
        row = db.get(MerchFulfillment, UUID(str(fid)))
        if row is None:
            write_desk_scan_audit(
                db,
                actor_user_id=user.id,
                host_profile_id=host_id,
                event_id=event_id,
                action="merch.scan_pickup",
                result="invalid",
                denial_reason="Merch item not found",
            )
            db.commit()
            raise HTTPException(status_code=404, detail="Merch item not found")
        jti = payload.get("jti")
        if jti and row.pickup_qr_token_hash:
            # Accept if hash matches stored jti OR pickup code matches (re-issued display).
            if (
                hash_merch_qr_jti(str(jti)) != row.pickup_qr_token_hash
                and payload.get("code") != row.pickup_code
            ):
                write_desk_scan_audit(
                    db,
                    actor_user_id=user.id,
                    host_profile_id=host_id,
                    event_id=event_id,
                    action="merch.scan_pickup",
                    result="invalid",
                    merch_order_item_id=row.order_item_id,
                    denial_reason="Merch QR token mismatch",
                )
                db.commit()
                raise HTTPException(status_code=400, detail="Merch QR token mismatch")
        _record_fulfillment_event(
            db,
            fulfillment=row,
            action="qr_scanned",
            actor_user_id=user.id,
        )
        scan_method = "qr"
    elif pickup_code:
        code = pickup_code.strip().upper()
        row = db.scalar(
            select(MerchFulfillment).where(MerchFulfillment.pickup_code == code)
        )
        if row is None:
            write_desk_scan_audit(
                db,
                actor_user_id=user.id,
                host_profile_id=host_id,
                event_id=event_id,
                action="merch.scan_pickup",
                result="invalid",
                denial_reason="Pickup code not found",
            )
            db.commit()
            raise HTTPException(status_code=404, detail="Pickup code not found")
        scan_method = "code"
    else:
        raise HTTPException(status_code=400, detail="Provide token or pickup_code")

    assert row is not None
    if row.event_id is not None and row.event_id != event_id:
        write_desk_scan_audit(
            db,
            actor_user_id=user.id,
            host_profile_id=host_id,
            event_id=event_id,
            action="merch.scan_pickup",
            result="denied",
            merch_order_item_id=row.order_item_id,
            denial_reason="Merch item belongs to another event",
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Merch item belongs to another event")
    if row.fulfillment_method != "pickup":
        raise HTTPException(status_code=400, detail="This item is not pickup fulfillment")
    _assert_pickup_allowed(db, row)
    from app.analytics.trusted import emit_merch_qr_scanned

    variant = db.get(EventMerchVariant, row.merch_variant_id)
    emit_merch_qr_scanned(
        db,
        fulfillment_id=row.id,
        event_id=row.event_id or event_id,
        host_id=row.host_id,
        actor_user_id=user.id,
        merch_product_id=variant.product_id if variant else None,
        merch_variant_id=row.merch_variant_id,
        method=scan_method,
    )
    result = update_fulfillment_status(
        db, user=user, fulfillment_id=row.id, status="fulfilled"
    )
    write_desk_scan_audit(
        db,
        actor_user_id=user.id,
        host_profile_id=host_id or row.host_id,
        event_id=event_id,
        action="merch.scan_pickup",
        result="success",
        merch_order_item_id=row.order_item_id,
        metadata={"method": scan_method, "fulfillment_id": str(row.id)},
    )
    db.commit()
    # Desk scan summary: product/variant/qty/code + staff stamp — no contact/address.
    result["buyer_email"] = None
    result["shipping_address"] = None
    result["qr_token"] = None
    return result


def attach_qr_to_serialize(db: Session, data: dict, row: MerchFulfillment) -> dict:
    """Add qr_token for eligible buyer pickup display only."""
    if row.fulfillment_method != "pickup":
        data["qr_token"] = None
        data["qr_typ"] = MERCH_QR_TYP
        return data
    if row.status in {"cancelled", "fulfilled"}:
        data["qr_token"] = None
        data["qr_typ"] = MERCH_QR_TYP
        return data
    data["qr_token"] = buyer_qr_token_if_eligible(db, row)
    data["qr_typ"] = MERCH_QR_TYP
    data["fulfillment_method"] = row.fulfillment_method
    return data
