"""Host / admin earnings reports — gross, deductions, net after fees."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.finance.earnings_service import build_host_earnings_report, earnings_report_csv
from app.finance.fees.constants import (
    FEE_KEY_BUYER_SERVICE,
    FEE_KEY_TICKET_COMMISSION,
)
from app.finance.fees.models import HostFeeOverride, PlatformFeeSetting
from app.finance.ledger import debit_refund
from app.finance.models import Refund, RefundRequest
from app.finance.service import record_sale_credit_for_order
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem, Payment
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed(db: Session) -> tuple[User, Host, Event, TicketType, User, User]:
    admin = User(
        email="earn-admin@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Earn Admin",
        is_active=True,
    )
    admin_role = get_role_by_name(db, "finance_admin")
    assert admin_role is not None
    admin.roles.append(admin_role)
    db.add(admin)

    host_user = User(
        email="earn-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Earn Host",
        is_active=True,
    )
    host_role = get_role_by_name(db, "host")
    assert host_role is not None
    host_user.roles.append(host_role)
    db.add(host_user)
    db.flush()

    other_host_user = User(
        email="earn-other-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Other Host",
        is_active=True,
    )
    other_host_user.roles.append(host_role)
    db.add(other_host_user)
    db.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Earn Host",
        slug="earn-host",
        status="active",
    )
    other_host = Host(
        user_id=other_host_user.id,
        display_name="Other Host",
        slug="earn-other-host",
        status="active",
    )
    db.add(host)
    db.add(other_host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Earn"))
    db.add(HostProfile(host_id=other_host.id, bio="Other"))

    buyer = User(
        email="earn-buyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Earn Buyer",
        is_active=True,
    )
    buyer_role = get_role_by_name(db, "buyer")
    assert buyer_role is not None
    buyer.roles.append(buyer_role)
    db.add(buyer)
    db.flush()

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=5)
    event = Event(
        title="Earnings Event",
        slug="earnings-event",
        description="Event used for host earnings report tests with enough text.",
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
        quantity=100,
        quantity_sold=1,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=10,
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
            fixed_value=None,
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
    return admin, host, event, tt, buyer, other_host_user


def _paid_order(
    db: Session,
    *,
    host: Host,
    event: Event,
    tt: TicketType,
    buyer: User,
    reference: str = "PDY-EARN-1",
) -> Order:
    # Subtotal 10000; discount 0; buyer fee 300; host fee 500; host net 9500; total 10300
    order = Order(
        reference=reference,
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
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
        paid_at=datetime.now(UTC),
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
        Payment(
            order_id=order.id,
            provider="paystack",
            reference=order.reference,
            amount=order.total_amount,
            currency="NGN",
            status="successful",
        )
    )
    db.commit()
    record_sale_credit_for_order(db, order)
    db.commit()
    return order


def test_host_earnings_show_gross_and_net(
    client: TestClient, db_session: Session
) -> None:
    _admin, host, event, tt, buyer, _other = _seed(db_session)
    _paid_order(db_session, host=host, event=event, tt=tt, buyer=buyer)
    headers = _login(client, "earn-host@example.com")
    res = client.get("/api/v1/finance/host/earnings", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    summary = body["summary"]
    assert Decimal(summary["gross_ticket_sales"]) == Decimal("10000.00")
    assert Decimal(summary["host_gross"]) == Decimal("10000.00")
    assert Decimal(summary["buyer_platform_fees"]) == Decimal("300.00")
    assert Decimal(summary["padeya_commission"]) == Decimal("500.00")
    assert Decimal(summary["net_earnings"]) == Decimal("9500.00")
    # Buyer fee must not inflate host gross
    assert Decimal(summary["host_gross"]) < Decimal("10300.00")
    row = body["rows"][0]
    assert Decimal(row["buyer_paid_total"]) == Decimal("10300.00")
    assert Decimal(row["host_gross"]) == Decimal("10000.00")
    assert Decimal(row["buyer_fee_total"]) == Decimal("300.00")
    assert Decimal(row["host_net"]) == Decimal("9500.00")


def test_host_commission_deducted_from_net(client: TestClient, db_session: Session) -> None:
    _admin, host, event, tt, buyer, _ = _seed(db_session)
    _paid_order(db_session, host=host, event=event, tt=tt, buyer=buyer)
    report = build_host_earnings_report(db_session, host_id=host.id)
    assert report.summary.host_gross - report.summary.padeya_commission == Decimal(
        "9500.00"
    )
    assert report.summary.net_earnings == Decimal("9500.00")


def test_buyer_fee_excluded_from_host_gross(
    client: TestClient, db_session: Session
) -> None:
    _admin, host, event, tt, buyer, _ = _seed(db_session)
    _paid_order(db_session, host=host, event=event, tt=tt, buyer=buyer)
    report = build_host_earnings_report(db_session, host_id=host.id)
    assert report.summary.buyer_platform_fees == Decimal("300.00")
    assert report.summary.host_gross == Decimal("10000.00")
    assert report.summary.host_gross + report.summary.buyer_platform_fees == Decimal(
        "10300.00"
    )


def test_host_override_reflected_in_fee_terms(
    client: TestClient, db_session: Session
) -> None:
    admin, host, event, tt, buyer, _ = _seed(db_session)
    _paid_order(db_session, host=host, event=event, tt=tt, buyer=buyer)
    db_session.add(
        HostFeeOverride(
            host_id=host.id,
            fee_key=FEE_KEY_TICKET_COMMISSION,
            percentage_value=Decimal("8.00"),
            fixed_value=None,
            payer="host",
            enabled=True,
            effective_from=datetime.now(UTC) - timedelta(days=1),
            reason="Custom ticket commission for earnings test",
            created_by_admin_id=admin.id,
            updated_by_admin_id=admin.id,
        )
    )
    db_session.commit()
    headers = _login(client, "earn-host@example.com")
    res = client.get("/api/v1/finance/host/earnings", headers=headers)
    assert res.status_code == 200, res.text
    terms = {t["fee_key"]: t for t in res.json()["fee_terms"]}
    assert FEE_KEY_TICKET_COMMISSION in terms
    assert Decimal(terms[FEE_KEY_TICKET_COMMISSION]["percentage_value"]) == Decimal(
        "8.00"
    )
    assert terms[FEE_KEY_TICKET_COMMISSION]["source"] == "host_override"
    assert terms[FEE_KEY_BUYER_SERVICE]["payer"] == "buyer"


def test_refund_reduces_net(client: TestClient, db_session: Session) -> None:
    _admin, host, event, tt, buyer, _ = _seed(db_session)
    order = _paid_order(db_session, host=host, event=event, tt=tt, buyer=buyer)
    req = RefundRequest(
        order_id=order.id,
        payment_id=None,
        buyer_user_id=buyer.id,
        host_id=host.id,
        event_id=event.id,
        status="completed",
        refund_type="full",
        requested_amount=Decimal("2000.00"),
        currency="NGN",
        reason="Test refund for earnings",
        policy_snapshot="test",
    )
    db_session.add(req)
    db_session.flush()
    entry = debit_refund(
        db_session,
        host_id=host.id,
        amount=Decimal("2000.00"),
        currency="NGN",
        refund_request_id=req.id,
        actor_user_id=buyer.id,
    )
    db_session.add(
        Refund(
            refund_request_id=req.id,
            order_id=order.id,
            host_id=host.id,
            amount=Decimal("2000.00"),
            currency="NGN",
            status="completed",
            processed_by_user_id=buyer.id,
            ledger_entry_id=entry.id,
        )
    )
    db_session.commit()
    report = build_host_earnings_report(db_session, host_id=host.id)
    assert report.summary.refunds_total == Decimal("2000.00")
    assert report.summary.net_earnings == Decimal("7500.00")
    assert report.rows[0].refund_amount == Decimal("2000.00")


def test_admin_can_view_host_earnings(client: TestClient, db_session: Session) -> None:
    _admin, host, event, tt, buyer, _ = _seed(db_session)
    _paid_order(db_session, host=host, event=event, tt=tt, buyer=buyer)
    headers = _login(client, "earn-admin@example.com")
    res = client.get(
        f"/api/v1/finance/admin/hosts/{host.id}/earnings",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert Decimal(res.json()["summary"]["net_earnings"]) == Decimal("9500.00")


def test_host_cannot_view_another_host_earnings(
    client: TestClient, db_session: Session
) -> None:
    _admin, host, event, tt, buyer, other_host_user = _seed(db_session)
    _paid_order(db_session, host=host, event=event, tt=tt, buyer=buyer)
    other_headers = _login(client, other_host_user.email)
    # Other host's own earnings are empty / their host, not the first host's data
    own = client.get("/api/v1/finance/host/earnings", headers=other_headers)
    assert own.status_code == 200, own.text
    assert Decimal(own.json()["summary"]["net_earnings"]) == Decimal("0")
    assert own.json()["summary"]["host_id"] != str(host.id)

    # Direct admin-style path is not available to hosts
    blocked = client.get(
        f"/api/v1/finance/admin/hosts/{host.id}/earnings",
        headers=other_headers,
    )
    assert blocked.status_code in {401, 403}


def test_csv_export_works(client: TestClient, db_session: Session) -> None:
    _admin, host, event, tt, buyer, _ = _seed(db_session)
    _paid_order(db_session, host=host, event=event, tt=tt, buyer=buyer)
    headers = _login(client, "earn-host@example.com")
    res = client.get("/api/v1/finance/host/earnings/export.csv", headers=headers)
    assert res.status_code == 200, res.text
    assert "text/csv" in res.headers.get("content-type", "")
    assert "PDY-EARN-1" in res.text
    assert "host_net" in res.text

    report = build_host_earnings_report(db_session, host_id=host.id)
    csv_body = earnings_report_csv(report)
    assert "9500.00" in csv_body


def test_event_earnings_scoped(client: TestClient, db_session: Session) -> None:
    _admin, host, event, tt, buyer, _ = _seed(db_session)
    _paid_order(db_session, host=host, event=event, tt=tt, buyer=buyer)
    headers = _login(client, "earn-host@example.com")
    res = client.get(
        f"/api/v1/finance/host/events/{event.id}/earnings",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["summary"]["event_id"] == str(event.id)
    assert Decimal(res.json()["summary"]["net_earnings"]) == Decimal("9500.00")
