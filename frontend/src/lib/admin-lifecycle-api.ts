import { apiRequest } from "@/lib/api";
import type {
  AdminUserActivityDetailList,
  AdminUserActivityKind,
  AdminUserActivitySection,
  AdminUserAuditItem,
  AdminUserDetail,
  AdminUserFlag,
  AdminUserList,
  AdminUserNote,
  AdminUserRestriction,
  AuditLog,
  EventCategory,
  UserPublic,
} from "@/lib/types/lifecycle";
import type { EventItem } from "@/lib/types/events";

export async function fetchAdminUsers(params?: {
  q?: string;
  status?: "active" | "inactive" | "all" | string;
  role?: string;
  page?: number;
  limit?: number;
}): Promise<AdminUserList> {
  const search = new URLSearchParams();
  if (params?.q?.trim()) search.set("q", params.q.trim());
  if (params?.status && params.status !== "all") {
    search.set("status", params.status);
  }
  if (params?.role && params.role !== "all") {
    search.set("role", params.role);
  }
  if (params?.page != null) search.set("page", String(params.page));
  if (params?.limit != null) search.set("limit", String(params.limit));
  const q = search.toString();
  return apiRequest<AdminUserList>(`/admin/users${q ? `?${q}` : ""}`);
}

export async function fetchAdminUser(userId: string): Promise<AdminUserDetail> {
  return apiRequest<AdminUserDetail>(`/admin/users/${userId}`);
}

export async function fetchAdminUserActivity(
  userId: string,
): Promise<AdminUserActivitySection> {
  return apiRequest<AdminUserActivitySection>(
    `/admin/users/${userId}/activity`,
  );
}

export async function fetchAdminUserActivityDetail(
  userId: string,
  kind: AdminUserActivityKind,
  params?: { page?: number; limit?: number },
): Promise<AdminUserActivityDetailList> {
  const search = new URLSearchParams();
  if (params?.page != null) search.set("page", String(params.page));
  if (params?.limit != null) search.set("limit", String(params.limit));
  const q = search.toString();
  return apiRequest<AdminUserActivityDetailList>(
    `/admin/users/${userId}/activity/${kind}${q ? `?${q}` : ""}`,
  );
}

export async function fetchAdminUserAudit(
  userId: string,
): Promise<AdminUserAuditItem[]> {
  return apiRequest<AdminUserAuditItem[]>(`/admin/users/${userId}/audit`);
}

export async function lookupAdminUserByEmail(email: string): Promise<UserPublic> {
  const q = new URLSearchParams({ email: email.trim() });
  return apiRequest<UserPublic>(`/users/admin/lookup?${q.toString()}`);
}

export async function fetchAdminCategories(
  includeInactive = false,
): Promise<EventCategory[]> {
  const q = includeInactive ? "?include_inactive=true" : "";
  return apiRequest<EventCategory[]>(`/events/admin/categories${q}`);
}

export async function createAdminCategory(body: {
  name: string;
  slug?: string;
  description?: string;
}): Promise<EventCategory> {
  return apiRequest<EventCategory>("/events/admin/categories", {
    method: "POST",
    body,
  });
}

export async function updateAdminCategory(
  id: string,
  body: { name?: string; description?: string },
): Promise<EventCategory> {
  return apiRequest<EventCategory>(`/events/admin/categories/${id}`, {
    method: "PATCH",
    body,
  });
}

export async function deactivateAdminCategory(id: string): Promise<EventCategory> {
  return apiRequest<EventCategory>(`/events/admin/categories/${id}/deactivate`, {
    method: "POST",
  });
}

export async function restoreAdminCategory(id: string): Promise<EventCategory> {
  return apiRequest<EventCategory>(`/events/admin/categories/${id}/restore`, {
    method: "POST",
  });
}

export async function featureEvent(eventId: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/admin/${eventId}/feature`, {
    method: "POST",
  });
}

export async function unfeatureEvent(eventId: string): Promise<EventItem> {
  return apiRequest<EventItem>(`/events/admin/${eventId}/unfeature`, {
    method: "POST",
  });
}

export async function setEventPadeyaPick(
  eventId: string,
  opts?: { context_type?: string; slot_number?: 1 | 2 },
): Promise<EventItem> {
  const params = new URLSearchParams();
  if (opts?.context_type) params.set("context_type", opts.context_type);
  if (opts?.slot_number != null) {
    params.set("slot_number", String(opts.slot_number));
  }
  const qs = params.toString();
  return apiRequest<EventItem>(
    `/events/admin/${eventId}/padeya-pick${qs ? `?${qs}` : ""}`,
    { method: "POST" },
  );
}

export async function clearEventPadeyaPick(
  eventId: string,
  opts?: { context_type?: string },
): Promise<EventItem> {
  const params = new URLSearchParams();
  if (opts?.context_type) params.set("context_type", opts.context_type);
  const qs = params.toString();
  return apiRequest<EventItem>(
    `/events/admin/${eventId}/unpadeya-pick${qs ? `?${qs}` : ""}`,
    { method: "POST" },
  );
}

export async function fetchAuditLogs(params?: {
  action?: string;
  resource_type?: string;
  resource_id?: string;
  limit?: number;
  offset?: number;
}): Promise<AuditLog[]> {
  const search = new URLSearchParams();
  if (params?.action) search.set("action", params.action);
  if (params?.resource_type) search.set("resource_type", params.resource_type);
  if (params?.resource_id) search.set("resource_id", params.resource_id);
  if (params?.limit != null) search.set("limit", String(params.limit));
  if (params?.offset != null) search.set("offset", String(params.offset));
  const q = search.toString();
  return apiRequest<AuditLog[]>(`/admin/audit-logs${q ? `?${q}` : ""}`);
}

export async function updateMyProfile(body: {
  full_name?: string;
  display_name?: string;
  username?: string;
}): Promise<UserPublic> {
  return apiRequest<UserPublic>("/users/me", { method: "PATCH", body });
}

export async function suspendUser(
  userId: string,
  reason: string,
): Promise<UserPublic> {
  return changeAdminUserAccountStatus(userId, {
    status: "suspended",
    reason,
  });
}

/** @deprecated Prefer {@link suspendUser} — backend alias for suspend. */
export async function deactivateUser(
  userId: string,
  reason: string,
): Promise<UserPublic> {
  return suspendUser(userId, reason);
}

export async function unsuspendUser(
  userId: string,
  reason: string,
): Promise<UserPublic> {
  return changeAdminUserAccountStatus(userId, {
    status: "active",
    reason,
  });
}

/** @deprecated Prefer {@link unsuspendUser} — backend alias for unsuspend. */
export async function restoreUser(
  userId: string,
  reason: string,
): Promise<UserPublic> {
  return unsuspendUser(userId, reason);
}

export async function addAdminUserNote(
  userId: string,
  payload: { note_type?: string; body: string },
): Promise<AdminUserNote> {
  return apiRequest<AdminUserNote>(`/admin/users/${userId}/notes`, {
    method: "POST",
    body: {
      note_type: (payload.note_type || "general").trim(),
      body: payload.body.trim(),
    },
  });
}

export async function addAdminUserFlag(
  userId: string,
  payload: {
    flag_type: string;
    severity?: string;
    reason: string;
    internal_note?: string;
  },
): Promise<AdminUserFlag> {
  return apiRequest<AdminUserFlag>(`/admin/users/${userId}/flags`, {
    method: "POST",
    body: {
      flag_type: payload.flag_type.trim(),
      severity: (payload.severity || "medium").trim(),
      reason: payload.reason.trim(),
      ...(payload.internal_note?.trim()
        ? { internal_note: payload.internal_note.trim() }
        : {}),
    },
  });
}

export async function resolveAdminUserFlag(
  userId: string,
  flagId: string,
  reason: string,
  note?: string,
): Promise<AdminUserFlag> {
  return apiRequest<AdminUserFlag>(
    `/admin/users/${userId}/flags/${flagId}`,
    {
      method: "PATCH",
      body: {
        status: "resolved",
        reason: reason.trim(),
        ...(note?.trim() ? { resolution_note: note.trim() } : {}),
      },
    },
  );
}

export async function dismissAdminUserFlag(
  userId: string,
  flagId: string,
  reason: string,
  note?: string,
): Promise<AdminUserFlag> {
  return apiRequest<AdminUserFlag>(
    `/admin/users/${userId}/flags/${flagId}`,
    {
      method: "PATCH",
      body: {
        status: "dismissed",
        reason: reason.trim(),
        ...(note?.trim() ? { resolution_note: note.trim() } : {}),
      },
    },
  );
}

export async function revokeAdminUserSessions(
  userId: string,
  reason: string,
): Promise<{ user_id: string; revoked_count: number }> {
  return apiRequest<{ user_id: string; revoked_count: number }>(
    `/admin/users/${userId}/force-logout`,
    {
      method: "POST",
      body: { reason: reason.trim() },
    },
  );
}

export async function forceAdminUserPasswordReset(
  userId: string,
  reason: string,
): Promise<{ user_id: string; email_sent: boolean }> {
  return apiRequest<{ user_id: string; email_sent: boolean }>(
    `/admin/users/${userId}/force-password-reset`,
    {
      method: "POST",
      body: { reason: reason.trim() },
    },
  );
}

export async function changeAdminUserAccountStatus(
  userId: string,
  payload: {
    status: string;
    reason: string;
    restrictions?: string[];
  },
): Promise<UserPublic> {
  return apiRequest<UserPublic>(`/admin/users/${userId}/status`, {
    method: "POST",
    body: {
      status: payload.status.trim(),
      reason: payload.reason.trim(),
      ...(payload.restrictions != null
        ? { restrictions: payload.restrictions }
        : {}),
    },
  });
}

/**
 * Sync active restriction keys for a user.
 * Backend persists history rows in `user_restrictions` (apply / revoke; never hard-delete).
 * Auth: `admin.users.restrict`
 *
 * @deprecated Prefer {@link applyAdminUserRestrictions} (POST) — PUT is not the contract.
 */
export async function updateAdminUserRestrictions(
  userId: string,
  payload: {
    restrictions: string[];
    reason: string;
    ends_at?: string | null;
    internal_note?: string | null;
  },
): Promise<AdminUserDetail> {
  return applyAdminUserRestrictions(userId, {
    restriction_keys: payload.restrictions,
    reason: payload.reason,
    ends_at: payload.ends_at,
    internal_note: payload.internal_note,
  }).then(() => fetchAdminUser(userId));
}

export type AdminUserRestrictionsList = {
  items: AdminUserRestriction[];
};

function normalizeRestrictionsList(
  data: AdminUserRestriction[] | AdminUserRestrictionsList,
): AdminUserRestriction[] {
  return Array.isArray(data) ? data : data.items ?? [];
}

/** GET /admin/users/{id}/restrictions */
export async function fetchAdminUserRestrictions(
  userId: string,
): Promise<AdminUserRestriction[]> {
  const data = await apiRequest<
    AdminUserRestriction[] | AdminUserRestrictionsList
  >(`/admin/users/${userId}/restrictions`);
  return normalizeRestrictionsList(data);
}

/** POST /admin/users/{id}/restrictions — apply new active rows. */
export async function applyAdminUserRestrictions(
  userId: string,
  payload: {
    restriction_keys: string[];
    reason: string;
    internal_note?: string | null;
    ends_at?: string | null;
  },
): Promise<AdminUserRestriction[]> {
  const data = await apiRequest<
    AdminUserRestriction[] | AdminUserRestrictionsList
  >(`/admin/users/${userId}/restrictions`, {
    method: "POST",
    body: {
      restriction_keys: payload.restriction_keys,
      reason: payload.reason.trim(),
      ...(payload.ends_at != null && payload.ends_at !== ""
        ? { ends_at: payload.ends_at }
        : {}),
      ...(payload.internal_note?.trim()
        ? { internal_note: payload.internal_note.trim() }
        : {}),
    },
  });
  return normalizeRestrictionsList(data);
}

/** PATCH /admin/users/{id}/restrictions/{restrictionId} — e.g. extend ends_at. */
export async function extendAdminUserRestriction(
  userId: string,
  restrictionId: string,
  payload: { ends_at: string; reason?: string },
): Promise<AdminUserRestriction> {
  return apiRequest<AdminUserRestriction>(
    `/admin/users/${userId}/restrictions/${restrictionId}`,
    {
      method: "PATCH",
      body: {
        ends_at: payload.ends_at,
        ...(payload.reason?.trim() ? { reason: payload.reason.trim() } : {}),
      },
    },
  );
}

/** POST /admin/users/{id}/restrictions/{restrictionId}/revoke */
export async function revokeAdminUserRestriction(
  userId: string,
  restrictionId: string,
  reason: string,
): Promise<AdminUserRestriction> {
  return apiRequest<AdminUserRestriction>(
    `/admin/users/${userId}/restrictions/${restrictionId}/revoke`,
    {
      method: "POST",
      body: { reason: reason.trim() },
    },
  );
}

export async function banUser(
  userId: string,
  reason: string,
): Promise<UserPublic> {
  return changeAdminUserAccountStatus(userId, {
    status: "banned",
    reason,
  });
}

export async function markAdminUserUnderReview(
  userId: string,
  reason: string,
): Promise<UserPublic> {
  return changeAdminUserAccountStatus(userId, {
    status: "under_review",
    reason,
  });
}

export async function clearAdminUserUnderReview(
  userId: string,
  reason: string,
): Promise<UserPublic> {
  return changeAdminUserAccountStatus(userId, {
    status: "active",
    reason,
  });
}
