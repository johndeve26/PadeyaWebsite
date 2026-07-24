"""Event Memories: auto-create, visibility, host edit, Legacy link, admin hide."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, TicketType
from app.hosts.models import Host, HostProfile
from app.memories.models import EventMemory
from app.tickets.models import Ticket
from app.tickets.qr import new_public_ticket_code
from app.users.models import User
from app.users.service import get_role_by_name
from app.reviews.models import VerifiedReview
from app.payments.models import Order, OrderItem


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_host(
    db: Session, *, email: str = "mem-host@example.com", slug: str = "mem-host"
) -> tuple[Host, User]:
    host_user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Memory Host",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db, "host"))
    db.add(host_user)
    db.flush()
    host = Host(
        user_id=host_user.id,
        display_name="Memory Host",
        slug=slug,
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, bio="Memory host"))
    db.commit()
    return host, host_user


def _seed_event(
    db: Session,
    host: Host,
    *,
    slug: str = "night-recap",
    status: str = "published",
    days_ago: int = 2,
) -> Event:
    start = datetime.now(UTC) - timedelta(days=days_ago)
    event = Event(
        title="Night Recap",
        slug=slug,
        description="A completed night out with enough description for validation.",
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        venue_name="The Yard",
        city="Lagos",
        status=status,
        featured=False,
        published_at=start - timedelta(days=7),
    )
    db.add(event)
    db.flush()
    tt = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        price=Decimal("3000.00"),
        quantity=100,
        quantity_sold=2,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=4,
        visibility="public",
        status="active",
    )
    db.add(tt)
    db.commit()
    db.refresh(event)
    return event


def _seed_checked_in_ticket(db: Session, event: Event, buyer: User) -> Ticket:
    tt = db.query(TicketType).filter_by(event_id=event.id).first()
    assert tt is not None
    order = Order(
        reference=f"PDY-MEM-{event.slug.upper()}",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("3000.00"),
        discount_amount=Decimal("0"),
        total_amount=Decimal("3000.00"),
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
        unit_price=Decimal("3000.00"),
        line_total=Decimal("3000.00"),
        ticket_type_name=tt.name,
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
        status="checked_in",
        ticket_type_name=tt.name,
        holder_name=buyer.full_name,
        holder_email=buyer.email,
        checked_in_at=datetime.now(UTC),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def test_auto_create_memory_on_complete(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session)
    event = _seed_event(db_session, host, status="published")
    headers = _login(client, host_user.email)

    before = db_session.query(EventMemory).filter_by(event_id=event.id).first()
    assert before is None

    resp = client.post(f"/api/v1/events/by-id/{event.id}/complete", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "completed"

    memory = db_session.query(EventMemory).filter_by(event_id=event.id).first()
    assert memory is not None
    assert memory.status == "published"
    assert memory.host_id == host.id


def test_public_visibility_only_after_completed(client: TestClient, db_session: Session):
    host, _ = _seed_host(db_session, email="vis-host@example.com", slug="vis-host")
    event = _seed_event(db_session, host, slug="still-live", status="published")

    # Manually create memory while event still published — must stay private
    db_session.add(
        EventMemory(
            event_id=event.id,
            host_id=host.id,
            status="published",
            published_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    blocked = client.get(f"/api/v1/memories/public/{host.slug}/{event.slug}")
    assert blocked.status_code == 404

    event.status = "completed"
    db_session.commit()

    ok = client.get(f"/api/v1/memories/public/{host.slug}/{event.slug}")
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["event_title"] == "Night Recap"
    assert body["venue_name"] == "The Yard"
    assert body["attendance"]["checked_in"] == 0
    assert body["share_path"] == f"/@{host.slug}/memories/{event.slug}"


def test_host_edit_permission(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session, email="edit-host@example.com", slug="edit-host")
    other, other_user = _seed_host(
        db_session, email="other-host@example.com", slug="other-host"
    )
    event = _seed_event(db_session, host, slug="edit-night", status="completed")
    db_session.add(
        EventMemory(
            event_id=event.id,
            host_id=host.id,
            status="published",
            published_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    owner = _login(client, host_user.email)
    patched = client.patch(
        f"/api/v1/memories/host/events/{event.id}",
        headers=owner,
        json={"host_recap_note": "Thank you for coming out."},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["host_recap_note"] == "Thank you for coming out."

    media = client.post(
        f"/api/v1/memories/host/events/{event.id}/media",
        headers=owner,
        json={
            "url": "https://cdn.example.com/recap.jpg",
            "media_type": "image",
            "label": "Crowd",
        },
    )
    assert media.status_code == 200, media.text
    assert len(media.json()["media"]) == 1

    stranger = _login(client, other_user.email)
    denied = client.patch(
        f"/api/v1/memories/host/events/{event.id}",
        headers=stranger,
        json={"host_recap_note": "Hack"},
    )
    assert denied.status_code == 403

    assert other.id != host.id


def test_memory_linked_to_legacy_page(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session, email="leg-host@example.com", slug="leg-host")
    event = _seed_event(db_session, host, slug="legacy-night", status="published")
    headers = _login(client, host_user.email)

    complete = client.post(f"/api/v1/events/by-id/{event.id}/complete", headers=headers)
    assert complete.status_code == 200

    page = client.get(f"/api/v1/legacy/{host.slug}")
    assert page.status_code == 200, page.text
    data = page.json()
    assert len(data["event_memories"]) >= 1
    mem = data["event_memories"][0]
    assert mem["event_slug"] == event.slug
    assert mem["share_path"] == f"/@{host.slug}/memories/{event.slug}"

    past = next(e for e in data["past_events"] if e["slug"] == event.slug)
    assert past["memory_path"] == f"/@{host.slug}/memories/{event.slug}"


def test_admin_hide_memory(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session, email="hide-host@example.com", slug="hide-host")
    event = _seed_event(db_session, host, slug="hide-night", status="completed")
    memory = EventMemory(
        event_id=event.id,
        host_id=host.id,
        status="published",
        published_at=datetime.now(UTC),
        host_recap_note="Visible note",
    )
    db_session.add(memory)
    db_session.commit()
    db_session.refresh(memory)

    public = client.get(f"/api/v1/memories/public/{host.slug}/{event.slug}")
    assert public.status_code == 200

    admin = User(
        email="mem-admin@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Mem Admin",
        is_active=True,
    )
    admin.roles.append(get_role_by_name(db_session, "super_admin"))
    db_session.add(admin)
    db_session.commit()
    admin_headers = _login(client, admin.email)

    hide = client.post(
        f"/api/v1/memories/admin/{memory.id}/moderate",
        headers=admin_headers,
        json={"action": "hide", "note": "Inappropriate"},
    )
    assert hide.status_code == 200, hide.text
    assert hide.json()["status"] == "hidden"

    gone = client.get(f"/api/v1/memories/public/{host.slug}/{event.slug}")
    assert gone.status_code == 404

    page = client.get(f"/api/v1/legacy/{host.slug}")
    assert page.status_code == 200
    assert all(m["event_slug"] != event.slug for m in page.json()["event_memories"])

    # host still owns the event but cannot revive while hidden via public
    host_headers = _login(client, host_user.email)
    host_view = client.get(
        f"/api/v1/memories/host/events/{event.id}", headers=host_headers
    )
    assert host_view.status_code == 200
    assert host_view.json()["status"] == "hidden"


def test_attendance_and_top_reviews_on_memory(client: TestClient, db_session: Session):
    host, host_user = _seed_host(db_session, email="stats-host@example.com", slug="stats-host")
    event = _seed_event(db_session, host, slug="stats-night", status="completed")
    db_session.add(
        EventMemory(
            event_id=event.id,
            host_id=host.id,
            status="published",
            published_at=datetime.now(UTC),
        )
    )
    buyer = User(
        email="mem-buyer@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Mem Buyer",
        is_active=True,
    )
    buyer.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add(buyer)
    db_session.commit()
    ticket = _seed_checked_in_ticket(db_session, event, buyer)
    db_session.add(
        VerifiedReview(
            event_id=event.id,
            host_id=host.id,
            reviewer_user_id=buyer.id,
            ticket_id=ticket.id,
            rating=5,
            title="Amazing",
            body="Best night of the year hands down.",
            status="visible",
        )
    )
    db_session.commit()

    resp = client.get(f"/api/v1/memories/public/{host.slug}/{event.slug}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["attendance"]["checked_in"] == 1
    assert data["attendance"]["tickets_sold"] == 1
    assert float(data["verified_rating"]) == 5.0
    assert len(data["top_reviews"]) == 1
    assert data["top_reviews"][0]["title"] == "Amazing"
    assert host_user.email.endswith("@example.com")
