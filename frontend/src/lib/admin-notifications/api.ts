import { apiRequest } from "@/lib/api";

export type NotificationChannels = {
  in_app: boolean;
  push: boolean;
  email: boolean;
};

export type AdminNotificationSetting = {
  id: string;
  type_key: string;
  label: string;
  description: string;
  critical: boolean;
  enabled: boolean;
  channels: NotificationChannels;
  push_unavailable_reason?: string | null;
  audience: string;
  template_id: string | null;
  cooldown_seconds: number;
  send_mode: string;
  classification: string;
  respect_user_prefs: boolean;
  audience_filters: Record<string, unknown>;
  updated_at?: string;
};

export type AdminNotificationTemplate = {
  id: string;
  type_key: string | null;
  name: string;
  title_template: string;
  body_template: string;
  cta_text: string | null;
  cta_url_template: string | null;
  email_template_key: string | null;
  is_system: boolean;
  archived_at: string | null;
};

export type AdminNotificationCampaign = {
  id: string;
  title: string;
  body: string;
  cta_text: string | null;
  cta_url: string | null;
  channels: NotificationChannels;
  audience_mode: string;
  audience_filters: Record<string, unknown>;
  status: string;
  scheduled_at: string | null;
  sent_at: string | null;
  recipient_count: number;
  created_by_admin_id: string;
  created_at: string;
};

export type CampaignDelivery = {
  id: string;
  type_key: string;
  recipient_user_id: string;
  channel: string;
  status: string;
  error_reason: string | null;
  sent_at: string | null;
  failed_at: string | null;
  created_at: string;
};

export type NotificationUserHit = {
  id: string;
  full_name: string;
  email: string;
  roles: string[];
};

export async function fetchAdminNotificationSettings() {
  return apiRequest<AdminNotificationSetting[]>(
    "/admin/notifications/settings",
  );
}

export async function updateAdminNotificationSetting(
  typeKey: string,
  body: Partial<{
    enabled: boolean;
    channels: Partial<NotificationChannels>;
    audience: string;
    cooldown_seconds: number;
    send_mode: string;
    classification: string;
    respect_user_prefs: boolean;
  }>,
) {
  return apiRequest<AdminNotificationSetting>(
    `/admin/notifications/settings/${encodeURIComponent(typeKey)}`,
    { method: "PUT", body },
  );
}

export async function fetchAdminNotificationTemplates() {
  return apiRequest<AdminNotificationTemplate[]>(
    "/admin/notifications/templates",
  );
}

export async function createAdminNotificationTemplate(body: {
  name: string;
  title_template: string;
  body_template: string;
  type_key?: string;
  cta_text?: string;
  cta_url_template?: string;
}) {
  return apiRequest<AdminNotificationTemplate>(
    "/admin/notifications/templates",
    { method: "POST", body },
  );
}

export async function fetchAdminNotificationCampaigns() {
  return apiRequest<AdminNotificationCampaign[]>(
    "/admin/notifications/campaigns",
  );
}

export async function createAdminNotificationCampaign(
  body: Record<string, unknown>,
) {
  return apiRequest<AdminNotificationCampaign>(
    "/admin/notifications/campaigns",
    { method: "POST", body },
  );
}

export async function sendAdminNotificationCampaign(id: string) {
  return apiRequest<{ campaign: AdminNotificationCampaign; delivery: unknown }>(
    `/admin/notifications/campaigns/${id}/send`,
    { method: "POST" },
  );
}

export async function testAdminNotificationCampaign(id: string) {
  return apiRequest<Record<string, unknown>>(
    `/admin/notifications/campaigns/${id}/test`,
    { method: "POST" },
  );
}

export async function fetchAdminCampaignDeliveries(id: string) {
  return apiRequest<CampaignDelivery[]>(
    `/admin/notifications/campaigns/${id}/deliveries`,
  );
}

export async function previewAdminNotificationAudience(body: {
  audience_mode: string;
  audience_filters?: Record<string, unknown>;
  user_ids?: string[];
}) {
  return apiRequest<{ count: number; sample: unknown[] }>(
    "/admin/notifications/audience/preview",
    { method: "POST", body },
  );
}

export async function searchAdminNotificationUsers(q: string) {
  const qs = new URLSearchParams({ q, limit: "30" });
  return apiRequest<NotificationUserHit[]>(
    `/admin/notifications/users/search?${qs}`,
  );
}
