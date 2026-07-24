"""Sponsorship deliverable fulfillment tracking."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.messaging.models import InAppNotification
from app.sponsorships.deals_payment import paystack_reference_for_invoice
from app.sponsorships.models import SponsorshipDeal, SponsorshipDeliverable, SponsorshipInvoice
from app.payments.paystack import sign_body_for_tests
from tests.test_sponsorship_deals import _deal_flow, _login


def _activate_deal(client: TestClient, db_session: Session, ctx: dict) -> None:
    invoice = db_session.get(SponsorshipInvoice, uuid.UUID(ctx["invoice"]["id"]))
    ref = paystack_reference_for_invoice(invoice.id)
    invoice.paystack_reference = ref
    db_session.commit()
    payload = {
        "event": "charge.success",
        "data": {
            "id": 99001,
            "reference": ref,
            "amount": int(Decimal(invoice.amount) * 100),
            "status": "success",
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    client.post(
        "/api/v1/payments/webhooks/paystack",
        content=raw,
        headers={
            "x-paystack-signature": sign_body_for_tests(raw, db=db_session),
            "content-type": "application/json",
        },
    )
    db_session.expire_all()


def test_active_deal_creates_deliverables(client: TestClient, db_session: Session):
    ctx = _deal_flow(client, db_session)
    _activate_deal(client, db_session, ctx)
    rows = db_session.query(SponsorshipDeliverable).filter_by(
        deal_id=uuid.UUID(ctx["deal_id"])
    )
    assert rows.count() >= 2
    assert all(r.status == "pending" for r in rows)


def test_host_submit_and_sponsor_approve(client: TestClient, db_session: Session):
    ctx = _deal_flow(client, db_session)
    _activate_deal(client, db_session, ctx)
    listed = client.get(
        f"/api/v1/host/sponsorship-deals/{ctx['deal_id']}/deliverables",
        headers=ctx["host_headers"],
    )
    assert listed.status_code == 200, listed.text
    deliv_id = listed.json()[0]["id"]
    submitted = client.post(
        f"/api/v1/host/sponsorship-deals/{ctx['deal_id']}/deliverables/{deliv_id}/submit",
        headers=ctx["host_headers"],
        json={
            "proof_url": "https://cdn.example.com/proof.png",
            "proof_notes": "Logo live on event page",
        },
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"
    approved = client.post(
        f"/api/v1/sponsors/workspaces/{ctx['sponsor_id']}/deals/{ctx['deal_id']}/deliverables/{deliv_id}/approve",
        headers=ctx["sponsor_headers"],
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"


def test_sponsor_reject_proof(client: TestClient, db_session: Session):
    ctx = _deal_flow(client, db_session)
    _activate_deal(client, db_session, ctx)
    deliv_id = client.get(
        f"/api/v1/host/sponsorship-deals/{ctx['deal_id']}/deliverables",
        headers=ctx["host_headers"],
    ).json()[0]["id"]
    client.post(
        f"/api/v1/host/sponsorship-deals/{ctx['deal_id']}/deliverables/{deliv_id}/submit",
        headers=ctx["host_headers"],
        json={"proof_url": "https://cdn.example.com/a.png"},
    )
    rejected = client.post(
        f"/api/v1/sponsors/workspaces/{ctx['sponsor_id']}/deals/{ctx['deal_id']}/deliverables/{deliv_id}/reject",
        headers=ctx["sponsor_headers"],
        json={"rejection_reason": "Logo size too small"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


def test_non_member_cannot_list_deliverables(client: TestClient, db_session: Session):
    from app.core.security import hash_password
    from app.users.models import User
    from app.users.service import get_role_by_name

    ctx = _deal_flow(client, db_session)
    _activate_deal(client, db_session, ctx)
    stranger = User(
        email="deliv-stranger@example.com",
        password_hash=hash_password("securepass1"),
        full_name="X",
        is_active=True,
    )
    stranger.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add(stranger)
    db_session.commit()
    denied = client.get(
        f"/api/v1/sponsors/workspaces/{ctx['sponsor_id']}/deals/{ctx['deal_id']}/deliverables",
        headers=_login(client, stranger.email),
    )
    assert denied.status_code in {403, 404}


def test_reports_include_deliverable_counts(client: TestClient, db_session: Session):
    ctx = _deal_flow(client, db_session)
    _activate_deal(client, db_session, ctx)
    report = client.get(
        f"/api/v1/sponsors/workspaces/{ctx['sponsor_id']}/reports/overview",
        headers=ctx["sponsor_headers"],
    )
    assert report.status_code == 200
    deals = report.json()["deals"]
    assert deals["deliverables_pending"] >= 1
    text = report.text.lower()
    assert "attendee" not in text
    assert "raw_payload" not in text


def test_submit_queues_notification(client: TestClient, db_session: Session):
    ctx = _deal_flow(client, db_session)
    _activate_deal(client, db_session, ctx)
    deliv_id = client.get(
        f"/api/v1/host/sponsorship-deals/{ctx['deal_id']}/deliverables",
        headers=ctx["host_headers"],
    ).json()[0]["id"]
    before = db_session.scalar(select(func.count()).select_from(InAppNotification)) or 0
    client.post(
        f"/api/v1/host/sponsorship-deals/{ctx['deal_id']}/deliverables/{deliv_id}/submit",
        headers=ctx["host_headers"],
        json={"proof_url": "https://cdn.example.com/b.png"},
    )
    after = db_session.scalar(select(func.count()).select_from(InAppNotification)) or 0
    assert after > before
    latest = db_session.scalar(
        select(InAppNotification).order_by(InAppNotification.created_at.desc()).limit(1)
    )
    assert latest is not None
    assert "deliverable" in (latest.title or "").lower()


def test_all_deliverables_complete_marks_deal(client: TestClient, db_session: Session):
    ctx = _deal_flow(client, db_session)
    deal = db_session.get(SponsorshipDeal, uuid.UUID(ctx["deal_id"]))
    deal.ends_at = None
    db_session.commit()
    _activate_deal(client, db_session, ctx)
    rows = client.get(
        f"/api/v1/host/sponsorship-deals/{ctx['deal_id']}/deliverables",
        headers=ctx["host_headers"],
    ).json()
    for row in rows:
        client.post(
            f"/api/v1/host/sponsorship-deals/{ctx['deal_id']}/deliverables/{row['id']}/submit",
            headers=ctx["host_headers"],
            json={"proof_url": "https://cdn.example.com/done.png"},
        )
        client.post(
            f"/api/v1/sponsors/workspaces/{ctx['sponsor_id']}/deals/{ctx['deal_id']}/deliverables/{row['id']}/approve",
            headers=ctx["sponsor_headers"],
        )
    db_session.expire_all()
    deal = db_session.get(SponsorshipDeal, uuid.UUID(ctx["deal_id"]))
    assert deal.status == "completed"
