export type SponsorshipSlot = {
  id: string;
  host_id: string;
  event_id: string | null;
  slot_type: string;
  slot_type_label: string;
  title: string;
  description: string;
  price: string | number;
  currency: string;
  status: string;
  moderation_status: string;
  host_display_name: string | null;
  host_username: string | null;
  host_verified: boolean;
  event_title: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SponsorHost = {
  host_id: string;
  display_name: string;
  username: string;
  verified: boolean;
  city: string | null;
  bio: string | null;
  accepting_sponsors: boolean;
  pitch: string | null;
  open_slots: number;
};

export type SponsorshipInquiry = {
  id: string;
  slot_id: string;
  sponsor_id: string | null;
  company_name: string;
  contact_name: string;
  contact_email: string;
  website: string | null;
  message: string;
  proposed_budget: string | number | null;
  status: string;
  host_note: string | null;
  slot_title: string | null;
  created_at: string;
  updated_at: string;
};

export type HostSponsorshipSettings = {
  host_id: string;
  accepting_sponsors: boolean;
  contact_email: string | null;
  pitch: string | null;
  audience_notes: string | null;
};

export type SponsorshipPlacement = {
  id: string;
  slot_id: string;
  sponsor_id: string;
  inquiry_id: string | null;
  status: string;
  asset_url: string | null;
  starts_at: string | null;
  ends_at: string | null;
  company_name: string | null;
  slot_title: string | null;
  analytics: {
    placement_id: string;
    impressions: number;
    clicks: number;
    inquiries_attributed: number;
  } | null;
  created_at: string;
};
