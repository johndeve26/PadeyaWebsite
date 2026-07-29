"""Phase 17 — advanced ticketing tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.payments.models import Order, OrderItem
from app.tickets.advanced_models import TicketGroup, TicketGroupMember
from app.tickets.models import Ticket, TicketQrToken
from app.tickets.qr import create_signed_qr_payload, hash_jti, new_public_ticket_code, new_qr_jti
from app.tickets.service import issue_tickets_for_paid_order
from app.users.models import User
from app.users.service import get_role_by_name


def _register(client: TestClient, email: str, name: str = "User") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "securepass1", "full_name": name, "gender": "prefer_not_to_say"},
    )
    return _login(client, email)


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_paid_ticket(
    db: Session,
    *,
    host_email: str = "adv-host@example.com",
    buyer_email: str = "adv-buyer@example.com",
    ticket_kind: str = "regular",
    seats_per_unit: int = 1,
    slug: str = "adv-night",
) -> tuple[Event, Host, User, User, Ticket, str]:
    host_user = User(
        email=host_email,
        password_hash=hash_password("securepass1"),
        full_name="Adv Host",
        is_active=True,
    )
    host_role = get_role_by_name(db, "host")
    assert host_role is not None
    host_user.roles.append(host_role)
    db.add(host_user)
    db.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Adv Host",
        slug=host_email.split("@")[0],
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(hours=2)
    event = Event(
        title="Advanced Night",
        slug=slug,
        description="Event used for advanced ticketing tests with enough text.",
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
        name="VIP Table" if ticket_kind == "table" else "Group Pack" if ticket_kind == "group" else "GA",
        type=ticket_kind,
        price=Decimal("5000.00"),
        quantity=20,
        quantity_sold=1,
        quantity_reserved=0,
        seats_per_unit=seats_per_unit,
        min_per_order=1,
        max_per_order=5,
        visibility="public",
        status="active",
    )
    db.add(tt)
    db.flush()

    buyer = User(
        email=buyer_email,
        password_hash=hash_password("securepass1"),
        full_name="Adv Buyer",
        is_active=True,
    )
    buyer_role = get_role_by_name(db, "buyer")
    assert buyer_role is not None
    buyer.roles.append(buyer_role)
    db.add(buyer)
    db.flush()

    order = Order(
        reference=f"PDY-ADV-{slug.upper()}",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000.00"),
        total_amount=Decimal("5000.00"),
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
        unit_price=Decimal("5000.00"),
        line_total=Decimal("5000.00"),
        ticket_type_name=tt.name,
    )
    db.add(item)
    db.flush()
    order.items  # ensure relationship loaded
    db.refresh(order)

    # Reload order with items for issuer
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select

    order = db.scalar(
        select(Order).where(Order.id == order.id).options(selectinload(Order.items))
    )
    assert order is not None
    tickets = issue_tickets_for_paid_order(db, order)
    db.commit()
    ticket = tickets[0]
    qr = db.scalar(select(TicketQrToken).where(TicketQrToken.ticket_id == ticket.id))
    assert qr is not None
    return event, host, host_user, buyer, ticket, qr.signed_payload


def test_ticket_transfer_old_owner_blocked_new_owner_valid(
    client: TestClient, db_session: Session
):
    event, _host, host_user, buyer, ticket, old_qr = _seed_paid_ticket(db_session)
    recipient_headers = _register(client, "adv-recipient@example.com", "Recipient")
    buyer_headers = _login(client, buyer.email)
    host_headers = _login(client, host_user.email)

    # Transfer
    transfer = client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=buyer_headers,
        json={"to_email": "adv-recipient@example.com", "to_name": "Recipient", "note": "Gift"},
    )
    assert transfer.status_code == 200, transfer.json()
    assert transfer.json()["to_email"] == "adv-recipient@example.com"

    # Old owner cannot fetch ticket
    old_view = client.get(f"/api/v1/tickets/{ticket.id}", headers=buyer_headers)
    assert old_view.status_code == 404

    # New owner can fetch and has QR
    new_view = client.get(f"/api/v1/tickets/{ticket.id}", headers=recipient_headers)
    assert new_view.status_code == 200
    new_qr = new_view.json()["qr_payload"]
    assert new_qr
    assert new_qr != old_qr

    # Old QR fails validation; new QR succeeds
    bad = client.post(
        "/api/v1/checkins/validate",
        headers=host_headers,
        json={"event_id": str(event.id), "qr_payload": old_qr},
    )
    assert bad.status_code == 200
    assert bad.json()["outcome"] == "invalid"

    good = client.post(
        "/api/v1/checkins/validate",
        headers=host_headers,
        json={"event_id": str(event.id), "qr_payload": new_qr},
    )
    assert good.status_code == 200
    assert good.json()["outcome"] == "valid"

    # Transfer history for host
    history = client.get(
        f"/api/v1/tickets/events/{event.id}/transfers",
        headers=host_headers,
    )
    assert history.status_code == 200
    assert len(history.json()) == 1

    # Audit log
    logs = db_session.query(AuditLog).filter(AuditLog.action == "tickets.transfer").all()
    assert len(logs) >= 1


def test_transfer_audit_and_admin_visibility(client: TestClient, db_session: Session):
    _event, _host, _host_user, buyer, ticket, _qr = _seed_paid_ticket(
        db_session, slug="adv-audit", buyer_email="audit-buyer@example.com", host_email="audit-host@example.com"
    )
    _register(client, "audit-to@example.com", "To User")
    buyer_headers = _login(client, buyer.email)

    resp = client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=buyer_headers,
        json={"to_email": "audit-to@example.com", "to_name": "Audit To"},
    )
    assert resp.status_code == 200

    # Super admin list
    admin = User(
        email="adv-admin@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Admin",
        is_active=True,
    )
    role = get_role_by_name(db_session, "super_admin")
    assert role is not None
    admin.roles.append(role)
    db_session.add(admin)
    db_session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "adv-admin@example.com", "password": "securepass1"},
    )
    admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    transfers = client.get("/api/v1/tickets/admin/transfers", headers=admin_headers)
    assert transfers.status_code == 200
    assert any(t["ticket_id"] == str(ticket.id) for t in transfers.json())


def test_transfer_unknown_recipient_email(client: TestClient, db_session: Session):
    from sqlalchemy import select

    from app.email.models import EmailEvent

    event, _host, _host_user, buyer, ticket, _qr = _seed_paid_ticket(
        db_session,
        slug="adv-no-recipient",
        buyer_email="no-recip-buyer@example.com",
    )
    buyer_headers = _login(client, buyer.email)
    resp = client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=buyer_headers,
        json={
            "to_email": "ban@smartlancedesigns.com",
            "to_name": "Ban Smart",
        },
    )
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["status"] == "pending"
    assert body["recipient_name"] == "Ban Smart"
    assert body["to_user_id"] is None

    mine = client.get("/api/v1/tickets/mine", headers=buyer_headers)
    assert mine.status_code == 200
    assert not any(t["id"] == str(ticket.id) for t in mine.json())

    mail = db_session.scalar(
        select(EmailEvent).where(
            EmailEvent.template == "ticket_transfer_invite",
            EmailEvent.recipient_email == "ban@smartlancedesigns.com",
        )
    )
    assert mail is not None
    assert mail.context_json.get("recipient_name") == "Ban Smart"
    assert mail.context_json.get("event_title") == event.title
    token = mail.context_json.get("claim_token")
    assert token

    assert body.get("claim_path", "").startswith("/tickets/claim?token=")

    ctx = client.get(
        f"/api/v1/tickets/claim/context?token={token}",
    )
    assert ctx.status_code == 200, ctx.json()
    assert ctx.json()["recipient_email"] == "ban@smartlancedesigns.com"

    recipient_headers = _register(client, "ban@smartlancedesigns.com", "Ban Smart")

    recipient_history = client.get(
        "/api/v1/tickets/transfers/mine",
        headers=recipient_headers,
    )
    assert recipient_history.status_code == 200
    transfer_id = body["id"]
    assert any(
        h["id"] == transfer_id and h["role"] == "received" and h["status"] == "pending"
        for h in recipient_history.json()
    )

    claim_by_id = client.post(
        f"/api/v1/tickets/transfers/{transfer_id}/claim",
        headers=recipient_headers,
        json={},
    )
    assert claim_by_id.status_code == 200, claim_by_id.json()
    assert claim_by_id.json()["qr_payload"]

    recipient_mine = client.get("/api/v1/tickets/mine", headers=recipient_headers)
    assert any(t["id"] == str(ticket.id) for t in recipient_mine.json())

    received_mail = db_session.scalar(
        select(EmailEvent).where(
            EmailEvent.template == "ticket_transfer_received",
            EmailEvent.recipient_email == "ban@smartlancedesigns.com",
        )
    )
    assert received_mail is not None

    accepted_mail = db_session.scalar(
        select(EmailEvent).where(
            EmailEvent.template == "ticket_transfer_accepted",
            EmailEvent.recipient_email == buyer.email,
        )
    )
    assert accepted_mail is not None

    # Token claim after completion should fail
    token_claim_after = client.post(
        "/api/v1/tickets/claim",
        headers=recipient_headers,
        json={"token": token},
    )
    assert token_claim_after.status_code == 400

    revoke = client.post(
        f"/api/v1/tickets/transfers/{body['id']}/revoke",
        headers=buyer_headers,
    )
    assert revoke.status_code == 400

    buyer_mine_after_claim = client.get("/api/v1/tickets/mine", headers=buyer_headers)
    assert not any(t["id"] == str(ticket.id) for t in buyer_mine_after_claim.json())


def test_revoke_pending_transfer_restores_ticket(client: TestClient, db_session: Session):
    _event, _host, _host_user, buyer, ticket, _qr = _seed_paid_ticket(
        db_session,
        slug="adv-revoke-xfer",
        buyer_email="revoke-buyer@example.com",
    )
    buyer_headers = _login(client, buyer.email)
    resp = client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=buyer_headers,
        json={
            "to_email": "revoke-recipient@example.com",
            "to_name": "Revoke Target",
        },
    )
    assert resp.status_code == 200, resp.json()
    transfer_id = resp.json()["id"]

    mine_empty = client.get("/api/v1/tickets/mine", headers=buyer_headers)
    assert not any(t["id"] == str(ticket.id) for t in mine_empty.json())

    history = client.get("/api/v1/tickets/transfers/mine", headers=buyer_headers)
    assert history.status_code == 200
    assert any(h["id"] == transfer_id and h["status"] == "pending" for h in history.json())

    resend = client.post(
        f"/api/v1/tickets/transfers/{transfer_id}/resend-invite",
        headers=buyer_headers,
    )
    assert resend.status_code == 200, resend.json()
    assert resend.json()["claim_path"].startswith("/tickets/claim?token=")

    link = client.post(
        f"/api/v1/tickets/transfers/{transfer_id}/claim-link",
        headers=buyer_headers,
    )
    assert link.status_code == 200
    assert link.json()["claim_path"].startswith("/tickets/claim?token=")

    revoked = client.post(
        f"/api/v1/tickets/transfers/{transfer_id}/revoke",
        headers=buyer_headers,
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    mine_back = client.get("/api/v1/tickets/mine", headers=buyer_headers)
    assert any(t["id"] == str(ticket.id) for t in mine_back.json())


def test_group_ticket_generation(client: TestClient, db_session: Session):
    event, _host, _hu, buyer, _ticket, _qr = _seed_paid_ticket(
        db_session,
        ticket_kind="group",
        seats_per_unit=4,
        slug="adv-group",
        buyer_email="group-buyer@example.com",
        host_email="group-host@example.com",
    )
    tickets = (
        db_session.query(Ticket).filter(Ticket.event_id == event.id).all()
    )
    assert len(tickets) == 4
    groups = db_session.query(TicketGroup).filter(TicketGroup.event_id == event.id).all()
    assert len(groups) == 1
    assert groups[0].expected_size == 4
    members = (
        db_session.query(TicketGroupMember)
        .filter(TicketGroupMember.group_id == groups[0].id)
        .all()
    )
    assert len(members) == 4
    buyer_headers = _login(client, buyer.email)
    mine = client.get("/api/v1/tickets/mine", headers=buyer_headers)
    assert mine.status_code == 200
    assert len(mine.json()) == 4


def test_table_ticket_validation(client: TestClient, db_session: Session):
    event, _host, host_user, buyer, ticket, qr = _seed_paid_ticket(
        db_session,
        ticket_kind="table",
        seats_per_unit=3,
        slug="adv-table",
        buyer_email="table-buyer@example.com",
        host_email="table-host@example.com",
    )
    tickets = db_session.query(Ticket).filter(Ticket.event_id == event.id).all()
    assert len(tickets) == 3
    assert all(t.table_label for t in tickets)
    assert ticket.seat_label == "S1"

    host_headers = _login(client, host_user.email)
    # Create manual table + assign
    created = client.post(
        f"/api/v1/tickets/events/{event.id}/tables",
        headers=host_headers,
        json={"table_label": "VIP-A", "capacity": 3},
    )
    assert created.status_code == 200
    reservation_id = created.json()["id"]
    assigned = client.patch(
        f"/api/v1/tickets/tables/{reservation_id}/assign",
        headers=host_headers,
        json={"ticket_id": str(ticket.id), "seat_label": "A1"},
    )
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "assigned"

    # Table seat tickets still validate at door
    ok = client.post(
        "/api/v1/checkins/validate",
        headers=host_headers,
        json={"event_id": str(event.id), "qr_payload": qr},
    )
    assert ok.status_code == 200
    assert ok.json()["outcome"] == "valid"

    # Cancelled fails
    buyer_headers = _login(client, buyer.email)
    wrong = client.post(
        f"/api/v1/tickets/{ticket.id}/cancel",
        headers=buyer_headers,
        json={"password": "wrong-password", "reason": "Changed plans"},
    )
    assert wrong.status_code == 403
    assert "password" in wrong.json()["detail"].lower()

    cancel = client.post(
        f"/api/v1/tickets/{ticket.id}/cancel",
        headers=buyer_headers,
        json={"password": "securepass1", "reason": "Changed plans"},
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
    bad = client.post(
        "/api/v1/checkins/validate",
        headers=host_headers,
        json={"event_id": str(event.id), "qr_payload": qr},
    )
    # QR may still decode but ticket cancelled / revoked
    assert bad.json()["outcome"] == "invalid"


def test_rotating_qr_validation(client: TestClient, db_session: Session):
    event, _host, host_user, buyer, ticket, _qr = _seed_paid_ticket(
        db_session,
        slug="adv-rotate",
        buyer_email="rotate-buyer@example.com",
        host_email="rotate-host@example.com",
    )
    buyer_headers = _login(client, buyer.email)
    host_headers = _login(client, host_user.email)

    mode = client.post(
        f"/api/v1/tickets/{ticket.id}/qr-mode",
        headers=buyer_headers,
        json={"qr_mode": "rotating"},
    )
    assert mode.status_code == 200
    first_qr = mode.json()["qr_payload"]
    assert first_qr
    assert mode.json()["qr_mode"] == "rotating"

    # Force expiry and fetch again to rotate
    token = db_session.query(TicketQrToken).filter_by(ticket_id=ticket.id).one()
    token.expires_at = datetime.now(UTC) - timedelta(seconds=5)
    db_session.commit()

    refreshed = client.get(f"/api/v1/tickets/{ticket.id}", headers=buyer_headers)
    assert refreshed.status_code == 200
    second_qr = refreshed.json()["qr_payload"]
    assert second_qr
    assert second_qr != first_qr

    old = client.post(
        "/api/v1/checkins/validate",
        headers=host_headers,
        json={"event_id": str(event.id), "qr_payload": first_qr},
    )
    assert old.json()["outcome"] == "invalid"

    new = client.post(
        "/api/v1/checkins/validate",
        headers=host_headers,
        json={"event_id": str(event.id), "qr_payload": second_qr},
    )
    assert new.json()["outcome"] == "valid"


def test_offline_sync_conflict(client: TestClient, db_session: Session):
    event, _host, host_user, _buyer, ticket, qr = _seed_paid_ticket(
        db_session,
        slug="adv-offline",
        buyer_email="offline-buyer@example.com",
        host_email="offline-host@example.com",
    )
    host_headers = _login(client, host_user.email)

    # Online check-in first
    online = client.post(
        "/api/v1/checkins/scan",
        headers=host_headers,
        json={"event_id": str(event.id), "qr_payload": qr},
    )
    assert online.status_code == 200
    assert online.json()["outcome"] == "success"

    # Offline sync of same ticket → conflict
    sync = client.post(
        "/api/v1/checkins/offline/sync",
        headers=host_headers,
        json={
            "event_id": str(event.id),
            "client_batch_id": "batch-1",
            "device_label": "Door iPad",
            "scans": [
                {
                    "client_scan_id": "local-1",
                    "public_code": ticket.public_code,
                    "scanned_at": datetime.now(UTC).isoformat(),
                }
            ],
        },
    )
    assert sync.status_code == 200, sync.json()
    body = sync.json()
    assert body["conflict_count"] == 1
    assert body["results"][0]["sync_status"] == "conflict"

    # Fresh ticket offline accept
    code = new_public_ticket_code()
    jti = new_qr_jti()
    # Create another active ticket on same event
    from app.payments.models import OrderItem as OI

    order = db_session.query(Order).filter(Order.event_id == event.id).one()
    item = db_session.query(OI).filter(OI.order_id == order.id).first()
    t2 = Ticket(
        public_code=code,
        order_id=order.id,
        order_item_id=item.id,
        event_id=event.id,
        ticket_type_id=ticket.ticket_type_id,
        buyer_user_id=ticket.buyer_user_id,
        status="active",
        ticket_type_name=ticket.ticket_type_name,
        holder_name="Second",
        holder_email="second@example.com",
    )
    db_session.add(t2)
    db_session.flush()
    signed = create_signed_qr_payload(public_code=code, event_id=event.id, jti=jti)
    db_session.add(
        TicketQrToken(
            ticket_id=t2.id,
            jti_hash=hash_jti(jti),
            signed_payload=signed,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
    )
    db_session.commit()

    sync2 = client.post(
        "/api/v1/checkins/offline/sync",
        headers=host_headers,
        json={
            "event_id": str(event.id),
            "client_batch_id": "batch-2",
            "scans": [
                {
                    "client_scan_id": "local-2",
                    "qr_payload": signed,
                    "scanned_at": datetime.now(UTC).isoformat(),
                }
            ],
        },
    )
    assert sync2.status_code == 200
    assert sync2.json()["accepted_count"] == 1
    assert sync2.json()["results"][0]["sync_status"] == "accepted"


def test_ticket_pdf_download_owner_only(client: TestClient, db_session: Session):
    event, _host, host_user, buyer, ticket, _qr = _seed_paid_ticket(
        db_session,
        slug="adv-pdf",
        buyer_email="pdf-buyer@example.com",
        host_email="pdf-host@example.com",
    )
    buyer_headers = _login(client, buyer.email)
    host_headers = _login(client, host_user.email)

    denied = client.get(f"/api/v1/tickets/{ticket.id}/pdf", headers=host_headers)
    assert denied.status_code == 404

    # Rotating mode should still produce a lasting static PDF QR
    mode = client.post(
        f"/api/v1/tickets/{ticket.id}/qr-mode",
        headers=buyer_headers,
        json={"qr_mode": "rotating"},
    )
    assert mode.status_code == 200

    pdf = client.get(f"/api/v1/tickets/{ticket.id}/pdf", headers=buyer_headers)
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert "attachment" in pdf.headers.get("content-disposition", "").lower()
    assert pdf.content[:4] == b"%PDF"
    assert len(pdf.content) > 500

    refreshed = client.get(f"/api/v1/tickets/{ticket.id}", headers=buyer_headers)
    assert refreshed.status_code == 200
    assert refreshed.json()["qr_mode"] == "static"

    # Cancelled tickets download as clearly invalid (no live QR refresh)
    cancel = client.post(
        f"/api/v1/tickets/{ticket.id}/cancel",
        headers=buyer_headers,
        json={"password": "securepass1"},
    )
    assert cancel.status_code == 200
    cancelled_pdf = client.get(f"/api/v1/tickets/{ticket.id}/pdf", headers=buyer_headers)
    assert cancelled_pdf.status_code == 200, cancelled_pdf.text
    assert cancelled_pdf.content[:4] == b"%PDF"
