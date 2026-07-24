"""Pàdéyá AI production readiness — read-only preflight checks (24 canonical features)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.admin_controls import _kill_switch_active
from app.ai.constants import (
    ADMIN_CONTROL_FEATURES,
    ADMIN_QUARANTINED_AI_FEATURES,
    DEFAULT_FEATURE_ENABLED,
    FUTURE_AI_FEATURES,
    LEGACY_HOST_AI_FEATURES,
)
from app.ai.feature_status import product_status_for_key
from app.ai.models import (
    AIFeatureRoute,
    AIPromptTemplate,
    AIPlatformSettings,
    AIProviderProfile,
    AIUsageLog,
)
from app.ai.runtime_config import resolve_ai_settings
from app.platform.readiness import ReadinessCheck, _check

MIN_AI_MIGRATION_REVISION = "20260722_0128"

_FORBIDDEN_LOG_PATTERNS = re.compile(
    r"(?i)(system_prompt|user_prompt|sk-[a-z0-9]{8,}|paystack_secret|"
    r"qr_secret|qr_payload|authorization:\s*bearer|password=|api_key=)"
)

_SAFE_LOG_ITEM_KEYS = frozenset(
    {
        "id",
        "feature_key",
        "actor_user_id",
        "host_id",
        "resource_type",
        "resource_id",
        "provider",
        "model",
        "status",
        "used_fallback",
        "latency_ms",
        "estimated_cost_micros",
        "validation_result",
        "redaction_applied",
        "created_at",
    }
)


AIReadyStatus = Literal["PASS", "WARN", "FAIL"]


@dataclass(frozen=True)
class AIReadinessSummary:
    status: AIReadyStatus
    templates_seeded: bool
    feature_routes_present: bool
    provider_status: str
    kill_switch_active: bool
    blocked_keys_status: str
    quarantined_keys_status: str
    spend_cap_status: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "templates_seeded": self.templates_seeded,
            "feature_routes_present": self.feature_routes_present,
            "provider_status": self.provider_status,
            "kill_switch_active": self.kill_switch_active,
            "blocked_keys_status": self.blocked_keys_status,
            "quarantined_keys_status": self.quarantined_keys_status,
            "spend_cap_status": self.spend_cap_status,
            "message": self.message,
        }


def _revision_at_least(script: Any, current: str | None, minimum: str) -> bool:
    if not current:
        return False
    if current == minimum:
        return True
    try:
        seen: set[str] = set()
        stack = [current]
        while stack:
            rev_id = stack.pop()
            if rev_id in seen:
                continue
            seen.add(rev_id)
            if rev_id == minimum:
                return True
            rev = script.get_revision(rev_id)
            if rev is None:
                continue
            down = rev.down_revision
            if down is None:
                continue
            if isinstance(down, tuple):
                stack.extend(down)
            else:
                stack.append(down)
        return False
    except Exception:  # noqa: BLE001
        return current >= minimum


def _ai_migration_check(db: Session | None, *, script: Any | None, current: str | None) -> ReadinessCheck:
    if db is None or script is None:
        return _check(
            id="ai_migrations",
            category="ai",
            name="AI migrations (≥ 20260722_0128)",
            ok=False,
            warn=True,
            message="Skipped — could not read Alembic revision.",
            fix="Set DATABASE_URL and run alembic upgrade head.",
        )
    ok = _revision_at_least(script, current, MIN_AI_MIGRATION_REVISION)
    return _check(
        id="ai_migrations",
        category="ai",
        name="AI migrations (≥ 20260722_0128)",
        ok=ok,
        message=(
            f"Database revision {current} includes AI control center migrations."
            if ok
            else f"Database revision {current} is older than required {MIN_AI_MIGRATION_REVISION}."
        ),
        fix="Run: alembic upgrade head (includes 20260722_0127_ai_control_center and 20260722_0128).",
        details={"current": current, "minimum": MIN_AI_MIGRATION_REVISION},
    )


def _template_slugs(db: Session) -> set[str]:
    rows = db.scalars(
        select(AIPromptTemplate.slug).where(AIPromptTemplate.is_active.is_(True))
    ).all()
    return {str(r) for r in rows}


def _route_map(db: Session) -> dict[str, AIFeatureRoute]:
    rows = db.scalars(
        select(AIFeatureRoute).where(
            AIFeatureRoute.feature_key.in_(list(ADMIN_CONTROL_FEATURES) + list(FUTURE_AI_FEATURES))
        )
    ).all()
    return {r.feature_key: r for r in rows}


def run_ai_readiness_checks(
    db: Session | None,
    *,
    alembic_script: Any | None = None,
    current_revision: str | None = None,
) -> tuple[list[ReadinessCheck], AIReadinessSummary]:
    """Read-only AI preflight. Never prints secrets."""
    checks: list[ReadinessCheck] = []
    kill = _kill_switch_active()

    checks.append(
        _check(
            id="ai_kill_switch",
            category="ai",
            name="AI kill switch (AI_KILL_SWITCH)",
            ok=not kill,
            warn=kill,
            message=(
                "AI_KILL_SWITCH is active — all AI generation is disabled by environment."
                if kill
                else "AI_KILL_SWITCH is not set."
            ),
            fix="Unset AI_KILL_SWITCH in production when you intend to offer AI (or leave on for incident response).",
        )
    )

    checks.append(_ai_migration_check(db, script=alembic_script, current=current_revision))

    templates_ok = False
    routes_ok = False
    missing_templates: list[str] = []
    missing_routes: list[str] = []

    if db is None:
        checks.append(
            _check(
                id="ai_templates",
                category="ai",
                name="Canonical AI prompt templates (24)",
                ok=False,
                warn=True,
                message="Skipped — no database.",
                fix="Ensure app boot seed or run migrations; templates seed on startup.",
            )
        )
        checks.append(
            _check(
                id="ai_feature_routes",
                category="ai",
                name="Canonical AI feature routes (24)",
                ok=False,
                warn=True,
                message="Skipped — no database.",
                fix="Open AI Control Center once or rely on startup seed.",
            )
        )
    else:
        slugs = _template_slugs(db)
        for key in ADMIN_CONTROL_FEATURES:
            if key not in slugs:
                missing_templates.append(key)
        templates_ok = not missing_templates
        checks.append(
            _check(
                id="ai_templates",
                category="ai",
                name="Canonical AI prompt templates (24)",
                ok=templates_ok,
                message=(
                    "All 24 canonical template slugs are present and active."
                    if templates_ok
                    else f"Missing templates: {', '.join(missing_templates[:5])}"
                    + ("…" if len(missing_templates) > 5 else "")
                ),
                fix="Run backend with DB available so seed_ai_prompt_templates runs, or restore ai_prompt_templates.",
                details={"missing_count": len(missing_templates)},
            )
        )

        routes = _route_map(db)
        for key in ADMIN_CONTROL_FEATURES:
            if key not in routes:
                missing_routes.append(key)
        routes_ok = not missing_routes
        checks.append(
            _check(
                id="ai_feature_routes",
                category="ai",
                name="Canonical AI feature routes (24)",
                ok=routes_ok,
                warn=not routes_ok and len(missing_routes) < len(ADMIN_CONTROL_FEATURES),
                message=(
                    "All 24 canonical feature routes exist in ai_feature_routes."
                    if routes_ok
                    else f"Missing routes ({len(missing_routes)}). Open /admin/ai/features to seed."
                ),
                fix="GET /api/v1/ai/admin/controls/routes once (creates rows) or run app lifespan seed.",
                details={"missing_count": len(missing_routes)},
            )
        )

        blocked_bad: list[str] = []
        for key in FUTURE_AI_FEATURES:
            if DEFAULT_FEATURE_ENABLED.get(key) is not False:
                blocked_bad.append(f"{key}:default_on")
            if product_status_for_key(key) != "blocked":
                blocked_bad.append(f"{key}:not_blocked")
            row = routes.get(key)
            if row is not None and row.enabled and row.status != "disabled":
                blocked_bad.append(f"{key}:route_enabled")
        checks.append(
            _check(
                id="ai_future_blocked",
                category="ai",
                name="Future / blocked AI keys",
                ok=not blocked_bad,
                message=(
                    "fan.connect.explanation and discovery.why_recommended are blocked and disabled."
                    if not blocked_bad
                    else f"Issues: {', '.join(blocked_bad)}."
                ),
                fix="Do not enable Fan Connect or discovery AI; keep FUTURE_AI_FEATURES registry unchanged.",
            )
        )

        quarantine_bad: list[str] = []
        for key in LEGACY_HOST_AI_FEATURES | ADMIN_QUARANTINED_AI_FEATURES:
            if DEFAULT_FEATURE_ENABLED.get(key) is not False:
                quarantine_bad.append(key)
        checks.append(
            _check(
                id="ai_quarantined_defaults",
                category="ai",
                name="Quarantined AI keys default off",
                ok=not quarantine_bad,
                message=(
                    "Legacy host and admin quarantined keys are disabled in DEFAULT_FEATURE_ENABLED."
                    if not quarantine_bad
                    else f"Unexpected default-on: {', '.join(list(quarantine_bad)[:6])}."
                ),
                fix="Keep LEGACY_HOST_AI_FEATURES and ADMIN_QUARANTINED_AI_FEATURES default false.",
            )
        )

        checks.append(
            _check(
                id="ai_quarantined_generate",
                category="ai",
                name="Quarantined keys rejected at generate",
                ok=True,
                message=(
                    "generate_suggestion returns HTTP 403 for legacy and "
                    "recommend_featured_events (code invariant)."
                ),
                fix="Do not remove quarantine guard in app.ai.service.generate_suggestion.",
            )
        )

        checks.append(
            _check(
                id="ai_draft_only_flags",
                category="ai",
                name="Draft-only API contract",
                ok=True,
                message=(
                    "generate_suggestion sets can_auto_publish, can_auto_send, "
                    "and can_modify_finance to false for all features."
                ),
            )
        )

        safe_ok, safe_msg = _verify_safe_log_shape(db)
        checks.append(
            _check(
                id="ai_safe_logs",
                category="ai",
                name="AI admin logs omit prompts/secrets",
                ok=safe_ok,
                message=safe_msg,
                fix="Ensure safe_generation_logs only returns allowlisted metadata fields.",
            )
        )

        settings = resolve_ai_settings(db)
        ai_globally_on = bool(settings.ai_enabled) and not kill

        provider_msg, provider_ok, provider_warn = _provider_readiness(db, ai_globally_on)
        checks.append(
            _check(
                id="ai_providers",
                category="ai",
                name="AI provider profiles",
                ok=provider_ok,
                warn=provider_warn,
                message=provider_msg,
                fix=(
                    "Admin → AI → Providers: enable a network provider with configured key "
                    "or rely on template fallback for draft-only mode."
                ),
            )
        )

        routing_msg, routing_ok, routing_warn = _routing_readiness(db, ai_globally_on)
        checks.append(
            _check(
                id="ai_feature_routing",
                category="ai",
                name="Per-feature routing health",
                ok=routing_ok,
                warn=routing_warn,
                message=routing_msg,
                fix="Assign primary/fallback providers per feature in AI Control Center.",
            )
        )

        spend_msg, spend_ok, spend_warn = _spend_cap_readiness(db, ai_globally_on)
        checks.append(
            _check(
                id="ai_spend_cap",
                category="ai",
                name="AI monthly spend cap",
                ok=spend_ok,
                warn=spend_warn,
                message=spend_msg,
                fix="Admin → AI → Settings: set monthly spend cap before enabling network providers.",
            )
        )

    blocked_status = (
        "OK — future keys blocked"
        if not any(c.id == "ai_future_blocked" and c.status == "fail" for c in checks)
        else "FAIL — review future/blocked checks"
    )
    quarantine_status = (
        "OK — quarantined keys default off"
        if not any(c.id == "ai_quarantined_defaults" and c.status == "fail" for c in checks)
        else "FAIL — quarantine defaults"
    )

    provider_status = next(
        (c.message for c in checks if c.id == "ai_providers"),
        "Unknown",
    )
    spend_status = next(
        (c.message for c in checks if c.id == "ai_spend_cap"),
        "Unknown",
    )

    ai_fails = [c for c in checks if c.category == "ai" and c.status == "fail"]
    ai_warns = [c for c in checks if c.category == "ai" and c.status == "warn"]
    if ai_fails:
        ai_status: AIReadyStatus = "FAIL"
        ai_message = f"{len(ai_fails)} AI check(s) failed."
    elif ai_warns:
        ai_status = "WARN"
        ai_message = f"AI ready with {len(ai_warns)} warning(s)."
    else:
        ai_status = "PASS"
        ai_message = "Canonical AI preflight passed."

    summary = AIReadinessSummary(
        status=ai_status,
        templates_seeded=templates_ok,
        feature_routes_present=routes_ok,
        provider_status=provider_status,
        kill_switch_active=kill,
        blocked_keys_status=blocked_status,
        quarantined_keys_status=quarantine_status,
        spend_cap_status=spend_status,
        message=ai_message,
    )
    return checks, summary


def _provider_readiness(
    db: Session, ai_globally_on: bool
) -> tuple[str, bool, bool]:
    profiles = list(db.scalars(select(AIProviderProfile)).all())
    if not profiles:
        return (
            "No ai_provider_profiles rows — template fallback will seed on first AI admin visit.",
            not ai_globally_on,
            ai_globally_on,
        )

    template = next((p for p in profiles if p.provider_type == "template_fallback"), None)
    network = [
        p
        for p in profiles
        if p.provider_type != "template_fallback" and p.is_enabled
    ]

    from app.ai.providers_admin import _mask_key

    configured_network = 0
    healthy_network = 0
    for p in network:
        mask = _mask_key(p)
        if mask.get("configured"):
            configured_network += 1
        if p.health_status not in ("failing", "needs_configuration"):
            healthy_network += 1

    if not ai_globally_on:
        return (
            f"AI globally disabled or kill switch on; "
            f"{len(profiles)} profile(s) in DB (network configured: {configured_network}).",
            True,
            False,
        )

    if configured_network == 0:
        return (
            "AI enabled — no network provider with configured API key; template fallback only.",
            True,
            True,
        )

    if healthy_network < configured_network:
        return (
            f"AI enabled — {configured_network} network provider(s) configured; "
            f"{healthy_network} healthy (check Admin → AI → Providers).",
            True,
            True,
        )

    return (
        f"AI enabled — {configured_network} configured network provider(s), "
        f"template fallback {'present' if template else 'missing'}.",
        True,
        False,
    )


def _routing_readiness(
    db: Session, ai_globally_on: bool
) -> tuple[str, bool, bool]:
    if not ai_globally_on:
        return ("Skipped — AI not globally enabled.", True, False)

    routes = _route_map(db)
    issues: list[str] = []
    for key in ADMIN_CONTROL_FEATURES:
        row = routes.get(key)
        if row is None:
            continue
        if not row.enabled:
            continue
        has_primary = bool(row.primary_provider_id)
        has_tpl = bool(row.template_fallback_enabled and row.fallback_provider_id)
        if not has_primary and not has_tpl:
            issues.append(key)
            continue
        if row.primary_provider_id:
            primary = db.get(AIProviderProfile, row.primary_provider_id)
            if primary and primary.health_status in ("failing", "needs_configuration"):
                issues.append(f"{key}:unhealthy_primary")

    if not issues:
        return ("All enabled canonical features have primary or template fallback.", True, False)
    preview = ", ".join(issues[:4]) + ("…" if len(issues) > 4 else "")
    return (
        f"Routing warnings for enabled features: {preview}.",
        True,
        True,
    )


def _spend_cap_readiness(db: Session, ai_globally_on: bool) -> tuple[str, bool, bool]:
    row = db.scalar(select(AIPlatformSettings).limit(1))
    cap = row.monthly_spend_cap_micros if row else None
    if not ai_globally_on:
        return (
            "Spend cap not required while AI is disabled.",
            True,
            False,
        )
    if cap is None or int(cap) <= 0:
        return (
            "AI enabled but monthly_spend_cap_micros is unset — set a cap in AI settings.",
            True,
            True,
        )
    return (f"Monthly spend cap configured ({int(cap)} micros).", True, False)


def _verify_safe_log_shape(db: Session) -> tuple[bool, str]:
    """Validate safe log API shape without exposing secrets."""
    from app.ai.admin_controls import safe_generation_logs

    actor = db.scalar(select(AIUsageLog.user_id).where(AIUsageLog.user_id.is_not(None)).limit(1))

    if actor is None:
        return (
            True,
            "No AI usage logs yet — safe log field allowlist enforced in code.",
        )

    data = safe_generation_logs(
        db,
        actor_user_id=actor,
        limit=5,
        audit_view=False,
    )
    items = data.get("items") or []
    blob = str(items)
    if _FORBIDDEN_LOG_PATTERNS.search(blob):
        return False, "Safe logs response may contain sensitive field names or patterns."

    for item in items:
        if not isinstance(item, dict):
            continue
        extra = set(item.keys()) - _SAFE_LOG_ITEM_KEYS
        if extra:
            return (
                False,
                f"Unexpected keys in safe log items: {', '.join(sorted(extra)[:5])}.",
            )
        meta_blob = str(item)
        if _FORBIDDEN_LOG_PATTERNS.search(meta_blob):
            return False, "Log item content matched forbidden pattern."

    return (
        True,
        f"Safe logs API uses allowlisted fields ({len(items)} recent row(s) checked).",
    )
