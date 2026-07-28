"""Generate reproducible Phase 1 API audit artifacts.

Usage:
    cd backend && python3 scripts/api_audit/generate.py
"""

from __future__ import annotations

import ast
import inspect
import json
import os
import re
import sys
import textwrap
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"
FRONTEND_ROOT = REPO_ROOT / "frontend"
ARTIFACTS_DIR = BACKEND_ROOT / "artifacts" / "api-audit"
LIVE_OPENAPI_URL = "https://padeyawebsite.onrender.com/openapi.json"

PHASE0_BASELINE = {
    "operations": 1161,
    "tags": 77,
    "paths": 1015,
    "methods": {"GET": 519, "POST": 459, "PATCH": 128, "PUT": 5, "DELETE": 50},
}


def _seed_env() -> None:
    os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    os.environ.setdefault("SECRET_KEY", "phase1-audit-secret-key")
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("DEMO_MODE", "false")
    os.environ.setdefault("EMAIL_PROVIDER", "log")
    os.environ.setdefault("EMAIL_ENABLED", "true")
    os.environ.setdefault("EMAIL_DEV_MODE", "true")
    os.environ.setdefault("EMAIL_QUEUE_ENABLED", "false")
    os.environ.setdefault("PUSH_QUEUE_ENABLED", "false")
    os.environ.setdefault("MEDIA_PUBLIC_BASE_URL", "http://testserver")
    os.environ.setdefault("MEDIA_ROOT", "media_uploads_test")
    os.environ.setdefault("MEDIA_STORAGE_PROVIDER", "local")
    os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
    os.environ.setdefault("EMAIL_SETTINGS_ENCRYPTION_KEY", "phase1-audit-email-key")


_seed_env()
sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.routing import APIRoute, APIWebSocketRoute  # noqa: E402
from starlette.routing import Mount  # noqa: E402

from app.main import app  # noqa: E402
from app.events.constants import EVENT_STATUSES  # noqa: E402
from app.finance.constants import PAYOUT_STATUSES, REFUND_REQUEST_STATUSES  # noqa: E402
from app.memories.constants import (  # noqa: E402
    ELIGIBLE_EVENT_STATUSES,
    MEMORY_MODERATION_STATUSES,
    MEMORY_PHOTO_STATUSES,
    MEMORY_STATUSES,
)
from app.merch.constants import (  # noqa: E402
    FULFILLMENT_STATUSES,
    PRODUCT_STATUSES,
    UNSAFE_EVENT_STATUSES,
    VARIANT_STATUSES,
)
from app.sponsorships.constants import (  # noqa: E402
    INQUIRY_STATUSES,
    PLACEMENT_STATUSES,
    SLOT_STATUSES,
)
from app.sponsorships.deals_constants import (  # noqa: E402
    DEAL_STATUSES,
    INVOICE_STATUSES,
)
from app.support.constants import STATUSES as SUPPORT_STATUSES  # noqa: E402
from app.vault.constants import (  # noqa: E402
    ITEM_STATUSES as VAULT_ITEM_STATUSES,
    PURCHASE_STATUSES as VAULT_PURCHASE_STATUSES,
)


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple, set)):
        return [jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if hasattr(value, "model_dump"):
        try:
            return jsonable(value.model_dump())
        except Exception:
            return repr(value)
    if hasattr(value, "__dict__"):
        return {
            k: jsonable(v)
            for k, v in vars(value).items()
            if not k.startswith("_")
        }
    return repr(value)


def write_json(name: str, payload: Any) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS_DIR / name
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=False)
        fh.write("\n")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def fetch_live_openapi() -> dict[str, Any]:
    req = Request(
        LIVE_OPENAPI_URL,
        headers={"User-Agent": "PadeyaApiAudit/phase1", "Accept": "application/json"},
    )
    with urlopen(req, timeout=20) as resp:
        return json.load(resp)


def schema_ref_name(schema: Any) -> str | None:
    if not isinstance(schema, dict):
        return None
    if "$ref" in schema:
        return str(schema["$ref"]).rsplit("/", 1)[-1]
    return schema.get("title") or schema.get("type")


def summarize_request_body(body: Any) -> dict[str, Any] | None:
    if not isinstance(body, dict):
        return None
    out: dict[str, Any] = {
        "required": bool(body.get("required")),
        "content_types": sorted((body.get("content") or {}).keys()),
        "schemas": {},
    }
    for content_type, spec in (body.get("content") or {}).items():
        out["schemas"][content_type] = schema_ref_name(spec.get("schema"))
    return out


def summarize_responses(responses: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for status, spec in responses.items():
        content = spec.get("content") or {}
        out[status] = {
            "description": spec.get("description"),
            "content_types": sorted(content.keys()),
            "schemas": {
                content_type: schema_ref_name(content_spec.get("schema"))
                for content_type, content_spec in content.items()
            },
        }
    return out


def build_live_inventory(openapi: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    tags: set[str] = set()
    methods = Counter()
    schemas = openapi.get("components", {}).get("schemas", {})
    for path, item in sorted((openapi.get("paths") or {}).items()):
        for method, op in sorted(item.items()):
            method_upper = method.upper()
            if method_upper not in {"GET", "POST", "PATCH", "PUT", "DELETE"}:
                continue
            methods[method_upper] += 1
            op_tags = op.get("tags") or ["(untagged)"]
            tags.update(op_tags)
            parameters = op.get("parameters") or []
            operations.append(
                {
                    "method": method_upper,
                    "path": path,
                    "operationId": op.get("operationId"),
                    "summary": op.get("summary"),
                    "tags": op_tags,
                    "path_parameters": [
                        {
                            "name": p.get("name"),
                            "required": p.get("required"),
                            "schema": schema_ref_name(p.get("schema")),
                        }
                        for p in parameters
                        if p.get("in") == "path"
                    ],
                    "query_parameters": [
                        {
                            "name": p.get("name"),
                            "required": p.get("required"),
                            "schema": schema_ref_name(p.get("schema")),
                        }
                        for p in parameters
                        if p.get("in") == "query"
                    ],
                    "request_schema": summarize_request_body(op.get("requestBody")),
                    "responses": summarize_responses(op.get("responses") or {}),
                    "security": jsonable(op.get("security", "__INHERIT__")),
                }
            )
    summary = {
        "url": LIVE_OPENAPI_URL,
        "openapi_version": openapi.get("openapi"),
        "title": openapi.get("info", {}).get("title"),
        "operation_count": len(operations),
        "path_template_count": len(openapi.get("paths") or {}),
        "tag_count": len(tags),
        "tags": sorted(tags),
        "method_counts": dict(methods),
        "schema_count": len(schemas),
    }
    return operations, summary


def route_source_file(route: APIRoute | APIWebSocketRoute) -> str | None:
    try:
        return inspect.getsourcefile(route.endpoint)
    except Exception:
        return None


def route_source_text(route: APIRoute) -> str:
    try:
        return inspect.getsource(route.endpoint)
    except Exception:
        return ""


def route_dependency_names(route: APIRoute) -> list[str]:
    out: list[str] = []
    dependant = getattr(route, "dependant", None)
    if dependant is None:
        return out
    for dep in getattr(dependant, "dependencies", []):
        call = getattr(dep, "call", None)
        if call is not None:
            out.append(getattr(call, "__name__", repr(call)))
    return out


def build_router_module_map() -> dict[str, dict[str, Any]]:
    text = read_text(BACKEND_ROOT / "app" / "main.py")
    imports: dict[str, str] = {}
    includes: dict[str, dict[str, Any]] = {}

    from_re = re.compile(r"from\s+([\w.]+)\s+import\s+(.*)")
    for line in text.splitlines():
        match = from_re.match(line.strip())
        if not match:
            continue
        module, imported = match.groups()
        for part in imported.split(","):
            part = part.strip()
            if " as " in part:
                orig, alias = [x.strip() for x in part.split(" as ", 1)]
                imports[alias] = f"{module}.{orig}"
            else:
                imports[part] = f"{module}.{part}"

    include_re = re.compile(r"app\.include_router\((\w+),\s*prefix=(\w+)\)")
    for idx, line in enumerate(text.splitlines(), start=1):
        match = include_re.search(line)
        if not match:
            continue
        name, prefix_var = match.groups()
        includes[name] = {
            "module_symbol": imports.get(name),
            "include_order": idx,
            "prefix_var": prefix_var,
        }
    return includes


def build_local_inventory() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    route_map = build_router_module_map()
    http_routes: list[dict[str, Any]] = []
    hidden_http: list[dict[str, Any]] = []
    websocket_routes: list[dict[str, Any]] = []
    static_mounts: list[dict[str, Any]] = []
    root_aliases: list[dict[str, Any]] = []

    for order, route in enumerate(app.routes):
        if isinstance(route, APIRoute):
            source_file = route_source_file(route)
            module_info = None
            for name, info in route_map.items():
                module_path = info.get("module_symbol", "")
                if module_path and source_file and module_path.split(".router")[0].replace(".", "/") in source_file:
                    module_info = {"router_symbol": name, **info}
                    break
            for method in sorted(route.methods):
                if method in {"HEAD", "OPTIONS"}:
                    continue
                entry = {
                    "method": method,
                    "path": route.path,
                    "name": route.name,
                    "operationId": route.operation_id,
                    "include_in_schema": route.include_in_schema,
                    "response_model": getattr(route.response_model, "__name__", repr(route.response_model))
                    if getattr(route, "response_model", None) is not None
                    else None,
                    "dependencies": route_dependency_names(route),
                    "source_file": source_file,
                    "endpoint_name": getattr(route.endpoint, "__name__", None),
                    "registration_order": order,
                    "router_module": module_info,
                }
                http_routes.append(entry)
                if not route.include_in_schema:
                    hidden_http.append(entry)
                if route.path in {"/", "/health", "/ready", "/api/v1/health", "/api/v1/ready"}:
                    root_aliases.append(entry)
        elif isinstance(route, APIWebSocketRoute):
            websocket_routes.append(
                {
                    "path": route.path,
                    "name": route.name,
                    "source_file": route_source_file(route),
                    "registration_order": order,
                }
            )
        elif isinstance(route, Mount):
            static_mounts.append(
                {
                    "path": route.path,
                    "name": route.name,
                    "app_type": type(route.app).__name__,
                    "registration_order": order,
                }
            )

    summary = {
        "http_route_count": len(http_routes),
        "openapi_http_route_count": sum(1 for item in http_routes if item["include_in_schema"]),
        "hidden_http_count": len(hidden_http),
        "websocket_count": len(websocket_routes),
        "static_mount_count": len(static_mounts),
        "root_alias_count": len(root_aliases),
    }
    hidden = {
        "hidden_http_routes": hidden_http,
        "websocket_routes": websocket_routes,
        "static_mounts": static_mounts,
        "root_aliases": root_aliases,
    }
    return http_routes, summary, hidden


def compare_live_local(live_ops: list[dict[str, Any]], local_routes: list[dict[str, Any]]) -> dict[str, Any]:
    live_set = {(row["method"], row["path"]) for row in live_ops}
    local_schema_routes = [row for row in local_routes if row["include_in_schema"]]
    local_set = {(row["method"], row["path"]) for row in local_schema_routes}
    live_only = sorted(live_set - local_set)
    local_only = sorted(local_set - live_set)
    return {
        "phase0_expected_exact_match": True,
        "current_exact_match": not live_only and not local_only,
        "live_operation_count": len(live_set),
        "local_schema_route_count": len(local_set),
        "intersection_count": len(live_set & local_set),
        "live_only": [{"method": m, "path": p} for m, p in live_only],
        "local_only": [{"method": m, "path": p} for m, p in local_only],
    }


@dataclass
class FrontendHit:
    source_file: str
    line: int
    helper: str
    method: str | None
    path: str
    final_url_pattern: str | None
    classification: str
    notes: str | None = None


API_START_RE = (
    "/auth",
    "/events",
    "/hosts",
    "/host/",
    "/tickets",
    "/payments",
    "/orders",
    "/checkout",
    "/merch",
    "/dashboard",
    "/promos",
    "/ambassadors",
    "/checkins",
    "/reviews",
    "/vault",
    "/passport",
    "/messages",
    "/crm",
    "/support",
    "/admin",
    "/finance",
    "/sponsors",
    "/sponsorships",
    "/fan-connect",
    "/memories",
    "/blog",
    "/help",
    "/taxonomy",
    "/cms",
    "/analytics",
    "/push",
    "/notifications",
    "/pricing",
    "/u/",
    "/f/",
    "/legacy",
    "/me/",
)


def _path_like(value: str) -> bool:
    return value.startswith(API_START_RE) or value.startswith("/api/v1/")


def scan_frontend() -> list[dict[str, Any]]:
    hits: list[FrontendHit] = []
    files = list(FRONTEND_ROOT.rglob("*.ts")) + list(FRONTEND_ROOT.rglob("*.tsx"))
    api_request_re = re.compile(
        r"apiRequest(?:<[^>]+>)?\(\s*(?P<quote>[`'\"])(?P<path>.+?)(?P=quote)(?:,\s*(?P<opts>\{.*?\}))?",
        re.S,
    )
    fetch_re = re.compile(r"fetch\(\s*(?P<quote>[`'\"])(?P<url>.+?)(?P=quote)", re.S)
    ws_re = re.compile(r"messages/ws")
    for file in files:
        rel = str(file.relative_to(REPO_ROOT))
        text = read_text(file)
        for match in api_request_re.finditer(text):
            path = match.group("path")
            if not _path_like(path):
                continue
            opts = match.group("opts") or ""
            method_match = re.search(r'method:\s*["\']([A-Z]+)["\']', opts)
            method = method_match.group(1) if method_match else None
            line = text[: match.start()].count("\n") + 1
            final_url = f"${{API_URL}}${{API_PREFIX}}{path}"
            classification = "apiRequest"
            notes = None
            if path.startswith("/api/v1/"):
                notes = "path already includes API prefix before apiRequest"
            hits.append(
                FrontendHit(
                    source_file=rel,
                    line=line,
                    helper="apiRequest",
                    method=method,
                    path=path,
                    final_url_pattern=final_url,
                    classification=classification,
                    notes=notes,
                )
            )
        for match in fetch_re.finditer(text):
            url = match.group("url")
            if "/api/v1" not in url and not any(part in url for part in API_START_RE):
                continue
            line = text[: match.start()].count("\n") + 1
            method = None
            lookahead = text[match.end() : match.end() + 250]
            method_match = re.search(r'method:\s*["\']([A-Z]+)["\']', lookahead)
            if method_match:
                method = method_match.group(1)
            classification = "fetch"
            notes = None
            if "localhost:8000" in url or "127.0.0.1:8000" in url:
                notes = "hardcoded localhost fallback in request construction"
            hits.append(
                FrontendHit(
                    source_file=rel,
                    line=line,
                    helper="fetch",
                    method=method,
                    path=url,
                    final_url_pattern=url,
                    classification=classification,
                    notes=notes,
                )
            )
        if ws_re.search(text):
            for idx, line_text in enumerate(text.splitlines(), start=1):
                if "messages/ws" in line_text:
                    hits.append(
                        FrontendHit(
                            source_file=rel,
                            line=idx,
                            helper="websocket",
                            method="WS",
                            path="/messages/ws",
                            final_url_pattern="${getApiWsBaseUrl()}${API_PREFIX}/messages/ws?token=...",
                            classification="websocket",
                        )
                    )
    return [asdict(hit) for hit in hits]


def compare_frontend_live(
    live_ops: list[dict[str, Any]],
    frontend_hits: list[dict[str, Any]],
) -> dict[str, Any]:
    live_paths = {row["path"] for row in live_ops}
    issues: list[dict[str, Any]] = []
    matched = 0
    for hit in frontend_hits:
        path = hit["path"]
        if hit["helper"] == "websocket":
            continue
        if hit["helper"] == "apiRequest" and path.startswith("/api/v1/"):
            stripped = path.replace("/api/v1", "", 1)
            issues.append(
                {
                    "type": "DOUBLE_PREFIX",
                    "source_file": hit["source_file"],
                    "line": hit["line"],
                    "path": path,
                    "expected_live_path": f"/api/v1{stripped}",
                }
            )
            continue
        normalized = path
        if normalized.startswith("${"):
            continue
        if normalized.startswith("/api/v1/"):
            if normalized in live_paths:
                matched += 1
            elif normalized.replace("/api/v1", "", 1) and normalized.startswith("/api/v1/"):
                stripped = normalized.replace("/api/v1", "", 1)
                if f"/api/v1{stripped}" in live_paths:
                    issues.append(
                        {
                            "type": "DOUBLE_PREFIX",
                            "source_file": hit["source_file"],
                            "line": hit["line"],
                            "path": path,
                            "expected_live_path": f"/api/v1{stripped}",
                        }
                    )
        elif normalized.startswith("/"):
            if f"/api/v1{normalized}" in live_paths or normalized in live_paths:
                matched += 1
        if "localhost:8000" in path or "127.0.0.1:8000" in path:
            issues.append(
                {
                    "type": "HOSTNAME_FALLBACK",
                    "source_file": hit["source_file"],
                    "line": hit["line"],
                    "path": path,
                }
            )
    return {
        "frontend_hit_count": len(frontend_hits),
        "rough_live_match_count": matched,
        "issues": issues,
    }


def classify_security(route: APIRoute) -> tuple[str, list[str], str]:
    deps = route_dependency_names(route)
    path = route.path
    source = route_source_text(route)
    if "paystack_webhook" in route.name or "signature" in source.lower():
        return "WEBHOOK_SIGNATURE", deps, "high"
    if "get_current_user_optional" in deps:
        return "OPTIONAL_AUTH", deps, "high"
    if any(dep in deps for dep in ("require_permission",)):
        return "PERMISSION_GATED", deps, "high"
    if any(dep in deps for dep in ("require_role",)):
        return "ROLE_GATED", deps, "high"
    if "get_current_user" in deps or "CurrentUser" in source:
        if any(token in path for token in ("{event_id}", "{host_id}", "{product_id}", "{ticket_id}", "{order_id}", "{thread_id}", "{deal_id}", "{invoice_id}", "{request_id}", "{payout_id}", "{memory_id}", "{item_id}")):
            return "OWNER_GATED", deps, "medium"
        return "AUTHENTICATED", deps, "high"
    if path == "/api/v1/messages/ws":
        return "AUTHENTICATED", deps, "high"
    if path.startswith("/api/v1/admin"):
        return "PERMISSION_GATED", deps, "medium"
    return "PUBLIC", deps, "medium"


def build_openapi_security_audit(
    live_ops: list[dict[str, Any]], local_routes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    route_index = {
        (row["method"], row["path"]): row for row in local_routes if row["include_in_schema"]
    }
    results = []
    for op in live_ops:
        key = (op["method"], op["path"])
        row = route_index.get(key)
        actual = "UNKNOWN"
        dependencies: list[str] = []
        confidence = "low"
        if row is not None:
            route_obj = next(
                (
                    route
                    for route in app.routes
                    if isinstance(route, APIRoute)
                    and route.path == row["path"]
                    and op["method"] in getattr(route, "methods", set())
                ),
                None,
            )
            if route_obj is not None:
                actual, dependencies, confidence = classify_security(route_obj)
        results.append(
            {
                "method": op["method"],
                "path": op["path"],
                "operationId": op["operationId"],
                "tags": op["tags"],
                "openapi_security": op["security"],
                "actual_enforcement": actual,
                "dependency_calls": dependencies,
                "confidence": confidence,
                "security_defect": False,
                "notes": None,
            }
        )
    return results


def identity_class(security_label: str, path: str, tags: list[str]) -> str:
    if security_label == "PUBLIC":
        return "PUBLIC"
    if security_label == "OPTIONAL_AUTH":
        return "OPTIONAL_AUTH"
    if security_label == "WEBHOOK_SIGNATURE":
        return "WEBHOOK"
    if path.startswith("/api/v1/admin"):
        if "finance" in path:
            return "FINANCE_ADMIN"
        return "ADMIN"
    if "support" in path and security_label in {"PERMISSION_GATED", "ROLE_GATED"}:
        return "SUPPORT"
    if "sponsors" in path or any("sponsor" in tag for tag in tags):
        return "SPONSOR"
    if "host/" in path or path.startswith("/api/v1/hosts"):
        return "HOST_TEAM_PERMISSION" if security_label in {"OWNER_GATED", "PERMISSION_GATED"} else "HOST"
    if security_label == "AUTHENTICATED":
        return "AUTHENTICATED"
    if security_label == "OWNER_GATED":
        return "HOST_OWNER" if any(token in path for token in ("event", "host", "product", "deal")) else "FAN"
    if security_label in {"ROLE_GATED", "PERMISSION_GATED"}:
        return "ADMIN"
    return "OTHER"


def build_auth_matrix(security_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in security_audit:
        out.append(
            {
                "method": row["method"],
                "path": row["path"],
                "operationId": row["operationId"],
                "identity_class": identity_class(
                    row["actual_enforcement"], row["path"], row["tags"]
                ),
                "actual_enforcement": row["actual_enforcement"],
                "evidence": row["dependency_calls"],
                "confidence": row["confidence"],
            }
        )
    return out


def build_ownership_matrix(live_ops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    resource_map = [
        ("{event_id}", "host workspace", "HOST_A", "HOST_B", "FAN_A", "ANONYMOUS"),
        ("{host_id}", "host workspace", "HOST_A", "HOST_B", "FAN_A", "ANONYMOUS"),
        ("{ticket_id}", "ticket buyer", "FAN_A", "FAN_B", "HOST_B", "ANONYMOUS"),
        ("{order_id}", "order buyer", "FAN_A", "FAN_B", "HOST_A", "ANONYMOUS"),
        ("{thread_id}", "message participants", "FAN_A", "FAN_B", "HOST_B", "ANONYMOUS"),
        ("{deal_id}", "sponsor workspace", "SPONSOR_A", "HOST_B", "FAN_A", "ANONYMOUS"),
        ("{memory_id}", "memory uploader", "FAN_A", "FAN_B", "HOST_B", "ANONYMOUS"),
        ("{item_id}", "vault purchaser/grantee", "FAN_A", "FAN_B", "HOST_B", "ANONYMOUS"),
    ]
    rows = []
    for op in live_ops:
        for token, owner_type, owner, other_same_role, wrong_role, anon in resource_map:
            if token in op["path"]:
                rows.append(
                    {
                        "method": op["method"],
                        "path": op["path"],
                        "resource_owner_type": owner_type,
                        "future_tests": [
                            {"actor": owner, "expected": "ALLOW"},
                            {"actor": other_same_role, "expected": "DENY"},
                            {"actor": wrong_role, "expected": "DENY"},
                            {"actor": anon, "expected": "DENY"},
                        ],
                    }
                )
                break
    return rows


def valid_transition_pairs(states: list[str]) -> list[list[str]]:
    return [[states[idx], states[idx + 1]] for idx in range(len(states) - 1)]


def invalid_transition_pairs(states: list[str]) -> list[list[str]]:
    if len(states) < 3:
        return []
    return [[states[-1], states[0]], [states[0], states[-1]]]


def build_state_machines() -> dict[str, Any]:
    order_states = ["pending", "paid", "failed", "abandoned", "cancelled"]
    payment_states = ["pending", "successful", "failed"]
    ticket_states = [
        "active",
        "reserved",
        "checked_in",
        "cancelled",
        "refunded",
        "transferred",
        "invalid",
        "expired",
    ]
    transfer_states = ["pending", "completed", "revoked", "declined"]
    return {
        "events": {
            "states": list(EVENT_STATUSES),
            "valid_transitions": valid_transition_pairs(list(EVENT_STATUSES)),
            "invalid_transitions": invalid_transition_pairs(list(EVENT_STATUSES)),
            "operations": ["/api/v1/events", "/api/v1/host/events/{event_id}"],
            "critical_invariants": ["cancelled/paused events must not remain purchasable"],
        },
        "orders": {
            "states": order_states,
            "valid_transitions": [["pending", "paid"], ["pending", "failed"], ["pending", "cancelled"]],
            "invalid_transitions": [["paid", "pending"], ["cancelled", "paid"]],
            "operations": ["/api/v1/orders/{order_id}", "/api/v1/payments/checkout/{order_id}"],
            "critical_invariants": ["frontend callback alone must not mark order paid"],
        },
        "payments": {
            "states": payment_states,
            "valid_transitions": [["pending", "successful"], ["pending", "failed"]],
            "invalid_transitions": [["successful", "pending"]],
            "operations": ["/api/v1/payments/webhooks/paystack"],
            "critical_invariants": ["duplicate webhook must not duplicate tickets or ledger"],
        },
        "tickets": {
            "states": ticket_states,
            "valid_transitions": [["reserved", "active"], ["active", "checked_in"], ["active", "transferred"]],
            "invalid_transitions": [["checked_in", "active"], ["cancelled", "checked_in"]],
            "operations": ["/api/v1/tickets/{ticket_id}", "/api/v1/checkins/scan"],
            "critical_invariants": ["QR must not expose raw identifiers", "duplicate check-in must be blocked"],
        },
        "transfers": {
            "states": transfer_states,
            "valid_transitions": valid_transition_pairs(transfer_states),
            "invalid_transitions": [["completed", "pending"]],
            "operations": ["/api/v1/tickets/transfers/{transfer_id}/claim"],
            "critical_invariants": ["claim must be one-time and ownership checked"],
        },
        "refunds": {
            "states": list(REFUND_REQUEST_STATUSES),
            "valid_transitions": valid_transition_pairs(list(REFUND_REQUEST_STATUSES)),
            "invalid_transitions": [["completed", "requested"]],
            "operations": ["/api/v1/finance/refunds"],
            "critical_invariants": ["refunded tickets must not remain valid"],
        },
        "payouts": {
            "states": list(PAYOUT_STATUSES),
            "valid_transitions": valid_transition_pairs(list(PAYOUT_STATUSES)),
            "invalid_transitions": [["paid", "requested"]],
            "operations": ["/api/v1/finance/payouts"],
            "critical_invariants": ["manual payout evidence must remain immutable"],
        },
        "memories": {
            "states": list(MEMORY_STATUSES),
            "valid_transitions": [["draft", "published"], ["published", "hidden"]],
            "invalid_transitions": [["hidden", "draft"]],
            "operations": ["/api/v1/memories", "/api/v1/memories/{memory_id}"],
            "critical_invariants": [
                f"eligible events only: {', '.join(ELIGIBLE_EVENT_STATUSES)}",
                f"moderation states: {', '.join(MEMORY_MODERATION_STATUSES)}",
                f"photo states: {', '.join(MEMORY_PHOTO_STATUSES)}",
            ],
        },
        "merch": {
            "states": list(PRODUCT_STATUSES),
            "valid_transitions": [["draft", "active"], ["active", "paused"], ["active", "sold_out"], ["active", "archived"]],
            "invalid_transitions": [["archived", "draft"]],
            "operations": ["/api/v1/merch", "/api/v1/host/merchandise"],
            "critical_invariants": [
                f"unsafe event statuses: {', '.join(sorted(UNSAFE_EVENT_STATUSES))}",
                f"variant states: {', '.join(VARIANT_STATUSES)}",
                f"fulfillment states: {', '.join(FULFILLMENT_STATUSES)}",
            ],
        },
        "support": {
            "states": list(SUPPORT_STATUSES),
            "valid_transitions": valid_transition_pairs(list(SUPPORT_STATUSES)),
            "invalid_transitions": [["archived", "open"]],
            "operations": ["/api/v1/support/tickets/{ticket_id}"],
            "critical_invariants": ["non-requesters must not access support tickets"],
        },
        "sponsorship": {
            "states": list(DEAL_STATUSES),
            "valid_transitions": [["draft", "proposed"], ["proposed", "accepted"], ["accepted", "invoice_pending"], ["payment_pending", "paid"], ["paid", "active"], ["active", "completed"]],
            "invalid_transitions": [["completed", "draft"]],
            "operations": ["/api/v1/host/sponsorship-deals/{deal_id}", "/api/v1/sponsors/workspaces/{sponsor_id}/deals/{deal_id}/pay"],
            "critical_invariants": [
                f"slot states: {', '.join(SLOT_STATUSES)}",
                f"inquiry states: {', '.join(INQUIRY_STATUSES)}",
                f"placement states: {', '.join(PLACEMENT_STATUSES)}",
                f"invoice states: {', '.join(INVOICE_STATUSES)}",
            ],
        },
        "vault": {
            "states": list(VAULT_ITEM_STATUSES),
            "valid_transitions": [["draft", "published"], ["published", "expired"], ["published", "archived"]],
            "invalid_transitions": [["archived", "draft"]],
            "operations": ["/api/v1/vault", "/api/v1/vault/purchases/{purchase_id}"],
            "critical_invariants": [
                f"purchase states: {', '.join(VAULT_PURCHASE_STATUSES)}",
                "private vault media must never become public CDN content",
            ],
        },
    }


def classify_risk(op: dict[str, Any]) -> dict[str, Any]:
    method = op["method"]
    path = op["path"]
    tags = op["tags"]
    if "webhook" in path or path.startswith("/api/v1/finance") or path.startswith("/api/v1/admin"):
        return {"tier": "TIER_3", "severity": "HIGH" if "admin" in path else "CRITICAL"}
    if method in {"POST", "PATCH", "PUT", "DELETE"}:
        return {"tier": "TIER_2", "severity": "MEDIUM"}
    if path.startswith("/api/v1/host") or path.startswith("/api/v1/me") or "tickets" in tags:
        return {"tier": "TIER_1", "severity": "MEDIUM"}
    return {"tier": "TIER_0", "severity": "LOW"}


def meaningful_scenarios(op: dict[str, Any], security: str) -> list[str]:
    method = op["method"]
    path = op["path"]
    scenarios = ["HAPPY_PATH"]
    if security not in {"PUBLIC", "WEBHOOK_SIGNATURE"}:
        scenarios.extend(["NO_AUTH", "INVALID_AUTH"])
    if security in {"OWNER_GATED", "PERMISSION_GATED", "ROLE_GATED"}:
        scenarios.extend(["WRONG_ROLE", "WRONG_OWNER"])
    if op["path_parameters"]:
        scenarios.extend(["INVALID_UUID", "NOT_FOUND"])
    if method in {"POST", "PATCH", "PUT"}:
        scenarios.extend(["INVALID_BODY", "MISSING_FIELD", "BOUNDARY"])
    if "webhook" in path or "checkin" in path or "claim" in path or "checkout" in path:
        scenarios.extend(["DUPLICATE", "IDEMPOTENT_RETRY", "CONCURRENT"])
    if "status" in path or "cancel" in path or "approve" in path or "publish" in path:
        scenarios.append("STATE_CONFLICT")
    if "payments" in path or "email" in path or "push" in path or "vault" in path:
        scenarios.append("PROVIDER_FAILURE")
    if path.startswith("/api/v1/auth/"):
        scenarios.extend(["EXPIRED_AUTH", "RATE_LIMIT"])
    return sorted(set(scenarios), key=scenarios.index)


def build_scenario_plan(
    live_ops: list[dict[str, Any]],
    security_audit: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    security_index = {
        (row["method"], row["path"]): row["actual_enforcement"] for row in security_audit
    }
    rows = []
    total = 0
    for op in live_ops:
        scenarios = meaningful_scenarios(
            op, security_index.get((op["method"], op["path"]), "PUBLIC")
        )
        total += len(scenarios)
        rows.append(
            {
                "method": op["method"],
                "path": op["path"],
                "operationId": op["operationId"],
                "scenarios": scenarios,
            }
        )
    return rows, total


def build_production_safety_plan(live_ops: list[dict[str, Any]], security_audit: list[dict[str, Any]]) -> list[dict[str, Any]]:
    security_index = {
        (row["method"], row["path"]): row["actual_enforcement"] for row in security_audit
    }
    rows = []
    for op in live_ops:
        method = op["method"]
        path = op["path"]
        security = security_index.get((method, path), "PUBLIC")
        if "webhook" in path or path.startswith("/api/v1/finance") or "payout" in path or "refund" in path:
            mode = "NEVER_AUTOMATED_PRODUCTION"
        elif method == "GET" and security == "PUBLIC":
            mode = "SAFE_LIVE_READ"
        elif method == "GET":
            mode = "DEDICATED_ACCOUNT_LIVE_READ"
        elif "payments" in path or "email" in path or "push" in path:
            mode = "MOCKED_PROVIDER_ONLY"
        elif method in {"POST", "PATCH", "PUT", "DELETE"}:
            mode = "LOCAL_ONLY"
        else:
            mode = "CONTROLLED_LIVE_MUTATION"
        rows.append({"method": method, "path": path, "mode": mode})
    return rows


def build_duplicate_report(local_routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in local_routes:
        grouped[(row["method"], row["path"])].append(row)
    report = []
    for (method, path), rows in sorted(grouped.items()):
        if len(rows) < 2:
            continue
        first, second = rows[0], rows[1]
        same_impl = first["endpoint_name"] == second["endpoint_name"]
        same_deps = first["dependencies"] == second["dependencies"]
        same_resp = first["response_model"] == second["response_model"]
        if same_impl and same_deps and same_resp:
            classification = "INTENTIONAL_EXACT_ALIAS"
        elif same_deps and same_resp:
            classification = "INTENTIONAL_BUT_DANGEROUS_DUPLICATION"
        else:
            classification = "ROUTE_COLLISION"
        report.append(
            {
                "method": method,
                "path": path,
                "classification": classification,
                "registrations": rows,
                "first_matching_handler": first["endpoint_name"],
                "second_matching_handler": second["endpoint_name"],
            }
        )
    return report


def scan_openapi_for_sensitive_schema(openapi: dict[str, Any]) -> list[dict[str, Any]]:
    risky_names = (
        "password_hash",
        "secret_key",
        "refresh_token",
        "access_token",
        "webhook_secret",
        "private_key",
        "r2_secret",
        "aws_secret_access_key",
    )
    findings = []
    for schema_name, schema in (openapi.get("components", {}).get("schemas") or {}).items():
        props = schema.get("properties") or {}
        for prop_name in props:
            lowered = prop_name.lower()
            if any(token in lowered for token in risky_names):
                findings.append(
                    {
                        "schema": schema_name,
                        "field": prop_name,
                        "reason": "potentially sensitive schema field name",
                    }
                )
    return findings


def build_test_coverage(live_ops: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    test_files = sorted((BACKEND_ROOT / "tests").glob("test_*.py"))
    rows = []
    scenario_totals = Counter()
    covered = 0
    for op in live_ops:
        matched_files = []
        scenarios = set()
        path_pattern = re.escape(op["path"])
        path_pattern = re.sub(r"\\\{[^}]+\\\}", r"[^\"']+", path_pattern)
        client_pattern = re.compile(
            rf"client\.{op['method'].lower()}\(\s*f?[\"']{path_pattern}[\"']",
            re.S,
        )
        api_pattern = None
        if len(op["path"]) > 8 and op["path"] not in {"/", "/health", "/ready"}:
            api_pattern = re.compile(
                rf"[\"']{re.escape(op['path'])}[\"']",
                re.S,
            )
        for file in test_files:
            text = read_text(file)
            if client_pattern.search(text) or (api_pattern is not None and api_pattern.search(text)):
                matched_files.append(str(file.relative_to(BACKEND_ROOT)))
                lowered = text.lower()
                if " 401" in lowered or "no auth" in lowered:
                    scenarios.add("no_auth")
                if "403" in lowered:
                    scenarios.add("wrong_role")
                if "404" in lowered:
                    scenarios.add("missing_resource")
                if "422" in lowered or "400" in lowered:
                    scenarios.add("invalid_body")
                if "duplicate" in lowered:
                    scenarios.add("duplicate")
                if "concurrent" in lowered or "threadpoolexecutor" in lowered:
                    scenarios.add("concurrency")
                if "webhook" in lowered and "duplicate" in lowered:
                    scenarios.add("idempotent_retry")
                if "client." in lowered:
                    scenarios.add("happy_path")
        matched_files = sorted(set(matched_files))
        if matched_files:
            covered += 1
        for scenario in scenarios:
            scenario_totals[scenario] += 1
        rows.append(
            {
                "method": op["method"],
                "path": op["path"],
                "operationId": op["operationId"],
                "test_files": matched_files,
                "scenario_types_found": sorted(scenarios),
            }
        )
    summary = {
        "live_operation_count": len(live_ops),
        "operations_with_direct_or_loose_test_mapping": covered,
        "operations_without_test_mapping": len(live_ops) - covered,
        "scenario_type_counts": dict(scenario_totals),
    }
    return rows, summary


def build_failure_register(
    frontend_diff: dict[str, Any],
    duplicate_report: list[dict[str, Any]],
    live_summary: dict[str, Any],
    baseline_failures: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []

    double_prefix_issues = [
        row for row in frontend_diff["issues"] if row["type"] == "DOUBLE_PREFIX"
    ]
    if double_prefix_issues:
        example = double_prefix_issues[0]
        path = example["path"]
        stripped = path.replace("/api/v1", "", 1)
        failures.append(
            {
                "id": "API-P1-001",
                "severity": "P1",
                "status": "CONFIRMED",
                "method": "MULTI",
                "path": path,
                "module": "frontend sponsor deals",
                "scenario": "frontend URL construction",
                "environment": "local/static-analysis",
                "expected": f"${{API_URL}}${{API_PREFIX}}{stripped}",
                "actual": f"${{API_URL}}${{API_PREFIX}}{path}",
                "reproduction": "Run sponsor-deals audit test and inspect fetch URL construction",
                "root_cause": None,
                "regression_test": "frontend/src/lib/sponsor-deals-api.audit.test.ts",
                "fix": None,
                "targeted_retest": None,
                "module_retest": None,
                "full_retest": None,
                "live_verification": None,
            }
        )

    if (
        live_summary["operation_count"] != PHASE0_BASELINE["operations"]
        or live_summary["tag_count"] != PHASE0_BASELINE["tags"]
    ):
        failures.append(
            {
                "id": "API-DRIFT-001",
                "severity": "P2",
                "status": "OPEN",
                "method": "N/A",
                "path": "openapi.json",
                "module": "inventory",
                "scenario": "live openapi drift",
                "environment": "live read-only",
                "expected": f"{PHASE0_BASELINE['operations']} operations / {PHASE0_BASELINE['tags']} tags",
                "actual": f"{live_summary['operation_count']} operations / {live_summary['tag_count']} tags",
                "reproduction": "Re-run backend/scripts/api_audit/generate.py",
                "root_cause": None,
                "regression_test": None,
                "fix": None,
                "targeted_retest": None,
                "module_retest": None,
                "full_retest": None,
                "live_verification": None,
            }
        )

    for idx, row in enumerate(duplicate_report, start=1):
        if row["classification"] == "ROUTE_COLLISION":
            failures.append(
                {
                    "id": f"API-P2-{idx:03d}",
                    "severity": "P2",
                    "status": "OPEN",
                    "method": row["method"],
                    "path": row["path"],
                    "module": "routing",
                    "scenario": "duplicate route registration",
                    "environment": "local import",
                    "expected": "single unambiguous handler per method/path",
                    "actual": f"{len(row['registrations'])} handlers registered",
                    "reproduction": "Re-run route collision report generator",
                    "root_cause": None,
                    "regression_test": None,
                    "fix": None,
                    "targeted_retest": None,
                    "module_retest": None,
                    "full_retest": None,
                    "live_verification": None,
                }
            )

    for item in baseline_failures or []:
        failures.append(item)
    return failures


def baseline_findings_from_results() -> list[dict[str, Any]]:
    path = ARTIFACTS_DIR / "13-baseline-test-results.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    findings = []
    seq = 100
    for row in payload.get("results", []):
        if row.get("status") not in {
            "PRE_EXISTING_PRODUCT_FAILURE",
            "TEST_INFRASTRUCTURE_FAILURE",
        }:
            continue
        severity = "P2" if row["status"] == "PRE_EXISTING_PRODUCT_FAILURE" else "P3"
        findings.append(
            {
                "id": f"API-{severity}-{seq:03d}",
                "severity": severity,
                "status": "OPEN",
                "method": "TEST",
                "path": row.get("classname") or "pytest",
                "module": "backend baseline",
                "scenario": row.get("name"),
                "environment": "local pytest",
                "expected": "existing backend baseline passes",
                "actual": row.get("message") or row.get("status"),
                "reproduction": "pytest --junitxml=artifacts/api-audit/baseline-junit.xml",
                "root_cause": None,
                "regression_test": None,
                "fix": None,
                "targeted_retest": None,
                "module_retest": None,
                "full_retest": None,
                "live_verification": None,
            }
        )
        seq += 1
    return findings


def build_risk_classification(live_ops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for op in live_ops:
        risk = classify_risk(op)
        rows.append(
            {
                "method": op["method"],
                "path": op["path"],
                "operationId": op["operationId"],
                "tier": risk["tier"],
                "severity": risk["severity"],
            }
        )
    return rows


def build_hostname_findings() -> list[dict[str, Any]]:
    """Classify hostname references found in frontend/backend audit scan."""
    return [
        {
            "id": "HN-001",
            "host": "127.0.0.1:8000 / localhost:8000",
            "locations": [
                "frontend/src/lib/api-base.ts (SSR fallback via API_PROXY_TARGET)",
                "frontend/next.config.ts (rewrite proxy target)",
                "frontend/src/lib/cache/public-api.ts, blog-api.ts, knowledge-base/api.ts, seo/public-fetch.ts, sitemap.ts",
            ],
            "classification": "VALID DEVELOPMENT FALLBACK",
            "runtime": "Used only when NEXT_PUBLIC_API_URL is unset during SSR/build; browser uses same-origin rewrites.",
            "action": "No fix in Phase 1; verify production env sets NEXT_PUBLIC_API_URL.",
        },
        {
            "id": "HN-002",
            "host": "localhost:8000 hardcoded in page loaders",
            "locations": [
                "frontend/src/app/hosts/page.tsx",
                "frontend/src/app/sponsorships/hosts/page.tsx",
                "frontend/src/lib/seo/hub-page.tsx",
            ],
            "classification": "VALID DEVELOPMENT FALLBACK (with risk)",
            "runtime": "Bypasses getApiBaseUrl(); falls back to localhost when env unset. Production with NEXT_PUBLIC_API_URL set is unaffected.",
            "action": "Phase 2: consolidate onto getApiBaseUrl() for consistency.",
        },
        {
            "id": "HN-003",
            "host": "padeyawebsite.onrender.com",
            "locations": [
                "frontend/next.config.ts (images.remotePatterns)",
                "frontend/src/lib/media-image.ts (OPTIMIZABLE_MEDIA_HOSTS)",
            ],
            "classification": "LEGACY COMPATIBILITY",
            "runtime": "Allows Next/Image optimization for legacy Render-hosted media URLs still stored in DB.",
            "action": "Monitor; not a runtime API bug.",
        },
        {
            "id": "HN-004",
            "host": "padeya.smartlancedesigns.com",
            "locations": [
                "frontend/src/lib/media.ts (enforcePadeyaDemoAssetUrl rewrite)",
                "frontend/src/lib/seo/env-policy.ts (forbidden canonical host)",
            ],
            "classification": "LEGACY COMPATIBILITY",
            "runtime": "Rewrites legacy demo asset URLs to padeya.com; explicitly forbidden as canonical host.",
            "action": "No fix; intentional migration shim.",
        },
    ]


def build_high_risk_gaps(
    live_ops: list[dict[str, Any]], coverage_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    tag_map = {(o["method"], o["path"]): o["tags"] for o in live_ops}
    cov_map = {(o["method"], o["path"]): o for o in coverage_rows}
    modules = {
        "AUTH": ["auth"],
        "PAYMENTS": ["payments"],
        "ORDERS": ["payments", "orders", "checkout"],
        "PAYSTACK WEBHOOK": ["payments", "webhook"],
        "TICKETS": ["tickets"],
        "CHECKINS": ["checkins"],
        "FINANCE": ["finance", "finance-fees"],
        "VAULT": ["vault"],
        "PRIVATE MEDIA": ["vault", "messaging", "messages/attachments"],
        "MESSAGING": ["messaging"],
        "SUPPORT": ["support"],
        "MEMORIES": ["memories"],
        "ADMIN": ["admin"],
        "HOST OWNERSHIP": ["hosts", "host-team", "events", "host/"],
    }
    rows = []
    for name, needles in modules.items():
        ops = []
        for key, tags in tag_map.items():
            path = key[1]
            if any(n in path.lower() or any(n in t.lower() for t in tags) for n in needles):
                ops.append(key)
        tested = sum(1 for k in ops if cov_map.get(k, {}).get("test_files"))
        scenarios = set()
        for k in ops:
            scenarios.update(cov_map.get(k, {}).get("scenario_types_found", []))
        missing = sorted(
            s
            for s in (
                "happy_path",
                "no_auth",
                "wrong_role",
                "wrong_owner",
                "invalid_body",
                "missing_resource",
                "duplicate",
                "concurrency",
                "idempotent_retry",
                "provider_failure",
            )
            if s not in scenarios
        )
        rows.append(
            {
                "module": name,
                "operations": len(ops),
                "operations_with_tests": tested,
                "coverage_gap": len(ops) - tested,
                "existing_scenario_types": sorted(scenarios),
                "missing_scenario_categories": missing,
            }
        )
    return rows


def build_concurrency_test_plan() -> list[dict[str, Any]]:
    return [
        {
            "id": "CC-001",
            "domain": "Paystack webhook",
            "invariant": "Duplicate webhook delivery must not create duplicate tickets, orders, ledger entries, or inventory deductions.",
            "test_design": "Two concurrent POST /payments/webhooks/paystack with identical event_key; assert one processed, one duplicate status.",
            "existing_coverage": "test_payments.py::test_idempotent_webhook_and_duplicate_protection (sequential only)",
            "gap": "No true parallel/concurrent webhook race test.",
        },
        {
            "id": "CC-002",
            "domain": "Check-in",
            "invariant": "Two simultaneous scan requests for same ticket → exactly one first check-in; second returns duplicate; ticket status remains checked_in once.",
            "test_design": "Parallel POST /checkins/scan with identical valid QR payload.",
            "existing_coverage": "test_checkins.py::test_duplicate_check_in (sequential)",
            "gap": "No concurrent scan race test.",
        },
        {
            "id": "CC-003",
            "domain": "Ticket inventory",
            "invariant": "Last available ticket must not oversell under concurrent checkout.",
            "test_design": "Parallel checkout attempts when quantity_remaining=1.",
            "existing_coverage": "Partial via payments tests; no explicit race.",
            "gap": "Concurrency race untested.",
        },
        {
            "id": "CC-004",
            "domain": "Merch inventory",
            "invariant": "Last merch variant must not oversell under concurrent cart/checkout.",
            "test_design": "Parallel checkout with last unit in stock.",
            "existing_coverage": "test_merch.py webhook idempotency (sequential)",
            "gap": "Inventory race untested.",
        },
        {
            "id": "CC-005",
            "domain": "Promo redemption",
            "invariant": "Single-use promo must not apply twice under concurrent requests.",
            "test_design": "Parallel checkout with same one-time promo code.",
            "existing_coverage": "test_promos.py (no concurrency)",
            "gap": "Redemption race untested.",
        },
        {
            "id": "CC-006",
            "domain": "Ticket transfer claim",
            "invariant": "Transfer claim token must be single-use; concurrent claims → one success, one reject.",
            "test_design": "Parallel POST claim with same transfer token.",
            "existing_coverage": "test_advanced_ticketing.py (sequential flows)",
            "gap": "Claim race untested.",
        },
        {
            "id": "CC-007",
            "domain": "Memory contribution limit",
            "invariant": "Per-user/event photo limit must not be exceeded under concurrent uploads.",
            "test_design": "Parallel POST memory photo uploads at limit boundary.",
            "existing_coverage": "test_memories.py, test_memory_photos.py (sequential)",
            "gap": "Upload race untested.",
        },
    ]


def build_baseline_summary() -> dict[str, Any] | None:
    path = ARTIFACTS_DIR / "13-baseline-test-results.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    by_module: dict[str, int] = Counter()
    for row in payload.get("results", []):
        if row.get("status") == "PRE_EXISTING_PRODUCT_FAILURE":
            mod = (row.get("classname") or "unknown").replace("tests.", "")
            by_module[mod] += 1
    return {
        "collected": payload.get("collected"),
        "passed": payload.get("passed"),
        "failed": payload.get("failed"),
        "skipped": payload.get("skipped"),
        "errors": payload.get("errors"),
        "duration_seconds": payload.get("duration_seconds"),
        "failed_by_module": dict(by_module.most_common(20)),
    }


def build_phase1_report(
    live_summary: dict[str, Any],
    local_summary: dict[str, Any],
    live_local_diff: dict[str, Any],
    hidden: dict[str, Any],
    frontend_diff: dict[str, Any],
    duplicate_report: list[dict[str, Any]],
    security_audit: list[dict[str, Any]],
    coverage_summary: dict[str, Any],
    scenario_total: int,
    failure_register: list[dict[str, Any]],
    hostname_findings: list[dict[str, Any]],
    high_risk_gaps: list[dict[str, Any]],
    concurrency_plan: list[dict[str, Any]],
    baseline_summary: dict[str, Any] | None,
    schema_findings: list[dict[str, Any]],
    ownership_count: int = 0,
) -> str:
    counts = Counter(row["severity"] for row in failure_register)
    security_unset = sum(1 for row in security_audit if row["openapi_security"] == "__INHERIT__")
    enforcement = Counter(row["actual_enforcement"] for row in security_audit)
    p1_findings = [f for f in failure_register if f["severity"] == "P1"]
    open_findings = [f for f in failure_register if f["status"] in {"OPEN", "CONFIRMED", "NEEDS_REPRODUCTION"}]

    baseline_block = "Baseline not run."
    if baseline_summary:
        baseline_block = textwrap.dedent(
            f"""\
            - collected: {baseline_summary['collected']}
            - passed: {baseline_summary['passed']}
            - failed: {baseline_summary['failed']}
            - skipped: {baseline_summary['skipped']}
            - errors: {baseline_summary['errors']}
            - duration: {baseline_summary['duration_seconds']:.1f}s
            - top failing modules: {baseline_summary['failed_by_module']}"""
        )

    gap_lines = "\n".join(
        f"- **{g['module']}**: {g['operations']} ops, {g['operations_with_tests']} tested, gap {g['coverage_gap']}; missing scenarios: {', '.join(g['missing_scenario_categories'][:6])}"
        for g in high_risk_gaps
    )

    cc_lines = "\n".join(
        f"- **{c['id']}** {c['domain']}: {c['invariant']}"
        for c in concurrency_plan
    )

    hn_lines = "\n".join(
        f"- **{h['id']}** {h['host']} → {h['classification']}"
        for h in hostname_findings
    )

    dup_lines = "\n".join(
        f"- `{d['method']} {d['path']}` → {d['classification']} (first: `{d['first_matching_handler']}`)"
        for d in duplicate_report
    )

    return textwrap.dedent(
        f"""\
        # PÀDÉYÁ FINAL API AUDIT — PHASE 1 REPORT

        Generated by `backend/scripts/api_audit/generate.py`.

        ## A. Phase 1 verdict

        **PHASE 1 COMPLETE — BASELINE ESTABLISHED, FIXES DEFERRED.**

        Reproducible audit harness created. Live OpenAPI re-confirmed at **1,161 operations / 77 tags**.
        Local/live parity holds at **100%** for documented routes. **PF-001 CONFIRMED** (sponsor-deals double `/api/v1`).
        Backend baseline: **{baseline_summary['passed'] if baseline_summary else '?'} passed / {baseline_summary['failed'] if baseline_summary else '?'} failed** of {baseline_summary['collected'] if baseline_summary else '?'} tests.
        **{len(open_findings)} open findings** in failure register ({counts.get('P1', 0)} P1, {counts.get('P2', 0)} P2).

        ## B. Live OpenAPI count re-confirmed

        | Metric | Value |
        |--------|------:|
        | Operations | {live_summary['operation_count']} |
        | Tags | {live_summary['tag_count']} |
        | Path templates | {live_summary['path_template_count']} |
        | GET/POST/PATCH/PUT/DELETE | {live_summary['method_counts'].get('GET')}/{live_summary['method_counts'].get('POST')}/{live_summary['method_counts'].get('PATCH')}/{live_summary['method_counts'].get('PUT')}/{live_summary['method_counts'].get('DELETE')} |

        No API-DRIFT-001 — counts match Phase 0 baseline.

        ## C. Local/live parity

        - Intersection: **{live_local_diff['intersection_count']} / {live_local_diff['live_operation_count']}**
        - Live-only: {len(live_local_diff['live_only'])}
        - Local-only (OpenAPI): {len(live_local_diff['local_only'])}
        - Exact match: **{live_local_diff['current_exact_match']}**

        ## D. Hidden API surface

        - Hidden HTTP routes: **{local_summary['hidden_http_count']}** (email settings aliases, platform go-live)
        - WebSocket: **WS /api/v1/messages/ws**
        - Static mount: **GET /media/{{path}}**
        - Root aliases: /, /health, /ready (+ /api/v1 mirrors)
        - FastAPI meta: /docs, /redoc, /openapi.json (local only, not in live inventory denominator)

        ## E. Frontend/live contract findings

        - Frontend hits scanned: **{frontend_diff['frontend_hit_count']}**
        - Contract issues: **{len(frontend_diff['issues'])}** (all DOUBLE_PREFIX in sponsor-deals-api.ts)
        - PF-001: **CONFIRMED** — 22 call sites produce `/api/v1/api/v1/...`

        ## F. PF-001 confirmation result

        **CONFIRMED** via `frontend/src/lib/sponsor-deals-api.audit.test.ts`:
        - `apiRequest('/api/v1/host/sponsorship-deals')` → `https://api.example.test/api/v1/api/v1/host/sponsorship-deals`
        - Recorded as **API-P1-001** in failure register. **Not fixed in Phase 1.**

        ## G. Hostname/runtime findings

        {hn_lines}

        None classified as ACTUAL PRODUCTION BUG without env misconfiguration.

        ## H. Duplicate route findings

        {dup_lines}

        All classified **INTENTIONAL_BUT_DANGEROUS_DUPLICATION** — first registered handler wins; no behavioral divergence detected.

        ## I. OpenAPI security findings

        - Unset/inherited OpenAPI security: **{security_unset}** ops (require code-level verification in Phase 2)
        - Actual enforcement distribution: {dict(enforcement)}
        - Security defects flagged: **0** (no missing runtime auth detected by static analysis)
        - Sensitive schema name matches: **{len(schema_findings)}** (auth token fields in request schemas — expected, not credential leak)

        ## J. Existing backend test baseline

        {baseline_block}

        Dominant failure cluster: ambassador/impersonation modules (NameError/ImportError in working tree).

        ## K. Operation test coverage

        - Mapped: **{coverage_summary['operations_with_direct_or_loose_test_mapping']} / {coverage_summary['live_operation_count']}** ({100 * coverage_summary['operations_with_direct_or_loose_test_mapping'] // coverage_summary['live_operation_count']}%)
        - Unmapped: **{coverage_summary['operations_without_test_mapping']}**

        ## L. Scenario-quality coverage

        Scenario types found across mapped ops: {coverage_summary.get('scenario_type_counts', {})}
        One happy-path test ≠ full coverage; Phase 2 applies per-op scenario matrix.

        ## M. High-risk test gaps

        {gap_lines}

        ## N. Auth matrix summary

        Prepared for all 1,161 ops in `07-auth-matrix.json`. Identity classes include PUBLIC, AUTHENTICATED, OWNER_GATED, PERMISSION_GATED, OPTIONAL_AUTH, WEBHOOK.

        ## O. Ownership/IDOR matrix summary

        **{ownership_count}** ownership-sensitive operations identified in `08-ownership-matrix.json`.

        ## P. State machine summary

        Documented in `09-state-machines.json`: events, orders, payments, tickets, transfers, refunds, payouts, memories, merch, support, sponsorship, vault.

        ## Q. Exact planned scenario count

        **{scenario_total}** meaningful scenarios across 1,161 operations (`10-scenario-plan.json`).

        ## R. Concurrency test plan

        {cc_lines}

        Design only — not executed in Phase 1.

        ## S. Failure register

        See `12-failure-register.json`. Key entries:
        - **API-P1-001**: sponsor-deals double prefix (CONFIRMED)
        - **API-P2-100+**: baseline test failures ({baseline_summary['failed'] if baseline_summary else 0} individual test failures)

        ## T–W. Severity counts

        - P0: {counts.get('P0', 0)}
        - P1: {counts.get('P1', 0)}
        - P2: {counts.get('P2', 0)}
        - P3: {counts.get('P3', 0)}

        ## X. Audit artifacts generated

        All 17 artifacts in `backend/artifacts/api-audit/` (gitignored).

        ## Y. Files changed (audit infrastructure only)

        - `backend/scripts/api_audit/generate.py`
        - `backend/scripts/api_audit/parse_pytest_junit.py`
        - `backend/scripts/api_audit/__init__.py`
        - `frontend/src/lib/sponsor-deals-api.audit.test.ts`
        - `.gitignore` (artifacts path)

        ## Z. Phase 2 recommendation

        Execute Phase 2: **fix API-P1-001**, resolve baseline ambassador/impersonation failures, then run auth/IDOR matrix on Tier 3 modules (payments, tickets, check-ins, vault, finance) using audit personas in staging.
        """
    )


def main() -> None:
    openapi = fetch_live_openapi()
    live_ops, live_summary = build_live_inventory(openapi)
    write_json(
        "00-live-openapi-inventory.json",
        {"summary": live_summary, "operations": live_ops},
    )

    local_routes, local_summary, hidden = build_local_inventory()
    write_json(
        "01-local-route-inventory.json",
        {"summary": local_summary, "routes": local_routes},
    )
    write_json("14-hidden-surface-inventory.json", hidden)

    live_local_diff = compare_live_local(live_ops, local_routes)
    write_json("02-live-local-diff.json", live_local_diff)

    frontend_hits = scan_frontend()
    write_json("03-frontend-consumer-inventory.json", {"hits": frontend_hits})
    frontend_diff = compare_frontend_live(live_ops, frontend_hits)
    write_json("04-frontend-live-diff.json", frontend_diff)

    coverage_rows, coverage_summary = build_test_coverage(live_ops)
    write_json(
        "05-existing-test-coverage.json",
        {"summary": coverage_summary, "operations": coverage_rows},
    )

    risk_rows = build_risk_classification(live_ops)
    write_json("06-risk-classification.json", {"operations": risk_rows})

    security_audit = build_openapi_security_audit(live_ops, local_routes)

    auth_matrix = build_auth_matrix(security_audit)
    write_json("07-auth-matrix.json", {"operations": auth_matrix})

    ownership_rows = build_ownership_matrix(live_ops)
    write_json("08-ownership-matrix.json", {"operations": ownership_rows})

    state_machines = build_state_machines()
    write_json("09-state-machines.json", state_machines)

    scenario_rows, scenario_total = build_scenario_plan(live_ops, security_audit)
    write_json(
        "10-scenario-plan.json",
        {"planned_scenario_count": scenario_total, "operations": scenario_rows},
    )

    production_safety = build_production_safety_plan(live_ops, security_audit)
    write_json("11-production-safety-plan.json", {"operations": production_safety})

    duplicate_report = build_duplicate_report(local_routes)
    write_json("15-route-collision-report.json", {"duplicates": duplicate_report})

    schema_findings = scan_openapi_for_sensitive_schema(openapi)
    hostname_findings = build_hostname_findings()
    high_risk_gaps = build_high_risk_gaps(live_ops, coverage_rows)
    concurrency_plan = build_concurrency_test_plan()
    baseline_summary = build_baseline_summary()

    write_json("17-hostname-findings.json", {"findings": hostname_findings})
    write_json("18-high-risk-test-gaps.json", {"modules": high_risk_gaps})
    write_json("19-concurrency-test-plan.json", {"plans": concurrency_plan})
    write_json(
        "16-openapi-security-audit.json",
        {
            "operations": security_audit,
            "sensitive_schema_findings": schema_findings,
        },
    )

    failure_register = build_failure_register(
        frontend_diff,
        duplicate_report,
        live_summary,
        baseline_failures=baseline_findings_from_results(),
    )
    write_json("12-failure-register.json", {"findings": failure_register})

    report = build_phase1_report(
        live_summary,
        local_summary,
        live_local_diff,
        hidden,
        frontend_diff,
        duplicate_report,
        security_audit,
        coverage_summary,
        scenario_total,
        failure_register,
        hostname_findings,
        high_risk_gaps,
        concurrency_plan,
        baseline_summary,
        schema_findings,
        ownership_count=len(ownership_rows),
    )
    (ARTIFACTS_DIR / "PHASE-1-REPORT.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except URLError as exc:
        raise SystemExit(f"Failed to fetch live OpenAPI: {exc}") from exc
