"""Phase 4.5 — CC-005 promo concurrency on PostgreSQL."""

from __future__ import annotations

import os
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.promos.models import PromoCode
from tests.phase45.helpers import create_buyer, login, run_barriered, seed_event

pytestmark = pytest.mark.skipif(
    os.environ.get("PHASE45_POSTGRES") != "1",
    reason="Phase 4.5 Postgres concurrency — set PHASE45_POSTGRES=1",
)

ITERATIONS = int(os.environ.get("PHASE45_ITERATIONS", "20"))


def test_cc005_promo_usage_limit_one_concurrent(
    client: TestClient, db_session: Session
):
    failures: list[str] = []
    for i in range(ITERATIONS):
        try:
            event, tt = seed_event(db_session, price="2000.00", qty=20)
            promo = PromoCode(
                host_id=event.host_id,
                code=f"P45{uuid4().hex[:8].upper()}",
                discount_type="fixed",
                discount_value=Decimal("500.00"),
                event_id=event.id,
                usage_limit=1,
                usage_count=0,
                status="active",
                max_per_user=5,
            )
            db_session.add(promo)
            db_session.commit()

            e1 = f"pr-a-{i}-{uuid4().hex[:8]}@example.com"
            e2 = f"pr-b-{i}-{uuid4().hex[:8]}@example.com"
            create_buyer(db_session, e1)
            create_buyer(db_session, e2)
            h1 = login(client, e1)
            h2 = login(client, e2)
            body = {
                "event_id": str(event.id),
                "promo_code": promo.code,
                "items": [{"ticket_type_id": str(tt.id), "quantity": 1}],
            }

            def _o1() -> int:
                return client.post("/api/v1/orders", headers=h1, json=body).status_code

            def _o2() -> int:
                return client.post("/api/v1/orders", headers=h2, json=body).status_code

            codes = run_barriered([_o1, _o2])
            assert codes.count(201) <= 1, codes
            db_session.expire_all()
            db_session.refresh(promo)
            assert promo.usage_count <= 1
        except Exception as exc:  # noqa: BLE001
            failures.append(f"iter={i}: {type(exc).__name__}: {exc}")
    assert not failures, failures


def test_cc005_per_user_limit_same_user_concurrent(
    client: TestClient, db_session: Session
):
    failures: list[str] = []
    for i in range(ITERATIONS):
        try:
            event, tt = seed_event(db_session, price="2000.00", qty=20)
            promo = PromoCode(
                host_id=event.host_id,
                code=f"U45{uuid4().hex[:8].upper()}",
                discount_type="fixed",
                discount_value=Decimal("100.00"),
                event_id=event.id,
                usage_limit=10,
                usage_count=0,
                status="active",
                max_per_user=1,
            )
            db_session.add(promo)
            db_session.commit()
            email = f"pr-u-{i}-{uuid4().hex[:8]}@example.com"
            create_buyer(db_session, email)
            headers = login(client, email)
            body = {
                "event_id": str(event.id),
                "promo_code": promo.code,
                "items": [{"ticket_type_id": str(tt.id), "quantity": 1}],
            }

            def _o() -> int:
                return client.post(
                    "/api/v1/orders", headers=headers, json=body
                ).status_code

            codes = run_barriered([_o, _o])
            assert codes.count(201) <= 1, codes
        except Exception as exc:  # noqa: BLE001
            failures.append(f"iter={i}: {type(exc).__name__}: {exc}")
    assert not failures, failures
