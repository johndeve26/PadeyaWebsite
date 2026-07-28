"""Paystack payment for sponsorship invoices — webhook-only confirmation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.payments.paystack import PaystackError, initialize_transaction
from app.sponsorships.deals_constants import PAYABLE_INVOICE_STATUSES, PAYSTACK_REF_PREFIX
from app.sponsorships.models import (
    SponsorshipAnalytics,
    SponsorshipDeal,
    SponsorshipInvoice,
    SponsorshipPaymentEvent,
    SponsorshipPlacement,
)


def _now() -> datetime:
    return datetime.now(UTC)


def redact_paystack_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    return {
        "event": payload.get("event"),
        "reference": data.get("reference"),
        "status": data.get("status"),
        "amount": data.get("amount"),
        "currency": data.get("currency"),
        "id": data.get("id"),
    }


def paystack_reference_for_invoice(invoice_id: uuid.UUID) -> str:
    return f"{PAYSTACK_REF_PREFIX}{invoice_id.hex[:24].upper()}"


def initialize_invoice_payment(
    db: Session,
    *,
    invoice: SponsorshipInvoice,
    deal: SponsorshipDeal,
    payer_email: str,
) -> str:
    if invoice.status not in PAYABLE_INVOICE_STATUSES and invoice.status != "paid":
        raise HTTPException(status_code=400, detail="Invoice is not payable")
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="Invoice already paid")

    ref = invoice.paystack_reference or paystack_reference_for_invoice(invoice.id)
    settings = get_settings()
    base = (settings.frontend_url or "http://localhost:3000").rstrip("/")
    callback = f"{base}/sponsor/deals/{deal.id}?payment=return"
    amount_kobo = int(invoice.amount * 100)
    try:
        data = initialize_transaction(
            email=payer_email,
            amount_kobo=amount_kobo,
            reference=ref,
            callback_url=callback,
            metadata={
                "kind": "sponsorship_invoice",
                "invoice_id": str(invoice.id),
                "deal_id": str(deal.id),
            },
            db=db,
        )
    except PaystackError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    invoice.paystack_reference = ref
    invoice.payment_url = data.get("authorization_url")
    invoice.status = "payment_pending"
    deal.status = "payment_pending"
    db.flush()
    return str(invoice.payment_url or "")


def finalize_sponsorship_paystack_success(
    db: Session,
    *,
    reference: str,
    data: dict[str, Any],
    raw_payload: dict[str, Any],
    event_type: str = "charge.success",
) -> None:
    if not reference.startswith(PAYSTACK_REF_PREFIX):
        return

    invoice = db.scalar(
        select(SponsorshipInvoice)
        .where(SponsorshipInvoice.paystack_reference == reference)
        .with_for_update()
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="Sponsorship invoice not found")

    deal = db.get(SponsorshipDeal, invoice.deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    if invoice.status == "paid" and deal.status in {"paid", "active", "completed"}:
        return

    amount = data.get("amount")
    if amount is None:
        raise HTTPException(status_code=400, detail="Payment amount missing")
    try:
        amount_kobo = int(amount)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Payment amount invalid") from exc
    expected_kobo = int(invoice.amount * 100)
    if amount_kobo != expected_kobo:
        raise HTTPException(status_code=400, detail="Payment amount mismatch")
    currency = data.get("currency")
    if currency is not None:
        if str(currency).strip().upper() != str(invoice.currency or "").strip().upper():
            raise HTTPException(status_code=400, detail="Payment currency mismatch")

    provider_ref = str(data.get("id") or reference)
    redacted = redact_paystack_payload(raw_payload)
    try:
        db.add(
            SponsorshipPaymentEvent(
                invoice_id=invoice.id,
                deal_id=deal.id,
                provider="paystack",
                provider_reference=provider_ref,
                event_type=event_type,
                status="success",
                amount=invoice.amount,
                currency=invoice.currency,
                raw_payload_redacted=redacted,
            )
        )
        db.flush()
    except IntegrityError:
        db.rollback()
        invoice = db.scalar(
            select(SponsorshipInvoice)
            .where(SponsorshipInvoice.paystack_reference == reference)
            .with_for_update()
        )
        deal = db.get(SponsorshipDeal, invoice.deal_id) if invoice else None
        if invoice and invoice.status == "paid":
            return
        raise

    now = _now()
    invoice.status = "paid"
    invoice.paid_at = now
    deal.status = "active"

    placement = None
    if deal.placement_id:
        placement = db.get(SponsorshipPlacement, deal.placement_id)
    if placement is None and deal.slot_id:
        placement = SponsorshipPlacement(
            slot_id=deal.slot_id,
            sponsor_id=deal.sponsor_id,
            inquiry_id=deal.inquiry_id,
            status="active",
            starts_at=deal.starts_at,
            ends_at=deal.ends_at,
        )
        db.add(placement)
        db.flush()
        db.add(SponsorshipAnalytics(placement_id=placement.id))
        deal.placement_id = placement.id
    elif placement is not None:
        placement.status = "active"

    from app.sponsorships.deliverables_service import ensure_deliverables_for_active_deal

    ensure_deliverables_for_active_deal(
        db, deal=deal, placement_id=deal.placement_id
    )

    write_audit_log(
        db,
        action="sponsorship_deals.payment_confirmed",
        actor_user_id=None,
        resource_type="sponsorship_deal",
        resource_id=str(deal.id),
        details={"invoice_id": str(invoice.id), "reference": reference},
    )
    db.flush()
    _notify_payment_confirmed(db, deal=deal, invoice=invoice)


def _notify_payment_confirmed(
    db: Session, *, deal: SponsorshipDeal, invoice: SponsorshipInvoice
) -> None:
    from app.notifications.service import notify_user
    from app.sponsorships.models import Sponsor
    from app.hosts.models import Host

    sponsor = db.get(Sponsor, deal.sponsor_id)
    host = db.get(Host, deal.host_id)
    if sponsor and sponsor.owner_user_id:
        notify_user(
            db,
            user_id=sponsor.owner_user_id,
            kind="sponsor.deal_active",
            title="Sponsorship payment confirmed",
            body=f"Your deal “{deal.title}” is active on Pàdéyá.",
            link_path=f"/sponsor/deals/{deal.id}",
            dedupe_key=f"sponsor_deal_paid:{deal.id}",
        )
    if host and host.user_id:
        notify_user(
            db,
            user_id=host.user_id,
            kind="sponsor.deal_active",
            title="Sponsor payment received",
            body=f"Deal “{deal.title}” is now active.",
            link_path=f"/host/sponsorships/deals/{deal.id}",
            dedupe_key=f"host_deal_paid:{deal.id}",
        )
