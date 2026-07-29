"""Refunds, balances, ledger, and payout finance tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.finance.models import HostBalance, LedgerEntry, PayoutEvidence, Refund
from app.finance.service import record_sale_credit_for_order
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem, Payment
from app.tickets.models import Ticket, TicketQrToken
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name


def _register(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name, "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_paid_order(db: Session) -> tuple[Host, User, User, Order, Ticket]:
    host_user = User(
        email="fin-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Finance Host",
        is_active=True,
    )
    host_role = get_role_by_name(db, "host")
    assert host_role is not None
    host_user.roles.append(host_role)
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Finance Host",
        slug="finance-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Finance host"))

    buyer = User(
        email="fin-buyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Finance Buyer",
        is_active=True,
    )
    buyer_role = get_role_by_name(db, "buyer")
    assert buyer_role is not None
    buyer.roles.append(buyer_role)
    db.add(buyer)
    db.flush()

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=14)
    event = Event(
        title="Finance Event",
        slug="finance-event",
        description="Event used for finance refund and payout tests with detail.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        city="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
        refund_policy="admin_controlled",
    )
    db.add(event)
    db.flush()
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("10000.00"),
        quantity=100,
        quantity_sold=1,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=4,
        visibility="public",
        status="active",
    )
    db.add(tt)
    db.flush()
    order = Order(
        reference="PDY-FINANCE01",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("10000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("10000.00"),
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        paid_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    item = OrderItem(
        order_id=order.id,
        ticket_type_id=tt.id,
        quantity=1,
        unit_price=Decimal("10000.00"),
        line_total=Decimal("10000.00"),
        ticket_type_name=tt.name,
    )
    db.add(item)
    db.flush()
    db.add(
        Payment(
            order_id=order.id,
            provider="paystack",
            reference="PDY-FINANCE01",
            amount=Decimal("10000.00"),
            currency="NGN",
            status="successful",
            paid_at=datetime.now(UTC),
        )
    )
    ticket = Ticket(
        public_code=new_public_ticket_code(),
        order_id=order.id,
        order_item_id=item.id,
        event_id=event.id,
        ticket_type_id=tt.id,
        buyer_user_id=buyer.id,
        status="active",
        ticket_type_name=tt.name,
        holder_name=buyer.full_name,
        holder_email=buyer.email,
    )
    db.add(ticket)
    db.flush()
    db.add(
        TicketQrToken(
            ticket_id=ticket.id,
            jti_hash="a" * 64,
            signed_payload="signed",
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
    )
    record_sale_credit_for_order(db, order)
    db.commit()
    return host, host_user, buyer, order, ticket


def test_refund_request_and_approval_invalidates_ticket(
    client: TestClient, db_session: Session, assign_role
):
    host, _, buyer, order, ticket = _seed_paid_order(db_session)
    buyer_headers = _login(client, buyer.email)

    created = client.post(
        "/api/v1/finance/refunds/requests",
        headers=buyer_headers,
        json={"order_id": str(order.id), "reason": "Cannot attend the event anymore"},
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]
    assert created.json()["status"] == "requested"

    # Partial not supported
    partial = client.post(
        "/api/v1/finance/refunds/requests",
        headers=buyer_headers,
        json={
            "order_id": str(order.id),
            "reason": "Want half back please now",
            "refund_type": "partial",
            "amount": "5000.00",
        },
    )
    assert partial.status_code in {400, 409}

    _register(client, "fin-admin@example.com", "Fin Admin")
    assign_role("fin-admin@example.com", "finance_admin")
    admin_headers = _login(client, "fin-admin@example.com")

    approved = client.post(
        f"/api/v1/finance/refunds/requests/{request_id}/review",
        headers=admin_headers,
        json={"action": "approve", "note": "Full refund granted"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "completed"

    db_session.refresh(ticket)
    assert ticket.status == "refunded"
    qr = db_session.query(TicketQrToken).filter_by(ticket_id=ticket.id).one()
    assert qr.revoked_at is not None

    db_session.refresh(order)
    assert order.status == "refunded"
    assert db_session.query(Refund).count() == 1

    balance = db_session.query(HostBalance).filter_by(host_id=host.id).one()
    assert balance.available_balance == Decimal("0.00")
    assert balance.lifetime_refunded == Decimal("10000.00")


def test_host_balance_update_on_sale(client: TestClient, db_session: Session):
    host, host_user, _, order, _ = _seed_paid_order(db_session)
    headers = _login(client, host_user.email)
    bal = client.get("/api/v1/finance/host/balance", headers=headers)
    assert bal.status_code == 200, bal.text
    assert Decimal(bal.json()["available_balance"]) == Decimal("10000.00")
    assert Decimal(bal.json()["lifetime_earned"]) == Decimal("10000.00")
    assert (
        db_session.query(LedgerEntry)
        .filter_by(host_id=host.id, entry_type="sale_credit", reference_id=str(order.id))
        .count()
        == 1
    )


def test_payout_request_approve_and_mark_paid_with_evidence(
    client: TestClient, db_session: Session, assign_role
):
    host, host_user, _, _, _ = _seed_paid_order(db_session)
    host_headers = _login(client, host_user.email)

    requested = client.post(
        "/api/v1/finance/host/payouts",
        headers=host_headers,
        json={
            "amount": "4000.00",
            "bank": {
                "bank_name": "Test Bank",
                "account_name": "Finance Host",
                "account_number": "0123456789",
            },
            "note": "Week 1 settlement",
        },
    )
    assert requested.status_code == 201, requested.text
    payout_id = requested.json()["id"]
    assert requested.json()["status"] == "requested"

    balance = db_session.query(HostBalance).filter_by(host_id=host.id).one()
    db_session.refresh(balance)
    assert balance.available_balance == Decimal("6000.00")
    assert balance.pending_payout_balance == Decimal("4000.00")

    _register(client, "fin-review@example.com", "Fin Review")
    assign_role("fin-review@example.com", "finance_admin")
    finance_headers = _login(client, "fin-review@example.com")

    # Finance cannot mark paid
    denied_paid = client.post(
        f"/api/v1/finance/admin/payouts/{payout_id}/mark-paid",
        headers=finance_headers,
        json={
            "bank_transfer_reference": "TRX-1",
            "evidence_file_url": "https://example.com/proof.png",
        },
    )
    assert denied_paid.status_code == 403

    approved = client.post(
        f"/api/v1/finance/admin/payouts/{payout_id}/review",
        headers=finance_headers,
        json={"action": "approve", "note": "Looks good"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    _register(client, "super-fin@example.com", "Super")
    assign_role("super-fin@example.com", "super_admin")
    super_headers = _login(client, "super-fin@example.com")

    # Evidence required
    missing = client.post(
        f"/api/v1/finance/admin/payouts/{payout_id}/mark-paid",
        headers=super_headers,
        json={"bank_transfer_reference": "", "evidence_file_url": ""},
    )
    assert missing.status_code == 422 or missing.status_code == 400

    paid = client.post(
        f"/api/v1/finance/admin/payouts/{payout_id}/mark-paid",
        headers=super_headers,
        json={
            "bank_transfer_reference": "TRX-998877",
            "evidence_file_url": "https://cdn.example.com/payout-proof.pdf",
            "admin_note": "Sent via bank transfer",
        },
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "paid"
    assert paid.json()["evidence"]["bank_transfer_reference"] == "TRX-998877"

    db_session.refresh(balance)
    assert balance.pending_payout_balance == Decimal("0.00")
    assert balance.lifetime_paid_out == Decimal("4000.00")
    assert db_session.query(PayoutEvidence).count() == 1

    # Cannot reverse casually
    again = client.post(
        f"/api/v1/finance/admin/payouts/{payout_id}/mark-paid",
        headers=super_headers,
        json={
            "bank_transfer_reference": "TRX-2",
            "evidence_file_url": "https://cdn.example.com/payout-proof2.pdf",
        },
    )
    assert again.status_code == 400


def test_reject_payout_releases_hold(
    client: TestClient, db_session: Session, assign_role
):
    host, host_user, _, _, _ = _seed_paid_order(db_session)
    host_headers = _login(client, host_user.email)
    created = client.post(
        "/api/v1/finance/host/payouts",
        headers=host_headers,
        json={
            "amount": "2500.00",
            "bank": {
                "bank_name": "Test Bank",
                "account_name": "Finance Host",
                "account_number": "0123456789",
            },
        },
    )
    payout_id = created.json()["id"]

    _register(client, "fin-reject@example.com", "Fin Reject")
    assign_role("fin-reject@example.com", "finance_admin")
    finance_headers = _login(client, "fin-reject@example.com")

    rejected = client.post(
        f"/api/v1/finance/admin/payouts/{payout_id}/review",
        headers=finance_headers,
        json={"action": "reject", "note": "Incomplete bank details"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    balance = db_session.query(HostBalance).filter_by(host_id=host.id).one()
    db_session.refresh(balance)
    assert balance.available_balance == Decimal("10000.00")
    assert balance.pending_payout_balance == Decimal("0.00")


def test_support_permission_restrictions(
    client: TestClient, db_session: Session, assign_role
):
    _, _, buyer, order, _ = _seed_paid_order(db_session)
    buyer_headers = _login(client, buyer.email)
    created = client.post(
        "/api/v1/finance/refunds/requests",
        headers=buyer_headers,
        json={"order_id": str(order.id), "reason": "Need help with a refund please"},
    )
    request_id = created.json()["id"]

    _register(client, "support-fin@example.com", "Support")
    assign_role("support-fin@example.com", "support_agent")
    support_headers = _login(client, "support-fin@example.com")

    # Can view / escalate
    listing = client.get("/api/v1/finance/refunds/requests", headers=support_headers)
    assert listing.status_code == 200
    assert len(listing.json()) >= 1

    escalated = client.post(
        f"/api/v1/finance/refunds/requests/{request_id}/escalate",
        headers=support_headers,
        json={"note": "Buyer called; escalating to finance"},
    )
    assert escalated.status_code == 200
    assert escalated.json()["status"] == "under_review"

    # Cannot approve refund
    approve = client.post(
        f"/api/v1/finance/refunds/requests/{request_id}/review",
        headers=support_headers,
        json={"action": "approve"},
    )
    assert approve.status_code == 403

    # Cannot list/manage payouts or ledger
    payouts = client.get("/api/v1/finance/admin/payouts", headers=support_headers)
    assert payouts.status_code == 403
    ledger = client.get("/api/v1/finance/admin/ledger", headers=support_headers)
    assert ledger.status_code == 403
    settlement = client.get("/api/v1/finance/admin/settlement", headers=support_headers)
    assert settlement.status_code == 403
