"""Phase 9 — sponsorship finance void RBAC (API9-P1-001)."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.users.constants import ROLE_PERMISSIONS
from tests.phase9.helpers import persona_with_role


def test_support_cannot_void_sponsorship_invoice_endpoint(
    client: TestClient, assign_role, db_session: Session
):
    support = persona_with_role(
        client,
        assign_role,
        email=f"support-void-{uuid4().hex[:8]}@example.com",
        role="support_agent",
    )
    finance = persona_with_role(
        client,
        assign_role,
        email=f"finance-void-{uuid4().hex[:8]}@example.com",
        role="finance_admin",
    )
    invoice_id = uuid4()

    denied = client.post(
        f"/api/v1/admin/sponsorship-invoices/{invoice_id}/void",
        headers=support.headers,
    )
    assert denied.status_code == 403, denied.text

    # Finance has permission; missing invoice → 404 (auth passed)
    missing = client.post(
        f"/api/v1/admin/sponsorship-invoices/{invoice_id}/void",
        headers=finance.headers,
    )
    assert missing.status_code in {404, 400}, missing.text
    assert missing.status_code != 403


def test_catalog_support_lacks_sponsorship_finance_permission():
    assert "admin.sponsorship_deals.finance" not in ROLE_PERMISSIONS["support_agent"]
    assert "admin.sponsorship_deals.finance" not in ROLE_PERMISSIONS["moderation"]
    assert "admin.sponsorship_deals.finance" in ROLE_PERMISSIONS["finance_admin"]
