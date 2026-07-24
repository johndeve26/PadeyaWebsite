"""AI Copilot request/response schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AIFeaturePublic(BaseModel):
    key: str
    label: str
    audience: str
    enabled: bool = True


class AIGenerateRequest(BaseModel):
    feature: str = Field(min_length=2, max_length=80)
    event_id: UUID | None = None
    merch_product_id: UUID | None = None
    support_ticket_id: UUID | None = None
    blog_post_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)
    extra: dict[str, Any] | None = None


class AIArticleSuggestion(BaseModel):
    id: str | None = None
    slug: str | None = None
    title: str | None = None
    path: str | None = None


class AISocialSnippet(BaseModel):
    platform: str
    text: str


class AISuggestionResponse(BaseModel):
    feature: str
    label: str
    suggestion: str
    options: list[str] | None = None
    category_slug: str | None = None
    tags: list[str] | None = None
    priority: str | None = None
    priority_reason: str | None = None
    articles: list[AIArticleSuggestion] | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    suggested_slug: str | None = None
    og_description: str | None = None
    social_snippets: list[AISocialSnippet] | None = None
    announcement_subject: str | None = None
    announcement_email_body: str | None = None
    announcement_whatsapp_body: str | None = None
    sponsorship_pitch_title: str | None = None
    sponsorship_short_pitch: str | None = None
    sponsorship_value_bullets: str | None = None
    sponsorship_audience_summary: str | None = None
    sponsorship_package_wording: str | None = None
    sponsorship_follow_up_message: str | None = None
    provider: str
    model_name: str | None
    used_fallback: bool
    requires_human_confirmation: bool = True
    can_auto_publish: bool = False
    can_auto_send: bool = False
    can_modify_finance: bool = False
    draft_only: bool = True
    fallback_reason: str | None = None
    disclaimer: str = (
        "AI suggestions are drafts. Review before publishing."
    )
    usage_log_id: UUID
    created_at: datetime
    redaction_applied: bool = False


class AIStatusPublic(BaseModel):
    enabled: bool
    provider: str
    model: str
    rate_limit_per_hour: int
    kill_switch: bool = False
    disabled_by_environment: bool = False
    ai_enabled_setting: bool | None = None
    status_label: str | None = None


class AIAdminOverviewPublic(BaseModel):
    brand: str = "Pàdéyá"
    global_ai: dict[str, Any]
    provider: dict[str, Any]
    api_key: dict[str, Any]
    spend: dict[str, Any]
    rate_limit_per_hour: int
    control_center: dict[str, Any] | None = None


class AIProviderProfilePublic(BaseModel):
    id: str
    provider_type: str
    display_name: str
    base_url: str | None = None
    default_model: str | None = None
    available_models: list[str] = Field(default_factory=list)
    is_enabled: bool = True
    priority: int = 100
    timeout_seconds: int = 30
    max_tokens_default: int = 800
    rate_limit_per_minute: int | None = None
    monthly_spend_limit_micros: int | None = None
    notes: str | None = None
    health_status: str = "unknown"
    api_key_status: dict[str, Any] = Field(default_factory=dict)
    use_env_api_key: bool = False
    created_at: str | None = None
    updated_at: str | None = None


class AIProviderProfileCreate(BaseModel):
    provider_type: str = Field(min_length=2, max_length=32)
    display_name: str = Field(min_length=2, max_length=120)
    base_url: str | None = Field(default=None, max_length=500)
    default_model: str | None = Field(default=None, max_length=120)
    available_models: list[str] | None = None
    is_enabled: bool = True
    priority: int = 100
    timeout_seconds: int = 30
    max_tokens_default: int = 800
    use_env_api_key: bool = False
    notes: str | None = None
    api_key: str | None = Field(default=None, min_length=8, max_length=512)


class AIProviderProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    base_url: str | None = Field(default=None, max_length=500)
    default_model: str | None = Field(default=None, max_length=120)
    available_models: list[str] | None = None
    is_enabled: bool | None = None
    priority: int | None = None
    timeout_seconds: int | None = None
    max_tokens_default: int | None = None
    rate_limit_per_minute: int | None = None
    monthly_spend_limit_micros: int | None = None
    notes: str | None = None
    use_env_api_key: bool | None = None
    api_key: str | None = Field(default=None, min_length=8, max_length=512)
    clear_api_key: bool | None = None


class AIFeatureReadinessPublic(BaseModel):
    backend_allowlist: bool
    prompt_template: bool
    context_builder: bool
    redaction_rules: bool
    output_validation: bool
    frontend_ui: bool
    audit_usage_logging: bool
    safe_to_enable: bool


class AIFeatureRoutePublic(BaseModel):
    feature_key: str
    label: str
    category: str
    future: bool = False
    enabled: bool
    status: str
    product_status: str = "active"
    operational_status: str = "off"
    readiness: AIFeatureReadinessPublic
    safety_review_required: bool = False
    safety_note: str | None = None
    future_helper_text: str | None = None
    routing_editable: bool = True
    docs_reference: str = "docs/AI_FEATURE_STATUS_AUDIT.md"
    primary_provider_id: str | None = None
    primary_provider_name: str | None = None
    primary_model: str | None = None
    primary_model_label: str = "All (auto)"
    fallback_provider_id: str | None = None
    fallback_provider_name: str | None = None
    fallback_model: str | None = None
    fallback_model_label: str = "All (auto)"
    template_fallback_enabled: bool = True
    daily_request_limit: int | None = None
    monthly_request_limit: int | None = None
    max_tokens: int | None = None
    monthly_spend_cap_micros: int | None = None
    requires_human_review: bool = True
    human_review_locked: bool = False
    allowed_permissions: list[str] = Field(default_factory=list)
    last_used_at: str | None = None


class AIFeatureRouteUpdate(BaseModel):
    enabled: bool | None = None
    primary_provider_id: str | None = None
    primary_model: str | None = None
    fallback_provider_id: str | None = None
    fallback_model: str | None = None
    template_fallback_enabled: bool | None = None
    daily_request_limit: int | None = None
    monthly_request_limit: int | None = None
    max_tokens: int | None = None
    monthly_spend_cap_micros: int | None = None
    requires_human_review: bool | None = None
    allowed_permissions: list[str] | None = None
    status: str | None = None
    clear_daily_limit: bool = False
    clear_monthly_limit: bool = False
    clear_max_tokens: bool = False


class AIGlobalSettingsUpdate(BaseModel):
    enabled: bool | None = None
    provider: str | None = Field(default=None, max_length=64)
    model: str | None = Field(default=None, max_length=120)
    base_url: str | None = Field(default=None, max_length=500)


class AISpendSettingsUpdate(BaseModel):
    monthly_spend_cap_micros: int | None = None
    clear_cap: bool = False
    warning_threshold_pct: int | None = Field(default=None, ge=1, le=100)
    hard_stop_threshold_pct: int | None = Field(default=None, ge=1, le=100)
    hard_stop_enabled: bool | None = None
    allow_template_fallback_when_capped: bool | None = None


class AIFeatureConfigUpdate(BaseModel):
    enabled: bool | None = None
    allowed_permissions: list[str] | None = None
    daily_request_limit: int | None = None
    monthly_request_limit: int | None = None
    token_limit_per_request: int | None = None
    requires_human_review: bool | None = None
    status: str | None = Field(default=None, max_length=32)
    clear_daily_limit: bool = False
    clear_monthly_limit: bool = False
    clear_token_limit: bool = False


class AIFeatureConfigPublic(BaseModel):
    feature_key: str
    label: str
    group: str
    enabled: bool
    enabled_in_db: bool
    env_disabled: bool = False
    allowed_permissions: list[str] = Field(default_factory=list)
    daily_request_limit: int | None = None
    monthly_request_limit: int | None = None
    token_limit_per_request: int | None = None
    requires_human_review: bool = True
    status: str = "active"
    updated_at: str | None = None


class AITestConnectionPublic(BaseModel):
    ok: bool
    status: str
    message: str
    provider: str | None = None
    model: str | None = None
    used_fallback: bool = False
    latency_ms: float | None = None
    api_key_configured: bool = False


class AISafeUsageLogPublic(BaseModel):
    id: str
    feature_key: str
    actor_user_id: str | None = None
    host_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    provider: str
    model: str | None = None
    status: str
    used_fallback: bool = False
    latency_ms: int | float | None = None
    estimated_cost_micros: int | None = None
    validation_result: str | None = None
    redaction_applied: bool = False
    created_at: str | None = None


class AIGenerationFeedbackRequest(BaseModel):
    usage_log_id: UUID
    action: Literal["accepted", "applied", "rejected", "dismissed"]
    event_id: UUID | None = None
    merch_product_id: UUID | None = None
    support_ticket_id: UUID | None = None
    blog_post_id: UUID | None = None
    applied_field: str | None = Field(default=None, max_length=64)
    selected_option: str | None = Field(default=None, max_length=500)


class AIPromptTemplateCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=160)
    audience: str = Field(min_length=2, max_length=32)
    system_prompt: str = Field(min_length=5)
    user_template: str = Field(min_length=5)
    description: str | None = None


class AIPromptTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    audience: str | None = Field(default=None, min_length=2, max_length=32)
    system_prompt: str | None = Field(default=None, min_length=5)
    user_template: str | None = Field(default=None, min_length=5)
    description: str | None = None
    is_active: bool | None = None


class AIPromptTemplatePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    audience: str
    system_prompt: str
    user_template: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AIUsageLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    host_id: UUID | None
    feature_key: str
    prompt_template_slug: str | None
    provider: str
    model_name: str | None
    success: bool
    used_fallback: bool
    created_at: datetime
