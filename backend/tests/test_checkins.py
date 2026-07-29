"""QR check-in scanner tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.tickets.models import Ticket, TicketQrToken
from app.tickets.qr import create_signed_qr_payload, hash_jti, new_public_ticket_code, new_qr_jti
from app.users.models import User
from app.users.service import get_role_by_name
from app.core.security import hash_password


def _auth(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name, "gender": "prefer_not_to_say"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_event_with_ticket(
    db: Session,
    *,
    ticket_status: str = "active",
) -> tuple[Event, Host, User, Ticket, str]:
    host_user = User(
        email="checkin-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Checkin Host",
        is_active=True,
    )
    host_role = get_role_by_name(db, "host")
    assert host_role is not None
    host_user.roles.append(host_role)
    db.add(host_user)
    db.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Checkin Host",
        slug="checkin-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(hours=2)
    event = Event(
        title="Gate Night",
        slug="gate-night",
        description="Event used for check-in scanner tests with enough text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
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
        price=Decimal("1000.00"),
        quantity=50,
        quantity_sold=1,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=5,
        visibility="public",
        status="active",
    )
    db.add(tt)
    db.flush()

    buyer = User(
        email="attendee@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Attendee One",
        is_active=True,
    )
    buyer_role = get_role_by_name(db, "buyer")
    assert buyer_role is not None
    buyer.roles.append(buyer_role)
    db.add(buyer)
    db.flush()

    # Minimal order scaffolding for FK integrity
    from app.payments.models import Order, OrderItem

    order = Order(
        reference="PDY-CHECKIN1",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("1000.00"),
        total_amount=Decimal("1000.00"),
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
        unit_price=Decimal("1000.00"),
        line_total=Decimal("1000.00"),
        ticket_type_name="GA",
    )
    db.add(item)
    db.flush()

    code = new_public_ticket_code()
    ticket = Ticket(
        public_code=code,
        order_id=order.id,
        order_item_id=item.id,
        event_id=event.id,
        ticket_type_id=tt.id,
        buyer_user_id=buyer.id,
        status=ticket_status,
        ticket_type_name="GA",
        holder_name=buyer.full_name,
        holder_email=buyer.email,
        checked_in_at=datetime.now(UTC) if ticket_status == "checked_in" else None,
    )
    db.add(ticket)
    db.flush()

    jti = new_qr_jti()
    signed = create_signed_qr_payload(public_code=code, event_id=event.id, jti=jti)
    db.add(
        TicketQrToken(
            ticket_id=ticket.id,
            jti_hash=hash_jti(jti),
            signed_payload=signed,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
    )
    db.commit()
    db.refresh(ticket)
    return event, host, host_user, ticket, signed


def _host_headers(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "checkin-host@example.com", "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_valid_check_in(client: TestClient, db_session: Session):
    event, _, _, ticket, qr = _seed_event_with_ticket(db_session)
    headers = _host_headers(client)

    session = client.post(
        "/api/v1/checkins/sessions",
        headers=headers,
        json={"event_id": str(event.id), "device_label": "Gate A"},
    )
    assert session.status_code == 201
    session_id = session.json()["id"]

    result = client.post(
        "/api/v1/checkins/scan",
        headers=headers,
        json={
            "event_id": str(event.id),
            "qr_payload": qr,
            "session_id": session_id,
        },
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["outcome"] == "success"
    assert body["ticket"]["public_code"] == ticket.public_code
    assert body["scanner_name"] == "Checkin Host"

    db_session.refresh(ticket)
    assert ticket.status == "checked_in"
    assert ticket.checked_in_at is not None


def test_duplicate_check_in(client: TestClient, db_session: Session):
    event, _, _, _, qr = _seed_event_with_ticket(db_session)
    headers = _host_headers(client)
    first = client.post(
        "/api/v1/checkins/scan",
        headers=headers,
        json={"event_id": str(event.id), "qr_payload": qr},
    )
    assert first.json()["outcome"] == "success"
    second = client.post(
        "/api/v1/checkins/scan",
        headers=headers,
        json={"event_id": str(event.id), "qr_payload": qr},
    )
    assert second.status_code == 200
    assert second.json()["outcome"] == "duplicate"
    assert "already" in second.json()["message"].lower() or "Duplicate" in second.json()["message"]


def test_invalid_ticket_qr(client: TestClient, db_session: Session):
    event, _, _, _, _ = _seed_event_with_ticket(db_session)
    headers = _host_headers(client)
    result = client.post(
        "/api/v1/checkins/scan",
        headers=headers,
        json={"event_id": str(event.id), "qr_payload": "not-a-valid-jwt-token-value"},
    )
    assert result.status_code == 200
    assert result.json()["outcome"] == "invalid"


def test_refunded_ticket(client: TestClient, db_session: Session):
    event, _, _, ticket, qr = _seed_event_with_ticket(db_session, ticket_status="refunded")
    headers = _host_headers(client)
    result = client.post(
        "/api/v1/checkins/scan",
        headers=headers,
        json={"event_id": str(event.id), "qr_payload": qr},
    )
    assert result.status_code == 200
    assert result.json()["outcome"] == "invalid"
    assert "refunded" in result.json()["message"].lower()
    db_session.refresh(ticket)
    assert ticket.status == "refunded"


def test_unauthorized_scanner(client: TestClient, db_session: Session):
    event, _, _, _, qr = _seed_event_with_ticket(db_session)
    stranger = _auth(client, "stranger@example.com", "Stranger")
    result = client.post(
        "/api/v1/checkins/scan",
        headers=stranger,
        json={"event_id": str(event.id), "qr_payload": qr},
    )
    assert result.status_code == 403


def test_assigned_staff_scanner(client: TestClient, db_session: Session):
    event, _, _, ticket, qr = _seed_event_with_ticket(db_session)
    host_headers = _host_headers(client)
    staff_headers = _auth(client, "staff@example.com", "Door Staff")

    # Staff cannot scan before assignment
    denied = client.post(
        "/api/v1/checkins/scan",
        headers=staff_headers,
        json={"event_id": str(event.id), "qr_payload": qr},
    )
    assert denied.status_code == 403

    assign = client.post(
        f"/api/v1/checkins/events/{event.id}/staff",
        headers=host_headers,
        json={"email": "staff@example.com"},
    )
    assert assign.status_code == 201, assign.text
    assignment_id = assign.json()["id"]

    # Refresh staff token not required — permissions checked from DB roles + assignment
    ok = client.post(
        "/api/v1/checkins/scan",
        headers=staff_headers,
        json={"event_id": str(event.id), "qr_payload": qr},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["outcome"] == "success"
    assert ok.json()["ticket"]["holder_name"] == ticket.holder_name

    unassign = client.delete(
        f"/api/v1/checkins/events/{event.id}/staff/{assignment_id}",
        headers=host_headers,
    )
    assert unassign.status_code == 200

    denied_again = client.post(
        "/api/v1/checkins/scan",
        headers=staff_headers,
        json={"event_id": str(event.id), "qr_payload": qr},
    )
    assert denied_again.status_code == 403


def test_admin_override_with_reason(client: TestClient, db_session: Session):
    event, _, _, ticket, _ = _seed_event_with_ticket(db_session, ticket_status="cancelled")
    admin_headers = _auth(client, "override-admin@example.com", "Override Admin")
    from app.users.service import get_user_by_email

    admin = get_user_by_email(db_session, "override-admin@example.com")
    role = get_role_by_name(db_session, "super_admin")
    assert admin and role
    admin.roles.append(role)
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "override-admin@example.com", "password": "securepass1"},
    )
    admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    result = client.post(
        "/api/v1/checkins/override",
        headers=admin_headers,
        json={
            "event_id": str(event.id),
            "ticket_id": str(ticket.id),
            "reason": "VIP guest list confirmation at door",
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["outcome"] == "success"
    db_session.refresh(ticket)
    assert ticket.status == "checked_in"

    logs = client.get(
        f"/api/v1/checkins/events/{event.id}",
        headers=admin_headers,
    )
    assert logs.status_code == 200
    assert any(row["method"] == "override" and row["override_reason"] for row in logs.json())


def test_manual_search_and_stats(client: TestClient, db_session: Session):
    event, _, _, ticket, qr = _seed_event_with_ticket(db_session)
    headers = _host_headers(client)
    client.post(
        "/api/v1/checkins/scan",
        headers=headers,
        json={"event_id": str(event.id), "qr_payload": qr},
    )
    search = client.get(
        f"/api/v1/checkins/events/{event.id}/search",
        headers=headers,
        params={"q": "Attendee"},
    )
    assert search.status_code == 200
    assert any(row["id"] == str(ticket.id) for row in search.json())

    stats = client.get(
        f"/api/v1/checkins/events/{event.id}/stats",
        headers=headers,
    )
    assert stats.status_code == 200
    body = stats.json()
    assert body["total_tickets"] == 1
    assert body["checked_in"] == 1
    assert body["successful_scans"] >= 1
