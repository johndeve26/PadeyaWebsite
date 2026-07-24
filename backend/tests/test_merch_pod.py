"""Print-on-demand — jobs only after verified payment; manual fulfill."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.merch.models import EventMerchProduct, MerchFulfillment, MerchPodJob
from app.merch.pod import MANUAL_FULFILLMENT_NOTE
from tests.test_merch import (
    _create_active_product,
    _login,
    _pay_order,
    _register_buyer,
    _seed_host_event,
)


def test_pod_job_created_after_paid_pod_product(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=3)
    prod = db_session.get(EventMerchProduct, uuid.UUID(product["id"]))
    assert prod is not None
    prod.print_on_demand_enabled = True
    db_session.commit()

    upsert = client.put(
        "/api/v1/host/merchandise/print-on-demand/integrations",
        headers=host_headers,
        json={"provider": "manual", "status": "connected"},
    )
    assert upsert.status_code == 200, upsert.text
    assert upsert.json()["provider"] == "manual"
    assert "credentials" not in upsert.json()
    assert upsert.json()["has_credentials"] is False

    buyer = _register_buyer(client, "pod-paid@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
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

    before = list(
        db_session.scalars(
            select(MerchPodJob).where(MerchPodJob.order_id == uuid.UUID(body["id"]))
        )
    )
    assert before == []

    _pay_order(client, buyer, body)

    jobs = list(
        db_session.scalars(
            select(MerchPodJob).where(MerchPodJob.order_id == uuid.UUID(body["id"]))
        )
    )
    assert len(jobs) == 1
    assert jobs[0].status == "manual_required"
    assert jobs[0].manual_required is True
    assert jobs[0].error_note == MANUAL_FULFILLMENT_NOTE
    assert jobs[0].provider == "manual"

    fulfillment = db_session.scalar(
        select(MerchFulfillment).where(
            MerchFulfillment.order_id == uuid.UUID(body["id"])
        )
    )
    assert fulfillment is not None
    assert fulfillment.fulfillment_method == "print_on_demand"
    assert fulfillment.pod_job_id == jobs[0].id

    host_jobs = client.get(
        "/api/v1/host/merchandise/print-on-demand",
        headers=host_headers,
    )
    assert host_jobs.status_code == 200
    assert len(host_jobs.json()) == 1
    assert host_jobs.json()[0]["status_label"] == MANUAL_FULFILLMENT_NOTE


def test_unpaid_pod_product_creates_no_job(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=2)
    prod = db_session.get(EventMerchProduct, uuid.UUID(product["id"]))
    assert prod is not None
    prod.print_on_demand_enabled = True
    db_session.commit()

    buyer = _register_buyer(client, "pod-unpaid@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
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

    jobs = list(
        db_session.scalars(
            select(MerchPodJob).where(MerchPodJob.order_id == uuid.UUID(body["id"]))
        )
    )
    assert jobs == []
    assert Decimal(body["total_amount"]) == Decimal("7500.00")


def test_mark_pod_job_manually_fulfilled(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=2)
    prod = db_session.get(EventMerchProduct, uuid.UUID(product["id"]))
    assert prod is not None
    prod.print_on_demand_enabled = True
    db_session.commit()

    buyer = _register_buyer(client, "pod-fulfill@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
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
    _pay_order(client, buyer, body)

    job = db_session.scalar(
        select(MerchPodJob).where(MerchPodJob.order_id == uuid.UUID(body["id"]))
    )
    assert job is not None

    fulfilled = client.post(
        f"/api/v1/host/merchandise/print-on-demand/jobs/{job.id}/fulfill",
        headers=host_headers,
    )
    assert fulfilled.status_code == 200, fulfilled.text
    assert fulfilled.json()["status"] == "fulfilled"
    assert fulfilled.json()["fulfilled_at"] is not None

    db_session.refresh(job)
    assert job.status == "fulfilled"
    assert job.manual_required is False

    if job.merch_fulfillment_id:
        fulfillment = db_session.get(MerchFulfillment, job.merch_fulfillment_id)
        assert fulfillment is not None
        assert fulfillment.status == "fulfilled"


def test_non_pod_product_paid_creates_no_job(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    event.allow_merch_only_checkout = True
    db_session.commit()
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id, inventory=2)
    buyer = _register_buyer(client, "pod-nonpod@example.com")
    order = client.post(
        "/api/v1/orders",
        headers=buyer,
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
    _pay_order(client, buyer, body)
    jobs = list(
        db_session.scalars(
            select(MerchPodJob).where(MerchPodJob.order_id == uuid.UUID(body["id"]))
        )
    )
    assert jobs == []


def test_product_toggle_print_on_demand_via_api(
    client: TestClient, db_session: Session
):
    _, _, event, _ = _seed_host_event(db_session)
    host_headers = _login(client, "merchhost@example.com")
    product = _create_active_product(client, host_headers, event.id)
    patched = client.patch(
        f"/api/v1/merch/products/{product['id']}",
        headers=host_headers,
        json={"print_on_demand_enabled": True},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["print_on_demand_enabled"] is True
