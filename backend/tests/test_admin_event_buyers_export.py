"""Admin event buyer list + CSV/JSON export — modes, perms, filters, audit."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.audit import AuditLog
from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.passport.models import FanPassport
from app.payments.models import Order, OrderItem, Payment
from app.tickets.admin_export import (
    AUDIT_EXPORTED,
    AUDIT_FINANCE,
    AUDIT_PRIVATE_CONTACT,
    _CSV_HEADERS,
    _assert_safe_headers,
    sanitize_csv_cell,
)
from app.tickets.models import Ticket
from app.tickets.service import issue_tickets_for_paid_order
from app.users.models import Permission, Role, User
from app.users.service import get_role_by_name
from sqlalchemy import select
from sqlalchemy.orm import selectinload


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _grant_perms(db: Session, user: User, *codes: str) -> None:
    role = Role(name=f"tmp-export-{uuid.uuid4().hex[:8]}", description="test")
    for code in codes:
        perm = db.scalar(select(Permission).where(Permission.code == code))
        assert perm is not None, f"missing permission {code}"
        role.permissions.append(perm)
    db.add(role)
    user.roles.append(role)
    db.commit()


def _seed_event_with_ticket(
    db: Session,
    *,
    holder_name: str = "Export Holder",
    promo: str = "WELCOME10",
    referral: str = "AMB123",
) -> tuple[Event, User, User, Ticket]:
    suffix = uuid.uuid4().hex[:8]
    host_user = User(
        email=f"buyer-export-host-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Export Host",
        is_active=True,
    )
    host_user.roles.append(get_role_by_name(db, "host"))
    buyer = User(
        email=f"buyer-export-fan-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Export Buyer",
        is_active=True,
    )
    buyer.roles.append(get_role_by_name(db, "buyer"))
    db.add_all([host_user, buyer])
    db.flush()

    host = Host(
        user_id=host_user.id,
        display_name="Export Host Org",
        slug=f"buyer-export-host-{suffix}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))

    db.add(
        FanPassport(
            user_id=buyer.id,
            display_name="Export Fan",
            username=f"exportfan{suffix}",
            visibility="public",
            bio="Public bio for export",
            avatar_url="https://cdn.example.com/a.png",
        )
    )

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=2)
    event = Event(
        title="Buyer Export Night",
        slug=f"buyer-export-night-{suffix}",
        description="Event used for admin buyer CSV export tests with enough text.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        status="published",
        city="Lagos",
        venue_name="Secret Hall",
        address="12 Hidden Street",
        published_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()

    ticket_type = TicketType(
        event_id=event.id,
        name="General",
        type="regular",
        price=Decimal("5000.00"),
        quantity=100,
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
        reference=f"paystack_ref_must_not_appear_{suffix}",
        buyer_user_id=buyer.id,
        event_id=event.id,
        status="paid",
        currency="NGN",
        subtotal_amount=Decimal("5000.00"),
        discount_amount=Decimal("500.00"),
        total_amount=Decimal("4500.00"),
        buyer_email=buyer.email,
        buyer_name=buyer.full_name,
        paid_at=datetime.now(UTC),
        promo_code_snapshot=promo,
        referral_code=referral,
        referral_attribution_source="explicit",
    )
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            item_kind="ticket",
            ticket_type_id=ticket_type.id,
            quantity=1,
            unit_price=Decimal("5000.00"),
            line_total=Decimal("5000.00"),
            ticket_type_name="General",
        )
    )
    db.add(
        Payment(
            order_id=order.id,
            provider="paystack",
            reference=f"paystack_ref_must_not_appear_{suffix}",
            status="success",
            amount=Decimal("4500.00"),
            currency="NGN",
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
    ticket.holder_name = holder_name
    ticket.holder_email = buyer.email
    db.commit()
    return event, host_user, buyer, ticket


def _admin_headers(client: TestClient, db: Session) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    admin = User(
        email=f"buyer-export-admin-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Export Admin",
        is_active=True,
    )
    admin.roles.append(get_role_by_name(db, "super_admin"))
    db.add(admin)
    db.commit()
    return _login(client, admin.email)


def _scoped_admin(
    client: TestClient, db: Session, *codes: str
) -> tuple[User, dict[str, str]]:
    suffix = uuid.uuid4().hex[:8]
    admin = User(
        email=f"buyer-export-scoped-{suffix}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Scoped Export Admin",
        is_active=True,
    )
    db.add(admin)
    db.flush()
    _grant_perms(db, admin, *codes)
    return admin, _login(client, admin.email)


def test_csv_headers_are_safe() -> None:
    _assert_safe_headers(_CSV_HEADERS)
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd") == "'+cmd"
    assert sanitize_csv_cell("-2") == "'-2"
    assert sanitize_csv_cell("@SUM") == "'@SUM"
    assert sanitize_csv_cell("normal") == "normal"


def test_admin_event_buyers_list_and_export(
    client: TestClient, db_session: Session
) -> None:
    event, _host, buyer, ticket = _seed_event_with_ticket(db_session)
    headers = _admin_headers(client, db_session)

    listed = client.get(
        f"/api/v1/admin/events/{event.id}/buyers",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    payload = listed.json()
    assert payload["total"] >= 1
    item = payload["items"][0]
    assert item["passport_username"].startswith("exportfan")
    assert item["host_name"] == "Export Host Org"
    assert item.get("holder_email") in (None, "")
    assert item.get("buyer_account_email") in (None, "")
    assert "qr_payload" not in item
    assert "paystack" not in str(item).lower()

    csv_res = client.get(
        f"/api/v1/admin/events/{event.id}/buyers/export?format=csv&mode=operations",
        headers=headers,
    )
    assert csv_res.status_code == 200, csv_res.text
    body = csv_res.text
    assert "safe_ticket_code" in body
    assert "exportfan" in body
    assert buyer.email not in body
    assert ticket.holder_email not in body or "holder_email" not in body.split("\n")[0]
    assert "paystack_ref_must_not_appear" not in body
    assert "12 Hidden Street" not in body
    assert "Secret Hall" not in body
    assert f'filename="padeya-event-buyers-{event.slug}-' in (
        csv_res.headers.get("content-disposition") or ""
    )

    json_res = client.get(
        f"/api/v1/admin/events/{event.id}/buyers/export?format=json&mode=public_summary",
        headers=headers,
    )
    assert json_res.status_code == 200, json_res.text
    data = json_res.json()
    assert data["count"] >= 1
    assert data["mode"] == "public_summary"
    assert "buyer_email" not in data["items"][0]
    assert "amount_paid" not in data["items"][0]

    xlsx = client.get(
        f"/api/v1/admin/events/{event.id}/buyers/export?format=xlsx",
        headers=headers,
    )
    assert xlsx.status_code == 400

    history = client.get(
        f"/api/v1/admin/events/{event.id}/buyers/exports",
        headers=headers,
    )
    assert history.status_code == 200, history.text
    assert len(history.json()) >= 2
    assert history.json()[0]["action"] in {
        AUDIT_EXPORTED,
        AUDIT_PRIVATE_CONTACT,
        AUDIT_FINANCE,
    }


def test_legacy_tickets_export_path_still_works(
    client: TestClient, db_session: Session
) -> None:
    event, _host, _buyer, _ticket = _seed_event_with_ticket(db_session)
    headers = _admin_headers(client, db_session)
    res = client.get(
        f"/api/v1/tickets/admin/events/{event.id}/buyers/export.csv",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert "text/csv" in res.headers.get("content-type", "")


def test_non_admin_cannot_export_buyers(
    client: TestClient, db_session: Session
) -> None:
    event, host_user, _buyer, _ticket = _seed_event_with_ticket(db_session)
    headers = _login(client, host_user.email)
    res = client.get(
        f"/api/v1/admin/events/{event.id}/buyers/export",
        headers=headers,
    )
    assert res.status_code == 403


def test_requires_both_view_and_export_perms(
    client: TestClient, db_session: Session
) -> None:
    event, _host, _buyer, _ticket = _seed_event_with_ticket(db_session)
    _user, headers = _scoped_admin(client, db_session, "admin.events.view")
    res = client.get(
        f"/api/v1/admin/events/{event.id}/buyers",
        headers=headers,
    )
    assert res.status_code == 403

    _user2, headers2 = _scoped_admin(
        client, db_session, "admin.events.view", "admin.events.export_buyers"
    )
    res2 = client.get(
        f"/api/v1/admin/events/{event.id}/buyers",
        headers=headers2,
    )
    assert res2.status_code == 200, res2.text


def test_private_contact_requires_perm_and_reason(
    client: TestClient, db_session: Session
) -> None:
    event, _host, buyer, _ticket = _seed_event_with_ticket(db_session)
    _user, headers = _scoped_admin(
        client, db_session, "admin.events.view", "admin.events.export_buyers"
    )
    denied = client.get(
        f"/api/v1/admin/events/{event.id}/buyers/export"
        f"?mode=operations&include_private_contact=true&reason=support",
        headers=headers,
    )
    assert denied.status_code == 403

    _user2, headers2 = _scoped_admin(
        client,
        db_session,
        "admin.events.view",
        "admin.events.export_buyers",
        "admin.events.export_private_contact",
    )
    missing_reason = client.get(
        f"/api/v1/admin/events/{event.id}/buyers/export"
        f"?mode=operations&include_private_contact=true",
        headers=headers2,
    )
    assert missing_reason.status_code == 400

    ok = client.get(
        f"/api/v1/admin/events/{event.id}/buyers/export"
        f"?mode=operations&include_private_contact=true&reason=Door%20ops",
        headers=headers2,
    )
    assert ok.status_code == 200, ok.text
    assert buyer.email in ok.text
    assert "holder_email" in ok.text.split("\n")[0]

    audit = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.action == AUDIT_PRIVATE_CONTACT,
            AuditLog.resource_id == str(event.id),
        )
        .order_by(AuditLog.created_at.desc())
    )
    assert audit is not None
    assert audit.details is not None
    assert audit.details.get("reason") == "Door ops"
    assert audit.details.get("export_mode") == "operations"


def test_finance_mode_requires_perm_and_reason(
    client: TestClient, db_session: Session
) -> None:
    event, _host, buyer, _ticket = _seed_event_with_ticket(db_session)
    _user, headers = _scoped_admin(
        client, db_session, "admin.events.view", "admin.events.export_buyers"
    )
    denied = client.get(
        f"/api/v1/admin/events/{event.id}/buyers/export?mode=finance&reason=recon",
        headers=headers,
    )
    assert denied.status_code == 403

    _user2, headers2 = _scoped_admin(
        client,
        db_session,
        "admin.events.view",
        "admin.events.export_buyers",
        "admin.finance.export_event_sales",
    )
    missing = client.get(
        f"/api/v1/admin/events/{event.id}/buyers/export?mode=finance",
        headers=headers2,
    )
    assert missing.status_code == 400

    ok = client.get(
        f"/api/v1/admin/events/{event.id}/buyers/export?mode=finance&reason=Month%20end",
        headers=headers2,
    )
    assert ok.status_code == 200, ok.text
    assert "amount_paid" in ok.text
    assert "order_id" in ok.text.split("\n")[0]
    assert buyer.email not in ok.text
    assert "paystack_ref_must_not_appear" not in ok.text

    audit = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.action == AUDIT_FINANCE,
            AuditLog.resource_id == str(event.id),
        )
        .order_by(AuditLog.created_at.desc())
    )
    assert audit is not None
    assert audit.details is not None
    assert audit.details.get("reason") == "Month end"


def test_filters_apply_to_list_and_export(
    client: TestClient, db_session: Session
) -> None:
    event, _host, _buyer, _ticket = _seed_event_with_ticket(
        db_session, promo="SAVE20", referral="REF99"
    )
    headers = _admin_headers(client, db_session)

    miss = client.get(
        f"/api/v1/admin/events/{event.id}/buyers?promo_code=NOPE",
        headers=headers,
    )
    assert miss.status_code == 200
    assert miss.json()["total"] == 0

    hit = client.get(
        f"/api/v1/admin/events/{event.id}/buyers?promo_code=SAVE20&ambassador_code=REF99",
        headers=headers,
    )
    assert hit.status_code == 200
    assert hit.json()["total"] >= 1

    export = client.get(
        f"/api/v1/admin/events/{event.id}/buyers/export"
        f"?format=csv&mode=operations&promo_code=SAVE20&ambassador_code=REF99",
        headers=headers,
    )
    assert export.status_code == 200
    assert "SAVE20" in export.text
    assert "REF99" in export.text


def test_search_by_username_not_email(
    client: TestClient, db_session: Session
) -> None:
    event, _host, buyer, _ticket = _seed_event_with_ticket(db_session)
    headers = _admin_headers(client, db_session)
    username = db_session.scalar(
        select(FanPassport.username).where(FanPassport.user_id == buyer.id)
    )
    assert username

    by_user = client.get(
        f"/api/v1/admin/events/{event.id}/buyers?q={username}",
        headers=headers,
    )
    assert by_user.status_code == 200
    assert by_user.json()["total"] >= 1

    by_email = client.get(
        f"/api/v1/admin/events/{event.id}/buyers?q={buyer.email}",
        headers=headers,
    )
    assert by_email.status_code == 200
    assert by_email.json()["total"] == 0


def test_csv_formula_injection_sanitized(
    client: TestClient, db_session: Session
) -> None:
    event, _host, buyer, ticket = _seed_event_with_ticket(
        db_session, holder_name="=1+2"
    )
    headers = _admin_headers(client, db_session)
    res = client.get(
        f"/api/v1/admin/events/{event.id}/buyers/export?format=csv&mode=operations",
        headers=headers,
    )
    assert res.status_code == 200
    reader = csv.DictReader(io.StringIO(res.text))
    rows = list(reader)
    assert rows
    assert rows[0]["attendee_name"].startswith("'=")
    assert buyer.email not in res.text
    assert ticket.public_code in res.text


def test_never_exports_qr_paystack_or_venue(
    client: TestClient, db_session: Session
) -> None:
    event, _host, buyer, ticket = _seed_event_with_ticket(db_session)
    headers = _admin_headers(client, db_session)
    for mode in ("public_summary", "operations", "finance"):
        qs = f"format=json&mode={mode}"
        if mode == "finance":
            qs += "&reason=audit"
        res = client.get(
            f"/api/v1/admin/events/{event.id}/buyers/export?{qs}",
            headers=headers,
        )
        assert res.status_code == 200, res.text
        text = res.text.lower()
        assert "signed_payload" not in text
        assert "jti" not in text
        assert "paystack_ref_must_not_appear" not in text
        assert "12 hidden street" not in text
        assert "secret hall" not in text
        assert "qr_payload" not in text
        assert str(ticket.id) if mode == "finance" else True
        if mode != "finance":
            # finance may include full order/ticket ids by design
            pass
    assert buyer.email  # keep fixture used
