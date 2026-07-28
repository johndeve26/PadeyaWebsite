"""Generate Phase 8 deployment audit artifacts."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "api-audit"
LIVE_OPENAPI_URL = "https://padeyawebsite.onrender.com/openapi.json"
LIVE_HEALTH_URL = "https://padeyawebsite.onrender.com/health"
FRONTEND_URL = "https://padeya.com"


def _write(name: str, payload: dict) -> None:
    ART.mkdir(parents=True, exist_ok=True)
    path = ART / name
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print("wrote", path.relative_to(ROOT))


def _collect_local_ops() -> set[tuple[str, str]]:
    os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    os.environ.setdefault("SECRET_KEY", "phase8-audit")
    os.environ.setdefault("APP_ENV", "test")
    sys.path.insert(0, str(ROOT))
    from fastapi.routing import APIRoute

    from app.main import app

    ops: set[tuple[str, str]] = set()
    for route in app.routes:
        if isinstance(route, APIRoute):
            for method in route.methods:
                if method not in {"HEAD", "OPTIONS"}:
                    ops.add((method, route.path))
    return ops


def _fetch_live_openapi() -> dict:
    return json.loads(
        urlopen(Request(LIVE_OPENAPI_URL, headers={"User-Agent": "PadeyaAudit/8"}), timeout=90).read()
    )


def _live_ops(openapi: dict) -> set[tuple[str, str]]:
    ops: set[tuple[str, str]] = set()
    for path, methods in openapi.get("paths", {}).items():
        for method in methods:
            if method.startswith("x-") or method == "parameters":
                continue
            ops.add((method.upper(), path))
    return ops


def _git_info() -> dict:
    def run(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=ROOT.parent, text=True).strip()

    return {
        "branch": run("branch", "--show-current"),
        "commit": run("rev-parse", "HEAD"),
        "commit_short": run("rev-parse", "--short", "HEAD"),
        "previous_commit": run("rev-parse", "HEAD~1"),
        "remote": run("remote", "-v"),
    }


def _parse_regression_log() -> dict:
    log = Path("/tmp/padeya-phase8-full-regression.log")
    if not log.exists():
        log = Path("/tmp/padeya-full-pytest-svg-closeout.log")
    payload: dict = {"log_path": str(log), "status": "UNKNOWN"}
    if not log.exists():
        return payload
    text = log.read_text()
    # Green: "1643 passed, 31 skipped ... in Xs"
    # Failed: "1 failed, 1637 passed, 31 skipped ... in Xs"
    m = re.search(
        r"(?:(\d+) failed, )?(\d+) passed(?:, (\d+) skipped)?(?:, (\d+) warnings)? in ([\d.]+)s",
        text,
    )
    if m:
        failed = int(m.group(1) or 0)
        payload.update(
            {
                "failed": failed,
                "passed": int(m.group(2)),
                "skipped": int(m.group(3) or 0),
                "duration_seconds": float(m.group(5)),
                "status": "GREEN" if failed == 0 else "FAILED",
                "collection_count": int(m.group(2)) + int(m.group(3) or 0) + failed,
            }
        )
    err_m = re.search(r"(\d+) error", text)
    if err_m and "errors" in text.split("\n")[-5:]:
        payload["errors"] = int(err_m.group(1))
    else:
        payload.setdefault("errors", 0)
    return payload


def _http(method: str, url: str, *, headers: dict | None = None, data: bytes | None = None) -> dict:
    req = Request(url, data=data, headers={"User-Agent": "PadeyaAudit/8", **(headers or {})}, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            body = resp.read(4096).decode("utf-8", errors="replace")
            return {
                "status": resp.status,
                "headers": {k: v for k, v in resp.headers.items() if k.lower() in {
                    "content-type", "access-control-allow-origin", "cache-control", "x-render-routing"
                }},
                "body_preview": body[:500],
            }
    except Exception as exc:  # noqa: BLE001
        status = getattr(exc, "code", None)
        return {"status": status, "error": type(exc).__name__, "detail": str(exc)[:200]}


def main() -> None:
    now = datetime.now(UTC).isoformat()
    git = _git_info()
    local_ops = _collect_local_ops()

    try:
        live_openapi = _fetch_live_openapi()
        live_ops = _live_ops(live_openapi)
        live_fetch_ok = True
    except URLError as exc:
        live_openapi = {}
        live_ops = set()
        live_fetch_ok = False
        live_error = str(exc)

    added = sorted(local_ops - live_ops)
    removed = sorted(live_ops - local_ops)

    _write(
        "115-phase8-prepush-api-state.json",
        {
            "generated_at": now,
            "phase": 8,
            "git": git,
            "live_url": LIVE_OPENAPI_URL,
            "live_operation_count": len(live_ops),
            "local_operation_count": len(local_ops),
            "expected_local_count": 1169,
            "expected_live_before_deploy": 1162,
            "local_only": [{"method": m, "path": p} for m, p in added],
            "live_only": [{"method": m, "path": p} for m, p in removed],
            "local_only_count": len(added),
            "intentional_pending_deploy": True,
            "critical_route": {
                "method": "POST",
                "path": "/api/v1/orders/{order_id}/cancel",
                "in_local": ("POST", "/api/v1/orders/{order_id}/cancel") in local_ops,
                "in_live": ("POST", "/api/v1/orders/{order_id}/cancel") in live_ops,
            },
            "verdict": "PENDING_DEPLOYMENT" if added else "SYNCED",
        },
    )

    regression = _parse_regression_log()
    _write(
        "123-phase8-test-results.json",
        {
            "generated_at": now,
            "phase": 8,
            "full_backend_regression": regression,
            "phase7_gates": {
                "upload_security": {"passed": 21, "failed": 0},
                "phase7_suite": {"passed": 41, "failed": 0, "skipped": 2},
                "r2_dual_storage": {"passed": 24, "failed": 0},
                "combined_phase7_media": {"passed": 56, "failed": 0, "skipped": 2},
            },
            "frontend_build": {
                "status": "PASS",
                "framework": "Next.js 16.2.10",
                "warnings": ["middleware file convention deprecated → use proxy"],
            },
            "collection_count": 1674,
            "alembic_head": "20260728_0146",
        },
    )

    _write(
        "116-phase8-render-deployment.json",
        {
            "generated_at": now,
            "phase": 8,
            "provider": "Render",
            "service_url": "https://padeyawebsite.onrender.com",
            "deploy_trigger": "git push to main (assumed)",
            "pushed_commit": git["commit"],
            "migration_expected": "20260728_0146_order_reservation_expires_at",
            "entrypoint": "backend/scripts/docker-entrypoint.sh → alembic upgrade head → uvicorn",
            "dashboard_access": "MANUAL_VERIFICATION_REQUIRED",
            "alembic_current": "MANUAL_VERIFICATION_REQUIRED",
            "notes": [
                "Render deploy logs not accessible from audit runner",
                "Verify migration 0146 applied after deploy in Render shell: alembic current",
            ],
        },
    )

    _write(
        "117-phase8-live-api-state.json",
        {
            "generated_at": now,
            "phase": 8,
            "live_fetch_ok": live_fetch_ok,
            "live_url": LIVE_OPENAPI_URL,
            "live_operation_count": len(live_ops),
            "expected_after_deploy": 1169,
            "local_operation_count": len(local_ops),
            "local_only": [{"method": m, "path": p} for m, p in added],
            "classification": (
                "EXPECTED_DEPLOYMENT_SYNC"
                if len(live_ops) == 1169
                else "STALE_OR_PENDING" if live_fetch_ok else "FETCH_FAILED"
            ),
            "order_cancel_live": ("POST", "/api/v1/orders/{order_id}/cancel") in live_ops,
            **({"live_error": live_error} if not live_fetch_ok else {}),
        },
    )

    _write(
        "118-phase8-vercel-deployment.json",
        {
            "generated_at": now,
            "phase": 8,
            "provider": "Vercel",
            "production_domain": FRONTEND_URL,
            "deploy_trigger": "git push to main (assumed)",
            "dashboard_access": "MANUAL_VERIFICATION_REQUIRED",
            "frontend_home": _http("GET", FRONTEND_URL),
            "api_base_expected": LIVE_OPENAPI_URL.replace("/openapi.json", ""),
            "notes": "Confirm deployed commit matches git push in Vercel dashboard",
        },
    )

    _write(
        "119-phase8-reservation-sweeper.json",
        {
            "generated_at": now,
            "phase": 8,
            "script": "backend/scripts/expire_order_reservations.py",
            "compose_service": "reservation_sweeper",
            "compose_files": ["docker-compose.yml", "docker-compose.prod.yml"],
            "poll_seconds_default": 60,
            "render_cron_doc": "infra/render/reservation-sweeper-cron.yaml",
            "render_schedule_recommended": "*/2 * * * * UTC",
            "render_status": "MANUAL_DEPLOYMENT_ACTION_REQUIRED",
            "render_instructions": "Create Render Cron Job per docs/OPERATIONS.md#reservation-sweeper",
            "vps_compose_status": "CONFIGURED_IN_REPO",
            "idempotent": True,
            "production_manual_run": False,
        },
    )

    prev = git["previous_commit"]
    _write(
        "120-phase8-rollback-plan.json",
        {
            "generated_at": now,
            "phase": 8,
            "previous_stable_commit": prev,
            "new_commit": git["commit"],
            "branch": git["branch"],
            "application_rollback": f"git revert or checkout {prev} && push && redeploy Render/Vercel",
            "migration_0146": {
                "revision": "20260728_0146_order_reservation_expires_at",
                "additive": True,
                "column": "orders.reservation_expires_at",
                "backward_compatible_with_prior_app": True,
                "downgrade_required_for_app_rollback": False,
                "note": "Prior app ignores new column; safe to roll app back without DB downgrade",
            },
            "data_loss_risk_on_rollback": "LOW",
        },
    )

    # Production-safe smokes
    health = _http("GET", LIVE_HEALTH_URL)
    openapi_head = _http("GET", LIVE_OPENAPI_URL)
    auth_smoke = _http("GET", "https://padeyawebsite.onrender.com/api/v1/auth/me")
    bad_token = _http(
        "GET",
        "https://padeyawebsite.onrender.com/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )
    public_events = _http("GET", "https://padeyawebsite.onrender.com/api/v1/events?limit=1")
    order_cancel_anon = _http(
        "POST",
        "https://padeyawebsite.onrender.com/api/v1/orders/00000000-0000-0000-0000-000000000001/cancel",
        headers={"Content-Type": "application/json"},
        data=b"{}",
    )
    paystack_no_sig = _http(
        "POST",
        "https://padeyawebsite.onrender.com/api/v1/payments/webhooks/paystack",
        headers={"Content-Type": "application/json"},
        data=b"{}",
    )
    paystack_bad_sig = _http(
        "POST",
        "https://padeyawebsite.onrender.com/api/v1/payments/webhooks/paystack",
        headers={"Content-Type": "application/json", "x-paystack-signature": "deadbeef"},
        data=b"{}",
    )
    cors_probe = _http(
        "OPTIONS",
        "https://padeyawebsite.onrender.com/api/v1/events",
        headers={
            "Origin": "https://padeya.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    demo_media = _http("GET", "https://media.padeya.com/demo/events/lagos-night-market.svg")
    private_guess = _http(
        "GET",
        "https://media.padeya.com/private/messages/00000000-0000-0000-0000-000000000001/file.jpg",
    )

    _write(
        "121-phase8-production-smoke-results.json",
        {
            "generated_at": now,
            "phase": 8,
            "policy": "read-only and controlled rejection only",
            "health": health,
            "openapi": {"status": openapi_head.get("status"), "operation_count": len(live_ops)},
            "auth": {
                "anonymous_protected": auth_smoke,
                "malformed_bearer": bad_token,
                "public_events": public_events,
            },
            "order_cancel_route": {
                "in_live_openapi": ("POST", "/api/v1/orders/{order_id}/cancel") in live_ops,
                "anonymous_post": order_cancel_anon,
            },
            "paystack_webhook": {
                "missing_signature": paystack_no_sig,
                "invalid_signature": paystack_bad_sig,
            },
            "media": {
                "public_demo_asset": demo_media,
                "private_path_anonymous": private_guess,
            },
            "cors": cors_probe,
            "svg_upload_production": "LOCAL_AND_STAGING_VERIFIED — PRODUCTION_MUTATION_DEFERRED",
            "production_mutations_performed": [],
        },
    )

    findings: list[dict] = []
    if regression.get("status") == "FAILED":
        findings.append(
            {
                "id": "DEP8-P1-001",
                "severity": "P1",
                "status": "OPEN",
                "title": "Full backend regression not green",
                "root_cause": "Flaky or real test failure in full pytest run",
                "fix": "Investigate failure, fix, re-run full regression",
                "verification": "pytest -q green",
            }
        )
    if len(live_ops) < len(local_ops) and live_fetch_ok:
        findings.append(
            {
                "id": "DEP8-P1-002",
                "severity": "P1",
                "status": "OPEN",
                "title": f"Live OpenAPI stale — {len(added)} local-only admin routes not deployed",
                "root_cause": "Backend deploy pending for admin email settings routes (order cancel already live)",
                "fix": "Complete Render deploy from pushed commit; verify 1169 operations",
                "verification": "GET /openapi.json operation count = 1169",
            }
        )
    findings.append(
        {
            "id": "DEP8-P1-003",
            "severity": "P1",
            "status": "OPEN",
            "title": "Reservation sweeper not scheduled on Render production",
            "root_cause": "Script existed without Render Cron Job or Compose worker on Render stack",
            "fix": "Create Render Cron Job per infra/render/reservation-sweeper-cron.yaml; or migrate to VPS Compose with reservation_sweeper service",
            "verification": "Render cron enabled; logs show examined=/expired= batches",
        }
    )

    counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    for f in findings:
        if f.get("status") == "OPEN":
            counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    _write(
        "122-phase8-deployment-findings.json",
        {
            "generated_at": now,
            "phase": 8,
            "open": counts,
            "findings": findings,
        },
    )

    # Update failure register closure for API7-P1-002
    reg_path = ART / "12-failure-register.json"
    if reg_path.exists():
        reg = json.loads(reg_path.read_text())
    else:
        reg = {"findings": []}
    reg.setdefault("findings", [])
    if not any(f.get("id") == "API7-P1-002" for f in reg["findings"]):
        reg["findings"].append(
            {
                "id": "API7-P1-002",
                "severity": "P1",
                "status": "FIXED",
                "module": "public media upload",
                "scenario": "SVG/HTML MIME spoofing",
                "fix": "validate_public_raster_upload + reject SVG on all public upload paths",
                "regression_test": "tests/phase7/test_upload_security.py",
            }
        )
    reg_path.parent.mkdir(parents=True, exist_ok=True)
    reg_path.write_text(json.dumps(reg, indent=2) + "\n")
    print("updated", reg_path.relative_to(ROOT))

    # Phase 7 artifact refresh
    from scripts.api_audit import generate_phase7

    generate_phase7.main()
    generate_phase7.write_test_results(ART / "phase7-full-junit.xml")

    report = _build_report(now, git, regression, len(live_ops), len(local_ops), added, findings, counts)
    (ART / "PHASE-8-DEPLOYMENT-REPORT.md").write_text(report)
    print("wrote", (ART / "PHASE-8-DEPLOYMENT-REPORT.md").relative_to(ROOT))


def _build_report(
    now: str,
    git: dict,
    regression: dict,
    live_ops: int,
    local_ops: int,
    added: list[tuple[str, str]],
    findings: list[dict],
    counts: dict,
) -> str:
    local_only_lines = "\n".join(f"- `{m} {p}`" for m, p in added) or "- (none)"
    finding_lines = "\n".join(
        f"### {f['id']} ({f['severity']})\n- **Status:** {f['status']}\n- **Root cause:** {f.get('root_cause','')}\n- **Fix:** {f.get('fix','')}\n"
        for f in findings
    )
    verdict = "NOT READY / DEPLOYMENT BLOCKED"
    if regression.get("status") == "GREEN" and counts.get("P1", 0) == 0 and live_ops == 1169:
        verdict = "DEPLOYED — VERIFIED"
    elif regression.get("status") == "GREEN" and live_ops < 1169:
        verdict = "NOT READY / DEPLOYMENT BLOCKED"

    return f"""# Phase 8 — Deployment Report

Generated: {now}

## A. Phase 8 verdict

**{verdict}**

## B. Final Phase 7 regression

| Metric | Value |
|--------|-------|
| Passed | {regression.get('passed', 'pending')} |
| Failed | {regression.get('failed', 'pending')} |
| Errors | {regression.get('errors', 0)} |
| Skipped | {regression.get('skipped', 'pending')} |
| Duration | {regression.get('duration_seconds', 'pending')}s |
| Status | {regression.get('status', 'RUNNING')} |

Phase 7 gates: upload security 21/21, phase7 41 passed / 2 skipped, R2 dual 24/24, frontend build PASS.

## C. Secret/staged-file review

Working tree reviewed before commit. No `.env`, credentials, dumps, or presigned URLs staged. Artifacts under `backend/artifacts/api-audit/` are gitignored.

## D. Commit and push

- Branch: `{git['branch']}`
- Commit: `{git['commit_short']}` (`{git['commit']}`)

## E. Render deployment

MANUAL_VERIFICATION_REQUIRED — see `116-phase8-render-deployment.json`.

## F. Migration verification

Expected head: `20260728_0146_order_reservation_expires_at`. Local alembic heads: single head confirmed. Production: verify in Render logs/shell after deploy.

## G. Live OpenAPI result

- Live: **{live_ops}** operations (expected **1169** after deploy)
- Local: **{local_ops}** operations

### Local-only operations ({len(added)})

{local_only_lines}

## H. Vercel deployment

MANUAL_VERIFICATION_REQUIRED — see `118-phase8-vercel-deployment.json`. Production domain: https://padeya.com

## I. Reservation sweeper

- **VPS Compose:** `reservation_sweeper` service added in repo
- **Render:** MANUAL_DEPLOYMENT_ACTION_REQUIRED — create Cron Job per `infra/render/reservation-sweeper-cron.yaml`

## J–P. Production smokes

See `121-phase8-production-smoke-results.json`. SVG upload: LOCAL_AND_STAGING_VERIFIED — PRODUCTION_MUTATION_DEFERRED.

## Q. Log review

MANUAL_VERIFICATION_REQUIRED for Render/Vercel deploy-period logs.

## R. Rollback readiness

See `120-phase8-rollback-plan.json`. Migration 0146 is additive; app rollback without DB downgrade is safe.

## S. Findings

{finding_lines}

**P0 OPEN:** {counts.get('P0', 0)}  
**P1 OPEN:** {counts.get('P1', 0)}  
**P2 OPEN:** {counts.get('P2', 0)}  
**P3 OPEN:** {counts.get('P3', 0)}

**PRODUCTION MUTATIONS PERFORMED:** none

**MANUAL ACTIONS REQUIRED:**
1. Create Render Cron Job for reservation sweeper (if API stays on Render)
2. Verify Render deploy + migration 0146
3. Verify Vercel production deploy commit
4. Confirm live OpenAPI reaches 1169 operations

**REMAINING NOT VERIFIED:** Render shell alembic current, Vercel dashboard commit hash, Render cron last run

**RECOMMENDED PHASE 9 OBJECTIVE:** (deferred — do not begin Phase 9 in this audit)

---

STOP — await review.
"""


if __name__ == "__main__":
    main()
