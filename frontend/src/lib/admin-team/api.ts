import { apiRequest } from "@/lib/api";

export type AdminTeamRole = {
  id: string;
  name: string;
  description: string | null;
  system_key: string | null;
  is_system: boolean;
  is_high_level: boolean;
  linked_role_id: string | null;
  permission_codes: string[];
  archived_at: string | null;
  created_at: string | null;
};

export type AdminTeamUser = {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
};

export type AdminTeamMember = {
  id: string;
  user_id: string;
  status: string;
  user: AdminTeamUser | null;
  role: AdminTeamRole | null;
  invited_by_user_id: string | null;
  disabled_at: string | null;
  removed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  permissions: string[];
};

export type AdminTeamInviteResult = {
  invite_id: string | null;
  status: string;
  email_hint: string;
  member: AdminTeamMember | null;
  expires_at: string | null;
};

export type AdminTeamInvitePreview = {
  email_hint: string;
  role_name: string | null;
  role_label: string | null;
  system_key: string | null;
  expires_at: string | null;
  status: string;
  already_accepted: boolean;
};

export type AdminPendingInvite = {
  id: string;
  email_hint: string;
  status: string;
  role: AdminTeamRole | null;
  expires_at: string | null;
  created_at: string | null;
};

export type AdminPermissionGroup = {
  group: string;
  permissions: {
    code: string;
    description: string;
    high_level: boolean;
  }[];
};

export type AdminTeamAuditItem = {
  id: string;
  action: string;
  actor_user_id: string | null;
  target_user_id: string | null;
  target_member_id: string | null;
  entity_type: string | null;
  entity_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string | null;
};

export function fetchAdminTeam(status?: string) {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<{
    members: AdminTeamMember[];
    pending_invites: AdminPendingInvite[];
  }>(`/admin/team${q}`);
}

export function inviteAdminTeamMember(body: {
  email: string;
  admin_role_id?: string;
  system_key?: string;
}) {
  return apiRequest<AdminTeamInviteResult>("/admin/team/invite", {
    method: "POST",
    body,
  });
}

export function previewAdminTeamInvite(token: string) {
  return apiRequest<AdminTeamInvitePreview>(
    `/admin/team/invites/${encodeURIComponent(token)}`,
  );
}

export function acceptAdminTeamInvite(token: string) {
  return apiRequest<AdminTeamMember>(
    `/admin/team/invites/${encodeURIComponent(token)}/accept`,
    { method: "POST" },
  );
}

export function fetchAdminTeamRoles() {
  return apiRequest<{
    roles: AdminTeamRole[];
    permission_catalog: AdminPermissionGroup[];
  }>("/admin/team/roles");
}

export function createAdminTeamRole(body: {
  name: string;
  description?: string;
  permission_codes: string[];
}) {
  return apiRequest<AdminTeamRole>("/admin/team/roles", {
    method: "POST",
    body,
  });
}

export function updateAdminTeamRole(
  roleId: string,
  body: {
    name?: string;
    description?: string;
    permission_codes?: string[];
  },
) {
  return apiRequest<AdminTeamRole>(`/admin/team/roles/${roleId}`, {
    method: "PATCH",
    body,
  });
}

export function archiveAdminTeamRole(roleId: string) {
  return apiRequest<AdminTeamRole>(`/admin/team/roles/${roleId}/archive`, {
    method: "POST",
    body: {},
  });
}

export function fetchAdminTeamMember(memberId: string) {
  return apiRequest<{
    member: AdminTeamMember;
    audit: AdminTeamAuditItem[];
  }>(`/admin/team/members/${memberId}`);
}

export function updateAdminTeamMember(
  memberId: string,
  body: {
    admin_role_id?: string;
    system_key?: string;
    permission_codes?: string[];
  },
) {
  return apiRequest<AdminTeamMember>(`/admin/team/members/${memberId}`, {
    method: "PATCH",
    body,
  });
}

export function disableAdminTeamMember(
  memberId: string,
  body: { reason?: string; remove?: boolean } = {},
) {
  return apiRequest<AdminTeamMember>(
    `/admin/team/members/${memberId}/disable`,
    { method: "POST", body },
  );
}

export function forceLogoutAdminTeamMember(
  memberId: string,
  body: { reason?: string } = {},
) {
  return apiRequest<{ user_id: string; revoked_count: number }>(
    `/admin/team/members/${memberId}/force-logout`,
    { method: "POST", body },
  );
}
