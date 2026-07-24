"""Admin AI controls: settings, feature toggles, spend, usage, test connection."""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from app.ai.constants import (
    ADMIN_CONTROL_FEATURES,
    DEFAULT_FEATURE_ENABLED,
    DEFAULT_FEATURE_PERMISSIONS,
    FEATURE_LABELS,
    feature_group,
)
from app.ai.models import AIFeatureConfig, AIPlatformSettings, AIUsageLog
from app.ai.providers import get_ai_provider
from app.ai.runtime_config import (
    ALLOWED_PROVIDERS,
    NETWORK_PROVIDERS,
    effective_base_url,
    resolve_ai_settings,
)
from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.runtime_settings.service import runtime_settings_service


def _kill_switch_active() -> bool:
    return (os.environ.get("AI_KILL_SWITCH") or "").strip() in {
        "1",
        "true",
        "TRUE",
        "yes",
    }


def _api_key_status() -> dict[str, Any]:
    settings = get_settings()
    key = (settings.ai_api_key or "").strip()
    configured = bool(key)
    last4 = key[-4:] if configured and len(key) >= 4 else None
    return {
        "configured": configured,
        "source": "env",
        "editable": False,
        "masked": f"••••{last4}" if last4 else None,
        "last_four": last4,
        "note": "AI_API_KEY is env-only and never returned in full.",
    }


def get_or_create_platform_settings(db: Session) -> AIPlatformSettings:
    row = db.scalar(select(AIPlatformSettings).limit(1))
    if row is None:
        row = AIPlatformSettings(
            monthly_spend_cap_micros=None,
            warning_threshold_pct=80,
            hard_stop_threshold_pct=100,
            hard_stop_enabled=True,
            allow_template_fallback_when_capped=True,
        )
        db.add(row)
        db.flush()
    return row


def get_or_create_feature_config(db: Session, feature_key: str) -> AIFeatureConfig:
    row = db.scalar(
        select(AIFeatureConfig).where(AIFeatureConfig.feature_key == feature_key)
    )
    if row is None:
        row = AIFeatureConfig(
            feature_key=feature_key,
            enabled=bool(DEFAULT_FEATURE_ENABLED.get(feature_key, False)),
            allowed_permissions=list(
                DEFAULT_FEATURE_PERMISSIONS.get(feature_key, [])
            ),
            daily_request_limit=None,
            monthly_request_limit=None,
            token_limit_per_request=None,
            requires_human_review=True,
            status="active",
        )
        db.add(row)
        db.flush()
    return row


def month_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.now(UTC)
    start = datetime(now.year, now.month, 1, tzinfo=UTC)
    if now.month == 12:
        end = datetime(now.year + 1, 1, 1, tzinfo=UTC)
    else:
        end = datetime(now.year, now.month + 1, 1, tzinfo=UTC)
    return start, end


def day_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.now(UTC)
    start = datetime(now.year, now.month, now.day, tzinfo=UTC)
    end = start + timedelta(days=1)
    return start, end


def _sum_cost_micros(db: Session, *, since: datetime, until: datetime | None = None) -> int:
    q = select(AIUsageLog.meta).where(AIUsageLog.created_at >= since)
    if until is not None:
        q = q.where(AIUsageLog.created_at < until)
    total = 0
    for meta in db.scalars(q).all():
        if not isinstance(meta, dict):
            continue
        val = meta.get("estimated_cost_micros")
        if val is None:
            continue
        try:
            total += int(val)
        except (TypeError, ValueError):
            continue
    return total


def spend_status(db: Session) -> dict[str, Any]:
    platform = get_or_create_platform_settings(db)
    start, end = month_window()
    spent = _sum_cost_micros(db, since=start, until=end)
    cap = platform.monthly_spend_cap_micros
    pct = None
    if cap is not None and cap > 0:
        pct = round((spent / cap) * 100, 2)
    warning = False
    hard_blocked = False
    if cap is not None and cap > 0 and pct is not None:
        warning = pct >= platform.warning_threshold_pct
        if platform.hard_stop_enabled and pct >= platform.hard_stop_threshold_pct:
            hard_blocked = True
    return {
        "monthly_spend_cap_micros": cap,
        "warning_threshold_pct": platform.warning_threshold_pct,
        "hard_stop_threshold_pct": platform.hard_stop_threshold_pct,
        "hard_stop_enabled": platform.hard_stop_enabled,
        "allow_template_fallback_when_capped": platform.allow_template_fallback_when_capped,
        "month_start": start.isoformat(),
        "spent_micros_this_month": spent,
        "spend_pct_of_cap": pct,
        "warning_reached": warning,
        "hard_blocked": hard_blocked,
    }


def assert_spend_allows_network(db: Session) -> dict[str, Any]:
    """If hard-blocked, raise unless template fallback is allowed (caller forces template)."""
    status_info = spend_status(db)
    if not status_info["hard_blocked"]:
        return status_info
    if status_info["allow_template_fallback_when_capped"]:
        return {**status_info, "force_template_fallback": True}
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Monthly AI spend cap reached. Template fallback is disabled.",
    )


def assert_feature_request_limits(db: Session, feature_key: str) -> None:
    from app.ai.feature_routing import get_or_create_feature_route

    route = get_or_create_feature_route(db, feature_key)
    daily_lim = route.daily_request_limit
    monthly_lim = route.monthly_request_limit
    if daily_lim is None or monthly_lim is None:
        cfg = get_or_create_feature_config(db, feature_key)
        if daily_lim is None:
            daily_lim = cfg.daily_request_limit
        if monthly_lim is None:
            monthly_lim = cfg.monthly_request_limit

    day_start, day_end = day_window()
    month_start, month_end = month_window()
    if daily_lim is not None and daily_lim >= 0:
        daily = int(
            db.scalar(
                select(func.count())
                .select_from(AIUsageLog)
                .where(
                    AIUsageLog.feature_key == feature_key,
                    AIUsageLog.created_at >= day_start,
                    AIUsageLog.created_at < day_end,
                )
            )
            or 0
        )
        if daily >= daily_lim:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily AI request limit reached for this feature.",
            )
    if monthly_lim is not None and monthly_lim >= 0:
        monthly = int(
            db.scalar(
                select(func.count())
                .select_from(AIUsageLog)
                .where(
                    AIUsageLog.feature_key == feature_key,
                    AIUsageLog.created_at >= month_start,
                    AIUsageLog.created_at < month_end,
                )
            )
            or 0
        )
        if monthly >= monthly_lim:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Monthly AI request limit reached for this feature.",
            )


def get_admin_overview(db: Session) -> dict[str, Any]:
    from app.ai.feature_routing import list_feature_routes_public
    from app.ai.providers_admin import list_provider_profiles

    settings = resolve_ai_settings(db)
    kill = _kill_switch_active()
    spend = spend_status(db)
    month_start, month_end = month_window()
    total_month = int(
        db.scalar(
            select(func.count())
            .select_from(AIUsageLog)
            .where(
                AIUsageLog.created_at >= month_start,
                AIUsageLog.created_at < month_end,
            )
        )
        or 0
    )
    success_month = int(
        db.scalar(
            select(func.count())
            .select_from(AIUsageLog)
            .where(
                AIUsageLog.created_at >= month_start,
                AIUsageLog.created_at < month_end,
                AIUsageLog.success.is_(True),
            )
        )
        or 0
    )
    dash = usage_dashboard(db)
    providers = list_provider_profiles(db)
    routes = list_feature_routes_public(db)
    enabled_providers = sum(1 for p in providers if p["is_enabled"])
    healthy_providers = sum(
        1 for p in providers if p["health_status"] in {"healthy", "unknown"}
    )
    enabled_features = sum(1 for r in routes if r["enabled"] and not r.get("future"))
    routing_issues = sum(
        1
        for r in routes
        if r["enabled"]
        and not r.get("future")
        and not r.get("primary_provider_id")
    )
    return {
        "brand": "Pàdéyá",
        "global_ai": {
            "enabled": bool(settings.ai_enabled) and not kill,
            "ai_enabled_setting": bool(settings.ai_enabled),
            "kill_switch": kill,
            "disabled_by_environment": kill,
            "status_label": (
                "Disabled by environment"
                if kill
                else ("Enabled" if settings.ai_enabled else "Disabled")
            ),
            "can_override_kill_switch": False,
        },
        "provider": {
            "provider": settings.ai_provider,
            "model": settings.ai_model,
            "base_url": effective_base_url(settings),
            "allowed_providers": sorted(
                p for p in ALLOWED_PROVIDERS if p not in {"off", "disabled"}
            ),
        },
        "api_key": _api_key_status(),
        "spend": spend,
        "rate_limit_per_hour": settings.ai_rate_limit_per_hour,
        "control_center": {
            "providers_configured": len(providers),
            "providers_enabled": enabled_providers,
            "providers_healthy": healthy_providers,
            "features_enabled": enabled_features,
            "routing_gaps": routing_issues,
            "requests_this_month": total_month,
            "success_rate_pct": round((success_month / total_month) * 100, 2)
            if total_month
            else None,
            "estimated_cost_micros": dash.get("estimated_cost_micros"),
            "average_latency_ms": dash.get("average_latency_ms"),
            "validation_failures": dash.get("validation_failures"),
            "redaction_applied_count": dash.get("redaction_applied_count"),
            "fallback_usage": dash.get("fallback_usage"),
            "recent_failure_count": dash.get("failure_count"),
        },
    }


def update_global_settings(
    db: Session,
    *,
    actor_user_id: UUID,
    enabled: bool | None = None,
    provider: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    if _kill_switch_active() and enabled is True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI is disabled by environment (AI_KILL_SWITCH). Cannot enable from UI.",
        )

    if enabled is not None:
        runtime_settings_service.upsert(
            db,
            category="ai",
            key="ai_enabled",
            value=bool(enabled),
            actor_user_id=actor_user_id,
            reason="AI admin controls global switch",
            ip_address=ip_address,
            user_agent=user_agent,
            commit=False,
        )
        write_audit_log(
            db,
            action="ai.settings.global_toggle",
            actor_user_id=actor_user_id,
            resource_type="ai_settings",
            resource_id="global",
            details={"enabled": bool(enabled), "kill_switch": _kill_switch_active()},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    if provider is not None:
        p = provider.strip().lower()
        if p not in ALLOWED_PROVIDERS:
            raise HTTPException(status_code=400, detail=f"Unsupported provider: {p}")
        runtime_settings_service.upsert(
            db,
            category="ai",
            key="ai_provider",
            value=p,
            actor_user_id=actor_user_id,
            reason="AI admin controls provider",
            ip_address=ip_address,
            user_agent=user_agent,
            commit=False,
        )
        write_audit_log(
            db,
            action="ai.settings.provider_changed",
            actor_user_id=actor_user_id,
            resource_type="ai_settings",
            resource_id="provider",
            details={"provider": p},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    if model is not None:
        m = model.strip()
        if not m:
            raise HTTPException(status_code=400, detail="Model cannot be empty")
        runtime_settings_service.upsert(
            db,
            category="ai",
            key="ai_model",
            value=m,
            actor_user_id=actor_user_id,
            reason="AI admin controls model",
            ip_address=ip_address,
            user_agent=user_agent,
            commit=False,
        )
        write_audit_log(
            db,
            action="ai.settings.model_changed",
            actor_user_id=actor_user_id,
            resource_type="ai_settings",
            resource_id="model",
            details={"model": m},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    if base_url is not None:
        url = base_url.strip()
        runtime_settings_service.upsert(
            db,
            category="ai",
            key="ai_base_url",
            value=url,
            actor_user_id=actor_user_id,
            reason="AI admin controls base URL",
            ip_address=ip_address,
            user_agent=user_agent,
            commit=False,
        )
        write_audit_log(
            db,
            action="ai.settings.base_url_changed",
            actor_user_id=actor_user_id,
            resource_type="ai_settings",
            resource_id="base_url",
            details={"base_url": url},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    db.commit()
    return get_admin_overview(db)


def update_spend_settings(
    db: Session,
    *,
    actor_user_id: UUID,
    monthly_spend_cap_micros: int | None = ...,  # type: ignore[assignment]
    warning_threshold_pct: int | None = None,
    hard_stop_threshold_pct: int | None = None,
    hard_stop_enabled: bool | None = None,
    allow_template_fallback_when_capped: bool | None = None,
    clear_cap: bool = False,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    row = get_or_create_platform_settings(db)
    before = {
        "monthly_spend_cap_micros": row.monthly_spend_cap_micros,
        "warning_threshold_pct": row.warning_threshold_pct,
        "hard_stop_threshold_pct": row.hard_stop_threshold_pct,
        "hard_stop_enabled": row.hard_stop_enabled,
        "allow_template_fallback_when_capped": row.allow_template_fallback_when_capped,
    }
    if clear_cap:
        row.monthly_spend_cap_micros = None
    elif monthly_spend_cap_micros is not ...:
        if monthly_spend_cap_micros is not None and monthly_spend_cap_micros < 0:
            raise HTTPException(status_code=400, detail="Spend cap must be >= 0")
        row.monthly_spend_cap_micros = monthly_spend_cap_micros
    if warning_threshold_pct is not None:
        if not 1 <= warning_threshold_pct <= 100:
            raise HTTPException(status_code=400, detail="warning_threshold_pct 1–100")
        row.warning_threshold_pct = warning_threshold_pct
    if hard_stop_threshold_pct is not None:
        if not 1 <= hard_stop_threshold_pct <= 100:
            raise HTTPException(status_code=400, detail="hard_stop_threshold_pct 1–100")
        row.hard_stop_threshold_pct = hard_stop_threshold_pct
    if hard_stop_enabled is not None:
        row.hard_stop_enabled = hard_stop_enabled
    if allow_template_fallback_when_capped is not None:
        row.allow_template_fallback_when_capped = allow_template_fallback_when_capped
    row.updated_by_user_id = actor_user_id
    write_audit_log(
        db,
        action="ai.settings.spend_cap_changed",
        actor_user_id=actor_user_id,
        resource_type="ai_platform_settings",
        resource_id=str(row.id),
        details={"before": before, "after": {
            "monthly_spend_cap_micros": row.monthly_spend_cap_micros,
            "warning_threshold_pct": row.warning_threshold_pct,
            "hard_stop_threshold_pct": row.hard_stop_threshold_pct,
            "hard_stop_enabled": row.hard_stop_enabled,
            "allow_template_fallback_when_capped": row.allow_template_fallback_when_capped,
        }},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return spend_status(db)


def list_feature_configs(db: Session) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key in ADMIN_CONTROL_FEATURES:
        cfg = get_or_create_feature_config(db, key)
        env_disabled = key in {
            p.strip()
            for p in (os.environ.get("AI_DISABLED_FEATURES") or "").split(",")
            if p.strip()
        }
        items.append(
            {
                "feature_key": key,
                "label": FEATURE_LABELS.get(key, key),
                "group": feature_group(key),
                "enabled": bool(cfg.enabled) and not env_disabled,
                "enabled_in_db": bool(cfg.enabled),
                "env_disabled": env_disabled,
                "allowed_permissions": list(cfg.allowed_permissions or []),
                "daily_request_limit": cfg.daily_request_limit,
                "monthly_request_limit": cfg.monthly_request_limit,
                "token_limit_per_request": cfg.token_limit_per_request,
                "requires_human_review": bool(cfg.requires_human_review),
                "status": cfg.status,
                "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None,
            }
        )
    db.commit()  # persist newly created defaults
    return items


def update_feature_config(
    db: Session,
    *,
    feature_key: str,
    actor_user_id: UUID,
    enabled: bool | None = None,
    allowed_permissions: list[str] | None = None,
    daily_request_limit: int | None = ...,  # type: ignore[assignment]
    monthly_request_limit: int | None = ...,  # type: ignore[assignment]
    token_limit_per_request: int | None = ...,  # type: ignore[assignment]
    requires_human_review: bool | None = None,
    status_value: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    if feature_key not in ADMIN_CONTROL_FEATURES:
        raise HTTPException(status_code=404, detail="Unknown AI feature key")
    cfg = get_or_create_feature_config(db, feature_key)
    before = {
        "enabled": cfg.enabled,
        "allowed_permissions": list(cfg.allowed_permissions or []),
        "daily_request_limit": cfg.daily_request_limit,
        "monthly_request_limit": cfg.monthly_request_limit,
        "token_limit_per_request": cfg.token_limit_per_request,
        "requires_human_review": cfg.requires_human_review,
        "status": cfg.status,
    }
    if enabled is not None:
        cfg.enabled = enabled
    if allowed_permissions is not None:
        cfg.allowed_permissions = [str(p).strip() for p in allowed_permissions if str(p).strip()]
    if daily_request_limit is not ...:
        cfg.daily_request_limit = daily_request_limit
    if monthly_request_limit is not ...:
        cfg.monthly_request_limit = monthly_request_limit
    if token_limit_per_request is not ...:
        cfg.token_limit_per_request = token_limit_per_request
    if requires_human_review is not None:
        cfg.requires_human_review = requires_human_review
    if status_value is not None:
        if status_value not in {"active", "disabled", "deprecated"}:
            raise HTTPException(status_code=400, detail="Invalid status")
        cfg.status = status_value
        if status_value == "disabled":
            cfg.enabled = False
    cfg.updated_by_user_id = actor_user_id
    write_audit_log(
        db,
        action="ai.features.updated",
        actor_user_id=actor_user_id,
        resource_type="ai_feature_config",
        resource_id=feature_key,
        details={"before": before, "after": {
            "enabled": cfg.enabled,
            "allowed_permissions": list(cfg.allowed_permissions or []),
            "daily_request_limit": cfg.daily_request_limit,
            "monthly_request_limit": cfg.monthly_request_limit,
            "token_limit_per_request": cfg.token_limit_per_request,
            "requires_human_review": cfg.requires_human_review,
            "status": cfg.status,
        }},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return next(i for i in list_feature_configs(db) if i["feature_key"] == feature_key)


def test_connection(
    db: Session,
    *,
    actor_user_id: UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    if _kill_switch_active():
        result = {
            "ok": False,
            "status": "disabled_by_environment",
            "message": "AI is disabled by environment (AI_KILL_SWITCH)",
            "provider": None,
            "model": None,
            "used_fallback": False,
            "latency_ms": None,
            "api_key_configured": _api_key_status()["configured"],
        }
        write_audit_log(
            db,
            action="ai.settings.test_connection",
            actor_user_id=actor_user_id,
            resource_type="ai_settings",
            resource_id="test_connection",
            details={k: v for k, v in result.items() if k != "message"},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.commit()
        return result

    settings = resolve_ai_settings(db)
    # Apply effective base URL for network providers
    settings = settings.model_copy(
        update={"ai_base_url": effective_base_url(settings)}
    )
    provider_name = (settings.ai_provider or "template").strip().lower()
    if provider_name in NETWORK_PROVIDERS and not (settings.ai_api_key or "").strip():
        result = {
            "ok": False,
            "status": "needs_configuration",
            "message": "AI_API_KEY is not configured (env-only)",
            "provider": provider_name,
            "model": settings.ai_model,
            "used_fallback": False,
            "latency_ms": None,
            "api_key_configured": False,
        }
    else:
        provider = get_ai_provider(settings)
        started = time.perf_counter()
        completion = provider.complete(
            system_prompt="You are a health-check probe for Pàdéyá.",
            user_prompt="Reply with exactly: ok",
        )
        latency = round((time.perf_counter() - started) * 1000, 2)
        ok = bool(completion.text) and not (
            provider_name in NETWORK_PROVIDERS and completion.used_fallback
            and completion.error_message
        )
        # Template provider success is OK
        if provider_name in {"template", "none"}:
            ok = bool(completion.text)
        result = {
            "ok": ok,
            "status": "success" if ok else "failed",
            "message": (
                "AI provider responded"
                if ok
                else (completion.error_message or "Provider test failed")
            )[:300],
            "provider": completion.provider,
            "model": completion.model_name or settings.ai_model,
            "used_fallback": bool(completion.used_fallback),
            "latency_ms": latency,
            "api_key_configured": _api_key_status()["configured"],
        }

    write_audit_log(
        db,
        action="ai.settings.test_connection",
        actor_user_id=actor_user_id,
        resource_type="ai_settings",
        resource_id="test_connection",
        details={
            "ok": result["ok"],
            "status": result["status"],
            "provider": result.get("provider"),
            "model": result.get("model"),
            "used_fallback": result.get("used_fallback"),
            "latency_ms": result.get("latency_ms"),
            "api_key_configured": result.get("api_key_configured"),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return result


def _parse_date(value: str | None, *, end: bool = False) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    try:
        if len(raw) == 10:
            dt = datetime.fromisoformat(raw).replace(tzinfo=UTC)
            if end:
                return dt + timedelta(days=1)
            return dt
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date: {value}") from exc


def usage_dashboard(
    db: Session,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    since = _parse_date(date_from) or (datetime.now(UTC) - timedelta(days=30))
    until = _parse_date(date_to, end=True)

    filters = [AIUsageLog.created_at >= since]
    if until is not None:
        filters.append(AIUsageLog.created_at < until)

    def _base() -> Select[Any]:
        return select(AIUsageLog).where(and_(*filters))

    total = int(
        db.scalar(select(func.count()).select_from(AIUsageLog).where(and_(*filters)))
        or 0
    )
    success_n = int(
        db.scalar(
            select(func.count())
            .select_from(AIUsageLog)
            .where(and_(*filters, AIUsageLog.success.is_(True)))
        )
        or 0
    )
    failure_n = total - success_n
    fallback_n = int(
        db.scalar(
            select(func.count())
            .select_from(AIUsageLog)
            .where(and_(*filters, AIUsageLog.used_fallback.is_(True)))
        )
        or 0
    )

    logs = list(db.scalars(_base()).all())
    cost_total = 0
    latency_sum = 0
    latency_n = 0
    validation_failures = 0
    redaction_n = 0
    by_feature: dict[str, dict[str, Any]] = {}
    by_provider: dict[str, dict[str, Any]] = {}
    by_user: dict[str, int] = {}
    by_host: dict[str, int] = {}

    for log in logs:
        meta = log.meta if isinstance(log.meta, dict) else {}
        c = meta.get("estimated_cost_micros")
        if c is not None:
            try:
                cost_total += int(c)
            except (TypeError, ValueError):
                pass
        lat = meta.get("latency_ms")
        if lat is not None:
            try:
                latency_sum += int(lat)
                latency_n += 1
            except (TypeError, ValueError):
                pass
        if meta.get("validation_failed") or meta.get("validation_result") == "failed":
            validation_failures += 1
        if meta.get("redaction_applied"):
            redaction_n += 1

        feat = by_feature.setdefault(
            log.feature_key,
            {"feature_key": log.feature_key, "requests": 0, "success": 0, "cost_micros": 0},
        )
        feat["requests"] += 1
        if log.success:
            feat["success"] += 1
        if c is not None:
            try:
                feat["cost_micros"] += int(c)
            except (TypeError, ValueError):
                pass

        pkey = f"{log.provider}|{log.model_name or '-'}"
        prov = by_provider.setdefault(
            pkey,
            {
                "provider": log.provider,
                "model": log.model_name,
                "requests": 0,
                "success": 0,
                "cost_micros": 0,
            },
        )
        prov["requests"] += 1
        if log.success:
            prov["success"] += 1
        if c is not None:
            try:
                prov["cost_micros"] += int(c)
            except (TypeError, ValueError):
                pass

        if log.user_id:
            uid = str(log.user_id)
            by_user[uid] = by_user.get(uid, 0) + 1
        if log.host_id:
            hid = str(log.host_id)
            by_host[hid] = by_host.get(hid, 0) + 1

    top_users = sorted(
        [{"user_id": k, "requests": v} for k, v in by_user.items()],
        key=lambda x: x["requests"],
        reverse=True,
    )[:20]
    top_hosts = sorted(
        [{"host_id": k, "requests": v} for k, v in by_host.items()],
        key=lambda x: x["requests"],
        reverse=True,
    )[:20]

    return {
        "date_from": since.isoformat(),
        "date_to": until.isoformat() if until else None,
        "total_requests": total,
        "success_count": success_n,
        "failure_count": failure_n,
        "success_rate": round((success_n / total) * 100, 2) if total else None,
        "estimated_cost_micros": cost_total,
        "average_latency_ms": round(latency_sum / latency_n, 2) if latency_n else None,
        "validation_failures": validation_failures,
        "redaction_applied_count": redaction_n,
        "fallback_usage": fallback_n,
        "by_feature": sorted(by_feature.values(), key=lambda x: x["requests"], reverse=True),
        "by_provider_model": sorted(
            by_provider.values(), key=lambda x: x["requests"], reverse=True
        ),
        "top_users": top_users,
        "top_hosts": top_hosts,
        "spend": spend_status(db),
    }


def safe_generation_logs(
    db: Session,
    *,
    actor_user_id: UUID,
    limit: int = 50,
    offset: int = 0,
    feature_key: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    audit_view: bool = True,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    since = _parse_date(date_from)
    until = _parse_date(date_to, end=True)
    filters = []
    if since is not None:
        filters.append(AIUsageLog.created_at >= since)
    if until is not None:
        filters.append(AIUsageLog.created_at < until)
    if feature_key:
        filters.append(AIUsageLog.feature_key == feature_key.strip())

    q = select(AIUsageLog)
    if filters:
        q = q.where(and_(*filters))
    q = q.order_by(AIUsageLog.created_at.desc()).offset(max(0, offset)).limit(
        min(max(1, limit), 200)
    )
    rows = list(db.scalars(q).all())
    items = []
    for log in rows:
        meta = log.meta if isinstance(log.meta, dict) else {}
        items.append(
            {
                "id": str(log.id),
                "feature_key": log.feature_key,
                "actor_user_id": str(log.user_id) if log.user_id else None,
                "host_id": str(log.host_id) if log.host_id else None,
                "resource_type": meta.get("audience") or meta.get("resource_scope"),
                "resource_id": (
                    meta.get("event_id")
                    or meta.get("merch_product_id")
                    or meta.get("support_ticket_id")
                    or meta.get("blog_post_id")
                ),
                "provider": log.provider,
                "model": log.model_name,
                "status": "success" if log.success else "failed",
                "used_fallback": log.used_fallback,
                "latency_ms": meta.get("latency_ms"),
                "estimated_cost_micros": meta.get("estimated_cost_micros"),
                "validation_result": meta.get("validation_result"),
                "redaction_applied": bool(meta.get("redaction_applied")),
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
        )

    if audit_view:
        write_audit_log(
            db,
            action="ai.logs.viewed",
            actor_user_id=actor_user_id,
            resource_type="ai_usage_logs",
            resource_id="list",
            details={
                "count": len(items),
                "feature_key": feature_key,
                "date_from": date_from,
                "date_to": date_to,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.commit()

    return {"items": items, "limit": limit, "offset": offset}
