import { apiRequest } from "@/lib/api";

export type SponsorCampaignListItem = {
  id: string;
  name: string;
  public_ref: string;
  objective: string;
  status: string;
  visibility: string;
  moderation_status: string;
  budget_min: string | null;
  budget_max: string | null;
  currency: string;
  start_date: string | null;
  end_date: string | null;
  saved_items_count: number;
  inquiries_count: number;
  created_at: string;
  updated_at: string;
};

export type CampaignSavedItemRow = {
  id: string;
  sponsor_saved_item_id: string;
  item_type: string;
  item_id: string;
  title: string | null;
  subtitle: string | null;
  href: string | null;
  available: boolean;
  note: string | null;
  created_at: string;
};

export type CampaignInquiryRow = {
  id: string;
  slot_id: string;
  slot_title: string | null;
  host_display_name: string | null;
  status: string;
  created_at: string;
};

export type SponsorCampaignDetail = SponsorCampaignListItem & {
  description: string | null;
  target_categories: string[] | null;
  target_locations: string[] | null;
  target_audience: Record<string, unknown> | null;
  rejection_reason: string | null;
  saved_items: CampaignSavedItemRow[];
  inquiries: CampaignInquiryRow[];
  can_edit: boolean;
};

export const CAMPAIGN_OBJECTIVES: { value: string; label: string }[] = [
  { value: "brand_awareness", label: "Brand awareness" },
  { value: "product_launch", label: "Product launch" },
  { value: "event_activation", label: "Event activation" },
  { value: "lead_generation", label: "Lead generation" },
  { value: "community_engagement", label: "Community engagement" },
  { value: "campus_activation", label: "Campus activation" },
  { value: "merch_collaboration", label: "Merch collaboration" },
  { value: "media_partnership", label: "Media partnership" },
  { value: "other", label: "Other" },
];

export async function fetchSponsorCampaigns(
  sponsorId: string,
): Promise<{ items: SponsorCampaignListItem[]; total: number }> {
  return apiRequest(`/sponsors/workspaces/${sponsorId}/campaigns`);
}

export async function fetchSponsorCampaign(
  sponsorId: string,
  campaignId: string,
): Promise<SponsorCampaignDetail> {
  return apiRequest(
    `/sponsors/workspaces/${sponsorId}/campaigns/${campaignId}`,
  );
}

export async function createSponsorCampaign(
  sponsorId: string,
  body: {
    name: string;
    objective: string;
    description?: string;
    target_categories?: string[];
    target_locations?: string[];
    target_audience?: Record<string, unknown>;
    budget_min?: number | string;
    budget_max?: number | string;
    currency?: string;
    start_date?: string;
    end_date?: string;
    visibility?: string;
    sponsor_saved_item_id?: string;
  },
): Promise<SponsorCampaignDetail> {
  return apiRequest(`/sponsors/workspaces/${sponsorId}/campaigns`, {
    method: "POST",
    body,
  });
}

export async function updateSponsorCampaign(
  sponsorId: string,
  campaignId: string,
  body: Record<string, unknown>,
): Promise<SponsorCampaignDetail> {
  return apiRequest(
    `/sponsors/workspaces/${sponsorId}/campaigns/${campaignId}`,
    { method: "PATCH", body },
  );
}

export async function activateSponsorCampaign(
  sponsorId: string,
  campaignId: string,
): Promise<SponsorCampaignDetail> {
  return apiRequest(
    `/sponsors/workspaces/${sponsorId}/campaigns/${campaignId}/activate`,
    { method: "POST" },
  );
}

export async function pauseSponsorCampaign(
  sponsorId: string,
  campaignId: string,
): Promise<SponsorCampaignDetail> {
  return apiRequest(
    `/sponsors/workspaces/${sponsorId}/campaigns/${campaignId}/pause`,
    { method: "POST" },
  );
}

export async function archiveSponsorCampaign(
  sponsorId: string,
  campaignId: string,
): Promise<SponsorCampaignDetail> {
  return apiRequest(
    `/sponsors/workspaces/${sponsorId}/campaigns/${campaignId}/archive`,
    { method: "POST" },
  );
}

export async function addSavedItemToCampaign(
  sponsorId: string,
  campaignId: string,
  sponsorSavedItemId: string,
  note?: string,
): Promise<CampaignSavedItemRow> {
  return apiRequest(
    `/sponsors/workspaces/${sponsorId}/campaigns/${campaignId}/saved-items`,
    {
      method: "POST",
      body: { sponsor_saved_item_id: sponsorSavedItemId, note },
    },
  );
}

export async function removeSavedItemFromCampaign(
  sponsorId: string,
  campaignId: string,
  savedItemId: string,
): Promise<void> {
  return apiRequest(
    `/sponsors/workspaces/${sponsorId}/campaigns/${campaignId}/saved-items/${savedItemId}`,
    { method: "DELETE" },
  );
}

export async function fetchAdminSponsorCampaigns(): Promise<
  {
    id: string;
    sponsor_id: string;
    sponsor_name: string;
    name: string;
    objective: string;
    status: string;
    visibility: string;
    moderation_status: string;
    created_at: string;
  }[]
> {
  return apiRequest("/admin/sponsor-campaigns");
}

export async function adminApproveSponsorCampaign(
  campaignId: string,
): Promise<void> {
  await apiRequest(`/admin/sponsor-campaigns/${campaignId}/approve`, {
    method: "POST",
  });
}

export async function adminRejectSponsorCampaign(
  campaignId: string,
  rejection_reason: string,
): Promise<void> {
  await apiRequest(`/admin/sponsor-campaigns/${campaignId}/reject`, {
    method: "POST",
    body: { rejection_reason },
  });
}

export type CampaignRecommendation = {
  item_type: string;
  item_id: string;
  score: number;
  score_label: string | null;
  reasons: { code: string; label: string }[];
  title: string | null;
  subtitle: string | null;
  href: string | null;
  available: boolean;
  host_display_name: string | null;
  slot_price: number | null;
  audience_estimate: number | null;
};

export async function fetchCampaignRecommendations(
  sponsorId: string,
  campaignId: string,
): Promise<{ items: CampaignRecommendation[]; total: number }> {
  return apiRequest(
    `/sponsors/workspaces/${sponsorId}/campaigns/${campaignId}/recommendations`,
  );
}

export async function sendCampaignRecommendationFeedback(
  sponsorId: string,
  campaignId: string,
  itemId: string,
  body: { item_type: string; action: string },
): Promise<void> {
  await apiRequest(
    `/sponsors/workspaces/${sponsorId}/campaigns/${campaignId}/recommendations/${itemId}/feedback`,
    { method: "POST", body },
  );
}
