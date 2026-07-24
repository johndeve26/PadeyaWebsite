"""Sponsor-branded merch — public fields, revenue splits, admin hide."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.merch.models import EventMerchProduct, MerchRevenueSplit
from app.payments.models import Order
from sqlalchemy import select
from tests.test_merch import (
    _admin_headers,
    _login,
    _pay_order,
    _register_buyer,
    _seed_host_event,
)


def _create_sponsor_product(
    client: TestClient,
    host_headers: dict[str, str],
    event_id: UUID,
    *,
    split_type: str | None = "percent",
    split_value: str | None = "10.00",
    inventory: int = 5,
) -> dict:
    response = client.post(
        f"/api/v1/merch/events/{event_id}/products",
        headers=host_headers,
        json={
            "name": "Partner Tee",
            "description": "Sponsor collab tee",
            "base_price": "10000.00",
            "status": "active",
            "pickup_instructions": "Merch stand",
            "is_sponsor_branded": True,
            "sponsor_brand_name": "Acme Partners",
            "sponsor_logo_url": "https://cdn.example.com/acme-logo.png",
            "sponsor_description": "Official partnership merch",
            "sponsor_split_type": split_type,
            "sponsor_split_value": split_value,
            "variants": [
                {
                    "label": "M / Black",
                    "inventory_count": inventory,
                    "status": "active",
                }
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_public_catalog_exposes_sponsor_brand_fields(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_sponsor_product(client, host_headers, event.id)

    catalog = client.get(f"/api/v1/merch/events/{event.id}/catalog")
    assert catalog.status_code == 200, catalog.text
    rows = catalog.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == product["id"]
    assert row["is_sponsor_branded"] is True
    assert row["sponsor_brand_name"] == "Acme Partners"
    assert row["sponsor_logo_url"] == "https://cdn.example.com/acme-logo.png"
    assert row["sponsor_description"] == "Official partnership merch"
    assert "sponsor_split_type" not in row
    assert "sponsor_split_value" not in row
    assert "sponsor_id" not in row or row.get("sponsor_id") in (None, "")


def test_sponsor_split_percent_and_fixed_on_paid_order(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")

    percent_product = _create_sponsor_product(
        client,
        host_headers,
        event.id,
        split_type="percent",
        split_value="20.00",
    )
    fixed_product = _create_sponsor_product(
        client,
        host_headers,
        event.id,
        split_type="fixed",
        split_value="1500.00",
    )
    db_product = db_session.get(EventMerchProduct, UUID(fixed_product["id"]))
    assert db_product is not None
    db_product.name = "Partner Cap"
    db_session.commit()

    buyer = _register_buyer(client, "sponsor-buyer@example.com")
    for product, expected_sponsor in (
        (percent_product, Decimal("2000.00")),
        (fixed_product, Decimal("1500.00")),
    ):
        variant_id = product["variants"][0]["id"]
        order_res = client.post(
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
        assert order_res.status_code in {200, 201}, order_res.text
        order = order_res.json()
        _pay_order(client, buyer, order)

        paid = db_session.get(Order, UUID(order["id"]))
        assert paid is not None
        split = db_session.scalar(
            select(MerchRevenueSplit).where(
                MerchRevenueSplit.order_id == paid.id,
                MerchRevenueSplit.product_id == UUID(product["id"]),
            )
        )
        assert split is not None
        assert split.is_sponsor_branded is True
        assert Decimal(split.sponsor_amount) == expected_sponsor
        assert Decimal(split.host_amount) == Decimal("10000.00") - expected_sponsor

    report = client.get(
        "/api/v1/host/merchandise/revenue",
        headers=host_headers,
    )
    assert report.status_code == 200, report.text
    body = report.json()
    assert Decimal(str(body["sponsor_amount"])) == Decimal("3500.00")
    assert int(body["sponsor_branded_line_count"]) >= 2
    assert any(
        line.get("is_sponsor_branded") for line in body.get("by_product", [])
    )


def test_admin_can_hide_sponsor_product(client: TestClient, db_session: Session):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_sponsor_product(client, host_headers, event.id)
    variant_id = product["variants"][0]["id"]
    admin = _admin_headers(client, db_session)

    listed = client.get(
        "/api/v1/admin/merchandise",
        headers=admin,
        params={"is_sponsor_branded": True},
    )
    assert listed.status_code == 200, listed.text
    assert any(row["id"] == product["id"] for row in listed.json())
    assert all(row["is_sponsor_branded"] for row in listed.json())

    hide = client.post(
        f"/api/v1/merch/admin/products/{product['id']}/moderate",
        headers=admin,
        json={"action": "hide", "note": "Misleading sponsor branding"},
    )
    assert hide.status_code == 200, hide.text
    assert hide.json()["moderation_status"] == "hidden"
    assert hide.json()["is_sponsor_branded"] is True

    catalog = client.get(f"/api/v1/merch/events/{event.id}/catalog")
    assert catalog.status_code == 200
    assert catalog.json() == []

    buyer = _register_buyer(client, "sponsor-hidden-buyer@example.com")
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
