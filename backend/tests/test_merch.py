"""Event-linked merchandise catalog, checkout, and fulfillment tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from unittest.mock import patch

from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.merch.models import EventMerchProduct, EventMerchVariant, MerchFulfillment
from app.payments.paystack import sign_body_for_tests
from app.tickets.models import Ticket
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str, password: str = "securepass1") -> dict[str, str]:
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_host_event(db: Session) -> tuple[User, Host, Event, TicketType]:
    host_user = User(
        email="merchhost@example.com",
        password_hash="x",
        full_name="Merch Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    host_user.roles.append(role)
    db.add(host_user)
    db.flush()

    # Use real password hash for login in host flows that need CurrentUser
    from app.core.security import hash_password

    host_user.password_hash = hash_password("securepass1")

    host = Host(
        user_id=host_user.id,
        display_name="Merch Host",
        slug="merch-host",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(
        HostProfile(
            host_id=host.id,
            city="Lagos",
            merch_storefront_enabled=True,
            merch_storefront_visibility="public",
        )
    )

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=10)
    event = Event(
        title="Merch Fest",
        slug="merch-fest",
        description="Published event for merch tests with enough detail for validation.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=4),
        venue_name="Yard",
        city="Lagos",
        state="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()

    ticket_type = TicketType(
        event_id=event.id,
        name="GA",
        type="regular",
        description="Entry",
        price=Decimal("3000.00"),
        quantity=50,
        quantity_sold=0,
        quantity_reserved=0,
        min_per_order=1,
        max_per_order=5,
        visibility="public",
        status="active",
    )
    db.add(ticket_type)
    db.commit()
    db.refresh(event)
    db.refresh(ticket_type)
    db.refresh(host_user)
    return host_user, host, event, ticket_type


def _register_buyer(client: TestClient, email: str) -> dict[str, str]:
    # full_name (and therefore the derived username) must be unique per buyer —
    # the register endpoint slugifies full_name into a username and 409s on
    # collision, which would silently block registration + the login below.
    local_part = email.split("@")[0]
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass1",
            "full_name": f"Merch Buyer {local_part}",
            "gender": "prefer_not_to_say",
        },
    )
    assert res.status_code == 201, res.text
    return _login(client, email)


def _create_active_product(
    client: TestClient,
    host_headers: dict[str, str],
    event_id: UUID,
    *,
    inventory: int = 5,
    status: str = "active",
) -> dict:
    response = client.post(
        f"/api/v1/merch/events/{event_id}/products",
        headers=host_headers,
        json={
            "name": "Festival Tee",
            "description": "Soft cotton tee",
            "base_price": "7500.00",
            "status": status,
            "pickup_instructions": "Merch stand",
            "variants": [
                {
                    "label": "L / Black",
                    "inventory_count": inventory,
                    "status": "active",
                }
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _pay_order(client: TestClient, headers: dict[str, str], order: dict) -> None:
    with patch(
        "app.payments.service.initialize_transaction",
        return_value={
            "authorization_url": "https://checkout.paystack.com/test",
            "access_code": "ACCESS",
            "reference": order["reference"],
        },
    ):
        client.post(f"/api/v1/payments/checkout/{order['id']}", headers=headers)

    # Unique Paystack event id per order so multi-pay tests stay idempotent-safe.
    event_id = int(UUID(order["id"]).int % 10**9) + 1000
    payload = {
        "event": "charge.success",
        "data": {
            "id": event_id,
            "reference": order["reference"],
            "amount": int(Decimal(order["total_amount"]) * 100),
            "status": "success",
        },
    }
    body = json.dumps(payload).encode("utf-8")
    ok = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=body,
        headers={
            "x-paystack-signature": sign_body_for_tests(body),
            "content-type": "application/json",
        },
    )
    assert ok.status_code == 200, ok.text


def test_draft_product_not_in_public_catalog(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    _create_active_product(client, host_headers, event.id, status="draft")

    catalog = client.get(f"/api/v1/merch/events/{event.id}/catalog")
    assert catalog.status_code == 200
    assert catalog.json() == []


def test_merch_only_blocked_unless_host_enables(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=2)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merchbuyer0@example.com")

    blocked = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert blocked.status_code == 400
    assert "merch-only" in blocked.json()["detail"].lower()


def test_merch_only_order_creates_fulfillment_no_tickets(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=3)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merchbuyer1@example.com")

    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    assert body["total_amount"] == "7500.00"
    assert body["items"][0]["item_kind"] == "merch"

    _pay_order(client, buyer_headers, body)

    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(body["id"])))
    )
    assert tickets == []

    fulfills = list(
        db_session.scalars(
            select(MerchFulfillment).where(MerchFulfillment.order_id == UUID(body["id"]))
        )
    )
    assert len(fulfills) == 1
    assert fulfills[0].status == "awaiting_pickup"
    assert fulfills[0].pickup_code.startswith("MRCH-")

    variant = db_session.get(EventMerchVariant, UUID(variant_id))
    assert variant is not None
    assert variant.inventory_count == 2

    mine = client.get("/api/v1/merch/mine", headers=buyer_headers)
    assert mine.status_code == 200
    assert len(mine.json()) == 1


def test_ticket_plus_merch_order(client: TestClient, db_session: Session):
    _, _, event, ticket_type = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=4)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merchbuyer2@example.com")

    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {"item_kind": "ticket", "ticket_type_id": str(ticket_type.id), "quantity": 1},
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                },
            ],
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    assert Decimal(body["total_amount"]) == Decimal("10500.00")

    _pay_order(client, buyer_headers, body)

    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(body["id"])))
    )
    assert len(tickets) == 1
    fulfills = list(
        db_session.scalars(
            select(MerchFulfillment).where(MerchFulfillment.order_id == UUID(body["id"]))
        )
    )
    assert len(fulfills) == 1
    assert fulfills[0].status == "awaiting_pickup"


def test_fulfill_rejects_double_pickup(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merchbuyer3@example.com")

    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    ).json()
    _pay_order(client, buyer_headers, order)

    fulfill = db_session.scalar(
        select(MerchFulfillment).where(MerchFulfillment.order_id == UUID(order["id"]))
    )
    assert fulfill is not None
    assert fulfill.pickup_code.startswith("MRCH-")

    first = client.post(
        f"/api/v1/merch/fulfillments/{fulfill.id}/fulfill",
        headers=host_headers,
    )
    assert first.status_code == 200
    body = first.json()
    assert body["status"] == "fulfilled"
    assert body["fulfilled_by_name"]
    assert body["fulfilled_at"]

    second = client.post(
        f"/api/v1/merch/fulfillments/{fulfill.id}/fulfill",
        headers=host_headers,
    )
    assert second.status_code == 409
    assert "already" in second.json()["detail"].lower()


def test_cancelled_fulfillment_cannot_be_picked_up(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merchbuyer_cancel_pickup@example.com")

    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    ).json()
    _pay_order(client, buyer_headers, order)

    fulfill = db_session.scalar(
        select(MerchFulfillment).where(MerchFulfillment.order_id == UUID(order["id"]))
    )
    assert fulfill is not None
    fulfill.status = "cancelled"
    db_session.commit()

    blocked = client.post(
        f"/api/v1/merch/fulfillments/{fulfill.id}/fulfill",
        headers=host_headers,
    )
    assert blocked.status_code == 400
    assert "cancelled" in blocked.json()["detail"].lower()


def test_stranger_cannot_fulfill_merch(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merchbuyer_stranger@example.com")

    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    ).json()
    _pay_order(client, buyer_headers, order)
    fulfill = db_session.scalar(
        select(MerchFulfillment).where(MerchFulfillment.order_id == UUID(order["id"]))
    )
    assert fulfill is not None

    stranger = _register_buyer(client, "notstaff@example.com")
    denied = client.post(
        f"/api/v1/merch/fulfillments/{fulfill.id}/fulfill",
        headers=stranger,
    )
    assert denied.status_code == 403


def test_inventory_cannot_oversell(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=1)
    variant_id = product["variants"][0]["id"]
    buyer_a = _register_buyer(client, "merchbuyer4@example.com")
    buyer_b = _register_buyer(client, "merchbuyer5@example.com")

    order_a = client.post(
        "/api/v1/orders",
        headers=buyer_a,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert order_a.status_code == 201
    _pay_order(client, buyer_a, order_a.json())

    order_b = client.post(
        "/api/v1/orders",
        headers=buyer_b,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert order_b.status_code == 409


def test_unpaid_order_has_no_fulfillment(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merchbuyer6@example.com")

    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert order.status_code == 201
    fulfills = list(
        db_session.scalars(
            select(MerchFulfillment).where(
                MerchFulfillment.order_id == UUID(order.json()["id"])
            )
        )
    )
    assert fulfills == []
    product_row = db_session.get(EventMerchProduct, UUID(product["id"]))
    assert product_row is not None
    variant = db_session.get(EventMerchVariant, UUID(variant_id))
    assert variant is not None
    assert variant.inventory_count == 5


def _admin_headers(client: TestClient, db: Session, email: str = "merchadmin@example.com") -> dict[str, str]:
    from app.core.security import hash_password

    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Merch Admin",
        is_active=True,
    )
    role = get_role_by_name(db, "super_admin")
    assert role is not None
    user.roles.append(role)
    db.add(user)
    db.commit()
    return _login(client, email)


def test_admin_hide_removes_from_catalog_and_blocks_checkout(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]
    admin = _admin_headers(client, db_session)

    hide = client.post(
        f"/api/v1/merch/admin/products/{product['id']}/moderate",
        headers=admin,
        json={"action": "hide", "note": "Unsafe listing"},
    )
    assert hide.status_code == 200, hide.text
    assert hide.json()["moderation_status"] == "hidden"
    assert hide.json()["status"] == "paused"

    catalog = client.get(f"/api/v1/merch/events/{event.id}/catalog")
    assert catalog.status_code == 200
    assert catalog.json() == []

    buyer = _register_buyer(client, "merchbuyer-hidden@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert order.status_code == 400

    # Host sees hidden status + reason; cannot reactivate until restore.
    host_view = client.get(
        f"/api/v1/merch/products/{product['id']}", headers=host_headers
    )
    assert host_view.status_code == 200, host_view.text
    assert host_view.json()["moderation_status"] == "hidden"
    assert host_view.json()["moderation_note"] == "Unsafe listing"
    activate = client.patch(
        f"/api/v1/merch/products/{product['id']}",
        headers=host_headers,
        json={"status": "active"},
    )
    assert activate.status_code == 400


def test_admin_product_list_includes_sales_and_reports(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    buyer = _register_buyer(client, "merchbuyer-admin-list@example.com")
    client.post(
        f"/api/v1/merch/products/{product['id']}/report",
        headers=buyer,
        json={"reason": "Misleading product photo here", "details": "Looks edited"},
    )
    admin = _admin_headers(client, db_session, "merchadmin-list@example.com")
    listed = client.get("/api/v1/merch/admin/products", headers=admin)
    assert listed.status_code == 200, listed.text
    row = next(r for r in listed.json() if r["id"] == product["id"])
    assert row["host_name"]
    assert row["event_title"]
    assert "sold_count" in row
    assert row["report_count"] >= 1
    assert row["open_report_count"] >= 1
    assert row["created_at"]

    detail = client.get(
        f"/api/v1/merch/admin/products/{product['id']}", headers=admin
    )
    assert detail.status_code == 200
    assert detail.json()["name"] == product["name"]


def test_admin_report_reviewing_and_snapshot(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    buyer = _register_buyer(client, "merchbuyer-reviewing@example.com")
    report = client.post(
        f"/api/v1/merch/products/{product['id']}/report",
        headers=buyer,
        json={
            "reason": "Off-platform payment pressure",
            "details": "Listing pushed bank transfer",
        },
    )
    assert report.status_code == 200, report.text
    report_id = report.json()["id"]
    assert report.json()["product_snapshot"]["name"] == product["name"]
    assert report.json()["details"] == "Listing pushed bank transfer"

    admin = _admin_headers(client, db_session, "merchadmin-review@example.com")
    reviewing = client.patch(
        f"/api/v1/merch/admin/reports/{report_id}",
        headers=admin,
        json={"status": "reviewing", "admin_notes": "Checking photos"},
    )
    assert reviewing.status_code == 200, reviewing.text
    assert reviewing.json()["status"] == "reviewing"
    assert reviewing.json()["admin_notes"] == "Checking photos"

    resolved = client.post(
        f"/api/v1/merch/admin/reports/{report_id}/resolve",
        headers=admin,
        json={
            "resolution": "resolved",
            "note": "Hidden after review",
            "admin_notes": "Confirmed off-platform ask",
            "moderate_action": "hide",
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["admin_notes"] == "Confirmed off-platform ask"


def test_admin_orders_omit_payment_amounts(client: TestClient, db_session: Session):
    _, _, event, ticket_type = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=2)
    variant_id = product["variants"][0]["id"]
    buyer = _register_buyer(client, "merchbuyer-admin-orders@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [
                {"ticket_type_id": str(ticket_type.id), "quantity": 1},
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                },
            ],
        },
    )
    assert order.status_code == 201, order.text
    _pay_order(client, buyer, order.json())

    admin = _admin_headers(client, db_session, "merchadmin2@example.com")
    rows = client.get("/api/v1/merch/admin/orders", headers=admin)
    assert rows.status_code == 200, rows.text
    data = rows.json()
    assert len(data) >= 1
    row = data[0]
    assert "order_reference" in row
    assert "pickup_code" in row
    assert "total_amount" not in row
    assert "unit_price" not in row
    assert "payment_id" not in row
    assert "paystack" not in str(row).lower()


def test_buyer_report_and_admin_resolve(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    buyer = _register_buyer(client, "merchbuyer-report@example.com")

    report = client.post(
        f"/api/v1/merch/products/{product['id']}/report",
        headers=buyer,
        json={"reason": "Counterfeit branding on this tee"},
    )
    assert report.status_code == 200, report.text
    assert report.json()["status"] == "open"

    admin = _admin_headers(client, db_session, "merchadmin3@example.com")
    listed = client.get("/api/v1/merch/admin/reports?status=open", headers=admin)
    assert listed.status_code == 200
    assert len(listed.json()) >= 1

    resolved = client.post(
        f"/api/v1/merch/admin/reports/{report.json()['id']}/resolve",
        headers=admin,
        json={
            "resolution": "resolved",
            "note": "Removed counterfeit listing",
            "moderate_action": "hide",
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "resolved"

    product_row = db_session.get(EventMerchProduct, UUID(product["id"]))
    assert product_row is not None
    db_session.refresh(product_row)
    assert product_row.moderation_status == "hidden"


def test_order_item_snapshots_stable_after_product_edit(
    client: TestClient, db_session: Session
):
    _, _, event, ticket_type = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=3)
    variant_id = product["variants"][0]["id"]
    buyer = _register_buyer(client, "merchbuyer-snap@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [
                {"ticket_type_id": str(ticket_type.id), "quantity": 1},
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                },
            ],
        },
    )
    assert order.status_code == 201, order.text
    order_body = order.json()
    merch_line = next(i for i in order_body["items"] if i.get("item_kind") == "merch")
    assert merch_line["product_name"] == "Festival Tee"
    assert merch_line["variant_label"] == "L / Black"
    assert Decimal(merch_line["unit_price"]) == Decimal("7500.00")

    patched = client.patch(
        f"/api/v1/merch/products/{product['id']}",
        headers=host_headers,
        json={"name": "Renamed Tee", "base_price": "9999.00"},
    )
    assert patched.status_code == 200
    client.patch(
        f"/api/v1/merch/variants/{variant_id}",
        headers=host_headers,
        json={"label": "XL / Red"},
    )

    _pay_order(client, buyer, order_body)
    mine = client.get("/api/v1/merch/mine", headers=buyer)
    assert mine.status_code == 200
    row = mine.json()[0]
    assert row["product_name_snapshot"] == "Festival Tee"
    assert row["variant_label_snapshot"] == "L / Black"

    from app.payments.models import OrderItem

    item = db_session.get(OrderItem, UUID(merch_line["id"]))
    assert item is not None
    assert item.product_name == "Festival Tee"
    assert item.variant_label == "L / Black"
    assert Decimal(item.unit_price) == Decimal("7500.00")


def test_private_event_redacts_public_pickup_instructions(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.location_visibility = "hidden_until_payment"
    event.address = "12 Secret Street, Lagos"
    event.public_location_label = "Lagos Island area"
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    created = client.post(
        f"/api/v1/merch/events/{event.id}/products",
        headers=host_headers,
        json={
            "name": "Secret Cap",
            "product_type": "cap",
            "base_price": "3000.00",
            "status": "active",
            "pickup_instructions": "Collect at 12 Secret Street side door",
            "pickup_location_label": "Merch stand",
            "pickup_time_window": "After doors",
            "show_on_event_page": True,
            "variants": [
                {"label": "One size", "inventory_count": 5, "status": "active"}
            ],
        },
    )
    assert created.status_code == 200, created.text
    catalog = client.get(f"/api/v1/merch/events/{event.id}/catalog")
    assert catalog.status_code == 200
    row = catalog.json()[0]
    assert "Secret Street" not in (row.get("pickup_instructions") or "")
    assert row["pickup_location_label"] == "Merch stand"
    assert row["pickup_time_window"] == "After doors"


def test_private_event_redacts_street_like_pickup_label(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.location_visibility = "area_only"
    event.address = "12 Secret Street, Lagos"
    event.public_location_label = "Lagos Island area"
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    created = client.post(
        f"/api/v1/merch/events/{event.id}/products",
        headers=host_headers,
        json={
            "name": "Area Cap",
            "product_type": "cap",
            "base_price": "3000.00",
            "status": "active",
            "pickup_location_label": "12 Secret Street merch table",
            "pickup_instructions": "Ask security for the stand",
            "show_on_event_page": True,
            "variants": [
                {"label": "One size", "inventory_count": 5, "status": "active"}
            ],
        },
    )
    assert created.status_code == 200, created.text
    catalog = client.get(f"/api/v1/merch/events/{event.id}/catalog")
    assert catalog.status_code == 200
    row = catalog.json()[0]
    assert "Secret Street" not in (row.get("pickup_location_label") or "")
    assert "Secret Street" not in (row.get("pickup_instructions") or "")


def test_unsafe_merch_copy_rejected_on_create(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    blocked = client.post(
        f"/api/v1/merch/events/{event.id}/products",
        headers=host_headers,
        json={
            "name": "Pay Outside Tee",
            "product_type": "t_shirt",
            "base_price": "5000.00",
            "status": "active",
            "description": "Pay via https://paystack.com/pay/demo instead",
            "variants": [
                {"label": "M", "inventory_count": 3, "status": "active"}
            ],
        },
    )
    assert blocked.status_code == 400
    assert "Unsafe content" in blocked.json()["detail"]


def test_pending_mine_uses_public_safe_pickup(client: TestClient, db_session: Session):
    _, _, event, ticket_type = _seed_host_event(db_session)
    event.location_visibility = "hidden_until_payment"
    event.address = "99 Hidden Close, Lagos"
    event.public_location_label = "Island area"
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    created = client.post(
        f"/api/v1/merch/events/{event.id}/products",
        headers=host_headers,
        json={
            "name": "Pending Cap",
            "product_type": "cap",
            "base_price": "2500.00",
            "status": "active",
            "pickup_location_label": "Merch stand",
            "pickup_instructions": "Collect at 99 Hidden Close after entry",
            "fulfillment_notes": "Staff: unlock cabinet B",
            "show_on_event_page": True,
            "variants": [
                {"label": "One size", "inventory_count": 4, "status": "active"}
            ],
        },
    )
    assert created.status_code == 200, created.text
    variant_id = created.json()["variants"][0]["id"]
    buyer = _register_buyer(client, "merchbuyer-pending-privacy@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [
                {"ticket_type_id": str(ticket_type.id), "quantity": 1},
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                },
            ],
        },
    )
    assert order.status_code == 201, order.text
    mine = client.get("/api/v1/merch/mine", headers=buyer)
    assert mine.status_code == 200, mine.text
    rows = mine.json()
    assert len(rows) >= 1
    pending = next(r for r in rows if r["display_status"] == "pending_payment")
    assert pending["fulfillment_notes"] is None
    assert pending.get("buyer_email") is None
    assert "Hidden Close" not in (pending.get("pickup_instructions_snapshot") or "")
    assert "cabinet" not in (pending.get("pickup_instructions_snapshot") or "").lower()


def test_host_fulfillment_omits_buyer_email(client: TestClient, db_session: Session):
    _, _, event, ticket_type = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=2)
    variant_id = product["variants"][0]["id"]
    buyer = _register_buyer(client, "merchbuyer-desk-privacy@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [
                {"ticket_type_id": str(ticket_type.id), "quantity": 1},
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                },
            ],
        },
    )
    assert order.status_code == 201, order.text
    _pay_order(client, buyer, order.json())
    desk = client.get(
        f"/api/v1/merch/host/events/{event.id}/fulfillments",
        headers=host_headers,
    )
    assert desk.status_code == 200, desk.text
    row = desk.json()[0]
    assert row.get("buyer_email") is None
    assert row.get("buyer_name")


def test_host_merch_stats_and_duplicate(client: TestClient, db_session: Session):
    _, _, event, ticket_type = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=3)
    variant_id = product["variants"][0]["id"]
    buyer = _register_buyer(client, "merchbuyer-studio@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [
                {"ticket_type_id": str(ticket_type.id), "quantity": 1},
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                },
            ],
        },
    )
    assert order.status_code == 201, order.text
    _pay_order(client, buyer, order.json())

    stats = client.get(
        f"/api/v1/merch/host/events/{event.id}/stats", headers=host_headers
    )
    assert stats.status_code == 200, stats.text
    body = stats.json()
    assert body["sales_status"] == "selling"
    assert body["items_sold"] >= 1
    assert Decimal(body["total_merch_revenue"]) >= Decimal("7500.00")
    assert "payment" not in str(body).lower()
    assert "paystack" not in str(body).lower()

    dup = client.post(
        f"/api/v1/merch/products/{product['id']}/duplicate",
        headers=host_headers,
    )
    assert dup.status_code == 200, dup.text
    assert dup.json()["status"] == "draft"
    assert "(copy)" in dup.json()["name"]


def test_host_can_set_product_type_and_sales_fields(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    created = client.post(
        f"/api/v1/merch/events/{event.id}/products",
        headers=host_headers,
        json={
            "name": "VIP Pack",
            "short_description": "Limited pack",
            "product_type": "vip_pack",
            "base_price": "25000.00",
            "status": "active",
            "requires_ticket": True,
            "max_per_buyer": 1,
            "is_featured": True,
            "show_on_event_page": True,
            "variants": [
                {
                    "label": "Standard",
                    "size": "OS",
                    "color": "Black",
                    "option_1_name": "Edition",
                    "option_1_value": "Night One",
                    "sku": "VIP-01",
                    "inventory_count": 10,
                    "status": "active",
                }
            ],
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["product_type"] == "vip_pack"
    assert body["requires_ticket"] is True
    assert body["max_per_buyer"] == 1
    assert body["is_featured"] is True
    assert body["variants"][0]["option_1_value"] == "Night One"


def test_pending_order_reserves_merch_stock(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=1)
    variant_id = product["variants"][0]["id"]
    buyer_a = _register_buyer(client, "merchbuyer-res-a@example.com")
    buyer_b = _register_buyer(client, "merchbuyer-res-b@example.com")

    first = client.post(
        "/api/v1/orders",
        headers=buyer_a,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert first.status_code == 201, first.text
    variant = db_session.get(EventMerchVariant, UUID(variant_id))
    assert variant is not None
    db_session.refresh(variant)
    assert variant.reserved_quantity == 1
    assert variant.inventory_count == 1

    second = client.post(
        "/api/v1/orders",
        headers=buyer_b,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert second.status_code == 409


def test_deactivate_unsafe_requires_suspended_host(client: TestClient, db_session: Session):
    _, host, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    admin = _admin_headers(client, db_session, "merchadmin4@example.com")

    blocked = client.post(
        f"/api/v1/merch/admin/products/{product['id']}/deactivate-unsafe",
        headers=admin,
        json={"note": "Trying early"},
    )
    assert blocked.status_code == 400

    host.status = "suspended"
    db_session.commit()

    ok = client.post(
        f"/api/v1/merch/admin/products/{product['id']}/deactivate-unsafe",
        headers=admin,
        json={"note": "Host suspended"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["moderation_status"] == "hidden"
    assert ok.json()["status"] == "paused"


def test_merch_checkout_blocked_when_host_suspended(
    client: TestClient, db_session: Session
):
    _, host, event, ticket_type = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=2)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merchbuyer_host_suspend@example.com")

    host.status = "suspended"
    db_session.commit()

    blocked = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "ticket",
                    "ticket_type_id": str(ticket_type.id),
                    "quantity": 1,
                },
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                },
            ],
        },
    )
    assert blocked.status_code == 400
    assert "unavailable" in blocked.json()["detail"].lower()


def test_requires_ticket_allows_existing_event_ticket(
    client: TestClient, db_session: Session
):
    _, _, event, ticket_type = _seed_host_event(db_session)
    event.allow_merch_only_checkout = False
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=3)
    patched = client.patch(
        f"/api/v1/merch/products/{product['id']}",
        headers=host_headers,
        json={"requires_ticket": True},
    )
    assert patched.status_code == 200, patched.text
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merchbuyer_req_ticket@example.com")

    # Buy a ticket first
    ticket_order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "ticket",
                    "ticket_type_id": str(ticket_type.id),
                    "quantity": 1,
                }
            ],
        },
    )
    assert ticket_order.status_code == 201, ticket_order.text
    _pay_order(client, buyer_headers, ticket_order.json())

    # Merch-only with existing ticket should succeed even when merch-only flag is off
    merch_order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert merch_order.status_code == 201, merch_order.text
    _pay_order(client, buyer_headers, merch_order.json())

    fulfills = list(
        db_session.scalars(
            select(MerchFulfillment).where(
                MerchFulfillment.order_id == UUID(merch_order.json()["id"])
            )
        )
    )
    assert len(fulfills) == 1


def test_max_per_buyer_enforced(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=5)
    patched = client.patch(
        f"/api/v1/merch/products/{product['id']}",
        headers=host_headers,
        json={"max_per_buyer": 1},
    )
    assert patched.status_code == 200, patched.text
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merchbuyer_max@example.com")

    first = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert first.status_code == 201, first.text
    _pay_order(client, buyer_headers, first.json())

    second = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert second.status_code == 400
    assert "per-buyer" in second.json()["detail"].lower()


def test_merch_webhook_idempotent_inventory(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=4)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merchbuyer_idem@example.com")

    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()

    with patch(
        "app.payments.service.initialize_transaction",
        return_value={
            "authorization_url": "https://checkout.paystack.com/test",
            "access_code": "ACCESS",
            "reference": body["reference"],
        },
    ):
        client.post(f"/api/v1/payments/checkout/{body['id']}", headers=buyer_headers)

    payload = {
        "event": "charge.success",
        "data": {
            "id": 991001,
            "reference": body["reference"],
            "amount": int(Decimal(body["total_amount"]) * 100),
            "status": "success",
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    headers = {
        "x-paystack-signature": sign_body_for_tests(raw),
        "content-type": "application/json",
    }
    first = client.post(
        "/api/v1/payments/webhooks/paystack", content=raw, headers=headers
    )
    second = client.post(
        "/api/v1/payments/webhooks/paystack", content=raw, headers=headers
    )
    assert first.status_code == 200
    assert second.status_code == 200

    variant = db_session.get(EventMerchVariant, UUID(variant_id))
    assert variant is not None
    db_session.refresh(variant)
    assert variant.inventory_count == 3
    assert variant.sold_quantity == 1

    fulfills = list(
        db_session.scalars(
            select(MerchFulfillment).where(MerchFulfillment.order_id == UUID(body["id"]))
        )
    )
    assert len(fulfills) == 1


def test_host_staff_can_fulfill_but_not_edit_catalog(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merchbuyer_staff_desk@example.com")

    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    ).json()
    _pay_order(client, buyer_headers, order)

    client.post(
        "/api/v1/auth/register",
        json={
            "email": "merchdesk@example.com",
            "password": "securepass1",
            "full_name": "Desk Staff",
        "gender": "prefer_not_to_say"},
    )
    assign = client.post(
        f"/api/v1/checkins/events/{event.id}/staff",
        headers=host_headers,
        json={"email": "merchdesk@example.com"},
    )
    assert assign.status_code in {200, 201}, assign.text
    staff_headers = _login(client, "merchdesk@example.com")

    queue = client.get(
        f"/api/v1/merch/host/events/{event.id}/fulfillments",
        headers=staff_headers,
    )
    assert queue.status_code == 200, queue.text
    assert len(queue.json()) >= 1

    fulfill = db_session.scalar(
        select(MerchFulfillment).where(MerchFulfillment.order_id == UUID(order["id"]))
    )
    assert fulfill is not None
    picked = client.post(
        f"/api/v1/merch/fulfillments/{fulfill.id}/fulfill",
        headers=staff_headers,
    )
    assert picked.status_code == 200, picked.text

    edit = client.patch(
        f"/api/v1/merch/products/{product['id']}",
        headers=staff_headers,
        json={"base_price": "1.00", "name": "Hacked price"},
    )
    assert edit.status_code == 403


def test_support_can_view_admin_merch_but_not_moderate(
    client: TestClient, db_session: Session
):
    from app.core.security import hash_password

    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)

    support = User(
        email="merchsupport@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Merch Support",
        is_active=True,
    )
    role = get_role_by_name(db_session, "support_agent")
    assert role is not None
    support.roles.append(role)
    db_session.add(support)
    db_session.commit()
    support_headers = _login(client, "merchsupport@example.com")

    listed = client.get("/api/v1/merch/admin/products", headers=support_headers)
    assert listed.status_code == 200, listed.text

    hide = client.post(
        f"/api/v1/merch/admin/products/{product['id']}/moderate",
        headers=support_headers,
        json={"action": "hide", "note": "Support should not hide"},
    )
    assert hide.status_code == 403


def test_buyer_cannot_view_host_fulfillment_queue(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    buyer_headers = _register_buyer(client, "merchbuyer_nofulfill@example.com")
    denied = client.get(
        f"/api/v1/merch/host/events/{event.id}/fulfillments",
        headers=buyer_headers,
    )
    assert denied.status_code == 403


def test_merchandise_path_aliases(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    create = client.post(
        f"/api/v1/host/events/{event.id}/merchandise",
        headers=host_headers,
        json={
            "name": "Festival Tee",
            "description": "Soft cotton tee",
            "base_price": "7500.00",
            "status": "active",
            "pickup_instructions": "Merch stand",
            "variants": [
                {
                    "label": "L / Black",
                    "inventory_count": 5,
                    "status": "active",
                }
            ],
        },
    )
    assert create.status_code == 200, create.text
    product = create.json()

    alias_list = client.get(
        f"/api/v1/host/events/{event.id}/merchandise",
        headers=host_headers,
    )
    assert alias_list.status_code == 200, alias_list.text
    assert any(p["id"] == product["id"] for p in alias_list.json())

    host_get = client.get(
        f"/api/v1/host/events/{event.id}/merchandise/{product['id']}",
        headers=host_headers,
    )
    assert host_get.status_code == 200, host_get.text
    assert host_get.json()["id"] == product["id"]

    public = client.get(f"/api/v1/events/{event.slug}/merchandise")
    assert public.status_code == 200, public.text
    assert any(p["id"] == product["id"] for p in public.json())

    by_slug = client.get(
        f"/api/v1/events/{event.slug}/merchandise/{product['slug']}"
    )
    assert by_slug.status_code == 200, by_slug.text
    assert by_slug.json()["id"] == product["id"]

    buyer_headers = _register_buyer(client, "merchbuyer_alias@example.com")
    event_row = db_session.get(Event, event.id)
    assert event_row is not None
    event_row.allow_merch_only_checkout = True
    db_session.commit()

    variant_id = product["variants"][0]["id"]
    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "buyer_name": "Alias Buyer",
            "buyer_email": "merchbuyer_alias@example.com",
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert order.status_code in (200, 201), order.text
    order_body = order.json()
    _pay_order(client, buyer_headers, order_body)

    mine_alias = client.get("/api/v1/dashboard/merchandise", headers=buyer_headers)
    assert mine_alias.status_code == 200, mine_alias.text
    rows = mine_alias.json()
    assert len(rows) >= 1
    item = rows[0]
    single = client.get(
        f"/api/v1/dashboard/merchandise/{item['id']}",
        headers=buyer_headers,
    )
    assert single.status_code == 200, single.text
    assert single.json()["order_item_id"] == item["order_item_id"]

    host_orders = client.get(
        f"/api/v1/host/events/{event.id}/merchandise/orders",
        headers=host_headers,
    )
    assert host_orders.status_code == 200, host_orders.text
    assert any(r["id"] == item["id"] for r in host_orders.json())

    ready = client.patch(
        f"/api/v1/host/merchandise/order-items/{item['order_item_id']}/ready",
        headers=host_headers,
    )
    assert ready.status_code == 200, ready.text
    assert ready.json()["status"] == "collect_at_stand"

    picked_up = client.patch(
        f"/api/v1/host/merchandise/order-items/{item['order_item_id']}/picked-up",
        headers=host_headers,
    )
    assert picked_up.status_code == 200, picked_up.text
    assert picked_up.json()["status"] == "fulfilled"

    pause = client.patch(
        f"/api/v1/host/events/{event.id}/merchandise/{product['id']}/pause",
        headers=host_headers,
    )
    assert pause.status_code == 200, pause.text
    assert pause.json()["status"] == "paused"

    # Second product: PATCH update + archive (avoids double analytics emit on sold SKU).
    other = _create_active_product(client, host_headers, event.id, inventory=2)
    host_patch = client.patch(
        f"/api/v1/host/events/{event.id}/merchandise/{other['id']}",
        headers=host_headers,
        json={"short_description": "Alias patch"},
    )
    assert host_patch.status_code == 200, host_patch.text
    assert host_patch.json()["short_description"] == "Alias patch"

    archive = client.patch(
        f"/api/v1/host/events/{event.id}/merchandise/{other['id']}/archive",
        headers=host_headers,
    )
    assert archive.status_code == 200, archive.text
    assert archive.json()["status"] == "archived"
    assert archive.json().get("archived_at") is not None

    admin_user = User(
        email="merchaliasadmin@example.com",
        password_hash="x",
        full_name="Merch Admin",
        is_active=True,
    )
    from app.core.security import hash_password

    admin_user.password_hash = hash_password("securepass1")
    role = get_role_by_name(db_session, "super_admin")
    assert role is not None
    admin_user.roles.append(role)
    db_session.add(admin_user)
    db_session.commit()
    admin_headers = _login(client, "merchaliasadmin@example.com")

    admin_list = client.get("/api/v1/admin/merchandise", headers=admin_headers)
    assert admin_list.status_code == 200, admin_list.text

    hide = client.patch(
        f"/api/v1/admin/merchandise/{product['id']}/hide",
        headers=admin_headers,
    )
    assert hide.status_code == 200, hide.text
    assert hide.json()["moderation_status"] == "hidden"

    restore = client.patch(
        f"/api/v1/admin/merchandise/{product['id']}/restore",
        headers=admin_headers,
    )
    assert restore.status_code == 200, restore.text


def test_merch_notification_bodies_omit_payment_secrets(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    buyer_headers = _register_buyer(client, "merchnotify@example.com")
    event_row = db_session.get(Event, event.id)
    assert event_row is not None
    event_row.allow_merch_only_checkout = True
    db_session.commit()

    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "buyer_name": "Notify Buyer",
            "buyer_email": "merchnotify@example.com",
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": product["variants"][0]["id"],
                    "quantity": 1,
                }
            ],
        },
    )
    assert order.status_code in (200, 201), order.text
    order_body = order.json()
    _pay_order(client, buyer_headers, order_body)

    from app.messaging.models import InAppNotification

    me = client.get("/api/v1/auth/me", headers=buyer_headers)
    buyer_id = UUID(me.json()["id"])
    notes = list(
        db_session.scalars(
            select(InAppNotification).where(InAppNotification.user_id == buyer_id)
        ).all()
    )
    confirmed = [n for n in notes if n.kind in {"merch.confirmed", "merch.paid"}]
    assert confirmed
    blob = " ".join(f"{n.title} {n.body}" for n in confirmed).lower()
    assert "your merch order is confirmed" in blob
    for banned in (
        "paystack",
        "authorization",
        "card",
        "access_code",
        order_body["reference"].lower(),
        "7500",
        "₦",
    ):
        assert banned not in blob


def test_merch_discount_and_shipping_address_private(
    client: TestClient, db_session: Session
):
    _, host, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=5)
    variant_id = product["variants"][0]["id"]

    from app.merch.discounts import create_discount
    from app.merch.models import EventMerchProduct
    from app.merch.shipping import upsert_zone

    prod = db_session.get(EventMerchProduct, UUID(product["id"]))
    assert prod is not None
    prod.shipping_enabled = True
    upsert_zone(
        db_session,
        host_id=host.id,
        name="Lagos",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        flat_fee=Decimal("1500.00"),
        event_id=event.id,
    )
    create_discount(
        db_session,
        host_id=host.id,
        code="SAVE15",
        discount_type="percent",
        discount_value=Decimal("15"),
        applies_to="merch_only",
        event_id=event.id,
    )
    db_session.commit()

    buyer_headers = _register_buyer(client, "merchship@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "fulfillment_method": "shipping",
            "merch_discount_code": "SAVE15",
            "shipping_address": {
                "recipient_name": "Ada Buyer",
                "phone": "+2348012345678",
                "line1": "12 Hidden Street",
                "city": "Lagos",
                "state": "Lagos",
                "country": "Nigeria",
            },
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    assert Decimal(body["merch_discount_amount"]) > 0
    assert Decimal(body["shipping_amount"]) == Decimal("1500.00")
    # Public order payload must not echo street/phone
    blob = json.dumps(body).lower()
    assert "12 hidden street" not in blob
    assert "+2348012345678" not in blob

    _pay_order(client, buyer_headers, body)
    from app.merch.models import MerchFulfillment, MerchRevenueSplit, MerchShippingAddress
    from app.core.sensitive import decrypt_sensitive

    fulfills = list(
        db_session.scalars(
            select(MerchFulfillment).where(MerchFulfillment.order_id == UUID(body["id"]))
        )
    )
    assert len(fulfills) == 1
    assert fulfills[0].fulfillment_method == "shipping"
    addr = db_session.get(MerchShippingAddress, fulfills[0].shipping_address_id)
    assert addr is not None
    assert decrypt_sensitive(addr.line1_enc) == "12 Hidden Street"

    splits = list(
        db_session.scalars(
            select(MerchRevenueSplit).where(MerchRevenueSplit.order_id == UUID(body["id"]))
        )
    )
    assert len(splits) == 1


def test_merch_pickup_qr_typ_and_scan(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=3)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merchqr@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    _pay_order(client, buyer_headers, body)

    mine = client.get("/api/v1/merch/mine", headers=buyer_headers)
    assert mine.status_code == 200
    row = mine.json()[0]
    assert row.get("qr_typ") == "padeya.merch.pickup"
    assert row.get("qr_token")
    assert "padeya.ticket" not in (row.get("qr_token") or "")

    scan = client.post(
        f"/api/v1/host/events/{event.id}/merchandise/scan-qr",
        headers=host_headers,
        json={"token": row["qr_token"]},
    )
    assert scan.status_code == 200, scan.text
    scanned = scan.json()
    assert scanned["status"] == "fulfilled"
    assert scanned.get("shipping_address") is None
    assert scanned.get("buyer_email") is None
    assert scanned.get("qr_token") is None
    assert scanned.get("fulfilled_at")
    assert scanned.get("fulfilled_by_name")


def test_merch_scan_rejects_ticket_qr(client: TestClient, db_session: Session):
    from app.tickets.qr import create_signed_qr_payload, new_qr_jti

    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    ticket_token = create_signed_qr_payload(
        public_code="PDY-MERCH-REJECT",
        event_id=str(event.id),
        jti=new_qr_jti(),
    )
    res = client.post(
        f"/api/v1/host/events/{event.id}/merchandise/scan-qr",
        headers=host_headers,
        json={"token": ticket_token},
    )
    assert res.status_code == 400
    detail = res.json()["detail"].lower()
    assert "ticket" in detail or "invalid" in detail


def test_merch_pickup_once_via_scan(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=2)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merchqr_once@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    _pay_order(client, buyer_headers, body)

    mine = client.get("/api/v1/merch/mine", headers=buyer_headers)
    row = mine.json()[0]
    first = client.post(
        f"/api/v1/host/events/{event.id}/merchandise/scan-qr",
        headers=host_headers,
        json={"pickup_code": row["pickup_code"]},
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "fulfilled"

    dup = client.post(
        f"/api/v1/host/events/{event.id}/merchandise/scan-qr",
        headers=host_headers,
        json={"pickup_code": row["pickup_code"]},
    )
    assert dup.status_code == 409
    assert "already" in dup.json()["detail"].lower()

    mine_after = client.get("/api/v1/merch/mine", headers=buyer_headers)
    assert mine_after.json()[0].get("qr_token") in (None, "")


def test_merch_scan_cancelled_blocked(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=2)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "merchqr_cancel@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    ).json()
    _pay_order(client, buyer_headers, order)

    fulfill = db_session.scalar(
        select(MerchFulfillment).where(MerchFulfillment.order_id == UUID(order["id"]))
    )
    assert fulfill is not None
    code = fulfill.pickup_code
    fulfill.status = "cancelled"
    db_session.commit()

    blocked = client.post(
        f"/api/v1/host/events/{event.id}/merchandise/scan-qr",
        headers=host_headers,
        json={"pickup_code": code},
    )
    assert blocked.status_code == 400
    assert "cancelled" in blocked.json()["detail"].lower()


def _create_active_bundle(
    db: Session,
    *,
    host: Host,
    event: Event,
    ticket_type: TicketType,
    product: dict,
    name: str = "GA + Merch",
    bundle_price: Decimal = Decimal("9000.00"),
    inventory_limit: int | None = 10,
    max_per_buyer: int | None = None,
    sales_start_at=None,
    sales_end_at=None,
    status: str = "active",
):
    from app.merch.bundles import create_bundle

    bundle = create_bundle(
        db,
        host_id=host.id,
        event_id=event.id,
        name=name,
        ticket_type_id=ticket_type.id,
        merch_variant_rules=[
            {
                "product_id": product["id"],
                "variant_id": product["variants"][0]["id"],
                "quantity": 1,
            }
        ],
        bundle_price=bundle_price,
        inventory_limit=inventory_limit,
        max_per_buyer=max_per_buyer,
        sales_start_at=sales_start_at,
        sales_end_at=sales_end_at,
        status=status,
    )
    db.commit()
    db.refresh(bundle)
    return bundle


def test_merch_bundle_expands_on_order(client: TestClient, db_session: Session):
    _, host, event, ticket_type = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=5)
    bundle = _create_active_bundle(
        db_session, host=host, event=event, ticket_type=ticket_type, product=product
    )

    buyer_headers = _register_buyer(client, "merchbundle@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "bundle",
                    "bundle_id": str(bundle.id),
                    "quantity": 1,
                }
            ],
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    assert Decimal(body["total_amount"]) == Decimal("9000.00")
    kinds = {i["item_kind"] for i in body["items"]}
    assert "ticket" in kinds and "merch" in kinds
    _pay_order(client, buyer_headers, body)
    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(body["id"])))
    )
    assert len(tickets) == 1
    fulfills = list(
        db_session.scalars(
            select(MerchFulfillment).where(MerchFulfillment.order_id == UUID(body["id"]))
        )
    )
    assert len(fulfills) == 1


def test_bundle_unpaid_does_not_issue_ticket_or_merch(
    client: TestClient, db_session: Session
):
    _, host, event, ticket_type = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=5)
    bundle = _create_active_bundle(
        db_session, host=host, event=event, ticket_type=ticket_type, product=product
    )
    buyer_headers = _register_buyer(client, "merchbundle_unpaid@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "bundle",
                    "bundle_id": str(bundle.id),
                    "quantity": 1,
                }
            ],
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    assert body["status"] == "pending"
    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(body["id"])))
    )
    fulfills = list(
        db_session.scalars(
            select(MerchFulfillment).where(MerchFulfillment.order_id == UUID(body["id"]))
        )
    )
    assert tickets == []
    assert fulfills == []


def test_bundle_inventory_and_sales_window_and_max_per_buyer(
    client: TestClient, db_session: Session
):
    _, host, event, ticket_type = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=5)

    draft = _create_active_bundle(
        db_session,
        host=host,
        event=event,
        ticket_type=ticket_type,
        product=product,
        name="Draft pack",
        status="draft",
    )
    buyer_headers = _register_buyer(client, "merchbundle_rules@example.com")
    rejected = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {"item_kind": "bundle", "bundle_id": str(draft.id), "quantity": 1}
            ],
        },
    )
    assert rejected.status_code == 400

    future = _create_active_bundle(
        db_session,
        host=host,
        event=event,
        ticket_type=ticket_type,
        product=product,
        name="Future pack",
        sales_start_at=datetime.now(UTC) + timedelta(days=2),
    )
    not_started = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {"item_kind": "bundle", "bundle_id": str(future.id), "quantity": 1}
            ],
        },
    )
    assert not_started.status_code == 400
    assert "not started" in not_started.json()["detail"].lower()

    ended = _create_active_bundle(
        db_session,
        host=host,
        event=event,
        ticket_type=ticket_type,
        product=product,
        name="Ended pack",
        sales_end_at=datetime.now(UTC) - timedelta(hours=1),
    )
    window_ended = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {"item_kind": "bundle", "bundle_id": str(ended.id), "quantity": 1}
            ],
        },
    )
    assert window_ended.status_code == 400

    limited = _create_active_bundle(
        db_session,
        host=host,
        event=event,
        ticket_type=ticket_type,
        product=product,
        name="Limited pack",
        inventory_limit=1,
    )
    first = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {"item_kind": "bundle", "bundle_id": str(limited.id), "quantity": 1}
            ],
        },
    )
    assert first.status_code == 201, first.text
    _pay_order(client, buyer_headers, first.json())

    buyer_b = _register_buyer(client, "merchbundle_rules_b@example.com")
    oversell = client.post(
        "/api/v1/orders",
        headers=buyer_b,
        json={
            "event_id": str(event.id),
            "items": [
                {"item_kind": "bundle", "bundle_id": str(limited.id), "quantity": 1}
            ],
        },
    )
    assert oversell.status_code == 409

    per_buyer = _create_active_bundle(
        db_session,
        host=host,
        event=event,
        ticket_type=ticket_type,
        product=product,
        name="One per buyer",
        inventory_limit=5,
        max_per_buyer=1,
    )
    ok = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {"item_kind": "bundle", "bundle_id": str(per_buyer.id), "quantity": 1}
            ],
        },
    )
    assert ok.status_code == 201, ok.text
    _pay_order(client, buyer_headers, ok.json())
    again = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {"item_kind": "bundle", "bundle_id": str(per_buyer.id), "quantity": 1}
            ],
        },
    )
    assert again.status_code == 400
    assert "per-buyer" in again.json()["detail"].lower()


def test_bundle_webhook_idempotent(client: TestClient, db_session: Session):
    _, host, event, ticket_type = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=5)
    bundle = _create_active_bundle(
        db_session,
        host=host,
        event=event,
        ticket_type=ticket_type,
        product=product,
        inventory_limit=5,
    )
    buyer_headers = _register_buyer(client, "merchbundle_idem@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "bundle",
                    "bundle_id": str(bundle.id),
                    "quantity": 1,
                }
            ],
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    _pay_order(client, buyer_headers, body)

    # Replay the same webhook signature path via a second charge.success with
    # a new provider event id but same paid order reference — finalize stays
    # idempotent for tickets + merch + bundle sold counts.
    with patch(
        "app.payments.service.initialize_transaction",
        return_value={
            "authorization_url": "https://checkout.paystack.com/test",
            "access_code": "ACCESS",
            "reference": body["reference"],
        },
    ):
        # order already paid; re-checkout may fail — call webhook directly twice
        pass

    payload = {
        "event": "charge.success",
        "data": {
            "id": int(UUID(body["id"]).int % 10**9) + 5000,
            "reference": body["reference"],
            "amount": int(Decimal(body["total_amount"]) * 100),
            "status": "success",
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    replay = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=raw,
        headers={
            "x-paystack-signature": sign_body_for_tests(raw),
            "content-type": "application/json",
        },
    )
    assert replay.status_code == 200, replay.text

    db_session.refresh(bundle)
    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(body["id"])))
    )
    fulfills = list(
        db_session.scalars(
            select(MerchFulfillment).where(MerchFulfillment.order_id == UUID(body["id"]))
        )
    )
    assert len(tickets) == 1
    assert len(fulfills) == 1
    assert int(bundle.quantity_sold or 0) == 1


def test_host_bundle_crud_api(client: TestClient, db_session: Session):
    _, _, event, ticket_type = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=5)
    created = client.post(
        f"/api/v1/host/events/{event.id}/bundles",
        headers=host_headers,
        json={
            "name": "Host Pack",
            "description": "GA + tee",
            "bundle_price": "8500.00",
            "currency": "NGN",
            "ticket_type_id": str(ticket_type.id),
            "merch_variant_rules": [
                {
                    "product_id": product["id"],
                    "variant_id": product["variants"][0]["id"],
                    "quantity": 1,
                }
            ],
            "inventory_limit": 20,
            "max_per_buyer": 2,
            "status": "draft",
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()
    assert row["name"] == "Host Pack"
    assert Decimal(row["savings"]) >= 0

    patched = client.patch(
        f"/api/v1/host/events/{event.id}/bundles/{row['id']}",
        headers=host_headers,
        json={"status": "active", "bundle_price": "8000.00"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["status"] == "active"

    public = client.get(f"/api/v1/events/{event.id}/bundles")
    assert public.status_code == 200
    assert any(b["id"] == row["id"] for b in public.json())

    archived = client.post(
        f"/api/v1/host/events/{event.id}/bundles/{row['id']}/archive",
        headers=host_headers,
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"


def test_host_storefront_and_review_hosts_cannot_delete(
    client: TestClient, db_session: Session
):
    _, host, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=4)
    from app.merch.models import EventMerchProduct

    prod = db_session.get(EventMerchProduct, UUID(product["id"]))
    assert prod is not None
    prod.storefront_visibility = "host_storefront"
    db_session.commit()

    store = client.get(f"/api/v1/u/{host.slug}/merch")
    assert store.status_code == 200, store.text
    assert store.json()["product_count"] >= 1

    buyer_headers = _register_buyer(client, "merchreview@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": product["variants"][0]["id"],
                    "quantity": 1,
                }
            ],
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    _pay_order(client, buyer_headers, body)
    item_id = body["items"][0]["id"]
    review = client.post(
        "/api/v1/dashboard/merchandise/reviews",
        headers=buyer_headers,
        json={"order_item_id": item_id, "rating": 5, "body": "Great tee"},
    )
    assert review.status_code == 200, review.text
    assert review.json()["verified_purchase"] is True
    assert review.json()["status"] == "published"
    public_keys = set(review.json())
    assert "order_item_id" not in public_keys
    assert "buyer_user_id" not in public_keys
    assert "email" not in public_keys

    # One review per order line
    dup = client.post(
        "/api/v1/dashboard/merchandise/reviews",
        headers=buyer_headers,
        json={"order_item_id": item_id, "rating": 4, "body": "Again"},
    )
    assert dup.status_code == 400

    # Buyer can edit
    edited = client.patch(
        f"/api/v1/dashboard/merchandise/reviews/{review.json()['id']}",
        headers=buyer_headers,
        json={"rating": 4, "body": "Still great"},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["rating"] == 4

    # Host can reply; delete is forbidden (product invariant)
    reply = client.post(
        f"/api/v1/host/merchandise/reviews/{review.json()['id']}/reply",
        headers=host_headers,
        json={"reply": "Thanks for supporting the drop!"},
    )
    assert reply.status_code == 200, reply.text
    assert reply.json()["host_reply"]
    banned = client.delete(
        f"/api/v1/host/merchandise/reviews/{review.json()['id']}",
        headers=host_headers,
    )
    assert banned.status_code == 403

    # Admin can hide (drops from public list)
    admin = _admin_headers(client, db_session, "merchadmin-reviews@example.com")
    hidden = client.post(
        f"/api/v1/admin/merchandise/reviews/{review.json()['id']}/moderate",
        headers=admin,
        json={"action": "hide", "note": "spammy"},
    )
    assert hidden.status_code == 200, hidden.text
    assert hidden.json()["status"] == "hidden_by_admin"
    listed = client.get(f"/api/v1/merch/products/{product['id']}/reviews")
    assert listed.status_code == 200
    assert listed.json()["review_count"] == 0


def test_unverified_merch_review_blocked(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=3)
    buyer_headers = _register_buyer(client, "merchreview-unpaid@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer_headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": product["variants"][0]["id"],
                    "quantity": 1,
                }
            ],
        },
    )
    assert order.status_code == 201, order.text
    item_id = order.json()["items"][0]["id"]
    # Unpaid — no fulfillment → cannot review
    blocked = client.post(
        "/api/v1/dashboard/merchandise/reviews",
        headers=buyer_headers,
        json={"order_item_id": item_id, "rating": 5, "body": "Too soon"},
    )
    assert blocked.status_code == 400
    assert "paid" in blocked.json()["detail"].lower() or "verified" in blocked.json()[
        "detail"
    ].lower() or "fulfill" in blocked.json()["detail"].lower()
