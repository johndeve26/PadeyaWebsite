import { apiRequest } from "@/lib/api";
import type {
  HostSponsorshipSettings,
  SponsorHost,
  SponsorshipInquiry,
  SponsorshipPlacement,
  SponsorshipSlot,
} from "@/lib/types/sponsorships";

export async function fetchPublicSponsorshipSlots(): Promise<SponsorshipSlot[]> {
  return apiRequest<SponsorshipSlot[]>("/sponsorships/public/slots", { auth: false });
}

export async function fetchPublicSponsorshipSlot(
  slotId: string,
): Promise<SponsorshipSlot> {
  return apiRequest<SponsorshipSlot>(`/sponsorships/public/slots/${slotId}`, {
    auth: false,
  });
}

export async function fetchSponsorHosts(): Promise<SponsorHost[]> {
  return apiRequest<SponsorHost[]>("/sponsorships/public/hosts", { auth: false });
}

export async function submitSponsorshipInquiry(
  slotId: string,
  body: {
    company_name: string;
    contact_name: string;
    contact_email: string;
    website?: string;
    message: string;
    proposed_budget?: number | string;
    campaign_id?: string;
    sponsor_id?: string;
  },
): Promise<SponsorshipInquiry> {
  const useAuth = Boolean(body.campaign_id || body.sponsor_id);
  return apiRequest<SponsorshipInquiry>(
    `/sponsorships/public/slots/${slotId}/inquire`,
    { method: "POST", body, auth: useAuth ? true : false },
  );
}

export async function fetchHostSponsorshipSettings(): Promise<HostSponsorshipSettings> {
  return apiRequest<HostSponsorshipSettings>("/sponsorships/host/settings");
}

export async function updateHostSponsorshipSettings(
  body: Partial<HostSponsorshipSettings>,
): Promise<HostSponsorshipSettings> {
  return apiRequest<HostSponsorshipSettings>("/sponsorships/host/settings", {
    method: "PATCH",
    body,
  });
}

export async function fetchHostSponsorshipSlots(): Promise<SponsorshipSlot[]> {
  return apiRequest<SponsorshipSlot[]>("/sponsorships/host/slots");
}

export async function createSponsorshipSlot(
  body: Record<string, unknown>,
): Promise<SponsorshipSlot> {
  return apiRequest<SponsorshipSlot>("/sponsorships/host/slots", {
    method: "POST",
    body,
  });
}

export async function updateSponsorshipSlot(
  slotId: string,
  body: Record<string, unknown>,
): Promise<SponsorshipSlot> {
  return apiRequest<SponsorshipSlot>(`/sponsorships/host/slots/${slotId}`, {
    method: "PATCH",
    body,
  });
}

export async function fetchHostInquiries(): Promise<SponsorshipInquiry[]> {
  return apiRequest<SponsorshipInquiry[]>("/sponsorships/host/inquiries");
}

export async function updateHostInquiry(
  inquiryId: string,
  body: { status: string; host_note?: string },
): Promise<SponsorshipInquiry> {
  return apiRequest<SponsorshipInquiry>(
    `/sponsorships/host/inquiries/${inquiryId}`,
    { method: "PATCH", body },
  );
}

export async function fetchHostPlacements(): Promise<SponsorshipPlacement[]> {
  return apiRequest<SponsorshipPlacement[]>("/sponsorships/host/placements");
}

export async function fetchAdminSponsorshipSlots(): Promise<SponsorshipSlot[]> {
  return apiRequest<SponsorshipSlot[]>("/sponsorships/admin/slots");
}

export async function moderateSponsorshipSlot(
  slotId: string,
  action: string,
  note?: string,
): Promise<SponsorshipSlot> {
  return apiRequest<SponsorshipSlot>(
    `/sponsorships/admin/slots/${slotId}/moderate`,
    { method: "POST", body: { action, note } },
  );
}
