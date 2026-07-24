import { apiRequest } from "@/lib/api";
import type {
  AIAdminOverview,
  AIFeature,
  AIFeatureConfig,
  AIFeatureRoute,
  AIProviderProfile,
  AISafeLog,
  AISafetyOverview,
  AISpendStatus,
  AIStatus,
  AISuggestion,
  AITestConnectionResult,
  AIUsageDashboard,
} from "@/lib/types/ai";

export async function fetchAIStatus(): Promise<AIStatus> {
  return apiRequest<AIStatus>("/ai/status", { auth: false });
}

export async function fetchHostAIFeatures(): Promise<AIFeature[]> {
  return apiRequest<AIFeature[]>("/ai/host/features");
}

export async function generateHostAI(payload: {
  feature: string;
  event_id?: string;
  merch_product_id?: string;
  notes?: string;
  extra?: Record<string, string>;
}): Promise<AISuggestion> {
  return apiRequest<AISuggestion>("/ai/host/generate", {
    method: "POST",
    body: payload,
  });
}

export async function generateHostEventAI(
  eventId: string,
  payload: {
    feature: string;
    notes?: string;
    extra?: Record<string, string>;
    merch_product_id?: string;
  },
): Promise<AISuggestion> {
  return apiRequest<AISuggestion>(`/ai/host/events/${eventId}/generate`, {
    method: "POST",
    body: payload,
  });
}

export async function recordHostAIGenerationFeedback(payload: {
  usage_log_id: string;
  action: "accepted" | "applied" | "rejected" | "dismissed";
  event_id?: string;
  merch_product_id?: string;
  applied_field?: string;
  selected_option?: string;
}): Promise<{ ok: boolean; action: string; usage_log_id: string }> {
  return apiRequest("/ai/host/generation-feedback", {
    method: "POST",
    body: payload,
  });
}

export async function generateFanPassportAI(payload: {
  feature?: string;
  notes?: string;
  extra?: Record<string, string>;
}): Promise<AISuggestion> {
  return apiRequest<AISuggestion>("/ai/fan/passport/generate", {
    method: "POST",
    body: { feature: "fan.passport.bio", ...payload },
  });
}

export async function recordFanAIGenerationFeedback(payload: {
  usage_log_id: string;
  action: "accepted" | "applied" | "rejected" | "dismissed";
  applied_field?: string;
  selected_option?: string;
}): Promise<{ ok: boolean; action: string; usage_log_id: string }> {
  return apiRequest("/ai/fan/generation-feedback", {
    method: "POST",
    body: payload,
  });
}

export async function fetchAdminAIFeatures(): Promise<AIFeature[]> {
  return apiRequest<AIFeature[]>("/ai/admin/features");
}

export async function generateAdminAI(payload: {
  feature: string;
  notes?: string;
  support_ticket_id?: string;
  blog_post_id?: string;
  extra?: Record<string, string>;
}): Promise<AISuggestion> {
  return apiRequest<AISuggestion>("/ai/admin/generate", {
    method: "POST",
    body: payload,
  });
}

export async function generateSupportTicketAI(
  ticketId: string,
  payload: {
    feature: string;
    notes?: string;
  },
): Promise<AISuggestion> {
  return apiRequest<AISuggestion>(
    `/ai/admin/support/tickets/${ticketId}/generate`,
    {
      method: "POST",
      body: payload,
    },
  );
}

export async function recordAdminAIGenerationFeedback(payload: {
  usage_log_id: string;
  action: "accepted" | "applied" | "rejected" | "dismissed";
  support_ticket_id?: string;
  blog_post_id?: string;
  applied_field?: string;
  selected_option?: string;
}): Promise<{ ok: boolean; action: string; usage_log_id: string }> {
  return apiRequest("/ai/admin/generation-feedback", {
    method: "POST",
    body: payload,
  });
}

export async function generateAdminSupportSummary(
  notes?: string,
): Promise<AISuggestion> {
  const qs = notes ? `?notes=${encodeURIComponent(notes)}` : "";
  return apiRequest<AISuggestion>(`/ai/admin/support/summary${qs}`, {
    method: "POST",
  });
}

export async function fetchAIAdminOverview(): Promise<AIAdminOverview> {
  return apiRequest<AIAdminOverview>("/ai/admin/controls/overview");
}

export async function updateAIAdminSettings(payload: {
  enabled?: boolean;
  provider?: string;
  model?: string;
  base_url?: string;
}): Promise<AIAdminOverview> {
  return apiRequest<AIAdminOverview>("/ai/admin/controls/settings", {
    method: "PATCH",
    body: payload,
  });
}

export async function updateAISpendSettings(payload: {
  monthly_spend_cap_micros?: number | null;
  clear_cap?: boolean;
  warning_threshold_pct?: number;
  hard_stop_threshold_pct?: number;
  hard_stop_enabled?: boolean;
  allow_template_fallback_when_capped?: boolean;
}): Promise<AISpendStatus> {
  return apiRequest<AISpendStatus>("/ai/admin/controls/spend", {
    method: "PATCH",
    body: payload,
  });
}

export async function testAIConnection(): Promise<AITestConnectionResult> {
  return apiRequest<AITestConnectionResult>("/ai/admin/controls/test-connection", {
    method: "POST",
  });
}

export async function fetchAIFeatureConfigs(): Promise<AIFeatureConfig[]> {
  return apiRequest<AIFeatureConfig[]>("/ai/admin/controls/features");
}

export async function updateAIFeatureConfig(
  featureKey: string,
  payload: {
    enabled?: boolean;
    allowed_permissions?: string[];
    daily_request_limit?: number | null;
    monthly_request_limit?: number | null;
    token_limit_per_request?: number | null;
    requires_human_review?: boolean;
    status?: string;
    clear_daily_limit?: boolean;
    clear_monthly_limit?: boolean;
    clear_token_limit?: boolean;
  },
): Promise<AIFeatureConfig> {
  return apiRequest<AIFeatureConfig>(
    `/ai/admin/controls/features/${encodeURIComponent(featureKey)}`,
    {
      method: "PATCH",
      body: payload,
    },
  );
}

export async function fetchAIUsageDashboard(params?: {
  date_from?: string;
  date_to?: string;
}): Promise<AIUsageDashboard> {
  const qs = new URLSearchParams();
  if (params?.date_from) qs.set("date_from", params.date_from);
  if (params?.date_to) qs.set("date_to", params.date_to);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiRequest<AIUsageDashboard>(`/ai/admin/controls/usage${suffix}`);
}

export async function fetchAISafeLogs(params?: {
  limit?: number;
  offset?: number;
  feature_key?: string;
  date_from?: string;
  date_to?: string;
}): Promise<{ items: AISafeLog[]; limit: number; offset: number }> {
  const qs = new URLSearchParams();
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.offset != null) qs.set("offset", String(params.offset));
  if (params?.feature_key) qs.set("feature_key", params.feature_key);
  if (params?.date_from) qs.set("date_from", params.date_from);
  if (params?.date_to) qs.set("date_to", params.date_to);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiRequest(`/ai/admin/controls/logs${suffix}`);
}

export async function fetchAIProviderProfiles(): Promise<AIProviderProfile[]> {
  return apiRequest<AIProviderProfile[]>("/ai/admin/controls/providers");
}

export async function createAIProviderProfile(body: {
  provider_type: string;
  display_name: string;
  base_url?: string;
  default_model?: string;
  available_models?: string[];
  is_enabled?: boolean;
  priority?: number;
  timeout_seconds?: number;
  max_tokens_default?: number;
  use_env_api_key?: boolean;
  notes?: string;
  api_key?: string;
}): Promise<AIProviderProfile> {
  return apiRequest<AIProviderProfile>("/ai/admin/controls/providers", {
    method: "POST",
    body,
  });
}

export async function updateAIProviderProfile(
  id: string,
  body: Partial<{
    display_name: string;
    base_url: string;
    default_model: string;
    available_models: string[];
    is_enabled: boolean;
    priority: number;
    timeout_seconds: number;
    max_tokens_default: number;
    use_env_api_key: boolean;
    notes: string | undefined;
    api_key?: string;
    clear_api_key?: boolean;
  }>,
): Promise<AIProviderProfile> {
  return apiRequest<AIProviderProfile>(`/ai/admin/controls/providers/${id}`, {
    method: "PATCH",
    body,
  });
}

export async function deleteAIProviderProfile(id: string): Promise<void> {
  await apiRequest(`/ai/admin/controls/providers/${id}`, { method: "DELETE" });
}

export async function testAIProviderProfile(
  id: string,
): Promise<Record<string, unknown>> {
  return apiRequest(`/ai/admin/controls/providers/${id}/test`, { method: "POST" });
}

export async function fetchAIFeatureRoutes(): Promise<AIFeatureRoute[]> {
  return apiRequest<AIFeatureRoute[]>("/ai/admin/controls/routes");
}

export async function updateAIFeatureRoute(
  featureKey: string,
  body: Partial<{
    enabled: boolean;
    primary_provider_id: string | null;
    primary_model: string | null;
    fallback_provider_id: string | null;
    fallback_model: string | null;
    template_fallback_enabled: boolean;
    daily_request_limit: number | null;
    monthly_request_limit: number | null;
    max_tokens: number | null;
    requires_human_review: boolean;
    clear_daily_limit: boolean;
    clear_monthly_limit: boolean;
  }>,
): Promise<AIFeatureRoute> {
  return apiRequest<AIFeatureRoute>(
    `/ai/admin/controls/routes/${encodeURIComponent(featureKey)}`,
    { method: "PATCH", body },
  );
}

export async function fetchAISafetyOverview(): Promise<AISafetyOverview> {
  return apiRequest<AISafetyOverview>("/ai/admin/controls/safety");
}
