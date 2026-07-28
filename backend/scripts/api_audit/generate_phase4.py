"""Generate Phase 4 API audit artifacts from executed results."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "api-audit"


def _write(name: str, payload: dict) -> None:
    ART.mkdir(parents=True, exist_ok=True)
    path = ART / name
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print("wrote", path.relative_to(ROOT))


def main() -> None:
    now = datetime.now(UTC).isoformat()

    inventory = {
        "generated_at": now,
        "phase": 4,
        "operations": [
            {
                "method": "POST",
                "path": "/api/v1/orders",
                "auth": "buyer/guest",
                "creates_order": True,
                "changes_inventory": True,
                "external_provider": False,
            },
            {
                "method": "POST",
                "path": "/api/v1/payments/checkout/{order_id}",
                "auth": "owner/guest",
                "creates_payment": True,
                "external_provider": True,
                "idempotency": "pending payment row + provider reference",
            },
            {
                "method": "POST",
                "path": "/api/v1/payments/checkout/{order_id}/confirm",
                "auth": "owner/guest",
                "issues_tickets": True,
                "external_provider": True,
                "note": "server-side verify; not FE success",
            },
            {
                "method": "POST",
                "path": "/api/v1/payments/webhooks/paystack",
                "auth": "signature",
                "issues_tickets": True,
                "creates_ledger": True,
                "idempotency": "uq_payment_webhook_events_key + order FOR UPDATE",
            },
            {
                "method": "POST",
                "path": "/api/v1/vault/.../unlock (Paystack)",
                "auth": "buyer",
                "reference_prefix": "PDY-VLT-",
            },
            {
                "method": "POST",
                "path": "sponsorship invoice pay",
                "auth": "sponsor",
                "reference_prefix": "PDY-SPN-",
            },
        ],
        "reference_namespaces": ["PDY-", "PDY-VLT-", "PDY-SPN-"],
    }
    _write("31-phase4-operation-inventory.json", inventory)

    machines = {
        "generated_at": now,
        "order": {
            "states": ["pending", "paid", "failed", "cancelled", "abandoned", "refunded"],
            "transitions": [
                {"from": "pending", "to": "paid", "via": "finalize_successful_payment"},
                {"from": "pending", "to": "failed", "via": "mark_payment_failed"},
                {"from": "paid", "to": "paid", "via": "idempotent recovery"},
                {"forbidden": ["paid→failed silent undo via late charge.failed"]},
            ],
        },
        "payment": {
            "states": ["pending", "successful", "failed", "refunded"],
            "note": "payment.status=successful when order.status=paid",
        },
        "webhook_event": {
            "states": ["received", "processed", "failed"],
            "unique": ["provider", "event_key"],
        },
        "ticket": {
            "issued_only_after": "verified paid finalize",
            "idempotent": "issue_tickets_for_paid_order returns existing by order_id",
        },
        "vault_purchase": {"states": ["pending", "paid", "failed"], "prefix": "PDY-VLT-"},
        "sponsorship_invoice": {
            "states": ["payable", "payment_pending", "paid"],
            "prefix": "PDY-SPN-",
        },
    }
    _write("32-phase4-payment-state-machines.json", machines)

    findings = {
        "generated_at": now,
        "open": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
        "closed": {"P0": 0, "P1": 1, "P2": 0, "P3": 0},
        "findings": [
            {
                "id": "API4-P1-001",
                "severity": "P1",
                "status": "FIXED",
                "title": "Paystack charge.success could finalize when amount omitted",
                "workflow": "webhook/confirm apply_paystack_charge_success",
                "expected": "reject missing/mismatched amount; wrong currency reject",
                "actual": "amount checked only if present (orders/vault/sponsor)",
                "root_cause": "optional amount guard",
                "fix": "_require_paystack_amount_and_currency; sponsorship required amount",
                "files": [
                    "backend/app/payments/webhook.py",
                    "backend/app/sponsorships/deals_payment.py",
                    "backend/tests/test_phase4_webhook_integrity.py",
                ],
                "regression_test": "tests/test_phase4_webhook_integrity.py::test_missing_amount_rejects_finalization",
            }
        ],
    }
    _write("39-phase4-findings.json", findings)

    print("phase4 artifact stubs written; merge test results after pytest")


if __name__ == "__main__":
    main()
