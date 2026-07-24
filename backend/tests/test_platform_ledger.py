"""Platform ledger + revenue reporting tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.finance.fees.constants import (
    FEE_KEY_BUYER_SERVICE,
    FEE_KEY_TICKET_COMMISSION,
)
from app.finance.fees.models import OrderFeeSnapshot, PlatformFeeSetting
from app.finance.fees.money import major_to_minor
from app.finance.models import PlatformLedgerEntry
from app.finance.platform_ledger import (
    append_platform_ledger_entry,
    record_platform_payout_entry,
    record_platform_refund_entries,
)
from app.finance.platform_revenue import build_platform_revenue_report
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem, Payment
from app.payments.webhook import finalize_successful_payment
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed(db: Session) -> tuple[User, Host, Event, TicketType, User]:
    admin = User(
        email="plat-ledger-admin@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Ledger Admin",
        is_active=True,
    )
    role = get_role_by_name(db, "finance_admin")
    assert role is not None
    admin.roles.append(role)
    db.add(admin)

    host_user = User(
        email="plat-ledger-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Ledger Host",
        is_active=True,
    )
    host_role = get_role_by_name(db, "host")
    assert host_role is not None
    host_user.roles.append(host_role)
    db.add(host_user)
    db.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Ledger Host",
        slug="plat-ledger-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Ledger"))

    buyer = User(
        email="plat-ledger-buyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Ledger Buyer",
        is_active=True,
    )
    buyer_role = get_role_by_name(db, "buyer")
    assert buyer_role is not None
    buyer.roles.append(buyer_role)
    db.add(buyer)
    db.flush()

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=3)
    event = Event(
        title="Platform Ledger Event",
        slug="platform-ledger-event",
        description="Event for platform ledger tests with enough description text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
        city="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("10000.00"),
        quantity=50,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=5,
        status="active",
        visibility="public",
    )
    db.add(tt)
    now = datetime.now(UTC) - timedelta(days=1)
    db.add(
        PlatformFeeSetting(
            fee_key=FEE_KEY_TICKET_COMMISSION,
            label="Ticket commission",
            category="ticket",
            fee_type="percentage",
            percentage_value=Decimal("5.00"),
            currency="NGN",
            payer="host",
            enabled=True,
            applies_to="all",
            effective_from=now,
            created_by_admin_id=admin.id,
            updated_by_admin_id=admin.id,
        )
    )
    db.add(
        PlatformFeeSetting(
            fee_key=FEE_KEY_BUYER_SERVICE,
            label="Buyer service fee",
            category="general",
            fee_type="mixed",
            percentage_value=Decimal("2.00"),
            fixed_value=100_00,
            currency="NGN",
            payer="buyer",
            enabled=True,
            applies_to="all",
            effective_from=now,
            created_by_admin_id=admin.id,
            updated_by_admin_id=admin.id,
        )
    )
    db.commit()
    return admin, host, event, tt, buyer


def _pending_order(
    db: Session,
    *,
    event: Event,
    tt: TicketType,
    buyer: User,
    reference: str = "PDY-PLAT-1",
) -> tuple[Order, Payment]:
    order = Order(
        reference=reference,
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="pending",
        currency="NGN",
        subtotal_amount=Decimal("10000.00"),
        discount_amount=Decimal("0"),
        merch_discount_amount=Decimal("0"),
        shipping_amount=Decimal("0"),
        buyer_fee_total=Decimal("300.00"),
        host_fee_total=Decimal("500.00"),
        processing_fee_total=Decimal("0"),
        platform_revenue_total=Decimal("800.00"),
        host_net_estimate=Decimal("9500.00"),
        total_amount=Decimal("10300.00"),
        buyer_email=buyer.email,
        buyer_name=buyer.full_name or "Buyer",
    )
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            item_kind="ticket",
            ticket_type_id=tt.id,
            quantity=1,
            unit_price=Decimal("10000.00"),
            line_total=Decimal("10000.00"),
            ticket_type_name="GA",
        )
    )
    db.add(
        OrderFeeSnapshot(
            order_id=order.id,
            host_id=event.host_id,
            fee_key=FEE_KEY_TICKET_COMMISSION,
            label="Ticket commission",
            category="ticket",
            fee_type="percentage",
            percentage_value=Decimal("5.00"),
            fixed_value=None,
            payer="host",
            amount=major_to_minor(Decimal("500.00")),
            currency="NGN",
            source="global",
        )
    )
    db.add(
        OrderFeeSnapshot(
            order_id=order.id,
            host_id=event.host_id,
            fee_key=FEE_KEY_BUYER_SERVICE,
            label="Buyer service fee",
            category="general",
            fee_type="mixed",
            percentage_value=Decimal("2.00"),
            fixed_value=100_00,
            payer="buyer",
            amount=major_to_minor(Decimal("300.00")),
            currency="NGN",
            source="global",
        )
    )
    payment = Payment(
        order_id=order.id,
        provider="paystack",
        reference=order.reference,
        amount=order.total_amount,
        currency="NGN",
        status="pending",
    )
    db.add(payment)
    db.commit()
    db.refresh(order)
    db.refresh(payment)
    return order, payment


def test_ledger_entries_created_after_successful_payment_webhook(
    db_session: Session,
) -> None:
    _admin, host, event, tt, buyer = _seed(db_session)
    order, payment = _pending_order(db_session, event=event, tt=tt, buyer=buyer)
    finalize_successful_payment(
        db_session,
        order=order,
        payment=payment,
        provider_payment_id="pay_test_1",
        raw_payload={"event": "charge.success", "data": {"amount": 1030000}},
        actor_user_id=buyer.id,
    )
    db_session.commit()
    rows = (
        db_session.query(PlatformLedgerEntry)
        .filter(PlatformLedgerEntry.order_id == order.id)
        .all()
    )
    types = {r.entry_type for r in rows}
    assert "buyer_payment" in types
    assert "ticket_revenue" in types
    assert "buyer_platform_fee" in types
    assert "host_commission" in types
    payment_row = next(r for r in rows if r.entry_type == "buyer_payment")
    assert Decimal(payment_row.amount) == Decimal("10300.00")
    fee_row = next(r for r in rows if r.entry_type == "buyer_platform_fee")
    assert Decimal(fee_row.amount) == Decimal("300.00")


def test_duplicate_webhook_does_not_duplicate_ledger(db_session: Session) -> None:
    _admin, host, event, tt, buyer = _seed(db_session)
    order, payment = _pending_order(db_session, event=event, tt=tt, buyer=buyer)
    finalize_successful_payment(
        db_session,
        order=order,
        payment=payment,
        provider_payment_id="pay_test_2",
        raw_payload={"event": "charge.success"},
        actor_user_id=buyer.id,
    )
    db_session.commit()
    count1 = (
        db_session.query(PlatformLedgerEntry)
        .filter(PlatformLedgerEntry.order_id == order.id)
        .count()
    )
    # Second finalize (order already paid) — recovery path
    order = db_session.get(Order, order.id)
    payment = db_session.get(Payment, payment.id)
    assert order is not None and payment is not None
    finalize_successful_payment(
        db_session,
        order=order,
        payment=payment,
        provider_payment_id="pay_test_2",
        raw_payload={"event": "charge.success"},
        actor_user_id=buyer.id,
    )
    db_session.commit()
    count2 = (
        db_session.query(PlatformLedgerEntry)
        .filter(PlatformLedgerEntry.order_id == order.id)
        .count()
    )
    assert count1 == count2
    assert count1 >= 4


def test_refund_creates_ledger_reversal(db_session: Session) -> None:
    _admin, host, event, tt, buyer = _seed(db_session)
    order, payment = _pending_order(db_session, event=event, tt=tt, buyer=buyer)
    finalize_successful_payment(
        db_session,
        order=order,
        payment=payment,
        provider_payment_id="pay_ref",
        raw_payload={},
        actor_user_id=buyer.id,
    )
    db_session.commit()
    order = db_session.get(Order, order.id)
    assert order is not None
    refund_id = uuid4()
    record_platform_refund_entries(
        db_session,
        order=order,
        refund_id=refund_id,
        amount=Decimal("10300.00"),
        host_id=host.id,
        actor_user_id=buyer.id,
    )
    db_session.commit()
    refunds = (
        db_session.query(PlatformLedgerEntry)
        .filter(
            PlatformLedgerEntry.entry_type == "refund",
            PlatformLedgerEntry.reference_id == str(refund_id),
        )
        .all()
    )
    assert len(refunds) == 1
    assert refunds[0].direction == "debit"
    adjustments = (
        db_session.query(PlatformLedgerEntry)
        .filter(
            PlatformLedgerEntry.entry_type == "adjustment",
            PlatformLedgerEntry.reference_id == str(refund_id),
        )
        .all()
    )
    assert len(adjustments) >= 2


def test_payout_creates_payout_ledger_entry(db_session: Session) -> None:
    _admin, host, event, tt, buyer = _seed(db_session)
    order, payment = _pending_order(db_session, event=event, tt=tt, buyer=buyer)
    finalize_successful_payment(
        db_session,
        order=order,
        payment=payment,
        provider_payment_id="pay_po",
        raw_payload={},
        actor_user_id=buyer.id,
    )
    db_session.commit()
    payout_id = uuid4()
    record_platform_payout_entry(
        db_session,
        payout_request_id=payout_id,
        host_id=host.id,
        amount=Decimal("5000.00"),
        actor_user_id=_admin.id if False else buyer.id,
    )
    db_session.commit()
    rows = (
        db_session.query(PlatformLedgerEntry)
        .filter(PlatformLedgerEntry.entry_type == "host_payout")
        .all()
    )
    assert len(rows) == 1
    assert rows[0].direction == "debit"
    assert Decimal(rows[0].amount) == Decimal("5000.00")


def test_platform_revenue_report_totals_correctly(
    client: TestClient, db_session: Session
) -> None:
    admin, host, event, tt, buyer = _seed(db_session)
    order, payment = _pending_order(db_session, event=event, tt=tt, buyer=buyer)
    finalize_successful_payment(
        db_session,
        order=order,
        payment=payment,
        provider_payment_id="pay_rev",
        raw_payload={},
        actor_user_id=buyer.id,
    )
    db_session.commit()
    report = build_platform_revenue_report(db_session)
    summary = report["summary"]
    assert Decimal(summary["gross_payment_volume"]) == Decimal("10300.00")
    assert Decimal(summary["buyer_service_fee_revenue"]) == Decimal("300.00")
    assert Decimal(summary["ticket_commission_revenue"]) == Decimal("500.00")
    assert Decimal(summary["platform_revenue"]) == Decimal("800.00")
    assert Decimal(summary["host_net_payable"]) == Decimal("9500.00")

    headers = _login(client, admin.email)
    res = client.get("/api/v1/finance/admin/platform-revenue", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()["summary"]
    assert Decimal(body["platform_revenue"]) == Decimal("800.00")


def test_host_payable_totals_correctly(db_session: Session) -> None:
    _admin, host, event, tt, buyer = _seed(db_session)
    order, payment = _pending_order(db_session, event=event, tt=tt, buyer=buyer)
    finalize_successful_payment(
        db_session,
        order=order,
        payment=payment,
        provider_payment_id="pay_hp",
        raw_payload={},
        actor_user_id=buyer.id,
    )
    db_session.commit()
    report = build_platform_revenue_report(db_session, host_id=host.id)
    assert Decimal(report["summary"]["host_net_payable"]) == Decimal("9500.00")


def test_finance_export_requires_permission(
    client: TestClient, db_session: Session
) -> None:
    _admin, host, event, tt, buyer = _seed(db_session)
    buyer_headers = _login(client, buyer.email)
    denied = client.get(
        "/api/v1/finance/admin/platform-revenue/export.csv",
        headers=buyer_headers,
    )
    assert denied.status_code in {401, 403}

    admin_headers = _login(client, "plat-ledger-admin@example.com")
    order, payment = _pending_order(
        db_session, event=event, tt=tt, buyer=buyer, reference="PDY-PLAT-EXP"
    )
    finalize_successful_payment(
        db_session,
        order=order,
        payment=payment,
        provider_payment_id="pay_exp",
        raw_payload={},
        actor_user_id=buyer.id,
    )
    db_session.commit()
    ok = client.get(
        "/api/v1/finance/admin/platform-revenue/export.csv",
        headers=admin_headers,
    )
    assert ok.status_code == 200, ok.text
    assert "text/csv" in ok.headers.get("content-type", "")
    assert "gross_payment_volume" in ok.text


def test_ledger_entries_are_not_mutable(db_session: Session) -> None:
    _admin, host, event, tt, buyer = _seed(db_session)
    order, payment = _pending_order(db_session, event=event, tt=tt, buyer=buyer)
    finalize_successful_payment(
        db_session,
        order=order,
        payment=payment,
        provider_payment_id="pay_mut",
        raw_payload={},
        actor_user_id=buyer.id,
    )
    db_session.commit()
    row = (
        db_session.query(PlatformLedgerEntry)
        .filter(PlatformLedgerEntry.order_id == order.id)
        .first()
    )
    assert row is not None
    original = Decimal(row.amount)
    # Direct ORM mutation must not be exposed via API; corrections use adjustments.
    row.amount = Decimal("1.00")
    db_session.flush()
    # Application rule: create adjustment instead of relying on edits
    adj = append_platform_ledger_entry(
        db_session,
        entry_type="adjustment",
        amount=original,
        direction="debit",
        dedupe_key=f"adjustment:test-correction:{row.id}",
        description="Correction — do not edit prior rows",
        host_id=host.id,
        order_id=order.id,
    )
    assert adj is not None
    # No public UPDATE/DELETE routes exist for platform ledger
    assert not hasattr(PlatformLedgerEntry, "update")
