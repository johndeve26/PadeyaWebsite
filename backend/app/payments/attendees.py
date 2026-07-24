"""Checkout attendee / gift purchase helpers.

Order belongs to the buyer. Tickets are assigned to attendees. Delivery goes
to buyer, recipient, or both based on order flags — only after verified payment.
Never claim a user account by email alone (recipient_user_id stays null unless
an explicit verified linking rule is added later).
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.payments.models import Order, OrderAttendee
from app.payments.schemas import AttendeeAssignmentIn, OrderCreate
from app.users.models import User

PurchaseMode = Literal["self", "other", "group"]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9\s\-().]{7,40}$")

# Soft rate limit: pending/paid checkout attempts per buyer per hour
from app.core.config import get_settings

_settings = get_settings()
CHECKOUT_ORDERS_PER_HOUR = 20 if _settings.app_env == "production" else 100


@dataclass(frozen=True)
class ResolvedAttendee:
    ticket_type_id: uuid.UUID
    unit_index: int
    name: str
    email: str
    phone: str | None
    delivery_email: str
    delivery_phone: str | None


def normalize_email(value: str) -> str:
    return value.strip().lower()


def validate_email(value: str, *, field: str = "email") -> str:
    email = normalize_email(value)
    if not email or len(email) > 320 or not EMAIL_RE.match(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field}",
        )
    return email


def validate_phone(value: str | None, *, field: str = "phone") -> str | None:
    if value is None:
        return None
    phone = value.strip()
    if not phone:
        return None
    if not PHONE_RE.match(phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field}",
        )
    return phone[:40]


def validate_name(value: str, *, field: str = "name") -> str:
    name = " ".join(value.split()).strip()
    if len(name) < 2 or len(name) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field}",
        )
    return name


def assert_checkout_rate_limit(db: Session, *, user_id: uuid.UUID) -> None:
    from datetime import UTC, datetime, timedelta

    since = datetime.now(UTC) - timedelta(hours=1)
    count = db.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.buyer_user_id == user_id, Order.created_at >= since)
    )
    if (count or 0) >= CHECKOUT_ORDERS_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many checkout attempts. Try again later.",
        )


def resolve_attendees_for_order(
    *,
    user: User | None,
    buyer_name: str,
    buyer_email: str,
    payload: OrderCreate,
    ticket_qty_by_type: dict[uuid.UUID, int],
) -> tuple[PurchaseMode, list[ResolvedAttendee], dict]:
    """Validate purchase mode + attendees. Returns mode, rows, order-level gift fields."""
    mode: PurchaseMode = payload.purchase_mode or "self"
    total_tickets = sum(ticket_qty_by_type.values())

    gift_fields = {
        "purchase_mode": mode,
        "is_gift": False,
        "purchased_for_someone_else": False,
        "gift_message": None,
        "send_ticket_to_recipient": False,
        "keep_buyer_copy": True,
        "recipient_name": None,
        "recipient_email": None,
        "recipient_phone": None,
        "recipient_user_id": None,
    }

    if total_tickets == 0:
        # Merch-only: ignore attendee payload
        return mode, [], gift_fields

    default_name = validate_name(buyer_name, field="buyer name")
    default_email = validate_email(buyer_email, field="buyer email")

    if mode == "self":
        # Prefill editable buyer details (optional override via attendees or recipient)
        name = default_name
        email = default_email
        phone = None
        if payload.attendee_name:
            name = validate_name(payload.attendee_name, field="attendee name")
        if payload.attendee_email:
            email = validate_email(payload.attendee_email, field="attendee email")
        if payload.attendee_phone is not None:
            phone = validate_phone(payload.attendee_phone, field="attendee phone")
        rows = [
            ResolvedAttendee(
                ticket_type_id=tt_id,
                unit_index=idx,
                name=name,
                email=email,
                phone=phone,
                delivery_email=email,
                delivery_phone=phone,
            )
            for tt_id, qty in ticket_qty_by_type.items()
            for idx in range(qty)
        ]
        gift_fields["keep_buyer_copy"] = True
        return mode, rows, gift_fields

    if mode == "other":
        name = validate_name(
            payload.recipient_name or payload.attendee_name or "",
            field="recipient name",
        )
        email = validate_email(
            payload.recipient_email or payload.attendee_email or "",
            field="recipient email",
        )
        phone = validate_phone(
            payload.recipient_phone or payload.attendee_phone,
            field="recipient phone",
        )
        gift_message = (payload.gift_message or "").strip() or None
        if gift_message and len(gift_message) > 1000:
            raise HTTPException(
                status_code=400, detail="Gift message must be under 1000 characters"
            )
        send_to = bool(payload.send_ticket_to_recipient)
        keep_copy = (
            True
            if payload.keep_buyer_copy is None
            else bool(payload.keep_buyer_copy)
        )
        if not send_to and not keep_copy:
            # Always deliver somewhere
            keep_copy = True
        rows = [
            ResolvedAttendee(
                ticket_type_id=tt_id,
                unit_index=idx,
                name=name,
                email=email,
                phone=phone,
                delivery_email=email,
                delivery_phone=phone,
            )
            for tt_id, qty in ticket_qty_by_type.items()
            for idx in range(qty)
        ]
        gift_fields.update(
            {
                "is_gift": True,
                "purchased_for_someone_else": True,
                "gift_message": gift_message,
                "send_ticket_to_recipient": send_to,
                "keep_buyer_copy": keep_copy,
                "recipient_name": name,
                "recipient_email": email,
                "recipient_phone": phone,
                # Never claim account by email alone
                "recipient_user_id": None,
            }
        )
        return mode, rows, gift_fields

    # group
    assignments = list(payload.attendees or [])
    use_same = bool(payload.use_same_buyer_details_for_all)
    expected = total_tickets

    if use_same:
        name = validate_name(
            payload.attendee_name or default_name,
            field="attendee name",
        )
        email = validate_email(
            payload.attendee_email or default_email,
            field="attendee email",
        )
        phone = validate_phone(payload.attendee_phone, field="attendee phone")
        rows = [
            ResolvedAttendee(
                ticket_type_id=tt_id,
                unit_index=idx,
                name=name,
                email=email,
                phone=phone,
                delivery_email=email,
                delivery_phone=phone,
            )
            for tt_id, qty in ticket_qty_by_type.items()
            for idx in range(qty)
        ]
    else:
        if len(assignments) != expected:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Provide exactly {expected} attendee assignment(s) "
                    "for group checkout (one per ticket)."
                ),
            )
        by_key: dict[tuple[uuid.UUID, int], AttendeeAssignmentIn] = {}
        for row in assignments:
            key = (row.ticket_type_id, row.unit_index)
            if key in by_key:
                raise HTTPException(
                    status_code=400,
                    detail="Duplicate attendee assignment for the same ticket unit",
                )
            if row.ticket_type_id not in ticket_qty_by_type:
                raise HTTPException(
                    status_code=400,
                    detail="Attendee assignment references a ticket type not in the cart",
                )
            if row.unit_index < 0 or row.unit_index >= ticket_qty_by_type[row.ticket_type_id]:
                raise HTTPException(
                    status_code=400,
                    detail="Attendee unit_index out of range for ticket quantity",
                )
            by_key[key] = row

        rows = []
        for tt_id, qty in ticket_qty_by_type.items():
            for idx in range(qty):
                row = by_key[(tt_id, idx)]
                name = validate_name(row.attendee_name, field="attendee name")
                email = validate_email(row.attendee_email, field="attendee email")
                phone = validate_phone(row.attendee_phone, field="attendee phone")
                delivery = (
                    validate_email(row.delivery_email, field="delivery email")
                    if row.delivery_email
                    else email
                )
                rows.append(
                    ResolvedAttendee(
                        ticket_type_id=tt_id,
                        unit_index=idx,
                        name=name,
                        email=email,
                        phone=phone,
                        delivery_email=delivery,
                        delivery_phone=validate_phone(
                            row.delivery_phone, field="delivery phone"
                        )
                        or phone,
                    )
                )

    gift_fields.update(
        {
            "is_gift": any(r.email != default_email for r in rows),
            "purchased_for_someone_else": any(r.email != default_email for r in rows),
            "send_ticket_to_recipient": bool(payload.send_ticket_to_recipient)
            or any(r.email != default_email for r in rows),
            "keep_buyer_copy": (
                True
                if payload.keep_buyer_copy is None
                else bool(payload.keep_buyer_copy)
            ),
            "gift_message": (payload.gift_message or "").strip() or None,
        }
    )
    if not gift_fields["send_ticket_to_recipient"] and not gift_fields["keep_buyer_copy"]:
        gift_fields["keep_buyer_copy"] = True
    return mode, rows, gift_fields


def persist_order_attendees(
    db: Session,
    *,
    order: Order,
    attendees: list[ResolvedAttendee],
    actor_user_id: uuid.UUID | None,
) -> None:
    for row in attendees:
        db.add(
            OrderAttendee(
                order_id=order.id,
                ticket_type_id=row.ticket_type_id,
                unit_index=row.unit_index,
                attendee_name=row.name,
                attendee_email=row.email,
                attendee_phone=row.phone,
                delivery_email=row.delivery_email,
                delivery_phone=row.delivery_phone,
                recipient_user_id=None,  # never claim by email alone
            )
        )
    if attendees:
        write_audit_log(
            db,
            action="checkout.attendee_assignment",
            actor_user_id=actor_user_id,
            resource_type="order",
            resource_id=str(order.id),
            details={
                "purchase_mode": order.purchase_mode,
                "attendee_count": len(attendees),
                "is_gift": order.is_gift,
                "send_ticket_to_recipient": order.send_ticket_to_recipient,
                "keep_buyer_copy": order.keep_buyer_copy,
            },
        )


def attendee_lookup(
    attendees: list[OrderAttendee],
    *,
    ticket_type_id: uuid.UUID,
    unit_index: int,
) -> OrderAttendee | None:
    for row in attendees:
        if row.ticket_type_id == ticket_type_id and row.unit_index == unit_index:
            return row
    return None
