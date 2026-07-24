"""Logged-out checkout validation, rate limits, and legacy claim tokens.

Checkout without a session requires buyer name + email. Existing accounts must
sign in. After verified payment, new buyers get an account + set-password email.
Legacy claim links remain for older ticket-only guest orders.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.security import hash_token
from app.payments.attendees import normalize_email, validate_email, validate_name, validate_phone
from app.payments.models import Order
from app.tickets.models import Ticket
from app.users.models import User
from app.users.restrictions import (
    assert_can_buy_merch,
    assert_can_buy_tickets,
    assert_can_checkout,
)
from app.users.service import get_user_by_email

CLAIM_TOKEN_TTL_HOURS = 72
GUEST_ORDERS_PER_EMAIL_PER_HOUR = 8
GUEST_ORDERS_PER_IP_PER_HOUR = 20


def resolve_matched_account(db: Session, email: str) -> User | None:
    """Lookup existing account by email — never auto-login or attach."""
    return get_user_by_email(db, normalize_email(email))


def assert_guest_email_allowed_for_checkout(
    db: Session,
    *,
    email: str,
    host_id: uuid.UUID,
    has_tickets: bool,
    has_merch: bool,
) -> User | None:
    """
    If guest email matches an existing account, enforce the same product
    restrictions / own-host block without logging them in or exposing data.
    Returns the matched user (for optional soft-link later) or None.
    """
    matched = resolve_matched_account(db, email)
    if matched is None:
        return None

    # Suspended / banned / inactive — block guest bypass
    from app.users.account_status_service import effective_account_status

    acct = effective_account_status(matched)
    if acct in {"suspended", "banned"} or not matched.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This email is linked to an account that can’t checkout. "
                "Log in for details or contact support."
            ),
        )

    try:
        assert_can_checkout(db, matched)
        if has_tickets:
            assert_can_buy_tickets(db, matched)
        if has_merch:
            assert_can_buy_merch(db, matched)
    except HTTPException as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=(
                "This email is linked to an account with purchase restrictions. "
                "Log in to continue or contact support."
            ),
        ) from exc

    from app.hosts.fan_self_abuse import is_user_owner_of_host, CHECKOUT_OWN_HOST_DETAIL

    if is_user_owner_of_host(db, user_id=matched.id, host_profile_id=host_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=CHECKOUT_OWN_HOST_DETAIL,
        )

    return matched


def assert_guest_checkout_rate_limit(
    db: Session,
    *,
    email: str,
    ip_address: str | None = None,
) -> None:
    since = datetime.now(UTC) - timedelta(hours=1)
    email_norm = normalize_email(email)
    email_count = db.scalar(
        select(func.count())
        .select_from(Order)
        .where(
            Order.guest_buyer_email == email_norm,
            Order.created_at >= since,
        )
    )
    if (email_count or 0) >= GUEST_ORDERS_PER_EMAIL_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many guest checkout attempts for this email. Try again later.",
        )
    if ip_address:
        # Soft IP limit via audit-less count of guest orders (email distinctness
        # already limits; IP is defense-in-depth using buyer_email fallback).
        ip_count = db.scalar(
            select(func.count())
            .select_from(Order)
            .where(
                Order.is_guest_checkout.is_(True),
                Order.created_at >= since,
            )
        )
        if (ip_count or 0) >= GUEST_ORDERS_PER_IP_PER_HOUR * 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many guest checkout attempts. Try again later.",
            )


def validate_guest_buyer_fields(
    *,
    name: str | None,
    email: str | None,
    phone: str | None,
) -> tuple[str, str, str | None]:
    if not name or not email:
        raise HTTPException(
            status_code=400,
            detail="Guest checkout requires full name and email",
        )
    return (
        validate_name(name, field="buyer name"),
        validate_email(email, field="buyer email"),
        validate_phone(phone, field="buyer phone"),
    )


def issue_claim_token(db: Session, order: Order) -> str:
    """Create a hashed claim token on a paid guest order. Returns raw token once."""
    raw = secrets.token_urlsafe(32)
    order.claim_token_hash = hash_token(raw)
    order.claim_token_expires_at = datetime.now(UTC) + timedelta(hours=CLAIM_TOKEN_TTL_HOURS)
    db.flush()
    return raw


def find_order_by_claim_token(db: Session, raw_token: str) -> Order | None:
    token_hash = hash_token(raw_token.strip())
    order = db.scalar(select(Order).where(Order.claim_token_hash == token_hash))
    if order is None:
        return None
    expires = order.claim_token_expires_at
    if expires is None:
        return None
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        return None
    return order


def claim_order_for_user(
    db: Session,
    *,
    order: Order,
    user: User,
    raw_token: str | None = None,
) -> Order:
    """Attach a paid guest order + tickets to a verified user account."""
    if order.claimed_at is not None and order.claimed_by_user_id == user.id:
        return order
    if order.claimed_at is not None:
        raise HTTPException(status_code=400, detail="This order was already claimed")
    if order.status != "paid":
        raise HTTPException(
            status_code=400,
            detail="Order must be paid before it can be claimed",
        )
    if not order.is_guest_checkout and order.buyer_user_id is not None:
        raise HTTPException(status_code=400, detail="This order is not a guest order")

    guest_email = normalize_email(order.guest_buyer_email or order.buyer_email or "")
    user_email = normalize_email(user.email or "")
    if not guest_email or guest_email != user_email:
        raise HTTPException(
            status_code=403,
            detail="Claim email must match the buyer email on this order",
        )

    from app.auth.verified_email import assert_verified_email

    assert_verified_email(user)

    if raw_token:
        found = find_order_by_claim_token(db, raw_token)
        if found is None or found.id != order.id:
            raise HTTPException(status_code=400, detail="Invalid or expired claim link")

    now = datetime.now(UTC)
    order.buyer_user_id = user.id
    order.claimed_by_user_id = user.id
    order.claimed_at = now
    order.claim_token_hash = None
    order.claim_token_expires_at = None

    tickets = list(db.scalars(select(Ticket).where(Ticket.order_id == order.id)))
    for ticket in tickets:
        ticket.buyer_user_id = user.id
        ticket.claimed_by_user_id = user.id
        ticket.claimed_at = now

    write_audit_log(
        db,
        action="checkout.guest_order_claimed",
        actor_user_id=user.id,
        resource_type="order",
        resource_id=str(order.id),
        details={"ticket_count": len(tickets)},
    )
    db.flush()
    return order


def request_guest_claim_link(
    db: Session,
    *,
    order_reference: str,
    email: str,
) -> dict[str, str]:
    """
    Re-send a guest claim magic link when reference + buyer email match.
    Raises HTTPException with clear detail when they do not correlate.
    """
    from app.email.service import enqueue_template
    from app.payments.service import (
        finalize_pending_order_via_paystack,
        get_order_by_reference,
        normalize_order_reference,
    )

    ref = normalize_order_reference(order_reference)
    if not ref or not ref.startswith("PDY-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter a valid order reference from your receipt (starts with PDY-).",
        )

    email_norm = normalize_email(email)
    if not email_norm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter the buyer email you used at checkout.",
        )

    order = get_order_by_reference(db, ref)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No order found with that reference. Copy it exactly from your receipt email or order page.",
        )

    buyer_email = normalize_email(order.guest_buyer_email or order.buyer_email or "")
    if not buyer_email or buyer_email != email_norm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That email doesn't match the buyer on this order. Use the same email you entered at checkout.",
        )

    if order.status == "pending":
        try:
            order = finalize_pending_order_via_paystack(
                db,
                order,
                actor_user_id=None,
                audit_action="payments.claim_start_confirmed",
            )
        except HTTPException as exc:
            if exc.status_code == status.HTTP_409:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Payment isn't confirmed for this order yet. "
                        "If you just paid, wait a minute and try again."
                    ),
                ) from exc
            raise

    if order.status != "paid":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This order isn't paid yet. Complete checkout or wait for payment confirmation, "
                "then try again."
            ),
        )

    if not order.is_guest_checkout and order.buyer_user_id is not None:
        return {
            "status": "on_account",
            "detail": (
                "This order is already on a Pàdéyá account. "
                "Sign in with the buyer email you used at checkout, then open Orders or My tickets."
            ),
            "order_id": order.id,
        }

    if order.claimed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="These tickets were already claimed. Sign in to the account that claimed them.",
        )

    raw = issue_claim_token(db, order)
    enqueue_template(
        db,
        template="ticket_claim_link",
        to=buyer_email,
        recipient_user_id=None,
        dedupe_key=f"order:{order.id}:claim_link:{raw[:8]}",
        context={
            "buyer_name": order.buyer_name,
            "event_title": "your event",
            "claim_token": raw,
            "order_reference": order.reference,
        },
    )
    db.commit()
    return {
        "status": "sent",
        "detail": "Claim link sent. Check your inbox (and spam folder) for the buyer email on this order.",
        "order_id": None,
    }
