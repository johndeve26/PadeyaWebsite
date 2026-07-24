"""AI Copilot API — server-side suggestions only."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.ai.admin_controls import (
    get_admin_overview,
    list_feature_configs,
    safe_generation_logs,
    test_connection,
    update_feature_config,
    update_global_settings,
    update_spend_settings,
    usage_dashboard,
)
from app.ai.feature_routing import list_feature_routes_public
from app.ai.providers_admin import (
    create_provider_profile,
    delete_provider_profile,
    env_api_key_banner,
    list_provider_profiles,
    test_provider_profile,
    update_provider_profile,
)
from app.ai.safety import get_safety_overview, update_feature_route
from app.ai.schemas import (
    AIAdminOverviewPublic,
    AIProviderProfileCreate,
    AIProviderProfilePublic,
    AIProviderProfileUpdate,
    AIFeatureConfigPublic,
    AIFeatureConfigUpdate,
    AIFeaturePublic,
    AIFeatureRoutePublic,
    AIFeatureRouteUpdate,
    AIGenerateRequest,
    AIGenerationFeedbackRequest,
    AIGlobalSettingsUpdate,
    AIPromptTemplateCreate,
    AIPromptTemplatePublic,
    AIPromptTemplateUpdate,
    AISafeUsageLogPublic,
    AISpendSettingsUpdate,
    AIStatusPublic,
    AISuggestionResponse,
    AITestConnectionPublic,
    AIUsageLogPublic,
)
from app.ai.service import (
    ai_status,
    generate_suggestion,
    list_features,
    record_generation_feedback,
)
from app.ai.templates_admin import (
    create_prompt_template,
    deactivate_prompt_template,
    list_prompt_templates,
    list_usage_logs,
    update_prompt_template,
)
from app.auth.dependencies import CurrentUser, require_permission
from app.core.database import get_db
from app.users.models import User

router = APIRouter(prefix="/ai", tags=["ai"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.get("/health")
async def ai_module_health() -> dict[str, str]:
    return {"module": "ai", "status": "ok"}


@router.get("/status", response_model=AIStatusPublic)
def get_status(db: Annotated[Session, Depends(get_db)]) -> AIStatusPublic:
    return AIStatusPublic.model_validate(ai_status(db))


@router.get("/host/features", response_model=list[AIFeaturePublic])
def host_features(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[AIFeaturePublic]:
    from app.ai.service import assert_host_ai_actor

    assert_host_ai_actor(db, user)
    return [AIFeaturePublic.model_validate(f) for f in list_features("host", db=db)]


@router.post("/host/generate", response_model=AISuggestionResponse)
def host_generate(
    payload: AIGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AISuggestionResponse:
    return AISuggestionResponse.model_validate(
        generate_suggestion(db, user=user, audience="host", payload=payload)
    )


@router.post("/host/events/{event_id}/generate", response_model=AISuggestionResponse)
def host_event_generate(
    event_id: UUID,
    payload: AIGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AISuggestionResponse:
    data = payload.model_copy(update={"event_id": event_id})
    return AISuggestionResponse.model_validate(
        generate_suggestion(db, user=user, audience="host", payload=data)
    )


@router.post("/host/generation-feedback")
def host_generation_feedback(
    payload: AIGenerationFeedbackRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    """Record accepted / applied / rejected drafts — never auto-publishes."""
    return record_generation_feedback(db, user=user, payload=payload)


@router.get("/fan/features", response_model=list[AIFeaturePublic])
def fan_features(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> list[AIFeaturePublic]:
    _ = user
    return [AIFeaturePublic.model_validate(f) for f in list_features("fan", db=db)]


@router.post("/fan/passport/generate", response_model=AISuggestionResponse)
def fan_passport_generate(
    payload: AIGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> AISuggestionResponse:
    """Owned Passport bio drafts only — never auto-publishes or changes visibility."""
    data = payload.model_copy(
        update={"feature": payload.feature or "fan.passport.bio"}
    )
    return AISuggestionResponse.model_validate(
        generate_suggestion(db, user=user, audience="fan", payload=data)
    )


@router.post("/fan/generation-feedback")
def fan_generation_feedback(
    payload: AIGenerationFeedbackRequest,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
) -> dict:
    return record_generation_feedback(db, user=user, payload=payload)


@router.get("/admin/features", response_model=list[AIFeaturePublic])
def admin_features(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("ai.use_platform", "admin.full_access"))
    ],
) -> list[AIFeaturePublic]:
    _ = user
    return [AIFeaturePublic.model_validate(f) for f in list_features("admin", db=db)]


@router.post("/admin/generate", response_model=AISuggestionResponse)
def admin_generate(
    payload: AIGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("ai.use_platform", "admin.full_access"))
    ],
) -> AISuggestionResponse:
    return AISuggestionResponse.model_validate(
        generate_suggestion(db, user=user, audience="admin", payload=payload)
    )


@router.post(
    "/admin/support/tickets/{ticket_id}/generate",
    response_model=AISuggestionResponse,
)
def admin_support_ticket_generate(
    ticket_id: UUID,
    payload: AIGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("ai.use_platform", "admin.full_access"))
    ],
) -> AISuggestionResponse:
    """Staff-only support AI draft — never auto-sends or changes ticket state."""
    data = payload.model_copy(update={"support_ticket_id": ticket_id})
    return AISuggestionResponse.model_validate(
        generate_suggestion(db, user=user, audience="admin", payload=data)
    )


@router.post("/admin/generation-feedback")
def admin_generation_feedback(
    payload: AIGenerationFeedbackRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("ai.use_platform", "admin.full_access"))
    ],
) -> dict:
    return record_generation_feedback(db, user=user, payload=payload)


@router.post("/admin/support/summary", response_model=AISuggestionResponse)
def admin_support_summary(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("ai.use_platform", "admin.full_access"))
    ],
    notes: str | None = None,
) -> AISuggestionResponse:
    payload = AIGenerateRequest(
        feature="admin.support.queue_summary", notes=notes
    )
    return AISuggestionResponse.model_validate(
        generate_suggestion(db, user=user, audience="admin", payload=payload)
    )


# ---- Admin AI controls (/admin/ai UI) ----


@router.get("/admin/controls/overview", response_model=AIAdminOverviewPublic)
def admin_ai_overview(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.ai.view",
                "admin.ai.manage_settings",
                "admin.full_access",
            )
        ),
    ],
) -> AIAdminOverviewPublic:
    _ = user
    return AIAdminOverviewPublic.model_validate(get_admin_overview(db))


@router.get("/admin/controls/providers", response_model=list[AIProviderProfilePublic])
def admin_ai_list_providers(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.ai.view",
                "admin.ai.manage_providers",
                "admin.full_access",
            )
        ),
    ],
) -> list[AIProviderProfilePublic]:
    _ = user
    return [AIProviderProfilePublic.model_validate(p) for p in list_provider_profiles(db)]


@router.post(
    "/admin/controls/providers",
    response_model=AIProviderProfilePublic,
    status_code=201,
)
def admin_ai_create_provider(
    payload: AIProviderProfileCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission("admin.ai.manage_providers", "admin.full_access")
        ),
    ],
) -> AIProviderProfilePublic:
    ip, ua = _client_meta(request)
    row = create_provider_profile(
        db,
        actor_user_id=user.id,
        provider_type=payload.provider_type,
        display_name=payload.display_name,
        base_url=payload.base_url,
        default_model=payload.default_model,
        available_models=payload.available_models,
        is_enabled=payload.is_enabled,
        priority=payload.priority,
        timeout_seconds=payload.timeout_seconds,
        max_tokens_default=payload.max_tokens_default,
        use_env_api_key=payload.use_env_api_key,
        notes=payload.notes,
        api_key=payload.api_key,
        ip_address=ip,
        user_agent=ua,
    )
    return AIProviderProfilePublic.model_validate(row)


@router.patch(
    "/admin/controls/providers/{profile_id}",
    response_model=AIProviderProfilePublic,
)
def admin_ai_update_provider(
    profile_id: UUID,
    payload: AIProviderProfileUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission("admin.ai.manage_providers", "admin.full_access")
        ),
    ],
) -> AIProviderProfilePublic:
    ip, ua = _client_meta(request)
    fields = payload.model_dump(exclude_unset=True)
    row = update_provider_profile(
        db,
        profile_id=profile_id,
        actor_user_id=user.id,
        ip_address=ip,
        user_agent=ua,
        **fields,
    )
    return AIProviderProfilePublic.model_validate(row)


@router.delete(
    "/admin/controls/providers/{profile_id}",
    status_code=204,
)
def admin_ai_delete_provider(
    profile_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission("admin.ai.manage_providers", "admin.full_access")
        ),
    ],
) -> None:
    ip, ua = _client_meta(request)
    delete_provider_profile(
        db,
        profile_id=profile_id,
        actor_user_id=user.id,
        ip_address=ip,
        user_agent=ua,
    )


@router.post("/admin/controls/providers/{profile_id}/test")
def admin_ai_test_provider(
    profile_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.ai.test_connection",
                "admin.ai.manage_providers",
                "admin.full_access",
            )
        ),
    ],
) -> dict[str, Any]:
    ip, ua = _client_meta(request)
    return test_provider_profile(
        db,
        profile_id=profile_id,
        actor_user_id=user.id,
        ip_address=ip,
        user_agent=ua,
    )


@router.get("/admin/controls/routes", response_model=list[AIFeatureRoutePublic])
def admin_ai_feature_routes(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.ai.view",
                "admin.ai.manage_features",
                "admin.full_access",
            )
        ),
    ],
) -> list[AIFeatureRoutePublic]:
    _ = user
    return [
        AIFeatureRoutePublic.model_validate(r) for r in list_feature_routes_public(db)
    ]


@router.patch(
    "/admin/controls/routes/{feature_key}",
    response_model=AIFeatureRoutePublic,
)
def admin_ai_update_route(
    feature_key: str,
    payload: AIFeatureRouteUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission("admin.ai.manage_features", "admin.full_access")
        ),
    ],
) -> AIFeatureRoutePublic:
    ip, ua = _client_meta(request)
    fields = payload.model_dump(exclude_unset=True)
    for clear_key, field in (
        ("clear_daily_limit", "daily_request_limit"),
        ("clear_monthly_limit", "monthly_request_limit"),
        ("clear_max_tokens", "max_tokens"),
    ):
        if fields.pop(clear_key, False):
            fields[field] = None
    row = update_feature_route(
        db,
        feature_key=feature_key,
        actor_user_id=user.id,
        ip_address=ip,
        user_agent=ua,
        **fields,
    )
    return AIFeatureRoutePublic.model_validate(row)


@router.get("/admin/controls/safety")
def admin_ai_safety(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.ai.view",
                "admin.ai.manage_safety",
                "admin.full_access",
            )
        ),
    ],
) -> dict[str, Any]:
    _ = user
    data = get_safety_overview(db)
    data["api_key_banner"] = env_api_key_banner()
    return data


@router.patch("/admin/controls/settings", response_model=AIAdminOverviewPublic)
def admin_ai_update_settings(
    payload: AIGlobalSettingsUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.ai.manage_settings",
                "admin.settings.edit_runtime",
                "admin.full_access",
            )
        ),
    ],
) -> AIAdminOverviewPublic:
    ip, ua = _client_meta(request)
    return AIAdminOverviewPublic.model_validate(
        update_global_settings(
            db,
            actor_user_id=user.id,
            enabled=payload.enabled,
            provider=payload.provider,
            model=payload.model,
            base_url=payload.base_url,
            ip_address=ip,
            user_agent=ua,
        )
    )


@router.patch("/admin/controls/spend")
def admin_ai_update_spend(
    payload: AISpendSettingsUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.ai.manage_spend",
                "admin.ai.manage_settings",
                "admin.full_access",
            )
        ),
    ],
) -> dict[str, Any]:
    ip, ua = _client_meta(request)
    return update_spend_settings(
        db,
        actor_user_id=user.id,
        monthly_spend_cap_micros=payload.monthly_spend_cap_micros,
        clear_cap=payload.clear_cap,
        warning_threshold_pct=payload.warning_threshold_pct,
        hard_stop_threshold_pct=payload.hard_stop_threshold_pct,
        hard_stop_enabled=payload.hard_stop_enabled,
        allow_template_fallback_when_capped=payload.allow_template_fallback_when_capped,
        ip_address=ip,
        user_agent=ua,
    )


@router.post("/admin/controls/test-connection", response_model=AITestConnectionPublic)
def admin_ai_test_connection(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.ai.test_connection",
                "admin.ai.manage_settings",
                "admin.full_access",
            )
        ),
    ],
) -> AITestConnectionPublic:
    ip, ua = _client_meta(request)
    return AITestConnectionPublic.model_validate(
        test_connection(
            db, actor_user_id=user.id, ip_address=ip, user_agent=ua
        )
    )


@router.get("/admin/controls/features", response_model=list[AIFeatureConfigPublic])
def admin_ai_feature_configs(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.ai.view",
                "admin.ai.manage_features",
                "admin.full_access",
            )
        ),
    ],
) -> list[AIFeatureConfigPublic]:
    _ = user
    return [AIFeatureConfigPublic.model_validate(i) for i in list_feature_configs(db)]


@router.patch(
    "/admin/controls/features/{feature_key}",
    response_model=AIFeatureConfigPublic,
)
def admin_ai_update_feature(
    feature_key: str,
    payload: AIFeatureConfigUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission("admin.ai.manage_features", "admin.full_access")
        ),
    ],
) -> AIFeatureConfigPublic:
    ip, ua = _client_meta(request)
    daily: int | None | object = ...
    monthly: int | None | object = ...
    tokens: int | None | object = ...
    if payload.clear_daily_limit:
        daily = None
    elif "daily_request_limit" in payload.model_fields_set:
        daily = payload.daily_request_limit
    if payload.clear_monthly_limit:
        monthly = None
    elif "monthly_request_limit" in payload.model_fields_set:
        monthly = payload.monthly_request_limit
    if payload.clear_token_limit:
        tokens = None
    elif "token_limit_per_request" in payload.model_fields_set:
        tokens = payload.token_limit_per_request
    return AIFeatureConfigPublic.model_validate(
        update_feature_config(
            db,
            feature_key=feature_key,
            actor_user_id=user.id,
            enabled=payload.enabled,
            allowed_permissions=payload.allowed_permissions,
            daily_request_limit=daily,  # type: ignore[arg-type]
            monthly_request_limit=monthly,  # type: ignore[arg-type]
            token_limit_per_request=tokens,  # type: ignore[arg-type]
            requires_human_review=payload.requires_human_review,
            status_value=payload.status,
            ip_address=ip,
            user_agent=ua,
        )
    )


@router.get("/admin/controls/usage")
def admin_ai_usage_dashboard(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.ai.view_usage",
                "admin.ai.view",
                "admin.full_access",
            )
        ),
    ],
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    _ = user
    return usage_dashboard(db, date_from=date_from, date_to=date_to)


@router.get("/admin/controls/logs")
def admin_ai_safe_logs(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User,
        Depends(
            require_permission(
                "admin.ai.view_logs",
                "admin.ai.view_usage",
                "admin.full_access",
            )
        ),
    ],
    limit: int = 50,
    offset: int = 0,
    feature_key: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    ip, ua = _client_meta(request)
    data = safe_generation_logs(
        db,
        actor_user_id=user.id,
        limit=limit,
        offset=offset,
        feature_key=feature_key,
        date_from=date_from,
        date_to=date_to,
        audit_view=True,
        ip_address=ip,
        user_agent=ua,
    )
    data["items"] = [
        AISafeUsageLogPublic.model_validate(i).model_dump() for i in data["items"]
    ]
    return data


@router.get("/admin/templates", response_model=list[AIPromptTemplatePublic])
def admin_list_templates(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("ai.use_platform", "admin.full_access"))
    ],
) -> list[AIPromptTemplatePublic]:
    _ = user
    return [
        AIPromptTemplatePublic.model_validate(t) for t in list_prompt_templates(db)
    ]


@router.post(
    "/admin/templates",
    response_model=AIPromptTemplatePublic,
    status_code=201,
)
def admin_create_template(
    payload: AIPromptTemplateCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("ai.use_platform", "admin.full_access"))
    ],
) -> AIPromptTemplatePublic:
    row = create_prompt_template(
        db,
        user=user,
        slug=payload.slug,
        name=payload.name,
        audience=payload.audience,
        system_prompt=payload.system_prompt,
        user_template=payload.user_template,
        description=payload.description,
    )
    return AIPromptTemplatePublic.model_validate(row)


@router.patch("/admin/templates/{template_id}", response_model=AIPromptTemplatePublic)
def admin_update_template(
    template_id: UUID,
    payload: AIPromptTemplateUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("ai.use_platform", "admin.full_access"))
    ],
) -> AIPromptTemplatePublic:
    row = update_prompt_template(
        db,
        user=user,
        template_id=template_id,
        name=payload.name,
        audience=payload.audience,
        system_prompt=payload.system_prompt,
        user_template=payload.user_template,
        description=payload.description,
        is_active=payload.is_active,
    )
    return AIPromptTemplatePublic.model_validate(row)


@router.post(
    "/admin/templates/{template_id}/deactivate",
    response_model=AIPromptTemplatePublic,
)
def admin_deactivate_template(
    template_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("ai.use_platform", "admin.full_access"))
    ],
) -> AIPromptTemplatePublic:
    row = deactivate_prompt_template(db, user=user, template_id=template_id)
    return AIPromptTemplatePublic.model_validate(row)


@router.get("/admin/usage-logs", response_model=list[AIUsageLogPublic])
def admin_usage_logs(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[
        User, Depends(require_permission("ai.use_platform", "admin.full_access"))
    ],
) -> list[AIUsageLogPublic]:
    _ = user
    return [AIUsageLogPublic.model_validate(r) for r in list_usage_logs(db)]
