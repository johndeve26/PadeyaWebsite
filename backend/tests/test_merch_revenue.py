"""Merch revenue split snapshots, refund reversal, and PII-free CSV export."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.merch.fulfillment import cancel_fulfillments_for_refunded_order
from app.merch.models import MerchRevenueSplit
from app.merch.revenue import (
    _PII_COLUMNS,
    admin_revenue_report,
    create_splits_for_paid_order,
    export_admin_revenue_csv,
    export_host_revenue_csv,
    host_revenue_report,
    reverse_splits_on_refund,
)
from app.payments.models import Order
from tests.test_merch import (
    _admin_headers,
    _create_active_product,
    _login,
    _pay_order,
    _register_buyer,
    _seed_host_event,
)


def _enable_merch_only(db: Session, event) -> None:
    event.allow_merch_only_checkout = True
    db.commit()


def _place_and_pay_merch(
    client: TestClient,
    db: Session,
    *,
    event,
    variant_id: str,
    buyer_email: str,
) -> dict:
    buyer = _register_buyer(client, buyer_email)
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "item_kind": "merch",
                    "merch_variant_id": variant_id,
                    "quantity": 2,
                }
            ],
        },
    )
    assert order.status_code == 201, order.text
    body = order.json()
    _pay_order(client, buyer, body)
    return body


def test_create_splits_on_verified_payment(
    client: TestClient, db_session: Session
):
    _, host, event, _ = _seed_host_event(db_session)
    _enable_merch_only(db_session, event)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=10)
    variant_id = product["variants"][0]["id"]

    body = _place_and_pay_merch(
        client,
        db_session,
        event=event,
        variant_id=variant_id,
        buyer_email="rev-pay@example.com",
    )

    splits = list(
        db_session.scalars(
            select(MerchRevenueSplit).where(
                MerchRevenueSplit.order_id == UUID(body["id"])
            )
        )
    )
    assert len(splits) == 1
    split = splits[0]
    assert split.status == "payable"
    assert split.host_id == host.id
    assert Decimal(split.gross_amount) > 0
    assert Decimal(split.platform_amount) >= 0
    assert Decimal(split.host_amount) > 0
    assert (
        Decimal(split.host_amount)
        + Decimal(split.platform_amount)
        + Decimal(split.sponsor_amount)
        + Decimal(split.print_partner_amount)
    ) == Decimal(split.gross_amount)

    # Idempotent — second call does not duplicate
    order_row = db_session.get(Order, UUID(body["id"]))
    assert order_row is not None
    again = create_splits_for_paid_order(db_session, order_row)
    db_session.commit()
    assert len(again) == 1
    assert (
        db_session.scalar(
            select(MerchRevenueSplit).where(
                MerchRevenueSplit.order_id == UUID(body["id"])
            )
        )
        is not None
    )
    count = len(
        list(
            db_session.scalars(
                select(MerchRevenueSplit).where(
                    MerchRevenueSplit.order_id == UUID(body["id"])
                )
            )
        )
    )
    assert count == 1


def test_reverse_splits_on_refund(client: TestClient, db_session: Session):
    _, host, event, _ = _seed_host_event(db_session)
    _enable_merch_only(db_session, event)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=5)
    variant_id = product["variants"][0]["id"]

    body = _place_and_pay_merch(
        client,
        db_session,
        event=event,
        variant_id=variant_id,
        buyer_email="rev-refund@example.com",
    )
    order_row = db_session.get(Order, UUID(body["id"]))
    assert order_row is not None

    split = db_session.scalar(
        select(MerchRevenueSplit).where(MerchRevenueSplit.order_id == order_row.id)
    )
    assert split is not None
    original_gross = Decimal(split.gross_amount)

    cancel_fulfillments_for_refunded_order(db_session, order=order_row)
    db_session.commit()
    db_session.refresh(split)

    assert split.status == "reversed"
    assert Decimal(split.gross_amount) == original_gross

    report = host_revenue_report(db_session, host_id=host.id)
    assert Decimal(report["total_gross"]) == Decimal("0.00")
    assert Decimal(report["refunds"]["gross"]) == original_gross
    assert report["refunds"]["line_count"] == 1
    assert report["units_sold"] == 0


def test_reverse_splits_idempotent_via_direct_call(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    _enable_merch_only(db_session, event)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    body = _place_and_pay_merch(
        client,
        db_session,
        event=event,
        variant_id=product["variants"][0]["id"],
        buyer_email="rev-idem@example.com",
    )
    order_row = db_session.get(Order, UUID(body["id"]))
    assert order_row is not None
    reverse_splits_on_refund(db_session, order_row)
    reverse_splits_on_refund(db_session, order_row)
    db_session.commit()
    split = db_session.scalar(
        select(MerchRevenueSplit).where(MerchRevenueSplit.order_id == order_row.id)
    )
    assert split is not None
    assert split.status == "reversed"


def test_host_and_admin_report_metrics(client: TestClient, db_session: Session):
    _, host, event, _ = _seed_host_event(db_session)
    _enable_merch_only(db_session, event)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=20)
    variant_id = product["variants"][0]["id"]

    _place_and_pay_merch(
        client,
        db_session,
        event=event,
        variant_id=variant_id,
        buyer_email="rev-report@example.com",
    )

    host_report = host_revenue_report(db_session, host_id=host.id)
    assert Decimal(host_report["total_merch_gmv"]) > 0
    assert host_report["units_sold"] == 2
    assert "by_event" in host_report
    assert "by_product" in host_report
    assert "by_variant" in host_report
    assert "by_fulfillment_method" in host_report
    assert "top_products" in host_report
    assert "payout_status" in host_report
    assert "discount_impact" in host_report
    assert "bundle_revenue" in host_report
    assert "sponsor_branded_revenue" in host_report
    assert host_report["payout_status"]["pending_payout_line_count"] >= 1

    api = client.get("/api/v1/host/merchandise/revenue", headers=host_headers)
    assert api.status_code == 200, api.text
    body = api.json()
    assert Decimal(str(body["total_merch_gmv"])) == Decimal(
        host_report["total_merch_gmv"]
    )
    blob = str(body).lower()
    assert "rev-report@example.com" not in blob
    assert "+234" not in blob
    assert "hidden street" not in blob

    admin = admin_revenue_report(db_session)
    assert Decimal(admin["platform_merch_gmv"]) > 0
    assert Decimal(admin["platform_fees"]) >= 0
    assert Decimal(admin["host_revenue"]) > 0
    assert "top_hosts" in admin
    assert "top_products" in admin
    assert "top_events" in admin
    assert "pending_payouts" in admin
    assert admin["pending_payouts"]["line_count"] >= 1

    admin_headers = _admin_headers(client, db_session, "rev-admin@example.com")
    admin_api = client.get(
        "/api/v1/admin/merchandise/revenue", headers=admin_headers
    )
    assert admin_api.status_code == 200, admin_api.text
    assert Decimal(str(admin_api.json()["platform_merch_gmv"])) > 0
    assert Decimal(str(admin_api.json()["host_revenue"])) > 0


def test_csv_export_has_no_pii(client: TestClient, db_session: Session):
    _, host, event, _ = _seed_host_event(db_session)
    _enable_merch_only(db_session, event)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    _place_and_pay_merch(
        client,
        db_session,
        event=event,
        variant_id=product["variants"][0]["id"],
        buyer_email="rev-csv-buyer@example.com",
    )

    host_csv = export_host_revenue_csv(db_session, host_id=host.id)
    admin_csv = export_admin_revenue_csv(db_session)
    for csv_text in (host_csv, admin_csv):
        header = csv_text.splitlines()[0].lower()
        for col in _PII_COLUMNS:
            assert col not in header.split(",")
        assert "rev-csv-buyer@example.com" not in csv_text.lower()
        assert "phone" not in header
        assert "email" not in header
        assert "address" not in header
        assert "recipient" not in header
        assert "payment_reference" not in header
        assert "gross" in header
        assert "host_amount" in header

    export = client.get(
        "/api/v1/host/merchandise/revenue/export.csv",
        headers=host_headers,
    )
    assert export.status_code == 200, export.text
    assert "text/csv" in export.headers.get("content-type", "")
    assert "rev-csv-buyer@example.com" not in export.text.lower()

    admin_headers = _admin_headers(client, db_session, "rev-csv-admin@example.com")
    admin_export = client.get(
        "/api/v1/admin/merchandise/revenue/export.csv",
        headers=admin_headers,
    )
    assert admin_export.status_code == 200, admin_export.text
    assert "host_id" in admin_export.text.splitlines()[0]
    assert "rev-csv-buyer@example.com" not in admin_export.text.lower()
