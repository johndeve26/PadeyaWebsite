import { apiRequest } from "@/lib/api";
import { readActiveHostId } from "@/lib/host-workspace";
import type { Host } from "@/lib/types/events";
import type {
  HostBankAccount,
  HostTeamAuditItem,
  HostTeamInvitePreview,
  HostTeamMember,
  HostTeamPermissions,
  HostVerification,
} from "@/lib/types/lifecycle";

/** Resolve workspace query for `/host/team*` routes. */
function hostTeamQs(hostId?: string | null): string {
  const id = hostId ?? readActiveHostId();
  return id ? `?host_id=${encodeURIComponent(id)}` : "";
}

function withQs(path: string, hostId?: string | null): string {
  const qs = hostTeamQs(hostId);
  if (!qs) return path;
  return path.includes("?") ? `${path}&${qs.slice(1)}` : `${path}${qs}`;
}

/** Legacy `/hosts/.../team` base — detail, resend, restore, permissions. */
function legacyTeamBase(hostId?: string | null): string {
  const id = hostId ?? readActiveHostId();
  return id ? `/hosts/${id}/team` : "/hosts/me/team";
}

function teamListQs(includeArchived: boolean, hostId?: string | null): string {
  const arch = includeArchived ? "include_archived=true" : "";
  const id = hostId ?? readActiveHostId();
  const parts = [arch, id ? `host_id=${encodeURIComponent(id)}` : ""].filter(
    Boolean,
  );
  return parts.length ? `?${parts.join("&")}` : "";
}

export async function fetchHostTeamMembers(
  includeArchived = false,
  hostId?: string | null,
): Promise<HostTeamMember[]> {
  return apiRequest<HostTeamMember[]>(
    `/host/team${teamListQs(includeArchived, hostId)}`,
  );
}

export async function fetchHostTeamInvites(
  includeArchived = false,
  hostId?: string | null,
): Promise<HostTeamMember[]> {
  return apiRequest<HostTeamMember[]>(
    `/host/team/invites${teamListQs(includeArchived, hostId)}`,
  );
}

export async function fetchHostTeam(
  includeArchived = false,
  hostId?: string | null,
): Promise<HostTeamMember[]> {
  const [members, invites] = await Promise.all([
    fetchHostTeamMembers(includeArchived, hostId),
    fetchHostTeamInvites(includeArchived, hostId),
  ]);
  return [...invites, ...members].sort((a, b) =>
    (b.created_at || "").localeCompare(a.created_at || ""),
  );
}

export async function fetchHostTeamMember(
  id: string,
  hostId?: string | null,
): Promise<HostTeamMember> {
  return apiRequest<HostTeamMember>(`${legacyTeamBase(hostId)}/${id}`);
}

export async function fetchHostTeamAudit(
  limit = 50,
  hostId?: string | null,
): Promise<HostTeamAuditItem[]> {
  return apiRequest<HostTeamAuditItem[]>(
    withQs(`/host/team/audit-log?limit=${limit}`, hostId),
  );
}

export type HostTeamInviteCreateResponse = {
  invite_id: string;
  invite_method: "email" | "username" | string;
  status: string;
  masked_email?: string | null;
  display_name?: string | null;
  username?: string | null;
  avatar_url?: string | null;
};

export type HostTeamInviteLookup = {
  invite_method: "email" | "username" | null;
  valid: boolean;
  found: boolean;
  display_name: string | null;
  username: string | null;
  avatar_url: string | null;
  masked_email: string | null;
  message: string | null;
};

export async function lookupHostTeamInvitee(
  identifier: string,
  hostId?: string | null,
): Promise<HostTeamInviteLookup> {
  const base = withQs("/host/team/invites/lookup", hostId);
  const sep = base.includes("?") ? "&" : "?";
  return apiRequest<HostTeamInviteLookup>(
    `${base}${sep}identifier=${encodeURIComponent(identifier)}`,
  );
}

export async function inviteHostTeamMember(
  body: {
    /** Email address or Pàdéyá username (with or without @). */
    invite_identifier: string;
    role?: string;
    role_label?: string;
    permissions_json?: Partial<HostTeamPermissions>;
    scope_json?: {
      type: "host_wide" | "selected_events";
      event_ids?: string[];
    };
    selected_event_ids?: string[];
    /** @deprecated Prefer invite_identifier */
    email?: string;
    /** @deprecated Prefer permissions_json */
    permissions?: Partial<HostTeamPermissions>;
    /** @deprecated Prefer scope_json */
    scope?: "host_wide" | "selected_events";
    /** @deprecated Prefer selected_event_ids */
    scoped_event_ids?: string[];
  },
  hostId?: string | null,
): Promise<HostTeamInviteCreateResponse> {
  return apiRequest<HostTeamInviteCreateResponse>(
    withQs("/host/team/invites", hostId),
    {
      method: "POST",
      body,
    },
  );
}

/** @deprecated Prefer inviteHostTeamMember */
export async function createHostTeamMember(body: {
  user_id?: string;
  invited_email?: string;
  role_label?: string;
  role?: string;
}): Promise<HostTeamMember> {
  return apiRequest<HostTeamMember>("/hosts/me/team", { method: "POST", body });
}

export async function updateHostTeamMember(
  id: string,
  body: {
    role?: string;
    role_label?: string;
    status?: string;
    permissions?: Partial<HostTeamPermissions>;
  },
  hostId?: string | null,
): Promise<HostTeamMember> {
  return apiRequest<HostTeamMember>(
    withQs(`/host/team/members/${id}`, hostId),
    { method: "PATCH", body },
  );
}

export async function updateHostTeamPermissions(
  id: string,
  body: {
    role?: string;
    role_label?: string;
    permissions: HostTeamPermissions;
    scope?: "host_wide" | "selected_events";
    scoped_event_ids?: string[];
  },
  hostId?: string | null,
): Promise<HostTeamMember> {
  return apiRequest<HostTeamMember>(`${legacyTeamBase(hostId)}/${id}/permissions`, {
    method: "PATCH",
    body,
  });
}

export async function resendHostTeamInvite(
  id: string,
  hostId?: string | null,
): Promise<HostTeamMember> {
  return apiRequest<HostTeamMember>(`${legacyTeamBase(hostId)}/${id}/resend`, {
    method: "POST",
  });
}

export async function suspendHostTeamMember(
  id: string,
  hostId?: string | null,
): Promise<HostTeamMember> {
  return apiRequest<HostTeamMember>(
    withQs(`/host/team/members/${id}/suspend`, hostId),
    { method: "POST" },
  );
}

export async function archiveHostTeamMember(
  id: string,
  hostId?: string | null,
): Promise<HostTeamMember> {
  return apiRequest<HostTeamMember>(
    withQs(`/host/team/members/${id}/remove`, hostId),
    { method: "POST" },
  );
}

export async function revokeHostTeamInvite(
  id: string,
  hostId?: string | null,
): Promise<HostTeamMember> {
  return apiRequest<HostTeamMember>(
    withQs(`/host/team/invites/${id}/revoke`, hostId),
    { method: "POST" },
  );
}

export async function restoreHostTeamMember(
  id: string,
  hostId?: string | null,
): Promise<HostTeamMember> {
  return apiRequest<HostTeamMember>(`${legacyTeamBase(hostId)}/${id}/restore`, {
    method: "POST",
  });
}

export async function previewHostTeamInvite(
  token: string,
): Promise<HostTeamInvitePreview> {
  return apiRequest<HostTeamInvitePreview>(`/team/invites/${token}`, {
    auth: false,
  });
}

export async function acceptHostTeamInvite(
  token: string,
): Promise<HostTeamMember> {
  return apiRequest<HostTeamMember>(`/team/invites/${token}/accept`, {
    method: "POST",
  });
}

export async function declineHostTeamInvite(
  token: string,
): Promise<HostTeamMember> {
  return apiRequest<HostTeamMember>(`/hosts/team-invites/${token}/decline`, {
    method: "POST",
  });
}

export async function fetchHostBankAccounts(
  includeArchived = false,
): Promise<HostBankAccount[]> {
  const q = includeArchived ? "?include_archived=true" : "";
  return apiRequest<HostBankAccount[]>(`/hosts/me/bank-accounts${q}`);
}

export async function fetchHostBankAccount(
  id: string,
): Promise<HostBankAccount> {
  return apiRequest<HostBankAccount>(`/hosts/me/bank-accounts/${id}`);
}

export async function createHostBankAccount(body: {
  label: string;
  bank_name: string;
  account_name: string;
  account_number: string;
  currency?: string;
  is_default?: boolean;
}): Promise<HostBankAccount> {
  return apiRequest<HostBankAccount>("/hosts/me/bank-accounts", {
    method: "POST",
    body,
  });
}

export async function updateHostBankAccount(
  id: string,
  body: {
    label?: string;
    bank_name?: string;
    account_name?: string;
    account_number?: string;
    currency?: string;
    is_default?: boolean;
  },
): Promise<HostBankAccount> {
  return apiRequest<HostBankAccount>(`/hosts/me/bank-accounts/${id}`, {
    method: "PATCH",
    body,
  });
}

export async function archiveHostBankAccount(
  id: string,
): Promise<HostBankAccount> {
  return apiRequest<HostBankAccount>(`/hosts/me/bank-accounts/${id}/archive`, {
    method: "POST",
  });
}

export async function restoreHostBankAccount(
  id: string,
): Promise<HostBankAccount> {
  return apiRequest<HostBankAccount>(`/hosts/me/bank-accounts/${id}/restore`, {
    method: "POST",
  });
}

export async function fetchAdminVerifications(
  status?: string,
): Promise<HostVerification[]> {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<HostVerification[]>(`/hosts/admin/verifications${q}`);
}

export async function approveHostVerification(
  id: string,
): Promise<HostVerification> {
  return apiRequest<HostVerification>(
    `/hosts/admin/verifications/${id}/approve`,
    { method: "POST" },
  );
}

export async function rejectHostVerification(
  id: string,
  notes: string,
): Promise<HostVerification> {
  return apiRequest<HostVerification>(
    `/hosts/admin/verifications/${id}/reject`,
    { method: "POST", body: { notes } },
  );
}

/** Soft-suspend a host workspace (owner user account untouched). */
export async function suspendHostWorkspace(
  hostId: string,
  reason: string,
): Promise<Host> {
  return apiRequest<Host>(`/hosts/admin/${hostId}/suspend`, {
    method: "POST",
    body: { reason: reason.trim() },
  });
}

export async function restoreHostWorkspace(
  hostId: string,
  reason = "Restored by admin",
): Promise<Host> {
  return apiRequest<Host>(`/hosts/admin/${hostId}/restore`, {
    method: "POST",
    body: { reason: reason.trim() },
  });
}

/** Soft EOL — host must already be suspended. */
export async function forceDeleteHostWorkspace(
  hostId: string,
  reason: string,
): Promise<Host> {
  return apiRequest<Host>(`/hosts/admin/${hostId}/force-delete`, {
    method: "POST",
    body: { reason: reason.trim() },
  });
}
