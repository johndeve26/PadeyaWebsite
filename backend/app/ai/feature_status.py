"""Product vs operational status and readiness checklist for Control Center."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.constants import (
    ADMIN_CONTROL_FEATURES,
    ADMIN_QUARANTINED_AI_FEATURES,
    ADMIN_SUMMARY_FEATURES,
    ANNOUNCEMENT_FEATURES,
    CANONICAL_HOST_AI_FEATURES,
    LEGACY_HOST_AI_FEATURES,
    PASSPORT_FEATURES,
    SPONSORSHIP_FEATURES,
    BLOG_FEATURES,
    FEATURE_HOST_EVENT_DESCRIPTION,
    FEATURE_HOST_EVENT_TITLE,
    FEATURE_HOST_MERCH_CATEGORY,
    FEATURE_HOST_MERCH_DESCRIPTION,
    FEATURE_HOST_MERCH_TAGS,
    FEATURE_HOST_MERCH_TITLE,
    FEATURE_PLATFORM_ASSISTANT_CHAT,
    FEATURE_TEMPLATE_SLUG,
    FUTURE_AI_FEATURES,
    SUPPORT_FEATURES,
)
from app.ai.models import AIFeatureRoute, AIProviderProfile, AIPromptTemplate

FUTURE_HELPER_TEXT = (
    "Planned capability — not connected to Pàdéyá AI yet. "
    "Enabling here does not activate product UI or generation."
)

SAFETY_REVIEW_FEATURES: frozenset[str] = frozenset(
    {
        "fan.connect.explanation",
        "discovery.why_recommended",
    }
)

SAFETY_REVIEW_NOTE = "Requires product/safety review before implementation."

DOCS_REFERENCE = "docs/AI_FEATURE_STATUS_AUDIT.md"

_DEPRECATED_KEYS: frozenset[str] = LEGACY_HOST_AI_FEATURES
_PARTIAL_KEYS: frozenset[str] = frozenset()

EVENT_COPY_FEATURES = frozenset(
    {FEATURE_HOST_EVENT_TITLE, FEATURE_HOST_EVENT_DESCRIPTION}
)
MERCH_FEATURES = frozenset(
    {
        FEATURE_HOST_MERCH_TITLE,
        FEATURE_HOST_MERCH_DESCRIPTION,
        FEATURE_HOST_MERCH_CATEGORY,
        FEATURE_HOST_MERCH_TAGS,
    }
)


PLATFORM_FEATURES = frozenset({FEATURE_PLATFORM_ASSISTANT_CHAT})


def _on_generate_allowlist(feature_key: str) -> bool:
    if feature_key in LEGACY_HOST_AI_FEATURES or feature_key in ADMIN_QUARANTINED_AI_FEATURES:
        return False
    if feature_key in CANONICAL_HOST_AI_FEATURES:
        return True
    if feature_key in {"generate_event_title", "generate_event_description"}:
        return True
    if feature_key in ADMIN_CONTROL_FEATURES:
        return True
    return False


def _has_dedicated_context(feature_key: str) -> bool:
    if feature_key in EVENT_COPY_FEATURES or feature_key in MERCH_FEATURES:
        return True
    if feature_key in SUPPORT_FEATURES:
        return True
    if feature_key in BLOG_FEATURES:
        return True
    if feature_key in ADMIN_SUMMARY_FEATURES:
        return True
    if feature_key in ANNOUNCEMENT_FEATURES:
        return True
    if feature_key in SPONSORSHIP_FEATURES:
        return True
    if feature_key in PASSPORT_FEATURES:
        return True
    if feature_key in PLATFORM_FEATURES:
        return True
    return False


def _has_feature_validation(feature_key: str) -> bool:
    if feature_key in EVENT_COPY_FEATURES or feature_key in MERCH_FEATURES:
        return True
    if feature_key in SUPPORT_FEATURES or feature_key in BLOG_FEATURES:
        return True
    if feature_key in ADMIN_SUMMARY_FEATURES:
        return True
    if feature_key in ANNOUNCEMENT_FEATURES:
        return True
    if feature_key in SPONSORSHIP_FEATURES:
        return True
    if feature_key in PASSPORT_FEATURES:
        return True
    if feature_key in PLATFORM_FEATURES:
        return True
    return False


def _has_redaction_path(feature_key: str) -> bool:
    return _has_dedicated_context(feature_key)


def _frontend_ui_wired(feature_key: str) -> bool:
    return feature_key in set(ADMIN_CONTROL_FEATURES)


def _readiness_for_future(_feature_key: str) -> dict[str, bool]:
    return {
        "backend_allowlist": False,
        "prompt_template": False,
        "context_builder": False,
        "redaction_rules": False,
        "output_validation": False,
        "frontend_ui": False,
        "audit_usage_logging": True,
        "safe_to_enable": False,
    }


def _readiness_for_active(
    feature_key: str, *, template_slugs: set[str]
) -> dict[str, bool]:
    slug = FEATURE_TEMPLATE_SLUG.get(feature_key, feature_key)
    has_template = (
        slug in template_slugs
        or feature_key in template_slugs
        or feature_key in PLATFORM_FEATURES
    )
    allowlist = _on_generate_allowlist(feature_key)
    context = _has_dedicated_context(feature_key)
    redaction = _has_redaction_path(feature_key)
    validation = _has_feature_validation(feature_key)
    frontend = _frontend_ui_wired(feature_key)
    safe = allowlist and has_template and context and redaction and validation and frontend
    return {
        "backend_allowlist": allowlist,
        "prompt_template": has_template,
        "context_builder": context,
        "redaction_rules": redaction,
        "output_validation": validation,
        "frontend_ui": frontend,
        "audit_usage_logging": True,
        "safe_to_enable": safe,
    }


def _provider_needs_configuration(profile: AIProviderProfile | None) -> bool:
    if profile is None:
        return True
    if profile.provider_type == "template_fallback":
        return False
    if not profile.is_enabled:
        return True
    from app.ai.providers_admin import _mask_key

    if not _mask_key(profile)["configured"]:
        return True
    if profile.health_status in ("needs_configuration", "failing"):
        return True
    return False


def product_status_for_key(feature_key: str) -> str:
    if feature_key in FUTURE_AI_FEATURES:
        if feature_key in SAFETY_REVIEW_FEATURES:
            return "blocked"
        return "future"
    if feature_key in ADMIN_QUARANTINED_AI_FEATURES:
        return "blocked"
    if feature_key in _DEPRECATED_KEYS:
        return "deprecated"
    if feature_key in _PARTIAL_KEYS:
        return "partial"
    return "active"


def operational_status_for_route(
    *,
    feature_key: str,
    route: AIFeatureRoute,
    primary: AIProviderProfile | None,
    operationally_enabled: bool,
) -> str:
    product = product_status_for_key(feature_key)
    if product in ("future", "blocked", "deprecated", "partial"):
        return "not_available"
    if not operationally_enabled:
        return "off"
    _ = route
    if _provider_needs_configuration(primary):
        return "needs_configuration"
    return "on"


def enrich_route_row(
    row: dict[str, Any],
    *,
    route: AIFeatureRoute,
    primary: AIProviderProfile | None,
    template_slugs: set[str],
) -> dict[str, Any]:
    key = row["feature_key"]
    is_future = key in FUTURE_AI_FEATURES
    safety = key in SAFETY_REVIEW_FEATURES

    readiness = (
        _readiness_for_future(key)
        if is_future
        else _readiness_for_active(key, template_slugs=template_slugs)
    )

    operational = operational_status_for_route(
        feature_key=key,
        route=route,
        primary=primary,
        operationally_enabled=bool(row.get("enabled")),
    )

    row["product_status"] = product_status_for_key(key)
    row["operational_status"] = operational
    row["readiness"] = readiness
    row["safety_review_required"] = safety
    row["safety_note"] = SAFETY_REVIEW_NOTE if safety else None
    row["future_helper_text"] = FUTURE_HELPER_TEXT if is_future else None
    row["routing_editable"] = not is_future
    row["docs_reference"] = DOCS_REFERENCE
    return row


def load_active_template_slugs(db: Session) -> set[str]:
    rows = db.scalars(
        select(AIPromptTemplate.slug).where(AIPromptTemplate.is_active.is_(True))
    ).all()
    return {str(r) for r in rows}
