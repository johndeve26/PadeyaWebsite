"""Sponsorship deal lifecycle services."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.hosts.models import Host
from app.hosts.team_access import require_host_for_permission
from app.sponsor_profiles.campaign_service import require_sponsor_can_manage_campaigns
from app.sponsor_profiles.service import require_sponsor_access
from app.sponsorships.deals_constants import (
    DEAL_STATUSES,
    HOST_EDIT_STATUSES,
    INVOICE_STATUSES,
    SPONSOR_DECIDE_STATUSES,
)
from app.sponsorships.deals_payment import initialize_invoice_payment
from app.sponsorships.deals_schemas import SponsorshipDealCreate, SponsorshipDealUpdate
from app.sponsorships.models import (
    Sponsor,
    SponsorshipDeal,
    SponsorshipInquiry,
    SponsorshipInvoice,
    SponsorshipSlot,
)
from app.users.models import User
from app.users.service import user_has_permission


def _now() -> datetime:
    return datetime.now(UTC)


def _invoice_number() -> str:
    return f"SPN-{datetime.now(UTC).strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"


def _serialize_deal(
    db: Session,
    deal: SponsorshipDeal,
    *,
    viewer_user: User | None = None,
    sponsor_team_can_manage: bool = False,
) -> dict[str, Any]:
    host = db.get(Host, deal.host_id)
    sponsor = db.get(Sponsor, deal.sponsor_id)
    invoice = db.scalar(
        select(SponsorshipInvoice)
        .where(SponsorshipInvoice.deal_id == deal.id)
        .order_by(SponsorshipInvoice.created_at.desc())
    )
    inv_pub = None
    if invoice:
        inv_pub = {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "amount": invoice.amount,
            "currency": invoice.currency,
            "status": invoice.status,
            "due_at": invoice.due_at,
            "paid_at": invoice.paid_at,
            "payment_url": invoice.payment_url
            if invoice.status in {"issued", "payment_pending"}
            else None,
        }
    can_accept = (
        sponsor_team_can_manage and deal.status in SPONSOR_DECIDE_STATUSES
    )
    can_pay = (
        sponsor_team_can_manage
        and invoice is not None
        and invoice.status in {"issued", "payment_pending"}
        and deal.status in {"accepted", "invoice_pending", "payment_pending"}
    )
    can_edit = deal.status in HOST_EDIT_STATUSES
    return {
        "id": deal.id,
        "sponsor_id": deal.sponsor_id,
        "host_id": deal.host_id,
        "event_id": deal.event_id,
        "campaign_id": deal.campaign_id,
        "inquiry_id": deal.inquiry_id,
        "slot_id": deal.slot_id,
        "placement_id": deal.placement_id,
        "title": deal.title,
        "description": deal.description,
        "package_type": deal.package_type,
        "deliverables": deal.deliverables,
        "amount": deal.amount,
        "currency": deal.currency,
        "status": deal.status,
        "accepted_at": deal.accepted_at,
        "starts_at": deal.starts_at,
        "ends_at": deal.ends_at,
        "created_at": deal.created_at,
        "updated_at": deal.updated_at,
        "host_display_name": host.display_name if host else None,
        "sponsor_display_name": (
            sponsor.display_name or sponsor.company_name if sponsor else None
        ),
        "invoice": inv_pub,
        "can_edit": can_edit,
        "can_accept": can_accept,
        "can_pay": can_pay,
    }


def _notify_proposal(db: Session, deal: SponsorshipDeal) -> None:
    from app.notifications.service import notify_user

    sponsor = db.get(Sponsor, deal.sponsor_id)
    if sponsor and sponsor.owner_user_id:
        notify_user(
            db,
            user_id=sponsor.owner_user_id,
            kind="sponsor.deal_proposal",
            title="New sponsorship proposal",
            body=f"A host sent a proposal: {deal.title}",
            link_path=f"/sponsor/deals/{deal.id}",
            dedupe_key=f"sponsor_deal_proposed:{deal.id}",
        )


def host_list_deals(db: Session, user: User) -> list[dict[str, Any]]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="sponsors.manage_slots"
    )
    rows = list(
        db.scalars(
            select(SponsorshipDeal)
            .where(SponsorshipDeal.host_id == host.id)
            .order_by(SponsorshipDeal.updated_at.desc())
        )
    )
    return [_serialize_deal(db, d, viewer_user=user) for d in rows]


def host_get_deal(db: Session, user: User, deal_id: uuid.UUID) -> dict[str, Any]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="sponsors.view"
    )
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None or deal.host_id != host.id:
        raise HTTPException(status_code=404, detail="Deal not found")
    return _serialize_deal(db, deal, viewer_user=user)


def host_create_deal(
    db: Session, user: User, payload: SponsorshipDealCreate
) -> dict[str, Any]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="sponsors.manage_slots"
    )
    sponsor = db.get(Sponsor, payload.sponsor_id)
    if sponsor is None:
        raise HTTPException(status_code=404, detail="Sponsor not found")

    inquiry = None
    slot = None
    if payload.inquiry_id:
        inquiry = db.get(SponsorshipInquiry, payload.inquiry_id)
        if inquiry is None:
            raise HTTPException(status_code=404, detail="Inquiry not found")
        slot = db.get(SponsorshipSlot, inquiry.slot_id)
        if slot is None or slot.host_id != host.id:
            raise HTTPException(status_code=400, detail="Inquiry not for this host")
        if inquiry.sponsor_id and inquiry.sponsor_id != payload.sponsor_id:
            raise HTTPException(status_code=400, detail="Inquiry sponsor mismatch")

    if payload.slot_id:
        slot = db.get(SponsorshipSlot, payload.slot_id)
        if slot is None or slot.host_id != host.id:
            raise HTTPException(status_code=400, detail="Invalid slot")

    deal = SponsorshipDeal(
        sponsor_id=payload.sponsor_id,
        host_id=host.id,
        event_id=payload.event_id or (slot.event_id if slot else None),
        campaign_id=payload.campaign_id,
        inquiry_id=payload.inquiry_id,
        slot_id=slot.id if slot else payload.slot_id,
        title=payload.title.strip(),
        description=payload.description,
        package_type=payload.package_type,
        deliverables=payload.deliverables,
        amount=Decimal(payload.amount).quantize(Decimal("0.01")),
        currency=(payload.currency or "NGN").upper(),
        status="draft",
        proposed_by_user_id=user.id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    db.add(deal)
    db.flush()
    write_audit_log(
        db,
        action="sponsorship_deals.create",
        actor_user_id=user.id,
        resource_type="sponsorship_deal",
        resource_id=str(deal.id),
        details={"host_id": str(host.id)},
    )
    db.commit()
    db.refresh(deal)
    return host_get_deal(db, user, deal.id)


def host_update_deal(
    db: Session, user: User, deal_id: uuid.UUID, payload: SponsorshipDealUpdate
) -> dict[str, Any]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="sponsors.manage_slots"
    )
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None or deal.host_id != host.id:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.status not in HOST_EDIT_STATUSES:
        raise HTTPException(status_code=400, detail="Deal cannot be edited")
    data = payload.model_dump(exclude_unset=True)
    for field in (
        "title",
        "description",
        "package_type",
        "deliverables",
        "starts_at",
        "ends_at",
        "campaign_id",
    ):
        if field in data:
            setattr(deal, field, data[field])
    if "amount" in data and data["amount"] is not None:
        deal.amount = Decimal(data["amount"]).quantize(Decimal("0.01"))
    db.commit()
    return host_get_deal(db, user, deal.id)


def host_send_deal(db: Session, user: User, deal_id: uuid.UUID) -> dict[str, Any]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="sponsors.manage_slots"
    )
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None or deal.host_id != host.id:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft deals can be sent")
    deal.status = "proposed"
    _notify_proposal(db, deal)
    write_audit_log(
        db,
        action="sponsorship_deals.send",
        actor_user_id=user.id,
        resource_type="sponsorship_deal",
        resource_id=str(deal.id),
        details={},
    )
    db.commit()
    return host_get_deal(db, user, deal.id)


def host_cancel_deal(db: Session, user: User, deal_id: uuid.UUID) -> dict[str, Any]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="sponsors.manage_slots"
    )
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None or deal.host_id != host.id:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.status in {"paid", "active", "completed"}:
        raise HTTPException(status_code=400, detail="Cannot cancel active deal")
    deal.status = "cancelled"
    db.commit()
    return host_get_deal(db, user, deal.id)


def _sponsor_can_manage(db: Session, user: User, sponsor: Sponsor) -> bool:
    try:
        require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor.id)
        return True
    except HTTPException:
        return False


def sponsor_list_deals(
    db: Session, user: User, sponsor_id: uuid.UUID
) -> list[dict[str, Any]]:
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    can_manage = _sponsor_can_manage(db, user, sponsor)
    rows = list(
        db.scalars(
            select(SponsorshipDeal)
            .where(SponsorshipDeal.sponsor_id == sponsor.id)
            .order_by(SponsorshipDeal.updated_at.desc())
        )
    )
    return [
        _serialize_deal(
            db, d, viewer_user=user, sponsor_team_can_manage=can_manage
        )
        for d in rows
    ]


def sponsor_get_deal(
    db: Session, user: User, sponsor_id: uuid.UUID, deal_id: uuid.UUID
) -> dict[str, Any]:
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None or deal.sponsor_id != sponsor.id:
        raise HTTPException(status_code=404, detail="Deal not found")
    return _serialize_deal(
        db,
        deal,
        viewer_user=user,
        sponsor_team_can_manage=_sponsor_can_manage(db, user, sponsor),
    )


def _create_invoice_for_deal(db: Session, deal: SponsorshipDeal) -> SponsorshipInvoice:
    invoice = SponsorshipInvoice(
        deal_id=deal.id,
        sponsor_id=deal.sponsor_id,
        host_id=deal.host_id,
        invoice_number=_invoice_number(),
        amount=deal.amount,
        currency=deal.currency,
        status="issued",
        due_at=_now() + timedelta(days=14),
    )
    db.add(invoice)
    deal.status = "invoice_pending"
    db.flush()
    return invoice


def sponsor_accept_deal(
    db: Session, user: User, sponsor_id: uuid.UUID, deal_id: uuid.UUID
) -> dict[str, Any]:
    require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor_id)
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None or deal.sponsor_id != sponsor.id:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.status not in SPONSOR_DECIDE_STATUSES:
        raise HTTPException(status_code=400, detail="Deal is not awaiting acceptance")
    deal.status = "accepted"
    deal.accepted_by_user_id = user.id
    deal.accepted_at = _now()
    _create_invoice_for_deal(db, deal)
    write_audit_log(
        db,
        action="sponsorship_deals.accept",
        actor_user_id=user.id,
        resource_type="sponsorship_deal",
        resource_id=str(deal.id),
        details={},
    )
    db.commit()
    return sponsor_get_deal(db, user, sponsor_id, deal_id)


def sponsor_reject_deal(
    db: Session, user: User, sponsor_id: uuid.UUID, deal_id: uuid.UUID
) -> dict[str, Any]:
    require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor_id)
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None or deal.sponsor_id != sponsor.id:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.status not in SPONSOR_DECIDE_STATUSES:
        raise HTTPException(status_code=400, detail="Deal is not awaiting decision")
    deal.status = "rejected"
    db.commit()
    return sponsor_get_deal(db, user, sponsor_id, deal_id)


def sponsor_pay_deal(
    db: Session, user: User, sponsor_id: uuid.UUID, deal_id: uuid.UUID
) -> dict[str, Any]:
    require_sponsor_can_manage_campaigns(db, user=user, sponsor_id=sponsor_id)
    sponsor, _ = require_sponsor_access(
        db, user=user, sponsor_id=sponsor_id, permission="sponsors.view_own"
    )
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None or deal.sponsor_id != sponsor.id:
        raise HTTPException(status_code=404, detail="Deal not found")
    invoice = db.scalar(
        select(SponsorshipInvoice)
        .where(SponsorshipInvoice.deal_id == deal.id)
        .order_by(SponsorshipInvoice.created_at.desc())
    )
    if invoice is None:
        raise HTTPException(status_code=400, detail="No invoice for deal")
    email = sponsor.contact_email
    if not email:
        raise HTTPException(status_code=400, detail="Sponsor contact email required")
    url = initialize_invoice_payment(
        db, invoice=invoice, deal=deal, payer_email=email
    )
    db.commit()
    return {
        "payment_url": url,
        "invoice_id": invoice.id,
        "message": "Complete payment on Paystack. Status updates after verified webhook only.",
    }


def host_revenue_report(db: Session, user: User) -> dict[str, Any]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="sponsors.view"
    )
    deals = list(
        db.scalars(select(SponsorshipDeal).where(SponsorshipDeal.host_id == host.id))
    )
    pending = Decimal("0")
    paid = Decimal("0")
    active = 0
    for d in deals:
        if d.status in {"accepted", "invoice_pending", "payment_pending"}:
            pending += d.amount
        if d.status in {"paid", "active", "completed"}:
            paid += d.amount
        if d.status == "active":
            active += 1
    from app.sponsorships.deliverables_service import deliverables_summary_for_host

    d_summary = deliverables_summary_for_host(db, host.id)
    return {
        "revenue_pending_ngn": pending.quantize(Decimal("0.01")) if pending else None,
        "revenue_paid_ngn": paid.quantize(Decimal("0.01")) if paid else None,
        "active_placements": active,
        "active_deals": d_summary["active_deals"],
        "pending_deliverables": d_summary["pending_deliverables"],
        "overdue_deliverables": d_summary["overdue"],
        "completed_deliverables": d_summary["completed"],
        "deliverables_completion_rate": d_summary["completion_rate"],
    }


def admin_list_deals(db: Session) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            select(SponsorshipDeal).order_by(SponsorshipDeal.created_at.desc()).limit(200)
        )
    )
    return [_serialize_deal(db, d) for d in rows]


def admin_get_deal(db: Session, deal_id: uuid.UUID) -> dict[str, Any]:
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")
    return _serialize_deal(db, deal)


def admin_cancel_deal(db: Session, actor: User, deal_id: uuid.UUID) -> dict[str, Any]:
    deal = db.get(SponsorshipDeal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")
    deal.status = "cancelled"
    write_audit_log(
        db,
        action="sponsorship_deals.admin_cancel",
        actor_user_id=actor.id,
        resource_type="sponsorship_deal",
        resource_id=str(deal.id),
        details={},
    )
    db.commit()
    return admin_get_deal(db, deal_id)


def admin_void_invoice(
    db: Session, actor: User, invoice_id: uuid.UUID
) -> dict[str, Any]:
    invoice = db.get(SponsorshipInvoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == "paid":
        raise HTTPException(status_code=400, detail="Cannot void paid invoice")
    invoice.status = "void"
    deal = db.get(SponsorshipDeal, invoice.deal_id)
    if deal and deal.status in {"invoice_pending", "payment_pending"}:
        deal.status = "cancelled"
    write_audit_log(
        db,
        action="sponsorship_invoices.admin_void",
        actor_user_id=actor.id,
        resource_type="sponsorship_invoice",
        resource_id=str(invoice.id),
        details={},
    )
    db.commit()
    return admin_get_deal(db, invoice.deal_id)


def deal_spend_totals(
    db: Session, sponsor_id: uuid.UUID, *, campaign_id: uuid.UUID | None = None
) -> dict[str, Decimal | None]:
    q = select(SponsorshipDeal).where(SponsorshipDeal.sponsor_id == sponsor_id)
    if campaign_id is not None:
        q = q.where(SponsorshipDeal.campaign_id == campaign_id)
    deals = list(db.scalars(q))
    committed = Decimal("0")
    paid = Decimal("0")
    for d in deals:
        if d.status in {"accepted", "invoice_pending", "payment_pending", "paid", "active", "completed"}:
            committed += d.amount
        if d.status in {"paid", "active", "completed"}:
            paid += d.amount
    return {
        "committed": committed.quantize(Decimal("0.01")) if committed else None,
        "paid": paid.quantize(Decimal("0.01")) if paid else None,
    }
