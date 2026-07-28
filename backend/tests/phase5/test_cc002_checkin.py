"""Phase 5 — CC-002 concurrent duplicate check-in (Postgres)."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.checkins.models import CheckIn
from app.checkins.schemas import CheckInRequest
from app.checkins.service import check_in_ticket
from app.tickets.models import Ticket
from app.users.models import User
from tests.phase45.helpers import run_barriered, session_factory
from tests.phase5.helpers import seed_event_with_ticket

pytestmark = pytest.mark.skipif(
    os.environ.get("PHASE45_POSTGRES") != "1",
    reason="Phase 5 CC-002 requires PHASE45_POSTGRES=1",
)

ITERATIONS = int(os.environ.get("PHASE45_ITERATIONS", "20"))


def test_cc002_concurrent_duplicate_checkin_iterations(
    client: TestClient, db_session: Session, db_engine
):
    """Two sessions race the same QR — exactly one success admission (CC-002)."""
    SessionLocal = session_factory(db_engine)
    failures: list[str] = []
    for i in range(ITERATIONS):
        try:
            event, _h, host_user, _b, ticket, qr = seed_event_with_ticket(
                db_session,
                slug=f"p5-cc002-{i}-{uuid4().hex[:6]}",
                host_email=f"p5-cc002-h-{i}-{uuid4().hex[:6]}@example.com",
                buyer_email=f"p5-cc002-b-{i}-{uuid4().hex[:6]}@example.com",
            )
            host_id = host_user.id
            event_id = event.id
            payload = CheckInRequest(event_id=event_id, qr_payload=qr)

            def _worker() -> str:
                s = SessionLocal()
                try:
                    user = s.get(User, host_id)
                    assert user is not None
                    result = check_in_ticket(s, user=user, payload=payload)
                    return result["outcome"]
                except Exception as exc:  # noqa: BLE001
                    s.rollback()
                    return f"err:{type(exc).__name__}"
                finally:
                    s.close()

            outcomes = run_barriered([_worker, _worker])
            assert outcomes.count("success") == 1, outcomes
            assert outcomes.count("duplicate") == 1, outcomes

            db_session.expire_all()
            row = db_session.get(Ticket, ticket.id)
            assert row is not None
            assert row.status == "checked_in"
            assert row.checked_in_at is not None
            success_logs = db_session.scalar(
                select(func.count())
                .select_from(CheckIn)
                .where(
                    CheckIn.ticket_id == ticket.id,
                    CheckIn.outcome == "success",
                )
            )
            assert success_logs == 1
        except Exception as exc:  # noqa: BLE001
            failures.append(f"iter={i}: {type(exc).__name__}: {exc}")
    assert not failures, failures
