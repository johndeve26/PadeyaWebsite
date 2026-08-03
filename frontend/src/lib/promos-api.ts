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
  return apiRequest<AmbassadorPlatformSettings>("/promos/admin/settings", {
    timeout: "long",
  });
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
  return apiRequest<AdminAmbassadorRow[]>(`/promos/admin/ambassadors${suffix}`, {
    timeout: "long",
  });
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

export type ReferralProgram = {
  id: string;
  name: string;
  description?: string | null;
  public_description?: string | null;
  scope: string;
  owner_type: string;
  status: string;
  enrollment_mode: string;
  default_landing_path: string;
  attribution_window_days: number;
  hold_period_days: number;
  commission_funded_by?: string;
  rules: Array<{
    id: string;
    product_type: string;
    commission_mode: string;
    commission_value: string | number;
    is_active: boolean;
  }>;
  enrollment_count?: number;
};

export async function fetchAdminReferralPrograms(params?: {
  scope?: string;
  status?: string;
}): Promise<ReferralProgram[]> {
  const qs = new URLSearchParams();
  if (params?.scope) qs.set("scope", params.scope);
  if (params?.status) qs.set("status", params.status);
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<ReferralProgram[]>(`/promos/admin/referral-programs${suffix}`);
}

export async function createAdminReferralProgram(
  input: Record<string, unknown>,
): Promise<ReferralProgram> {
  return apiRequest<ReferralProgram>("/promos/admin/referral-programs", {
    method: "POST",
    body: input,
  });
}

export async function enrollAdminReferralProgram(
  programId: string,
  input: { email?: string; user_id?: string; referral_code?: string },
): Promise<{ id: string; referral_code: string; referral_link_path: string }> {
  return apiRequest(`/promos/admin/referral-programs/${programId}/enrollments`, {
    method: "POST",
    body: input,
  });
}

export async function pauseAdminReferralProgram(
  programId: string,
): Promise<ReferralProgram> {
  return apiRequest(`/promos/admin/referral-programs/${programId}/pause`, {
    method: "POST",
  });
}

export async function activateAdminReferralProgram(
  programId: string,
): Promise<ReferralProgram> {
  return apiRequest(`/promos/admin/referral-programs/${programId}/activate`, {
    method: "POST",
  });
}

/* --- Unified referral reporting (ledger-backed) --- */

export type ReferralSummary = {
  clicks: number;
  conversion_rate: number;
  enrollments_active: number;
  converted_orders: number;
  attributed_items: number;
  referred_gross_sales: string;
  eligible_sales: string;
  pending_commission: string;
  available_commission: string;
  paid_commission: string;
  reversed_commission: string;
  net_commission: string;
  has_platform_enrollment?: boolean;
  has_host_enrollment?: boolean;
  primary_referral_link_path?: string | null;
  scopes?: string[];
};

export type ReferralProgramRow = {
  enrollment_id: string;
  name: string;
  scope_badge: string;
  scope: string;
  event_title?: string | null;
  product_coverage: string[];
  status: string;
  referral_code: string;
  referral_link_path?: string | null;
  clicks: number;
  converted_orders: number;
  referred_gross_sales: string;
  pending_commission: string;
  available_commission: string;
  paid_commission: string;
};

export type ReferralEarningRow = {
  id: string;
  date: string;
  entry_type: string;
  source: string;
  payer_type: string;
  program_name?: string | null;
  event_title?: string | null;
  product_type: string;
  eligible_sale: string;
  commission: string;
  status: string;
};

export async function fetchMyReferralSummary(params?: {
  scope?: string;
  product_type?: string;
}): Promise<ReferralSummary> {
  const qs = new URLSearchParams();
  if (params?.scope) qs.set("scope", params.scope);
  if (params?.product_type) qs.set("product_type", params.product_type);
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<ReferralSummary>(`/referrals/me/summary${suffix}`);
}

export async function fetchMyReferralPrograms(params?: {
  scope?: string;
}): Promise<ReferralProgramRow[]> {
  const qs = new URLSearchParams();
  if (params?.scope) qs.set("scope", params.scope);
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<ReferralProgramRow[]>(`/referrals/me/programs${suffix}`);
}

export async function fetchMyReferralEarnings(params?: {
  scope?: string;
  product_type?: string;
}): Promise<ReferralEarningRow[]> {
  const qs = new URLSearchParams();
  if (params?.scope) qs.set("scope", params.scope);
  if (params?.product_type) qs.set("product_type", params.product_type);
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<ReferralEarningRow[]>(`/referrals/me/earnings${suffix}`);
}

export async function fetchHostPlatformAttributedSales(): Promise<
  Array<{
    order_reference?: string | null;
    event_title?: string | null;
    product_type: string;
    gross_attributed_sale: string;
    attribution_badge: string;
    commission_funded_by: string;
    host_proceeds_note: string;
  }>
> {
  return apiRequest("/host/referrals/platform-attributed-sales");
}

export async function fetchAdminReferralSummary(): Promise<AdminReferralOverviewSummary> {
  return apiRequest("/admin/referrals/summary", { timeout: "long" });
}

export type AdminReferralOverviewSummary = {
  total_referred_gross_sales?: string | number;
  host_funded_commission?: string | number;
  platform_funded_commission?: string | number;
  pending_platform_liability?: string | number;
  approved_platform_liability?: string | number;
  paid_platform_commission?: string | number;
  platform_reversals?: string | number;
  host_reversals?: string | number;
  active_platform_programs?: number;
  active_platform_ambassadors?: number;
  converted_orders?: number;
  attributed_items?: number;
  active_host_campaigns?: number;
  active_platform_campaigns?: number;
  active_arrangements?: number;
  unique_active_ambassadors?: number;
  platform_enrollments_active?: number;
  host_enrollments_active?: number;
  commission_owed_total?: string | number;
  host_funded_owed?: string | number;
  platform_funded_owed?: string | number;
  pending_commission?: string | number;
  available_commission?: string | number;
  paid_commission?: string | number;
};

export async function fetchAdminReferralLiabilities(params?: {
  payer?: string;
}): Promise<Array<Record<string, unknown>>> {
  const qs = new URLSearchParams();
  if (params?.payer) qs.set("payer", params.payer);
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest(`/admin/referrals/liabilities${suffix}`);
}
