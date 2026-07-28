"""Phase 5 — QR payload security & tampering."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.tickets.qr import create_signed_qr_payload, new_qr_jti
from tests.phase5.helpers import host_headers, scan, seed_event_with_ticket


def test_qr_payload_is_signed_jwt_not_raw_ids(client: TestClient, db_session: Session):
    event, _h, host_user, _b, ticket, qr = seed_event_with_ticket(db_session)
    assert str(ticket.id) not in qr
    assert str(ticket.order_id) not in qr
    assert str(ticket.buyer_user_id) not in qr
    payload = jwt.decode(
        qr,
        get_settings().effective_qr_secret,
        algorithms=["HS256"],
    )
    assert payload["typ"] == "padeya.ticket.qr"
    assert payload["code"] == ticket.public_code
    assert payload["eid"] == str(event.id)
    assert "jti" in payload
    headers = host_headers(client, host_user.email)
    body = scan(client, headers, event_id=event.id, qr_payload=qr)
    assert body["outcome"] == "success"


def test_tampered_qr_signature_rejected(client: TestClient, db_session: Session):
    event, _h, host_user, _b, ticket, qr = seed_event_with_ticket(db_session)
    headers = host_headers(client, host_user.email)
    # Flip last character of JWT signature segment
    parts = qr.split(".")
    assert len(parts) == 3
    sig = parts[2]
    flipped = ("A" if sig[-1] != "A" else "B") + sig[:-1] if sig else "AAAA"
    tampered = ".".join([parts[0], parts[1], flipped[::-1] if len(flipped) > 1 else "XX"])
    body = scan(client, headers, event_id=event.id, qr_payload=tampered)
    assert body["outcome"] == "invalid"
    db_session.refresh(ticket)
    assert ticket.status == "active"
    assert ticket.checked_in_at is None


def test_malformed_qr_rejected_no_mutation(client: TestClient, db_session: Session):
    event, _h, host_user, _b, ticket, _qr = seed_event_with_ticket(db_session)
    headers = host_headers(client, host_user.email)
    for bad in ("not-a-jwt", "a.b", "eyJhbGciOiJIUzI1NiJ9.e30.bad"):
        body = scan(client, headers, event_id=event.id, qr_payload=bad)
        assert body["outcome"] == "invalid"
    # Empty payload is a request validation / service error — no admission
    empty = client.post(
        "/api/v1/checkins/scan",
        headers=headers,
        json={"event_id": str(event.id), "qr_payload": ""},
    )
    assert empty.status_code in (200, 400, 422)
    if empty.status_code == 200:
        assert empty.json()["outcome"] == "invalid"
    db_session.refresh(ticket)
    assert ticket.status == "active"


def test_cross_event_qr_rejected(client: TestClient, db_session: Session):
    event_a, _ha, host_a, _ba, ticket_a, qr_a = seed_event_with_ticket(
        db_session, slug=f"p5-xa-{uuid4().hex[:6]}"
    )
    event_b, _hb, host_b, _bb, ticket_b, _qr_b = seed_event_with_ticket(
        db_session,
        host_email=f"p5-hb-{uuid4().hex[:6]}@example.com",
        buyer_email=f"p5-bb-{uuid4().hex[:6]}@example.com",
        slug=f"p5-xb-{uuid4().hex[:6]}",
    )
    # Same host staff on event B scanning event A QR
    headers_b = host_headers(client, host_b.email)
    body = scan(client, headers_b, event_id=event_b.id, qr_payload=qr_a)
    assert body["outcome"] == "invalid"
    assert "event" in body["message"].lower() or "valid" in body["message"].lower()
    db_session.refresh(ticket_a)
    db_session.refresh(ticket_b)
    assert ticket_a.status == "active"
    assert ticket_b.status == "active"

    # Host A cannot use ticket A QR against event B either
    headers_a = host_headers(client, host_a.email)
    # Host A is not authorized for event B → 403
    res = client.post(
        "/api/v1/checkins/scan",
        headers=headers_a,
        json={"event_id": str(event_b.id), "qr_payload": qr_a},
    )
    assert res.status_code == 403


def test_forged_qr_wrong_secret_rejected(client: TestClient, db_session: Session):
    event, _h, host_user, _b, ticket, _qr = seed_event_with_ticket(db_session)
    forged = jwt.encode(
        {
            "typ": "padeya.ticket.qr",
            "code": ticket.public_code,
            "eid": str(event.id),
            "jti": new_qr_jti(),
            "rv": 1,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(days=30),
        },
        "wrong-secret-not-padeya",
        algorithm="HS256",
    )
    headers = host_headers(client, host_user.email)
    body = scan(client, headers, event_id=event.id, qr_payload=forged)
    assert body["outcome"] == "invalid"
    db_session.refresh(ticket)
    assert ticket.status == "active"


def test_jti_mismatch_rejected(client: TestClient, db_session: Session):
    event, _h, host_user, _b, ticket, _qr = seed_event_with_ticket(db_session)
    # Valid signature but wrong jti for this ticket
    bad = create_signed_qr_payload(
        public_code=ticket.public_code,
        event_id=event.id,
        jti=new_qr_jti(),
    )
    headers = host_headers(client, host_user.email)
    body = scan(client, headers, event_id=event.id, qr_payload=bad)
    assert body["outcome"] == "invalid"
    db_session.refresh(ticket)
    assert ticket.status == "active"
