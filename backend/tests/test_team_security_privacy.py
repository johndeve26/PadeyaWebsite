"""Host team security & privacy invariants (section 14)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checkins.models import EventStaffAssignment
from app.checkins.service import _ticket_info
from app.email.models import EmailEvent
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostTeamMember
from app.hosts.team_permissions import permissions_for_role
from app.merch.service import can_reveal_shipping_address
from app.teams.permissions import can_scan_ticket
from app.tickets.models import Ticket
from app.users.models import User


def _auth(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _onboard(client: TestClient, headers: dict[str, str], name: str) -> dict:
    r = client.post(
        "/api/v1/hosts/onboard",
        headers=headers,
        json={
            "display_name": name,
            "bio": "Security host",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _invite_token(db: Session, email: str) -> str:
    email_row = db.scalar(
        select(EmailEvent)
        .where(
            EmailEvent.recipient_email == email,
            EmailEvent.template == "team_invite",
        )
        .order_by(EmailEvent.created_at.desc())
    )
    assert email_row is not None
    path = (email_row.context_json or {})["invite_path"]
    return path.rsplit("/", 1)[-1]


def _seed_event(db: Session, host: Host) -> Event:
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=7)
    event = Event(
        title="Security Desk Night",
        slug=f"sec-desk-{uuid4().hex[:8]}",
        description="Event for host team security privacy tests with enough text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        venue_name="Private Hall",
        city="Lagos",
        state="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
        location_visibility="hidden_until_payment",
    )
    db.add(event)
    db.flush()
    db.add(
        TicketType(
            event_id=event.id,
            name="GA",
            type="regular",
            description="GA",
            price=Decimal("1000.00"),
            quantity=50,
            quantity_sold=0,
            quantity_reserved=0,
            min_per_order=1,
            max_per_order=5,
            visibility="public",
            status="active",
        )
    )
    db.commit()
    db.refresh(event)
    return event


def test_owner_cannot_be_removed_via_team_endpoints(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "sec-owner-host@example.com", "Owner Host")
    host = _onboard(client, host_h, "Owner Host Co")
    host_row = db_session.get(Host, UUID(host["id"]))
    assert host_row is not None

    # Owner is never a membership — inventing one still cannot be suspended.
    fake = HostTeamMember(
        host_id=host_row.id,
        user_id=host_row.user_id,
        role="admin",
        role_label="Admin",
        status="active",
        permissions_json=permissions_for_role("admin"),
        scope_json={"type": "host_wide", "event_ids": []},
    )
    db_session.add(fake)
    db_session.commit()

    suspended = client.post(
        f"/api/v1/host/team/members/{fake.id}/suspend?host_id={host['id']}",
        headers=host_h,
    )
    assert suspended.status_code == 400
    assert "owner" in suspended.json()["detail"].lower()

    removed = client.post(
        f"/api/v1/host/team/members/{fake.id}/remove?host_id={host['id']}",
        headers=host_h,
    )
    assert removed.status_code == 400


def test_suspend_deactivates_staff_and_blocks_scan_immediately(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "sec-sus-host@example.com", "Sus Host")
    host = _onboard(client, host_h, "Sus Host Co")
    host_row = db_session.get(Host, UUID(host["id"]))
    assert host_row is not None
    event = _seed_event(db_session, host_row)

    email = "sec-sus-member@example.com"
    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={
            "email": email,
            "role": "scanner",
            "permissions": {"tickets.scan_qr": True, "tickets.check_in": True},
            "scope": "selected_events",
            "scoped_event_ids": [str(event.id)],
        },
    )
    assert created.status_code == 201, created.text

    member_h = _auth(client, email, "Sus Member")
    accepted = client.post(
        f"/api/v1/team/invites/{_invite_token(db_session, email)}/accept",
        headers=member_h,
    )
    assert accepted.status_code == 200, accepted.text
    member_id = accepted.json()["id"]
    member_user_id = UUID(accepted.json()["user_id"])

    assert can_scan_ticket(db_session, member_user_id, host_row.id, event.id) is True

    staff = db_session.scalar(
        select(EventStaffAssignment).where(
            EventStaffAssignment.user_id == member_user_id,
            EventStaffAssignment.event_id == event.id,
        )
    )
    assert staff is not None
    assert staff.status == "active"

    suspended = client.post(
        f"/api/v1/host/team/members/{member_id}/suspend?host_id={host['id']}",
        headers=host_h,
    )
    assert suspended.status_code == 200
    db_session.expire_all()
    staff = db_session.get(EventStaffAssignment, staff.id)
    assert staff is not None
    assert staff.status == "inactive"
    assert can_scan_ticket(db_session, member_user_id, host_row.id, event.id) is False


def test_remove_deactivates_staff_and_blocks_scan_immediately(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "sec-rm-host@example.com", "Rm Host")
    host = _onboard(client, host_h, "Rm Host Co")
    host_row = db_session.get(Host, UUID(host["id"]))
    assert host_row is not None
    event = _seed_event(db_session, host_row)

    email = "sec-rm-member@example.com"
    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={
            "email": email,
            "role": "scanner",
            "permissions": {"tickets.scan_qr": True, "tickets.check_in": True},
            "scope": "selected_events",
            "scoped_event_ids": [str(event.id)],
        },
    )
    assert created.status_code == 201, created.text

    member_h = _auth(client, email, "Rm Member")
    accepted = client.post(
        f"/api/v1/team/invites/{_invite_token(db_session, email)}/accept",
        headers=member_h,
    )
    assert accepted.status_code == 200, accepted.text
    member_id = accepted.json()["id"]
    member_user_id = UUID(accepted.json()["user_id"])
    assert can_scan_ticket(db_session, member_user_id, host_row.id, event.id) is True

    removed = client.post(
        f"/api/v1/host/team/members/{member_id}/remove?host_id={host['id']}",
        headers=host_h,
    )
    assert removed.status_code == 200
    assert removed.json()["status"] == "removed"
    db_session.expire_all()
    staff = db_session.scalar(
        select(EventStaffAssignment).where(
            EventStaffAssignment.user_id == member_user_id,
            EventStaffAssignment.event_id == event.id,
        )
    )
    assert staff is not None
    assert staff.status == "inactive"
    assert can_scan_ticket(db_session, member_user_id, host_row.id, event.id) is False


def test_invite_accept_requires_matching_email(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "sec-email-host@example.com", "Email Host")
    _onboard(client, host_h, "Email Host Co")
    invited = "sec-invitee@example.com"
    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={"email": invited, "role": "viewer"},
    )
    assert created.status_code == 201
    token = _invite_token(db_session, invited)

    wrong_h = _auth(client, "sec-wrong@example.com", "Wrong")
    bad = client.post(f"/api/v1/team/invites/{token}/accept", headers=wrong_h)
    assert bad.status_code == 403
    assert "invited email" in bad.json()["detail"].lower()


def test_ticket_scan_info_omits_holder_email():
    ticket = Ticket(
        id=uuid4(),
        public_code="PDY-SEC-1",
        status="active",
        holder_name="Ada",
        holder_email="ada@example.com",
        ticket_type_name="GA",
        checked_in_at=None,
    )
    info = _ticket_info(ticket)
    assert info["holder_name"] == "Ada"
    assert info["holder_email"] is None
    assert info["public_code"] == "PDY-SEC-1"


def test_desk_search_returns_minimal_attendee(
    client: TestClient, db_session: Session
):
    from app.payments.models import Order, OrderItem
    from app.tickets.qr import new_public_ticket_code

    host_h = _auth(client, "sec-search-host@example.com", "Search Host")
    host = _onboard(client, host_h, "Search Host Co")
    host_row = db_session.get(Host, UUID(host["id"]))
    assert host_row is not None
    event = _seed_event(db_session, host_row)
    ticket_type = db_session.scalar(
        select(TicketType).where(TicketType.event_id == event.id)
    )
    assert ticket_type is not None
    _auth(client, "sec-search-buyer@example.com", "Search Buyer")
    buyer = db_session.scalar(
        select(User).where(User.email == "sec-search-buyer@example.com")
    )
    assert buyer is not None
    order = Order(
        reference=f"PDY-SEC-{uuid4().hex[:8]}",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("1000.00"),
        total_amount=Decimal("1000.00"),
        buyer_email=buyer.email,
        buyer_name=buyer.full_name or "Buyer",
        paid_at=datetime.now(UTC),
    )
    db_session.add(order)
    db_session.flush()
    item = OrderItem(
        order_id=order.id,
        ticket_type_id=ticket_type.id,
        quantity=1,
        unit_price=Decimal("1000.00"),
        line_total=Decimal("1000.00"),
        ticket_type_name="GA",
    )
    db_session.add(item)
    db_session.flush()
    code = new_public_ticket_code()
    ticket = Ticket(
        public_code=code,
        order_id=order.id,
        order_item_id=item.id,
        event_id=event.id,
        ticket_type_id=ticket_type.id,
        buyer_user_id=buyer.id,
        status="active",
        ticket_type_name="GA",
        holder_name="Search Person",
        holder_email="search-person@example.com",
    )
    db_session.add(ticket)
    db_session.commit()

    found = client.get(
        f"/api/v1/checkins/events/{event.id}/search?q=Search",
        headers=host_h,
    )
    assert found.status_code == 200, found.text
    rows = found.json()
    assert len(rows) >= 1
    row = next(r for r in rows if r["public_code"] == code)
    assert row["holder_name"] == "Search Person"
    assert "holder_email" not in row
    assert "order_id" not in row


def test_shipping_reveal_requires_manage_shipping(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "sec-ship-host@example.com", "Ship Host")
    host = _onboard(client, host_h, "Ship Host Co")
    host_row = db_session.get(Host, UUID(host["id"]))
    assert host_row is not None
    event = _seed_event(db_session, host_row)

    email = "sec-ship-merch@example.com"
    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={
            "email": email,
            "role": "merch_staff",
            "permissions": {
                "merch.scan_pickup_qr": True,
                "merch.mark_picked_up": True,
                "merch.manage_shipping": False,
            },
            "scope": "selected_events",
            "scoped_event_ids": [str(event.id)],
        },
    )
    assert created.status_code == 201, created.text
    member_h = _auth(client, email, "Ship Merch")
    accepted = client.post(
        f"/api/v1/team/invites/{_invite_token(db_session, email)}/accept",
        headers=member_h,
    )
    assert accepted.status_code == 200
    member = db_session.scalar(select(User).where(User.email == email))
    assert member is not None
    assert can_reveal_shipping_address(db_session, member, event.id) is False

    # Owner can reveal.
    owner = db_session.get(User, host_row.user_id)
    assert owner is not None
    assert can_reveal_shipping_address(db_session, owner, event.id) is True


def test_desk_events_hide_secret_venue_for_non_owners(
    client: TestClient, db_session: Session
):
    host_h = _auth(client, "sec-venue-host@example.com", "Venue Host")
    host = _onboard(client, host_h, "Venue Host Co")
    host_row = db_session.get(Host, UUID(host["id"]))
    assert host_row is not None
    event = _seed_event(db_session, host_row)

    email = "sec-venue-scan@example.com"
    created = client.post(
        "/api/v1/host/team/invites",
        headers=host_h,
        json={
            "email": email,
            "role": "scanner",
            "permissions": {"tickets.scan_qr": True, "tickets.check_in": True},
            "scope": "selected_events",
            "scoped_event_ids": [str(event.id)],
        },
    )
    assert created.status_code == 201
    member_h = _auth(client, email, "Venue Scan")
    accepted = client.post(
        f"/api/v1/team/invites/{_invite_token(db_session, email)}/accept",
        headers=member_h,
    )
    assert accepted.status_code == 200

    desk = client.get(
        f"/api/v1/hosts/workspaces/{host['id']}/desk-events",
        headers=member_h,
    )
    assert desk.status_code == 200, desk.text
    rows = desk.json()
    assert len(rows) >= 1
    row = next(r for r in rows if r["id"] == str(event.id))
    assert row.get("venue_name") is None
    assert row.get("location_label")
    assert "Private Hall" not in (row.get("location_label") or "")
