import { apiRequest } from "@/lib/api";

export type SponsorProfile = {
  id: string;
  owner_user_id: string | null;
  display_name: string;
  slug: string | null;
  sponsor_type: string | null;
  logo_url: string | null;
  cover_image_url: string | null;
  short_bio: string | null;
  description: string | null;
  website_url: string | null;
  industry: string | null;
  categories: string[] | null;
  target_locations: string[] | null;
  budget_range: string | null;
  campaign_goals: string[] | null;
  contact_email: string;
  contact_phone: string | null;
  verification_status: string;
  status: string;
  visibility: string;
  onboarding_status: string;
  sponsor_ready_score: number | null;
  created_at: string;
  updated_at: string;
};

export type SponsorWorkspace = {
  sponsor_id: string;
  display_name: string;
  slug: string | null;
  role: string;
  is_owner: boolean;
  permissions: Record<string, boolean>;
  verification_status: string;
  status: string;
  onboarding_status: string;
};

export type SponsorDirectoryCard = {
  id: string;
  display_name: string;
  slug: string;
  sponsor_type: string | null;
  logo_url: string | null;
  use_logo_fallback: boolean;
  industry: string | null;
  categories: string[];
  short_bio: string | null;
  verified: boolean;
  target_locations: string[];
  accepting_inquiries: boolean;
  public_campaigns_count: number;
  sponsored_events_count: number;
  partnered_hosts_count: number;
  partnership_hint: string | null;
};

export type SponsorPublicSummaryCard = {
  label: string;
  value: string;
};

export type SponsorPublicCampaignCard = {
  id: string;
  name: string;
  objective: string;
  objective_label: string;
  status: string;
  status_label: string;
  target_categories: string[];
  target_locations: string[];
  description: string | null;
  linked_sponsored_events_count: number;
};

export type SponsorPublicSponsoredEvent = {
  event_id: string | null;
  event_title: string;
  event_slug: string | null;
  host_id: string;
  host_slug: string | null;
  host_display_name: string;
  host_verified: boolean;
  category: string | null;
  city: string | null;
  area: string | null;
  starts_at: string | null;
  placement_status: string;
  placement_status_label: string;
  deliverable_labels: string[];
};

export type SponsorPublicPartnerHost = {
  host_id: string;
  slug: string | null;
  display_name: string;
  city: string | null;
  categories: string[];
  verified: boolean;
  sponsored_events_together: number;
};

export type SponsorPublicRelatedSponsor = {
  slug: string;
  display_name: string;
  industry: string | null;
  logo_url: string | null;
  categories: string[];
};

export type SponsorPublicProfile = {
  id: string;
  display_name: string;
  slug: string;
  sponsor_type: string | null;
  logo_url: string | null;
  cover_image_url: string | null;
  use_cover_fallback: boolean;
  short_bio: string | null;
  description: string | null;
  website_url: string | null;
  industry: string | null;
  categories: string[];
  target_locations: string[];
  campaign_goals: string[];
  verification_status: string;
  verified: boolean;
  show_contact_cta: boolean;
  accepting_inquiries: boolean;
  partnership_blurb: string | null;
  summary_cards: SponsorPublicSummaryCard[];
  public_campaigns: SponsorPublicCampaignCard[];
  sponsored_events: SponsorPublicSponsoredEvent[];
  partnered_hosts: SponsorPublicPartnerHost[];
  related_sponsors: SponsorPublicRelatedSponsor[];
};

export type SponsorInquiryRow = {
  id: string;
  slot_id: string;
  slot_title: string | null;
  host_display_name: string | null;
  status: string;
  message: string;
  created_at: string;
  updated_at: string;
};

export type SponsorAdminRow = {
  id: string;
  display_name: string;
  slug: string | null;
  sponsor_type: string | null;
  owner_user_id: string | null;
  verification_status: string;
  status: string;
  visibility: string;
  onboarding_status: string;
  created_at: string;
};

export type SponsorAdminDetail = SponsorProfile & {
  internal_notes: string | null;
  owner_email: string | null;
};

export async function fetchSponsorWorkspaces(): Promise<SponsorWorkspace[]> {
  return apiRequest<SponsorWorkspace[]>("/sponsors/workspaces");
}

export async function createSponsorProfile(body: {
  display_name: string;
  sponsor_type: string;
  industry?: string;
  categories?: string[];
  website_url?: string;
  short_bio?: string;
  description?: string;
  logo_url?: string;
  target_locations?: string[];
  campaign_goals?: string[];
  budget_range?: string;
  contact_email?: string;
  contact_phone?: string;
  submit_for_review?: boolean;
}): Promise<SponsorProfile> {
  return apiRequest<SponsorProfile>("/sponsors/profiles", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchMySponsorProfile(
  sponsorId?: string,
): Promise<SponsorProfile> {
  const q = sponsorId ? `?sponsor_id=${encodeURIComponent(sponsorId)}` : "";
  return apiRequest<SponsorProfile>(`/sponsors/me${q}`);
}

export async function updateMySponsorProfile(
  body: Record<string, unknown>,
  sponsorId?: string,
): Promise<SponsorProfile> {
  const q = sponsorId ? `?sponsor_id=${encodeURIComponent(sponsorId)}` : "";
  return apiRequest<SponsorProfile>(`/sponsors/me${q}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function fetchMySponsorInquiries(
  sponsorId?: string,
): Promise<SponsorInquiryRow[]> {
  const q = sponsorId ? `?sponsor_id=${encodeURIComponent(sponsorId)}` : "";
  return apiRequest<SponsorInquiryRow[]>(`/sponsors/me/inquiries${q}`);
}

export async function fetchSponsorDirectory(params?: {
  industry?: string;
  category?: string;
  location?: string;
  verified?: boolean;
  type?: string;
}): Promise<SponsorDirectoryCard[]> {
  const sp = new URLSearchParams();
  if (params?.industry) sp.set("industry", params.industry);
  if (params?.category) sp.set("category", params.category);
  if (params?.location) sp.set("location", params.location);
  if (params?.verified) sp.set("verified", "true");
  if (params?.type) sp.set("type", params.type);
  const qs = sp.toString();
  return apiRequest<SponsorDirectoryCard[]>(
    `/sponsors/public/directory${qs ? `?${qs}` : ""}`,
    { auth: false },
  );
}

export async function fetchPublicSponsorProfile(
  slug: string,
): Promise<SponsorPublicProfile> {
  return apiRequest<SponsorPublicProfile>(
    `/sponsors/public/${encodeURIComponent(slug)}`,
    { auth: false },
  );
}

export async function fetchAdminSponsors(): Promise<SponsorAdminRow[]> {
  return apiRequest<SponsorAdminRow[]>("/admin/sponsors");
}

export async function fetchAdminSponsorDetail(
  id: string,
): Promise<SponsorAdminDetail> {
  return apiRequest<SponsorAdminDetail>(
    `/admin/sponsors/${encodeURIComponent(id)}`,
  );
}

export async function adminVerifySponsor(
  id: string,
  action: "approve" | "reject",
  notes?: string,
): Promise<SponsorAdminDetail> {
  return apiRequest<SponsorAdminDetail>(
    `/admin/sponsors/${encodeURIComponent(id)}/verify`,
    {
      method: "POST",
      body: JSON.stringify({ action, notes }),
    },
  );
}

export async function adminSponsorStatus(
  id: string,
  status: string,
  notes?: string,
): Promise<SponsorAdminDetail> {
  return apiRequest<SponsorAdminDetail>(
    `/admin/sponsors/${encodeURIComponent(id)}/status`,
    {
      method: "POST",
      body: JSON.stringify({ status, notes }),
    },
  );
}

export async function adminSponsorNotes(
  id: string,
  internal_notes: string | null,
): Promise<SponsorAdminDetail> {
  return apiRequest<SponsorAdminDetail>(
    `/admin/sponsors/${encodeURIComponent(id)}/notes`,
    {
      method: "PATCH",
      body: JSON.stringify({ internal_notes }),
    },
  );
}
