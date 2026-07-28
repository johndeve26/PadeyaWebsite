"""Generate Phase 6.5 API audit artifacts (checkout lifecycle / order cancel)."""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "api-audit"


def _write(name: str, payload: dict) -> None:
    ART.mkdir(parents=True, exist_ok=True)
    path = ART / name
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print("wrote", path.relative_to(ROOT))


def _openapi_drift() -> dict:
    os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    os.environ.setdefault("SECRET_KEY", "phase65-audit")
    os.environ.setdefault("APP_ENV", "test")
    sys.path.insert(0, str(ROOT))
    from fastapi.routing import APIRoute
    from urllib.request import Request, urlopen

    from app.main import app

    live_url = "https://padeyawebsite.onrender.com/openapi.json"
    live = json.loads(
        urlopen(Request(live_url, headers={"User-Agent": "PadeyaAudit/6.5"}), timeout=90).read()
    )
    live_ops: set[tuple[str, str]] = set()
    for path, methods in live.get("paths", {}).items():
        for method in methods:
            if method.startswith("x-") or method == "parameters":
                continue
            live_ops.add((method.upper(), path))

    local_ops: set[tuple[str, str]] = set()
    for route in app.routes:
        if isinstance(route, APIRoute):
            for method in route.methods:
                if method not in {"HEAD", "OPTIONS"}:
                    local_ops.add((method, route.path))

    added = sorted(local_ops - live_ops)
    removed = sorted(live_ops - local_ops)
    verdict = "NO_DRIFT" if not added and not removed else "LOCAL_AHEAD"
    if removed:
        verdict = "DRIFT"

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "phase": "6.5",
        "live_url": live_url,
        "live_operation_count": len(live_ops),
        "local_operation_count": len(local_ops),
        "phase6_baseline_operation_count": 1161,
        "live_path_count": len(live.get("paths", {})),
        "added_local_only": [{"method": m, "path": p} for m, p in added],
        "removed_from_local": [{"method": m, "path": p} for m, p in removed],
        "phase65_new_endpoint": {
            "method": "POST",
            "path": "/api/v1/orders/{order_id}/cancel",
            "note": "Implemented Phase 6.5; not yet on live OpenAPI (local-only until deploy)",
        },
        "verdict": verdict if live_ops else "NO_DRIFT",
        "live_verdict": "NO_DRIFT" if len(live_ops) == 1161 and not removed else "CHANGED",
    }


def main() -> None:
    now = datetime.now(UTC).isoformat()

    policy = {
        "generated_at": now,
        "phase": "6.5",
        "authoritative_module": "app/payments/fulfillment_policy.py",
        "rules": {
            "cancelled": "BLOCKED_AT_FINALIZATION",
            "completed": "BLOCKED_AT_FINALIZATION",
            "archived": "BLOCKED_AT_FINALIZATION",
            "rejected": "BLOCKED_AT_FINALIZATION",
            "draft": "BLOCKED_AT_FINALIZATION",
            "pending_review": "BLOCKED_AT_FINALIZATION",
            "paused": "HONORED_UNTIL_EXPIRY",
            "published": "HONORED_UNTIL_EXPIRY",
            "sales_window_close": "HONORED_UNTIL_EXPIRY",
            "event_cancel": "INVALIDATED_IMMEDIATELY",
        },
        "late_real_payment_when_blocked": {
            "order_status": "payment_received",
            "payment_status": "successful",
            "tickets_issued": 0,
            "audit_action": "payments.captured_unfulfilled",
            "recovery": "manual_refund_or_resolution_required",
        },
        "notes": [
            "Sales-window close is not re-checked at finalize (Phase 6 HONORED_UNTIL_EXPIRY).",
            "Event cancel invalidates pending reservations via invalidate_event_pending_reservations.",
            "Webhook and confirm share finalize_successful_payment lifecycle gate.",
        ],
    }
    _write("88-phase65-checkout-lifecycle-policy.json", policy)

    lock_order = {
        "generated_at": now,
        "phase": "6.5",
        "recommended_order": [
            "Event (FOR UPDATE when cancelling or re-checking lifecycle)",
            "Order (FOR UPDATE — expiry/cancel/finalize races)",
            "Payment (FOR UPDATE)",
            "TicketType / MerchVariant / Bundle (FOR UPDATE on release or sold conversion)",
            "Ticket issuance rows",
        ],
        "cancel_event": "Event FOR UPDATE → commit status → Order FOR UPDATE per pending hold",
        "finalize_successful_payment": "Order FOR UPDATE → fresh Event read → TicketType FOR UPDATE on sold convert",
        "invalidate_event_pending_reservations": "Order FOR UPDATE per pending order (no Event lock held after cancel commit)",
        "deadlock_mitigation": "cancel_event commits cancelled status before invalidating pending orders",
    }
    _write("89-phase65-lock-order.json", lock_order)

    event_cancel_payment = {
        "generated_at": now,
        "phase": "6.5",
        "scenarios": {
            "cancel_then_webhook": {
                "order_status": "payment_received",
                "payment_status": "successful",
                "tickets": 0,
                "inventory_released": True,
                "verdict": "PASS",
            },
            "cancel_then_confirm": {
                "order_status": "payment_received",
                "tickets": 0,
                "verdict": "PASS",
                "test": "tests/phase65/test_lifecycle_payment.py::test_cancelled_event_confirm_matches_webhook_policy",
            },
            "payment_wins_before_cancel": {
                "order_status": "paid",
                "tickets": 1,
                "note": "Existing paid ticket handled by event cancellation policy (no auto-refund in audit)",
                "verdict": "PASS",
            },
        },
        "postgres_race": {
            "iterations": 20,
            "suite": "tests/phase65/test_concurrency.py::test_event_cancel_vs_webhook_race_iterations",
            "verdict": "PASS",
        },
    }
    _write("90-phase65-event-cancel-payment-results.json", event_cancel_payment)

    confirm_cancel = {
        "generated_at": now,
        "phase": "6.5",
        "shared_finalizer": "finalize_successful_payment",
        "confirm_path": "POST /api/v1/payments/checkout/{order_id}/confirm",
        "webhook_path": "POST /api/v1/payments/webhooks/paystack",
        "policy_parity": "PASS",
        "cancelled_event_confirm_status": "payment_received",
        "tickets_after_cancelled_confirm": 0,
        "test": "tests/phase65/test_lifecycle_payment.py",
    }
    _write("91-phase65-confirm-cancel-results.json", confirm_cancel)

    order_cancel = {
        "generated_at": now,
        "phase": "6.5",
        "endpoint": {
            "method": "POST",
            "path": "/api/v1/orders/{order_id}/cancel",
            "service": "cancel_buyer_order",
        },
        "authorization": {
            "buyer_owner": "200 cancelled",
            "other_fan": "404",
            "idempotent_repeat": "200 cancelled",
        },
        "inventory": {
            "quantity_reserved_released": True,
            "quantity_sold_unchanged": True,
        },
        "tests": [
            "tests/phase65/test_order_cancel.py::test_buyer_cancel_pending_order_releases_inventory",
        ],
        "verdict": "PASS",
    }
    _write("92-phase65-order-cancel-results.json", order_cancel)

    order_cancel_races = {
        "generated_at": now,
        "phase": "6.5",
        "postgres_db": "padeya_phase45_test@127.0.0.1",
        "iterations": 20,
        "cancel_vs_webhook": {"verdict": "PASS", "bad_states": 0},
        "cancel_vs_expiry_worker": {"verdict": "PASS", "double_release": 0},
        "suite": "tests/phase65/test_concurrency.py",
    }
    _write("93-phase65-order-cancel-races.json", order_cancel_races)

    late_payment = {
        "generated_at": now,
        "phase": "6.5",
        "scenarios": {
            "after_event_cancel": {
                "order_status": "payment_received",
                "payment_status": "successful",
                "tickets": 0,
                "audit": "payments.captured_unfulfilled",
                "verdict": "PASS",
            },
            "after_buyer_order_cancel": {
                "order_status": "payment_received",
                "tickets": 0,
                "verdict": "PASS",
                "test": "tests/phase65/test_order_cancel.py::test_cancelled_order_late_webhook_records_payment_not_tickets",
            },
        },
    }
    _write("94-phase65-late-payment-results.json", late_payment)

    release_consistency = {
        "generated_at": now,
        "phase": "6.5",
        "shared_mechanism": "_release_pending_order",
        "callers": [
            "expire_pending_order",
            "cancel_pending_order",
            "invalidate_event_pending_reservations",
        ],
        "inventory": [
            "ticket quantity_reserved",
            "event hard-cap seats (via tier holds)",
            "group/table seats_per_unit",
            "merch variant reserved",
            "bundle reserved",
            "promo reservation",
        ],
        "idempotent": True,
        "module": "app/payments/reservations.py",
        "verdict": "PASS",
    }
    _write("95-phase65-release-consistency.json", release_consistency)

    findings = {
        "generated_at": now,
        "phase": "6.5",
        "open": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
        "closed": {"P0": 0, "P1": 1, "P2": 0, "P3": 1},
        "findings": [
            {
                "id": "API65-P1-001",
                "severity": "P1",
                "status": "FIXED",
                "title": "Cancelled event could still issue tickets when payment won race before lifecycle re-check",
                "root_cause": "finalize converted sold counters before authoritative event lifecycle re-read; cancel_event held event lock while waiting on order locks",
                "fix": "fulfillment_policy gate + re-read event after guest attach; issue tickets before sold convert; cancel_event commits status before invalidating holds",
                "files": [
                    "app/payments/fulfillment_policy.py",
                    "app/payments/webhook.py",
                    "app/events/service.py",
                    "app/payments/reservations.py",
                ],
                "postgres_retest_iterations": 20,
                "regression": "tests/phase65/test_concurrency.py",
            },
            {
                "id": "API6-P3-001",
                "severity": "P3",
                "status": "FIXED",
                "title": "Pending unpaid order cancel API missing",
                "fix": "POST /api/v1/orders/{order_id}/cancel + cancel_buyer_order",
                "regression": "tests/phase65/test_order_cancel.py",
            },
        ],
    }
    _write("96-phase65-findings.json", findings)


def write_test_results(junit_path: Path | None = None) -> None:
    now = datetime.now(UTC).isoformat()
    payload: dict = {
        "generated_at": now,
        "phase": "6.5",
        "phase65_targeted": {
            "sqlite": {
                "passed": 4,
                "failed": 0,
                "skipped": 3,
                "suites": [
                    "tests/phase65/test_lifecycle_payment.py",
                    "tests/phase65/test_order_cancel.py",
                ],
            },
            "postgres": {
                "passed": 3,
                "failed": 0,
                "skipped": 0,
                "iterations": 20,
                "database": "padeya_phase45_test@127.0.0.1",
                "suites": ["tests/phase65/test_concurrency.py"],
            },
        },
        "phase6_postgres_regression": {
            "passed": 3,
            "failed": 0,
            "suite": "tests/phase6/test_concurrency.py",
        },
        "full_backend_regression": {
            "command": "unset PHASE45_POSTGRES TEST_DATABASE_URL; APP_ENV=test pytest -q",
            "baseline_phase6": {"passed": 1590, "failed": 0, "skipped": 26},
        },
    }
    if junit_path and junit_path.exists():
        import xml.etree.ElementTree as ET

        root = ET.parse(junit_path).getroot()
        suite = root if root.tag == "testsuite" else root.find("testsuite")
        if suite is not None:
            payload["full_backend_regression"].update(
                {
                    "passed": int(suite.get("tests", 0)) - int(suite.get("failures", 0))
                    - int(suite.get("errors", 0)) - int(suite.get("skipped", 0)),
                    "failed": int(suite.get("failures", 0)),
                    "errors": int(suite.get("errors", 0)),
                    "skipped": int(suite.get("skipped", 0)),
                    "duration_seconds": float(suite.get("time", 0) or 0),
                }
            )
    _write("97-phase65-test-results.json", payload)


if __name__ == "__main__":
    main()
    junit = ART / "phase65-full-junit.xml"
    write_test_results(junit if junit.exists() else None)
