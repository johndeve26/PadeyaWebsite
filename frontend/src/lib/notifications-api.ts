import { apiRequest } from "@/lib/api";

export type InAppNotification = {
  id: string;
  kind: string;
  title: string;
  body: string;
  link_path: string | null;
  thread_id: string | null;
  read_at: string | null;
  archived_at: string | null;
  popup_shown_at: string | null;
  created_at: string;
};

export type PushPreferences = {
  push_enabled: boolean;
  push_ticket_updates: boolean;
  push_merch_updates: boolean;
  push_event_reminders: boolean;
  push_messages: boolean;
  push_message_previews: boolean;
  push_fan_connect: boolean;
  push_sponsor_updates: boolean;
  push_host_activity: boolean;
  push_reviews: boolean;
  push_marketing: boolean;
  push_security: boolean;
};

export type PushProviderMode = "web_push" | "log";

export type PushProviderSettings = {
  id: string;
  is_active: boolean;
  push_enabled: boolean;
  provider: PushProviderMode | string;
  vapid_public_key: string | null;
  vapid_subject: string | null;
  vapid_private_configured: boolean;
  vapid_private_hint: string | null;
  last_test_status: string | null;
  last_test_error: string | null;
  last_test_at: string | null;
  created_by_user_id?: string | null;
  updated_by_user_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type PushDeliveryEvent = {
  id: string;
  user_id: string | null;
  subscription_id: string | null;
  notification_id: string | null;
  kind: string;
  status: string;
  error_message: string | null;
  created_at: string;
  sent_at: string | null;
};

export type NotificationCategory =
  | "all"
  | "tickets"
  | "merch"
  | "messages"
  | "fan_connect"
  | "host"
  | "sponsor"
  | "admin";

export async function fetchNotifications(params?: {
  limit?: number;
  offset?: number;
  category?: NotificationCategory | string;
  unread_only?: boolean;
}) {
  const q = new URLSearchParams();
  q.set("limit", String(params?.limit ?? 50));
  if (params?.offset != null) q.set("offset", String(params.offset));
  if (params?.category && params.category !== "all") {
    q.set("category", params.category);
  }
  if (params?.unread_only) {
    q.set("unread_only", "true");
  }
  return apiRequest<{
    items: InAppNotification[];
    total: number;
    unread_count: number;
  }>(`/notifications?${q.toString()}`);
}

/** Header bell preview — unread only, newest first. */
export async function fetchUnreadNotificationPreview(limit = 8) {
  return fetchNotifications({ limit, unread_only: true });
}

/** Full inbox route — stays in host workspace when applicable. */
export function notificationsInboxHref(pathname: string): string {
  if (pathname.startsWith("/host")) return "/host/notifications";
  return "/dashboard/notifications";
}

export async function fetchNotificationUnreadCount() {
  return apiRequest<{ unread_count: number }>("/notifications/unread-count");
}

export async function fetchPopupNotifications() {
  return apiRequest<{
    items: InAppNotification[];
    total: number;
    unread_count: number;
  }>("/notifications/popup");
}

export async function ackPopupNotifications(ids: string[]) {
  return apiRequest<{ marked: number }>("/notifications/popup/ack", {
    method: "POST",
    body: { notification_ids: ids },
  });
}

export async function markNotificationRead(id: string) {
  return apiRequest<InAppNotification>(`/notifications/${id}/read`, {
    method: "POST",
  });
}

export async function markAllNotificationsRead() {
  return apiRequest<{ marked: number }>("/notifications/read-all", {
    method: "POST",
  });
}

export async function archiveNotification(id: string) {
  return apiRequest<InAppNotification>(`/notifications/${id}/archive`, {
    method: "POST",
  });
}

/** Refresh header badge + bell preview after inbox mutations. */
export function notifyNotificationsChanged() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("padeya:notifications-changed"));
  }
}

export async function fetchVapidPublicKey() {
  return apiRequest<{ enabled: boolean; public_key: string }>(
    "/push/vapid-public-key",
    { auth: false },
  );
}

export type PushSubscriptionDevice = {
  id: string;
  device_label: string | null;
  platform: string | null;
  user_agent: string | null;
  endpoint_hint: string | null;
  is_active: boolean;
  revoked_at: string | null;
  last_success_at: string | null;
  last_failure_at: string | null;
  failure_count: number;
  created_at: string;
  updated_at: string;
};

export async function fetchPushSubscriptions(includeInactive = false) {
  const q = includeInactive ? "?include_inactive=true" : "";
  return apiRequest<{ items: PushSubscriptionDevice[]; total: number }>(
    `/push/subscriptions${q}`,
  );
}

export async function subscribePush(body: {
  endpoint: string;
  p256dh: string;
  auth: string;
  device_label?: string;
  platform?: string;
}) {
  return apiRequest<PushSubscriptionDevice>("/push/subscriptions", {
    method: "POST",
    body,
  });
}

export async function unsubscribePush(endpoint: string) {
  return apiRequest<{ revoked: boolean }>("/push/subscriptions", {
    method: "DELETE",
    body: { endpoint },
  });
}

export async function removePushSubscription(subscriptionId: string) {
  return apiRequest<{ revoked: boolean }>(
    `/push/subscriptions/${subscriptionId}`,
    { method: "DELETE" },
  );
}

export async function fetchPushPreferences() {
  return apiRequest<PushPreferences>("/push/preferences");
}

export async function updatePushPreferences(patch: Partial<PushPreferences>) {
  return apiRequest<PushPreferences>("/push/preferences", {
    method: "PATCH",
    body: patch,
  });
}

export async function fetchAdminPushSettings() {
  return apiRequest<PushProviderSettings>("/admin/push/settings");
}

export async function updateAdminPushSettings(patch: {
  push_enabled?: boolean;
  provider?: PushProviderMode | string;
  vapid_public_key?: string | null;
  vapid_private_key?: string | null;
  vapid_subject?: string | null;
  generate_vapid_keys?: boolean;
}) {
  return apiRequest<PushProviderSettings>("/admin/push/settings", {
    method: "PATCH",
    body: patch,
  });
}

export async function fetchAdminPushDeliveries(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.limit != null) q.set("limit", String(params.limit));
  if (params?.offset != null) q.set("offset", String(params.offset));
  const suffix = q.toString() ? `?${q}` : "";
  return apiRequest<{
    items: PushDeliveryEvent[];
    total: number;
    summary: Record<string, number>;
  }>(`/admin/push/deliveries${suffix}`);
}

export async function disableAdminPush() {
  return apiRequest<PushProviderSettings>("/admin/push/settings/disable", {
    method: "POST",
  });
}

export type AdminPushTestResult = {
  ok: boolean;
  message?: string;
  user_id?: string;
  email?: string | null;
  provider?: string;
  status?: string | null;
  active_subscription_count?: number;
  has_active_device?: boolean;
  title?: string;
  body?: string;
  action_url?: string;
};

export type AdminPushSubscriptionLookup = {
  user_id: string;
  email: string | null;
  full_name: string | null;
  active_subscription_count: number;
  has_active_device: boolean;
  devices: Array<{
    id: string;
    device_label: string | null;
    platform: string | null;
    endpoint_hint: string | null;
    is_active: boolean;
    last_success_at: string | null;
    last_failure_at: string | null;
    failure_count: number;
  }>;
};

export async function testAdminPush() {
  return apiRequest<AdminPushTestResult>("/admin/push/settings/test", {
    method: "POST",
    body: {},
  });
}

export async function testAdminPushToUser(params: {
  email?: string;
  user_id?: string;
}) {
  return apiRequest<AdminPushTestResult>("/admin/push/settings/test-user", {
    method: "POST",
    body: {
      email: params.email?.trim() || null,
      user_id: params.user_id?.trim() || null,
    },
  });
}

export async function lookupAdminPushSubscriptions(params: {
  email?: string;
  user_id?: string;
}) {
  const q = new URLSearchParams();
  if (params.email?.trim()) q.set("email", params.email.trim());
  if (params.user_id?.trim()) q.set("user_id", params.user_id.trim());
  return apiRequest<AdminPushSubscriptionLookup>(
    `/admin/push/subscriptions/lookup?${q.toString()}`,
  );
}

/** Convert VAPID public key to Uint8Array for PushManager.subscribe */
export function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) {
    output[i] = raw.charCodeAt(i);
  }
  return output;
}
