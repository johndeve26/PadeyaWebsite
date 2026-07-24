"""AI safety controls overview for the Control Center."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy.orm import Session

from app.ai.admin_controls import _kill_switch_active, get_admin_overview
from app.ai.constants import ADMIN_CONTROL_FEATURES, FUTURE_AI_FEATURES
from app.ai.feature_routing import list_feature_routes_public


PRODUCT_SAFETY_RULES: list[str] = [
    "AI cannot publish events or merch.",
    "AI cannot send support replies, CRM, email, or in-app messages.",
    "AI cannot issue tickets or change ticket status automatically.",
    "AI cannot change prices, inventory, or finance records.",
    "AI cannot refund, payout, or approve payments.",
    "AI cannot suspend, ban, or restrict users.",
    "AI cannot bypass Fan Connect eligibility rules.",
    "AI cannot auto-moderate content or hide reviews.",
]

DENYLISTED_DATA_CLASSES: list[str] = [
    "passwords and auth tokens",
    "Paystack payloads and card data",
    "QR / ticket secrets",
    "private venue addresses (when not public)",
    "Vault locked bodies",
    "private messages and admin notes",
    "buyer PII (email, phone)",
]


def get_safety_overview(db: Session) -> dict[str, Any]:
    kill = _kill_switch_active()
    overview = get_admin_overview(db)
    routes = list_feature_routes_public(db)
    enabled_count = sum(1 for r in routes if r["enabled"] and not r["future"])
    disabled_features = [
        r["feature_key"]
        for r in routes
        if not r["enabled"] or r["status"] == "disabled"
    ]
    env_disabled = [
        p.strip()
        for p in (os.environ.get("AI_DISABLED_FEATURES") or "").split(",")
        if p.strip()
    ]
    return {
        "kill_switch_active": kill,
        "global_ai_enabled": overview["global_ai"]["ai_enabled_setting"],
        "redaction_enabled": True,
        "output_validation_enabled": True,
        "human_review_default": True,
        "audit_logging_enabled": True,
        "retention_policy": "Usage logs store metadata only — no raw prompts or secrets.",
        "enabled_feature_count": enabled_count,
        "total_managed_features": len(ADMIN_CONTROL_FEATURES) + len(FUTURE_AI_FEATURES),
        "disabled_features": disabled_features,
        "env_disabled_features": env_disabled,
        "future_features": list(FUTURE_AI_FEATURES),
        "denylisted_data_classes": DENYLISTED_DATA_CLASSES,
        "product_rules": PRODUCT_SAFETY_RULES,
        "status_label": (
            "Disabled by environment"
            if kill
            else ("Operational" if overview["global_ai"]["enabled"] else "AI globally off")
        ),
    }


def update_feature_route(
    db: Session,
    *,
    feature_key: str,
    actor_user_id,
    ip_address: str | None = None,
    user_agent: str | None = None,
    **fields: Any,
) -> dict[str, Any]:
    from uuid import UUID

    from fastapi import HTTPException

    from app.ai.constants import FUTURE_AI_FEATURES, HIGH_RISK_HUMAN_REVIEW_LOCKED
    from app.ai.feature_routing import get_or_create_feature_route
    from app.ai.models import AIFeatureRoute
    from app.core.audit import write_audit_log

    if feature_key in FUTURE_AI_FEATURES:
        raise HTTPException(
            status_code=400,
            detail=(
                "This feature is planned but not implemented. "
                "Routing cannot be changed until the feature ships."
            ),
        )

    route = get_or_create_feature_route(db, feature_key)
    before = {
        "enabled": route.enabled,
        "primary_provider_id": str(route.primary_provider_id)
        if route.primary_provider_id
        else None,
        "primary_model": route.primary_model,
        "fallback_provider_id": str(route.fallback_provider_id)
        if route.fallback_provider_id
        else None,
        "fallback_model": route.fallback_model,
        "template_fallback_enabled": route.template_fallback_enabled,
    }
    if fields.get("enabled") is not None:
        route.enabled = bool(fields["enabled"])
    if fields.get("primary_provider_id") is not None:
        pid = fields["primary_provider_id"]
        route.primary_provider_id = UUID(pid) if pid else None
    if "primary_model" in fields:
        from app.ai.model_catalog import normalize_model_selection

        route.primary_model = normalize_model_selection(fields.get("primary_model"))
    if fields.get("fallback_provider_id") is not None:
        fid = fields["fallback_provider_id"]
        route.fallback_provider_id = UUID(fid) if fid else None
    if "fallback_model" in fields:
        from app.ai.model_catalog import normalize_model_selection

        route.fallback_model = normalize_model_selection(fields.get("fallback_model"))
    if fields.get("template_fallback_enabled") is not None:
        route.template_fallback_enabled = bool(fields["template_fallback_enabled"])
    for lim in (
        "daily_request_limit",
        "monthly_request_limit",
        "max_tokens",
        "monthly_spend_cap_micros",
    ):
        if lim in fields:
            setattr(route, lim, fields[lim])
    if fields.get("requires_human_review") is not None:
        if feature_key in HIGH_RISK_HUMAN_REVIEW_LOCKED:
            route.requires_human_review = True
        else:
            route.requires_human_review = bool(fields["requires_human_review"])
    if fields.get("allowed_permissions") is not None:
        route.allowed_permissions = list(fields["allowed_permissions"])
    if fields.get("status") is not None:
        route.status = fields["status"]
    route.updated_by_user_id = actor_user_id
    write_audit_log(
        db,
        action="ai.features.route_updated",
        actor_user_id=actor_user_id,
        resource_type="ai_feature_route",
        resource_id=feature_key,
        details={"before": before},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    items = list_feature_routes_public(db)
    match = next((i for i in items if i["feature_key"] == feature_key), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Feature route not found")
    return match
