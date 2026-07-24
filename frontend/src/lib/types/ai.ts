export type AIFeature = {
  key: string;
  label: string;
  audience: string;
  enabled?: boolean;
};

export type AIArticleSuggestion = {
  id?: string | null;
  slug?: string | null;
  title?: string | null;
  path?: string | null;
};

export type AISocialSnippet = {
  platform: string;
  text: string;
};

export type AISuggestion = {
  feature: string;
  label: string;
  suggestion: string;
  options?: string[] | null;
  category_slug?: string | null;
  tags?: string[] | null;
  priority?: string | null;
  priority_reason?: string | null;
  articles?: AIArticleSuggestion[] | null;
  seo_title?: string | null;
  seo_description?: string | null;
  suggested_slug?: string | null;
  og_description?: string | null;
  social_snippets?: AISocialSnippet[] | null;
  announcement_subject?: string | null;
  announcement_email_body?: string | null;
  announcement_whatsapp_body?: string | null;
  sponsorship_pitch_title?: string | null;
  sponsorship_short_pitch?: string | null;
  sponsorship_value_bullets?: string | null;
  sponsorship_audience_summary?: string | null;
  sponsorship_package_wording?: string | null;
  sponsorship_follow_up_message?: string | null;
  provider: string;
  model_name: string | null;
  used_fallback: boolean;
  fallback_reason?: string | null;
  requires_human_confirmation: boolean;
  can_auto_publish: boolean;
  can_auto_send: boolean;
  can_modify_finance: boolean;
  draft_only?: boolean;
  disclaimer?: string;
  usage_log_id: string;
  created_at: string;
  redaction_applied?: boolean;
};

export type AIStatus = {
  enabled: boolean;
  provider: string;
  model: string;
  rate_limit_per_hour: number;
  kill_switch?: boolean;
  disabled_by_environment?: boolean;
  ai_enabled_setting?: boolean | null;
  status_label?: string | null;
};

export type AIAdminOverview = {
  brand: string;
  global_ai: {
    enabled: boolean;
    ai_enabled_setting: boolean;
    kill_switch: boolean;
    disabled_by_environment: boolean;
    status_label: string;
    can_override_kill_switch: boolean;
  };
  provider: {
    provider: string;
    model: string;
    base_url: string;
    allowed_providers: string[];
  };
  api_key: {
    configured: boolean;
    source: string;
    editable: boolean;
    masked: string | null;
    last_four: string | null;
    note: string;
  };
  spend: AISpendStatus;
  rate_limit_per_hour: number;
  control_center?: {
    providers_configured: number;
    providers_enabled: number;
    providers_healthy: number;
    features_enabled: number;
    routing_gaps: number;
    requests_this_month: number;
    success_rate_pct: number | null;
    estimated_cost_micros: number;
    average_latency_ms: number | null;
    validation_failures: number;
    redaction_applied_count: number;
    fallback_usage: number;
    recent_failure_count: number;
  };
};

export type AISpendStatus = {
  monthly_spend_cap_micros: number | null;
  warning_threshold_pct: number;
  hard_stop_threshold_pct: number;
  hard_stop_enabled: boolean;
  allow_template_fallback_when_capped: boolean;
  month_start?: string;
  spent_micros_this_month?: number;
  spend_pct_of_cap?: number | null;
  warning_reached?: boolean;
  hard_blocked?: boolean;
};

export type AIProviderProfile = {
  id: string;
  provider_type: string;
  display_name: string;
  base_url: string | null;
  default_model: string | null;
  available_models: string[];
  is_enabled: boolean;
  priority: number;
  timeout_seconds: number;
  max_tokens_default: number;
  rate_limit_per_minute: number | null;
  monthly_spend_limit_micros: number | null;
  notes: string | null;
  health_status: string;
  api_key_status: {
    configured: boolean;
    source: string;
    editable: boolean;
    masked: string | null;
    last_four: string | null;
    note?: string;
  };
  use_env_api_key: boolean;
  created_at: string | null;
  updated_at: string | null;
};

export type AIFeatureReadiness = {
  backend_allowlist: boolean;
  prompt_template: boolean;
  context_builder: boolean;
  redaction_rules: boolean;
  output_validation: boolean;
  frontend_ui: boolean;
  audit_usage_logging: boolean;
  safe_to_enable: boolean;
};

export type AIFeatureRoute = {
  feature_key: string;
  label: string;
  category: string;
  future: boolean;
  enabled: boolean;
  status: string;
  product_status: string;
  operational_status: string;
  readiness: AIFeatureReadiness;
  safety_review_required: boolean;
  safety_note: string | null;
  future_helper_text: string | null;
  routing_editable: boolean;
  docs_reference: string;
  primary_provider_id: string | null;
  primary_provider_name: string | null;
  primary_model: string | null;
  primary_model_label?: string;
  fallback_provider_id: string | null;
  fallback_provider_name: string | null;
  fallback_model: string | null;
  fallback_model_label?: string;
  template_fallback_enabled: boolean;
  daily_request_limit: number | null;
  monthly_request_limit: number | null;
  max_tokens: number | null;
  monthly_spend_cap_micros: number | null;
  requires_human_review: boolean;
  human_review_locked: boolean;
  allowed_permissions: string[];
  last_used_at: string | null;
};

export type AISafetyOverview = {
  kill_switch_active: boolean;
  global_ai_enabled: boolean;
  redaction_enabled: boolean;
  output_validation_enabled: boolean;
  human_review_default: boolean;
  audit_logging_enabled: boolean;
  retention_policy: string;
  enabled_feature_count: number;
  total_managed_features: number;
  disabled_features: string[];
  env_disabled_features: string[];
  future_features: string[];
  denylisted_data_classes: string[];
  product_rules: string[];
  status_label: string;
  api_key_banner?: string;
};

export type AIFeatureConfig = {
  feature_key: string;
  label: string;
  group: string;
  enabled: boolean;
  enabled_in_db: boolean;
  env_disabled: boolean;
  allowed_permissions: string[];
  daily_request_limit: number | null;
  monthly_request_limit: number | null;
  token_limit_per_request: number | null;
  requires_human_review: boolean;
  status: string;
  updated_at: string | null;
};

export type AITestConnectionResult = {
  ok: boolean;
  status: string;
  message: string;
  provider: string | null;
  model: string | null;
  used_fallback: boolean;
  latency_ms: number | null;
  api_key_configured: boolean;
};

export type AIUsageDashboard = {
  date_from: string;
  date_to: string | null;
  total_requests: number;
  success_count: number;
  failure_count: number;
  success_rate: number | null;
  estimated_cost_micros: number;
  average_latency_ms: number | null;
  validation_failures: number;
  redaction_applied_count: number;
  fallback_usage: number;
  by_feature: Array<{
    feature_key: string;
    requests: number;
    success: number;
    cost_micros: number;
  }>;
  by_provider_model: Array<{
    provider: string;
    model: string | null;
    requests: number;
    success: number;
    cost_micros: number;
  }>;
  top_users: Array<{ user_id: string; requests: number }>;
  top_hosts: Array<{ host_id: string; requests: number }>;
  spend: AISpendStatus;
};

export type AISafeLog = {
  id: string;
  feature_key: string;
  actor_user_id: string | null;
  host_id: string | null;
  resource_type: string | null;
  resource_id: string | null;
  provider: string;
  model: string | null;
  status: string;
  used_fallback: boolean;
  latency_ms: number | null;
  estimated_cost_micros: number | null;
  validation_result: string | null;
  redaction_applied: boolean;
  created_at: string | null;
};
