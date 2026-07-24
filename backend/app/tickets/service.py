"""Ticket issuance, buyer queries, transfer, cancel, and rotating QR."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import write_audit_log
from app.email.service import enqueue_template, send_template
from app.core.security import verify_password
from app.events.models import Event, TicketType
from app.hosts.models import Host
from app.payments.models import Order
from app.tickets.advanced_models import (
    TableReservation,
    TicketGroup,
    TicketGroupMember,
    TicketTransfer,
)
from app.tickets.models import Ticket, TicketQrToken
from app.tickets.qr import (
    ROTATING_QR_TTL_SECONDS,
    create_signed_qr_payload,
    hash_device_fingerprint,
    hash_jti,
    new_public_ticket_code,
    new_qr_jti,
)
from app.users.models import User
from app.users.service import get_user_by_email, user_has_permission

GROUP_KINDS = {"group", "table"}

TRANSFER_SETUP_UNAVAILABLE = (
    "Ticket transfer is temporarily unavailable while the server database is being updated. "
    "Try again in a few minutes, or ask the site admin to run backend migrations."
)


def transfer_setup_http_error(exc: BaseException) -> HTTPException | None:
    """Map incomplete deploy / pending migrations to a clear client message."""
    parts = [str(exc).lower()]
    orig = getattr(exc, "orig", None)
    if orig is not None:
        parts.append(str(orig).lower())
    msg = " ".join(parts)

    if isinstance(exc, KeyError) and "template" in msg:
        return HTTPException(status_code=503, detail=TRANSFER_SETUP_UNAVAILABLE)

    from sqlalchemy.exc import SQLAlchemyError

    if isinstance(exc, SQLAlchemyError):
        markers = (
            "recipient_name",
            "claim_token_hash",
            "claim_token_expires",
            "undefined column",
            "does not exist",
            'null value in column "to_user_id"',
        )
        if any(m in msg for m in markers):
            return HTTPException(status_code=503, detail=TRANSFER_SETUP_UNAVAILABLE)

    return None

# Never expose street / lat-long / private join URLs on ticket list cards.
_HIDDEN_LOCATION_MODES = frozenset(
    {
        "hidden_until_payment",
        "hidden_until_24h_before",
        "hidden_until_manual_approval",
    }
)


def _safe_ticket_location_label(event: Event) -> str | None:
    """Public-safe location for buyer ticket dashboard (no street/private venue)."""
    vis = (event.location_visibility or "full_public").lower()
    if vis == "online_only":
        return event.public_location_label or "Online"
    if event.public_location_label:
        return event.public_location_label
    if vis in _HIDDEN_LOCATION_MODES:
        return event.city or "Location shared closer to the event"
    if vis == "area_only":
        return event.area or event.city
    return event.city or event.area


def _unique_public_code(db: Session) -> str:
    public_code = new_public_ticket_code()
    while db.scalar(select(Ticket.id).where(Ticket.public_code == public_code)):
        public_code = new_public_ticket_code()
    return public_code


def _issue_qr_for_ticket(
    db: Session,
    ticket: Ticket,
    *,
    rotating: bool = False,
) -> TicketQrToken:
    jti = new_qr_jti()
    version = 1
    if rotating:
        signed = create_signed_qr_payload(
            public_code=ticket.public_code,
            event_id=ticket.event_id,
            jti=jti,
            expires_seconds=ROTATING_QR_TTL_SECONDS,
            rotation_version=version,
        )
        expires_at = datetime.now(UTC) + timedelta(seconds=ROTATING_QR_TTL_SECONDS)
    else:
        signed = create_signed_qr_payload(
            public_code=ticket.public_code,
            event_id=ticket.event_id,
            jti=jti,
            rotation_version=version,
        )
        expires_at = datetime.now(UTC) + timedelta(days=365)
    qr = TicketQrToken(
        ticket_id=ticket.id,
        jti_hash=hash_jti(jti),
        signed_payload=signed,
        expires_at=expires_at,
        rotation_version=version,
        is_rotating=rotating,
    )
    db.add(qr)
    return qr


def _create_ticket_row(
    db: Session,
    *,
    order: Order,
    item,
    attendee_index: int | None = None,
    table_label: str | None = None,
    seat_label: str | None = None,
    holder_name: str | None = None,
    holder_email: str | None = None,
    holder_phone: str | None = None,
    is_gift: bool = False,
    recipient_user_id: uuid.UUID | None = None,
) -> Ticket:
    public_code = _unique_public_code(db)
    ticket = Ticket(
        public_code=public_code,
        order_id=order.id,
        order_item_id=item.id,
        event_id=order.event_id,
        ticket_type_id=item.ticket_type_id,
        buyer_user_id=order.buyer_user_id,
        status="active",
        ticket_type_name=item.ticket_type_name,
        holder_name=holder_name or order.buyer_name,
        holder_email=holder_email or order.buyer_email,
        holder_phone=holder_phone,
        is_gift=is_gift,
        recipient_user_id=recipient_user_id,
        attendee_index=attendee_index,
        table_label=table_label,
        seat_label=seat_label,
        qr_mode="static",
    )
    db.add(ticket)
    db.flush()
    _issue_qr_for_ticket(db, ticket, rotating=False)
    return ticket


def issue_tickets_for_paid_order(db: Session, order: Order) -> list[Ticket]:
    """
    Issue tickets exactly once for a paid order.
    Group/table types with seats_per_unit > 1 create multiple attendee entries.
    Holder identity comes from order_attendees when present (gift / group).
    """
    existing = list(db.scalars(select(Ticket).where(Ticket.order_id == order.id)))
    if existing:
        return existing

    from app.payments.attendees import attendee_lookup
    from app.payments.models import OrderAttendee

    attendees = list(
        db.scalars(
            select(OrderAttendee).where(OrderAttendee.order_id == order.id)
        )
    )
    # Track how many units of each ticket type we've issued (for attendee map)
    unit_counters: dict[uuid.UUID, int] = {}
    is_gift_order = bool(getattr(order, "is_gift", False) or getattr(order, "purchased_for_someone_else", False))

    def _holder_for(ticket_type_id: uuid.UUID) -> dict:
        idx = unit_counters.get(ticket_type_id, 0)
        unit_counters[ticket_type_id] = idx + 1
        row = attendee_lookup(
            attendees, ticket_type_id=ticket_type_id, unit_index=idx
        )
        if row is None:
            return {
                "holder_name": order.buyer_name,
                "holder_email": order.buyer_email,
                "holder_phone": None,
                "is_gift": is_gift_order,
                "recipient_user_id": None,
            }
        return {
            "holder_name": row.attendee_name,
            "holder_email": (
                (row.delivery_email or row.attendee_email or "").strip()
                or row.attendee_email
            ),
            "holder_phone": row.attendee_phone,
            "is_gift": is_gift_order
            or (
                row.attendee_email.lower() != (order.buyer_email or "").lower()
            ),
            # Never claim account by email alone
            "recipient_user_id": None,
        }

    created: list[Ticket] = []
    for item in order.items:
        kind_line = getattr(item, "item_kind", None) or "ticket"
        if kind_line == "merch" or item.ticket_type_id is None:
            continue
        ticket_type = db.get(TicketType, item.ticket_type_id)
        seats = 1
        if ticket_type is not None:
            seats = max(1, int(getattr(ticket_type, "seats_per_unit", 1) or 1))
        kind = ticket_type.type if ticket_type else "regular"

        for unit_index in range(item.quantity):
            holder = _holder_for(item.ticket_type_id)
            if kind in GROUP_KINDS and seats > 1:
                group = TicketGroup(
                    order_id=order.id,
                    order_item_id=item.id,
                    event_id=order.event_id,
                    ticket_type_id=item.ticket_type_id,
                    buyer_user_id=order.buyer_user_id,
                    group_kind=kind,
                    expected_size=seats,
                    label=f"{item.ticket_type_name} #{unit_index + 1}",
                    status="active",
                )
                db.add(group)
                db.flush()

                table_label = None
                if kind == "table":
                    table_label = f"T-{str(group.id)[:8].upper()}"
                    reservation = TableReservation(
                        event_id=order.event_id,
                        ticket_type_id=item.ticket_type_id,
                        group_id=group.id,
                        table_label=table_label,
                        capacity=seats,
                        status="reserved",
                        assignment_note="Auto-created from table ticket purchase",
                    )
                    db.add(reservation)

                primary: Ticket | None = None
                for seat_idx in range(seats):
                    seat_label = f"S{seat_idx + 1}" if kind == "table" else None
                    ticket = _create_ticket_row(
                        db,
                        order=order,
                        item=item,
                        attendee_index=seat_idx,
                        table_label=table_label,
                        seat_label=seat_label,
                        **holder,
                    )
                    db.add(
                        TicketGroupMember(
                            group_id=group.id,
                            ticket_id=ticket.id,
                            attendee_index=seat_idx,
                        )
                    )
                    if primary is None:
                        primary = ticket
                    created.append(ticket)

                if kind == "table" and primary is not None:
                    reservation = db.scalar(
                        select(TableReservation).where(TableReservation.group_id == group.id)
                    )
                    if reservation is not None:
                        reservation.primary_ticket_id = primary.id
            else:
                ticket = _create_ticket_row(db, order=order, item=item, **holder)
                created.append(ticket)

    return created


def send_ticket_email(
    db: Session,
    order: Order,
    tickets: list[Ticket],
    *,
    resend_tag: str | None = None,
) -> None:
    """Enqueue ticket confirmation after verified payment (outbox — not sync SMTP).

    Delivery rules:
    - Buyer always gets an order receipt when keep_buyer_copy (default) or self-purchase.
    - Recipient / holder emails for gift, group, or “buy for someone else”.
    - Never issues QR here — QR already exists only because finalize already ran.
    """
    from app.hosts.models import Host
    from app.users.models import User

    event = db.get(Event, order.event_id)
    title = event.title if event else "your event"
    codes = ", ".join(t.public_code for t in tickets[:8])
    if len(tickets) > 8:
        codes += ", …"

    keep_buyer = bool(getattr(order, "keep_buyer_copy", True))
    send_recipient = bool(getattr(order, "send_ticket_to_recipient", False))
    is_gift = bool(
        getattr(order, "is_gift", False)
        or getattr(order, "purchased_for_someone_else", False)
    )
    gift_message = getattr(order, "gift_message", None)
    recipient_email = getattr(order, "recipient_email", None)
    dedupe_suffix = f":resend:{resend_tag}" if resend_tag else ""
    force_send = bool(resend_tag)

    # Collect unique delivery emails from ticket holders when group gift
    holder_emails = {
        (t.holder_email or "").strip().lower()
        for t in tickets
        if t.holder_email
    }
    buyer_email_norm = (order.buyer_email or "").strip().lower()

    if keep_buyer or not is_gift:
        claim_token = None
        claim_path = None
        if bool(getattr(order, "is_guest_checkout", False)) and order.buyer_user_id is None:
            from app.payments.guest import issue_claim_token

            claim_token = issue_claim_token(db, order)
            claim_path = f"/checkout/claim?token={claim_token}&order={order.reference}"

        enqueue_template(
            db,
            template="ticket_confirmed",
            to=order.buyer_email,
            recipient_user_id=order.buyer_user_id,
            dedupe_key=f"order:{order.id}:ticket_confirmed{dedupe_suffix}",
            force=force_send,
            context={
                "buyer_name": order.buyer_name,
                "event_title": title,
                "ticket_codes": codes,
                "ticket_count": len(tickets),
                "is_gift": is_gift,
                "gift_message": gift_message,
                "is_guest": bool(getattr(order, "is_guest_checkout", False)),
                "claim_path": claim_path,
                "claim_token": claim_token,
                "order_id": str(order.id),
            },
        )
        if claim_token:
            enqueue_template(
                db,
                template="ticket_claim_link",
                to=order.buyer_email,
                recipient_user_id=None,
                dedupe_key=f"order:{order.id}:claim_link{dedupe_suffix}",
                force=force_send,
                context={
                    "buyer_name": order.buyer_name,
                    "event_title": title,
                    "claim_token": claim_token,
                    "claim_path": claim_path,
                    "order_reference": order.reference,
                },
            )
        from app.notifications.service import notify_user

        if order.buyer_user_id is not None:
            notify_user(
                db,
                user_id=order.buyer_user_id,
                kind="ticket.confirmed",
                title="Your ticket is ready.",
                body=f"Your tickets for {title} are confirmed on Pàdéyá.",
                link_path="/dashboard/tickets",
                dedupe_key=f"order:{order.id}:ticket.confirmed",
            )
            from app.notifications.triggers import notify_ticket_qr_ready

            notify_ticket_qr_ready(
                db,
                user_id=order.buyer_user_id,
                event_title=title,
                order_id=order.id,
            )

    purchase_mode = getattr(order, "purchase_mode", None) or "self"
    notify_recipients = (
        send_recipient
        or is_gift
        or purchase_mode in {"other", "group"}
    )
    recipient_targets: set[str] = set()
    if notify_recipients:
        if recipient_email:
            recipient_targets.add(recipient_email.strip().lower())
        for email in holder_emails:
            if email and email != buyer_email_norm:
                recipient_targets.add(email)

    for email in recipient_targets:
        if not email:
            continue
        if email == buyer_email_norm and keep_buyer:
            continue
        enqueue_template(
            db,
            template="ticket_gift_received",
            to=email,
            recipient_user_id=None,
            dedupe_key=f"order:{order.id}:gift:{email}{dedupe_suffix}",
            force=force_send,
            context={
                "recipient_name": getattr(order, "recipient_name", None)
                or "there",
                "buyer_name": order.buyer_name,
                "event_title": title,
                "ticket_codes": codes,
                "ticket_count": len(tickets),
                "gift_message": gift_message,
                "order_id": str(order.id),
            },
        )

    if event is not None:
        host = db.get(Host, event.host_id)
        host_user = db.get(User, host.user_id) if host else None
        if host_user and host_user.email:
            enqueue_template(
                db,
                template="host_ticket_sale",
                to=host_user.email,
                recipient_user_id=host_user.id,
                dedupe_key=f"order:{order.id}:host_ticket_sale",
                context={
                    "event_title": title,
                    "ticket_count": len(tickets),
                },
            )
            from app.notifications.service import notify_user

            notify_user(
                db,
                user_id=host_user.id,
                kind="host.ticket_sale",
                title="New ticket sale on Pàdéyá",
                body=f"{len(tickets)} ticket(s) sold for {title}.",
                link_path="/host/analytics",
                dedupe_key=f"order:{order.id}:host.ticket_sale",
            )
        from app.email.admin_triggers import admin_notify_ticket_sale_paid

        host_name = host.display_name if host else "Host"
        admin_notify_ticket_sale_paid(
            db,
            order_id=order.id,
            order_reference=order.reference,
            event_title=title,
            host_name=host_name,
            buyer_name=order.buyer_name or "Buyer",
            ticket_count=len(tickets),
            amount=order.total_amount,
            currency=order.currency or "NGN",
        )


def resend_order_ticket_emails(
    db: Session,
    *,
    user: User,
    order_id: uuid.UUID,
) -> dict[str, str]:
    """Buyer-initiated resend of ticket emails (e.g. gift recipient did not receive)."""
    from app.tickets.models import Ticket

    from app.payments.service import require_buyer_order

    order = require_buyer_order(db, user, order_id)
    if order.status != "paid":
        raise HTTPException(
            status_code=400,
            detail="Ticket emails send only after payment is confirmed.",
        )
    tickets = list(db.scalars(select(Ticket).where(Ticket.order_id == order.id)))
    if not tickets:
        raise HTTPException(status_code=400, detail="No tickets found for this order.")
    tag = secrets.token_hex(4)
    send_ticket_email(db, order, tickets, resend_tag=tag)
    write_audit_log(
        db,
        action="tickets.emails_resent",
        actor_user_id=user.id,
        resource_type="order",
        resource_id=str(order.id),
        details={"resend_tag": tag, "ticket_count": len(tickets)},
    )
    db.commit()
    return {
        "status": "ok",
        "detail": "Ticket emails queued again for the buyer and any recipients on this order.",
    }


def list_buyer_tickets(db: Session, user: User) -> list[Ticket]:
    return list(
        db.scalars(
            select(Ticket)
            .where(
                (Ticket.buyer_user_id == user.id)
                | (Ticket.claimed_by_user_id == user.id)
            )
            .options(selectinload(Ticket.qr_token))
            .order_by(Ticket.created_at.desc())
        )
    )


def get_buyer_ticket(db: Session, user: User, ticket_id: uuid.UUID) -> Ticket:
    ticket = db.scalar(
        select(Ticket)
        .where(
            Ticket.id == ticket_id,
            (Ticket.buyer_user_id == user.id)
            | (Ticket.claimed_by_user_id == user.id),
        )
        .options(selectinload(Ticket.qr_token))
    )
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


def _maybe_rotate_qr(db: Session, ticket: Ticket) -> None:
    token = ticket.qr_token
    if token is None or token.revoked_at is not None:
        return
    if not token.is_rotating and ticket.qr_mode != "rotating":
        return

    now = datetime.now(UTC)
    expires = token.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    # Rotate when expired or within 15s of expiry
    if expires > now + timedelta(seconds=15):
        return

    jti = new_qr_jti()
    version = int(token.rotation_version or 1) + 1
    signed = create_signed_qr_payload(
        public_code=ticket.public_code,
        event_id=ticket.event_id,
        jti=jti,
        expires_seconds=ROTATING_QR_TTL_SECONDS,
        rotation_version=version,
    )
    token.jti_hash = hash_jti(jti)
    token.signed_payload = signed
    token.expires_at = now + timedelta(seconds=ROTATING_QR_TTL_SECONDS)
    token.rotation_version = version
    token.is_rotating = True
    ticket.qr_mode = "rotating"
    db.flush()


def serialize_ticket(db: Session, ticket: Ticket, *, include_qr: bool = False) -> dict:
    event = db.get(Event, ticket.event_id)
    host: Host | None = db.get(Host, event.host_id) if event is not None else None
    if include_qr:
        _maybe_rotate_qr(db, ticket)
        db.commit()
        db.refresh(ticket)
        if ticket.qr_token:
            db.refresh(ticket.qr_token)

    payload = {
        "id": ticket.id,
        "public_code": ticket.public_code,
        "event_id": ticket.event_id,
        "order_id": ticket.order_id,
        "ticket_type_id": ticket.ticket_type_id,
        "ticket_type_name": ticket.ticket_type_name,
        "status": ticket.status,
        "holder_name": ticket.holder_name,
        "holder_email": ticket.holder_email,
        "holder_phone": getattr(ticket, "holder_phone", None),
        "is_gift": bool(getattr(ticket, "is_gift", False)),
        "checked_in_at": ticket.checked_in_at,
        "created_at": ticket.created_at,
        "event_title": event.title if event else None,
        "event_slug": event.slug if event else None,
        "event_cover_url": (
            (event.banner_url or event.mobile_banner_url or event.social_share_image_url)
            if event
            else None
        ),
        "event_starts_at": event.start_datetime if event else None,
        "event_ends_at": event.end_datetime if event else None,
        "event_status": event.status if event else None,
        "host_id": host.id if host else None,
        "host_name": host.display_name if host else None,
        "host_username": host.slug if host else None,
        "location_label": _safe_ticket_location_label(event) if event else None,
        "qr_payload": None,
        "qr_mode": ticket.qr_mode,
        "device_bound": bool(ticket.device_binding_hash),
        "seat_label": ticket.seat_label,
        "table_label": ticket.table_label,
        "attendee_index": ticket.attendee_index,
        "qr_expires_at": None,
        "qr_rotation_version": None,
    }
    if include_qr and ticket.qr_token and ticket.qr_token.revoked_at is None:
        payload["qr_payload"] = ticket.qr_token.signed_payload
        payload["qr_expires_at"] = ticket.qr_token.expires_at
        payload["qr_rotation_version"] = ticket.qr_token.rotation_version

    from app.merch.fulfillment import list_fulfillments_for_order

    from app.merch.fulfillment import buyer_display_status
    from app.payments.models import Order as OrderModel

    linked = list_fulfillments_for_order(db, order_id=ticket.order_id)
    order_row = db.get(OrderModel, ticket.order_id)
    order_status = order_row.status if order_row else None
    payload["linked_merch"] = [
        {
            "id": f.id,
            "order_item_id": f.order_item_id,
            "product_name": f.product_name_snapshot,
            "variant_label": f.variant_label_snapshot,
            "quantity": f.quantity,
            "status": f.status,
            "display_status": buyer_display_status(
                fulfillment_status=f.status, order_status=order_status
            ),
            "pickup_code": f.pickup_code,
            "pickup_instructions": f.pickup_instructions_snapshot,
        }
        for f in linked
    ]
    return payload


def _reissue_ticket_qr(db: Session, ticket: Ticket, old_qr: TicketQrToken | None) -> None:
    if old_qr is not None:
        jti = new_qr_jti()
        rotating = ticket.qr_mode == "rotating" or old_qr.is_rotating
        version = int(old_qr.rotation_version or 1) + 1
        if rotating:
            signed = create_signed_qr_payload(
                public_code=ticket.public_code,
                event_id=ticket.event_id,
                jti=jti,
                expires_seconds=ROTATING_QR_TTL_SECONDS,
                rotation_version=version,
            )
            expires_at = datetime.now(UTC) + timedelta(seconds=ROTATING_QR_TTL_SECONDS)
        else:
            signed = create_signed_qr_payload(
                public_code=ticket.public_code,
                event_id=ticket.event_id,
                jti=jti,
                rotation_version=version,
            )
            expires_at = datetime.now(UTC) + timedelta(days=365)
        old_qr.jti_hash = hash_jti(jti)
        old_qr.signed_payload = signed
        old_qr.expires_at = expires_at
        old_qr.rotation_version = version
        old_qr.is_rotating = rotating
        old_qr.revoked_at = None
    else:
        _issue_qr_for_ticket(db, ticket, rotating=ticket.qr_mode == "rotating")


def transfer_ticket(
    db: Session,
    *,
    user: User,
    ticket_id: uuid.UUID,
    to_email: str,
    to_name: str,
    note: str | None = None,
) -> tuple[TicketTransfer, str | None]:
    from app.payments.attendees import normalize_email, validate_email, validate_name
    from app.users.restrictions import assert_can_transfer_tickets

    assert_can_transfer_tickets(db, user)

    ticket = get_buyer_ticket(db, user, ticket_id)
    if ticket.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Only active tickets can be transferred (status={ticket.status})",
        )
    if ticket.checked_in_at is not None:
        raise HTTPException(status_code=400, detail="Checked-in tickets cannot be transferred")

    recipient_name = validate_name(to_name, field="recipient name")
    to_email_norm = validate_email(to_email, field="recipient email")

    pending = db.scalar(
        select(TicketTransfer).where(
            TicketTransfer.ticket_id == ticket.id,
            TicketTransfer.status == "pending",
        )
    )
    if pending is not None:
        raise HTTPException(
            status_code=400,
            detail="This ticket already has a pending transfer waiting to be claimed.",
        )

    recipient = get_user_by_email(db, to_email_norm)
    if recipient is not None and recipient.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot transfer a ticket to yourself")

    event = db.get(Event, ticket.event_id)
    event_title = event.title if event else "your event"
    from_user_id = ticket.buyer_user_id
    from_email = ticket.holder_email or user.email or ""
    old_qr = ticket.qr_token
    claim_path_for_response: str | None = None

    if recipient is not None:
        ticket.buyer_user_id = recipient.id
        ticket.holder_name = recipient_name
        ticket.holder_email = recipient.email
        if old_qr is not None:
            old_qr.revoked_at = datetime.now(UTC)
        _reissue_ticket_qr(db, ticket, old_qr)

        transfer = TicketTransfer(
            ticket_id=ticket.id,
            event_id=ticket.event_id,
            from_user_id=from_user_id or user.id,
            to_user_id=recipient.id,
            from_email=from_email,
            to_email=recipient.email,
            recipient_name=recipient_name,
            note=note,
            status="completed",
        )
        db.add(transfer)
        db.flush()
        _notify_recipient_transfer_completed(
            db,
            transfer=transfer,
            ticket=ticket,
            recipient=recipient,
            event_title=event_title,
            sender_name=user.full_name or "Someone",
        )
        _notify_sender_transfer_accepted(
            db,
            transfer=transfer,
            ticket=ticket,
            sender=user,
            event_title=event_title,
            recipient_name=recipient_name,
        )
    else:
        if old_qr is not None:
            old_qr.revoked_at = datetime.now(UTC)
        ticket.buyer_user_id = None
        ticket.holder_name = recipient_name
        ticket.holder_email = to_email_norm
        ticket.is_gift = True

        transfer = TicketTransfer(
            ticket_id=ticket.id,
            event_id=ticket.event_id,
            from_user_id=from_user_id or user.id,
            to_user_id=None,
            from_email=from_email,
            to_email=to_email_norm,
            recipient_name=recipient_name,
            note=note,
            status="pending",
        )
        db.add(transfer)
        db.flush()

        from app.tickets.transfer_claim import issue_transfer_claim_token

        raw_token = issue_transfer_claim_token(db, transfer)
        claim_path = _transfer_claim_path(raw_token, to_email_norm)
        claim_path_for_response = claim_path
        send_template(
            db,
            template="ticket_transfer_invite",
            to=to_email_norm,
            recipient_user_id=None,
            dedupe_key=f"ticket:{ticket.id}:transfer_invite:{transfer.id}",
            deliver_now=True,
            context={
                "recipient_name": recipient_name,
                "buyer_name": user.full_name or "Someone",
                "event_title": event_title,
                "ticket_code": ticket.public_code,
                "claim_token": raw_token,
                "claim_path": claim_path,
                "cta_path": claim_path,
                "recipient_email": to_email_norm,
            },
        )

    write_audit_log(
        db,
        action="tickets.transfer",
        actor_user_id=user.id,
        resource_type="ticket",
        resource_id=str(ticket.id),
        details={
            "from_user_id": str(from_user_id),
            "to_email": to_email_norm,
            "to_user_id": str(recipient.id) if recipient else None,
            "status": "completed" if recipient else "pending",
            "event_id": str(ticket.event_id),
        },
    )
    db.commit()
    db.refresh(transfer)
    return transfer, claim_path_for_response


def get_transfer_claim_context(db: Session, *, raw_token: str) -> dict:
    from app.tickets.transfer_claim import find_pending_transfer_by_claim_token

    transfer = find_pending_transfer_by_claim_token(db, raw_token)
    if transfer is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired transfer claim link",
        )
    event = db.get(Event, transfer.event_id)
    return {
        "recipient_email": transfer.to_email,
        "recipient_name": transfer.recipient_name,
        "event_title": event.title if event else None,
        "status": transfer.status,
    }


def claim_ticket_transfer(
    db: Session,
    *,
    user: User,
    raw_token: str,
) -> Ticket:
    from app.auth.verified_email import assert_verified_email
    from app.payments.attendees import normalize_email
    from app.tickets.transfer_claim import find_pending_transfer_by_claim_token

    transfer = find_pending_transfer_by_claim_token(db, raw_token)
    if transfer is None:
        raise HTTPException(status_code=400, detail="Invalid or expired transfer claim link")

    assert_verified_email(user)
    expected = normalize_email(transfer.to_email)
    actual = normalize_email(user.email or "")
    if not expected or expected != actual:
        raise HTTPException(
            status_code=403,
            detail="Log in with the same email the ticket was transferred to.",
        )

    ticket = _load_ticket_for_transfer_claim(db, transfer.ticket_id)
    return _finish_transfer_claim(db, transfer=transfer, ticket=ticket, user=user)


def _notify_sender_transfer_accepted(
    db: Session,
    *,
    transfer: TicketTransfer,
    ticket: Ticket,
    sender: User | None,
    event_title: str,
    recipient_name: str,
) -> None:
    from app.notifications.service import notify_user

    sender_user = sender or db.get(User, transfer.from_user_id)
    sender_name = (
        (sender_user.full_name if sender_user and sender_user.full_name else None)
        or transfer.from_email
        or "there"
    )
    sender_email = (sender_user.email if sender_user and sender_user.email else None) or (
        transfer.from_email or ""
    ).strip()
    if sender_email:
        send_template(
            db,
            template="ticket_transfer_accepted",
            to=sender_email,
            recipient_user_id=sender_user.id if sender_user else transfer.from_user_id,
            dedupe_key=f"ticket:{ticket.id}:transfer_accepted:{transfer.id}",
            deliver_now=True,
            context={
                "sender_name": sender_name,
                "recipient_name": recipient_name,
                "event_title": event_title,
                "ticket_code": ticket.public_code,
            },
        )
    if sender_user is not None:
        notify_user(
            db,
            user_id=sender_user.id,
            kind="ticket.transfer_accepted",
            title=f"Transfer accepted — {event_title}",
            body=f"{recipient_name} claimed the ticket you transferred.",
            link_path="/dashboard/tickets",
            dedupe_key=f"ticket:{ticket.id}:transfer_accepted_notify:{transfer.id}",
        )


def _notify_recipient_transfer_completed(
    db: Session,
    *,
    transfer: TicketTransfer,
    ticket: Ticket,
    recipient: User,
    event_title: str,
    sender_name: str,
) -> None:
    from app.notifications.service import notify_user

    recipient_name = transfer.recipient_name or recipient.full_name or "there"
    send_template(
        db,
        template="ticket_transfer_received",
        to=recipient.email,
        recipient_user_id=recipient.id,
        dedupe_key=f"ticket:{ticket.id}:transfer_received:{transfer.id}",
        deliver_now=True,
        context={
            "recipient_name": recipient_name,
            "buyer_name": sender_name,
            "event_title": event_title,
            "ticket_code": ticket.public_code,
        },
    )
    notify_user(
        db,
        user_id=recipient.id,
        kind="ticket.transferred",
        title=f"Ticket for {event_title}",
        body=f"{sender_name} transferred a ticket to you on Pàdéyá.",
        link_path="/dashboard/tickets",
        dedupe_key=f"ticket:{ticket.id}:transfer_notify:{transfer.id}",
    )


def _load_ticket_for_transfer_claim(db: Session, ticket_id: uuid.UUID) -> Ticket:
    ticket = db.scalar(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(selectinload(Ticket.qr_token))
        .with_for_update()
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


def _finish_transfer_claim(
    db: Session,
    *,
    transfer: TicketTransfer,
    ticket: Ticket,
    user: User,
) -> Ticket:
    if transfer.status != "pending":
        raise HTTPException(status_code=400, detail="This transfer was already completed")

    old_qr = ticket.qr_token
    ticket.buyer_user_id = user.id
    ticket.holder_name = transfer.recipient_name or user.full_name or "Guest"
    ticket.holder_email = user.email or transfer.to_email
    _reissue_ticket_qr(db, ticket, old_qr)

    transfer.status = "completed"
    transfer.to_user_id = user.id
    transfer.claim_token_hash = None
    transfer.claim_token_expires_at = None

    event = db.get(Event, ticket.event_id)
    event_title = event.title if event else "your event"
    sender = db.get(User, transfer.from_user_id)
    sender_name = (sender.full_name if sender and sender.full_name else None) or (
        transfer.from_email or "Someone"
    )
    recipient_name = transfer.recipient_name or user.full_name or user.email or "Guest"

    _notify_recipient_transfer_completed(
        db,
        transfer=transfer,
        ticket=ticket,
        recipient=user,
        event_title=event_title,
        sender_name=sender_name,
    )
    _notify_sender_transfer_accepted(
        db,
        transfer=transfer,
        ticket=ticket,
        sender=sender,
        event_title=event_title,
        recipient_name=recipient_name,
    )

    write_audit_log(
        db,
        action="tickets.transfer_claimed",
        actor_user_id=user.id,
        resource_type="ticket",
        resource_id=str(ticket.id),
        details={"transfer_id": str(transfer.id), "event_id": str(ticket.event_id)},
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def claim_pending_ticket_transfer_for_user(
    db: Session,
    *,
    user: User,
    transfer_id: uuid.UUID,
) -> Ticket:
    from app.auth.verified_email import assert_verified_email
    from app.payments.attendees import normalize_email

    assert_verified_email(user)
    transfer = db.get(TicketTransfer, transfer_id)
    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if transfer.status != "pending":
        raise HTTPException(status_code=400, detail="This transfer was already completed")

    expected = normalize_email(transfer.to_email)
    actual = normalize_email(user.email or "")
    if not expected or expected != actual:
        raise HTTPException(
            status_code=403,
            detail="This transfer was sent to a different email address.",
        )

    ticket = _load_ticket_for_transfer_claim(db, transfer.ticket_id)
    return _finish_transfer_claim(db, transfer=transfer, ticket=ticket, user=user)


def _restore_ticket_after_pending_transfer_cancel(
    db: Session,
    *,
    transfer: TicketTransfer,
    ticket: Ticket,
) -> None:
    sender = db.get(User, transfer.from_user_id)
    old_qr = ticket.qr_token
    ticket.buyer_user_id = transfer.from_user_id
    ticket.holder_name = (
        (sender.full_name if sender and sender.full_name else None)
        or transfer.from_email
    )
    ticket.holder_email = sender.email if sender and sender.email else transfer.from_email
    ticket.is_gift = False
    if old_qr is not None:
        old_qr.revoked_at = datetime.now(UTC)
    _reissue_ticket_qr(db, ticket, old_qr)
    transfer.claim_token_hash = None
    transfer.claim_token_expires_at = None


def _serialize_transfer_activity(db: Session, user: User, row: TicketTransfer) -> dict:
    from app.payments.attendees import normalize_email

    event = db.get(Event, row.event_id)
    ticket = db.get(Ticket, row.ticket_id)
    email_norm = normalize_email(user.email or "")
    to_norm = normalize_email(row.to_email)
    role = "sent" if row.from_user_id == user.id else "received"
    can_revoke = row.status == "pending" and row.from_user_id == user.id
    can_decline = (
        row.status == "pending"
        and row.from_user_id != user.id
        and email_norm
        and to_norm == email_norm
    )
    can_resend_invite = row.status == "pending" and row.from_user_id == user.id
    base = {
        "id": row.id,
        "ticket_id": row.ticket_id,
        "event_id": row.event_id,
        "from_user_id": row.from_user_id,
        "to_user_id": row.to_user_id,
        "from_email": row.from_email,
        "to_email": row.to_email,
        "recipient_name": row.recipient_name,
        "note": row.note,
        "status": row.status,
        "created_at": row.created_at,
        "claim_path": None,
        "event_title": event.title if event else None,
        "ticket_public_code": ticket.public_code if ticket else None,
        "role": role,
        "can_revoke": can_revoke,
        "can_decline": can_decline,
        "can_resend_invite": can_resend_invite,
    }
    return base


def list_my_ticket_transfers(
    db: Session,
    *,
    user: User,
    limit: int = 50,
) -> list[dict]:
    from app.payments.attendees import normalize_email

    email_norm = normalize_email(user.email or "")
    filters = [
        TicketTransfer.from_user_id == user.id,
        TicketTransfer.to_user_id == user.id,
    ]
    if email_norm:
        filters.append(TicketTransfer.to_email == email_norm)

    rows = list(
        db.scalars(
            select(TicketTransfer)
            .where(or_(*filters))
            .order_by(TicketTransfer.created_at.desc())
            .limit(min(limit, 100))
        )
    )
    return [_serialize_transfer_activity(db, user, row) for row in rows]


def revoke_pending_ticket_transfer(
    db: Session,
    *,
    user: User,
    transfer_id: uuid.UUID,
) -> TicketTransfer:
    transfer = db.get(TicketTransfer, transfer_id)
    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if transfer.from_user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the sender can revoke this transfer")
    if transfer.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Only pending transfers can be revoked (status={transfer.status})",
        )

    ticket = db.scalar(
        select(Ticket)
        .where(Ticket.id == transfer.ticket_id)
        .options(selectinload(Ticket.qr_token))
        .with_for_update()
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    transfer.status = "revoked"
    _restore_ticket_after_pending_transfer_cancel(db, transfer=transfer, ticket=ticket)

    write_audit_log(
        db,
        action="tickets.transfer_revoked",
        actor_user_id=user.id,
        resource_type="ticket_transfer",
        resource_id=str(transfer.id),
        details={"ticket_id": str(ticket.id), "event_id": str(transfer.event_id)},
    )
    db.commit()
    db.refresh(transfer)
    return transfer


def decline_pending_ticket_transfer(
    db: Session,
    *,
    user: User,
    transfer_id: uuid.UUID,
) -> TicketTransfer:
    from app.payments.attendees import normalize_email

    transfer = db.get(TicketTransfer, transfer_id)
    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if transfer.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Only pending transfers can be declined (status={transfer.status})",
        )
    email_norm = normalize_email(user.email or "")
    to_norm = normalize_email(transfer.to_email)
    if not email_norm or to_norm != email_norm:
        raise HTTPException(status_code=403, detail="This transfer was not sent to your email")

    ticket = db.scalar(
        select(Ticket)
        .where(Ticket.id == transfer.ticket_id)
        .options(selectinload(Ticket.qr_token))
        .with_for_update()
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    transfer.status = "declined"
    _restore_ticket_after_pending_transfer_cancel(db, transfer=transfer, ticket=ticket)

    write_audit_log(
        db,
        action="tickets.transfer_declined",
        actor_user_id=user.id,
        resource_type="ticket_transfer",
        resource_id=str(transfer.id),
        details={"ticket_id": str(ticket.id), "event_id": str(transfer.event_id)},
    )
    db.commit()
    db.refresh(transfer)
    return transfer


def _transfer_claim_path(raw_token: str, recipient_email: str) -> str:
    email_norm = (recipient_email or "").strip().lower()
    base = f"/tickets/claim?token={raw_token}"
    if email_norm and "@" in email_norm:
        return f"{base}&email={quote(email_norm, safe='')}"
    return base


def _issue_pending_transfer_claim_path(db: Session, transfer: TicketTransfer) -> str:
    from app.tickets.transfer_claim import issue_transfer_claim_token

    raw_token = issue_transfer_claim_token(db, transfer)
    return _transfer_claim_path(raw_token, transfer.to_email)


def refresh_pending_transfer_claim_link(
    db: Session,
    *,
    user: User,
    transfer_id: uuid.UUID,
) -> tuple[TicketTransfer, str]:
    transfer = db.get(TicketTransfer, transfer_id)
    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if transfer.from_user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the sender can copy this claim link")
    if transfer.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Claim links are only available for pending transfers (status={transfer.status})",
        )

    claim_path = _issue_pending_transfer_claim_path(db, transfer)
    write_audit_log(
        db,
        action="tickets.transfer_claim_link_refreshed",
        actor_user_id=user.id,
        resource_type="ticket_transfer",
        resource_id=str(transfer.id),
        details={"ticket_id": str(transfer.ticket_id)},
    )
    db.commit()
    db.refresh(transfer)
    return transfer, claim_path


def resend_pending_ticket_transfer_invite(
    db: Session,
    *,
    user: User,
    transfer_id: uuid.UUID,
) -> tuple[TicketTransfer, str]:
    transfer = db.get(TicketTransfer, transfer_id)
    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if transfer.from_user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the sender can resend this invite")
    if transfer.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Invite emails can only be resent for pending transfers (status={transfer.status})",
        )

    ticket = db.scalar(
        select(Ticket)
        .where(Ticket.id == transfer.ticket_id)
        .options(selectinload(Ticket.qr_token))
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    event = db.get(Event, ticket.event_id)
    event_title = event.title if event else "your event"
    sender = db.get(User, transfer.from_user_id)

    claim_path = _issue_pending_transfer_claim_path(db, transfer)
    raw_token = claim_path.split("token=", 1)[-1]
    resend_tag = secrets.token_hex(4)
    send_template(
        db,
        template="ticket_transfer_invite",
        to=transfer.to_email,
        recipient_user_id=None,
        dedupe_key=f"ticket:{ticket.id}:transfer_invite:{transfer.id}:resend:{resend_tag}",
        deliver_now=True,
        force=True,
        context={
            "recipient_name": transfer.recipient_name or "there",
            "buyer_name": (sender.full_name if sender and sender.full_name else None)
            or "Someone",
            "event_title": event_title,
            "ticket_code": ticket.public_code,
            "claim_token": raw_token,
            "claim_path": claim_path,
            "cta_path": claim_path,
            "recipient_email": transfer.to_email,
        },
    )

    write_audit_log(
        db,
        action="tickets.transfer_invite_resent",
        actor_user_id=user.id,
        resource_type="ticket_transfer",
        resource_id=str(transfer.id),
        details={"ticket_id": str(ticket.id), "to_email": transfer.to_email},
    )
    db.commit()
    db.refresh(transfer)
    return transfer, claim_path


def cancel_ticket(
    db: Session,
    *,
    user: User,
    ticket_id: uuid.UUID,
    password: str,
    reason: str | None = None,
) -> Ticket:
    ticket = db.scalar(
        select(Ticket).where(Ticket.id == ticket_id).options(selectinload(Ticket.qr_token))
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    is_owner = ticket.buyer_user_id == user.id
    is_admin = user_has_permission(user, "admin.full_access")
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to cancel this ticket")

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=403,
            detail="Incorrect password. Ticket was not cancelled.",
        )

    if ticket.status in {"cancelled", "refunded", "transferred", "invalid"}:
        raise HTTPException(status_code=400, detail=f"Ticket already {ticket.status}")
    if ticket.status == "checked_in" and not is_admin:
        raise HTTPException(status_code=400, detail="Checked-in tickets require admin cancel")

    ticket.status = "cancelled"
    if ticket.qr_token is not None:
        ticket.qr_token.revoked_at = datetime.now(UTC)

    write_audit_log(
        db,
        action="tickets.cancel",
        actor_user_id=user.id,
        resource_type="ticket",
        resource_id=str(ticket.id),
        details={"reason": reason, "event_id": str(ticket.event_id)},
    )

    # Cancelled tickets reverse Ambassadors commission for the order (idempotent).
    if ticket.order_id is not None:
        from app.ambassadors.payment import reverse_conversions_for_order
        from app.promos.commission import reverse_ambassador_sale_for_order

        cancel_reason = (reason or "Ticket cancelled").strip()[:500]
        reverse_ambassador_sale_for_order(
            db,
            order_id=ticket.order_id,
            reason=cancel_reason,
            actor_user_id=user.id,
        )
        reverse_conversions_for_order(
            db,
            order_id=ticket.order_id,
            reason=cancel_reason,
            actor_user_id=user.id,
        )

    db.commit()
    db.refresh(ticket)
    return ticket


def regenerate_ticket_qr(
    db: Session,
    *,
    user: User,
    ticket_id: uuid.UUID,
) -> Ticket:
    """Revoke current QR and issue a new signed payload (buyer or admin)."""
    ticket = db.scalar(
        select(Ticket).where(Ticket.id == ticket_id).options(selectinload(Ticket.qr_token))
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    is_owner = ticket.buyer_user_id == user.id
    is_admin = user_has_permission(user, "admin.full_access")
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Not allowed to regenerate QR")
    if ticket.status not in {"active", "checked_in"}:
        raise HTTPException(status_code=400, detail="QR can only be regenerated for active tickets")

    old_qr = ticket.qr_token
    rotating = ticket.qr_mode == "rotating"
    if old_qr is not None:
        old_qr.revoked_at = datetime.now(UTC)
        jti = new_qr_jti()
        version = int(old_qr.rotation_version or 1) + 1
        if rotating:
            signed = create_signed_qr_payload(
                public_code=ticket.public_code,
                event_id=ticket.event_id,
                jti=jti,
                expires_seconds=ROTATING_QR_TTL_SECONDS,
                rotation_version=version,
            )
            expires_at = datetime.now(UTC) + timedelta(seconds=ROTATING_QR_TTL_SECONDS)
        else:
            signed = create_signed_qr_payload(
                public_code=ticket.public_code,
                event_id=ticket.event_id,
                jti=jti,
                rotation_version=version,
            )
            expires_at = datetime.now(UTC) + timedelta(days=365)
        old_qr.jti_hash = hash_jti(jti)
        old_qr.signed_payload = signed
        old_qr.expires_at = expires_at
        old_qr.rotation_version = version
        old_qr.is_rotating = rotating
        old_qr.revoked_at = None
    else:
        _issue_qr_for_ticket(db, ticket, rotating=rotating)

    write_audit_log(
        db,
        action="tickets.qr_regenerate",
        actor_user_id=user.id,
        resource_type="ticket",
        resource_id=str(ticket.id),
    )
    if ticket.buyer_user_id is not None:
        from app.events.models import Event as EventModel
        from app.notifications.triggers import notify_ticket_qr_ready

        db.flush()
        db.refresh(ticket, attribute_names=["qr_token"])
        event_row = db.get(EventModel, ticket.event_id)
        qr_version = (
            int(ticket.qr_token.rotation_version)
            if ticket.qr_token is not None
            else 0
        )
        notify_ticket_qr_ready(
            db,
            buyer_user_id=ticket.buyer_user_id,
            event_title=event_row.title if event_row else "your event",
            dedupe_key=f"ticket:{ticket.id}:qr_regen:{qr_version}",
            send_email=True,
        )
    db.commit()
    db.refresh(ticket)
    return ticket


def set_ticket_qr_mode(
    db: Session,
    *,
    user: User,
    ticket_id: uuid.UUID,
    qr_mode: str,
) -> Ticket:
    if qr_mode not in {"static", "rotating"}:
        raise HTTPException(status_code=400, detail="qr_mode must be static or rotating")
    ticket = get_buyer_ticket(db, user, ticket_id)
    if ticket.status != "active":
        raise HTTPException(status_code=400, detail="Only active tickets can change QR mode")
    ticket.qr_mode = qr_mode
    if ticket.qr_token is not None:
        ticket.qr_token.is_rotating = qr_mode == "rotating"
        if qr_mode == "rotating":
            # Force immediate short-lived token
            ticket.qr_token.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            _maybe_rotate_qr(db, ticket)
    write_audit_log(
        db,
        action="tickets.qr_mode",
        actor_user_id=user.id,
        resource_type="ticket",
        resource_id=str(ticket.id),
        details={"qr_mode": qr_mode},
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def bind_ticket_device(
    db: Session,
    *,
    user: User,
    ticket_id: uuid.UUID,
    device_fingerprint: str,
) -> Ticket:
    """Placeholder device binding — stores hash only; check-in does not enforce yet."""
    ticket = get_buyer_ticket(db, user, ticket_id)
    if ticket.status != "active":
        raise HTTPException(status_code=400, detail="Only active tickets can be device-bound")
    if not device_fingerprint.strip():
        raise HTTPException(status_code=400, detail="device_fingerprint required")
    ticket.device_binding_hash = hash_device_fingerprint(device_fingerprint)
    ticket.device_bound_at = datetime.now(UTC)
    write_audit_log(
        db,
        action="tickets.device_bind",
        actor_user_id=user.id,
        resource_type="ticket",
        resource_id=str(ticket.id),
        details={"bound": True},
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def _ensure_static_qr_for_pdf(db: Session, ticket: Ticket) -> str:
    """Return a long-lived static QR payload suitable for printable PDFs.

    Rotating short-lived tokens are converted to static so the PDF remains valid
    offline. Updates the ticket QR row and sets qr_mode to static.
    """
    token = ticket.qr_token
    if token is None or token.revoked_at is not None:
        raise HTTPException(
            status_code=400,
            detail="Ticket has no active QR to include in the PDF",
        )

    now = datetime.now(UTC)
    expires = token.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)

    needs_static = (
        ticket.qr_mode == "rotating"
        or token.is_rotating
        or expires <= now + timedelta(days=1)
    )
    if not needs_static and token.signed_payload:
        return token.signed_payload

    jti = new_qr_jti()
    version = int(token.rotation_version or 1) + 1
    signed = create_signed_qr_payload(
        public_code=ticket.public_code,
        event_id=ticket.event_id,
        jti=jti,
        rotation_version=version,
    )
    token.jti_hash = hash_jti(jti)
    token.signed_payload = signed
    token.expires_at = now + timedelta(days=365)
    token.rotation_version = version
    token.is_rotating = False
    token.revoked_at = None
    ticket.qr_mode = "static"
    db.flush()
    return signed


def build_ticket_pdf_bytes(db: Session, ticket: Ticket) -> tuple[bytes, str]:
    """Build a ticket PDF without auth checks (webhook / email / public download)."""
    from app.tickets.pdf import pdf_filename_for_code, render_ticket_pdf

    if ticket.status not in {
        "active",
        "checked_in",
        "cancelled",
        "refunded",
        "pending",
    }:
        raise HTTPException(
            status_code=400,
            detail=f"PDF download is not available for this ticket (status={ticket.status})",
        )

    if ticket.status == "active":
        qr_payload = _ensure_static_qr_for_pdf(db, ticket)
    elif ticket.status == "checked_in":
        token = ticket.qr_token
        qr_payload = (
            token.signed_payload
            if token is not None
            and token.revoked_at is None
            and token.signed_payload
            else ""
        )
    else:
        qr_payload = ""

    event = db.get(Event, ticket.event_id)
    host: Host | None = db.get(Host, event.host_id) if event is not None else None

    pdf_bytes = render_ticket_pdf(
        event_title=event.title if event else "Event",
        ticket_type_name=ticket.ticket_type_name,
        public_code=ticket.public_code,
        holder_name=ticket.holder_name,
        holder_email=ticket.holder_email,
        qr_payload=qr_payload,
        starts_at=event.start_datetime if event else None,
        location_label=_safe_ticket_location_label(event) if event else None,
        host_name=host.display_name if host else None,
        status=ticket.status,
    )
    return pdf_bytes, pdf_filename_for_code(ticket.public_code)


def build_buyer_ticket_pdf(
    db: Session,
    *,
    user: User,
    ticket_id: uuid.UUID,
) -> tuple[bytes, str]:
    """Build a downloadable PDF pass for the ticket owner. Returns (bytes, filename)."""
    ticket = get_buyer_ticket(db, user, ticket_id)
    pdf_bytes, filename = build_ticket_pdf_bytes(db, ticket)
    write_audit_log(
        db,
        action="tickets.pdf_download",
        actor_user_id=user.id,
        resource_type="ticket",
        resource_id=str(ticket.id),
        details={"event_id": str(ticket.event_id), "public_code": ticket.public_code},
    )
    db.commit()
    return pdf_bytes, filename


def list_ticket_transfers_for_event(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
) -> list[TicketTransfer]:
    from app.checkins.permissions import can_scan_event

    if not (
        can_scan_event(db, user, event_id)
        or user_has_permission(user, "admin.full_access")
        or user_has_permission(user, "tickets.manage")
    ):
        raise HTTPException(status_code=403, detail="Not authorized to view transfers")
    return list(
        db.scalars(
            select(TicketTransfer)
            .where(TicketTransfer.event_id == event_id)
            .order_by(TicketTransfer.created_at.desc())
        )
    )


def list_ticket_transfers_for_ticket(
    db: Session,
    *,
    user: User,
    ticket_id: uuid.UUID,
) -> list[TicketTransfer]:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    from app.checkins.permissions import can_scan_event

    holds_ticket = ticket.buyer_user_id == user.id or ticket.claimed_by_user_id == user.id
    sent_transfer = db.scalar(
        select(TicketTransfer.id)
        .where(
            TicketTransfer.ticket_id == ticket_id,
            TicketTransfer.from_user_id == user.id,
        )
        .limit(1)
    )
    is_staff = can_scan_event(db, user, ticket.event_id)
    is_admin = user_has_permission(user, "admin.full_access")
    if not (holds_ticket or sent_transfer is not None or is_staff or is_admin):
        raise HTTPException(status_code=403, detail="Not authorized")
    return list(
        db.scalars(
            select(TicketTransfer)
            .where(TicketTransfer.ticket_id == ticket_id)
            .order_by(TicketTransfer.created_at.desc())
        )
    )


def admin_list_tickets(
    db: Session,
    *,
    user: User,
    limit: int = 100,
) -> list[Ticket]:
    if not (
        user_has_permission(user, "admin.full_access")
        or user_has_permission(user, "payments.view")
    ):
        raise HTTPException(status_code=403, detail="Not authorized")
    return list(
        db.scalars(
            select(Ticket)
            .options(selectinload(Ticket.qr_token))
            .order_by(Ticket.created_at.desc())
            .limit(min(limit, 200))
        )
    )


def admin_list_transfers(db: Session, *, user: User, limit: int = 100) -> list[TicketTransfer]:
    if not (
        user_has_permission(user, "admin.full_access")
        or user_has_permission(user, "payments.view")
    ):
        raise HTTPException(status_code=403, detail="Not authorized")
    return list(
        db.scalars(
            select(TicketTransfer).order_by(TicketTransfer.created_at.desc()).limit(min(limit, 200))
        )
    )
