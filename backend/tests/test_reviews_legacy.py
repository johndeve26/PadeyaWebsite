"""Verified reviews and Legacy Page tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile, HostVerification
from app.payments.models import Order, OrderItem
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name


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


def _seed_reviewable(
    db: Session,
    *,
    ticket_status: str = "checked_in",
    event_ended: bool = True,
    slug: str = "legacy-host",
) -> tuple[Event, Host, User, Ticket]:
    host_user = User(
        email="legacy-host@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Legacy Host",
        is_active=True,
    )
    host_role = get_role_by_name(db, "host")
    assert host_role is not None
    host_user.roles.append(host_role)
    db.add(host_user)
    db.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Legacy Host",
        slug=slug,
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(
        HostProfile(
            host_id=host.id,
            bio="Building nights that last.",
            city="Lagos",
            cover_url="https://cdn.example.com/cover.jpg",
            avatar_url="https://cdn.example.com/avatar.jpg",
        )
    )
    db.add(HostVerification(host_id=host.id, status="verified"))

    category = db.query(EventCategory).first()
    if event_ended:
        start = datetime.now(UTC) - timedelta(days=2)
        end = datetime.now(UTC) - timedelta(hours=6)
    else:
        start = datetime.now(UTC) + timedelta(hours=2)
        end = start + timedelta(hours=4)

    event = Event(
        title="Closed Night",
        slug="closed-night",
        description="Past event used for verified review eligibility tests.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=end,
        city="Lagos",
        status="published",
        featured=False,
        published_at=start - timedelta(days=1),
    )
    db.add(event)
    db.flush()

    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("2000.00"),
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

    buyer = User(
        email="reviewer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Reviewer One",
        is_active=True,
    )
    buyer_role = get_role_by_name(db, "buyer")
    assert buyer_role is not None
    buyer.roles.append(buyer_role)
    db.add(buyer)
    db.flush()

    order = Order(
        reference="PDY-LEGACY1",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("2000.00"),
        total_amount=Decimal("2000.00"),
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
        unit_price=Decimal("2000.00"),
        line_total=Decimal("2000.00"),
        ticket_type_name="GA",
    )
    db.add(item)
    db.flush()

    ticket = Ticket(
        public_code=new_public_ticket_code(),
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
    db.commit()
    db.refresh(ticket)
    return event, host, buyer, ticket


def _buyer_headers(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "reviewer@example.com", "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _host_headers(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "legacy-host@example.com", "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_review_eligibility_and_submit(client: TestClient, db_session: Session):
    event, host, _, ticket = _seed_reviewable(db_session)
    headers = _buyer_headers(client)

    elig = client.get(
        f"/api/v1/reviews/eligibility?ticket_id={ticket.id}",
        headers=headers,
    )
    assert elig.status_code == 200
    assert elig.json()["eligible"] is True

    created = client.post(
        "/api/v1/reviews",
        headers=headers,
        json={
            "ticket_id": str(ticket.id),
            "rating": 5,
            "title": "Incredible night",
            "body": "Checked in and the production was excellent throughout.",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["rating"] == 5
    assert body["event_id"] == str(event.id)
    assert body["host_id"] == str(host.id)

    page = client.get("/api/v1/legacy/legacy-host")
    assert page.status_code == 200
    legacy = page.json()
    assert legacy["username"] == "legacy-host"
    assert legacy["verified"] is True
    assert legacy["stats"]["review_count"] == 1
    assert len(legacy["reviews"]) == 1
    assert legacy["share_path"] == "/@legacy-host"


def test_cannot_review_without_check_in(client: TestClient, db_session: Session):
    _, _, _, ticket = _seed_reviewable(db_session, ticket_status="active")
    headers = _buyer_headers(client)

    elig = client.get(
        f"/api/v1/reviews/eligibility?ticket_id={ticket.id}",
        headers=headers,
    )
    assert elig.status_code == 200
    assert elig.json()["eligible"] is False
    assert "checked-in" in (elig.json()["reason"] or "").lower()

    created = client.post(
        "/api/v1/reviews",
        headers=headers,
        json={
            "ticket_id": str(ticket.id),
            "rating": 4,
            "body": "Should not be allowed without check-in at the door.",
        },
    )
    assert created.status_code == 400


def test_cannot_review_before_event_ends(client: TestClient, db_session: Session):
    _, _, _, ticket = _seed_reviewable(db_session, event_ended=False)
    headers = _buyer_headers(client)

    elig = client.get(
        f"/api/v1/reviews/eligibility?ticket_id={ticket.id}",
        headers=headers,
    )
    assert elig.status_code == 200
    assert elig.json()["eligible"] is False
    assert "ends" in (elig.json()["reason"] or "").lower()


def test_cannot_review_twice(client: TestClient, db_session: Session):
    _, _, _, ticket = _seed_reviewable(db_session)
    headers = _buyer_headers(client)
    payload = {
        "ticket_id": str(ticket.id),
        "rating": 5,
        "body": "First verified review after a proper check-in.",
    }
    assert client.post("/api/v1/reviews", headers=headers, json=payload).status_code == 201
    second = client.post("/api/v1/reviews", headers=headers, json=payload)
    assert second.status_code == 400
    assert "already" in second.json()["detail"].lower()


def test_host_cannot_delete_review(client: TestClient, db_session: Session):
    _, _, _, ticket = _seed_reviewable(db_session)
    buyer = _buyer_headers(client)
    created = client.post(
        "/api/v1/reviews",
        headers=buyer,
        json={
            "ticket_id": str(ticket.id),
            "rating": 3,
            "body": "Average experience but still a verified check-in review.",
        },
    )
    review_id = created.json()["id"]
    host = _host_headers(client)
    deleted = client.delete(f"/api/v1/reviews/{review_id}", headers=host)
    assert deleted.status_code == 403


def test_buyer_can_update_and_withdraw_review(client: TestClient, db_session: Session):
    _, _, _, ticket = _seed_reviewable(db_session, slug="withdraw-host")
    buyer = _buyer_headers(client)
    created = client.post(
        "/api/v1/reviews",
        headers=buyer,
        json={
            "ticket_id": str(ticket.id),
            "rating": 5,
            "title": "Solid night",
            "body": "Great night, would come again for sure on Pàdéyá.",
        },
    )
    assert created.status_code == 201, created.text
    review_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/reviews/{review_id}",
        headers=buyer,
        json={
            "rating": 4,
            "title": "Almost perfect",
            "body": "Updated after thinking it through — still a strong Pàdéyá night.",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["rating"] == 4
    assert updated.json()["title"] == "Almost perfect"
    assert updated.json()["status"] == "visible"

    withdrawn = client.delete(f"/api/v1/reviews/{review_id}", headers=buyer)
    assert withdrawn.status_code == 200, withdrawn.text
    assert withdrawn.json()["status"] == "withdrawn"

    # Edit after withdraw restores visibility
    restored = client.patch(
        f"/api/v1/reviews/{review_id}",
        headers=buyer,
        json={"body": "Restored review text after a short withdraw on Pàdéyá."},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["status"] == "visible"

    host = _host_headers(client)
    assert client.delete(f"/api/v1/reviews/{review_id}", headers=host).status_code == 403
    assert client.patch(
        f"/api/v1/reviews/{review_id}",
        headers=host,
        json={"body": "Hosts must not edit buyer reviews on Pàdéyá."},
    ).status_code == 404


def test_admin_moderation_works(client: TestClient, db_session: Session, assign_role):
    _, _, _, ticket = _seed_reviewable(db_session)
    buyer = _buyer_headers(client)
    created = client.post(
        "/api/v1/reviews",
        headers=buyer,
        json={
            "ticket_id": str(ticket.id),
            "rating": 1,
            "body": "Policy-violating language that should be hidden by moderators.",
        },
    )
    review_id = created.json()["id"]

    host = _host_headers(client)
    report = client.post(
        f"/api/v1/reviews/{review_id}/report",
        headers=host,
        json={"reason": "Contains abusive language against staff."},
    )
    assert report.status_code == 201

    admin_headers = _auth(client, "moderator@example.com", "Moderator")
    assign_role("moderator@example.com", "support_agent")

    reported = client.get("/api/v1/reviews/admin/reported", headers=admin_headers)
    assert reported.status_code == 200
    assert any(item["review_id"] == review_id for item in reported.json())

    hidden = client.post(
        f"/api/v1/reviews/{review_id}/moderate",
        headers=admin_headers,
        json={"action": "hide", "reason": "Violates community guidelines"},
    )
    assert hidden.status_code == 200
    assert hidden.json()["status"] == "hidden"

    page = client.get("/api/v1/legacy/legacy-host")
    assert page.status_code == 200
    assert page.json()["stats"]["review_count"] == 0
    assert page.json()["reviews"] == []

    restored = client.post(
        f"/api/v1/reviews/{review_id}/moderate",
        headers=admin_headers,
        json={"action": "restore", "reason": "Appeal accepted after review"},
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "visible"
