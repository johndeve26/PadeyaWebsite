import { apiRequest } from "@/lib/api";

/** Value resolution source from the API. */
export type RuntimeSettingSource = "db" | "env" | "default";

/** Optional status enum if backend provides it; otherwise derived client-side. */
export type RuntimeSettingStatus =
  | "missing"
  | "disabled"
  | "needs_configuration"
  | "env_fallback"
  | "db_override"
  | "configured"
  | "ok";

export type RuntimeSettingValueType =
  | "string"
  | "int"
  | "bool"
  | "float"
  | "json"
  | "secret";

export type RuntimeSettingItem = {
  key: string;
  category: string;
  label: string;
  description?: string | null;
  value_type: RuntimeSettingValueType | string;
  /** Non-secret current value (never a raw secret). */
  value?: string | number | boolean | null;
  /** Secret display only — never plaintext. */
  masked_value?: string | null;
  first_four?: string | null;
  last_four?: string | null;
  /** When true, show fingerprint UI instead of raw value (includes plain API keys). */
  fingerprint_display?: boolean;
  configured?: boolean;
  is_secret: boolean;
  editable: boolean;
  source: RuntimeSettingSource | string;
  status?: RuntimeSettingStatus | string | null;
  enabled?: boolean | null;
  restart_required?: boolean;
  last_updated_at?: string | null;
  validation_error?: string | null;
  provider?: string | null;
  /** Admin display unit (e.g. "mb") — value is already converted for the form. */
  admin_unit?: "mb" | string | null;
  validation_schema_json?: {
    min?: number | null;
    max?: number | null;
    unit?: string | null;
    allowed?: string[] | null;
  } | null;
};

export type RuntimeSettingsCategorySummary = {
  category: string;
  label?: string | null;
  description?: string | null;
  configured?: boolean;
  enabled?: boolean | null;
  status?: RuntimeSettingStatus | string | null;
  source?: RuntimeSettingSource | string | null;
  provider?: string | null;
  last_updated_at?: string | null;
  setting_count?: number;
  specialist_href?: string | null;
  testable?: boolean;
};

export type RuntimeSettingsDashboard = {
  categories: RuntimeSettingsCategorySummary[];
  settings?: RuntimeSettingItem[];
  system?: RuntimeSystemStatus | null;
};

export type RuntimeSettingsCategoryResponse = {
  category: string;
  label?: string | null;
  description?: string | null;
  settings: RuntimeSettingItem[];
  specialist_href?: string | null;
  provider?: string | null;
  status?: RuntimeSettingStatus | string | null;
  configured?: boolean;
  enabled?: boolean | null;
  last_updated_at?: string | null;
};

export type RuntimeSystemStatus = {
  version?: string | null;
  build_sha?: string | null;
  last_boot_at?: string | null;
  app_env?: string | null;
  items?: Array<{
    key: string;
    label?: string | null;
    configured?: boolean;
    status?: string | null;
    env_name?: string | null;
    provider?: string | null;
    source?: string | null;
  }>;
};

export type RuntimeSettingUpdateBody = {
  value?: string | number | boolean | null;
  /** Secret replace — omit or blank to keep existing. */
  secret_value?: string | null;
};

export type RuntimeSettingTestResult = {
  ok: boolean;
  message?: string | null;
  status?: string | null;
  detail?: string | null;
};

export type RuntimeSettingsAuditEntry = {
  id: string;
  action: string;
  resource_type?: string | null;
  resource_id?: string | null;
  actor_user_id?: string | null;
  created_at: string;
  metadata?: Record<string, unknown> | null;
  details?: Record<string, unknown> | null;
};

const BASE = "/admin/settings/runtime";

export async function fetchRuntimeSettingsDashboard(): Promise<RuntimeSettingsDashboard> {
  return apiRequest<RuntimeSettingsDashboard>(BASE);
}

export async function fetchRuntimeSettingsCategory(
  category: string,
): Promise<RuntimeSettingsCategoryResponse> {
  return apiRequest<RuntimeSettingsCategoryResponse>(
    `${BASE}/${encodeURIComponent(category)}`,
  );
}

export async function updateRuntimeSetting(
  category: string,
  key: string,
  body: RuntimeSettingUpdateBody,
): Promise<RuntimeSettingItem> {
  return apiRequest<RuntimeSettingItem>(
    `${BASE}/${encodeURIComponent(category)}/${encodeURIComponent(key)}`,
    { method: "PUT", body },
  );
}

export async function clearRuntimeSettingOverride(
  category: string,
  key: string,
): Promise<RuntimeSettingItem | { ok: boolean }> {
  return apiRequest(
    `${BASE}/${encodeURIComponent(category)}/${encodeURIComponent(key)}/override`,
    { method: "DELETE" },
  );
}

export async function testRuntimeSettingsCategory(
  category: string,
  body?: Record<string, unknown>,
): Promise<RuntimeSettingTestResult> {
  return apiRequest<RuntimeSettingTestResult>(
    `${BASE}/${encodeURIComponent(category)}/test`,
    { method: "POST", body: body ?? {} },
  );
}

export async function fetchRuntimeSettingsAudit(params?: {
  limit?: number;
  offset?: number;
  action?: string;
}): Promise<{ items: RuntimeSettingsAuditEntry[]; total?: number }> {
  const search = new URLSearchParams();
  if (params?.limit != null) search.set("limit", String(params.limit));
  if (params?.offset != null) search.set("offset", String(params.offset));
  if (params?.action) search.set("action", params.action);
  const q = search.toString();
  return apiRequest<{ items: RuntimeSettingsAuditEntry[]; total?: number }>(
    `${BASE}/audit${q ? `?${q}` : ""}`,
  );
}
