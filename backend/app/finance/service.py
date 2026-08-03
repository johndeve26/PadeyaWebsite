"""Refund and payout business logic with strict finance controls."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import write_audit_log
from app.events.models import Event, TicketType
from app.finance.constants import DEFAULT_REFUND_POLICY, REFUND_POLICY_TYPES
from app.finance.ledger import (
    complete_payout,
    credit_sale,
    debit_refund,
    get_or_create_host_balance,
    hold_payout,
    release_payout_hold,
)
from app.finance.models import (
    HostBalance,
    LedgerEntry,
    PayoutEvidence,
    PayoutRequest,
    Refund,
    RefundRequest,
)
from app.finance.schemas import (
    PayoutMarkPaid,
    PayoutRequestCreate,
    PayoutReview,
    RefundEscalate,
    RefundRequestCreate,
    RefundReview,
)
from app.hosts.models import Host
from app.hosts.team_access import require_host_for_permission
from app.payments.models import Order
from app.tickets.models import Ticket, TicketQrToken
from app.users.models import User
from app.users.service import user_has_permission, user_has_role, user_role_names


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def normalize_refund_policy(raw: str | None) -> str:
    if not raw:
        return DEFAULT_REFUND_POLICY
    value = raw.strip().lower().replace(" ", "_")
    if value in REFUND_POLICY_TYPES:
        return value
    # Allow free-text legacy values to fall back to admin control
    return DEFAULT_REFUND_POLICY


def policy_allows_buyer_request(event: Event, policy: str) -> tuple[bool, str]:
    now = datetime.now(UTC)
    start = _aware(event.start_datetime)
    if policy == "no_refunds":
        return False, "This event does not allow refunds"
    if policy == "partial_refund_only":
        return False, "Partial refunds are not available yet"
    if policy == "cancelled_event_only":
        if event.status != "cancelled":
            return False, "Refunds are only allowed if the event is cancelled"
        return True, "ok"
    if policy == "refund_until_7_days_before":
        if now > start - timedelta(days=7):
            return False, "Refund window closed (7 days before event)"
        return True, "ok"
    if policy == "refund_until_24_hours_before":
        if now > start - timedelta(hours=24):
            return False, "Refund window closed (24 hours before event)"
        return True, "ok"
    if policy == "admin_controlled":
        return True, "ok"
    if policy == "custom":
        # Custom text is host-defined; requests still go through admin review.
        return True, "ok"
    return False, "Refunds are not available for this event"


def is_super_admin(user: User) -> bool:
    return "super_admin" in user_role_names(user)


def can_approve_refunds(user: User) -> bool:
    """Finance admins and super admins only — not support agents."""
    if is_super_admin(user):
        return True
    if user_has_role(user, "support_agent") and not user_has_role(user, "finance_admin"):
        return False
    return user_has_permission(user, "refunds.approve") or user_has_permission(
        user, "admin.full_access"
    )


def can_review_payouts(user: User) -> bool:
    if is_super_admin(user):
        return True
    if user_has_role(user, "support_agent") and not user_has_role(user, "finance_admin"):
        return False
    return user_has_permission(user, "payouts.review") or user_has_permission(
        user, "admin.full_access"
    )


def record_sale_credit_for_order(db: Session, order: Order) -> LedgerEntry | None:
    """Idempotent host credit after successful payment.

    Credits host_net_estimate (merchandise + shipping − host-paid fees).
    Buyer-paid platform/service fees are not credited to the host.
    """
    event = db.get(Event, order.event_id)
    if event is None:
        return None
    buyer_fees = Decimal(getattr(order, "buyer_fee_total", None) or 0)
    host_net = getattr(order, "host_net_estimate", None)
    credit_amount = Decimal(host_net) if host_net is not None else None
    # Legacy / manually seeded orders may have host_net_estimate=0 with a paid total.
    if credit_amount is None or (
        credit_amount == 0 and Decimal(order.total_amount) > 0 and buyer_fees == 0
    ):
        credit_amount = Decimal(order.total_amount) - buyer_fees
    if credit_amount <= 0:
        return None
    existing = db.scalar(
        select(LedgerEntry).where(
            LedgerEntry.host_id == event.host_id,
            LedgerEntry.entry_type == "sale_credit",
            LedgerEntry.reference_type == "order",
            LedgerEntry.reference_id == str(order.id),
        )
    )
    if existing is not None:
        return existing
    return credit_sale(
        db,
        host_id=event.host_id,
        amount=credit_amount,
        currency=order.currency,
        order_id=order.id,
        actor_user_id=order.buyer_user_id,
    )


def _serialize_refund_request(db: Session, row: RefundRequest) -> dict:
    order = db.get(Order, row.order_id)
    event = db.get(Event, row.event_id)
    return {
        "id": row.id,
        "order_id": row.order_id,
        "payment_id": row.payment_id,
        "buyer_user_id": row.buyer_user_id,
        "host_id": row.host_id,
        "event_id": row.event_id,
        "status": row.status,
        "refund_type": row.refund_type,
        "requested_amount": row.requested_amount,
        "currency": row.currency,
        "reason": row.reason,
        "policy_snapshot": row.policy_snapshot,
        "ticket_ids": row.ticket_ids,
        "line_allocations": getattr(row, "line_allocations", None),
        "requires_referral_refund_allocation": bool(
            getattr(row, "requires_referral_refund_allocation", False)
        ),
        "escalation_note": row.escalation_note,
        "review_note": row.review_note,
        "reviewed_by_user_id": row.reviewed_by_user_id,
        "reviewed_at": row.reviewed_at,
        "created_at": row.created_at,
        "order_reference": order.reference if order else None,
        "event_title": event.title if event else None,
    }


def create_refund_request(
    db: Session, *, user: User, payload: RefundRequestCreate
) -> dict:
    from app.users.restrictions import assert_can_request_refunds

    assert_can_request_refunds(db, user)

    order = db.scalar(
        select(Order)
        .where(Order.id == payload.order_id)
        .options(selectinload(Order.payments), selectinload(Order.tickets))
    )
    if order is None or order.buyer_user_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in {"paid", "partially_refunded"}:
        raise HTTPException(status_code=400, detail="Only paid orders can be refunded")

    if payload.refund_type == "partial" or (
        payload.amount is not None and payload.amount < order.total_amount
    ):
        raise HTTPException(
            status_code=400,
            detail="Partial refunds are not available yet",
        )

    event = db.get(Event, order.event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    policy = normalize_refund_policy(
        getattr(event, "refund_policy_type", None) or event.refund_policy
    )
    allowed, message = policy_allows_buyer_request(event, policy)
    if not allowed:
        raise HTTPException(status_code=400, detail=message)

    open_req = db.scalar(
        select(RefundRequest).where(
            RefundRequest.order_id == order.id,
            RefundRequest.status.in_(
                ["requested", "under_review", "approved", "completed"]
            ),
        )
    )
    if open_req is not None:
        raise HTTPException(
            status_code=409, detail="A refund request already exists for this order"
        )

    payment = next(
        (p for p in order.payments if p.status == "successful"),
        order.payments[0] if order.payments else None,
    )
    tickets = [
        t
        for t in order.tickets
        if t.status in {"active", "checked_in", "reserved"}
    ]
    if not tickets:
        raise HTTPException(status_code=400, detail="No refundable tickets on this order")

    amount = Decimal(order.total_amount)
    row = RefundRequest(
        order_id=order.id,
        payment_id=payment.id if payment else None,
        buyer_user_id=user.id,
        host_id=event.host_id,
        event_id=event.id,
        status="requested",
        refund_type="full",
        requested_amount=amount,
        currency=order.currency,
        reason=payload.reason.strip(),
        policy_snapshot=policy,
        ticket_ids=[str(t.id) for t in tickets],
    )
    db.add(row)
    write_audit_log(
        db,
        action="finance.refund_request",
        actor_user_id=user.id,
        resource_type="refund_request",
        resource_id=str(row.id),
        details={"order_id": str(order.id), "amount": str(amount)},
    )
    from app.email.service import enqueue_template

    enqueue_template(
        db,
        template="ticket_refund_update",
        to=user.email,
        recipient_user_id=user.id,
        dedupe_key=f"refund_request:{row.id}:requested",
        context={
            "event_title": event.title,
            "refund_status": "requested",
        },
    )
    from app.notifications.triggers import notify_buyer_ticket_refund

    notify_buyer_ticket_refund(
        db,
        buyer_user_id=user.id,
        event_title=event.title,
        refund_status="requested",
        dedupe_key=f"refund_request:{row.id}:requested:notif",
    )
    db.commit()
    db.refresh(row)
    return _serialize_refund_request(db, row)


def list_my_refund_requests(db: Session, user: User) -> list[dict]:
    rows = db.scalars(
        select(RefundRequest)
        .where(RefundRequest.buyer_user_id == user.id)
        .order_by(RefundRequest.created_at.desc())
    ).all()
    return [_serialize_refund_request(db, r) for r in rows]


def cancel_refund_request(db: Session, *, user: User, request_id: UUID) -> dict:
    """Buyer (or finance) can cancel an open refund request before decision."""
    row = db.get(RefundRequest, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Refund request not found")
    is_buyer = row.buyer_user_id == user.id
    is_finance = can_approve_refunds(user) or is_super_admin(user)
    if not is_buyer and not is_finance:
        raise HTTPException(status_code=403, detail="Not allowed")
    if row.status not in {"requested", "under_review"}:
        raise HTTPException(
            status_code=400,
            detail="Only open refund requests can be cancelled",
        )
    row.status = "cancelled"
    write_audit_log(
        db,
        action="finance.refund_cancel",
        actor_user_id=user.id,
        resource_type="refund_request",
        resource_id=str(row.id),
    )
    db.commit()
    db.refresh(row)
    return _serialize_refund_request(db, row)


def list_refund_requests_for_staff(
    db: Session, user: User, *, status_filter: str | None = None
) -> list[dict]:
    if not (
        user_has_permission(user, "refunds.review")
        or user_has_permission(user, "admin.full_access")
    ):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    q = select(RefundRequest).order_by(RefundRequest.created_at.desc())
    if status_filter:
        q = q.where(RefundRequest.status == status_filter)
    rows = db.scalars(q).all()
    return [_serialize_refund_request(db, r) for r in rows]


def escalate_refund_request(
    db: Session, *, user: User, request_id: UUID, payload: RefundEscalate
) -> dict:
    if not (
        user_has_permission(user, "refunds.review")
        or user_has_permission(user, "admin.full_access")
    ):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    row = db.get(RefundRequest, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Refund request not found")
    if row.status not in {"requested", "under_review"}:
        raise HTTPException(status_code=400, detail="Request cannot be escalated")

    # Support may escalate/view notes only — never approve financial completion
    row.status = "under_review"
    row.escalation_note = payload.note.strip()
    write_audit_log(
        db,
        action="finance.refund_escalate",
        actor_user_id=user.id,
        resource_type="refund_request",
        resource_id=str(row.id),
        details={"note": payload.note[:200]},
    )
    db.commit()
    db.refresh(row)
    return _serialize_refund_request(db, row)


def _invalidate_tickets_for_refund(db: Session, order: Order) -> list[Ticket]:
    tickets = list(
        db.scalars(
            select(Ticket).where(
                Ticket.order_id == order.id,
                Ticket.status.in_(["active", "checked_in", "reserved"]),
            )
        )
    )
    for ticket in tickets:
        ticket.status = "refunded"
        qr = db.scalar(select(TicketQrToken).where(TicketQrToken.ticket_id == ticket.id))
        if qr is not None and qr.revoked_at is None:
            qr.revoked_at = datetime.now(UTC)
        tt = db.get(TicketType, ticket.ticket_type_id)
        if tt is not None and tt.quantity_sold > 0:
            tt.quantity_sold = max(0, tt.quantity_sold - 1)
            if tt.status == "sold_out" and tt.quantity_sold < tt.quantity:
                tt.status = "active"
    return tickets


def review_refund_request(
    db: Session, *, user: User, request_id: UUID, payload: RefundReview
) -> dict:
    if not can_approve_refunds(user):
        raise HTTPException(
            status_code=403,
            detail="Support agents cannot approve or reject refunds",
        )
    row = db.get(RefundRequest, request_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Refund request not found")
    if row.status not in {"requested", "under_review"}:
        raise HTTPException(status_code=400, detail="Request is not reviewable")

    now = datetime.now(UTC)
    row.reviewed_by_user_id = user.id
    row.reviewed_at = now
    row.review_note = (payload.note or "").strip() or None

    if payload.action == "reject":
        row.status = "rejected"
        write_audit_log(
            db,
            action="finance.refund_reject",
            actor_user_id=user.id,
            resource_type="refund_request",
            resource_id=str(row.id),
            details={"note": row.review_note},
        )
        from app.email.service import enqueue_template
        from app.events.models import Event as EventModel
        from app.users.models import User as UserModel

        buyer = db.get(UserModel, row.buyer_user_id)
        event_row = db.get(EventModel, row.event_id)
        if buyer and buyer.email:
            enqueue_template(
                db,
                template="ticket_refund_update",
                to=buyer.email,
                recipient_user_id=buyer.id,
                dedupe_key=f"refund_request:{row.id}:rejected",
                context={
                    "event_title": event_row.title if event_row else "your order",
                    "refund_status": "rejected",
                },
            )
        if buyer is not None:
            from app.notifications.triggers import notify_buyer_ticket_refund

            notify_buyer_ticket_refund(
                db,
                buyer_user_id=buyer.id,
                event_title=event_row.title if event_row else "your order",
                refund_status="rejected",
                dedupe_key=f"refund_request:{row.id}:rejected:notif",
            )
        db.commit()
        db.refresh(row)
        return _serialize_refund_request(db, row)

    # Approve full refund
    order = db.scalar(
        select(Order)
        .where(Order.id == row.order_id)
        .options(selectinload(Order.payments), selectinload(Order.items))
        .with_for_update()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    tickets = _invalidate_tickets_for_refund(db, order)

    from app.merch.fulfillment import cancel_fulfillments_for_refunded_order

    cancel_fulfillments_for_refunded_order(
        db, order=order, actor_user_id=user.id
    )

    entry = debit_refund(
        db,
        host_id=row.host_id,
        amount=Decimal(row.requested_amount),
        currency=row.currency,
        refund_request_id=row.id,
        actor_user_id=user.id,
    )
    refund = Refund(
        refund_request_id=row.id,
        order_id=order.id,
        host_id=row.host_id,
        amount=row.requested_amount,
        currency=row.currency,
        status="completed",
        processed_by_user_id=user.id,
        ledger_entry_id=entry.id,
    )
    db.add(refund)
    db.flush()
    row.status = "completed"
    order.status = "refunded"
    for payment in order.payments:
        if payment.status == "successful":
            payment.status = "refunded"

    from app.finance.platform_ledger import record_platform_refund_entries

    record_platform_refund_entries(
        db,
        order=order,
        refund_id=refund.id,
        amount=Decimal(row.requested_amount),
        host_id=row.host_id,
        actor_user_id=user.id,
    )

    from app.promos.commission import reverse_ambassador_sale_for_order
    from app.promos.refund_allocations import (
        ReferralRefundAllocationError,
        apply_referral_reversals_for_finance_refund,
        parse_allocation_payloads,
    )

    order_total = Decimal(order.total_amount or 0)
    requested = Decimal(row.requested_amount or 0)
    is_full_refund = (
        getattr(row, "refund_type", "full") == "full"
        or requested >= order_total
    )

    raw_allocs = None
    if payload.line_allocations:
        raw_allocs = [a.model_dump(mode="json") for a in payload.line_allocations]
        row.line_allocations = raw_allocs
    elif getattr(row, "line_allocations", None):
        raw_allocs = list(row.line_allocations or [])

    try:
        allocations = parse_allocation_payloads(raw_allocs)
    except ReferralRefundAllocationError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": exc.detail},
        ) from exc

    try:
        _, needs_alloc = apply_referral_reversals_for_finance_refund(
            db,
            order=order,
            refund_id=refund.id,
            requested_amount=requested,
            reason="Order refunded",
            actor_user_id=user.id,
            allocations=allocations,
            is_full_refund=is_full_refund,
        )
    except ReferralRefundAllocationError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": exc.detail},
        ) from exc

    if needs_alloc:
        row.requires_referral_refund_allocation = True

    from app.promos.ledger_service import remaining_reversible_amount
    from app.promos.referral_ledger import ReferralCommissionEntry as RCE

    earns = list(
        db.scalars(
            select(RCE).where(
                RCE.order_id == order.id,
                RCE.entry_type == "earning",
            )
        ).all()
    )
    all_cleared = (
        all(remaining_reversible_amount(db, earning=e) <= 0 for e in earns)
        if earns
        else True
    )
    if is_full_refund or all_cleared:
        # Ledger already updated above — mark legacy dual-write sales only.
        reverse_ambassador_sale_for_order(
            db,
            order_id=order.id,
            reason="Order refunded",
            actor_user_id=user.id,
            source_event_id=f"finance-refund:{refund.id}:legacy-sale",
            skip_ledger=True,
        )

    from app.ambassadors.payment import reverse_conversions_for_order

    reverse_conversions_for_order(
        db,
        order_id=order.id,
        reason="Order refunded",
        actor_user_id=user.id,
    )

    write_audit_log(
        db,
        action="finance.refund_approve",
        actor_user_id=user.id,
        resource_type="refund_request",
        resource_id=str(row.id),
        details={
            "amount": str(row.requested_amount),
            "tickets_invalidated": len(tickets),
            "ledger_entry_id": str(entry.id),
            "line_allocations": raw_allocs,
            "is_full_refund": is_full_refund,
        },
    )

    from app.analytics.trusted import emit_refund_approved

    emit_refund_approved(
        db,
        refund_request_id=row.id,
        order_id=order.id,
        event_id=order.event_id,
        host_id=row.host_id,
        amount=row.requested_amount,
        currency=row.currency or "NGN",
        actor_user_id=user.id,
    )

    from app.email.service import enqueue_template
    from app.events.models import Event as EventModel
    from app.users.models import User as UserModel

    buyer = db.get(UserModel, row.buyer_user_id)
    event_row = db.get(EventModel, order.event_id)
    if buyer and buyer.email:
        enqueue_template(
            db,
            template="ticket_refund_update",
            to=buyer.email,
            recipient_user_id=buyer.id,
            dedupe_key=f"refund_request:{row.id}:completed",
            context={
                "event_title": event_row.title if event_row else "your order",
                "refund_status": "approved",
            },
        )
    if buyer is not None:
        from app.notifications.triggers import notify_buyer_ticket_refund

        notify_buyer_ticket_refund(
            db,
            buyer_user_id=buyer.id,
            event_title=event_row.title if event_row else "your order",
            refund_status="approved",
            dedupe_key=f"refund_request:{row.id}:completed:notif",
        )

    db.commit()
    db.refresh(row)
    return _serialize_refund_request(db, row)


def get_host_balance(db: Session, user: User) -> dict:
    host, _ = require_host_for_permission(
        db,
        user=user,
        host_id=None,
        permission=("finance.view_sales_summary", "finance.view_payouts"),
    )
    balance = get_or_create_host_balance(db, host.id)
    db.commit()
    return {
        "host_id": balance.host_id,
        "currency": balance.currency,
        "available_balance": balance.available_balance,
        "pending_payout_balance": balance.pending_payout_balance,
        "lifetime_earned": balance.lifetime_earned,
        "lifetime_refunded": balance.lifetime_refunded,
        "lifetime_paid_out": balance.lifetime_paid_out,
        "updated_at": balance.updated_at,
    }


def _serialize_payout(db: Session, row: PayoutRequest) -> dict:
    host = db.get(Host, row.host_id)
    evidence = db.scalar(
        select(PayoutEvidence).where(PayoutEvidence.payout_request_id == row.id)
    )
    return {
        "id": row.id,
        "host_id": row.host_id,
        "amount": row.amount,
        "currency": row.currency,
        "status": row.status,
        "recipient_bank_snapshot": row.recipient_bank_snapshot,
        "host_note": row.host_note,
        "review_note": row.review_note,
        "rejection_reason": row.rejection_reason,
        "requested_by_user_id": row.requested_by_user_id,
        "reviewed_by_user_id": row.reviewed_by_user_id,
        "reviewed_at": row.reviewed_at,
        "created_at": row.created_at,
        "host_display_name": host.display_name if host else None,
        "evidence": evidence,
    }


def create_payout_request(
    db: Session, *, user: User, payload: PayoutRequestCreate
) -> dict:
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="finance.manage_payouts"
    )
    amount = Decimal(payload.amount).quantize(Decimal("0.01"))
    balance = get_or_create_host_balance(db, host.id)
    if amount > balance.available_balance:
        raise HTTPException(status_code=400, detail="Amount exceeds available balance")

    bank = {
        "bank_name": payload.bank.bank_name.strip(),
        "account_name": payload.bank.account_name.strip(),
        "account_number": payload.bank.account_number.strip(),
    }
    row = PayoutRequest(
        host_id=host.id,
        amount=amount,
        currency=balance.currency,
        status="requested",
        recipient_bank_snapshot=bank,
        host_note=(payload.note or "").strip() or None,
        requested_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    hold_payout(
        db,
        host_id=host.id,
        amount=amount,
        currency=balance.currency,
        payout_request_id=row.id,
        actor_user_id=user.id,
    )
    write_audit_log(
        db,
        action="finance.payout_request",
        actor_user_id=user.id,
        resource_type="payout_request",
        resource_id=str(row.id),
        details={"amount": str(amount)},
    )
    db.commit()
    db.refresh(row)
    return _serialize_payout(db, row)


def list_host_payouts(db: Session, user: User) -> list[dict]:
    host, _ = require_host_for_permission(
        db, user=user, host_id=None, permission="finance.view_payouts"
    )
    rows = db.scalars(
        select(PayoutRequest)
        .where(PayoutRequest.host_id == host.id)
        .order_by(PayoutRequest.created_at.desc())
    ).all()
    return [_serialize_payout(db, r) for r in rows]


def list_payouts_for_admin(
    db: Session, user: User, *, status_filter: str | None = None
) -> list[dict]:
    if not can_review_payouts(user) and not is_super_admin(user):
        # Support: allow view-only list if they somehow hit admin UI — deny mutations elsewhere
        if user_has_role(user, "support_agent"):
            raise HTTPException(
                status_code=403,
                detail="Support cannot manage payouts",
            )
        raise HTTPException(status_code=403, detail="Insufficient permission")
    q = select(PayoutRequest).order_by(PayoutRequest.created_at.desc())
    if status_filter:
        q = q.where(PayoutRequest.status == status_filter)
    return [_serialize_payout(db, r) for r in db.scalars(q).all()]


def review_payout_request(
    db: Session, *, user: User, payout_id: UUID, payload: PayoutReview
) -> dict:
    if not can_review_payouts(user):
        raise HTTPException(
            status_code=403,
            detail="Support agents cannot review or complete payouts",
        )
    row = db.get(PayoutRequest, payout_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Payout request not found")
    if row.status == "paid":
        raise HTTPException(status_code=400, detail="Paid payouts cannot be changed")
    if row.status in {"cancelled", "rejected"} and payload.action != "under_review":
        raise HTTPException(status_code=400, detail="Payout is closed")

    now = datetime.now(UTC)
    row.reviewed_by_user_id = user.id
    row.reviewed_at = now
    row.review_note = (payload.note or "").strip() or None

    if payload.action == "under_review":
        if row.status not in {"requested", "under_review", "approved"}:
            raise HTTPException(status_code=400, detail="Invalid status transition")
        row.status = "under_review"
        action = "finance.payout_under_review"
    elif payload.action == "approve":
        if row.status not in {"requested", "under_review"}:
            raise HTTPException(status_code=400, detail="Invalid status transition")
        row.status = "approved"
        action = "finance.payout_approve"
    else:
        if row.status not in {"requested", "under_review", "approved"}:
            raise HTTPException(status_code=400, detail="Invalid status transition")
        release_payout_hold(
            db,
            host_id=row.host_id,
            amount=Decimal(row.amount),
            currency=row.currency,
            payout_request_id=row.id,
            actor_user_id=user.id,
        )
        row.status = "rejected"
        row.rejection_reason = row.review_note or "Rejected"
        action = "finance.payout_reject"

    write_audit_log(
        db,
        action=action,
        actor_user_id=user.id,
        resource_type="payout_request",
        resource_id=str(row.id),
        details={"status": row.status, "note": row.review_note},
    )
    db.commit()
    db.refresh(row)
    return _serialize_payout(db, row)


def mark_payout_paid(
    db: Session, *, user: User, payout_id: UUID, payload: PayoutMarkPaid
) -> dict:
    if not is_super_admin(user):
        raise HTTPException(
            status_code=403,
            detail="Only super admins can mark payouts as paid",
        )
    if not payload.bank_transfer_reference.strip() or not payload.evidence_file_url.strip():
        raise HTTPException(
            status_code=400,
            detail="Bank transfer reference and evidence file URL are required",
        )

    row = db.get(PayoutRequest, payout_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Payout request not found")
    if row.status == "paid":
        raise HTTPException(status_code=400, detail="Payout already marked paid")
    if row.status != "approved":
        raise HTTPException(
            status_code=400,
            detail="Payout must be approved before it can be marked paid",
        )

    existing = db.scalar(
        select(PayoutEvidence).where(PayoutEvidence.payout_request_id == row.id)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Evidence already recorded")

    paid_at = payload.paid_at or datetime.now(UTC)
    if paid_at.tzinfo is None:
        paid_at = paid_at.replace(tzinfo=UTC)

    evidence = PayoutEvidence(
        payout_request_id=row.id,
        bank_transfer_reference=payload.bank_transfer_reference.strip(),
        evidence_file_url=payload.evidence_file_url.strip(),
        admin_note=(payload.admin_note or "").strip() or None,
        paid_at=paid_at,
        paid_by_user_id=user.id,
        recipient_bank_snapshot=dict(row.recipient_bank_snapshot),
    )
    db.add(evidence)
    complete_payout(
        db,
        host_id=row.host_id,
        amount=Decimal(row.amount),
        currency=row.currency,
        payout_request_id=row.id,
        actor_user_id=user.id,
    )
    from app.finance.platform_ledger import record_platform_payout_entry

    record_platform_payout_entry(
        db,
        payout_request_id=row.id,
        host_id=row.host_id,
        amount=Decimal(row.amount),
        currency=row.currency or "NGN",
        actor_user_id=user.id,
    )
    row.status = "paid"
    row.reviewed_by_user_id = user.id
    row.reviewed_at = datetime.now(UTC)

    write_audit_log(
        db,
        action="finance.payout_mark_paid",
        actor_user_id=user.id,
        resource_type="payout_request",
        resource_id=str(row.id),
        details={
            "bank_transfer_reference": evidence.bank_transfer_reference,
            "evidence_file_url": evidence.evidence_file_url,
            "paid_at": paid_at.isoformat(),
            "amount": str(row.amount),
        },
    )

    from app.analytics.trusted import emit_payout_completed

    emit_payout_completed(
        db,
        payout_request_id=row.id,
        host_id=row.host_id,
        amount=row.amount,
        currency=row.currency or "NGN",
        actor_user_id=user.id,
    )

    db.commit()
    db.refresh(row)
    return _serialize_payout(db, row)


def _has_platform_finance_access(user: User) -> bool:
    """Platform finance surfaces — not host-scoped ``payments.view``."""
    return (
        user_has_permission(user, "admin.full_access")
        or user_has_permission(user, "admin.finance.view_fees")
        or user_has_permission(user, "admin.finance.export_event_sales")
        or user_has_permission(user, "refunds.review")
    )


def list_ledger_entries(
    db: Session,
    user: User,
    *,
    host_id: UUID | None = None,
    limit: int = 100,
) -> list[LedgerEntry]:
    if not _has_platform_finance_access(user):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    if user_has_role(user, "support_agent") and not (
        user_has_role(user, "finance_admin") or is_super_admin(user)
    ):
        raise HTTPException(
            status_code=403, detail="Support cannot access the financial ledger"
        )
    q = select(LedgerEntry).order_by(LedgerEntry.created_at.desc()).limit(min(limit, 500))
    if host_id is not None:
        q = q.where(LedgerEntry.host_id == host_id)
    return list(db.scalars(q).all())


def list_host_ledger(db: Session, user: User, *, limit: int = 100) -> list[LedgerEntry]:
    host, _ = require_host_for_permission(
        db,
        user=user,
        host_id=None,
        permission=("finance.view_sales_summary", "finance.view_payouts"),
    )
    return list(
        db.scalars(
            select(LedgerEntry)
            .where(LedgerEntry.host_id == host.id)
            .order_by(LedgerEntry.created_at.desc())
            .limit(min(limit, 200))
        )
    )


def settlement_report(db: Session, user: User, *, host_id: UUID | None = None) -> dict:
    if not _has_platform_finance_access(user):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    if user_has_role(user, "support_agent") and not (
        user_has_role(user, "finance_admin") or is_super_admin(user)
    ):
        raise HTTPException(
            status_code=403, detail="Support cannot access settlement reports"
        )

    if host_id is not None:
        balance = get_or_create_host_balance(db, host_id)
        open_refunds = db.scalar(
            select(func.count())
            .select_from(RefundRequest)
            .where(
                RefundRequest.host_id == host_id,
                RefundRequest.status.in_(["requested", "under_review"]),
            )
        ) or 0
        open_payouts = db.scalar(
            select(func.count())
            .select_from(PayoutRequest)
            .where(
                PayoutRequest.host_id == host_id,
                PayoutRequest.status.in_(
                    ["requested", "under_review", "approved"]
                ),
            )
        ) or 0
        ledger_count = db.scalar(
            select(func.count())
            .select_from(LedgerEntry)
            .where(LedgerEntry.host_id == host_id)
        ) or 0
        db.commit()
        return {
            "host_id": host_id,
            "currency": balance.currency,
            "total_earned": balance.lifetime_earned,
            "total_refunded": balance.lifetime_refunded,
            "total_paid_out": balance.lifetime_paid_out,
            "available_balance": balance.available_balance,
            "pending_payout_balance": balance.pending_payout_balance,
            "open_refund_requests": int(open_refunds),
            "open_payout_requests": int(open_payouts),
            "ledger_entry_count": int(ledger_count),
        }

    balances = list(db.scalars(select(HostBalance)).all())
    total_earned = sum((b.lifetime_earned for b in balances), Decimal("0"))
    total_refunded = sum((b.lifetime_refunded for b in balances), Decimal("0"))
    total_paid = sum((b.lifetime_paid_out for b in balances), Decimal("0"))
    available = sum((b.available_balance for b in balances), Decimal("0"))
    pending = sum((b.pending_payout_balance for b in balances), Decimal("0"))
    open_refunds = db.scalar(
        select(func.count())
        .select_from(RefundRequest)
        .where(RefundRequest.status.in_(["requested", "under_review"]))
    ) or 0
    open_payouts = db.scalar(
        select(func.count())
        .select_from(PayoutRequest)
        .where(PayoutRequest.status.in_(["requested", "under_review", "approved"]))
    ) or 0
    ledger_count = db.scalar(select(func.count()).select_from(LedgerEntry)) or 0
    return {
        "host_id": None,
        "currency": "NGN",
        "total_earned": total_earned,
        "total_refunded": total_refunded,
        "total_paid_out": total_paid,
        "available_balance": available,
        "pending_payout_balance": pending,
        "open_refund_requests": int(open_refunds),
        "open_payout_requests": int(open_payouts),
        "ledger_entry_count": int(ledger_count),
    }
