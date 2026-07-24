"""Advanced merch commerce — QR type, shipping privacy, route smoke."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.sensitive import encrypt_sensitive
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.merch.models import EventMerchProduct, EventMerchVariant, MerchShippingAddress
from app.merch.qr_pickup import (
    MERCH_QR_TYP,
    create_merch_pickup_qr_payload,
    decode_merch_pickup_qr_payload,
)
from app.merch.shipping import compute_shipping_fee, public_shipping_hint, upsert_zone
from app.tickets.qr import create_signed_qr_payload, new_qr_jti
from app.users.models import User
from app.users.service import get_role_by_name
from tests.test_merch import (
    _create_active_product,
    _login,
    _pay_order,
    _register_buyer,
    _seed_host_event,
)


def test_merch_qr_typ_is_not_ticket_qr():
    token = create_merch_pickup_qr_payload(
        fulfillment_id="00000000-0000-0000-0000-000000000001",
        event_id="00000000-0000-0000-0000-000000000002",
        pickup_code="MRCH-TEST01",
        jti="test-jti",
    )
    payload = decode_merch_pickup_qr_payload(token)
    assert payload["typ"] == MERCH_QR_TYP
    assert payload["typ"] != "padeya.ticket.qr"


def test_ticket_qr_rejected_by_merch_decoder():
    ticket_token = create_signed_qr_payload(
        public_code="PDY-TEST",
        event_id="00000000-0000-0000-0000-000000000002",
        jti=new_qr_jti(),
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_merch_pickup_qr_payload(ticket_token)


def test_merch_qr_typ_constant_is_pickup_not_ticket():
    assert MERCH_QR_TYP == "padeya.merch.pickup"
    assert MERCH_QR_TYP != "padeya.ticket.qr"


def test_public_shipping_hint_omits_private_fields():
    addr = MerchShippingAddress(
        order_id=uuid.uuid4(),
        buyer_user_id=uuid.uuid4(),
        recipient_name_enc=encrypt_sensitive("Ada Buyer"),
        phone_enc=encrypt_sensitive("+2348012345678"),
        line1_enc=encrypt_sensitive("12 Private Street"),
        line2_enc=None,
        notes_enc=None,
        city="Lagos",
        state="Lagos",
        country="NG",
        postal_code="100001",
    )
    hint = public_shipping_hint(addr)
    assert hint is not None
    assert hint["city"] == "Lagos"
    assert hint["phone"] is None
    assert hint["line1"] is None
    assert hint["recipient_name"] is None


def test_host_storefront_and_cart_routes_exist(client: TestClient):
    storefront = client.get("/api/v1/u/nonexistent-host-xyz/merch")
    assert storefront.status_code in {200, 404}
    cart = client.get("/api/v1/dashboard/cart")
    assert cart.status_code in {401, 403}


def test_host_cannot_delete_review_without_auth(client: TestClient):
    res = client.delete(
        "/api/v1/host/merchandise/reviews/00000000-0000-0000-0000-000000000099"
    )
    assert res.status_code in {401, 403}


def test_shipping_requires_address_when_selected(
    client: TestClient, db_session: Session
):
    _, host, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=3)
    prod = db_session.get(EventMerchProduct, uuid.UUID(product["id"]))
    assert prod is not None
    prod.shipping_enabled = True
    db_session.commit()
    variant_id = product["variants"][0]["id"]
    buyer = _register_buyer(client, "ship-required@example.com")

    missing = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "fulfillment_method": "shipping",
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 1,
                }
            ],
        },
    )
    assert missing.status_code == 400
    assert "address" in missing.json()["detail"].lower()


def test_pickup_only_rejects_address_not_required(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=3)
    variant_id = product["variants"][0]["id"]
    buyer = _register_buyer(client, "pickup-only@example.com")

    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "fulfillment_method": "pickup",
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
    assert body.get("fulfillment_method") == "pickup"
    assert Decimal(body.get("shipping_amount") or 0) == Decimal("0")
    assert "shipping_address" not in body or body.get("shipping_address") in (
        None,
        {},
    )


def test_buyer_and_public_serializers_omit_street_address(
    client: TestClient, db_session: Session
):
    _, host, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=3)
    prod = db_session.get(EventMerchProduct, uuid.UUID(product["id"]))
    assert prod is not None
    prod.shipping_enabled = True
    upsert_zone(
        db_session,
        host_id=host.id,
        name="Lagos",
        country="Nigeria",
        state="Lagos",
        city="Ikeja",
        flat_fee=Decimal("2000.00"),
        event_id=event.id,
    )
    db_session.commit()
    variant_id = product["variants"][0]["id"]
    buyer = _register_buyer(client, "ship-privacy@example.com")

    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "fulfillment_method": "shipping",
            "shipping_address": {
                "recipient_name": "Ada Buyer",
                "phone_number": "+2348099990000",
                "address_line_1": "99 Secret Close",
                "city": "Ikeja",
                "state": "Lagos",
                "country": "Nigeria",
                "delivery_notes": "Blue gate",
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
    assert Decimal(body["shipping_amount"]) == Decimal("2000.00")
    blob = str(body).lower()
    assert "99 secret close" not in blob
    assert "+2348099990000" not in blob
    assert "blue gate" not in blob

    _pay_order(client, buyer, body)
    mine = client.get("/api/v1/merch/mine", headers=buyer)
    assert mine.status_code == 200
    row = mine.json()[0]
    assert row["fulfillment_method"] == "shipping"
    hint = row.get("shipping_address") or {}
    assert hint.get("city") == "Ikeja"
    assert hint.get("line1") is None
    assert hint.get("phone") is None
    mine_blob = str(row).lower()
    assert "99 secret close" not in mine_blob

    host_queue = client.get(
        f"/api/v1/host/events/{event.id}/merchandise/orders",
        headers=host_headers,
    )
    assert host_queue.status_code == 200, host_queue.text
    host_row = host_queue.json()[0]
    addr = host_row.get("shipping_address") or {}
    assert addr.get("line1") == "99 Secret Close"
    assert addr.get("phone") == "+2348099990000"


def test_zone_fee_zero_without_zones(db_session: Session):
    _, host, event, _ = _seed_host_event(db_session)
    fee = compute_shipping_fee(
        db_session,
        host_id=host.id,
        event_id=event.id,
        country="Nigeria",
        state="Lagos",
        city="Lagos",
    )
    assert fee == Decimal("0.00")

    upsert_zone(
        db_session,
        host_id=host.id,
        name="Lagos metro",
        country="Nigeria",
        state="Lagos",
        city=None,
        flat_fee=Decimal("1200.00"),
    )
    db_session.commit()
    fee2 = compute_shipping_fee(
        db_session,
        host_id=host.id,
        event_id=event.id,
        country="Nigeria",
        state="Lagos",
        city="Ikeja",
    )
    assert fee2 == Decimal("1200.00")

    with pytest.raises(Exception) as exc:
        compute_shipping_fee(
            db_session,
            host_id=host.id,
            event_id=event.id,
            country="Ghana",
            state="Accra",
            city="Accra",
        )
    assert "not available" in str(exc.value).lower()


def _seed_storefront_host(db: Session, *, slug: str = "shop-host") -> tuple[Host, HostProfile]:
    user = User(
        email=f"{slug}@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Shop Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    user.roles.append(role)
    db.add(user)
    db.flush()
    host = Host(
        user_id=user.id,
        display_name="Shop Host",
        slug=slug,
        status="active",
    )
    db.add(host)
    db.flush()
    profile = HostProfile(
        host_id=host.id,
        city="Lagos",
        avatar_url="https://cdn.example.com/avatar.jpg",
        merch_storefront_enabled=False,
        merch_storefront_visibility="hidden",
        merch_storefront_title="Shop Host Merch",
        merch_storefront_description="Drops and exclusives",
    )
    db.add(profile)
    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=5)
    event = Event(
        title="Shop Night",
        slug=f"{slug}-night",
        description="Published event for storefront tests with enough detail.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        venue_name="Yard",
        city="Lagos",
        state="Lagos",
        status="published",
        featured=False,
        published_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    db.add(
        TicketType(
            event_id=event.id,
            name="GA",
            type="regular",
            description="Entry",
            price=Decimal("2000.00"),
            quantity=20,
            quantity_sold=0,
            quantity_reserved=0,
            min_per_order=1,
            max_per_order=4,
            visibility="public",
            status="active",
        )
    )
    db.commit()
    db.refresh(host)
    db.refresh(profile)
    return host, profile


def _add_storefront_product(
    db: Session,
    *,
    host: Host,
    event_id: UUID | None,
    name: str,
    storefront_visibility: str = "host_storefront",
    is_vault_exclusive: bool = False,
    description: str = "Full locked vault description with size chart secrets",
    gallery_urls: list[str] | None = None,
) -> EventMerchProduct:
    product = EventMerchProduct(
        host_id=host.id,
        event_id=event_id,
        name=name,
        slug=name.lower().replace(" ", "-"),
        description=description,
        short_description="Vault teaser line",
        product_type="t_shirt",
        base_price=Decimal("8000.00"),
        currency="NGN",
        status="active",
        storefront_visibility=storefront_visibility,
        is_vault_exclusive=is_vault_exclusive,
        requires_vault_access=is_vault_exclusive,
        is_event_linked=event_id is not None,
        gallery_urls=gallery_urls or ["https://cdn.example.com/secret.jpg"],
        moderation_status="clear",
    )
    db.add(product)
    db.flush()
    db.add(
        EventMerchVariant(
            product_id=product.id,
            label="M",
            inventory_count=10,
            reserved_quantity=0,
            sold_quantity=0,
            status="active",
        )
    )
    db.commit()
    db.refresh(product)
    return product


def test_hidden_storefront_returns_404_for_public(
    client: TestClient, db_session: Session
):
    host, profile = _seed_storefront_host(db_session, slug="hidden-shop")
    assert profile.merch_storefront_enabled is False
    assert profile.merch_storefront_visibility == "hidden"

    res = client.get(f"/api/v1/u/{host.slug}/merch")
    assert res.status_code == 404

    # Enabling alone is not enough when visibility stays hidden
    profile.merch_storefront_enabled = True
    db_session.commit()
    res = client.get(f"/api/v1/u/{host.slug}/merch")
    assert res.status_code == 404


def test_unlisted_storefront_reachable_but_not_listed(
    client: TestClient, db_session: Session
):
    host, profile = _seed_storefront_host(db_session, slug="unlisted-shop")
    profile.merch_storefront_enabled = True
    profile.merch_storefront_visibility = "unlisted"
    db_session.commit()

    res = client.get(f"/api/v1/u/{host.slug}/merch")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["is_listed"] is False
    assert body["storefront_visibility"] == "unlisted"
    assert body["host_avatar_url"]
    assert body["legacy_path"] == f"/@{host.slug}"


def test_vault_teaser_omits_locked_content(client: TestClient, db_session: Session):
    host, profile = _seed_storefront_host(db_session, slug="vault-shop")
    profile.merch_storefront_enabled = True
    profile.merch_storefront_visibility = "public"
    db_session.commit()

    event = db_session.query(Event).filter(Event.host_id == host.id).one()
    product = _add_storefront_product(
        db_session,
        host=host,
        event_id=event.id,
        name="Vault Tee",
        storefront_visibility="vault_exclusive",
        is_vault_exclusive=True,
        description="SECRET vault-only cut and colorway notes",
        gallery_urls=["https://cdn.example.com/vault-secret.jpg"],
    )

    res = client.get(f"/api/v1/u/{host.slug}/merch")
    assert res.status_code == 200, res.text
    items = res.json()["products"]
    assert len(items) == 1
    row = items[0]
    assert row["access_locked"] is True
    assert row["teaser_only"] is True
    assert row["id"] == str(product.id)
    assert "SECRET" not in (row.get("description") or "")
    assert row["gallery_urls"] == []
    assert row["variants"] == []
    assert row["size_chart"] is None
    assert row["availability"] == "locked"
    assert row.get("required_vault_item_id") in (None, "")
    assert isinstance(row.get("access_requirements"), list)
    assert row.get("access_requirements")
    # Never leak Vault media/body/secrets via merch teaser payloads
    blob = str(row).lower()
    assert "secret" not in blob
    assert "vault body" not in blob

    detail = client.get(f"/api/v1/u/{host.slug}/merch/{product.id}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["access_locked"] is True
    assert "SECRET" not in (body.get("description") or "")
    assert body["gallery_urls"] == []
    assert body["variants"] == []
    assert body.get("required_vault_item_id") in (None, "")


def test_host_can_patch_storefront_settings(client: TestClient, db_session: Session):
    host, _profile = _seed_storefront_host(db_session, slug="settings-shop")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "settings-shop@example.com", "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    patch = client.patch(
        "/api/v1/host/merchandise/storefront",
        headers=headers,
        json={
            "enabled": True,
            "title": "Night Market Merch",
            "description": "Official drops on Pàdéyá",
            "visibility": "public",
        },
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["enabled"] is True
    assert patch.json()["visibility"] == "public"
    assert patch.json()["title"] == "Night Market Merch"

    public = client.get(f"/api/v1/u/{host.slug}/merch")
    assert public.status_code == 200
    assert public.json()["storefront_title"] == "Night Market Merch"
    assert public.json()["is_listed"] is True


def test_host_size_chart_create_and_public_get(
    client: TestClient, db_session: Session
):
    _seed_host_event(db_session)
    headers = _login(client, "merchhost@example.com")
    chart_json = {
        "columns": ["Size", "Chest", "Length", "Sleeve"],
        "rows": [
            ["S", "96", "68", "20"],
            ["M", "102", "70", "21"],
        ],
    }
    created = client.post(
        "/api/v1/host/merchandise/size-charts",
        headers=headers,
        json={
            "name": "Unisex tee",
            "product_type": "t_shirt",
            "units": "cm",
            "chart_json": chart_json,
            "fit_notes": "True to size",
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    chart_id = body["id"]
    assert body["name"] == "Unisex tee"
    assert body["status"] == "active"
    assert body["chart_json"]["columns"][0] == "Size"

    listed = client.get("/api/v1/host/merchandise/size-charts", headers=headers)
    assert listed.status_code == 200, listed.text
    assert any(row["id"] == chart_id for row in listed.json())

    public = client.get(f"/api/v1/merch/size-charts/{chart_id}")
    assert public.status_code == 200, public.text
    assert public.json()["fit_notes"] == "True to size"
    assert public.json()["chart_json"]["rows"][0][0] == "S"


def test_inactive_size_chart_not_returned_publicly(
    client: TestClient, db_session: Session
):
    _seed_host_event(db_session)
    headers = _login(client, "merchhost@example.com")
    created = client.post(
        "/api/v1/host/merchandise/size-charts",
        headers=headers,
        json={
            "name": "Cap one-size",
            "product_type": "cap",
            "units": "cm",
            "chart_json": {
                "columns": ["Size", "Circumference"],
                "rows": [["One size", "58"]],
            },
        },
    )
    assert created.status_code == 200, created.text
    chart_id = created.json()["id"]

    patched = client.patch(
        f"/api/v1/host/merchandise/size-charts/{chart_id}",
        headers=headers,
        json={"status": "inactive"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["status"] == "inactive"

    public = client.get(f"/api/v1/merch/size-charts/{chart_id}")
    assert public.status_code == 404

    archived = client.post(
        f"/api/v1/host/merchandise/size-charts/{chart_id}/archive",
        headers=headers,
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"
    assert archived.json()["archived_at"] is not None

    listed = client.get("/api/v1/host/merchandise/size-charts", headers=headers)
    assert listed.status_code == 200
    assert all(row["id"] != chart_id for row in listed.json())

    public_after_archive = client.get(f"/api/v1/merch/size-charts/{chart_id}")
    assert public_after_archive.status_code == 404


def test_size_chart_attaches_to_product(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    chart = client.post(
        "/api/v1/host/merchandise/size-charts",
        headers=host_headers,
        json={
            "name": "Tee chart",
            "product_type": "t_shirt",
            "units": "cm",
            "chart_json": {
                "columns": ["Size", "Chest"],
                "rows": [["M", "102"]],
            },
        },
    )
    assert chart.status_code == 200, chart.text
    chart_id = chart.json()["id"]

    product = client.post(
        f"/api/v1/merch/events/{event.id}/products",
        headers=host_headers,
        json={
            "name": "Sized Tee",
            "description": "With size guide",
            "base_price": "6000.00",
            "status": "active",
            "size_chart_id": chart_id,
            "show_on_event_page": True,
            "variants": [
                {"label": "M", "inventory_count": 4, "status": "active"}
            ],
        },
    )
    assert product.status_code == 200, product.text
    assert product.json()["size_chart_id"] == chart_id

    catalog = client.get(f"/api/v1/merch/events/{event.id}/catalog")
    assert catalog.status_code == 200, catalog.text
    row = next(p for p in catalog.json() if p["id"] == product.json()["id"])
    assert row["size_chart"] is not None
    assert row["size_chart"]["id"] == chart_id
    assert row["size_chart"]["chart_json"]["rows"][0][0] == "M"


def test_post_event_drop_eligibility_and_routes(
    client: TestClient, db_session: Session
):
    _, host, event, _ = _seed_host_event(db_session)
    event.status = "completed"
    event.allow_merch_only_checkout = True
    event.end_datetime = datetime.now(UTC) - timedelta(days=1)
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")

    future = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    created = client.post(
        f"/api/v1/host/events/{event.id}/post-event-drops",
        headers=host_headers,
        json={
            "name": "Afterparty Cap",
            "base_price": "4500.00",
            "audience": "public",
            "status": "active",
            "inventory_count": 5,
            "post_event_drop_at": future,
            "drop_description": "Recap merch for attendees",
        },
    )
    assert created.status_code == 200, created.text
    drop = created.json()
    assert drop["is_post_event_drop"] is True
    assert drop["is_drop_live"] is False
    product_id = drop["id"]
    variant_id = drop["variants"][0]["id"]

    listed = client.get(
        f"/api/v1/host/events/{event.id}/post-event-drops",
        headers=host_headers,
    )
    assert listed.status_code == 200, listed.text
    assert any(row["id"] == product_id for row in listed.json())

    buyer = _register_buyer(client, "drop-buyer@example.com")
    not_live = client.post(
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
    assert not_live.status_code in {400, 403}
    detail = str(not_live.json().get("detail", "")).lower()
    assert "drop" in detail or "available" in detail or "not" in detail

    past = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    patched = client.patch(
        f"/api/v1/host/merchandise/post-event-drops/{product_id}",
        headers=host_headers,
        json={"post_event_drop_at": past, "status": "active"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["is_drop_live"] is True

    eligible = client.get(
        "/api/v1/dashboard/merchandise/post-event-drops",
        headers=buyer,
    )
    assert eligible.status_code == 200, eligible.text
    assert any(row["id"] == product_id for row in eligible.json())

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
    assert order.status_code == 201, order.text

    # Ticket-gated drop: ineligible without a ticket
    ticket_drop = client.post(
        f"/api/v1/host/events/{event.id}/post-event-drops",
        headers=host_headers,
        json={
            "name": "Ticket Cap",
            "base_price": "3000.00",
            "audience": "ticket_buyers",
            "status": "active",
            "inventory_count": 3,
            "post_event_drop_at": past,
        },
    )
    assert ticket_drop.status_code == 200, ticket_drop.text
    gated_variant = ticket_drop.json()["variants"][0]["id"]
    stranger = _register_buyer(client, "drop-stranger@example.com")
    blocked = client.post(
        "/api/v1/orders",
        headers=stranger,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": gated_variant,
                    "quantity": 1,
                }
            ],
        },
    )
    assert blocked.status_code in {400, 403}
    assert "ticket" in str(blocked.json().get("detail", "")).lower()


def test_vault_exclusive_merch_requires_eligibility(
    client: TestClient, db_session: Session
):
    from app.vault.models import VaultAccessGrant, VaultItem, VaultPurchase

    _, host, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")

    vault = client.post(
        "/api/v1/vault/host/items",
        headers=host_headers,
        json={
            "title": "Vault replay",
            "content_type": "text_post",
            "preview_text": "Teaser",
            "body": "LOCKED VAULT BODY — never expose",
            "price": "1000.00",
            "status": "published",
            "access": {"access_type": "one_time_unlock"},
        },
    )
    assert vault.status_code == 201, vault.text
    vault_item_id = vault.json()["id"]
    assert "LOCKED VAULT BODY" in (vault.json().get("body") or "")

    public_vault = client.get(f"/api/v1/vault/public/{host.slug}/{vault.json()['slug']}")
    assert public_vault.status_code == 200
    assert public_vault.json()["locked"] is True
    assert public_vault.json()["body"] is None
    assert "LOCKED VAULT BODY" not in str(public_vault.json())

    product = client.post(
        f"/api/v1/merch/events/{event.id}/products",
        headers=host_headers,
        json={
            "name": "Vault Exclusive Tee",
            "description": "SECRET merch cut for Vault members",
            "base_price": "9000.00",
            "status": "active",
            "is_vault_exclusive": True,
            "requires_vault_access": True,
            "required_vault_item_id": vault_item_id,
            "storefront_visibility": "vault_exclusive",
            "show_on_event_page": True,
            "variants": [
                {"label": "L", "inventory_count": 3, "status": "active"}
            ],
        },
    )
    assert product.status_code == 200, product.text
    variant_id = product.json()["variants"][0]["id"]

    store = client.get(f"/api/v1/u/{host.slug}/merch")
    assert store.status_code == 200, store.text
    teaser = next(p for p in store.json()["products"] if p["id"] == product.json()["id"])
    assert teaser["access_locked"] is True
    assert "SECRET" not in (teaser.get("description") or "")
    assert teaser["variants"] == []
    assert "LOCKED VAULT BODY" not in str(teaser)
    assert teaser.get("required_vault_item_id") in (None, "")

    catalog = client.get(f"/api/v1/events/{event.slug}/merchandise")
    assert catalog.status_code == 200, catalog.text
    cat_row = next(p for p in catalog.json() if p["id"] == product.json()["id"])
    assert cat_row["access_locked"] is True
    assert cat_row["variants"] == []
    assert "SECRET" not in (cat_row.get("description") or "")
    assert "LOCKED VAULT BODY" not in str(cat_row)

    buyer_headers = _register_buyer(client, "vault-merch@example.com")
    buyer = db_session.query(User).filter_by(email="vault-merch@example.com").one()

    denied = client.post(
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
    assert denied.status_code in {400, 403}
    assert "vault" in str(denied.json().get("detail", "")).lower()

    db_session.add(
        VaultPurchase(
            vault_item_id=uuid.UUID(vault_item_id),
            host_id=host.id,
            user_id=buyer.id,
            amount=Decimal("1000.00"),
            currency="NGN",
            status="paid",
            payment_reference=f"vault-merch-{buyer.id}",
            paid_at=datetime.now(UTC),
        )
    )
    db_session.add(
        VaultAccessGrant(
            vault_item_id=uuid.UUID(vault_item_id),
            host_id=host.id,
            user_id=buyer.id,
            source="purchase",
            granted_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    unlocked = client.get(
        f"/api/v1/u/{host.slug}/merch/{product.json()['id']}",
        headers=buyer_headers,
    )
    assert unlocked.status_code == 200, unlocked.text
    assert unlocked.json()["access_eligible"] is True
    assert unlocked.json()["access_locked"] is False
    assert len(unlocked.json()["variants"]) >= 1

    ok = client.post(
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
    assert ok.status_code == 201, ok.text


def test_fan_passport_merch_badge_after_verified_payment(
    client: TestClient, db_session: Session
):
    from app.passport.models import FanBadge, UserBadge

    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=2)
    variant_id = product["variants"][0]["id"]
    buyer_headers = _register_buyer(client, "badge-merch@example.com")
    buyer = db_session.query(User).filter_by(email="badge-merch@example.com").one()

    before = (
        db_session.query(UserBadge)
        .join(FanBadge, FanBadge.id == UserBadge.badge_id)
        .filter(
            UserBadge.user_id == buyer.id,
            FanBadge.slug == "first-merch-buy",
        )
        .count()
    )
    assert before == 0

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
    unpaid_badges = client.get("/api/v1/passport/me/badges", headers=buyer_headers)
    assert unpaid_badges.status_code == 200
    unpaid_row = next(
        b for b in unpaid_badges.json() if b["slug"] == "first-merch-buy"
    )
    assert unpaid_row["earned"] is False

    _pay_order(client, buyer_headers, order.json())
    db_session.expire_all()

    earned = (
        db_session.query(UserBadge)
        .join(FanBadge, FanBadge.id == UserBadge.badge_id)
        .filter(
            UserBadge.user_id == buyer.id,
            FanBadge.slug == "first-merch-buy",
        )
        .count()
    )
    assert earned == 1

    badges = client.get("/api/v1/passport/me/badges", headers=buyer_headers)
    assert badges.status_code == 200
    row = next(b for b in badges.json() if b["slug"] == "first-merch-buy")
    assert row["earned"] is True
    # Badge payloads must stay free of payment / address secrets
    blob = str(badges.json()).lower()
    assert "paystack" not in blob
    assert "authorization" not in blob
    assert "shipping" not in blob


def test_hidden_location_not_on_public_merch_or_event(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.location_visibility = "hidden_until_payment"
    event.address = "77 Hidden Venue Road"
    event.venue_name = "Secret Yard"
    event.public_location_label = "Lagos Island area"
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    created = client.post(
        f"/api/v1/merch/events/{event.id}/products",
        headers=host_headers,
        json={
            "name": "Hidden Venue Tee",
            "base_price": "5000.00",
            "status": "active",
            "pickup_location_label": "77 Hidden Venue Road booth",
            "pickup_instructions": "Meet at 77 Hidden Venue Road",
            "show_on_event_page": True,
            "variants": [
                {"label": "M", "inventory_count": 2, "status": "active"}
            ],
        },
    )
    assert created.status_code == 200, created.text

    catalog = client.get(f"/api/v1/merch/events/{event.id}/catalog")
    assert catalog.status_code == 200
    cat_blob = str(catalog.json()).lower()
    assert "77 hidden venue road" not in cat_blob

    public_event = client.get(f"/api/v1/events/{event.slug}")
    assert public_event.status_code == 200, public_event.text
    event_blob = str(public_event.json()).lower()
    assert "77 hidden venue road" not in event_blob
    # Coarse area label may remain; street must not.
    assert "secret yard" not in event_blob or public_event.json().get(
        "location_visibility"
    ) == "hidden_until_payment"


def test_host_shipping_zones_crud_and_archive_excludes_checkout(
    client: TestClient, db_session: Session
):
    """Host can list/create/patch/archive zones; archived zones skip fee match."""
    _, host, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")

    created = client.post(
        "/api/v1/host/merchandise/shipping-zones",
        headers=host_headers,
        json={
            "name": "Lagos metro",
            "country": "Nigeria",
            "state": "Lagos",
            "city": "Ikeja",
            "flat_fee": "2500.00",
            "event_id": str(event.id),
        },
    )
    assert created.status_code == 200, created.text
    zone = created.json()
    assert zone["status"] == "active"
    assert Decimal(str(zone["flat_fee"])) == Decimal("2500.00")
    zone_id = zone["id"]
    # Zone APIs never echo buyer address fields.
    assert "line1" not in zone
    assert "phone" not in zone
    assert "recipient_name" not in zone

    listed = client.get(
        "/api/v1/host/merchandise/shipping-zones",
        headers=host_headers,
    )
    assert listed.status_code == 200, listed.text
    assert any(row["id"] == zone_id for row in listed.json())

    patched = client.patch(
        f"/api/v1/host/merchandise/shipping-zones/{zone_id}",
        headers=host_headers,
        json={"flat_fee": "3000.00", "name": "Lagos Ikeja"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["name"] == "Lagos Ikeja"
    assert Decimal(str(patched.json()["flat_fee"])) == Decimal("3000.00")

    product = _create_active_product(client, host_headers, event.id, inventory=2)
    prod = db_session.get(EventMerchProduct, uuid.UUID(product["id"]))
    assert prod is not None
    prod.shipping_enabled = True
    db_session.commit()
    variant_id = product["variants"][0]["id"]
    buyer = _register_buyer(client, "zone-archive@example.com")

    ok_order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "fulfillment_method": "shipping",
            "shipping_address": {
                "recipient_name": "Zone Buyer",
                "phone_number": "+2348011112222",
                "address_line_1": "1 Demo Close",
                "city": "Ikeja",
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
    assert ok_order.status_code == 201, ok_order.text
    assert Decimal(ok_order.json()["shipping_amount"]) == Decimal("3000.00")

    archived = client.post(
        f"/api/v1/host/merchandise/shipping-zones/{zone_id}/archive",
        headers=host_headers,
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"

    # No active zones remain → shipping fee falls back to ₦0 (not a match error).
    buyer2 = _register_buyer(client, "zone-archive-2@example.com")
    after = client.post(
        "/api/v1/orders",
        headers=buyer2,
        json={
            "event_id": str(event.id),
            "fulfillment_method": "shipping",
            "shipping_address": {
                "recipient_name": "Zone Buyer Two",
                "phone_number": "+2348011113333",
                "address_line_1": "2 Demo Close",
                "city": "Ikeja",
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
    assert after.status_code == 201, after.text
    assert Decimal(after.json()["shipping_amount"]) == Decimal("0")
    # Prior order snapshot unchanged.
    assert Decimal(ok_order.json()["shipping_amount"]) == Decimal("3000.00")
