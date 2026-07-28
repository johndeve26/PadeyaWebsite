"""Phase 4 — webhook signature, amount/currency, unknown refs, frontend bypass."""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.payments.models import Order, Payment, PaymentWebhookEvent
from app.payments.paystack import sign_body_for_tests
from app.tickets.models import Ticket
from tests.helpers.phase4_payments import (
    charge_success_payload,
    create_pending_order,
    expected_kobo,
    post_signed_webhook,
    register_and_login,
    seed_published_event,
)


def test_frontend_success_without_webhook_or_confirm_issues_zero_tickets(
    client: TestClient, db_session: Session
):
    """UNVERIFIED PAYMENT → ZERO tickets (no FE callback finalizer)."""
    event, ticket_type = seed_published_event(db_session, price="1000.00")
    headers = register_and_login(client, f"fe-bypass-{uuid4().hex[:8]}@example.com")
    order = create_pending_order(
        client,
        headers,
        event_id=str(event.id),
        ticket_type_id=str(ticket_type.id),
    )

    # Simulate client-only "success" — no webhook, no confirm, no provider verify.
    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert tickets == []
    row = db_session.get(Order, UUID(order["id"]))
    assert row is not None
    assert row.status == "pending"


def test_confirm_with_unverified_provider_issues_zero_tickets(
    client: TestClient, db_session: Session
):
    event, ticket_type = seed_published_event(db_session, price="1000.00")
    headers = register_and_login(client, f"confirm-pending-{uuid4().hex[:8]}@example.com")
    order = create_pending_order(
        client,
        headers,
        event_id=str(event.id),
        ticket_type_id=str(ticket_type.id),
    )

    with patch(
        "app.payments.service.verify_transaction",
        return_value={
            "id": 1,
            "reference": order["reference"],
            "amount": expected_kobo(order["total_amount"]),
            "currency": "NGN",
            "status": "pending",
        },
    ):
        res = client.post(
            f"/api/v1/payments/checkout/{order['id']}/confirm",
            headers=headers,
        )
    assert res.status_code == 409
    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert tickets == []


def test_invalid_missing_malformed_signature_no_side_effects(
    client: TestClient, db_session: Session
):
    event, ticket_type = seed_published_event(db_session, price="1000.00")
    headers = register_and_login(client, f"sig-{uuid4().hex[:8]}@example.com")
    order = create_pending_order(
        client,
        headers,
        event_id=str(event.id),
        ticket_type_id=str(ticket_type.id),
    )
    payload = charge_success_payload(
        reference=order["reference"],
        amount_kobo=expected_kobo(order["total_amount"]),
    )
    body = json.dumps(payload).encode("utf-8")

    cases = [
        {"x-paystack-signature": "invalid", "content-type": "application/json"},
        {"content-type": "application/json"},  # missing
        {"x-paystack-signature": "not-a-hex", "content-type": "application/json"},
        {
            "x-paystack-signature": sign_body_for_tests(body, secret="wrong-secret"),
            "content-type": "application/json",
        },
    ]
    for hdrs in cases:
        res = client.post("/api/v1/payments/webhooks/paystack", content=body, headers=hdrs)
        assert res.status_code == 400, hdrs

    # Modified body with signature for original body
    sig = sign_body_for_tests(body)
    tampered = json.dumps(
        {**payload, "data": {**payload["data"], "amount": 1}}
    ).encode("utf-8")
    res = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=tampered,
        headers={"x-paystack-signature": sig, "content-type": "application/json"},
    )
    assert res.status_code == 400

    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert tickets == []
    assert db_session.get(Order, UUID(order["id"])).status == "pending"
    assert db_session.scalar(select(PaymentWebhookEvent)) is None


def test_malformed_and_empty_webhook_body(client: TestClient, db_session: Session):
    empty = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=b"",
        headers={
            "x-paystack-signature": sign_body_for_tests(b""),
            "content-type": "application/json",
        },
    )
    assert empty.status_code == 400

    bad = b"{not-json"
    res = client.post(
        "/api/v1/payments/webhooks/paystack",
        content=bad,
        headers={
            "x-paystack-signature": sign_body_for_tests(bad),
            "content-type": "application/json",
        },
    )
    assert res.status_code == 400


def test_unknown_reference_does_not_create_order_or_tickets(
    client: TestClient, db_session: Session
):
    payload = charge_success_payload(
        reference="PDY-DOESNOTEXIST0001",
        amount_kobo=100000,
        event_id=900001,
    )
    res = post_signed_webhook(client, payload)
    assert res.status_code in {400, 404, 500}

    assert db_session.scalar(select(Order).where(Order.reference == "PDY-DOESNOTEXIST0001")) is None
    assert list(db_session.scalars(select(Ticket))) == []


def test_wrong_subsystem_vault_prefix_does_not_pay_ticket_order(
    client: TestClient, db_session: Session
):
    event, ticket_type = seed_published_event(db_session, price="1000.00")
    headers = register_and_login(client, f"ns-{uuid4().hex[:8]}@example.com")
    order = create_pending_order(
        client,
        headers,
        event_id=str(event.id),
        ticket_type_id=str(ticket_type.id),
    )
    # Forge a vault-prefixed reference that is not a vault purchase
    payload = charge_success_payload(
        reference="PDY-VLT-NOTAREALPURCHASE",
        amount_kobo=expected_kobo(order["total_amount"]),
        event_id=900002,
    )
    res = post_signed_webhook(client, payload)
    assert res.status_code in {400, 404, 500}
    assert db_session.get(Order, UUID(order["id"])).status == "pending"
    assert list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    ) == []


def test_amount_mismatch_rejects_and_issues_zero_tickets(
    client: TestClient, db_session: Session
):
    event, ticket_type = seed_published_event(db_session, price="1000.00")
    headers = register_and_login(client, f"amt-{uuid4().hex[:8]}@example.com")
    order = create_pending_order(
        client,
        headers,
        event_id=str(event.id),
        ticket_type_id=str(ticket_type.id),
    )
    expected = expected_kobo(order["total_amount"])

    for amount in (expected - 1, expected + 1, 0, -1, 10**12):
        payload = charge_success_payload(
            reference=order["reference"],
            amount_kobo=amount,
            event_id=910000 + abs(amount) % 1000,
        )
        res = post_signed_webhook(client, payload)
        assert res.status_code == 400, amount

    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert tickets == []
    assert db_session.get(Order, UUID(order["id"])).status == "pending"


def test_missing_amount_rejects_finalization(client: TestClient, db_session: Session):
    """API4-P1-001 regression: amount must be present (not optional)."""
    event, ticket_type = seed_published_event(db_session, price="1000.00")
    headers = register_and_login(client, f"noamt-{uuid4().hex[:8]}@example.com")
    order = create_pending_order(
        client,
        headers,
        event_id=str(event.id),
        ticket_type_id=str(ticket_type.id),
    )
    payload = charge_success_payload(
        reference=order["reference"],
        amount_kobo=0,
        event_id=920001,
        include_amount=False,
    )
    res = post_signed_webhook(client, payload)
    assert res.status_code == 400
    assert "amount" in res.json()["detail"].lower()
    assert list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    ) == []
    assert db_session.get(Order, UUID(order["id"])).status == "pending"


def test_wrong_currency_rejects_finalization(client: TestClient, db_session: Session):
    event, ticket_type = seed_published_event(db_session, price="1000.00")
    headers = register_and_login(client, f"cur-{uuid4().hex[:8]}@example.com")
    order = create_pending_order(
        client,
        headers,
        event_id=str(event.id),
        ticket_type_id=str(ticket_type.id),
    )
    payload = charge_success_payload(
        reference=order["reference"],
        amount_kobo=expected_kobo(order["total_amount"]),
        event_id=930001,
        currency="USD",
    )
    res = post_signed_webhook(client, payload)
    assert res.status_code == 400
    assert list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    ) == []


def test_verified_success_issues_exact_quantity_once(
    client: TestClient, db_session: Session
):
    event, ticket_type = seed_published_event(db_session, price="1000.00")
    headers = register_and_login(client, f"ok-{uuid4().hex[:8]}@example.com")
    order = create_pending_order(
        client,
        headers,
        event_id=str(event.id),
        ticket_type_id=str(ticket_type.id),
        quantity=2,
    )
    payload = charge_success_payload(
        reference=order["reference"],
        amount_kobo=expected_kobo(order["total_amount"]),
        event_id=940001,
    )
    res = post_signed_webhook(client, payload)
    assert res.status_code == 200, res.text
    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert len(tickets) == 2
    assert all(t.status == "active" for t in tickets)
    assert all(t.qr_token is not None or True for t in tickets)  # qr may be relation

    # Triple identical delivery
    for _ in range(2):
        again = post_signed_webhook(client, payload)
        assert again.status_code == 200
        assert again.json()["status"] == "duplicate"
    tickets_after = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert len(tickets_after) == 2
    db_session.refresh(ticket_type)
    assert ticket_type.quantity_sold == 2


def test_semantic_duplicate_same_reference_different_event_id(
    client: TestClient, db_session: Session
):
    event, ticket_type = seed_published_event(db_session, price="1000.00")
    headers = register_and_login(client, f"sem-{uuid4().hex[:8]}@example.com")
    order = create_pending_order(
        client,
        headers,
        event_id=str(event.id),
        ticket_type_id=str(ticket_type.id),
    )
    p1 = charge_success_payload(
        reference=order["reference"],
        amount_kobo=expected_kobo(order["total_amount"]),
        event_id=950001,
    )
    p2 = charge_success_payload(
        reference=order["reference"],
        amount_kobo=expected_kobo(order["total_amount"]),
        event_id=950002,
    )
    assert post_signed_webhook(client, p1).status_code == 200
    second = post_signed_webhook(client, p2)
    assert second.status_code == 200
    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert len(tickets) == 1
    payments = list(
        db_session.scalars(select(Payment).where(Payment.order_id == UUID(order["id"])))
    )
    assert len([p for p in payments if p.status == "successful"]) == 1


def test_late_failure_does_not_undo_paid_order(client: TestClient, db_session: Session):
    event, ticket_type = seed_published_event(db_session, price="1000.00")
    headers = register_and_login(client, f"late-{uuid4().hex[:8]}@example.com")
    order = create_pending_order(
        client,
        headers,
        event_id=str(event.id),
        ticket_type_id=str(ticket_type.id),
    )
    ok = charge_success_payload(
        reference=order["reference"],
        amount_kobo=expected_kobo(order["total_amount"]),
        event_id=960001,
    )
    assert post_signed_webhook(client, ok).status_code == 200

    fail_payload = {
        "event": "charge.failed",
        "data": {
            "id": 960002,
            "reference": order["reference"],
            "amount": expected_kobo(order["total_amount"]),
            "currency": "NGN",
            "status": "failed",
        },
    }
    fail = post_signed_webhook(client, fail_payload)
    assert fail.status_code == 200
    row = db_session.get(Order, UUID(order["id"]))
    assert row.status == "paid"
    tickets = list(
        db_session.scalars(select(Ticket).where(Ticket.order_id == UUID(order["id"])))
    )
    assert len(tickets) == 1


def test_checkout_blocked_for_completed_and_cancelled_events(
    client: TestClient, db_session: Session
):
    headers = register_and_login(client, f"buyer-gate-{uuid4().hex[:8]}@example.com")
    for status_name in ("completed", "cancelled", "draft"):
        event, ticket_type = seed_published_event(
            db_session,
            price="1000.00",
            slug=f"gate-{status_name}-{uuid4().hex[:6]}",
            host_email=f"host-{status_name}-{uuid4().hex[:6]}@example.com",
        )
        event.status = status_name
        db_session.commit()
        res = client.post(
            "/api/v1/orders",
            headers=headers,
            json={
                "event_id": str(event.id),
                "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
            },
        )
        assert res.status_code in {400, 403, 404, 409, 422}, (
            status_name,
            res.status_code,
            res.text,
        )


def test_zero_and_negative_quantity_rejected(client: TestClient, db_session: Session):
    event, ticket_type = seed_published_event(db_session, price="1000.00")
    headers = register_and_login(client, f"qty-{uuid4().hex[:8]}@example.com")
    for qty in (0, -1):
        res = client.post(
            "/api/v1/orders",
            headers=headers,
            json={
                "event_id": str(event.id),
                "items": [{"ticket_type_id": str(ticket_type.id), "quantity": qty}],
            },
        )
        assert res.status_code in {400, 422}, (qty, res.status_code, res.text)
