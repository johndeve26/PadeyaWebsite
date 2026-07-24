"""Sponsorship deal lifecycle: proposals, invoices, Paystack webhook."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.hosts.models import Host, HostProfile, HostVerification
from app.payments.paystack import sign_body_for_tests
from app.sponsorships.deals_payment import paystack_reference_for_invoice
from app.sponsorships.models import (
    HostSponsorshipSettings,
    Sponsor,
    SponsorTeamMember,
    SponsorshipDeal,
    SponsorshipInquiry,
    SponsorshipInvoice,
    SponsorshipPaymentEvent,
    SponsorshipPlacement,
    SponsorshipSlot,
)
from app.users.models import User
from app.users.service import get_role_by_name


def _login(client: TestClient, email: str) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "securepass1"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _host(db: Session, email: str = "deal-host@example.com") -> tuple[Host, User]:
    u = User(
        email=email,
        password_hash=hash_password("securepass1"),
        full_name="Deal Host",
        is_active=True,
    )
    u.roles.append(get_role_by_name(db, "host"))
    db.add(u)
    db.flush()
    host = Host(
        user_id=u.id,
        display_name="Deal Host",
        slug=f"dh-{email.split('@')[0]}",
        status="active",
    )
    db.add(host)
    db.flush()
    db.add(HostProfile(host_id=host.id, city="Lagos"))
    db.add(HostVerification(host_id=host.id, status="verified"))
    db.add(HostSponsorshipSettings(host_id=host.id, accepting_sponsors=True))
    db.commit()
    return host, u


def _sponsor(db: Session, owner: User) -> Sponsor:
    sp = Sponsor(
        owner_user_id=owner.id,
        user_id=owner.id,
        company_name="Deal Co",
        display_name="Deal Co",
        slug=f"dc-{owner.email.split('@')[0]}",
        sponsor_type="brand",
        contact_name="Owner",
        contact_email=owner.email,
        status="active",
        verification_status="verified",
        visibility="private",
        onboarding_status="active",
    )
    db.add(sp)
    db.commit()
    return sp


def _slot(db: Session, host: Host) -> SponsorshipSlot:
    slot = SponsorshipSlot(
        host_id=host.id,
        slot_type="title",
        title="Title sponsorship",
        description="Logo on event page",
        price=Decimal("500000"),
        status="published",
        moderation_status="approved",
    )
    db.add(slot)
    db.commit()
    return slot


def _inquiry(db: Session, *, slot: SponsorshipSlot, sponsor: Sponsor) -> SponsorshipInquiry:
    inq = SponsorshipInquiry(
        slot_id=slot.id,
        sponsor_id=sponsor.id,
        company_name=sponsor.company_name,
        contact_name="Owner",
        contact_email=sponsor.contact_email or "owner@example.com",
        message="Interested in sponsoring",
        status="reviewing",
    )
    db.add(inq)
    db.commit()
    return inq


def _deal_flow(client: TestClient, db_session: Session):
    host, host_user = _host(db_session)
    sponsor_owner = User(
        email="deal-sp@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Sponsor",
        is_active=True,
    )
    sponsor_owner.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add(sponsor_owner)
    db_session.commit()
    sponsor = _sponsor(db_session, sponsor_owner)
    slot = _slot(db_session, host)
    inquiry = _inquiry(db_session, slot=slot, sponsor=sponsor)

    host_h = _login(client, host_user.email)
    sp_h = _login(client, sponsor_owner.email)

    created = client.post(
        "/api/v1/host/sponsorship-deals",
        headers=host_h,
        json={
            "inquiry_id": str(inquiry.id),
            "sponsor_id": str(sponsor.id),
            "title": "Title package Q3",
            "package_type": "title_sponsor",
            "amount": "450000.00",
            "deliverables": ["Logo on event page", "Social mention"],
        },
    )
    assert created.status_code == 201, created.text
    deal_id = created.json()["id"]

    sent = client.post(
        f"/api/v1/host/sponsorship-deals/{deal_id}/send",
        headers=host_h,
    )
    assert sent.status_code == 200
    assert sent.json()["status"] == "proposed"

    accepted = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/deals/{deal_id}/accept",
        headers=sp_h,
    )
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["status"] == "invoice_pending"
    assert body["invoice"] is not None
    assert body["invoice"]["status"] == "issued"

    return {
        "host_headers": host_h,
        "sponsor_headers": sp_h,
        "sponsor_id": sponsor.id,
        "deal_id": deal_id,
        "invoice": body["invoice"],
        "host_user": host_user,
        "sponsor_owner": sponsor_owner,
    }


def test_host_creates_proposal_from_inquiry(client: TestClient, db_session: Session):
    ctx = _deal_flow(client, db_session)
    deal = db_session.get(SponsorshipDeal, uuid.UUID(ctx["deal_id"]))
    assert deal is not None
    assert deal.status == "invoice_pending"


def test_sponsor_viewer_cannot_accept_or_pay(client: TestClient, db_session: Session):
    host, host_user = _host(db_session, email="deal-h2@example.com")
    owner = User(
        email="deal-own2@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Owner",
        is_active=True,
    )
    owner.roles.append(get_role_by_name(db_session, "buyer"))
    viewer = User(
        email="deal-view@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Viewer",
        is_active=True,
    )
    viewer.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add_all([owner, viewer])
    db_session.commit()
    sponsor = _sponsor(db_session, owner)
    db_session.add(
        SponsorTeamMember(
            sponsor_id=sponsor.id,
            user_id=viewer.id,
            role="viewer",
            status="active",
        )
    )
    slot = _slot(db_session, host)
    inquiry = _inquiry(db_session, slot=slot, sponsor=sponsor)
    host_h = _login(client, host_user.email)
    created = client.post(
        "/api/v1/host/sponsorship-deals",
        headers=host_h,
        json={
            "inquiry_id": str(inquiry.id),
            "sponsor_id": str(sponsor.id),
            "title": "Viewer test deal",
            "package_type": "standard",
            "amount": "100000",
        },
    )
    deal_id = created.json()["id"]
    client.post(f"/api/v1/host/sponsorship-deals/{deal_id}/send", headers=host_h)
    view_h = _login(client, viewer.email)
    denied = client.post(
        f"/api/v1/sponsors/workspaces/{sponsor.id}/deals/{deal_id}/accept",
        headers=view_h,
    )
    assert denied.status_code == 403


def test_pay_init_does_not_mark_paid(client: TestClient, db_session: Session):
    ctx = _deal_flow(client, db_session)
    invoice = db_session.get(SponsorshipInvoice, uuid.UUID(ctx["invoice"]["id"]))
    ref = paystack_reference_for_invoice(invoice.id)
    with patch(
        "app.sponsorships.deals_payment.initialize_transaction",
        return_value={
            "authorization_url": "https://checkout.paystack.com/spn-test",
            "access_code": "ACC",
            "reference": ref,
        },
    ):
        pay = client.post(
            f"/api/v1/sponsors/workspaces/{ctx['sponsor_id']}/deals/{ctx['deal_id']}/pay",
            headers=ctx["sponsor_headers"],
        )
    assert pay.status_code == 200, pay.text
    invoice = db_session.get(SponsorshipInvoice, uuid.UUID(ctx["invoice"]["id"]))
    assert invoice is not None
    assert invoice.status == "payment_pending"
    deal = db_session.get(SponsorshipDeal, uuid.UUID(ctx["deal_id"]))
    assert deal is not None
    assert deal.status == "payment_pending"
    assert deal.status != "active"


def test_webhook_marks_paid_and_active_idempotent(
    client: TestClient, db_session: Session
):
    ctx = _deal_flow(client, db_session)
    invoice_id = ctx["invoice"]["id"]
    invoice = db_session.get(SponsorshipInvoice, uuid.UUID(invoice_id))
    assert invoice is not None
    ref = paystack_reference_for_invoice(invoice.id)
    invoice.paystack_reference = ref
    db_session.commit()

    payload = {
        "event": "charge.success",
        "data": {
            "id": 88001,
            "reference": ref,
            "amount": int(Decimal(invoice.amount) * 100),
            "status": "success",
            "currency": "NGN",
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    wh_headers = {
        "x-paystack-signature": sign_body_for_tests(raw, db=db_session),
        "content-type": "application/json",
    }
    first = client.post(
        "/api/v1/payments/webhooks/paystack", content=raw, headers=wh_headers
    )
    assert first.status_code == 200, first.text
    db_session.expire_all()
    invoice = db_session.get(SponsorshipInvoice, invoice.id)
    deal = db_session.get(SponsorshipDeal, uuid.UUID(ctx["deal_id"]))
    assert invoice.status == "paid"
    assert deal.status == "active"
    assert db_session.query(SponsorshipPlacement).filter_by(status="active").count() >= 1

    second = client.post(
        "/api/v1/payments/webhooks/paystack", content=raw, headers=wh_headers
    )
    assert second.status_code == 200
    assert (
        db_session.query(SponsorshipPaymentEvent)
        .filter_by(provider_reference="88001")
        .count()
        == 1
    )


def test_non_member_cannot_access_deal(client: TestClient, db_session: Session):
    ctx = _deal_flow(client, db_session)
    stranger = User(
        email="deal-stranger@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Stranger",
        is_active=True,
    )
    stranger.roles.append(get_role_by_name(db_session, "buyer"))
    db_session.add(stranger)
    db_session.commit()
    denied = client.get(
        f"/api/v1/sponsors/workspaces/{ctx['sponsor_id']}/deals/{ctx['deal_id']}",
        headers=_login(client, stranger.email),
    )
    assert denied.status_code in {403, 404}


def test_admin_can_view_deal_no_raw_payload(client: TestClient, db_session: Session):
    ctx = _deal_flow(client, db_session)
    admin = User(
        email="deal-admin@example.com",
        password_hash=hash_password("securepass1"),
        full_name="Admin",
        is_active=True,
    )
    admin.roles.append(get_role_by_name(db_session, "super_admin"))
    db_session.add(admin)
    db_session.commit()
    admin_h = _login(client, admin.email)
    listed = client.get("/api/v1/admin/sponsorship-deals", headers=admin_h)
    assert listed.status_code == 200
    detail = client.get(
        f"/api/v1/admin/sponsorship-deals/{ctx['deal_id']}", headers=admin_h
    )
    assert detail.status_code == 200
    text = detail.text.lower()
    assert "raw_payload" not in text
    assert "authorization" not in text


def test_reports_include_paid_deal_spend(client: TestClient, db_session: Session):
    ctx = _deal_flow(client, db_session)
    invoice = db_session.get(SponsorshipInvoice, uuid.UUID(ctx["invoice"]["id"]))
    ref = paystack_reference_for_invoice(invoice.id)
    invoice.paystack_reference = ref
    db_session.commit()
    payload = {
        "event": "charge.success",
        "data": {
            "id": 88002,
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
    report = client.get(
        f"/api/v1/sponsors/workspaces/{ctx['sponsor_id']}/reports/overview",
        headers=ctx["sponsor_headers"],
    )
    assert report.status_code == 200, report.text
    deals = report.json()["deals"]
    assert deals["paid_spend_ngn"] is not None
    assert Decimal(deals["paid_spend_ngn"]) >= Decimal("450000")
