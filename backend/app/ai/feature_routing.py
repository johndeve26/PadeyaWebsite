"""Feature-level provider routing with fallback chains."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.constants import (
    ADMIN_CONTROL_FEATURES,
    DEFAULT_FEATURE_ENABLED,
    FEATURE_HOST_ANNOUNCEMENTS_DRAFT,
    FEATURE_HOST_SPONSORSHIP_PITCH,
    FEATURE_FAN_PASSPORT_BIO,
    FEATURE_PLATFORM_ASSISTANT_CHAT,
    DEFAULT_FEATURE_PERMISSIONS,
    FEATURE_LABELS,
    FUTURE_AI_FEATURES,
    HIGH_RISK_HUMAN_REVIEW_LOCKED,
    feature_group,
)
from app.ai.model_catalog import (
    default_available_models,
    model_selection_label,
    models_to_try_for_profile,
)
from app.ai.feature_status import enrich_route_row, load_active_template_slugs
from app.ai.models import AIFeatureConfig, AIFeatureRoute, AIProviderProfile, AIUsageLog
from app.ai.providers import (
    ProviderInvokeConfig,
    StrictHTTPProvider,
    TemplateFallbackProvider,
    default_base_url_for_type,
)
from app.ai.runtime_config import effective_base_url, resolve_ai_settings
from app.core.config import get_settings
from app.core.encryption import decrypt_secret
from app.ai.providers import AICompletion, get_ai_provider

logger = logging.getLogger("padeya.ai.routing")


@dataclass
class RoutedCompletion:
    result: AICompletion
    chain: list[str]
    used_template_fallback: bool
    primary_failed: bool
    fallback_failed: bool


def sync_env_network_provider(db: Session) -> AIProviderProfile | None:
    """Ensure a network profile exists when AI_API_KEY is set (prod deploys often add key later)."""
    env_key = (get_settings().ai_api_key or "").strip()
    if not env_key:
        return None
    settings = resolve_ai_settings(db)
    row = db.scalar(
        select(AIProviderProfile)
        .where(AIProviderProfile.use_env_api_key.is_(True))
        .limit(1)
    )
    ptype = (settings.ai_provider or "openai").strip().lower()
    if ptype in {"template", "none", "off", "disabled"}:
        ptype = "openai"
    model = settings.ai_model or default_available_models(ptype)[0]
    if row is None:
        row = AIProviderProfile(
            provider_type=ptype,
            display_name="Environment default (AI_API_KEY)",
            base_url=effective_base_url(settings),
            use_env_api_key=True,
            api_key_last_four=env_key[-4:] if len(env_key) >= 4 else None,
            default_model=model,
            available_models=default_available_models(ptype),
            is_enabled=True,
            health_status="unknown",
            priority=10,
            timeout_seconds=settings.ai_timeout_seconds,
            max_tokens_default=settings.ai_max_tokens,
            notes="API key from AI_API_KEY env var (read-only in UI).",
        )
        db.add(row)
        db.flush()
        return row
    row.is_enabled = True
    row.provider_type = ptype
    row.base_url = effective_base_url(settings)
    row.default_model = model
    row.available_models = default_available_models(ptype)
    row.api_key_last_four = env_key[-4:] if len(env_key) >= 4 else row.api_key_last_four
    return row


def repair_route_primary_provider(db: Session, route: AIFeatureRoute) -> None:
    """Point feature routes at a network provider when primary was template-only."""
    net = sync_env_network_provider(db)
    if net is None:
        networks = list(
            db.scalars(
                select(AIProviderProfile)
                .where(
                    AIProviderProfile.provider_type != "template_fallback",
                    AIProviderProfile.is_enabled.is_(True),
                )
                .order_by(AIProviderProfile.priority.asc())
            ).all()
        )
        net = networks[0] if networks else None
    if net is None:
        return
    primary = (
        db.get(AIProviderProfile, route.primary_provider_id)
        if route.primary_provider_id
        else None
    )
    if primary is None or primary.provider_type == "template_fallback":
        route.primary_provider_id = net.id
    template = db.scalar(
        select(AIProviderProfile)
        .where(AIProviderProfile.provider_type == "template_fallback")
        .limit(1)
    )
    if template is not None and route.fallback_provider_id is None:
        route.fallback_provider_id = template.id
    db.flush()


def ensure_default_provider_profiles(db: Session) -> list[AIProviderProfile]:
    """Seed template + optional env-backed profile when none exist."""
    existing = list(db.scalars(select(AIProviderProfile)).all())
    if existing:
        sync_env_network_provider(db)
        return list(db.scalars(select(AIProviderProfile)).all())

    template = AIProviderProfile(
        provider_type="template_fallback",
        display_name="Pàdéyá template fallback",
        base_url=None,
        default_model="template-v1",
        available_models=["template-v1"],
        is_enabled=True,
        health_status="healthy",
        priority=1000,
        timeout_seconds=5,
        max_tokens_default=800,
        notes="Deterministic local drafts when network providers fail.",
    )
    db.add(template)
    db.flush()

    settings = resolve_ai_settings(db)
    env_key = (get_settings().ai_api_key or "").strip()
    if env_key:
        net = AIProviderProfile(
            provider_type=settings.ai_provider or "openai",
            display_name="Environment default (AI_API_KEY)",
            base_url=effective_base_url(settings),
            use_env_api_key=True,
            api_key_last_four=env_key[-4:] if len(env_key) >= 4 else None,
            default_model=settings.ai_model or default_available_models(settings.ai_provider or "openai")[0],
            available_models=default_available_models(settings.ai_provider or "openai"),
            is_enabled=True,
            health_status="unknown",
            priority=10,
            timeout_seconds=settings.ai_timeout_seconds,
            max_tokens_default=settings.ai_max_tokens,
            notes="API key from AI_API_KEY env var (read-only in UI).",
        )
        db.add(net)
        db.flush()

    db.commit()
    return list(db.scalars(select(AIProviderProfile)).all())


def get_or_create_feature_route(db: Session, feature_key: str) -> AIFeatureRoute:
    row = db.scalar(
        select(AIFeatureRoute).where(AIFeatureRoute.feature_key == feature_key)
    )
    if row is not None:
        if (
            feature_key not in FUTURE_AI_FEATURES
            and feature_key in ADMIN_CONTROL_FEATURES
            and row.status == "disabled"
        ):
            row.status = "active"
            if feature_key in (
                FEATURE_HOST_ANNOUNCEMENTS_DRAFT,
                FEATURE_HOST_SPONSORSHIP_PITCH,
                FEATURE_FAN_PASSPORT_BIO,
            ):
                row.enabled = bool(DEFAULT_FEATURE_ENABLED.get(feature_key, True))
                row.requires_human_review = True
        repair_route_primary_provider(db, row)
        return row

    cfg = db.scalar(
        select(AIFeatureConfig).where(AIFeatureConfig.feature_key == feature_key)
    )
    enabled_default = bool(DEFAULT_FEATURE_ENABLED.get(feature_key, False))
    if feature_key in FUTURE_AI_FEATURES:
        enabled_default = False

    profiles = ensure_default_provider_profiles(db)
    template_profile = next(
        (p for p in profiles if p.provider_type == "template_fallback"),
        profiles[0] if profiles else None,
    )
    primary = next(
        (p for p in profiles if p.provider_type != "template_fallback"),
        template_profile,
    )

    row = AIFeatureRoute(
        feature_key=feature_key,
        enabled=cfg.enabled if cfg else enabled_default,
        primary_provider_id=primary.id if primary else None,
        primary_model=None,
        fallback_provider_id=template_profile.id if template_profile else None,
        fallback_model=None,
        template_fallback_enabled=True,
        daily_request_limit=cfg.daily_request_limit if cfg else None,
        monthly_request_limit=cfg.monthly_request_limit if cfg else None,
        max_tokens=cfg.token_limit_per_request if cfg else None,
        requires_human_review=feature_key != FEATURE_PLATFORM_ASSISTANT_CHAT,
        allowed_permissions=list(
            (cfg.allowed_permissions if cfg else None)
            or DEFAULT_FEATURE_PERMISSIONS.get(feature_key, [])
        ),
        status="disabled" if feature_key in FUTURE_AI_FEATURES else "active",
    )
    db.add(row)
    db.flush()
    repair_route_primary_provider(db, row)
    return row


def _resolve_api_key(profile: AIProviderProfile) -> str | None:
    if profile.provider_type == "template_fallback":
        return None
    if profile.use_env_api_key:
        key = (get_settings().ai_api_key or "").strip()
        return key or None
    if profile.api_key_encrypted:
        try:
            key = decrypt_secret(profile.api_key_encrypted).strip()
            if key:
                return key
        except ValueError:
            logger.warning(
                "provider.encrypted_key_unavailable profile=%s — trying AI_API_KEY env",
                profile.display_name,
            )
    env_key = (get_settings().ai_api_key or "").strip()
    return env_key or None


def invoke_config_for_profile(
    profile: AIProviderProfile,
    *,
    model_override: str | None,
    max_tokens_override: int | None,
) -> ProviderInvokeConfig:
    ptype = profile.provider_type.strip().lower()
    model = (model_override or profile.default_model or "gpt-4o-mini").strip()
    base = (profile.base_url or "").strip() or default_base_url_for_type(ptype)
    return ProviderInvokeConfig(
        logical_name=profile.display_name[:64],
        provider_type=ptype,
        model=model,
        base_url=base,
        api_key=_resolve_api_key(profile),
        max_tokens=int(max_tokens_override or profile.max_tokens_default or 800),
        timeout_seconds=int(profile.timeout_seconds or 30),
        profile_id=str(profile.id),
    )


def _attempt(config: ProviderInvokeConfig, *, system_prompt: str, user_prompt: str) -> AICompletion:
    provider = StrictHTTPProvider(config)
    return provider.complete(system_prompt=system_prompt, user_prompt=user_prompt)


def _success(completion: AICompletion) -> bool:
    return bool(completion.text) and not completion.error_message


def complete_for_feature(
    db: Session,
    *,
    feature_key: str,
    system_prompt: str,
    user_prompt: str,
    force_template_only: bool = False,
) -> RoutedCompletion:
    """Primary → fallback profile → template fallback → legacy runtime provider."""
    chain: list[str] = []
    primary_failed = False
    fallback_failed = False
    used_template = False

    if force_template_only:
        tpl = TemplateFallbackProvider().complete(
            system_prompt=system_prompt, user_prompt=user_prompt
        )
        return RoutedCompletion(
            result=tpl,
            chain=["template_forced"],
            used_template_fallback=True,
            primary_failed=True,
            fallback_failed=True,
        )

    route = get_or_create_feature_route(db, feature_key)
    attempts: list[tuple[AIProviderProfile | None, str | None, str]] = []

    if route.primary_provider_id:
        primary = db.get(AIProviderProfile, route.primary_provider_id)
        if primary and primary.is_enabled:
            attempts.append((primary, route.primary_model, "primary"))

    if route.fallback_provider_id:
        fb = db.get(AIProviderProfile, route.fallback_provider_id)
        if fb and fb.is_enabled and fb.id != route.primary_provider_id:
            attempts.append((fb, route.fallback_model, "fallback"))

    max_tok = route.max_tokens

    for profile, model, label in attempts:
        if profile is None:
            continue
        if profile.provider_type == "template_fallback":
            if not route.template_fallback_enabled:
                continue
            tpl = TemplateFallbackProvider().complete(
                system_prompt=system_prompt, user_prompt=user_prompt
            )
            chain.append(f"{label}:template")
            used_template = True
            tpl.used_fallback = True
            return RoutedCompletion(
                result=tpl,
                chain=chain,
                used_template_fallback=True,
                primary_failed=primary_failed,
                fallback_failed=fallback_failed,
            )

        for model_name in models_to_try_for_profile(profile, model):
            cfg = invoke_config_for_profile(
                profile, model_override=model_name, max_tokens_override=max_tok
            )
            comp = _attempt(cfg, system_prompt=system_prompt, user_prompt=user_prompt)
            chain.append(f"{label}:{profile.display_name}:{model_name}")
            if _success(comp):
                return RoutedCompletion(
                    result=comp,
                    chain=chain,
                    used_template_fallback=False,
                    primary_failed=primary_failed,
                    fallback_failed=fallback_failed,
                )
        if label == "primary":
            primary_failed = True
        else:
            fallback_failed = True

    if route.template_fallback_enabled:
        tpl = TemplateFallbackProvider().complete(
            system_prompt=system_prompt, user_prompt=user_prompt
        )
        chain.append("template:chain_end")
        used_template = True
        tpl.used_fallback = True
        return RoutedCompletion(
            result=tpl,
            chain=chain,
            used_template_fallback=True,
            primary_failed=primary_failed,
            fallback_failed=fallback_failed,
        )

    # Legacy runtime fallback
    settings = resolve_ai_settings(db)
    legacy = get_ai_provider(settings)
    comp = legacy.complete(system_prompt=system_prompt, user_prompt=user_prompt)
    chain.append("legacy:runtime")
    return RoutedCompletion(
        result=comp,
        chain=chain,
        used_template_fallback=bool(comp.used_fallback),
        primary_failed=primary_failed,
        fallback_failed=fallback_failed,
    )


def feature_route_last_used(db: Session, feature_key: str) -> str | None:
    row = db.scalar(
        select(AIUsageLog.created_at)
        .where(AIUsageLog.feature_key == feature_key)
        .order_by(AIUsageLog.created_at.desc())
        .limit(1)
    )
    return row.isoformat() if row else None


def list_feature_routes_public(db: Session) -> list[dict[str, Any]]:
    ensure_default_provider_profiles(db)
    keys = list(ADMIN_CONTROL_FEATURES) + list(FUTURE_AI_FEATURES)
    template_slugs = load_active_template_slugs(db)
    out: list[dict[str, Any]] = []
    for key in keys:
        route = get_or_create_feature_route(db, key)
        primary = (
            db.get(AIProviderProfile, route.primary_provider_id)
            if route.primary_provider_id
            else None
        )
        fallback = (
            db.get(AIProviderProfile, route.fallback_provider_id)
            if route.fallback_provider_id
            else None
        )
        locked_review = key in HIGH_RISK_HUMAN_REVIEW_LOCKED
        payload = {
                "feature_key": key,
                "label": FEATURE_LABELS.get(key, key),
                "category": feature_group(key),
                "future": key in FUTURE_AI_FEATURES,
                "enabled": bool(route.enabled) and route.status != "disabled",
                "status": route.status,
                "primary_provider_id": str(route.primary_provider_id)
                if route.primary_provider_id
                else None,
                "primary_provider_name": primary.display_name if primary else None,
                "primary_model": route.primary_model,
                "primary_model_label": model_selection_label(route.primary_model),
                "fallback_provider_id": str(route.fallback_provider_id)
                if route.fallback_provider_id
                else None,
                "fallback_provider_name": fallback.display_name if fallback else None,
                "fallback_model": route.fallback_model,
                "fallback_model_label": model_selection_label(route.fallback_model),
                "template_fallback_enabled": route.template_fallback_enabled,
                "daily_request_limit": route.daily_request_limit,
                "monthly_request_limit": route.monthly_request_limit,
                "max_tokens": route.max_tokens,
                "monthly_spend_cap_micros": route.monthly_spend_cap_micros,
                "requires_human_review": bool(route.requires_human_review),
                "human_review_locked": locked_review,
                "allowed_permissions": list(route.allowed_permissions or []),
                "last_used_at": feature_route_last_used(db, key),
            }
        out.append(
            enrich_route_row(
                payload,
                route=route,
                primary=primary,
                template_slugs=template_slugs,
            )
        )
    db.commit()
    return out


def route_enabled(db: Session, feature_key: str) -> bool:
    route = db.scalar(
        select(AIFeatureRoute).where(AIFeatureRoute.feature_key == feature_key)
    )
    if route is not None:
        return bool(route.enabled) and route.status != "disabled"
    cfg = db.scalar(
        select(AIFeatureConfig).where(AIFeatureConfig.feature_key == feature_key)
    )
    if cfg is not None:
        return bool(cfg.enabled)
    return bool(DEFAULT_FEATURE_ENABLED.get(feature_key, False))
