"""Post-payment buyer account for logged-out merch checkout."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.register_username import (
    assert_username_available_for_registration,
    display_name_from_username,
    resolve_register_username,
)
from app.core.audit import write_audit_log
from app.core.security import hash_password
from app.merch.constants import ITEM_KIND_BUNDLE, ITEM_KIND_MERCH
from app.payments.attendees import normalize_email
from app.payments.models import Order
from app.tickets.models import Ticket
from app.users.constants import DEFAULT_REGISTER_ROLE
from app.users.models import User
from app.users.service import get_role_by_name, get_user_by_email


def order_has_merch_or_bundle(order: Order) -> bool:
    for item in order.items:
        kind = getattr(item, "item_kind", None) or "ticket"
        if kind in {ITEM_KIND_MERCH, ITEM_KIND_BUNDLE}:
            return True
        if getattr(item, "merch_variant_id", None) is not None:
            return True
    return False


def _unique_register_username(db: Session, *, full_name: str | None, email: str) -> str:
    seed = (full_name or "").strip() or email.split("@", 1)[0]
    base = resolve_register_username(username=None, full_name=seed)
    for attempt in range(12):
        candidate = base if attempt == 0 else f"{base[:28]}_{attempt}"
        try:
            assert_username_available_for_registration(db, candidate)
            return candidate
        except HTTPException:
            continue
    suffix = secrets.token_hex(2)
    return f"{base[:24]}_{suffix}"


def _create_user_from_checkout(
    db: Session,
    *,
    email: str,
    full_name: str | None,
) -> User:
    role = get_role_by_name(db, DEFAULT_REGISTER_ROLE)
    if role is None:
        raise RuntimeError("Default role is not seeded")

    username = _unique_register_username(db, full_name=full_name, email=email)
    display = (full_name or "").strip() or display_name_from_username(username)
    password = secrets.token_urlsafe(24)

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=display[:200],
        roles=[role],
    )
    db.add(user)
    db.flush()

    from app.passport.service import ensure_passport

    ensure_passport(db, user, preferred_username=username, display_name=display)

    write_audit_log(
        db,
        action="auth.register_from_checkout",
        actor_user_id=user.id,
        resource_type="user",
        resource_id=str(user.id),
        details={"email": user.email, "username": username},
    )
    return user


def _attach_paid_order_to_buyer(db: Session, *, order: Order, user: User) -> None:
    order.buyer_user_id = user.id
    order.is_guest_checkout = False
    order.claim_token_hash = None
    order.claim_token_expires_at = None

    now = datetime.now(UTC)
    tickets = list(db.scalars(select(Ticket).where(Ticket.order_id == order.id)))
    for ticket in tickets:
        ticket.claimed_by_user_id = user.id
        ticket.claimed_at = now
        if not ticket.holder_email:
            ticket.holder_email = user.email
        if not ticket.holder_name:
            ticket.holder_name = user.full_name

    write_audit_log(
        db,
        action="checkout.order_attached_to_buyer",
        actor_user_id=user.id,
        resource_type="order",
        resource_id=str(order.id),
        details={"reference": order.reference},
    )


def provision_guest_merch_buyer_if_needed(db: Session, order: Order) -> User | None:
    """
    After verified payment: logged-out checkout creates or attaches a buyer
    account and sends a set-password email for new users.
    """
    if order.buyer_user_id is not None:
        return None
    if not bool(getattr(order, "is_guest_checkout", False)):
        return None

    email = normalize_email(order.guest_buyer_email or order.buyer_email or "")
    if not email:
        return None

    user = get_user_by_email(db, email)
    created = False
    if user is None:
        user = _create_user_from_checkout(
            db,
            email=email,
            full_name=getattr(order, "guest_buyer_name", None),
        )
        created = True

    _attach_paid_order_to_buyer(db, order=order, user=user)

    if created:
        from app.auth.password_reset import queue_password_reset_email
        from app.email.service import send_template

        queue_password_reset_email(db, user)
        send_template(
            db,
            template="checkout_account_ready",
            to=user.email,
            recipient_user_id=user.id,
            context={
                "full_name": user.full_name,
                "order_reference": order.reference,
                "order_id": str(order.id),
            },
            dedupe_key=f"order:{order.id}:checkout_account_ready",
            deliver_now=True,
        )

    db.flush()
    return user


def assert_no_existing_account_for_email_checkout(
    db: Session,
    *,
    email: str,
) -> None:
    """Block logged-out checkout when the email already has an account."""
    matched = get_user_by_email(db, normalize_email(email))
    if matched is not None:
        raise HTTPException(
            status_code=409,
            detail="An account already uses this email. Sign in to complete checkout.",
        )


assert_no_existing_account_for_guest_merch = assert_no_existing_account_for_email_checkout
