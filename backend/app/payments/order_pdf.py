"""Order PDF downloads and email attachments (tickets + receipt)."""

from __future__ import annotations

import io
import uuid
import zipfile
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.events.models import Event
from app.hosts.models import Host
from app.payments.attendees import normalize_email
from app.payments.models import Order
from app.payments.service import get_order_by_id, normalize_order_reference
from app.tickets.models import Ticket
from app.tickets.pdf import render_order_receipt_pdf
from app.tickets.service import build_ticket_pdf_bytes


@dataclass(frozen=True)
class PdfAttachment:
    filename: str
    content: bytes
    mime_type: str = "application/pdf"


def _buyer_email(order: Order) -> str:
    raw = getattr(order, "guest_buyer_email", None) or order.buyer_email or ""
    return normalize_email(raw)


def email_may_access_order(db: Session, order: Order, email: str) -> bool:
    """Buyer or ticket holder on this order."""
    target = normalize_email(email)
    if not target:
        return False
    if target == _buyer_email(order):
        return True
    rows = db.scalars(
        select(Ticket.holder_email).where(Ticket.order_id == order.id)
    ).all()
    holder_emails = {normalize_email(e) for e in rows if e}
    return target in holder_emails


def assert_email_may_access_order(db: Session, order: Order, email: str) -> None:
    if not email_may_access_order(db, order, email):
        raise HTTPException(
            status_code=403,
            detail="Enter the same email you used at checkout to download this PDF.",
        )


def _tickets_for_recipient(
    db: Session, *, order: Order, recipient_email: str, scope: str
) -> list[Ticket]:
    tickets = list(
        db.scalars(
            select(Ticket)
            .where(Ticket.order_id == order.id)
            .options(selectinload(Ticket.qr_token))
            .order_by(Ticket.created_at)
        )
    )
    if not tickets:
        return []
    norm = normalize_email(recipient_email)
    buyer = _buyer_email(order)
    if scope == "holder":
        return [
            t
            for t in tickets
            if t.holder_email and normalize_email(t.holder_email) == norm
        ]
    if norm != buyer:
        return [
            t
            for t in tickets
            if t.holder_email and normalize_email(t.holder_email) == norm
        ]
    return tickets


def _eligible_pickup_summaries(
    db: Session, order: Order
) -> list[tuple[str, str, str | None]]:
    """(label, pickup_code, qr_token) for merch lines still awaiting pickup.

    Shipping/print-on-demand lines and already-picked-up/cancelled ones are
    left off the receipt — the QR only makes sense for an in-person pickup
    that hasn't happened yet.
    """
    from app.merch.models import MerchFulfillment
    from app.merch.qr_pickup import buyer_qr_token_if_eligible

    rows = db.scalars(
        select(MerchFulfillment).where(MerchFulfillment.order_id == order.id)
    ).all()
    summaries: list[tuple[str, str, str | None]] = []
    for row in rows:
        if (row.fulfillment_method or "pickup") != "pickup":
            continue
        if row.status in {"cancelled", "fulfilled"}:
            continue
        label = f"{row.quantity} × {row.product_name_snapshot}"
        if row.variant_label_snapshot:
            label = f"{label} ({row.variant_label_snapshot})"
        summaries.append((label, row.pickup_code, buyer_qr_token_if_eligible(db, row)))
    return summaries


def build_order_receipt_pdf(db: Session, *, order: Order) -> PdfAttachment | None:
    event = db.get(Event, order.event_id) if order.event_id else None
    # Host-shop orders (no event) still carry the host on the order itself.
    host_id = event.host_id if event is not None else getattr(order, "host_id", None)
    host = db.get(Host, host_id) if host_id else None
    lines: list[str] = []
    for item in order.items or []:
        label = (
            item.product_name
            or item.ticket_type_name
            or item.item_kind
            or "Item"
        )
        if item.variant_label:
            label = f"{label} ({item.variant_label})"
        lines.append(f"{item.quantity} × {label}")
    if not lines:
        lines.append("Order confirmed on Pàdéyá")
    pdf_bytes = render_order_receipt_pdf(
        order_reference=order.reference,
        buyer_name=order.buyer_name or "Buyer",
        buyer_email=_buyer_email(order) or order.buyer_email or "",
        event_title=event.title if event else None,
        host_name=host.display_name if host else None,
        line_items=lines,
        total_amount=str(order.total_amount),
        currency=order.currency or "NGN",
        pickups=_eligible_pickup_summaries(db, order),
    )
    safe_ref = normalize_order_reference(order.reference) or "order"
    return PdfAttachment(
        filename=f"padeya-order-{safe_ref.lower()}.pdf",
        content=pdf_bytes,
    )


def build_pdf_attachments_for_order_email(
    db: Session,
    *,
    order: Order,
    recipient_email: str,
    scope: str,
) -> list[PdfAttachment]:
    """Build PDF attachment list for a specific outbound email recipient."""
    if order.status != "paid":
        return []

    attachments: list[PdfAttachment] = []
    tickets = _tickets_for_recipient(
        db, order=order, recipient_email=recipient_email, scope=scope
    )
    seen_names: set[str] = set()
    for ticket in tickets:
        pdf_bytes, filename = build_ticket_pdf_bytes(db, ticket)
        if filename in seen_names:
            base, ext = filename.rsplit(".", 1) if "." in filename else (filename, "pdf")
            filename = f"{base}-{ticket.public_code[:8]}.{ext}"
        seen_names.add(filename)
        attachments.append(PdfAttachment(filename=filename, content=pdf_bytes))

    if not tickets:
        receipt = build_order_receipt_pdf(db, order=order)
        if receipt is not None:
            attachments.append(receipt)

    return attachments


def package_order_pdf_download(
    db: Session,
    *,
    order: Order,
    email: str,
) -> tuple[bytes, str, str]:
    """Return (body, filename, media_type) for HTTP download."""
    assert_email_may_access_order(db, order, email)
    if order.status != "paid":
        raise HTTPException(
            status_code=409,
            detail="PDF is available after payment is confirmed.",
        )

    norm = normalize_email(email)
    buyer = _buyer_email(order)
    scope = "buyer" if norm == buyer else "holder"
    attachments = build_pdf_attachments_for_order_email(
        db, order=order, recipient_email=email, scope=scope
    )
    if not attachments:
        receipt = build_order_receipt_pdf(db, order=order)
        if receipt is not None:
            attachments = [receipt]
    if not attachments:
        raise HTTPException(status_code=404, detail="No PDF is available for this order yet.")

    if len(attachments) == 1:
        att = attachments[0]
        return att.content, att.filename, att.mime_type

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for att in attachments:
            zf.writestr(att.filename, att.content)
    safe_ref = normalize_order_reference(order.reference) or "order"
    return (
        buf.getvalue(),
        f"padeya-order-{safe_ref.lower()}.zip",
        "application/zip",
    )


def resolve_email_attachments_for_event(db: Session, event) -> tuple[PdfAttachment, ...]:
    """Build attachments at send time from template context."""
    from app.email.models import EmailEvent

    if not isinstance(event, EmailEvent):
        return ()
    ctx = event.context_json or {}
    order_id_raw = ctx.get("order_id")
    if not order_id_raw:
        return ()
    try:
        order_id = uuid.UUID(str(order_id_raw))
    except ValueError:
        return ()
    order = get_order_by_id(db, order_id)
    if order is None or order.status != "paid":
        return ()

    template = event.template or ""
    scope = "buyer"
    if template == "ticket_gift_received":
        scope = "holder"
    if template not in {
        "ticket_confirmed",
        "ticket_gift_received",
        "checkout_account_ready",
    }:
        return ()

    items = build_pdf_attachments_for_order_email(
        db,
        order=order,
        recipient_email=event.recipient_email,
        scope=scope,
    )
    return tuple(items)
