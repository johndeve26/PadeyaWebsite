export type FollowingHost = {
  host_id: string;
  display_name: string;
  username: string;
  marketing_opt_in: boolean;
  followed_at: string;
};

export type AudienceMember = {
  user_id: string;
  display_name: string;
  email: string;
  marketing_opt_in: boolean;
  events_attended: number;
  tickets_purchased: number;
  last_order_at: string | null;
  tags: string[];
};

export type AudienceStats = {
  followers: number;
  past_buyers: number;
  repeat_buyers: number;
  vip_buyers: number;
  checked_in_attendees: number;
  no_shows: number;
  promo_code_buyers: number;
  ambassador_referrals: number;
  marketing_opted_in: number;
};

export type AudienceSegment = {
  id: string;
  name: string;
  slug: string;
  segment_key: string;
  description: string | null;
  filters: Record<string, unknown> | null;
  is_system: boolean;
  created_at: string;
  member_count: number;
};

export type AnnouncementRecipient = {
  id: string;
  user_id: string;
  email: string;
  display_name: string;
  channel: string;
  status: string;
  skip_reason: string | null;
};

export type Announcement = {
  id: string;
  host_id: string;
  segment_id: string | null;
  title: string;
  body_email: string;
  body_whatsapp: string | null;
  channel: string;
  status: string;
  delivery_status: string;
  recipient_count: number;
  created_at: string;
  recipients: AnnouncementRecipient[];
  whatsapp_export: string | null;
};

export type AnnouncementDispatchResult = {
  announcement_id: string;
  emailed: number;
  skipped: number;
  delivery_status: string;
  delivery_provider?: string | null;
};

export const SEGMENT_KEYS = [
  "followers",
  "past_buyers",
  "repeat_buyers",
  "vip_buyers",
  "checked_in_attendees",
  "no_shows",
  "promo_code_buyers",
  "ambassador_referrals",
  "superfans",
  "vault_subscribers",
] as const;

export type SegmentKey = (typeof SEGMENT_KEYS)[number];
