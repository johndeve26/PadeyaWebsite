"""Admin event buyer/attendee list + privacy-safe CSV/JSON export.

Export modes:
- public_summary — public profile + ticket status + safe codes
- operations (default) — public + operational; private contact only when permitted
- finance — financial depth; requires admin.finance.export_event_sales + reason

Never exported: QR payloads/jti, Paystack/provider refs/payloads, passwords,
hidden venue/private address, device_binding, Fan Connect graph, messages, vault secrets.
"""

from __future__ import annotations

import csv
import io
import json
import re
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.checkins.models import CheckIn
from app.core.audit import AuditLog, write_audit_log
from app.events.models import Event
from app.finance.models import RefundRequest
from app.hosts.models import Host, HostProfile
from app.passport.models import FanPassport
from app.passport.privacy import is_publicly_reachable
from app.payments.models import Order, Payment
from app.promos.ambassador_domain import AmbassadorParticipant
from app.tickets.advanced_models import TicketTransfer
from app.tickets.models import Ticket
from app.users.models import User
from app.users.service import user_has_permission

ExportMode = Literal["public_summary", "operations", "finance"]

PERM_VIEW = "admin.events.view"
PERM_EXPORT = "admin.events.export_buyers"
PERM_PRIVATE_CONTACT = "admin.events.export_private_contact"
PERM_FINANCE = "admin.finance.export_event_sales"

AUDIT_EXPORTED = "admin_event_buyers_exported"
AUDIT_PRIVATE_CONTACT = "admin_event_buyers_private_contact_exported"
AUDIT_FINANCE = "admin_event_buyers_finance_exported"
# Legacy action still listed in history queries for older rows.
EXPORT_AUDIT_ACTION = "tickets.admin.event_buyers_export"
_AUDIT_ACTIONS = (
    AUDIT_EXPORTED,
    AUDIT_PRIVATE_CONTACT,
    AUDIT_FINANCE,
    EXPORT_AUDIT_ACTION,
)

EXPORT_MAX_ROWS = 10_000
LIST_MAX_LIMIT = 500
DEFAULT_MODE: ExportMode = "operations"

_FORBIDDEN_SUBSTRINGS = (
    "qr",
    "payload",
    "jti",
    "payment_reference",
    "authorization",
    "paystack",
    "address",
    "venue",
    "lat",
    "lng",
    "device_binding",
    "order_reference",
    "password",
    "raw_response",
)

# Stable column order — never rely on dict key iteration.
_HEADERS_PUBLIC = [
    "event_id",
    "event_title",
    "event_slug",
    "event_date",
    "host_name",
    "host_id",
    "buyer_user_id",
    "display_name",
    "username",
    "public_profile_url",
    "avatar_url",
    "public_bio",
    "public_city",
    "public_country",
    "public_social_links",
    "public_passport_url",
    "safe_order_code",
    "safe_ticket_code",
    "ticket_type",
    "purchase_status",
    "checked_in",
]

_HEADERS_OPS = [
    "quantity",
    "purchase_date",
    "payment_status",
    "refund_status",
    "checked_in_at",
    "check_in_method",
    "ticket_source",
    "ambassador_code",
    "promo_code_used",
    "referral_source",
    "campaign_id",
    "attendee_name",
    "attendee_public_username",
    "seat_label",
    "table_label",
    "notes",
]

_HEADERS_PRIVATE_CONTACT = [
    "buyer_email",
    "buyer_phone",
    "holder_email",
]

_HEADERS_FINANCE = [
    "amount_paid",
    "currency",
    "discount_amount",
    "order_id",
    "ticket_id",
]

_CSV_HEADERS_ALL = (
    _HEADERS_PUBLIC + _HEADERS_OPS + _HEADERS_PRIVATE_CONTACT + _HEADERS_FINANCE
)
# Back-compat alias for tests / callers that still import _CSV_HEADERS.
_CSV_HEADERS = list(_CSV_HEADERS_ALL)

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _assert_safe_headers(headers: list[str]) -> None:
    for header in headers:
        lowered = header.lower()
        for bad in _FORBIDDEN_SUBSTRINGS:
            if bad in lowered:
                raise ValueError(f"Unsafe CSV column blocked: {header}")


def sanitize_csv_cell(value: Any) -> str:
    """Neutralize CSV/formula injection; empty for None."""
    if value is None:
        return ""
    text = str(value)
    if text and text[0] in _FORMULA_PREFIXES:
        return f"'{text}"
    return text


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _sanitize_slug(slug: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9-]+", "-", (slug or "").strip().lower())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or "event"


def require_admin_buyer_access(user: User) -> None:
    # Hosts may hold payments.view — do not reuse that here.
    if not (
        user_has_permission(user, PERM_VIEW)
        and user_has_permission(user, PERM_EXPORT)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access event buyers",
        )


def _parse_mode(mode: str | None) -> ExportMode:
    value = (mode or DEFAULT_MODE).strip().lower()
    if value in {"public_summary", "operations", "finance"}:
        return value  # type: ignore[return-value]
    raise HTTPException(
        status_code=400,
        detail="Unsupported export mode. Use public_summary, operations, or finance.",
    )


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"true", "1", "yes"}


def _parse_dt(value: str | None, *, end: bool = False) -> datetime | None:
    if not value or not value.strip():
        return None
    raw = value.strip()
    try:
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            dt = datetime.fromisoformat(raw).replace(tzinfo=UTC)
            if end:
                return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            return dt
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid datetime filter: {raw}",
        ) from exc


def _load_event(db: Session, event_id: uuid.UUID) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def _host_context(
    db: Session, event: Event
) -> tuple[str, str | None, str | None]:
    host = db.get(Host, event.host_id)
    host_name = host.display_name if host else ""
    host_id = str(event.host_id)
    profile = db.scalar(
        select(HostProfile).where(HostProfile.host_id == event.host_id)
    )
    host_profile_id = str(profile.id) if profile else None
    return host_name, host_id, host_profile_id


def _load_context(
    db: Session, tickets: list[Ticket]
) -> tuple[
    dict[uuid.UUID, User],
    dict[uuid.UUID, FanPassport],
    dict[uuid.UUID, str],
    dict[uuid.UUID, str],
    dict[uuid.UUID, str],
    set[uuid.UUID],
    dict[uuid.UUID, str],
]:
    buyer_ids = {t.buyer_user_id for t in tickets}
    order_ids = {t.order_id for t in tickets}
    ticket_ids = {t.id for t in tickets}
    users_by_id: dict[uuid.UUID, User] = {}
    passports_by_user: dict[uuid.UUID, FanPassport] = {}
    payment_status_by_order: dict[uuid.UUID, str] = {}
    refund_status_by_order: dict[uuid.UUID, str] = {}
    check_in_method_by_ticket: dict[uuid.UUID, str] = {}
    transferred_ticket_ids: set[uuid.UUID] = set()
    campaign_id_by_order: dict[uuid.UUID, str] = {}

    if buyer_ids:
        for row in db.scalars(select(User).where(User.id.in_(buyer_ids))).all():
            users_by_id[row.id] = row
        for row in db.scalars(
            select(FanPassport).where(FanPassport.user_id.in_(buyer_ids))
        ).all():
            passports_by_user[row.user_id] = row

    if order_ids:
        # Latest payment status per order (status only — never provider refs).
        pay_rows = db.execute(
            select(Payment.order_id, Payment.status, Payment.created_at)
            .where(Payment.order_id.in_(order_ids))
            .order_by(Payment.created_at.desc())
        ).all()
        for order_id, pay_status, _created in pay_rows:
            if order_id not in payment_status_by_order:
                payment_status_by_order[order_id] = pay_status or ""

        refund_rows = db.execute(
            select(RefundRequest.order_id, RefundRequest.status, RefundRequest.created_at)
            .where(RefundRequest.order_id.in_(order_ids))
            .order_by(RefundRequest.created_at.desc())
        ).all()
        for order_id, ref_status, _created in refund_rows:
            if order_id not in refund_status_by_order:
                refund_status_by_order[order_id] = ref_status or ""

        # Safe campaign id via ambassador participant FK (never payment refs).
        participant_ids = {
            o.ambassador_participant_id
            for o in db.scalars(
                select(Order).where(Order.id.in_(order_ids))
            ).all()
            if o.ambassador_participant_id
        }
        if participant_ids:
            part_rows = db.execute(
                select(AmbassadorParticipant.id, AmbassadorParticipant.campaign_id).where(
                    AmbassadorParticipant.id.in_(participant_ids)
                )
            ).all()
            campaign_by_participant = {
                pid: str(cid) for pid, cid in part_rows if cid is not None
            }
            for order in db.scalars(select(Order).where(Order.id.in_(order_ids))).all():
                if order.ambassador_participant_id:
                    cid = campaign_by_participant.get(order.ambassador_participant_id)
                    if cid:
                        campaign_id_by_order[order.id] = cid

    if ticket_ids:
        ci_rows = db.execute(
            select(CheckIn.ticket_id, CheckIn.method, CheckIn.created_at)
            .where(
                CheckIn.ticket_id.in_(ticket_ids),
                CheckIn.outcome.in_(("success", "checked_in", "ok")),
            )
            .order_by(CheckIn.created_at.desc())
        ).all()
        for ticket_id, method, _created in ci_rows:
            if ticket_id and ticket_id not in check_in_method_by_ticket:
                check_in_method_by_ticket[ticket_id] = method or ""

        transferred_ticket_ids = set(
            db.scalars(
                select(TicketTransfer.ticket_id).where(
                    TicketTransfer.ticket_id.in_(ticket_ids),
                    TicketTransfer.status == "completed",
                )
            ).all()
        )

    return (
        users_by_id,
        passports_by_user,
        payment_status_by_order,
        refund_status_by_order,
        check_in_method_by_ticket,
        transferred_ticket_ids,
        campaign_id_by_order,
    )


def _public_profile_fields(passport: FanPassport | None) -> dict[str, Any]:
    """Visibility-gated public passport fields only."""
    empty = {
        "display_name": None,
        "username": None,
        "public_profile_url": None,
        "avatar_url": None,
        "public_bio": None,
        "public_city": None,
        "public_country": None,
        "public_social_links": None,
        "public_passport_url": None,
    }
    if passport is None:
        return empty
    # Ops may still use display/username below; public_* gated here.
    username = passport.username
    reachable = is_publicly_reachable(passport.visibility) and passport.admin_hidden_at is None
    out = {
        "display_name": passport.display_name or None,
        "username": username,
        "public_profile_url": f"/f/{username}" if reachable and username else None,
        "avatar_url": passport.avatar_url if reachable else None,
        "public_bio": passport.bio if reachable else None,
        # FanPassport has no home city/country/social fields yet — leave empty.
        "public_city": None,
        "public_country": None,
        "public_social_links": None,
        "public_passport_url": f"/f/{username}" if reachable and username else None,
    }
    return out


def _headers_for(
    *,
    mode: ExportMode,
    include_private_contact: bool,
) -> list[str]:
    headers = list(_HEADERS_PUBLIC)
    if mode in {"operations", "finance"}:
        headers.extend(_HEADERS_OPS)
    if include_private_contact:
        headers.extend(_HEADERS_PRIVATE_CONTACT)
    if mode == "finance":
        headers.extend(_HEADERS_FINANCE)
    elif mode == "operations":
        # Ops-safe finance lite (status/promo already in ops; amount for table).
        headers.extend(["amount_paid", "currency", "discount_amount"])
    _assert_safe_headers(headers)
    return headers


def _serialize_row(
    *,
    event: Event,
    host_name: str,
    host_id: str,
    ticket: Ticket,
    order: Order | None,
    buyer: User | None,
    passport: FanPassport | None,
    payment_status: str | None,
    refund_status: str | None,
    check_in_method: str | None,
    transferred: bool,
    campaign_id: str | None,
    mode: ExportMode,
    include_private_contact: bool,
) -> dict[str, Any]:
    checked_in = bool(ticket.checked_in_at) or (ticket.status or "").lower() == "checked_in"
    public = _public_profile_fields(passport)
    # public_summary: only publicly reachable profile names/handles
    if mode == "public_summary":
        if not (
            passport
            and is_publicly_reachable(passport.visibility)
            and passport.admin_hidden_at is None
        ):
            public["display_name"] = None
            public["username"] = None

    safe_order = str(ticket.order_id)[:8] if ticket.order_id else ""
    row: dict[str, Any] = {
        "event_id": str(event.id),
        "event_title": event.title or "",
        "event_slug": event.slug or "",
        "event_date": _iso(event.start_datetime),
        "host_name": host_name,
        "host_id": host_id,
        "buyer_user_id": str(ticket.buyer_user_id),
        "display_name": public["display_name"],
        "username": public["username"],
        "public_profile_url": public["public_profile_url"],
        "avatar_url": public["avatar_url"],
        "public_bio": public["public_bio"],
        "public_city": public["public_city"],
        "public_country": public["public_country"],
        "public_social_links": public["public_social_links"],
        "public_passport_url": public["public_passport_url"],
        "safe_order_code": safe_order,
        "safe_ticket_code": ticket.public_code or "",
        "ticket_type": ticket.ticket_type_name or "",
        "purchase_status": ticket.status or "",
        "checked_in": checked_in,
        # Back-compat aliases used by existing FE table
        "ticket_id": str(ticket.id),
        "public_code": ticket.public_code or "",
        "ticket_type_name": ticket.ticket_type_name or "",
        "ticket_status": ticket.status or "",
        "is_checked_in": checked_in,
        "order_status": order.status if order else None,
        "passport_username": public["username"],
        "passport_display_name": public["display_name"],
        "promo_code": (order.promo_code_snapshot if order else None) or None,
    }

    if mode in {"operations", "finance"}:
        row.update(
            {
                "quantity": 1,
                "purchase_date": _iso(order.paid_at or order.created_at)
                if order
                else _iso(ticket.created_at),
                "payment_status": payment_status
                or (order.status if order else None),
                "refund_status": refund_status or None,
                "checked_in_at": _iso(ticket.checked_in_at),
                "check_in_method": check_in_method or None,
                "ticket_source": "transfer" if transferred else "purchase",
                "ambassador_code": (order.referral_code if order else None) or None,
                "promo_code_used": (order.promo_code_snapshot if order else None)
                or None,
                "referral_source": (order.referral_attribution_source if order else None)
                or None,
                "campaign_id": campaign_id,
                "attendee_name": ticket.holder_name or "",
                "attendee_public_username": public["username"],
                "seat_label": ticket.seat_label,
                "table_label": ticket.table_label,
                # No admin-safe free-text notes on tickets today.
                "notes": None,
                "ticket_created_at": _iso(ticket.created_at),
                "attendee_index": ticket.attendee_index,
                "order_paid_at": _iso(order.paid_at) if order else None,
                "holder_name": ticket.holder_name or "",
            }
        )
        row["amount_paid"] = str(order.total_amount) if order else None
        row["currency"] = order.currency if order else None
        row["discount_amount"] = str(order.discount_amount) if order else None
        row["order_total_amount"] = row["amount_paid"]
        row["order_currency"] = row["currency"]

    if include_private_contact:
        row["buyer_email"] = buyer.email if buyer else None
        # User model has no phone field yet.
        row["buyer_phone"] = None
        row["holder_email"] = ticket.holder_email or ""
        row["buyer_account_email"] = row["buyer_email"]
        row["buyer_full_name"] = buyer.full_name if buyer else None
    else:
        row["buyer_email"] = None
        row["buyer_phone"] = None
        row["holder_email"] = None
        row["buyer_account_email"] = None
        row["buyer_full_name"] = (
            public["display_name"] if mode != "public_summary" else public["display_name"]
        )

    if mode == "finance":
        row["order_id"] = str(ticket.order_id)
        row["ticket_id"] = str(ticket.id)
    else:
        # Keep ids for list FE but omit from public_summary CSV headers.
        row["order_id"] = str(ticket.order_id)

    return row


def _filters_dict(
    *,
    q: str | None,
    ticket_status: str | None,
    purchase_status: str | None,
    payment_status: str | None,
    refund_status: str | None,
    checked_in: str | None,
    ticket_type: str | None,
    purchased_from: str | None,
    purchased_to: str | None,
    promo_code: str | None,
    ambassador_code: str | None,
) -> dict[str, str | None]:
    return {
        "q": q,
        "ticket_status": ticket_status or purchase_status,
        "purchase_status": purchase_status or ticket_status,
        "payment_status": payment_status,
        "refund_status": refund_status,
        "checked_in": checked_in,
        "ticket_type": ticket_type,
        "purchased_from": purchased_from,
        "purchased_to": purchased_to,
        "promo_code": promo_code,
        "ambassador_code": ambassador_code,
    }


def _query_tickets(
    db: Session,
    *,
    event_id: uuid.UUID,
    q: str | None = None,
    ticket_status: str | None = None,
    purchase_status: str | None = None,
    payment_status: str | None = None,
    refund_status: str | None = None,
    checked_in: str | None = None,
    ticket_type: str | None = None,
    purchased_from: str | None = None,
    purchased_to: str | None = None,
    promo_code: str | None = None,
    ambassador_code: str | None = None,
) -> list[Ticket]:
    status_filter = (purchase_status or ticket_status or "").strip() or None
    stmt = (
        select(Ticket)
        .join(Order, Order.id == Ticket.order_id)
        .where(Ticket.event_id == event_id)
        .options(selectinload(Ticket.order))
        .order_by(Ticket.created_at.asc())
    )
    if status_filter:
        stmt = stmt.where(Ticket.status == status_filter)
    if ticket_type:
        stmt = stmt.where(Ticket.ticket_type_name.ilike(ticket_type.strip()))
    if checked_in in {"true", "1", "yes"}:
        stmt = stmt.where(
            or_(
                Ticket.checked_in_at.is_not(None),
                Ticket.status == "checked_in",
            )
        )
    elif checked_in in {"false", "0", "no"}:
        stmt = stmt.where(
            Ticket.checked_in_at.is_(None),
            Ticket.status != "checked_in",
        )

    from_dt = _parse_dt(purchased_from)
    to_dt = _parse_dt(purchased_to, end=True)
    if from_dt is not None:
        stmt = stmt.where(
            func.coalesce(Order.paid_at, Order.created_at) >= from_dt
        )
    if to_dt is not None:
        stmt = stmt.where(
            func.coalesce(Order.paid_at, Order.created_at) <= to_dt
        )
    if promo_code and promo_code.strip():
        stmt = stmt.where(Order.promo_code_snapshot.ilike(promo_code.strip()))
    if ambassador_code and ambassador_code.strip():
        stmt = stmt.where(Order.referral_code.ilike(ambassador_code.strip()))

    if payment_status and payment_status.strip():
        pay_exists = (
            select(Payment.id)
            .where(
                Payment.order_id == Order.id,
                Payment.status == payment_status.strip(),
            )
            .exists()
        )
        stmt = stmt.where(pay_exists)

    if refund_status and refund_status.strip():
        ref_exists = (
            select(RefundRequest.id)
            .where(
                RefundRequest.order_id == Order.id,
                RefundRequest.status == refund_status.strip(),
            )
            .exists()
        )
        stmt = stmt.where(ref_exists)

    if q and q.strip():
        term = f"%{q.strip()}%"
        passport_match = (
            select(FanPassport.user_id)
            .where(
                FanPassport.user_id == Ticket.buyer_user_id,
                or_(
                    FanPassport.username.ilike(term),
                    FanPassport.display_name.ilike(term),
                ),
            )
            .exists()
        )
        stmt = stmt.where(
            or_(
                Ticket.holder_name.ilike(term),
                Ticket.public_code.ilike(term),
                Ticket.ticket_type_name.ilike(term),
                passport_match,
            )
        )
    return list(db.scalars(stmt).all())


def _resolve_export_gates(
    user: User,
    *,
    mode: ExportMode,
    include_private_contact: bool,
    reason: str | None,
) -> tuple[bool, str]:
    """Returns (include_private_contact_effective, audit_action)."""
    if mode == "finance":
        if not user_has_permission(user, PERM_FINANCE):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing permission admin.finance.export_event_sales",
            )
        if not (reason or "").strip():
            raise HTTPException(
                status_code=400,
                detail="reason is required for finance exports",
            )
        want_private = include_private_contact
        if want_private and not user_has_permission(user, PERM_PRIVATE_CONTACT):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing permission admin.events.export_private_contact",
            )
        if want_private and not (reason or "").strip():
            raise HTTPException(
                status_code=400,
                detail="reason is required for private contact exports",
            )
        return want_private, AUDIT_FINANCE

    if include_private_contact:
        if not user_has_permission(user, PERM_PRIVATE_CONTACT):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing permission admin.events.export_private_contact",
            )
        if not (reason or "").strip():
            raise HTTPException(
                status_code=400,
                detail="reason is required for private contact exports",
            )
        return True, AUDIT_PRIVATE_CONTACT

    return False, AUDIT_EXPORTED


def list_admin_event_buyers(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    q: str | None = None,
    ticket_status: str | None = None,
    purchase_status: str | None = None,
    payment_status: str | None = None,
    refund_status: str | None = None,
    checked_in: str | None = None,
    ticket_type: str | None = None,
    purchased_from: str | None = None,
    purchased_to: str | None = None,
    promo_code: str | None = None,
    ambassador_code: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> dict[str, Any]:
    require_admin_buyer_access(user)
    event = _load_event(db, event_id)
    host_name, host_id, _host_profile_id = _host_context(db, event)
    tickets = _query_tickets(
        db,
        event_id=event_id,
        q=q,
        ticket_status=ticket_status,
        purchase_status=purchase_status,
        payment_status=payment_status,
        refund_status=refund_status,
        checked_in=checked_in,
        ticket_type=ticket_type,
        purchased_from=purchased_from,
        purchased_to=purchased_to,
        promo_code=promo_code,
        ambassador_code=ambassador_code,
    )
    total = len(tickets)
    limit = min(max(limit, 1), LIST_MAX_LIMIT)
    offset = max(offset, 0)
    page = tickets[offset : offset + limit]
    (
        users_by_id,
        passports_by_user,
        payment_status_by_order,
        refund_status_by_order,
        check_in_method_by_ticket,
        transferred_ticket_ids,
        campaign_id_by_order,
    ) = _load_context(db, page)
    # List never includes private contact — export opt-in only.
    rows = []
    for ticket in page:
        order = ticket.order or db.get(Order, ticket.order_id)
        rows.append(
            _serialize_row(
                event=event,
                host_name=host_name,
                host_id=host_id,
                ticket=ticket,
                order=order,
                buyer=users_by_id.get(ticket.buyer_user_id),
                passport=passports_by_user.get(ticket.buyer_user_id),
                payment_status=payment_status_by_order.get(ticket.order_id),
                refund_status=refund_status_by_order.get(ticket.order_id),
                check_in_method=check_in_method_by_ticket.get(ticket.id),
                transferred=ticket.id in transferred_ticket_ids,
                campaign_id=campaign_id_by_order.get(ticket.order_id),
                mode="operations",
                include_private_contact=False,
            )
        )
    return {
        "event_id": str(event.id),
        "event_title": event.title,
        "event_slug": event.slug,
        "event_date": _iso(event.start_datetime),
        "host_name": host_name,
        "host_id": host_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": rows,
    }


def _iter_csv(headers: list[str], rows: list[dict[str, Any]]) -> Iterator[str]:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    yield buf.getvalue()
    buf.seek(0)
    buf.truncate(0)
    for row in rows:
        writer.writerow([sanitize_csv_cell(row.get(h)) for h in headers])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)


def export_admin_event_buyers(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    format: str = "csv",
    mode: str | None = None,
    reason: str | None = None,
    include_private_contact: bool | str | None = False,
    q: str | None = None,
    ticket_status: str | None = None,
    purchase_status: str | None = None,
    payment_status: str | None = None,
    refund_status: str | None = None,
    checked_in: str | None = None,
    ticket_type: str | None = None,
    purchased_from: str | None = None,
    purchased_to: str | None = None,
    promo_code: str | None = None,
    ambassador_code: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[Any, str, str, dict[str, Any]]:
    """
    Returns (body_or_iterator, filename, media_type, meta).
    CSV body is an iterator of chunks for StreamingResponse.
    """
    require_admin_buyer_access(user)
    export_mode = _parse_mode(mode)
    want_private = (
        include_private_contact
        if isinstance(include_private_contact, bool)
        else _truthy(include_private_contact)
    )
    include_private, audit_action = _resolve_export_gates(
        user,
        mode=export_mode,
        include_private_contact=want_private,
        reason=reason,
    )

    fmt = (format or "csv").strip().lower()
    if fmt in {"xlsx", "xls"}:
        raise HTTPException(
            status_code=400,
            detail="XLSX export is not available. Use format=csv or format=json.",
        )
    if fmt not in {"csv", "json"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported export format. Use csv or json.",
        )

    headers = _headers_for(mode=export_mode, include_private_contact=include_private)
    event = _load_event(db, event_id)
    host_name, host_id, host_profile_id = _host_context(db, event)
    tickets = _query_tickets(
        db,
        event_id=event_id,
        q=q,
        ticket_status=ticket_status,
        purchase_status=purchase_status,
        payment_status=payment_status,
        refund_status=refund_status,
        checked_in=checked_in,
        ticket_type=ticket_type,
        purchased_from=purchased_from,
        purchased_to=purchased_to,
        promo_code=promo_code,
        ambassador_code=ambassador_code,
    )
    if len(tickets) > EXPORT_MAX_ROWS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Export exceeds maximum of {EXPORT_MAX_ROWS} rows "
                f"({len(tickets)} matched). Narrow filters and retry."
            ),
        )

    (
        users_by_id,
        passports_by_user,
        payment_status_by_order,
        refund_status_by_order,
        check_in_method_by_ticket,
        transferred_ticket_ids,
        campaign_id_by_order,
    ) = _load_context(db, tickets)

    rows: list[dict[str, Any]] = []
    for ticket in tickets:
        order = ticket.order or db.get(Order, ticket.order_id)
        full = _serialize_row(
            event=event,
            host_name=host_name,
            host_id=host_id,
            ticket=ticket,
            order=order,
            buyer=users_by_id.get(ticket.buyer_user_id),
            passport=passports_by_user.get(ticket.buyer_user_id),
            payment_status=payment_status_by_order.get(ticket.order_id),
            refund_status=refund_status_by_order.get(ticket.order_id),
            check_in_method=check_in_method_by_ticket.get(ticket.id),
            transferred=ticket.id in transferred_ticket_ids,
            campaign_id=campaign_id_by_order.get(ticket.order_id),
            mode=export_mode,
            include_private_contact=include_private,
        )
        rows.append({h: full.get(h) for h in headers})

    filters = _filters_dict(
        q=q,
        ticket_status=ticket_status,
        purchase_status=purchase_status,
        payment_status=payment_status,
        refund_status=refund_status,
        checked_in=checked_in,
        ticket_type=ticket_type,
        purchased_from=purchased_from,
        purchased_to=purchased_to,
        promo_code=promo_code,
        ambassador_code=ambassador_code,
    )
    reason_clean = (reason or "").strip() or None
    details = {
        "admin_user_id": str(user.id),
        "event_id": str(event_id),
        "host_profile_id": host_profile_id,
        "export_mode": export_mode,
        "format": fmt,
        "filters_json": filters,
        "row_count": len(rows),
        "reason": reason_clean,
        "include_private_contact": include_private,
    }
    write_audit_log(
        db,
        action=audit_action,
        actor_user_id=user.id,
        resource_type="event",
        resource_id=str(event_id),
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()

    day = datetime.now(UTC).strftime("%Y%m%d")
    slug = _sanitize_slug(event.slug or str(event_id))
    meta = {
        "row_count": len(rows),
        "mode": export_mode,
        "headers": headers,
        "audit_action": audit_action,
    }

    if fmt == "json":
        body = json.dumps(
            {
                "event_id": str(event.id),
                "event_title": event.title,
                "mode": export_mode,
                "count": len(rows),
                "items": rows,
            },
            indent=2,
            default=str,
        )
        return (
            body,
            f"padeya-event-buyers-{slug}-{day}.json",
            "application/json",
            meta,
        )

    return (
        _iter_csv(headers, rows),
        f"padeya-event-buyers-{slug}-{day}.csv",
        "text/csv; charset=utf-8",
        meta,
    )


def export_admin_event_buyers_csv(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    """Back-compat helper for the tickets-router CSV path."""
    body, filename, _media, _meta = export_admin_event_buyers(
        db,
        user=user,
        event_id=event_id,
        format="csv",
        mode="operations",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    if isinstance(body, str):
        return body, filename
    return "".join(body), filename


def list_admin_event_buyer_exports(
    db: Session,
    *,
    user: User,
    event_id: uuid.UUID,
    limit: int = 50,
) -> list[dict[str, Any]]:
    require_admin_buyer_access(user)
    _load_event(db, event_id)
    limit = min(max(limit, 1), 100)
    rows = list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.action.in_(_AUDIT_ACTIONS),
                AuditLog.resource_type == "event",
                AuditLog.resource_id == str(event_id),
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        ).all()
    )
    actor_ids = {r.actor_user_id for r in rows if r.actor_user_id}
    actors: dict[uuid.UUID, User] = {}
    if actor_ids:
        for u in db.scalars(select(User).where(User.id.in_(actor_ids))).all():
            actors[u.id] = u
    out: list[dict[str, Any]] = []
    for row in rows:
        actor = actors.get(row.actor_user_id) if row.actor_user_id else None
        details = row.details or {}
        out.append(
            {
                "id": str(row.id),
                "action": row.action,
                "actor_user_id": str(row.actor_user_id) if row.actor_user_id else None,
                "admin_user_id": details.get("admin_user_id")
                or (str(row.actor_user_id) if row.actor_user_id else None),
                "actor_name": actor.full_name if actor else None,
                "actor_email": actor.email if actor else None,
                "event_id": details.get("event_id") or str(event_id),
                "host_profile_id": details.get("host_profile_id"),
                "export_mode": details.get("export_mode"),
                "format": details.get("format"),
                "filters_json": details.get("filters_json") or details.get("filters"),
                "row_count": details.get("row_count"),
                "reason": details.get("reason"),
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "details": details,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    return out
