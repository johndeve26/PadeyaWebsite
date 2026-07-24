import { apiRequest } from "@/lib/api";

export type SponsorTeamMember = {
  id: string | null;
  sponsor_id: string;
  user_id: string | null;
  email: string | null;
  display_name: string | null;
  role: string;
  status: string;
  is_owner: boolean;
  permissions: Record<string, boolean>;
};

export type SponsorTeamInvite = {
  id: string;
  sponsor_id: string;
  email: string;
  role: string;
  status: string;
  invite_expires_at: string | null;
  invited_at: string;
};

export type SponsorTeamList = {
  members: SponsorTeamMember[];
  invites: SponsorTeamInvite[];
};

export async function fetchSponsorTeam(
  sponsorId: string,
): Promise<SponsorTeamList> {
  return apiRequest<SponsorTeamList>(
    `/sponsors/workspaces/${encodeURIComponent(sponsorId)}/team`,
  );
}

export async function inviteSponsorTeamMember(
  sponsorId: string,
  body: { email: string; role: string },
): Promise<void> {
  await apiRequest(
    `/sponsors/workspaces/${encodeURIComponent(sponsorId)}/team/invites`,
    { method: "POST", body },
  );
}

export async function resendSponsorTeamInvite(
  sponsorId: string,
  inviteId: string,
): Promise<void> {
  await apiRequest(
    `/sponsors/workspaces/${encodeURIComponent(sponsorId)}/team/invites/${encodeURIComponent(inviteId)}/resend`,
    { method: "POST" },
  );
}

export async function cancelSponsorTeamInvite(
  sponsorId: string,
  inviteId: string,
): Promise<void> {
  await apiRequest(
    `/sponsors/workspaces/${encodeURIComponent(sponsorId)}/team/invites/${encodeURIComponent(inviteId)}`,
    { method: "DELETE" },
  );
}

export async function updateSponsorTeamMemberRole(
  sponsorId: string,
  memberId: string,
  role: string,
): Promise<SponsorTeamMember> {
  return apiRequest<SponsorTeamMember>(
    `/sponsors/workspaces/${encodeURIComponent(sponsorId)}/team/members/${encodeURIComponent(memberId)}`,
    { method: "PATCH", body: { role } },
  );
}

export async function removeSponsorTeamMember(
  sponsorId: string,
  memberId: string,
): Promise<void> {
  await apiRequest(
    `/sponsors/workspaces/${encodeURIComponent(sponsorId)}/team/members/${encodeURIComponent(memberId)}`,
    { method: "DELETE" },
  );
}

export async function acceptSponsorTeamInvite(token: string): Promise<void> {
  await apiRequest(`/sponsors/team/invites/${encodeURIComponent(token)}/accept`, {
    method: "POST",
  });
}

export async function previewSponsorTeamInvite(token: string): Promise<{
  sponsor_display_name: string;
  role: string;
  status: string;
}> {
  return apiRequest(`/sponsors/team/invites/${encodeURIComponent(token)}`, {
    auth: false,
  });
}
