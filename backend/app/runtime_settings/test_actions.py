"""Safe, audited test actions for Admin Runtime Settings categories."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.config import get_settings
from app.runtime_settings.service import runtime_settings_service


def _audit_test(
    db: Session,
    *,
    category: str,
    actor_user_id: UUID | None,
    ok: bool,
    details: dict[str, Any],
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    # Never include secrets in details
    safe = {k: v for k, v in details.items() if "key" not in k.lower() or k.endswith("_configured")}
    write_audit_log(
        db,
        action="runtime_setting_tested",
        actor_user_id=actor_user_id,
        resource_type="runtime_setting",
        resource_id=category,
        details={
            "category": category,
            "action": "runtime_setting_tested",
            "ok": ok,
            **safe,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )


def test_category(
    db: Session,
    *,
    category: str,
    actor_user_id: UUID | None,
    actor_email: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    handlers = {
        "email": _test_email,
        "push": _test_push,
        "ai": _test_ai,
        "payments": _test_payments,
        "storage": _test_storage,
        "integrations": _test_integrations,
        "runtime": _test_noop_ok,
        "notifications": _test_noop_ok,
        "security-runtime": _test_noop_ok,
        "system-status": _test_system_status,
    }
    handler = handlers.get(category)
    if handler is None:
        result = {
            "ok": False,
            "category": category,
            "status": "not_available",
            "message": f"No test action for category '{category}'",
            "details": {},
        }
    else:
        result = handler(
            db,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
        )
        result.setdefault("category", category)

    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    _audit_test(
        db,
        category=category,
        actor_user_id=actor_user_id,
        ok=bool(result.get("ok")),
        details={
            "status": result.get("status"),
            "message": (result.get("message") or "")[:200],
            "latency_ms": result["latency_ms"],
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    return result


def _test_email(
    db: Session,
    *,
    actor_user_id: UUID | None,
    actor_email: str | None,
) -> dict[str, Any]:
    from app.email.settings_service import send_test_email, test_smtp_connection

    if not actor_email:
        conn = test_smtp_connection(db, actor_user_id=actor_user_id)
        return {
            "ok": bool(conn.get("ok")),
            "status": conn.get("status") or ("success" if conn.get("ok") else "failed"),
            "message": conn.get("error") or "SMTP connection tested (no admin email for send)",
            "details": {"mode": "connection"},
        }
    result = send_test_email(db, to=actor_email, actor_user_id=actor_user_id)
    return {
        "ok": bool(result.get("ok")),
        "status": result.get("status") or ("success" if result.get("ok") else "failed"),
        "message": result.get("error") or f"Test email sent to {actor_email}",
        "details": {
            "mode": "send",
            "provider": result.get("provider"),
            "skipped": result.get("skipped"),
        },
    }


def _test_push(
    db: Session,
    *,
    actor_user_id: UUID | None,
    actor_email: str | None,
) -> dict[str, Any]:
    from app.push.service import send_test_push
    from app.users.models import User

    if actor_user_id is None:
        return {
            "ok": False,
            "status": "needs_configuration",
            "message": "Admin user required for push test",
            "details": {},
        }
    user = db.get(User, actor_user_id)
    if user is None:
        return {
            "ok": False,
            "status": "failed",
            "message": "Admin user not found",
            "details": {},
        }
    try:
        result = send_test_push(db, user=user, actor_user_id=actor_user_id)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status": "failed",
            "message": str(exc)[:200],
            "details": {},
        }
    return {
        "ok": bool(result.get("ok")),
        "status": result.get("status") or ("success" if result.get("ok") else "failed"),
        "message": result.get("message") or "Push test completed",
        "details": {
            "has_active_device": result.get("has_active_device"),
            "provider": result.get("provider"),
            "active_subscription_count": result.get("active_subscription_count"),
        },
    }


def _test_ai(
    db: Session,
    *,
    actor_user_id: UUID | None,
    actor_email: str | None,
) -> dict[str, Any]:
    from app.ai.providers import get_ai_provider

    settings = get_settings()
    enabled = bool(
        runtime_settings_service.get_runtime_setting("ai_enabled", db=db, settings=settings)
    )
    if not enabled:
        return {
            "ok": False,
            "status": "disabled",
            "message": "AI is disabled",
            "details": {"ai_enabled": False},
        }
    provider_name = str(
        runtime_settings_service.get_runtime_setting("ai_provider", db=db, settings=settings)
        or "template"
    ).lower()
    if provider_name == "openai" and not (settings.ai_api_key or "").strip():
        return {
            "ok": False,
            "status": "needs_configuration",
            "message": "AI_API_KEY is not configured",
            "details": {"ai_api_key_configured": False, "provider": provider_name},
        }
    # Apply runtime overrides onto a shallow copy for provider selection
    provider = get_ai_provider(settings)
    started = time.perf_counter()
    result = provider.complete(
        system_prompt="You are a health-check probe for Pàdéyá.",
        user_prompt="Reply with exactly: ok",
    )
    latency = round((time.perf_counter() - started) * 1000, 2)
    return {
        "ok": bool(result.text),
        "status": "success" if result.text else "failed",
        "message": "AI provider responded" if result.text else (result.error_message or "empty"),
        "details": {
            "provider": result.provider,
            "model_name": result.model_name,
            "used_fallback": result.used_fallback,
            "latency_ms": latency,
            "ai_api_key_configured": bool((settings.ai_api_key or "").strip()),
        },
    }


def _test_payments(
    db: Session,
    *,
    actor_user_id: UUID | None,
    actor_email: str | None,
) -> dict[str, Any]:
    from app.payments.config import paystack_runtime

    cfg = paystack_runtime(db)
    secret = cfg.secret_configured
    webhook = bool(cfg.effective_webhook_secret.strip())
    public = cfg.public_configured
    ok = secret and webhook and public
    return {
        "ok": ok,
        "status": "success" if ok else "needs_configuration",
        "message": (
            f"Paystack {cfg.mode} keys present (no charge created)"
            if ok
            else f"Paystack {cfg.mode} keys missing — set test or live keys for the active mode"
        ),
        "details": {
            "paystack_mode": cfg.mode,
            "paystack_secret_configured": secret,
            "paystack_webhook_configured": webhook,
            "paystack_public_configured": public,
            "charge_attempted": False,
        },
    }


def _test_storage(
    db: Session,
    *,
    actor_user_id: UUID | None,
    actor_email: str | None,
) -> dict[str, Any]:
    settings = get_settings()
    provider = (settings.messaging_attachment_storage_provider or "local").strip().lower()
    if provider != "local":
        return {
            "ok": False,
            "status": "not_available",
            "message": f"Storage provider '{provider}' is not wired for live test",
            "details": {"provider": provider},
        }
    root = Path(settings.messaging_attachment_storage_root)
    if not root.is_absolute():
        root = Path.cwd() / root
    probe_dir = root / "_runtime_settings_probe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    name = f"probe-{uuid.uuid4().hex}.txt"
    path = probe_dir / name
    try:
        path.write_text("padeya-runtime-settings-probe", encoding="utf-8")
        read_back = path.read_text(encoding="utf-8")
        path.unlink(missing_ok=True)
        ok = read_back == "padeya-runtime-settings-probe"
        return {
            "ok": ok,
            "status": "success" if ok else "failed",
            "message": "Local storage write/read/delete ok" if ok else "Read mismatch",
            "details": {"provider": "local"},
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status": "failed",
            "message": str(exc)[:200],
            "details": {"provider": "local"},
        }
    finally:
        try:
            if path.exists():
                path.unlink()
        except Exception:  # noqa: BLE001
            pass


def _test_integrations(
    db: Session,
    *,
    actor_user_id: UUID | None,
    actor_email: str | None,
) -> dict[str, Any]:
    """Maps key status from runtime_settings; no live Google call in v1."""
    from app.events.geocode import google_places_api_key

    maps = bool(google_places_api_key(db))
    return {
        "ok": True,
        "status": "success" if maps else "not_configured",
        "message": (
            "Google Geocoding API key is configured in Admin → Integrations."
            if maps
            else "Google Geocoding API key is not configured (Admin → Integrations)."
        ),
        "details": {
            "maps_configured": maps,
            "recaptcha_configured": False,
            "deferred": False,
        },
    }


def _test_noop_ok(
    db: Session,
    *,
    actor_user_id: UUID | None,
    actor_email: str | None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "status": "success",
        "message": "No external integration test for this category",
        "details": {},
    }


def _test_system_status(
    db: Session,
    *,
    actor_user_id: UUID | None,
    actor_email: str | None,
) -> dict[str, Any]:
    status = runtime_settings_service.system_status(
        db, actor_user_id=actor_user_id, record_view_audit=False
    )
    return {
        "ok": True,
        "status": "success",
        "message": "System status snapshot collected",
        "details": {
            "environment": status.get("environment"),
            "redis": status.get("redis"),
            "configured": status.get("configured"),
        },
    }
