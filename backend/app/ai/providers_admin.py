"""Provider profile CRUD for the AI Control Center."""

from __future__ import annotations

import os
import time
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.ai.feature_routing import (
    ensure_default_provider_profiles,
    invoke_config_for_profile,
)
from app.ai.models import AIFeatureRoute, AIProviderHealthCheck, AIProviderProfile
from app.ai.model_catalog import default_available_models
from app.ai.providers import StrictHTTPProvider, default_base_url_for_type
from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.core.encryption import decrypt_secret, encrypt_secret, secret_last4

ALLOWED_PROVIDER_TYPES = frozenset(
    {
        "openai_compatible",
        "openai",
        "anthropic",
        "gemini",
        "grok",
        "template_fallback",
    }
)


def _mask_key(profile: AIProviderProfile) -> dict[str, Any]:
    env_note = "API keys are currently managed by environment variables."
    if profile.provider_type == "template_fallback":
        return {
            "configured": True,
            "source": "local",
            "editable": False,
            "masked": "n/a",
            "last_four": None,
        }
    if profile.use_env_api_key:
        key = (get_settings().ai_api_key or "").strip()
        last4 = profile.api_key_last_four or (key[-4:] if len(key) >= 4 else None)
        return {
            "configured": bool(key),
            "source": "env",
            "editable": True,
            "masked": f"••••{last4}" if last4 else None,
            "last_four": last4,
            "note": env_note + " Or store an encrypted key on this profile instead.",
        }
    if profile.api_key_encrypted:
        return {
            "configured": True,
            "source": "db_encrypted",
            "editable": True,
            "masked": f"••••{profile.api_key_last_four or '****'}",
            "last_four": profile.api_key_last_four,
        }
    return {
        "configured": False,
        "source": "none",
        "editable": True,
        "masked": None,
        "last_four": None,
        "note": env_note + " You can paste a key below to store it encrypted on this profile.",
    }


def _apply_stored_api_key(profile: AIProviderProfile, plain: str) -> None:
    text = (plain or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="API key cannot be empty")
    try:
        profile.api_key_encrypted = encrypt_secret(text)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Server encryption is not configured. Set EMAIL_SETTINGS_ENCRYPTION_KEY "
                "in backend env before storing provider API keys."
            ),
        ) from exc
    profile.api_key_last_four = secret_last4(text)
    profile.use_env_api_key = False


def _clear_stored_api_key(profile: AIProviderProfile) -> None:
    profile.api_key_encrypted = None
    profile.api_key_last_four = None


def _profile_public(profile: AIProviderProfile) -> dict[str, Any]:
    key_status = _mask_key(profile)
    health = profile.health_status or "unknown"
    if profile.provider_type != "template_fallback" and not key_status["configured"]:
        if profile.is_enabled:
            health = "needs_configuration"
    if not profile.is_enabled:
        health = "disabled"
    return {
        "id": str(profile.id),
        "provider_type": profile.provider_type,
        "display_name": profile.display_name,
        "base_url": profile.base_url or default_base_url_for_type(profile.provider_type),
        "default_model": profile.default_model,
        "available_models": list(profile.available_models or []),
        "is_enabled": profile.is_enabled,
        "priority": profile.priority,
        "timeout_seconds": profile.timeout_seconds,
        "max_tokens_default": profile.max_tokens_default,
        "rate_limit_per_minute": profile.rate_limit_per_minute,
        "monthly_spend_limit_micros": profile.monthly_spend_limit_micros,
        "notes": profile.notes,
        "health_status": health,
        "api_key_status": key_status,
        "use_env_api_key": profile.use_env_api_key,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


def list_provider_profiles(db: Session) -> list[dict[str, Any]]:
    ensure_default_provider_profiles(db)
    rows = list(
        db.scalars(
            select(AIProviderProfile).order_by(
                AIProviderProfile.priority, AIProviderProfile.display_name
            )
        ).all()
    )
    return [_profile_public(r) for r in rows]


def create_provider_profile(
    db: Session,
    *,
    actor_user_id: UUID,
    provider_type: str,
    display_name: str,
    base_url: str | None = None,
    default_model: str | None = None,
    available_models: list[str] | None = None,
    is_enabled: bool = True,
    priority: int = 100,
    timeout_seconds: int = 30,
    max_tokens_default: int = 800,
    use_env_api_key: bool = False,
    notes: str | None = None,
    api_key: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    ptype = provider_type.strip().lower()
    if ptype not in ALLOWED_PROVIDER_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported provider type")
    if ptype == "template_fallback":
        use_env_api_key = False
    elif api_key and api_key.strip():
        use_env_api_key = False
    catalog = default_available_models(ptype)
    if not available_models:
        available_models = catalog
    if not default_model:
        default_model = catalog[0] if catalog else "gpt-4o-mini"
    row = AIProviderProfile(
        provider_type=ptype,
        display_name=display_name.strip(),
        base_url=base_url.strip() if base_url else default_base_url_for_type(ptype),
        default_model=default_model,
        available_models=available_models or catalog,
        is_enabled=is_enabled,
        priority=priority,
        timeout_seconds=timeout_seconds,
        max_tokens_default=max_tokens_default,
        use_env_api_key=use_env_api_key,
        health_status="unknown",
        notes=notes,
        created_by_user_id=actor_user_id,
        updated_by_user_id=actor_user_id,
    )
    db.add(row)
    db.flush()
    audit_fields = ["display_name", "provider_type"]
    if api_key and api_key.strip() and ptype != "template_fallback":
        _apply_stored_api_key(row, api_key)
        audit_fields.append("api_key_stored")
    write_audit_log(
        db,
        action="ai.providers.created",
        actor_user_id=actor_user_id,
        resource_type="ai_provider_profile",
        resource_id=str(row.id),
        details={"display_name": display_name, "provider_type": ptype, "fields": audit_fields},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(row)
    return _profile_public(row)


def update_provider_profile(
    db: Session,
    *,
    profile_id: UUID,
    actor_user_id: UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
    **fields: Any,
) -> dict[str, Any]:
    row = db.get(AIProviderProfile, profile_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    api_key = fields.pop("api_key", None)
    clear_api_key = fields.pop("clear_api_key", None)
    allowed = {
        "display_name",
        "base_url",
        "default_model",
        "available_models",
        "is_enabled",
        "priority",
        "timeout_seconds",
        "max_tokens_default",
        "rate_limit_per_minute",
        "monthly_spend_limit_micros",
        "notes",
        "use_env_api_key",
        "health_status",
    }
    for key, val in fields.items():
        if key not in allowed or val is None:
            continue
        setattr(row, key, val)
    audit_fields = [k for k in fields if k in allowed and fields.get(k) is not None]
    if row.provider_type != "template_fallback":
        if clear_api_key:
            _clear_stored_api_key(row)
            audit_fields.append("api_key_cleared")
        elif api_key is not None and str(api_key).strip():
            _apply_stored_api_key(row, str(api_key))
            audit_fields.append("api_key_rotated")
    row.updated_by_user_id = actor_user_id
    write_audit_log(
        db,
        action="ai.providers.updated",
        actor_user_id=actor_user_id,
        resource_type="ai_provider_profile",
        resource_id=str(row.id),
        details={"fields": audit_fields},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(row)
    return _profile_public(row)


def delete_provider_profile(
    db: Session,
    *,
    profile_id: UUID,
    actor_user_id: UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    row = db.get(AIProviderProfile, profile_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    if row.provider_type == "template_fallback":
        raise HTTPException(
            status_code=400,
            detail="The template fallback provider cannot be deleted.",
        )
    route_rows = list(
        db.scalars(
            select(AIFeatureRoute).where(
                or_(
                    AIFeatureRoute.primary_provider_id == profile_id,
                    AIFeatureRoute.fallback_provider_id == profile_id,
                )
            )
        ).all()
    )
    if route_rows:
        keys = sorted({r.feature_key for r in route_rows})
        raise HTTPException(
            status_code=409,
            detail=(
                "Provider is used by feature routing. Reassign or disable those "
                f"features first: {', '.join(keys[:8])}"
                + ("…" if len(keys) > 8 else "")
            ),
        )
    display_name = row.display_name
    db.delete(row)
    write_audit_log(
        db,
        action="ai.providers.deleted",
        actor_user_id=actor_user_id,
        resource_type="ai_provider_profile",
        resource_id=str(profile_id),
        details={"display_name": display_name},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()


def test_provider_profile(
    db: Session,
    *,
    profile_id: UUID,
    actor_user_id: UUID,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    row = db.get(AIProviderProfile, profile_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Provider profile not found")
    if not row.is_enabled:
        return {
            "ok": False,
            "status": "disabled",
            "message": "Provider is disabled",
            "provider_id": str(profile_id),
        }

    cfg = invoke_config_for_profile(
        row, model_override=row.default_model, max_tokens_override=64
    )
    started = time.perf_counter()
    comp = StrictHTTPProvider(cfg).complete(
        system_prompt="You are a health-check probe for Pàdéyá.",
        user_prompt="Reply with exactly: ok",
    )
    latency = int((time.perf_counter() - started) * 1000)
    ok = bool(comp.text) and not comp.error_message
    status_label = "healthy" if ok else "failing"
    if not _mask_key(row)["configured"] and row.provider_type != "template_fallback":
        status_label = "needs_configuration"
        ok = False
    row.health_status = status_label
    db.add(
        AIProviderHealthCheck(
            provider_id=row.id,
            status=status_label,
            latency_ms=latency,
            error_message_safe=(comp.error_message or "")[:300] or None,
            checked_by_user_id=actor_user_id,
        )
    )
    write_audit_log(
        db,
        action="ai.providers.test_connection",
        actor_user_id=actor_user_id,
        resource_type="ai_provider_profile",
        resource_id=str(row.id),
        details={"ok": ok, "status": status_label, "latency_ms": latency},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return {
        "ok": ok,
        "status": status_label,
        "message": comp.error_message or ("Provider responded" if ok else "Test failed"),
        "provider_id": str(profile_id),
        "display_name": row.display_name,
        "model": comp.model_name or row.default_model,
        "latency_ms": latency,
        "used_fallback": comp.used_fallback,
        "api_key_configured": _mask_key(row)["configured"],
    }


def env_api_key_banner() -> str:
    if (os.environ.get("AI_API_KEY") or get_settings().ai_api_key or "").strip():
        return "API keys are currently managed by environment variables."
    return (
        "API keys are currently managed by environment variables. "
        "Set AI_API_KEY on the server for network providers."
    )
