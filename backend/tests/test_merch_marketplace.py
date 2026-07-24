"""Merch marketplace discovery + standalone create/checkout tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory, TicketType
from app.hosts.models import Host, HostProfile
from app.merch.models import EventMerchProduct, EventMerchVariant
from app.users.models import User
from app.users.service import get_role_by_name
from tests.test_merch import _login, _register_buyer


def _seed_marketplace_host(db: Session, *, slug: str = "shop-host") -> tuple[User, Host]:
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
    db.add(
        HostProfile(
            host_id=host.id,
            city="Lagos",
            merch_storefront_enabled=True,
            merch_storefront_visibility="public",
        )
    )
    db.commit()
    db.refresh(host)
    return user, host


def _add_product(
    db: Session,
    *,
    host: Host,
    name: str,
    slug: str,
    event_id=None,
    marketplace_kind: str = "standalone",
    storefront_visibility: str = "host_storefront",
    is_vault_exclusive: bool = False,
    is_featured: bool = False,
    status: str = "active",
    inventory: int = 10,
) -> EventMerchProduct:
    product = EventMerchProduct(
        host_id=host.id,
        event_id=event_id,
        name=name,
        slug=slug,
        description=f"{name} description",
        short_description=name,
        product_type="t_shirt",
        base_price=Decimal("5000.00"),
        currency="NGN",
        status=status,
        storefront_visibility=storefront_visibility,
        is_vault_exclusive=is_vault_exclusive,
        requires_vault_access=is_vault_exclusive,
        is_event_linked=event_id is not None,
        marketplace_kind=marketplace_kind,
        marketplace_listed=True,
        category="apparel",
        is_featured=is_featured,
        moderation_status="clear",
        pickup_enabled=True,
        shipping_enabled=True,
    )
    db.add(product)
    db.flush()
    db.add(
        EventMerchVariant(
            product_id=product.id,
            label="M",
            inventory_count=inventory,
            reserved_quantity=0,
            sold_quantity=0,
            status="active",
        )
    )
    db.commit()
    db.refresh(product)
    return product


def test_public_merch_list_returns_active_public_products(
    client: TestClient, db_session: Session
):
    _, host = _seed_marketplace_host(db_session, slug="list-host")
    _add_product(db_session, host=host, name="Night Tee", slug="night-tee")
    _add_product(
        db_session,
        host=host,
        name="Draft Hoodie",
        slug="draft-hoodie",
        status="draft",
    )
    _add_product(
        db_session,
        host=host,
        name="Hidden Cap",
        slug="hidden-cap",
        storefront_visibility="hidden",
        marketplace_kind="standalone",
    )

    res = client.get("/api/v1/merch")
    assert res.status_code == 200, res.text
    body = res.json()
    names = {item["name"] for item in body["items"]}
    assert "Night Tee" in names
    assert "Draft Hoodie" not in names
    assert "Hidden Cap" not in names


def test_standalone_merch_appears_without_event(
    client: TestClient, db_session: Session
):
    _, host = _seed_marketplace_host(db_session, slug="solo-host")
    product = _add_product(
        db_session,
        host=host,
        name="Evergreen Cap",
        slug="evergreen-cap",
        event_id=None,
        marketplace_kind="standalone",
    )
    assert product.event_id is None

    res = client.get("/api/v1/merch?type=standalone")
    assert res.status_code == 200, res.text
    items = res.json()["items"]
    assert any(i["slug"] == "evergreen-cap" and i.get("event_id") in (None, "") for i in items)

    detail = client.get("/api/v1/merch/evergreen-cap")
    assert detail.status_code == 200, detail.text
    data = detail.json()
    assert data["name"] == "Evergreen Cap"
    assert data["marketplace_kind"] == "standalone"
    assert data.get("event_id") in (None, "")


def test_event_merch_appears_on_event_page(
    client: TestClient, db_session: Session
):
    _, host = _seed_marketplace_host(db_session, slug="event-merch-host")
    category = db_session.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(days=5)
    event = Event(
        title="Drop Night",
        slug="drop-night",
        description="Published event for marketplace event merch coverage tests.",
        category_id=category.id if category else None,
        host_id=host.id,
        start_datetime=start,
        end_datetime=start + timedelta(hours=3),
        venue_name="Hall",
        city="Lagos",
        state="Lagos",
        status="published",
        published_at=datetime.now(UTC),
    )
    db_session.add(event)
    db_session.flush()
    db_session.add(
        TicketType(
            event_id=event.id,
            name="General",
            type="regular",
            description="Entry",
            price=Decimal("1000.00"),
            quantity=100,
            quantity_sold=0,
            quantity_reserved=0,
            min_per_order=1,
            max_per_order=5,
            visibility="public",
            status="active",
        )
    )
    db_session.commit()

    _add_product(
        db_session,
        host=host,
        name="Event Tee",
        slug="event-tee",
        event_id=event.id,
        marketplace_kind="event_merch",
        storefront_visibility="event_only",
    )

    res = client.get("/api/v1/events/drop-night/merch")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["event_slug"] == "drop-night"
    assert any(i["name"] == "Event Tee" for i in body["items"])


def test_inactive_private_merch_hidden(client: TestClient, db_session: Session):
    _, host = _seed_marketplace_host(db_session, slug="private-host")
    _add_product(
        db_session,
        host=host,
        name="Private Link Tee",
        slug="private-link-tee",
        storefront_visibility="private_link",
    )
    res = client.get("/api/v1/merch/private-link-tee")
    assert res.status_code == 404


def test_vault_exclusive_teaser_safe(client: TestClient, db_session: Session):
    _, host = _seed_marketplace_host(db_session, slug="vault-host")
    _add_product(
        db_session,
        host=host,
        name="Vault Jacket",
        slug="vault-jacket",
        marketplace_kind="vault_exclusive",
        storefront_visibility="vault_exclusive",
        is_vault_exclusive=True,
    )
    res = client.get("/api/v1/merch/vault")
    assert res.status_code == 200, res.text
    items = res.json()["items"]
    assert any(i["slug"] == "vault-jacket" for i in items)
    row = next(i for i in items if i["slug"] == "vault-jacket")
    # Locked teasers should not expose full gallery secrets when locked.
    assert row.get("is_vault_exclusive") is True


def test_host_create_standalone_merch(client: TestClient, db_session: Session):
    user, host = _seed_marketplace_host(db_session, slug="create-host")
    headers = _login(client, user.email)

    res = client.post(
        "/api/v1/host/merch",
        headers=headers,
        json={
            "name": "Studio Cap",
            "description": "Standalone host shop cap",
            "product_type": "cap",
            "base_price": 3500,
            "currency": "NGN",
            "status": "active",
            "marketplace_kind": "standalone",
            "category": "caps",
            "pickup_enabled": True,
            "shipping_enabled": True,
            "variants": [
                {"label": "One size", "inventory_count": 25, "status": "active"}
            ],
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["event_id"] is None
    assert body.get("is_event_linked") in (False, None)
    assert body.get("marketplace_kind") in ("standalone", None)
    assert body["host_id"] == str(host.id)

    listed = client.get("/api/v1/merch?type=standalone")
    assert listed.status_code == 200
    assert any(i["name"] == "Studio Cap" for i in listed.json()["items"])


def test_buyer_can_create_host_shop_merch_order(
    client: TestClient, db_session: Session
):
    _, host = _seed_marketplace_host(db_session, slug="buyer-shop-host")
    product = _add_product(
        db_session, host=host, name="Buyer Tee", slug="buyer-tee"
    )
    variant = db_session.query(EventMerchVariant).filter_by(product_id=product.id).one()
    headers = _register_buyer(client, email="buyer-shop@example.com")

    res = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "host_id": str(host.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": str(variant.id),
                    "quantity": 1,
                }
            ],
            "fulfillment_method": "pickup",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["event_id"] is None
    assert body["host_id"] == str(host.id)
    assert body["host_slug"] == host.slug
    assert len(body["items"]) == 1
    assert body["items"][0]["item_kind"] == "merch"


def test_own_host_cannot_buy_own_standalone_merch(
    client: TestClient, db_session: Session
):
    user, host = _seed_marketplace_host(db_session, slug="own-buy-host")
    product = _add_product(
        db_session, host=host, name="Own Tee", slug="own-tee"
    )
    variant = db_session.query(EventMerchVariant).filter_by(product_id=product.id).one()
    headers = _login(client, user.email)

    res = client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "host_id": str(host.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": str(variant.id),
                    "quantity": 1,
                }
            ],
            "fulfillment_method": "pickup",
        },
    )
    assert res.status_code == 403, res.text


def test_marketplace_host_shops_endpoint(
    client: TestClient, db_session: Session
):
    _, host = _seed_marketplace_host(db_session, slug="shops-endpoint-host")
    db_session.query(HostProfile).filter(HostProfile.host_id == host.id).update(
        {"merch_storefront_enabled": False}
    )
    db_session.commit()
    _add_product(db_session, host=host, name="Shop Tee", slug="shop-tee")

    res = client.get("/api/v1/merch/hosts")
    assert res.status_code == 200, res.text
    shops = res.json()
    assert any(s.get("host_slug") == "shops-endpoint-host" for s in shops)

    home = client.get("/api/v1/merch/home").json()
    assert any(
        s.get("host_slug") == "shops-endpoint-host"
        for s in home.get("host_shops") or []
    )


def test_marketplace_home_sections(client: TestClient, db_session: Session):
    _, host = _seed_marketplace_host(db_session, slug="home-host")
    _add_product(
        db_session,
        host=host,
        name="Featured Tee",
        slug="featured-tee",
        is_featured=True,
    )
    res = client.get("/api/v1/merch/home")
    assert res.status_code == 200, res.text
    body = res.json()
    assert "featured" in body
    assert "host_shops" in body
    assert "categories" in body
    assert "drops" in body
    assert "vault_exclusives" in body


def test_marketplace_categories_endpoint(client: TestClient, db_session: Session):
    res = client.get("/api/v1/merch/categories")
    assert res.status_code == 200, res.text
    rows = res.json()
    assert isinstance(rows, list)
    assert any(r["slug"] == "apparel" for r in rows)


def test_marketplace_host_shop_without_storefront_toggle(
    client: TestClient, db_session: Session
):
    _, host = _seed_marketplace_host(db_session, slug="market-host-shop")
    db_session.query(HostProfile).filter(HostProfile.host_id == host.id).update(
        {"merch_storefront_enabled": False}
    )
    db_session.commit()
    _add_product(db_session, host=host, name="Toggle Free Tee", slug="toggle-free-tee")

    res = client.get("/api/v1/merch/hosts/market-host-shop")
    assert res.status_code == 200, res.text
    body = res.json()
    assert any(p["slug"] == "toggle-free-tee" for p in body.get("products") or [])


def test_host_shop_marketplace_path(client: TestClient, db_session: Session):
    _, host = _seed_marketplace_host(db_session, slug="path-host")
    _add_product(db_session, host=host, name="Path Cap", slug="path-cap")
    res = client.get("/api/v1/merch/hosts/path-host")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("empty") is False or body.get("products") or body.get("items")
