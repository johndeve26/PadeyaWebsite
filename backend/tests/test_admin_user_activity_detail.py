"""Admin user Activity drill-down — lists, pagination, finance gates, safety."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.audit import AuditLog
from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem, Payment
from app.reviews.models import VerifiedReview
from app.tickets.models import Ticket
from app.tickets.service import issue_tickets_for_paid_order
from app.users.models import Permission, Role, User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _grant_perms(db: Session, user: User, *codes: str) -> None:
    role = Role(name=f"tmp-act-{uuid.uuid4().hex[:8]}", description="test")
    for code in codes:
        perm = db.scalar(select(Permission).where(Permission.code == code))
        assert perm is not None, f"missing permission {code}"
        role.permissions.append(perm)
    db.add(role)
    user.roles.append(role)
    db.commit()


def _seed_buyer_with_activity(
    db: Session,
) -> tuple[User, User, Ticket, Order, VerifiedReview]:
    suffix = uuid.uuid4().hex[:8]
    host_user = User(
        email=f"act-host-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Activity Host",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db, "host"))
    buyer = User(
        email=f"act-buyer-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Activity Buyer",
        is_active=True,
    )
    buyer.roles.append(get_role_by_name(db, "buyer"))
    db.add_all([host_user, buyer])
    db.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Activity Host Org",
        slug=f"act-host-{suffix}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=3)
    event = Event(
        title="Activity Drill Night",
        slug=f"activity-drill-{suffix}",
        description="Event used for admin activity drill-down tests with enough text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        status="published",
        city="Lagos",
        venue_name="Drill Hall",
        address="1 Test Street",
        published_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()

    ticket_type = TicketType(
        event_id=event.id,
        name="General",
        type="regular",
        price=Decimal("4000.00"),
        quantity=50,
        quantity_sold=0,
        quantity_reserved=0,
        seats_per_unit=1,
        min_per_order=1,
        max_per_order=5,
        visibility="public",
        status="active",
    )
    db.add(ticket_type)
    db.flush()

    order = Order(
        reference=f"ORD-ACT-{suffix}",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("4000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("4000.00"),
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        paid_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            item_kind="ticket",
            ticket_type_id=ticket_type.id,
            quantity=1,
            unit_price=Decimal("4000.00"),
            line_total=Decimal("4000.00"),
            ticket_type_name="General",
        )
    )
    db.add(
        Payment(
            order_id=order.id,
            provider="paystack",
            reference=f"psk_safe_ref_{suffix}",
            status="success",
            amount=Decimal("4000.00"),
            currency="NGN",
            access_code="should_never_appear",
            raw_response={"secret": "nope"},
        )
    )
    db.flush()

    order = db.scalar(
        select(Order).where(Order.id == order.id).options(selectinload(Order.items))
    )
    assert order is not None
    tickets = issue_tickets_for_paid_order(db, order)
    assert tickets
    ticket = tickets[0]

    review = VerifiedReview(
        event_id=event.id,
        host_id=host.id,
        reviewer_user_id=buyer.id,
        ticket_id=ticket.id,
        rating=5,
        title="Great",
        body="Private review body must not leak via activity lists.",
        status="visible",
    )
    db.add(review)
    db.commit()
    return buyer, host_user, ticket, order, review


def _admin_with(
    client: TestClient, db: Session, *perms: str
) -> tuple[User, dict[str, str]]:
    suffix = uuid.uuid4().hex[:8]
    admin = User(
        email=f"act-admin-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Activity Admin",
        is_active=True,
    )
    db.add(admin)
    db.flush()
    _grant_perms(db, admin, *perms)
    return admin, _login(client, admin.email)


def test_activity_tickets_orders_reviews_rows(
    client: TestClient, db_session: Session
):
    buyer, _, ticket, order, review = _seed_buyer_with_activity(db_session)
    _, headers = _admin_with(
        client,
        db_session,
        "admin.users.view",
        "admin.users.view_activity",
        "payments.view",
    )

    tickets = client.get(
        f"/api/v1/admin/users/{buyer.id}/activity/tickets",
        headers=headers,
    )
    assert tickets.status_code == 200, tickets.text
    body = tickets.json()
    assert body["kind"] == "tickets"
    assert body["total"] >= 1
    row = next(r for r in body["items"] if r["id"] == str(ticket.id))
    assert row["public_code"] == ticket.public_code
    assert row["event_name"] == "Activity Drill Night"
    assert row["order_reference"] == order.reference
    assert "signed_payload" not in tickets.text
    assert "qr_secret" not in tickets.text.lower()
    assert "jti_hash" not in tickets.text.lower()

    orders = client.get(
        f"/api/v1/admin/users/{buyer.id}/activity/orders",
        headers=headers,
    )
    assert orders.status_code == 200
    order_row = next(
        r for r in orders.json()["items"] if r["order_reference"] == order.reference
    )
    assert order_row["amount"] == "4000.00"
    assert order_row["paystack_reference"] is not None
    assert order_row["paystack_reference"].startswith("psk_safe_ref_")
    assert "access_code" not in orders.text
    assert "raw_response" not in orders.text

    reviews = client.get(
        f"/api/v1/admin/users/{buyer.id}/activity/reviews",
        headers=headers,
    )
    assert reviews.status_code == 200
    review_row = next(
        r for r in reviews.json()["items"] if r["id"] == str(review.id)
    )
    assert review_row["rating"] == 5
    assert review_row["verified_attendance"] is True
    assert "Private review body" not in reviews.text
    assert "body" not in review_row


def test_activity_empty_state_and_pagination(client: TestClient, db_session: Session):
    suffix = uuid.uuid4().hex[:8]
    buyer = User(
        email=f"act-empty-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Empty Buyer",
        is_active=True,
    )
    db_session.add(buyer)
    db_session.commit()

    _, headers = _admin_with(
        client, db_session, "admin.users.view", "admin.users.view_activity"
    )

    empty = client.get(
        f"/api/v1/admin/users/{buyer.id}/activity/tickets",
        headers=headers,
    )
    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert empty.json()["total"] == 0

    buyer2, _, _, _, _ = _seed_buyer_with_activity(db_session)
    page = client.get(
        f"/api/v1/admin/users/{buyer2.id}/activity/tickets",
        headers=headers,
        params={"page": 1, "limit": 1},
    )
    assert page.status_code == 200
    assert page.json()["limit"] == 1
    assert len(page.json()["items"]) <= 1
    assert page.json()["page"] == 1


def test_activity_finance_fields_hidden_without_payments_view(
    client: TestClient, db_session: Session
):
    buyer, _, _, order, _ = _seed_buyer_with_activity(db_session)
    _, headers = _admin_with(
        client, db_session, "admin.users.view", "admin.users.view_activity"
    )

    orders = client.get(
        f"/api/v1/admin/users/{buyer.id}/activity/orders",
        headers=headers,
    )
    assert orders.status_code == 200
    assert orders.json()["finance_fields_included"] is False
    row = next(
        r for r in orders.json()["items"] if r["order_reference"] == order.reference
    )
    assert row["amount"] is None
    assert row["currency"] is None
    assert row["paystack_reference"] is None
    assert row["payment_status"] == "paid"


def test_activity_does_not_expose_sensitive_fields(
    client: TestClient, db_session: Session
):
    buyer, _, _, _, _ = _seed_buyer_with_activity(db_session)
    _, headers = _admin_with(
        client,
        db_session,
        "admin.users.view",
        "admin.users.view_activity",
        "payments.view",
    )

    for kind in (
        "tickets",
        "orders",
        "merch",
        "refunds",
        "reviews",
        "hosts",
        "teams",
        "ambassadors",
    ):
        res = client.get(
            f"/api/v1/admin/users/{buyer.id}/activity/{kind}",
            headers=headers,
        )
        assert res.status_code == 200, f"{kind}: {res.text}"
        text = res.text.lower()
        assert "password" not in text
        assert "access_token" not in text
        assert "refresh_token" not in text
        assert "raw_response" not in text
        assert "signed_payload" not in text
        assert "pickup_qr_token_hash" not in text
        assert "access_code" not in text


def test_activity_detail_audited(client: TestClient, db_session: Session):
    buyer, _, _, _, _ = _seed_buyer_with_activity(db_session)
    admin, headers = _admin_with(
        client, db_session, "admin.users.view", "admin.users.view_activity"
    )

    res = client.get(
        f"/api/v1/admin/users/{buyer.id}/activity/orders",
        headers=headers,
    )
    assert res.status_code == 200

    actions = {
        row.action
        for row in db_session.scalars(
            select(AuditLog).where(
                AuditLog.actor_user_id == admin.id,
                AuditLog.resource_id == str(buyer.id),
            )
        ).all()
    }
    assert "admin_user_activity_detail_viewed" in actions


def test_activity_unknown_kind_404(client: TestClient, db_session: Session):
    buyer, _, _, _, _ = _seed_buyer_with_activity(db_session)
    _, headers = _admin_with(
        client, db_session, "admin.users.view", "admin.users.view_activity"
    )
    res = client.get(
        f"/api/v1/admin/users/{buyer.id}/activity/not-a-kind",
        headers=headers,
    )
    assert res.status_code == 404
