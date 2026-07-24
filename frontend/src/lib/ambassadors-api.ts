/** Domain Ambassadors APIs (`/api/v1/ambassadors/*`, host/admin). */

import { apiRequest } from "@/lib/api";

export type DomainEligibleEvent = {
  id: string;
  title: string;
  slug: string;
  city: string | null;
  start_datetime: string;
  banner_url: string | null;
  host_display_name: string | null;
  campaign_id: string;
  campaign_type: string;
  commission_type: string;
  commission_value: string | number;
  visibility: string;
};

export type DomainCampaign = {
  id: string;
  name: string;
  description: string | null;
  campaign_type: string;
  status: string;
  visibility: string;
  commission_type: string;
  commission_value: string | number;
  applies_to: string;
  hold_period_days: number;
  cookie_window_days: number;
  event_id: string | null;
  event_title: string | null;
  event_slug: string | null;
  is_joinable: boolean;
  created_at: string;
  updated_at: string;
};

export type DomainParticipant = {
  id: string;
  campaign_id: string;
  ambassador_profile_id: string;
  user_id: string;
  ambassador_code: string;
  status: string;
  joined_at: string;
  campaign_name: string | null;
  event_title: string | null;
  event_slug: string | null;
};

export type DomainLink = {
  participant_id: string;
  campaign_id: string;
  ambassador_code: string;
  event_id: string | null;
  event_slug: string | null;
  event_path: string | null;
  merch_path: string | null;
  share_url_path: string | null;
};

export type DomainEarnings = {
  confirmed_conversions: number;
  pending_amount: string | number;
  approved_amount: string | number;
  payable_amount: string | number;
  paid_amount: string | number;
  reversed_amount: string | number;
  gross_eligible: string | number;
};

export type DomainEventStatus = {
  event_id: string;
  event_slug: string;
  enabled: boolean;
  campaign_id: string | null;
  campaign_type: string | null;
  commission_type: string | null;
  commission_value: string | number | null;
  joined: boolean;
  participant_id: string | null;
  ambassador_code: string | null;
  terms_version: string;
};

export type HostParticipantRow = {
  id: string;
  campaign_id: string;
  user_id: string;
  ambassador_code: string;
  status: string;
  joined_at: string;
  display_name: string | null;
  clicks: number;
  total_clicks?: number;
  unique_clicks?: number;
  conversions: number;
  commission_amount: string | number;
};

export type HostAnalytics = {
  campaigns: number;
  active_participants: number;
  clicks: number;
  total_clicks?: number;
  unique_clicks?: number;
  conversions: number;
  commission_owed: string | number;
  commission_paid: string | number;
};

export type DomainConversion = {
  id: string;
  campaign_id: string;
  participant_id: string;
  conversion_type: string;
  gross_amount: string | number;
  eligible_amount: string | number;
  commission_amount: string | number;
  status: string;
  dedupe_key: string;
  verified_at: string | null;
  refunded_at: string | null;
  created_at: string;
  ambassador_code: string | null;
  campaign_name: string | null;
};

export type DomainPayout = {
  id: string;
  ambassador_profile_id: string;
  user_id: string;
  amount: string | number;
  status: string;
  payout_method: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  display_name: string | null;
};

export async function fetchDomainEligibleEvents(): Promise<DomainEligibleEvent[]> {
  return apiRequest<DomainEligibleEvent[]>("/ambassadors/eligible-events", {
    auth: false,
  });
}

export async function fetchDomainEarnings(): Promise<DomainEarnings> {
  return apiRequest<DomainEarnings>("/ambassadors/me/earnings");
}

export async function fetchMyDomainCampaigns(): Promise<DomainParticipant[]> {
  return apiRequest<DomainParticipant[]>("/ambassadors/me/campaigns");
}

export async function fetchMyDomainLinks(): Promise<DomainLink[]> {
  return apiRequest<DomainLink[]>("/ambassadors/me/links");
}

export async function fetchEventAmbassadorStatus(
  slug: string,
): Promise<DomainEventStatus> {
  return apiRequest<DomainEventStatus>(`/events/${slug}/ambassador-status`, {
    auth: false,
  });
}

export async function joinEventAmbassadorBySlug(
  slug: string,
  input: { accept_terms: boolean; campaign_id?: string },
): Promise<DomainParticipant> {
  return apiRequest<DomainParticipant>(`/events/${slug}/ambassador/join`, {
    method: "POST",
    body: input,
  });
}

export async function fetchHostDomainCampaigns(
  hostId?: string | null,
): Promise<DomainCampaign[]> {
  const qs = hostId ? `?host_id=${encodeURIComponent(hostId)}` : "";
  return apiRequest<DomainCampaign[]>(`/host/ambassadors/campaigns${qs}`);
}

export async function fetchHostDomainCampaign(
  campaignId: string,
  hostId?: string | null,
): Promise<DomainCampaign> {
  const qs = hostId ? `?host_id=${encodeURIComponent(hostId)}` : "";
  return apiRequest<DomainCampaign>(
    `/host/ambassadors/campaigns/${campaignId}${qs}`,
  );
}

export async function pauseHostDomainCampaign(
  campaignId: string,
  hostId?: string | null,
): Promise<DomainCampaign> {
  const qs = hostId ? `?host_id=${encodeURIComponent(hostId)}` : "";
  return apiRequest<DomainCampaign>(
    `/host/ambassadors/campaigns/${campaignId}/pause${qs}`,
    { method: "POST" },
  );
}

export async function endHostDomainCampaign(
  campaignId: string,
  hostId?: string | null,
): Promise<DomainCampaign> {
  const qs = hostId ? `?host_id=${encodeURIComponent(hostId)}` : "";
  return apiRequest<DomainCampaign>(
    `/host/ambassadors/campaigns/${campaignId}/end${qs}`,
    { method: "POST" },
  );
}

export async function fetchHostCampaignParticipants(
  campaignId: string,
  hostId?: string | null,
): Promise<HostParticipantRow[]> {
  const qs = hostId ? `?host_id=${encodeURIComponent(hostId)}` : "";
  return apiRequest<HostParticipantRow[]>(
    `/host/ambassadors/campaigns/${campaignId}/participants${qs}`,
  );
}

export async function removeHostParticipant(
  participantId: string,
  hostId?: string | null,
): Promise<{ message: string }> {
  const qs = hostId ? `?host_id=${encodeURIComponent(hostId)}` : "";
  return apiRequest<{ message: string }>(
    `/host/ambassadors/participants/${participantId}/remove${qs}`,
    { method: "POST" },
  );
}

export async function fetchHostAmbassadorAnalytics(): Promise<HostAnalytics> {
  return apiRequest<HostAnalytics>("/host/ambassadors/analytics");
}

export async function fetchHostDomainPayouts(
  hostId?: string | null,
): Promise<DomainPayout[]> {
  const qs = hostId ? `?host_id=${encodeURIComponent(hostId)}` : "";
  return apiRequest<DomainPayout[]>(`/host/ambassadors/payouts${qs}`);
}

export type HostConversionRow = {
  id: string;
  ambassador_id: string;
  event_id: string;
  tickets_sold: number;
  merch_units_sold: number;
  revenue_amount: string | number;
  eligible_sale_amount?: string | number;
  commission_owed: string | number;
  commission_amount?: string | number;
  status: string;
  payout_status?: string | null;
  created_at: string;
  hold_until?: string | null;
  reversal_reason?: string | null;
  rejection_reason?: string | null;
  payout_reference?: string | null;
  payout_note?: string | null;
  event_title?: string | null;
  campaign_id?: string | null;
  campaign_name?: string | null;
  ambassador_display_name?: string | null;
  ambassador_referral_code?: string | null;
  ambassador_user_id?: string | null;
};

function hostQs(hostId?: string | null, status?: string): string {
  const qs = new URLSearchParams();
  if (hostId) qs.set("host_id", hostId);
  if (status) qs.set("status", status);
  const s = qs.toString();
  return s ? `?${s}` : "";
}

export async function fetchHostConversions(params?: {
  hostId?: string | null;
  status?: string;
}): Promise<HostConversionRow[]> {
  return apiRequest<HostConversionRow[]>(
    `/host/ambassadors/conversions${hostQs(params?.hostId, params?.status)}`,
  );
}

export async function setHostConversionRewardStatus(
  conversionId: string,
  input: {
    status: "approved" | "rejected" | "paid" | "reversed";
    reason?: string | null;
    payout_reference?: string | null;
    payout_note?: string | null;
    hostId?: string | null;
  },
): Promise<HostConversionRow> {
  const qs = input.hostId
    ? `?host_id=${encodeURIComponent(input.hostId)}`
    : "";
  return apiRequest<HostConversionRow>(
    `/host/ambassadors/conversions/${conversionId}/reward-status${qs}`,
    {
      method: "POST",
      body: {
        status: input.status,
        reason: input.reason ?? null,
        payout_reference: input.payout_reference ?? null,
        payout_note: input.payout_note ?? null,
      },
    },
  );
}

export async function reverseHostConversion(
  conversionId: string,
  reason: string,
  hostId?: string | null,
): Promise<HostConversionRow> {
  return setHostConversionRewardStatus(conversionId, {
    status: "reversed",
    reason,
    hostId,
  });
}

export type HostConversionAuditEntry = {
  id: string;
  action: string;
  actor_user_id?: string | null;
  actor_type?: string | null;
  host_profile_id?: string | null;
  campaign_id?: string | null;
  conversion_id?: string | null;
  old_status?: string | null;
  new_status?: string | null;
  reason?: string | null;
  payout_reference?: string | null;
  timestamp?: string | null;
  created_at?: string | null;
  ip_address?: string | null;
  user_agent?: string | null;
  details?: Record<string, unknown> | null;
};

export async function fetchHostConversionAudit(
  conversionId: string,
  hostId?: string | null,
): Promise<HostConversionAuditEntry[]> {
  const qs = hostId ? `?host_id=${encodeURIComponent(hostId)}` : "";
  return apiRequest<HostConversionAuditEntry[]>(
    `/host/ambassadors/conversions/${conversionId}/audit${qs}`,
  );
}

export async function fetchHostRewardAudit(params?: {
  hostId?: string | null;
  campaignId?: string | null;
}): Promise<HostConversionAuditEntry[]> {
  const qs = new URLSearchParams();
  if (params?.hostId) qs.set("host_id", params.hostId);
  if (params?.campaignId) qs.set("campaign_id", params.campaignId);
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<HostConversionAuditEntry[]>(
    `/host/ambassadors/reward-audit${suffix}`,
  );
}

export async function fetchAdminDomainConversions(params?: {
  status?: string;
}): Promise<DomainConversion[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<DomainConversion[]>(`/admin/ambassadors/conversions${suffix}`);
}

export async function fetchAdminDomainPayouts(params?: {
  status?: string;
}): Promise<DomainPayout[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<DomainPayout[]>(`/admin/ambassadors/payouts${suffix}`);
}

export async function reverseDomainConversion(
  id: string,
  reason: string,
): Promise<DomainConversion> {
  return apiRequest<DomainConversion>(
    `/admin/ambassadors/conversions/${id}/reverse`,
    { method: "POST", body: { reason } },
  );
}

export type DomainFraudFlag = {
  id: string;
  flag_type: string;
  campaign_id: string | null;
  participant_id: string | null;
  ambassador_code: string | null;
  ip_hash: string | null;
  click_count: number;
  window_start: string | null;
  window_end: string | null;
  status: string;
  details: Record<string, unknown>;
  created_at: string;
};

export async function fetchAdminFraudFlags(params?: {
  status?: string;
}): Promise<DomainFraudFlag[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<DomainFraudFlag[]>(
    `/admin/ambassadors/fraud-flags${suffix}`,
  );
}

export async function trackAmbassadorClick(input: {
  ambassador_code: string;
  campaign_id?: string;
  event_id?: string;
  session_id?: string;
  landing_url: string;
  referrer_url?: string;
}): Promise<{ ok: boolean; attribution_id?: string }> {
  return apiRequest("/ambassadors/track-click", {
    method: "POST",
    body: input,
    auth: false,
  });
}
