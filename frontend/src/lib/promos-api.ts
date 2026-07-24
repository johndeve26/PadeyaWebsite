import { apiRequest } from "@/lib/api";
import type {
  AdminAmbassadorRow,
  Ambassador,
  AmbassadorCampaign,
  AmbassadorConversionAdmin,
  AmbassadorDashboard,
  AmbassadorEarningsSummary,
  AmbassadorEnrollmentList,
  AmbassadorPlatformSettings,
  HostAmbassadorDashboard,
  AmbassadorReportsSummary,
  CampaignLeaderboardRow,
  EligibleAmbassadorEvent,
  OpenAmbassadorProgram,
  PromoCode,
  PromoValidateResult,
} from "@/lib/types/promos";

export async function fetchHostPromos(): Promise<PromoCode[]> {
  return apiRequest<PromoCode[]>("/promos/codes");
}

export async function createPromo(input: Record<string, unknown>): Promise<PromoCode> {
  return apiRequest<PromoCode>("/promos/codes", { method: "POST", body: input });
}

export async function updatePromo(
  id: string,
  input: Record<string, unknown>,
): Promise<PromoCode> {
  return apiRequest<PromoCode>(`/promos/codes/${id}`, { method: "PATCH", body: input });
}

export async function validatePromo(input: {
  code: string;
  event_id: string;
  items: { ticket_type_id: string; quantity: number }[];
}): Promise<PromoValidateResult> {
  return apiRequest<PromoValidateResult>("/promos/validate", {
    method: "POST",
    body: input,
  });
}

export async function trackReferralClick(input: {
  referral_code: string;
  event_id?: string;
  landing_path?: string;
  source?: string;
  anonymous_visitor_id?: string;
}): Promise<{ status: string }> {
  return apiRequest<{ status: string }>("/promos/referrals/click", {
    method: "POST",
    body: input,
    auth: false,
  });
}

export async function fetchHostAmbassadors(): Promise<Ambassador[]> {
  return apiRequest<Ambassador[]>("/promos/ambassadors");
}

export async function createAmbassador(
  input: Record<string, unknown>,
): Promise<Ambassador> {
  return apiRequest<Ambassador>("/promos/ambassadors", { method: "POST", body: input });
}

export async function fetchHostAmbassador(
  id: string,
): Promise<HostAmbassadorDashboard> {
  return apiRequest<HostAmbassadorDashboard>(`/promos/ambassadors/${id}`);
}

export async function updateAmbassador(
  id: string,
  input: Record<string, unknown>,
): Promise<Ambassador> {
  return apiRequest<Ambassador>(`/promos/ambassadors/${id}`, {
    method: "PATCH",
    body: input,
  });
}

export async function fetchMyAmbassadorDashboard(): Promise<AmbassadorDashboard> {
  return apiRequest<AmbassadorDashboard>("/promos/ambassador/me");
}

export async function fetchMyAmbassadorEnrollments(): Promise<AmbassadorEnrollmentList> {
  return apiRequest<AmbassadorEnrollmentList>("/promos/ambassador/enrollments");
}

export async function fetchOpenAmbassadorProgram(
  eventId: string,
): Promise<OpenAmbassadorProgram> {
  return apiRequest<OpenAmbassadorProgram>(
    `/promos/events/${eventId}/ambassadors/program`,
    { auth: false },
  );
}

export async function joinOpenEventAmbassador(
  eventId: string,
  input: {
    accept_terms: boolean;
    campaign_type?: string;
    campaign_id?: string;
  } = { accept_terms: true },
): Promise<Ambassador> {
  return apiRequest<Ambassador>(`/promos/events/${eventId}/ambassadors/join`, {
    method: "POST",
    body: input,
  });
}

export async function fetchMyEventAmbassador(
  eventId: string,
  campaignType?: string,
): Promise<Ambassador> {
  const qs = campaignType
    ? `?campaign_type=${encodeURIComponent(campaignType)}`
    : "";
  return apiRequest<Ambassador>(
    `/promos/events/${eventId}/ambassadors/me${qs}`,
  );
}

export async function leaveOpenEventAmbassador(
  eventId: string,
): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(
    `/promos/events/${eventId}/ambassadors/leave`,
    { method: "POST" },
  );
}

export async function fetchEligibleAmbassadorEvents(): Promise<
  EligibleAmbassadorEvent[]
> {
  return apiRequest<EligibleAmbassadorEvent[]>(
    "/promos/ambassadors/eligible-events",
    { auth: false },
  );
}

export async function fetchAmbassadorEarningsSummary(): Promise<AmbassadorEarningsSummary> {
  return apiRequest<AmbassadorEarningsSummary>(
    "/promos/ambassador/earnings-summary",
  );
}

export async function fetchHostCampaigns(): Promise<AmbassadorCampaign[]> {
  return apiRequest<AmbassadorCampaign[]>("/promos/campaigns");
}

export async function createHostCampaign(
  input: Record<string, unknown>,
): Promise<AmbassadorCampaign> {
  return apiRequest<AmbassadorCampaign>("/promos/campaigns", {
    method: "POST",
    body: input,
  });
}

export async function fetchHostCampaign(
  id: string,
): Promise<AmbassadorCampaign> {
  return apiRequest<AmbassadorCampaign>(`/promos/campaigns/${id}`);
}

export async function updateHostCampaign(
  id: string,
  input: Record<string, unknown>,
): Promise<AmbassadorCampaign> {
  return apiRequest<AmbassadorCampaign>(`/promos/campaigns/${id}`, {
    method: "PATCH",
    body: input,
  });
}

export async function pauseHostCampaign(
  id: string,
): Promise<AmbassadorCampaign> {
  return apiRequest<AmbassadorCampaign>(`/promos/campaigns/${id}/pause`, {
    method: "POST",
  });
}

export async function resumeHostCampaign(
  id: string,
): Promise<AmbassadorCampaign> {
  return apiRequest<AmbassadorCampaign>(`/promos/campaigns/${id}/resume`, {
    method: "POST",
  });
}

export async function endHostCampaign(id: string): Promise<AmbassadorCampaign> {
  return apiRequest<AmbassadorCampaign>(`/promos/campaigns/${id}/end`, {
    method: "POST",
  });
}

export async function fetchCampaignLeaderboard(
  id: string,
): Promise<CampaignLeaderboardRow[]> {
  return apiRequest<CampaignLeaderboardRow[]>(
    `/promos/campaigns/${id}/leaderboard`,
  );
}

export async function removeCampaignAmbassador(
  campaignId: string,
  ambassadorId: string,
): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(
    `/promos/campaigns/${campaignId}/ambassadors/${ambassadorId}/remove`,
    { method: "POST" },
  );
}

export async function fetchEventCampaign(
  eventId: string,
): Promise<AmbassadorCampaign> {
  return apiRequest<AmbassadorCampaign>(`/promos/events/${eventId}/campaign`);
}

export async function fetchEventCampaigns(
  eventId: string,
): Promise<AmbassadorCampaign[]> {
  return apiRequest<AmbassadorCampaign[]>(
    `/promos/events/${eventId}/campaigns`,
  );
}

export async function fetchAdminAmbassadorSettings(): Promise<AmbassadorPlatformSettings> {
  return apiRequest<AmbassadorPlatformSettings>("/promos/admin/settings");
}

export async function updateAdminAmbassadorSettings(input: {
  enabled: boolean;
}): Promise<AmbassadorPlatformSettings> {
  return apiRequest<AmbassadorPlatformSettings>("/promos/admin/settings", {
    method: "PATCH",
    body: input,
  });
}

export async function fetchAdminCampaigns(params?: {
  status?: string;
  source?: string;
}): Promise<AmbassadorCampaign[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.source) qs.set("source", params.source);
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<AmbassadorCampaign[]>(`/promos/admin/campaigns${suffix}`);
}

export async function createAdminCampaign(
  input: Record<string, unknown>,
): Promise<AmbassadorCampaign> {
  return apiRequest<AmbassadorCampaign>("/promos/admin/campaigns", {
    method: "POST",
    body: input,
  });
}

export async function pauseAdminCampaign(
  id: string,
  reason?: string,
): Promise<AmbassadorCampaign> {
  return apiRequest<AmbassadorCampaign>(`/promos/admin/campaigns/${id}/pause`, {
    method: "POST",
    body: { reason: reason || null },
  });
}

export async function resumeAdminCampaign(
  id: string,
): Promise<AmbassadorCampaign> {
  return apiRequest<AmbassadorCampaign>(`/promos/admin/campaigns/${id}/resume`, {
    method: "POST",
  });
}

export async function fetchAdminAmbassadors(params?: {
  q?: string;
  status?: string;
  blocked_only?: boolean;
}): Promise<AdminAmbassadorRow[]> {
  const qs = new URLSearchParams();
  if (params?.q) qs.set("q", params.q);
  if (params?.status) qs.set("status", params.status);
  if (params?.blocked_only) qs.set("blocked_only", "true");
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<AdminAmbassadorRow[]>(`/promos/admin/ambassadors${suffix}`);
}

export async function blockAdminAmbassador(
  ambassadorId: string,
): Promise<{ ambassador_id: string; user_id: string; ambassadors_blocked: boolean }> {
  return apiRequest(`/promos/admin/ambassadors/${ambassadorId}/block`, {
    method: "POST",
  });
}

export async function unblockAdminAmbassador(
  ambassadorId: string,
): Promise<{ ambassador_id: string; user_id: string; ambassadors_blocked: boolean }> {
  return apiRequest(`/promos/admin/ambassadors/${ambassadorId}/unblock`, {
    method: "POST",
  });
}

export async function fetchAdminConversions(params?: {
  status?: string;
}): Promise<AmbassadorConversionAdmin[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<AmbassadorConversionAdmin[]>(
    `/promos/admin/conversions${suffix}`,
  );
}

export async function reverseAdminConversion(
  saleId: string,
  reason: string,
): Promise<AmbassadorConversionAdmin> {
  return apiRequest<AmbassadorConversionAdmin>(
    `/promos/admin/conversions/${saleId}/reverse`,
    { method: "POST", body: { reason } },
  );
}

export async function setAdminConversionRewardStatus(
  saleId: string,
  status: "attributed" | "approved" | "paid" | "rejected",
): Promise<AmbassadorConversionAdmin> {
  return apiRequest<AmbassadorConversionAdmin>(
    `/promos/admin/conversions/${saleId}/reward-status`,
    { method: "POST", body: { status } },
  );
}

export async function fetchAdminAmbassadorReports(): Promise<AmbassadorReportsSummary> {
  return apiRequest<AmbassadorReportsSummary>("/promos/admin/reports/summary");
}
