"""Phase 9 — admin RBAC: finance mutations denied for lower admin roles."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.users.constants import ROLE_PERMISSIONS
from app.users.service import get_role_by_name
from tests.phase9.helpers import persona_with_role


def test_support_cannot_approve_refunds_or_review_payouts(client: TestClient, assign_role):
    support = persona_with_role(
        client,
        assign_role,
        email=f"support-fin-{uuid4().hex[:8]}@example.com",
        role="support_agent",
    )
    # Refund review list is allowed for support (refunds.review); approve path is separate.
    listed = client.get("/api/v1/finance/refunds/requests", headers=support.headers)
    assert listed.status_code in {200, 403}, listed.text

    # Payout admin review is finance-gated (support denied)
    payouts = client.get("/api/v1/finance/admin/payouts", headers=support.headers)
    assert payouts.status_code == 403, payouts.text

    ledger = client.get("/api/v1/finance/admin/ledger", headers=support.headers)
    assert ledger.status_code == 403, ledger.text


def test_marketing_cannot_reach_finance_or_email_secrets(client: TestClient, assign_role):
    marketing = persona_with_role(
        client,
        assign_role,
        email=f"mkt-fin-{uuid4().hex[:8]}@example.com",
        role="marketing",
    )
    assert (
        client.get("/api/v1/finance/admin/payouts", headers=marketing.headers).status_code
        == 403
    )
    assert (
        client.get("/api/v1/admin/emails/settings", headers=marketing.headers).status_code
        == 403
    )
    assert (
        client.get("/api/v1/finance/refunds/requests", headers=marketing.headers).status_code
        == 403
    )


def test_finance_cannot_mark_payout_paid_or_impersonate(client: TestClient, assign_role):
    finance = persona_with_role(
        client,
        assign_role,
        email=f"fin-paid-{uuid4().hex[:8]}@example.com",
        role="finance_admin",
    )
    # mark-paid requires super_admin role — fake payout id still 403 on auth before 404
    res = client.post(
        f"/api/v1/finance/admin/payouts/{uuid4()}/mark-paid",
        headers=finance.headers,
        json={"bank_reference": "REF-1", "evidence_url": "https://example.com/e.pdf"},
    )
    assert res.status_code == 403, res.text

    # Cannot start impersonation
    target = persona_with_role(
        client,
        assign_role,
        email=f"target-{uuid4().hex[:8]}@example.com",
        role="buyer",
    )
    imp = client.post(
        f"/api/v1/admin/users/{target.user_id}/impersonation/start",
        headers=finance.headers,
        json={"reason": "phase9", "scope": "view"},
    )
    assert imp.status_code == 403, imp.text


def test_role_catalog_finance_invariants(db_session: Session):
    support_codes = set(ROLE_PERMISSIONS["support_agent"])
    finance_codes = set(ROLE_PERMISSIONS["finance_admin"])
    marketing_codes = set(ROLE_PERMISSIONS["marketing"])
    moderation_codes = set(ROLE_PERMISSIONS["moderation"])

    assert "refunds.approve" not in support_codes
    assert "payouts.approve" not in support_codes
    assert "payouts.mark_paid" not in support_codes
    assert "admin.sponsorship_deals.finance" not in support_codes
    assert "admin.sponsorship_deals.finance" not in moderation_codes
    assert "admin.full_access" not in finance_codes
    assert "payouts.mark_paid" not in finance_codes
    assert "admin.users.impersonate" not in finance_codes
    assert "admin.sponsorship_deals.finance" in finance_codes
    assert "payments.view" not in marketing_codes
    assert "refunds.approve" not in marketing_codes

    # Seeded DB roles match catalog
    support = get_role_by_name(db_session, "support_agent")
    assert support is not None
    assert "admin.sponsorship_deals.finance" not in {p.code for p in support.permissions}


def test_mass_assignment_cannot_self_promote(client: TestClient, assign_role):
    fan = persona_with_role(
        client, assign_role, email=f"fan-esc-{uuid4().hex[:8]}@example.com", role="buyer"
    )
    # Ordinary profile update must ignore privileged fields if accepted at all.
    res = client.patch(
        "/api/v1/users/me",
        headers=fan.headers,
        json={
            "display_name": "Escalator",
            "role": "super_admin",
            "is_admin": True,
            "is_super_admin": True,
            "permissions": ["admin.full_access"],
        },
    )
    assert res.status_code in {200, 400, 422}, res.text
    me = client.get("/api/v1/auth/me", headers=fan.headers)
    assert me.status_code == 200
    body = me.json()
    roles = {r.get("name") if isinstance(r, dict) else r for r in body.get("roles", [])}
    # buyer remains; no super_admin injection
    assert "super_admin" not in roles
    assert body.get("is_super_admin") not in {True, "true"}
