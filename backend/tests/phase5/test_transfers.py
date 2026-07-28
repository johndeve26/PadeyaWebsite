"""Phase 5 — transfers, claim security, CC-006 concurrent claim (Postgres)."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.email.models import EmailEvent
from app.tickets.advanced_models import TicketTransfer
from app.tickets.models import Ticket
from app.tickets.service import claim_pending_ticket_transfer_for_user
from app.users.models import User
from tests.phase45.helpers import run_barriered, session_factory
from tests.phase5.helpers import create_user, host_headers, login, scan, seed_event_with_ticket

ITERATIONS = int(os.environ.get("PHASE45_ITERATIONS", "20"))


def test_transferred_old_qr_rejected_new_admits(client: TestClient, db_session: Session):
    event, _h, host_user, buyer, ticket, old_qr = seed_event_with_ticket(db_session)
    recipient = create_user(
        db_session,
        f"p5-recip-{uuid4().hex[:6]}@example.com",
        name="Recipient",
    )
    buyer_h = login(client, buyer.email)
    host_h = host_headers(client, host_user.email)
    tr = client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=buyer_h,
        json={"to_email": recipient.email, "to_name": "Recipient"},
    )
    assert tr.status_code == 200, tr.text
    new_view = client.get(f"/api/v1/tickets/{ticket.id}", headers=login(client, recipient.email))
    assert new_view.status_code == 200
    new_qr = new_view.json()["qr_payload"]
    assert new_qr and new_qr != old_qr

    bad = scan(client, host_h, event_id=event.id, qr_payload=old_qr)
    assert bad["outcome"] == "invalid"
    good = scan(client, host_h, event_id=event.id, qr_payload=new_qr)
    assert good["outcome"] == "success"


def test_pending_transfer_blocks_check_in(client: TestClient, db_session: Session):
    event, _h, host_user, buyer, ticket, qr = seed_event_with_ticket(db_session)
    buyer_h = login(client, buyer.email)
    host_h = host_headers(client, host_user.email)
    unknown = f"p5-unknown-{uuid4().hex[:6]}@example.com"
    tr = client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=buyer_h,
        json={"to_email": unknown, "to_name": "Pending Person"},
    )
    assert tr.status_code == 200, tr.text
    assert tr.json()["status"] == "pending"

    # Old QR revoked
    via_qr = scan(client, host_h, event_id=event.id, qr_payload=qr)
    assert via_qr["outcome"] == "invalid"

    # Public code also blocked while pending
    via_code = scan(client, host_h, event_id=event.id, public_code=ticket.public_code)
    assert via_code["outcome"] == "invalid"
    assert "pending transfer" in via_code["message"].lower()
    db_session.refresh(ticket)
    assert ticket.status == "active"
    assert ticket.checked_in_at is None


def test_claim_token_wrong_email_forbidden(client: TestClient, db_session: Session):
    _event, _h, _hu, buyer, ticket, _qr = seed_event_with_ticket(db_session)
    buyer_h = login(client, buyer.email)
    unknown = f"p5-claim-{uuid4().hex[:6]}@example.com"
    tr = client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=buyer_h,
        json={"to_email": unknown, "to_name": "Claim Me"},
    )
    assert tr.status_code == 200
    mail = db_session.scalar(
        select(EmailEvent).where(
            EmailEvent.template == "ticket_transfer_invite",
            EmailEvent.recipient_email == unknown,
        )
    )
    assert mail is not None
    token = mail.context_json.get("claim_token")
    assert token

    wrong = create_user(
        db_session,
        f"p5-wrong-{uuid4().hex[:6]}@example.com",
        name="Wrong Email",
    )
    wrong_h = login(client, wrong.email)
    res = client.post(
        "/api/v1/tickets/claim",
        headers=wrong_h,
        json={"token": token},
    )
    assert res.status_code == 403


def test_claim_vs_revoke_race_safe(client: TestClient, db_session: Session):
    """Sequential claim-after-revoke stays consistent."""
    _event, _h, _hu, buyer, ticket, _qr = seed_event_with_ticket(db_session)
    buyer_h = login(client, buyer.email)
    email = f"p5-race-{uuid4().hex[:6]}@example.com"
    tr = client.post(
        f"/api/v1/tickets/{ticket.id}/transfer",
        headers=buyer_h,
        json={"to_email": email, "to_name": "Race"},
    )
    transfer_id = tr.json()["id"]
    mail = db_session.scalar(
        select(EmailEvent).where(
            EmailEvent.template == "ticket_transfer_invite",
            EmailEvent.recipient_email == email,
        )
    )
    token = mail.context_json["claim_token"]

    revoke = client.post(
        f"/api/v1/tickets/transfers/{transfer_id}/revoke",
        headers=buyer_h,
    )
    assert revoke.status_code == 200

    recipient = create_user(db_session, email, name="Race")
    claim = client.post(
        "/api/v1/tickets/claim",
        headers=login(client, recipient.email),
        json={"token": token},
    )
    assert claim.status_code == 400
    db_session.refresh(ticket)
    assert ticket.buyer_user_id == buyer.id


@pytest.mark.skipif(
    os.environ.get("PHASE45_POSTGRES") != "1",
    reason="Phase 5 CC-006 requires PHASE45_POSTGRES=1",
)
def test_cc006_concurrent_transfer_claim_iterations(
    client: TestClient, db_session: Session, db_engine
):
    """CC-006: pending transfer claimed twice concurrently → one completion."""
    SessionLocal = session_factory(db_engine)
    failures: list[str] = []
    for i in range(ITERATIONS):
        try:
            _event, _h, _hu, buyer, ticket, _qr = seed_event_with_ticket(
                db_session,
                slug=f"p5-cc006-{i}-{uuid4().hex[:6]}",
                host_email=f"p5-cc006-h-{i}-{uuid4().hex[:6]}@example.com",
                buyer_email=f"p5-cc006-b-{i}-{uuid4().hex[:6]}@example.com",
            )
            email = f"p5-cc006-r-{i}-{uuid4().hex[:6]}@example.com"
            # Transfer to unknown email first (pending), then create recipient.
            buyer_h = login(client, buyer.email)
            tr = client.post(
                f"/api/v1/tickets/{ticket.id}/transfer",
                headers=buyer_h,
                json={"to_email": email, "to_name": "Claimer"},
            )
            assert tr.status_code == 200, tr.text
            assert tr.json()["status"] == "pending"
            transfer_id = tr.json()["id"]
            recipient = create_user(db_session, email, name="Claimer")

            def _worker() -> str:
                s = SessionLocal()
                try:
                    user = s.get(User, recipient.id)
                    assert user is not None
                    claim_pending_ticket_transfer_for_user(
                        s, user=user, transfer_id=transfer_id
                    )
                    return "ok"
                except Exception as exc:  # noqa: BLE001
                    s.rollback()
                    return f"err:{type(exc).__name__}"
                finally:
                    s.close()

            results = run_barriered([_worker, _worker])
            assert results.count("ok") == 1, results

            db_session.expire_all()
            row = db_session.get(Ticket, ticket.id)
            assert row is not None
            assert row.buyer_user_id == recipient.id
            completed = db_session.scalar(
                select(func.count())
                .select_from(TicketTransfer)
                .where(
                    TicketTransfer.ticket_id == ticket.id,
                    TicketTransfer.status == "completed",
                )
            )
            assert completed == 1
        except Exception as exc:  # noqa: BLE001
            failures.append(f"iter={i}: {type(exc).__name__}: {exc}")
    assert not failures, failures
