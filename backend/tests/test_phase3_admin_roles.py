"""Phase 3 — admin / support / finance role boundaries."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers.phase3_personas import register_persona


def test_support_cannot_start_impersonation(client: TestClient, assign_role):
    support = register_persona(
        client,
        email="p3-support@example.com",
        full_name="Support Agent",
        assign_role=assign_role,
        role="support_agent",
    )
    target = register_persona(client, email="p3-imp-target@example.com", full_name="Target")
    resp = client.post(
        f"/api/v1/admin/users/{target.user_id}/impersonation/start",
        headers=support.headers,
        json={"reason": "support should not impersonate"},
    )
    assert resp.status_code == 403, resp.text


def test_finance_admin_cannot_start_impersonation(client: TestClient, assign_role):
    finance = register_persona(
        client,
        email="p3-finance@example.com",
        full_name="Finance Admin",
        assign_role=assign_role,
        role="finance_admin",
    )
    target = register_persona(client, email="p3-fin-target@example.com", full_name="Target")
    resp = client.post(
        f"/api/v1/admin/users/{target.user_id}/impersonation/start",
        headers=finance.headers,
        json={"reason": "finance should not impersonate"},
    )
    assert resp.status_code == 403, resp.text


def test_fan_and_host_cannot_access_admin_orders(
    client: TestClient, assign_role, db_session: Session
):
    """API3-P1-001: host ``payments.view`` must not unlock platform admin orders."""
    from tests.helpers.phase3_personas import login_existing, seed_host_with_event

    fan = register_persona(client, email="p3-adm-fan@example.com", full_name="Fan")
    seed_host_with_event(db_session, email="p3-adm-host@example.com", slug_suffix="admh")
    host_h = login_existing(client, "p3-adm-host@example.com")
    for headers in (fan.headers, host_h):
        assert client.get("/api/v1/admin/orders", headers=headers).status_code == 403
        assert client.get("/api/v1/admin/payments", headers=headers).status_code == 403
        tickets = client.get("/api/v1/tickets/admin/list", headers=headers)
        assert tickets.status_code == 403, tickets.text
        transfers = client.get("/api/v1/tickets/admin/transfers", headers=headers)
        assert transfers.status_code == 403, transfers.text
        assert client.get("/api/v1/finance/admin/ledger", headers=headers).status_code == 403
        assert (
            client.get("/api/v1/finance/admin/settlement", headers=headers).status_code
            == 403
        )


def test_finance_admin_can_list_admin_orders(client: TestClient, assign_role):
    finance = register_persona(
        client,
        email="p3-fin-orders@example.com",
        full_name="Finance Orders",
        assign_role=assign_role,
        role="finance_admin",
    )
    resp = client.get("/api/v1/admin/orders", headers=finance.headers)
    assert resp.status_code == 200, resp.text


def test_support_cannot_access_finance_payouts_admin(client: TestClient, assign_role):
    support = register_persona(
        client,
        email="p3-support-fin@example.com",
        full_name="Support Fin",
        assign_role=assign_role,
        role="support_agent",
    )
    # Common finance admin surfaces — must deny support.
    for path in (
        "/api/v1/admin/finance/payouts",
        "/api/v1/admin/finance/ledger",
        "/api/v1/admin/payouts",
    ):
        resp = client.get(path, headers=support.headers)
        # 403 forbidden or 404 if route not mounted under that exact path.
        assert resp.status_code in {403, 404}, (path, resp.status_code, resp.text)


def test_super_admin_can_list_admin_orders(client: TestClient, assign_role):
    admin = register_persona(
        client,
        email="p3-super@example.com",
        full_name="Super Admin",
        assign_role=assign_role,
        role="super_admin",
    )
    resp = client.get("/api/v1/admin/orders", headers=admin.headers)
    assert resp.status_code == 200, resp.text


def test_marketing_role_cannot_impersonate(client: TestClient, assign_role):
    """``marketing`` is a platform role without admin.users.impersonate."""
    limited = register_persona(
        client,
        email="p3-mkt-limited@example.com",
        full_name="Marketing Limited",
        assign_role=assign_role,
        role="marketing",
    )
    target = register_persona(client, email="p3-mkt-target@example.com", full_name="T")
    resp = client.post(
        f"/api/v1/admin/users/{target.user_id}/impersonation/start",
        headers=limited.headers,
        json={"reason": "marketing should not impersonate"},
    )
    assert resp.status_code == 403, resp.text


def test_platform_admin_role_may_impersonate_when_granted(client: TestClient, assign_role):
    """Documented product policy: role ``admin`` includes admin.users.impersonate."""
    admin = register_persona(
        client,
        email="p3-admin-ok@example.com",
        full_name="Platform Admin",
        assign_role=assign_role,
        role="admin",
    )
    target = register_persona(client, email="p3-admin-tgt@example.com", full_name="T")
    resp = client.post(
        f"/api/v1/admin/users/{target.user_id}/impersonation/start",
        headers=admin.headers,
        json={"reason": "platform admin support reproduction"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json().get("is_impersonating") is True or "access_token" in resp.json()
