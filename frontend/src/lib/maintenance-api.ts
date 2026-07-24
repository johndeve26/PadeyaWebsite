import { apiRequest } from "@/lib/api";

export type MaintenanceMode =
  | "off"
  | "scheduled"
  | "active"
  | "read_only"
  | "section_only";

export type MaintenanceSettings = {
  id: string;
  mode: MaintenanceMode | string;
  title: string;
  message: string;
  expected_back_at?: string | null;
  timezone: string;
  show_countdown: boolean;
  allow_admin_panel: boolean;
  updated_at?: string | null;
};

export type MaintenanceSection = {
  id: string;
  section_key: string;
  label: string;
  description?: string;
  enabled: boolean;
  mode: "maintenance" | "read_only" | string;
  title: string;
  message: string;
  starts_at?: string | null;
  ends_at?: string | null;
  affected_routes?: string[];
  affected_api_scopes?: string[];
};

export type MaintenanceDashboard = {
  settings: MaintenanceSettings;
  sections: MaintenanceSection[];
  section_catalog: Array<{
    key: string;
    label: string;
    description: string;
  }>;
  modes: string[];
  section_modes: string[];
  schedules: Array<{
    id: string;
    status: string;
    target_mode: string;
    title: string;
    starts_at: string;
    ends_at?: string | null;
    show_countdown: boolean;
  }>;
};

export type PublicMaintenanceStatus = {
  mode: string;
  maintenance: boolean;
  title: string;
  message: string;
  expected_back_at?: string | null;
  timezone?: string;
  show_countdown?: boolean;
  sections?: Array<{
    key: string;
    label: string;
    mode: string;
    title: string;
    message: string;
  }>;
  upcoming_schedule?: {
    id: string;
    title: string;
    starts_at: string;
    ends_at?: string | null;
    show_countdown: boolean;
  } | null;
};

export function fetchMaintenanceAdmin() {
  return apiRequest<MaintenanceDashboard>("/admin/platform/maintenance");
}

export function patchMaintenanceSettings(body: Partial<MaintenanceSettings>) {
  return apiRequest<MaintenanceSettings>("/admin/platform/maintenance", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function patchMaintenanceSection(
  sectionKey: string,
  body: Partial<MaintenanceSection>,
) {
  return apiRequest<MaintenanceSection>(
    `/admin/platform/maintenance/sections/${encodeURIComponent(sectionKey)}`,
    { method: "PATCH", body: JSON.stringify(body) },
  );
}

export function createMaintenanceSchedule(body: Record<string, unknown>) {
  return apiRequest<{ id: string; status: string }>(
    "/admin/platform/maintenance/schedules",
    { method: "POST", body: JSON.stringify(body) },
  );
}

export function cancelMaintenanceSchedule(id: string) {
  return apiRequest<{ status: string }>(
    `/admin/platform/maintenance/schedules/${id}/cancel`,
    { method: "POST" },
  );
}

export function fetchMaintenanceHistory() {
  return apiRequest<{ items: Array<Record<string, unknown>> }>(
    "/admin/platform/maintenance/history",
  );
}

export function fetchMaintenanceNotifications() {
  return apiRequest<{ items: Array<Record<string, unknown>> }>(
    "/admin/platform/maintenance/notifications",
  );
}

export function createMaintenanceNotification(body: Record<string, unknown>) {
  return apiRequest<Record<string, unknown>>(
    "/admin/platform/maintenance/notifications",
    { method: "POST", body: JSON.stringify(body) },
  );
}

export function testMaintenanceNotification(body: Record<string, unknown>) {
  return apiRequest<{ ok: boolean; delivery_count: number }>(
    "/admin/platform/maintenance/notifications/test",
    { method: "POST", body: JSON.stringify(body) },
  );
}

export function createMaintenanceBypass(hours = 8) {
  return apiRequest<{
    token: string;
    expires_at: string;
    header: string;
    warning: string;
  }>(`/admin/platform/maintenance/bypass?hours=${hours}`, { method: "POST" });
}

export function fetchPublicMaintenanceStatus() {
  return apiRequest<PublicMaintenanceStatus>("/maintenance/status");
}
