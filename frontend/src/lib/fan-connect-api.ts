import { apiRequest } from "@/lib/api";
import type {
  CanConnect,
  ConnectEvent,
  FanConnectAdminBlock,
  FanConnectAdminOverview,
  FanConnectAdminReport,
  FanConnectAdminUserHistory,
  FanConnectSettings,
  FanConnectSuggestionsPage,
  FanConnection,
} from "@/lib/types/fan-connect";

export async function fetchFanConnectSettings(): Promise<FanConnectSettings> {
  return apiRequest("/fan-connect/settings");
}

export async function updateFanConnectSettings(
  body: Partial<FanConnectSettings>,
): Promise<FanConnectSettings> {
  return apiRequest("/fan-connect/settings", { method: "PATCH", body });
}

export async function fetchCanConnect(username: string): Promise<CanConnect> {
  return apiRequest(`/fan-connect/can-connect/${encodeURIComponent(username)}`);
}

export async function createConnectRequest(body: {
  username: string;
  message?: string;
  context_event_id?: string;
}): Promise<FanConnection> {
  return apiRequest("/fan-connect/requests", { method: "POST", body });
}

export async function fetchConnectRequests(
  box: "incoming" | "outgoing",
): Promise<{ items: FanConnection[] }> {
  return apiRequest(`/fan-connect/requests?box=${box}`);
}

export async function acceptConnectRequest(
  id: string,
): Promise<FanConnection> {
  return apiRequest(`/fan-connect/requests/${encodeURIComponent(id)}/accept`, {
    method: "POST",
  });
}

export async function declineConnectRequest(
  id: string,
  body?: { cooldown_days?: number | null },
): Promise<FanConnection> {
  const payload =
    body?.cooldown_days != null ? { cooldown_days: body.cooldown_days } : {};
  return apiRequest(`/fan-connect/requests/${encodeURIComponent(id)}/decline`, {
    method: "POST",
    body: payload,
  });
}

export async function fetchDeclineCooldownOptions(): Promise<{
  default_cooldown_days: number;
  selectable_days: number[];
}> {
  return apiRequest("/fan-connect/decline-cooldown-options");
}

export async function fetchAdminFanConnectSettings(): Promise<{
  decline_cooldown_days_default: number;
  decline_cooldown_days_min: number;
  decline_cooldown_days_max: number;
  decline_cooldown_user_options: number[];
}> {
  return apiRequest("/admin/fan-connect/settings");
}

export async function updateAdminFanConnectSettings(body: {
  decline_cooldown_days_default: number;
}): Promise<Awaited<ReturnType<typeof fetchAdminFanConnectSettings>>> {
  return apiRequest("/admin/fan-connect/settings", {
    method: "PATCH",
    body,
  });
}

export async function cancelConnectRequest(
  id: string,
): Promise<FanConnection> {
  return apiRequest(`/fan-connect/requests/${encodeURIComponent(id)}/cancel`, {
    method: "POST",
  });
}

export async function fetchConnections(): Promise<{ items: FanConnection[] }> {
  return apiRequest("/fan-connect/connections");
}

export async function removeConnection(
  id: string,
): Promise<FanConnection> {
  return apiRequest(
    `/fan-connect/connections/${encodeURIComponent(id)}/remove`,
    { method: "POST" },
  );
}

export async function blockFanConnect(body: {
  username: string;
  reason?: string;
}): Promise<void> {
  await apiRequest("/fan-connect/block", { method: "POST", body });
}

export async function reportFanConnect(body: {
  username: string;
  reason: string;
  details?: string;
  connection_id?: string;
  thread_id?: string;
}): Promise<{ id: string; status: string; reason: string; created_at: string }> {
  return apiRequest("/fan-connect/report", { method: "POST", body });
}

export async function fetchConnectSuggestions(params?: {
  eventId?: string;
  category?: string;
  city?: string;
  area?: string;
  mode?: string;
  lat?: number;
  lng?: number;
  radiusKm?: number;
  limit?: number;
  page?: number;
  cursor?: string;
}): Promise<FanConnectSuggestionsPage> {
  const sp = new URLSearchParams();
  if (params?.eventId) sp.set("event_id", params.eventId);
  if (params?.category) sp.set("category", params.category);
  if (params?.city) sp.set("city", params.city);
  if (params?.area) sp.set("area", params.area);
  if (params?.mode) sp.set("mode", params.mode);
  if (params?.lat != null) sp.set("lat", String(params.lat));
  if (params?.lng != null) sp.set("lng", String(params.lng));
  if (params?.radiusKm != null) sp.set("radius_km", String(params.radiusKm));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  if (params?.page != null) sp.set("page", String(params.page));
  if (params?.cursor) sp.set("cursor", params.cursor);
  const qs = sp.toString();
  return apiRequest(`/fan-connect/suggestions${qs ? `?${qs}` : ""}`, {
    timeout: "long",
  });
}

export async function dismissConnectSuggestion(
  userId: string,
  body?: { reason?: string },
): Promise<{ ok: boolean; target_user_id: string }> {
  return apiRequest(
    `/fan-connect/suggestions/${encodeURIComponent(userId)}/dismiss`,
    { method: "POST", body: body ?? {} },
  );
}

export async function moreLikeThisSuggestion(
  userId: string,
): Promise<{ ok: boolean; target_user_id: string }> {
  return apiRequest(
    `/fan-connect/suggestions/${encodeURIComponent(userId)}/more-like-this`,
    { method: "POST" },
  );
}

export async function fetchFanConnectLocationPreference(): Promise<
  import("@/lib/types/fan-connect").FanConnectLocationPreference | null
> {
  return apiRequest("/fan-connect/location/preference");
}

export async function saveFanConnectLocationPreference(body: {
  city?: string;
  area?: string;
  country?: string;
  latitude_approx?: string;
  longitude_approx?: string;
  precision?: string;
}): Promise<import("@/lib/types/fan-connect").FanConnectLocationPreference> {
  return apiRequest("/fan-connect/location/preference", {
    method: "POST",
    body,
  });
}

export async function clearFanConnectLocationPreference(): Promise<void> {
  await apiRequest("/fan-connect/location/preference", { method: "DELETE" });
}

export async function fetchEventFanConnect(
  eventSlug: string,
  params?: { limit?: number; page?: number },
): Promise<FanConnectSuggestionsPage> {
  const sp = new URLSearchParams();
  if (params?.limit != null) sp.set("limit", String(params.limit));
  if (params?.page != null) sp.set("page", String(params.page));
  const qs = sp.toString();
  return apiRequest(
    `/events/${encodeURIComponent(eventSlug)}/fan-connect${qs ? `?${qs}` : ""}`,
  );
}

export async function fetchConnectEvents(): Promise<{ items: ConnectEvent[] }> {
  return apiRequest("/fan-connect/events");
}

export async function fetchAdminFanConnectOverview(): Promise<FanConnectAdminOverview> {
  return apiRequest("/admin/fan-connect/overview");
}

export async function fetchAdminFanConnectBlocks(): Promise<{
  items: FanConnectAdminBlock[];
  total: number;
}> {
  return apiRequest("/admin/fan-connect/blocks");
}

export async function fetchAdminFanConnectReports(params?: {
  status?: string;
}): Promise<{
  items: FanConnectAdminReport[];
  total: number;
}> {
  const sp = new URLSearchParams();
  if (params?.status) sp.set("status", params.status);
  const qs = sp.toString();
  return apiRequest(`/admin/fan-connect/reports${qs ? `?${qs}` : ""}`);
}

export async function fetchAdminFanConnectReport(
  reportId: string,
): Promise<FanConnectAdminReport> {
  return apiRequest(
    `/admin/fan-connect/reports/${encodeURIComponent(reportId)}`,
  );
}

export async function resolveAdminFanConnectReport(
  reportId: string,
  body: { resolution: "resolved" | "dismissed"; admin_notes?: string },
): Promise<FanConnectAdminReport> {
  return apiRequest(
    `/admin/fan-connect/reports/${encodeURIComponent(reportId)}/resolve`,
    { method: "POST", body },
  );
}

export async function fetchAdminFanConnectUserHistory(
  userId: string,
): Promise<FanConnectAdminUserHistory> {
  return apiRequest(
    `/admin/fan-connect/users/${encodeURIComponent(userId)}/moderation`,
  );
}

export async function disableAdminFanConnectUser(
  userId: string,
  body?: { reason?: string },
): Promise<{ user_id: string; disabled: boolean }> {
  return apiRequest(
    `/admin/fan-connect/users/${encodeURIComponent(userId)}/disable`,
    { method: "POST", body: body ?? {} },
  );
}
