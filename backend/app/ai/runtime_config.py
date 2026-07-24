"""Resolve effective AI settings from env + runtime_settings DB overrides.

API key remains env-only (`AI_API_KEY`). Never return secrets from admin APIs.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings

AI_RUNTIME_KEYS = (
    "ai_enabled",
    "ai_provider",
    "ai_model",
    "ai_base_url",
    "ai_max_tokens",
    "ai_timeout_seconds",
    "ai_rate_limit_per_hour",
)

# OpenAI-compatible default bases when admin picks a named provider.
PROVIDER_DEFAULT_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "grok": "https://api.x.ai/v1",
}

NETWORK_PROVIDERS = frozenset({"openai", "anthropic", "gemini", "grok"})
ALLOWED_PROVIDERS = frozenset(
    {"template", "openai", "anthropic", "gemini", "grok", "none", "off", "disabled"}
)


def resolve_ai_settings(db: Session | None = None) -> Settings:
    """Return Settings with non-secret AI knobs overlaid from runtime_settings."""
    base = get_settings()
    if db is None:
        return base

    from app.runtime_settings.service import runtime_settings_service

    updates: dict = {}
    enabled = runtime_settings_service.get_runtime_setting(
        "ai_enabled", db=db, settings=base
    )
    if enabled is not None:
        updates["ai_enabled"] = bool(enabled)

    provider = runtime_settings_service.get_runtime_setting(
        "ai_provider", db=db, settings=base
    )
    if provider is not None:
        updates["ai_provider"] = str(provider).strip().lower() or base.ai_provider

    model = runtime_settings_service.get_runtime_setting(
        "ai_model", db=db, settings=base
    )
    if model is not None:
        updates["ai_model"] = str(model).strip() or base.ai_model

    base_url = runtime_settings_service.get_runtime_setting(
        "ai_base_url", db=db, settings=base
    )
    if base_url is not None:
        updates["ai_base_url"] = str(base_url).strip() or base.ai_base_url

    max_tokens = runtime_settings_service.get_runtime_setting(
        "ai_max_tokens", db=db, settings=base
    )
    if max_tokens is not None:
        try:
            updates["ai_max_tokens"] = int(max_tokens)
        except (TypeError, ValueError):
            pass

    timeout = runtime_settings_service.get_runtime_setting(
        "ai_timeout_seconds", db=db, settings=base
    )
    if timeout is not None:
        try:
            updates["ai_timeout_seconds"] = int(timeout)
        except (TypeError, ValueError):
            pass

    rate = runtime_settings_service.get_runtime_setting(
        "ai_rate_limit_per_hour", db=db, settings=base
    )
    if rate is not None:
        try:
            updates["ai_rate_limit_per_hour"] = int(rate)
        except (TypeError, ValueError):
            pass

    if not updates:
        return base
    return base.model_copy(update=updates)


def effective_base_url(settings: Settings) -> str:
    """Prefer configured base URL; else provider default for network providers."""
    configured = (settings.ai_base_url or "").strip()
    provider = (settings.ai_provider or "template").strip().lower()
    default_openai = PROVIDER_DEFAULT_BASE_URLS["openai"]
    if configured and configured.rstrip("/") != default_openai.rstrip("/"):
        return configured
    if configured and provider in {"openai", "template", "none"}:
        return configured
    return PROVIDER_DEFAULT_BASE_URLS.get(provider, configured or default_openai)
