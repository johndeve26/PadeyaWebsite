import { apiRequest } from "@/lib/api";
import type { RecipientMode } from "@/lib/admin-email-recipients";

export type { RecipientMode } from "@/lib/admin-email-recipients";

export type EmailPreferences = {
  email_ticket_updates: boolean;
  email_merch_updates: boolean;
  email_event_reminders: boolean;
  email_messages: boolean;
  email_fan_connect: boolean;
  email_sponsor_updates: boolean;
  email_host_activity: boolean;
  email_marketing: boolean;
  email_security: boolean;
  unsubscribed_marketing_at?: string | null;
};

export type EmailEvent = {
  id: string;
  template: string;
  recipient_email: string;
  recipient_user_id: string | null;
  subject: string;
  status: string;
  provider: string | null;
  provider_message_id: string | null;
  error_message: string | null;
  attempts: number;
  last_attempt_at: string | null;
  sent_at: string | null;
  dedupe_key: string | null;
  preference_key: string | null;
  created_at: string;
  updated_at: string;
  body_text?: string | null;
  body_html?: string | null;
};

export async function fetchEmailPreferences(): Promise<EmailPreferences> {
  return apiRequest<EmailPreferences>("/email/preferences");
}

export async function updateEmailPreferences(
  patch: Partial<EmailPreferences>,
): Promise<EmailPreferences> {
  return apiRequest<EmailPreferences>("/email/preferences", {
    method: "PATCH",
    body: patch,
  });
}

export async function unsubscribeWithToken(
  token: string,
  marketingOnly = true,
): Promise<EmailPreferences> {
  return apiRequest<EmailPreferences>("/email/unsubscribe", {
    method: "POST",
    body: { token, marketing_only: marketingOnly },
    auth: false,
  });
}

export async function fetchEmailPreferencesByToken(
  token: string,
): Promise<EmailPreferences> {
  return apiRequest<EmailPreferences>(
    `/email/preferences/by-token?token=${encodeURIComponent(token)}`,
    { auth: false },
  );
}

export async function updateEmailPreferencesByToken(
  token: string,
  patch: Partial<EmailPreferences>,
): Promise<EmailPreferences> {
  return apiRequest<EmailPreferences>(
    `/email/preferences/by-token?token=${encodeURIComponent(token)}`,
    { method: "PATCH", body: patch, auth: false },
  );
}

export async function fetchAdminEmails(params?: {
  status?: string;
  template?: string;
  limit?: number;
}): Promise<{ items: EmailEvent[]; total: number }> {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.template) search.set("template", params.template);
  if (params?.limit) search.set("limit", String(params.limit));
  const q = search.toString();
  return apiRequest<{ items: EmailEvent[]; total: number }>(
    `/admin/emails${q ? `?${q}` : ""}`,
  );
}

export async function fetchAdminEmail(id: string): Promise<EmailEvent> {
  return apiRequest<EmailEvent>(`/admin/emails/${id}`);
}

export async function resendAdminEmail(id: string): Promise<{ id: string; status: string }> {
  return apiRequest<{ id: string; status: string }>(`/admin/emails/${id}/resend`, {
    method: "POST",
  });
}

export type EmailProviderSettings = {
  id: string;
  provider: string;
  is_active: boolean;
  email_enabled: boolean;
  dev_mode: boolean;
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_use_tls: boolean;
  smtp_use_ssl: boolean;
  smtp_from_email: string | null;
  smtp_from_name: string | null;
  smtp_reply_to: string | null;
  smtp_username_masked: string | null;
  smtp_username_last4: string | null;
  smtp_password_configured: boolean;
  smtp_password_last4: string | null;
  smtp_password_hint: string | null;
  last_test_status: string | null;
  last_test_error: string | null;
  last_test_at: string | null;
  last_successful_send_at: string | null;
  pending_emails_count: number;
  failed_emails_count: number;
  created_by_user_id: string | null;
  updated_by_user_id: string | null;
  created_at: string;
  updated_at: string;
  source: string;
};

export type EmailProviderSettingsUpdate = {
  provider?: string;
  email_enabled?: boolean;
  dev_mode?: boolean;
  smtp_host?: string | null;
  smtp_port?: number | null;
  smtp_use_tls?: boolean;
  smtp_use_ssl?: boolean;
  smtp_from_email?: string | null;
  smtp_from_name?: string | null;
  smtp_reply_to?: string | null;
  smtp_username?: string | null;
  smtp_password?: string | null;
  clear_smtp_password?: boolean;
  clear_smtp_username?: boolean;
};

export type EmailSettingsTestResult = {
  ok: boolean;
  status?: string | null;
  error?: string | null;
  provider?: string | null;
  skipped?: boolean | null;
  delivered_to_inbox?: boolean | null;
  to?: string | null;
  smtp_host?: string | null;
  smtp_port?: number | null;
  email_event_id?: string | null;
};

export async function fetchEmailProviderSettings(): Promise<EmailProviderSettings> {
  return apiRequest<EmailProviderSettings>("/admin/email/settings");
}

export async function updateEmailProviderSettings(
  patch: EmailProviderSettingsUpdate,
): Promise<EmailProviderSettings> {
  return apiRequest<EmailProviderSettings>("/admin/email/settings", {
    method: "PATCH",
    body: patch,
  });
}

export async function sendEmailSettingsTest(
  testRecipientEmail?: string,
): Promise<EmailSettingsTestResult> {
  return apiRequest<EmailSettingsTestResult>("/admin/email/settings/test", {
    method: "POST",
    body: testRecipientEmail
      ? { test_recipient_email: testRecipientEmail }
      : {},
  });
}

export async function disableEmailProviderSettings(): Promise<EmailProviderSettings> {
  return apiRequest<EmailProviderSettings>("/admin/email/settings/disable", {
    method: "POST",
  });
}

export async function activateEmailProviderSettings(
  settingsId?: string,
): Promise<EmailProviderSettings> {
  return apiRequest<EmailProviderSettings>("/admin/email/settings/activate", {
    method: "POST",
    body: settingsId ? { settings_id: settingsId } : {},
  });
}

export type AdminEmailTemplate = {
  key: string;
  title: string;
  category: string;
  is_required: boolean;
  is_enabled: boolean;
  default_enabled: boolean;
  recipient_mode: RecipientMode;
  recipient_group: string;
  default_recipient_group: string;
  custom_recipient_emails: string[];
  recipient_emails_display: string | null;
  resolved_recipient_count: number;
  max_recipients: number;
  delivery_mode: string;
  threshold_amount: number | null;
  variables: string[];
  subject: string;
  default_subject: string;
  preview_text: string;
  default_preview_text: string;
  headline: string;
  html_body?: string | null;
  text_body?: string | null;
  registry_subject: string;
  updated_at: string;
  updated_by_admin_id: string | null;
};

export type AdminEmailNotificationSettings = {
  master_enabled: boolean;
  digest_enabled: boolean;
  digest_hour_utc: number;
  updated_at: string;
};

export async function fetchAdminEmailTemplates(params?: {
  category?: string;
  q?: string;
}): Promise<AdminEmailTemplate[]> {
  const search = new URLSearchParams();
  if (params?.category) search.set("category", params.category);
  if (params?.q) search.set("q", params.q);
  const q = search.toString();
  const data = await apiRequest<{ items: AdminEmailTemplate[] }>(
    `/admin/emails/templates${q ? `?${q}` : ""}`,
  );
  return data.items;
}

export async function fetchAdminEmailTemplate(
  key: string,
): Promise<AdminEmailTemplate> {
  return apiRequest<AdminEmailTemplate>(`/admin/emails/templates/${encodeURIComponent(key)}`);
}

export async function updateAdminEmailTemplate(
  key: string,
  patch: Partial<{
    subject: string;
    preview_text: string;
    html_body: string;
    text_body: string;
    is_enabled: boolean;
    recipient_mode: RecipientMode;
    recipient_group: string;
    recipient_emails: string;
    custom_recipient_emails: string[];
    delivery_mode: string;
    threshold_amount: number | null;
  }>,
): Promise<AdminEmailTemplate> {
  return apiRequest<AdminEmailTemplate>(
    `/admin/emails/templates/${encodeURIComponent(key)}`,
    { method: "PATCH", body: patch },
  );
}

export async function restoreAdminEmailTemplate(key: string): Promise<AdminEmailTemplate> {
  return apiRequest<AdminEmailTemplate>(
    `/admin/emails/templates/${encodeURIComponent(key)}/restore-default`,
    { method: "POST" },
  );
}

export async function previewAdminEmailTemplate(
  key: string,
  context?: Record<string, string>,
): Promise<{ subject: string; text: string; html: string }> {
  return apiRequest(`/admin/emails/templates/${encodeURIComponent(key)}/preview`, {
    method: "POST",
    body: { context: context ?? null },
  });
}

export async function testSendAdminEmailTemplate(
  key: string,
  options?: { context?: Record<string, string>; test_recipient_emails?: string },
): Promise<{ recipient_count: number }> {
  return apiRequest<{ recipient_count: number }>(
    `/admin/emails/templates/${encodeURIComponent(key)}/test-send`,
    {
      method: "POST",
      body: {
        context: options?.context ?? null,
        test_recipient_emails: options?.test_recipient_emails ?? null,
      },
    },
  );
}

export async function fetchAdminEmailNotificationSettings(): Promise<AdminEmailNotificationSettings> {
  return apiRequest<AdminEmailNotificationSettings>("/admin/emails/notification-settings");
}

export async function updateAdminEmailNotificationSettings(
  patch: Partial<AdminEmailNotificationSettings>,
): Promise<AdminEmailNotificationSettings> {
  return apiRequest<AdminEmailNotificationSettings>("/admin/emails/notification-settings", {
    method: "PATCH",
    body: patch,
  });
}
