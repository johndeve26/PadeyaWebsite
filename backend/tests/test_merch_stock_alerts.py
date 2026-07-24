"""Host merch stock alerts — low stock, sold out, restock resolve."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.events.models import Event, EventCategory
from app.hosts.models import Host, HostProfile
from app.merch.models import EventMerchProduct, EventMerchVariant, MerchStockAlert
from app.merch.stock_alerts import evaluate_variant_stock_alerts
from app.users.models import User
from app.users.service import get_role_by_name


def _seed_host_product(
    db: Session,
    *,
    inventory: int = 10,
    reserved: int = 0,
    threshold: int = 5,
    email: str = "stock-alert-host@example.com",
    slug: str = "stock-alert-host",
    event_start_in_hours: int | None = 240,
) -> tuple[User, Host, EventMerchProduct, EventMerchVariant]:
    user = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Stock Alert Host",
        is_active=True,
    )
    role = get_role_by_name(db, "host")
    assert role is not None
    user.roles.append(role)
    db.add(user)
    db.flush()

    host = Host(
        user_id=user.id,
        display_name="Stock Alert Host",
        slug=slug,
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))

    category = db.query(EventCategory).first()
    start = datetime.now(UTC) + timedelta(
        hours=event_start_in_hours if event_start_in_hours is not None else 240
    )
    event = Event(
        title="Stock Alert Night",
        slug=f"{slug}-event",
        description="Event for stock alert unit tests with enough detail for validation.",
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

    product = EventMerchProduct(
        host_id=host.id,
        event_id=event.id,
        name="DJ Maze Neon Cap",
        slug="dj-maze-neon-cap",
        description="Cap for stock alert tests",
        product_type="cap",
        base_price=Decimal("5000.00"),
        currency="NGN",
        status="active",
        low_stock_threshold=threshold,
        moderation_status="clear",
    )
    db.add(product)
    db.flush()

    variant = EventMerchVariant(
        product_id=product.id,
        label="One size",
        inventory_count=inventory,
        reserved_quantity=reserved,
        sold_quantity=0,
        status="active",
    )
    db.add(variant)
    db.commit()
    db.refresh(product)
    db.refresh(variant)
    return user, host, product, variant


def test_low_stock_triggers_open_alert(db_session: Session):
    _, host, product, variant = _seed_host_product(
        db_session, inventory=4, threshold=5, email="low@example.com", slug="low-host"
    )
    created = evaluate_variant_stock_alerts(
        db_session, product=product, variant=variant, previous_available=10
    )
    db_session.commit()

    assert any(a.alert_type == "low_stock" for a in created)
    open_low = (
        db_session.query(MerchStockAlert)
        .filter_by(
            host_id=host.id,
            product_id=product.id,
            variant_id=variant.id,
            alert_type="low_stock",
            status="open",
        )
        .one()
    )
    assert open_low.threshold == 5
    assert open_low.available_snapshot == 4
    assert open_low.triggered_at is not None
    assert open_low.resolved_at is None


def test_sold_out_triggers_and_resolves_low_stock(db_session: Session):
    _, host, product, variant = _seed_host_product(
        db_session,
        inventory=3,
        threshold=5,
        email="sold@example.com",
        slug="sold-host",
    )
    evaluate_variant_stock_alerts(
        db_session, product=product, variant=variant, previous_available=6
    )
    db_session.commit()

    variant.inventory_count = 0
    created = evaluate_variant_stock_alerts(
        db_session, product=product, variant=variant, previous_available=3
    )
    db_session.commit()

    assert any(a.alert_type == "sold_out" for a in created)
    sold = (
        db_session.query(MerchStockAlert)
        .filter_by(
            host_id=host.id,
            product_id=product.id,
            variant_id=variant.id,
            alert_type="sold_out",
            status="open",
        )
        .one()
    )
    assert sold.available_snapshot == 0

    low = (
        db_session.query(MerchStockAlert)
        .filter_by(
            host_id=host.id,
            product_id=product.id,
            variant_id=variant.id,
            alert_type="low_stock",
        )
        .one()
    )
    assert low.status == "resolved"
    assert low.resolved_at is not None


def test_restocked_resolves_previous_alerts(db_session: Session):
    _, host, product, variant = _seed_host_product(
        db_session,
        inventory=0,
        threshold=5,
        email="restock@example.com",
        slug="restock-host",
    )
    evaluate_variant_stock_alerts(
        db_session, product=product, variant=variant, previous_available=2
    )
    db_session.commit()

    variant.inventory_count = 12
    created = evaluate_variant_stock_alerts(
        db_session, product=product, variant=variant, previous_available=0
    )
    db_session.commit()

    assert any(a.alert_type == "restocked" for a in created)

    sold = (
        db_session.query(MerchStockAlert)
        .filter_by(
            host_id=host.id,
            product_id=product.id,
            variant_id=variant.id,
            alert_type="sold_out",
        )
        .one()
    )
    assert sold.status == "resolved"
    assert sold.resolved_at is not None

    restocked = (
        db_session.query(MerchStockAlert)
        .filter_by(
            host_id=host.id,
            product_id=product.id,
            variant_id=variant.id,
            alert_type="restocked",
            status="open",
        )
        .one()
    )
    assert restocked.available_snapshot == 12


def test_high_reserve_and_pre_event_risk(db_session: Session):
    _, host, product, variant = _seed_host_product(
        db_session,
        inventory=10,
        reserved=8,
        threshold=5,
        email="risk@example.com",
        slug="risk-host",
        event_start_in_hours=24,
    )
    # available = 2 → low_stock + pre_event_risk; reserved 80% → high_reserve
    created = evaluate_variant_stock_alerts(
        db_session, product=product, variant=variant, previous_available=10
    )
    db_session.commit()

    types = {a.alert_type for a in created}
    assert "low_stock" in types
    assert "high_reserve" in types
    assert "pre_event_risk" in types

    open_types = {
        row.alert_type
        for row in db_session.query(MerchStockAlert).filter_by(
            host_id=host.id, status="open"
        )
    }
    assert open_types >= {"low_stock", "high_reserve", "pre_event_risk"}


def test_host_stock_alerts_api_lists_open(
    client: TestClient, db_session: Session
):
    user, host, product, variant = _seed_host_product(
        db_session,
        inventory=2,
        threshold=5,
        email="api-stock@example.com",
        slug="api-stock-host",
    )
    evaluate_variant_stock_alerts(
        db_session, product=product, variant=variant, previous_available=8
    )
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    res = client.get("/api/v1/host/merchandise/stock-alerts", headers=headers)
    assert res.status_code == 200, res.text
    rows = res.json()
    assert isinstance(rows, list)
    assert len(rows) >= 1
    low = next(r for r in rows if r["alert_type"] == "low_stock")
    assert low["product_id"] == str(product.id)
    assert low["variant_id"] == str(variant.id)
    assert low["host_id"] == str(host.id)
    assert low["threshold"] == 5
    assert low["current_available"] == 2
    assert low["product_name"] == "DJ Maze Neon Cap"
    assert low["triggered_at"]
    assert low.get("resolved_at") is None
