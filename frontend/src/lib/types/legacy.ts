import type { HostProfile } from "@/lib/types/events";

export type LegacyTier = {
  id: string;
  slug: string;
  name: string;
  rank: number;
  min_score: string | number;
  description: string | null;
  requirements: Record<string, number | null> | null;
  is_active: boolean;
};

export type LegacyStats = {
  events_hosted: number;
  tickets_sold: number;
  verified_checkins: number;
  average_verified_rating: string | number | null;
  review_count: number;
  followers: number;
  repeat_buyers_rate: string | number | null;
  refund_dispute_rate: string | number | null;
  legacy_status: string;
  composite_score?: string | number | null;
  completed_events?: number | null;
  /** Merch proof aggregates — counts only, never buyer identities or spend */
  merch_items_sold?: number;
  fans_collected_merch?: number;
  merch_proof_summaries?: string[];
};

export type LegacyEventCard = {
  id: string;
  title: string;
  slug: string;
  start_datetime: string;
  end_datetime: string;
  city: string | null;
  banner_url: string | null;
  status: string;
  memory_path?: string | null;
};

export type LegacyMemoryCard = {
  id: string;
  event_id: string;
  event_title: string;
  event_slug: string;
  start_datetime: string;
  city: string | null;
  banner_url: string | null;
  share_path: string;
  verified_rating?: string | number | null;
};

export type ReviewReply = {
  id: string;
  body: string;
  author_name: string | null;
  created_at: string;
};

export type VerifiedReview = {
  id: string;
  event_id: string;
  host_id: string;
  reviewer_user_id: string;
  ticket_id: string;
  rating: number;
  title: string | null;
  body: string;
  status: string;
  event_title: string | null;
  event_slug?: string | null;
  reviewer_name: string | null;
  created_at: string;
  reply: ReviewReply | null;
  report_count: number;
  moderation_reason: string | null;
};

export type LegacyContentBlock = {
  id: string;
  host_id: string;
  block_type: string;
  title_override: string | null;
  description_override: string | null;
  is_visible: boolean;
  sort_order: number;
  layout_style: string;
  source_type: string;
  item_limit: number | null;
  config: Record<string, unknown> | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type LegacyFeaturedItem = {
  id?: string | null;
  host_id?: string | null;
  item_type: string;
  item_id: string;
  placement: string;
  sort_order: number;
  created_at?: string | null;
};

export type LegacySocialLink = {
  id?: string | null;
  host_id?: string | null;
  platform: string;
  url: string;
  label?: string | null;
  sort_order: number;
  is_visible: boolean;
  created_at?: string | null;
};

export type LegacyContactSettings = {
  preference: string;
  public_email?: string | null;
  show_contact_form: boolean;
  preferred_channel?: string | null;
  note?: string | null;
  id?: string | null;
  host_id?: string | null;
};

export type LegacyPageSettings = {
  tagline?: string | null;
  primary_category_slug?: string | null;
  host_type_slug?: string | null;
  service_areas?: unknown[];
  sponsorship_available: boolean;
  sponsorship_note?: string | null;
  primary_cta_label?: string | null;
  primary_cta_type?: string | null;
  primary_cta_value?: string | null;
  secondary_cta_label?: string | null;
  secondary_cta_type?: string | null;
  secondary_cta_value?: string | null;
};

export type LegacyVaultPreviewCard = {
  id: string;
  title: string;
  slug: string;
  cover_url: string | null;
  preview_text: string | null;
  locked: boolean;
  has_access: boolean;
  featured?: boolean;
  access_type?: string | null;
  content_type?: string | null;
  price?: string | number | null;
  currency?: string | null;
  share_path: string;
};

export const VAULT_PREVIEW_LAYOUTS = [
  { value: "locked_cards", label: "Locked cards" },
  { value: "featured_spotlight", label: "Featured spotlight" },
  { value: "compact_row", label: "Compact row" },
] as const;

export type LegacySponsorPackageCard = {
  id: string;
  title: string;
  description: string;
  price: string | number;
  currency: string;
  slot_type: string;
  accepting_sponsors: boolean;
};

export type LegacyPage = {
  host_id: string;
  display_name: string;
  username: string;
  status: string;
  verified: boolean;
  legacy_status: string;
  tier?: LegacyTier | null;
  composite_score?: string | number | null;
  profile: HostProfile | null;
  stats: LegacyStats;
  about: string | null;
  upcoming_events: LegacyEventCard[];
  past_events: LegacyEventCard[];
  event_memories?: LegacyMemoryCard[];
  reviews: VerifiedReview[];
  follow_enabled: boolean;
  share_path: string;
  tagline?: string | null;
  settings?: LegacyPageSettings | null;
  content_blocks?: LegacyContentBlock[];
  featured_items?: LegacyFeaturedItem[];
  social_links?: LegacySocialLink[];
  contact?: LegacyContactSettings | null;
  vault_preview?: LegacyVaultPreviewCard[];
  sponsor_packages?: LegacySponsorPackageCard[];
  reviews_block_hidden?: boolean;
  trust_note?: string | null;
};

export type RequirementItem = {
  key: string;
  label: string;
  current: number;
  required: number;
  met: boolean;
};

export type ScoreHistory = {
  id: string;
  host_id?: string | null;
  tier_slug: string;
  previous_tier_slug: string | null;
  composite_score: string | number;
  previous_composite_score: string | number | null;
  reason: string;
  created_at: string;
  factor_scores?: Record<string, number> | null;
  metrics_snapshot?: Record<string, unknown> | null;
};

export type TierProgress = {
  host_id: string;
  composite_score: string | number;
  factor_scores: Record<string, number>;
  current_tier: LegacyTier | null;
  next_tier: LegacyTier | null;
  progress_percentage: string | number;
  requirements_met: RequirementItem[];
  requirements_remaining: RequirementItem[];
  suggested_actions: string[];
  metrics: Record<string, unknown>;
  history: ScoreHistory[];
};

export type HostTierSummary = {
  host_id: string;
  display_name: string;
  username: string;
  composite_score: string | number;
  tier: LegacyTier | null;
  legacy_status: string;
  updated_at: string;
};

export type ReviewEligibility = {
  eligible: boolean;
  reason: string | null;
  ticket_id: string | null;
  event_id: string | null;
  event_title: string | null;
  host_id: string | null;
};

export type ReviewReport = {
  id: string;
  review_id: string;
  reporter_user_id: string;
  reason: string;
  status: string;
  created_at: string;
  review: VerifiedReview | null;
};

export const BLOCK_TYPE_LABELS: Record<string, string> = {
  about: "About",
  upcoming_events: "Upcoming Events",
  past_events: "Past Events",
  event_memories: "Event Memories",
  verified_reviews: "Verified Reviews",
  vault_preview: "Vault Preview",
  sponsor_packages: "Sponsor Packages",
  photo_gallery: "Photo Gallery",
  featured_video: "Featured Video",
  faq: "FAQ",
  contact_cta: "Contact CTA",
  related_discovery: "Related Discovery",
};

export const BLOCK_TYPE_HINTS: Record<string, string> = {
  about: "Bio and host story visitors see first.",
  upcoming_events: "Published nights from your calendar.",
  past_events: "Archive of completed nights.",
  event_memories: "Public recaps linked to completed events.",
  verified_reviews: "Checked-in attendee reviews only. Hiding the block does not delete reviews.",
  vault_preview:
    "Choose which Vault teasers appear, set title/description, automatic or manual source, and layout. Locked bodies never appear on Legacy.",
  sponsor_packages: "Published sponsorship slots and CTA.",
  photo_gallery: "Manual media gallery.",
  featured_video: "Manual featured video embed.",
  faq: "Manual FAQ answers.",
  contact_cta: "Contact preference and CTA.",
  related_discovery: "Related hosts, cities, and scenes.",
};
