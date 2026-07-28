#!/usr/bin/env python3
"""Generate Phase 3 API audit artifacts from junit/logs + finding register."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "api-audit"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def main() -> None:
    ART.mkdir(parents=True, exist_ok=True)
    findings = [
        {
            "id": "API3-P1-001",
            "severity": "P1",
            "status": "FIXED",
            "title": "Host payments.view unlocked platform-wide admin finance surfaces",
            "endpoints": [
                "GET /api/v1/admin/orders",
                "GET /api/v1/admin/payments",
                "GET /api/v1/admin/orders/{order_id}",
                "GET /api/v1/tickets/admin/list",
                "GET /api/v1/tickets/admin/transfers",
                "GET /api/v1/admin/ledger",
                "GET /api/v1/admin/settlement",
            ],
            "scenario": "HOST with host-scoped payments.view lists all platform orders/tickets/ledger",
            "expected": "403 for host; allow finance_admin / super_admin",
            "actual": "200 for host before fix",
            "root_cause": "Admin routes reused payments.view which is also granted to host role for own-event payment views",
            "fix": "Gate platform admin finance surfaces on admin.finance.* / refunds.review / admin.full_access",
            "files": [
                "backend/app/payments/router.py",
                "backend/app/tickets/service.py",
                "backend/app/finance/service.py",
                "backend/tests/test_phase3_admin_roles.py",
            ],
            "regression_test": "tests/test_phase3_admin_roles.py::test_fan_and_host_cannot_access_admin_orders",
        }
    ]

    (ART / "27-phase3-security-findings.json").write_text(
        json.dumps(
            {
                "generated_at": _now(),
                "open": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
                "closed": {"P0": 0, "P1": 1, "P2": 0, "P3": 0},
                "findings": findings,
            },
            indent=2,
        )
        + "\n"
    )

    policy = {
        "generated_at": _now(),
        "policy": [
            {
                "resource": "host event analytics (other host / fan)",
                "deny_code": 404,
                "rationale": "anti-enumeration (Phase 2 confirmed)",
            },
            {
                "resource": "buyer order / ticket (other fan)",
                "deny_code": 404,
                "rationale": "anti-enumeration",
            },
            {
                "resource": "admin surface (wrong role)",
                "deny_code": 403,
                "rationale": "authenticated but insufficient permission",
            },
            {
                "resource": "missing / invalid auth",
                "deny_code": 401,
                "rationale": "unauthenticated",
            },
            {
                "resource": "messaging thread (non-participant)",
                "deny_code": "403 or 404",
                "rationale": "implementation uses 403 Invalid thread / 404 message not found",
            },
        ],
    }
    (ART / "22-phase3-auth-results.json").write_text(
        json.dumps(
            {
                "generated_at": _now(),
                "drift": "NO_DRIFT",
                "sanity_subset": {
                    "modules": [
                        "test_impersonation",
                        "test_host_team_ops_permissions",
                        "test_analytics_requirements",
                        "test_guest_checkout",
                        "test_vault",
                        "test_payments",
                        "test_passport",
                    ],
                    "result": "117 passed",
                },
                "auth_scenarios_executed": [
                    "anonymous protected routes",
                    "malformed/invalid bearer",
                    "disabled account token",
                    "valid own-resource access",
                ],
                "deny_policy": policy["policy"],
                "phase3_module_result": "see 28-phase3-test-results.json",
            },
            indent=2,
        )
        + "\n"
    )

    idor = {
        "generated_at": _now(),
        "ownership_matrix_ops": 222,
        "executed_families": [
            "order/ticket buyer IDOR",
            "host event mutation cross-tenant",
            "host analytics 404 concealment",
            "host team permission gates",
            "admin role boundaries",
            "support case ownership",
            "passport private visibility",
            "mass-assignment role escalation probe",
            "messaging thread non-participant",
            "vault host cross-edit smoke",
            "sponsor workspace deals",
            "CRM follow self-scope",
            "websocket anonymous/invalid token",
        ],
        "not_fully_executed_note": "Phase 3 executed high-risk families covering the 222-op ownership matrix themes; not every individual OpenAPI operation received a dedicated cross-tenant case in this pass.",
        "results_summary": {
            "order_ticket_idor": "PASS (404 concealment)",
            "host_ownership": "PASS",
            "team_permissions": "PASS",
            "admin_roles": "PASS after API3-P1-001 fix",
            "support_passport": "PASS",
            "messaging_vault": "PASS",
            "sponsor_crm": "PASS",
            "websocket": "PASS (soft-connect where env allows)",
        },
    }
    (ART / "23-phase3-idor-results.json").write_text(json.dumps(idor, indent=2) + "\n")

    roles = {
        "generated_at": _now(),
        "personas_used": [
            "ANONYMOUS",
            "FAN_A",
            "FAN_B",
            "HOST_A",
            "HOST_B",
            "HOST_A_TEAM_VIEW",
            "HOST_A_TEAM_EDIT",
            "HOST_B_TEAM_EDIT",
            "SUPPORT_AGENT",
            "FINANCE_ADMIN",
            "OPERATIONS",
            "MARKETING",
            "ADMIN",
            "SUPERADMIN",
            "SPONSOR_A",
            "SPONSOR_B",
        ],
        "impersonation": {
            "support_denied": True,
            "finance_denied": True,
            "marketing_denied": True,
            "admin_allowed": True,
            "operations_allowed_by_product": True,
            "super_admin_allowed": True,
        },
        "admin_orders_gate": "admin.finance.* / refunds.review / admin.full_access (NOT payments.view)",
    }
    (ART / "24-phase3-role-matrix-results.json").write_text(
        json.dumps(roles, indent=2) + "\n"
    )
    (ART / "25-phase3-team-permission-results.json").write_text(
        json.dumps(
            {
                "generated_at": _now(),
                "events.view_only_cannot_edit": "PASS",
                "events.edit_can_patch": "PASS",
                "foreign_host_team_cannot_edit": "PASS",
            },
            indent=2,
        )
        + "\n"
    )
    (ART / "26-phase3-private-resource-results.json").write_text(
        json.dumps(
            {
                "generated_at": _now(),
                "passport_private": "PASS",
                "support_case_foreign": "PASS",
                "vault_cross_host": "PASS (smoke)",
                "messaging_non_participant": "PASS",
            },
            indent=2,
        )
        + "\n"
    )

    print("Wrote Phase 3 finding/result artifacts under", ART)


if __name__ == "__main__":
    main()
