"""Generate Phase 2 API audit artifacts from junit + Phase 1 baseline.

Usage:
    cd backend && python3 scripts/api_audit/generate_phase2.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = BACKEND_ROOT / "artifacts" / "api-audit"
BASELINE_PATH = ARTIFACTS / "13-baseline-test-results.json"
PHASE2_JUNIT = ARTIFACTS / "phase2-junit.xml"
PHASE2_RESULTS = ARTIFACTS / "18-phase2-full-test-results.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_key(row: dict) -> str:
    cls = row.get("classname") or ""
    name = row.get("name") or ""
    mod = cls.split(".")[-1] if cls else cls
    return f"{mod}::{name}"


def main() -> int:
  sys.path.insert(0, str(BACKEND_ROOT))
  from scripts.api_audit.parse_pytest_junit import main as parse_junit

  if not PHASE2_JUNIT.is_file():
    print(f"Missing {PHASE2_JUNIT}", file=sys.stderr)
    return 1
  parse_junit([None, str(PHASE2_JUNIT), str(PHASE2_RESULTS)])

  baseline = load_json(BASELINE_PATH)
  phase2 = load_json(PHASE2_RESULTS)

  baseline_by = {test_key(r): r for r in baseline["results"]}
  phase2_by = {test_key(r): r for r in phase2["results"]}

  clusters: dict[str, dict] = {
      "RC-ACCESS_TOKEN": {
          "classification": "TEST_ISOLATION_BUG",
          "root_cause": "Registration auto-derives username from full_name; duplicate names caused 409 and login KeyError on access_token.",
          "fix": "tests/helpers/auth.py register_json(); updated registration helpers in affected modules.",
          "finding_ids": [],
      },
      "RC-AMBASSADOR_NAMEERROR": {
          "classification": "PRODUCT_BUG",
          "root_cause": "Missing resolve_campaign_commission_input import in ambassadors/host_service.py.",
          "fix": "Import from app.promos.commission in host_service.py.",
          "finding_ids": [],
      },
      "RC-USER_IMPORT": {
          "classification": "IMPORT/REFACTOR_DRIFT",
          "root_cause": "Stale User import from app.auth.models and AmbassadorCampaign from wrong module in referral_tracking.py.",
          "fix": "Correct imports in ambassadors/referral_tracking.py.",
          "finding_ids": [],
      },
      "RC-NORESULTFOUND": {
          "classification": "DUPLICATE_ROOT_CAUSE",
          "root_cause": "Downstream of failed registration (user row never created).",
          "fix": "Resolved by RC-ACCESS_TOKEN fixes.",
          "finding_ids": [],
      },
      "RC-ANALYTICS_404": {
          "classification": "STALE_TEST_EXPECTATION",
          "root_cause": "Host event analytics uses 404 anti-enumeration for unrelated actors; export checked permission before event access.",
          "fix": "Test expects 404; reorder export_host_event_analytics_csv permission checks.",
          "finding_ids": [],
      },
      "RC-MAINTENANCE_409": {
          "classification": "TEST_ISOLATION_BUG",
          "root_cause": "Username collision in maintenance tests.",
          "fix": "register_json in test_maintenance.py.",
          "finding_ids": [],
      },
      "RC-HOST_TEAM": {
          "classification": "TEST_ISOLATION_BUG",
          "root_cause": "host_team_ops_permissions _register used duplicate full_name.",
          "fix": "register_json in test_host_team_ops_permissions.py.",
          "finding_ids": [],
      },
      "RC-GUEST_CHECKOUT": {
          "classification": "PRODUCT_BUG",
          "root_cause": "Guest ticket checkout incorrectly auto-provisioned merch buyer accounts.",
          "fix": "Gate provision_guest_merch_buyer_if_needed with order_has_merch_or_bundle.",
          "finding_ids": [],
      },
      "RC-PASSPORT": {
          "classification": "STALE_TEST_EXPECTATION",
          "root_cause": "Passport creation timing and private visibility behavior changed.",
          "fix": "Updated test_passport expectations.",
          "finding_ids": [],
      },
      "RC-FAN_CONNECT": {
          "classification": "STALE_TEST_EXPECTATION",
          "root_cause": "fan_connect.request notifications live on /api/v1/notifications not messages feed.",
          "fix": "Updated fan_connect notification test.",
          "finding_ids": [],
      },
      "RC-NOTIFICATIONS": {
          "classification": "STALE_TEST_EXPECTATION",
          "root_cause": "Email template keys and wired notification kinds drift.",
          "fix": "admin_message_report template; WIRED_NOTIFY_KINDS updates.",
          "finding_ids": [],
      },
      "RC-PUSH_OUTBOX": {
          "classification": "TEST_FIXTURE_BUG",
          "root_cause": "Push drain test missing subscription registration.",
          "fix": "Register push subscription before drain in test.",
          "finding_ids": [],
      },
      "RC-LIFECYCLE": {
          "classification": "STALE_TEST_EXPECTATION",
          "root_cause": "Deactivate/restore requires reason; suspended users can login for appeals.",
          "fix": "Updated lifecycle deactivate test.",
          "finding_ids": [],
      },
      "RC-HOST_AS_FAN": {
          "classification": "PRODUCT_BUG",
          "root_cause": "Missing HTTPException import in tickets/router.py.",
          "fix": "Add HTTPException import.",
          "finding_ids": [],
      },
      "RC-IMPERSONATION": {
          "classification": "STALE_TEST_EXPECTATION",
          "root_cause": "Impersonation RBAC/audit expectations and logout during impersonation.",
          "fix": "Allow POST /auth/logout during impersonation; test updates for display_name and profile patch 403.",
          "finding_ids": [],
      },
      "RC-PLACEMENTS_CACHE": {
          "classification": "PRODUCT_BUG",
          "root_cause": "Placement set archive did not invalidate public picks/list caches.",
          "fix": "invalidate_event_caches in placements update_set_status.",
          "finding_ids": [],
      },
      "RC-P1-001": {
          "classification": "PRODUCT_BUG",
          "root_cause": "sponsor-deals-api.ts double /api/v1 prefix on apiRequest paths.",
          "fix": "Strip /api/v1 from paths; audit test asserts single prefix.",
          "finding_ids": ["API-P1-001"],
      },
      "RC-PUSH_SPONSOR": {
          "classification": "PRODUCT_BUG",
          "root_cause": "Sponsor deal/deliverable notification kinds lacked push template aliases.",
          "fix": "Add push templates and KIND_ALIASES in push/templates.py.",
          "finding_ids": [],
      },
      "RC-HOSTS_EVENTS_LIST": {
          "classification": "TEST_ISOLATION_BUG",
          "root_cause": "Public events list capped at 100; full-suite pollution hid approved event.",
          "fix": "Query with q=Needs Approval in test_admin_approval_rejection.",
          "finding_ids": [],
      },
  }

  # Map baseline failures to clusters by module/scenario heuristics
  module_cluster = {
      "test_impersonation": "RC-IMPERSONATION",
      "test_appeals": "RC-ACCESS_TOKEN",
      "test_taxonomy": "RC-ACCESS_TOKEN",
      "test_messaging": "RC-ACCESS_TOKEN",
      "test_placements": "RC-PLACEMENTS_CACHE",
      "test_event_studio_lifecycle": "RC-ACCESS_TOKEN",
      "test_event_subresource_lifecycle": "RC-ACCESS_TOKEN",
      "test_hosts_events": "RC-ACCESS_TOKEN",
      "test_event_calendar": "RC-ACCESS_TOKEN",
      "test_event_nearby": "RC-ACCESS_TOKEN",
      "test_event_location_privacy": "RC-ACCESS_TOKEN",
      "test_ambassador_fraud": "RC-USER_IMPORT",
      "test_ambassador_phase17": "RC-AMBASSADOR_NAMEERROR",
      "test_ambassadors_api_v2": "RC-AMBASSADOR_NAMEERROR",
      "test_open_ambassadors": "RC-AMBASSADOR_NAMEERROR",
      "test_promos": "RC-AMBASSADOR_NAMEERROR",
      "test_ambassador_payment_integration": "RC-AMBASSADOR_NAMEERROR",
      "test_guest_checkout": "RC-GUEST_CHECKOUT",
      "test_passport": "RC-PASSPORT",
      "test_fan_connect": "RC-FAN_CONNECT",
      "test_analytics_event_detail": "RC-ANALYTICS_404",
      "test_analytics_requirements": "RC-ANALYTICS_404",
      "test_host_team_ops_permissions": "RC-HOST_TEAM",
      "test_maintenance": "RC-MAINTENANCE_409",
      "test_host_as_fan": "RC-HOST_AS_FAN",
      "test_notification_triggers": "RC-NOTIFICATIONS",
      "test_notification_push_coverage": "RC-PUSH_SPONSOR",
      "test_notification_push_integration": "RC-PUSH_OUTBOX",
      "test_missing_lifecycle": "RC-LIFECYCLE",
  }

  register = load_json(ARTIFACTS / "12-failure-register.json")
  finding_map: dict[str, str] = {}
  for f in register["findings"]:
      fid = f["id"]
      if fid == "API-P1-001":
          finding_map[fid] = "RC-P1-001"
          continue
      scenario = f.get("scenario") or ""
      mod_path = f.get("path") or ""
      mod = mod_path.replace("tests.", "")
      cluster = module_cluster.get(mod, "RC-ACCESS_TOKEN")
      if "NoResultFound" in (f.get("actual") or ""):
          cluster = "RC-NORESULTFOUND"
      if "access_token" in (f.get("actual") or ""):
          cluster = "RC-ACCESS_TOKEN"
      finding_map[fid] = cluster
      clusters[cluster]["finding_ids"].append(fid)

  # Diff baseline vs phase2
  diff_rows = []
  for key, brow in baseline_by.items():
      p2 = phase2_by.get(key)
      if p2 is None:
          diff_rows.append(
              {
                  "test": key,
                  "baseline": brow["status"],
                  "phase2": "MISSING",
                  "delta": "removed_or_renamed",
              }
          )
          continue
      if brow["status"] != "PASS" and p2["status"] == "PASS":
          diff_rows.append(
              {
                  "test": key,
                  "baseline": brow["status"],
                  "phase2": p2["status"],
                  "delta": "fixed",
              }
          )
      elif brow["status"] == "PASS" and p2["status"] != "PASS":
          diff_rows.append(
              {
                  "test": key,
                  "baseline": brow["status"],
                  "phase2": p2["status"],
                  "delta": "regression",
              }
          )
      elif brow["status"] != "PASS" and p2["status"] != "PASS":
          diff_rows.append(
              {
                  "test": key,
                  "baseline": brow["status"],
                  "phase2": p2["status"],
                  "delta": "still_failing",
              }
          )

  for key, p2 in phase2_by.items():
      if key not in baseline_by:
          diff_rows.append(
              {
                  "test": key,
                  "baseline": "MISSING",
                  "phase2": p2["status"],
                  "delta": "new_test",
              }
          )

  fixed = sum(1 for r in diff_rows if r["delta"] == "fixed")
  regressions = sum(1 for r in diff_rows if r["delta"] == "regression")
  still = sum(1 for r in diff_rows if r["delta"] == "still_failing")
  new_tests = sum(1 for r in diff_rows if r["delta"] == "new_test")

  cluster_payload = {
      "generated_at": datetime.now(UTC).isoformat(),
      "baseline_failed": baseline["failed"],
      "phase2_failed": phase2["failed"],
      "clusters": [
          {
              "id": cid,
              **{k: v for k, v in meta.items() if k != "finding_ids"},
              "finding_count": len(meta["finding_ids"]),
              "finding_ids": sorted(meta["finding_ids"]),
          }
          for cid, meta in sorted(clusters.items())
      ],
  }

  fix_summary = {
      "generated_at": datetime.now(UTC).isoformat(),
      "api_p1_001": {
          "status": "FIXED",
          "files": [
              "frontend/src/lib/sponsor-deals-api.ts",
              "frontend/src/lib/sponsor-deals-api.audit.test.ts",
          ],
      },
      "product_fixes": [
          "backend/app/ambassadors/host_service.py",
          "backend/app/ambassadors/referral_tracking.py",
          "backend/app/tickets/router.py",
          "backend/app/payments/checkout_account.py",
          "backend/app/admin/impersonation_guards.py",
          "backend/app/placements/service.py",
          "backend/app/analytics/service.py",
          "backend/app/push/templates.py",
      ],
      "test_fixes": [
          "backend/tests/helpers/auth.py",
          "backend/tests/test_impersonation.py",
          "backend/tests/test_appeals.py",
          "backend/tests/test_taxonomy.py",
          "backend/tests/test_messaging.py",
          "backend/tests/test_placements.py",
          "backend/tests/test_event_studio_lifecycle.py",
          "backend/tests/test_event_subresource_lifecycle.py",
          "backend/tests/test_hosts_events.py",
          "backend/tests/test_event_calendar.py",
          "backend/tests/test_event_nearby.py",
          "backend/tests/test_event_location_privacy.py",
          "backend/tests/test_maintenance.py",
          "backend/tests/test_host_team_ops_permissions.py",
          "backend/tests/test_analytics_event_detail.py",
          "backend/tests/test_analytics_requirements.py",
          "backend/tests/test_ambassador_fraud.py",
          "backend/tests/test_ambassador_phase17.py",
          "plus misc notification/passport/fan_connect/lifecycle tests",
      ],
      "baseline_failures_fixed": fixed,
      "regressions": regressions,
      "still_failing": still,
      "new_tests": new_tests,
  }

  baseline_diff = {
      "generated_at": datetime.now(UTC).isoformat(),
      "baseline": {
          "collected": baseline["collected"],
          "passed": baseline["passed"],
          "failed": baseline["failed"],
          "errors": baseline["errors"],
      },
      "phase2": {
          "collected": phase2["collected"],
          "passed": phase2["passed"],
          "failed": phase2["failed"],
          "errors": phase2["errors"],
      },
      "summary": {
          "fixed": fixed,
          "regressions": regressions,
          "still_failing": still,
          "new_tests": new_tests,
      },
      "diff": diff_rows,
  }

  (ARTIFACTS / "17-phase2-root-cause-clusters.json").write_text(
      json.dumps(cluster_payload, indent=2) + "\n", encoding="utf-8"
    )
  (ARTIFACTS / "19-phase2-fix-summary.json").write_text(
      json.dumps(fix_summary, indent=2) + "\n", encoding="utf-8"
    )
  (ARTIFACTS / "20-phase2-baseline-diff.json").write_text(
      json.dumps(baseline_diff, indent=2) + "\n", encoding="utf-8"
    )

  # Update failure register closure
  for f in register["findings"]:
      cid = finding_map.get(f["id"], "UNKNOWN")
      f["root_cause"] = cid
      f["cluster_id"] = cid
      if f["id"] == "API-P1-001":
          f["status"] = "FIXED" if phase2["failed"] == 0 else "FIXED_PENDING_BASELINE"
          f["fix"] = "Removed duplicate /api/v1 prefix from sponsor-deals-api.ts paths."
      elif phase2["failed"] == 0:
          f["status"] = "CLOSED"
          f["fix"] = clusters.get(cid, {}).get("fix", "See cluster")
      else:
          p2_status = None
          scenario = f.get("scenario")
          for row in phase2["results"]:
              if row.get("name") == scenario:
                  p2_status = row.get("status")
                  break
          if p2_status == "PASS":
              f["status"] = "CLOSED"
              f["fix"] = clusters.get(cid, {}).get("fix", "See cluster")
          else:
              f["status"] = "OPEN"

  (ARTIFACTS / "12-failure-register.json").write_text(
      json.dumps(register, indent=2) + "\n", encoding="utf-8"
    )

  print(
      f"Phase2: {phase2['passed']} passed, {phase2['failed']} failed, "
      f"{phase2['errors']} errors / {phase2['collected']} collected"
  )
  print(f"Fixed baseline failures: {fixed}, regressions: {regressions}, still: {still}")
  return 0 if phase2["failed"] == 0 and phase2["errors"] == 0 else 1


if __name__ == "__main__":
  raise SystemExit(main())
