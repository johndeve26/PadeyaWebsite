export type FanBadge = {
  id: string;
  slug: string;
  name: string;
  description: string;
  criteria_key: string;
  awarded_at: string | null;
  earned: boolean;
};

export type LoyaltyRecord = {
  host_id: string;
  host_display_name: string;
  host_username: string;
  tickets_bought: number;
  check_ins: number;
  vip_purchases: number;
  is_superfan: boolean;
  follows_host: boolean;
};

export type PassportEvent = {
  event_id: string;
  title: string;
  slug: string;
  host_username: string | null;
  start_datetime: string;
  city: string | null;
  ticket_status: string;
  ticket_type_name: string;
  checked_in: boolean;
  is_vip: boolean;
};

export type PassportEventSafe = {
  event_id: string;
  title: string;
  slug: string;
  host_username?: string | null;
  host_display_name?: string | null;
  start_datetime: string;
  city?: string | null;
  checked_in?: boolean;
};

export type VaultSummary = {
  paid_unlocks: number;
  pending_unlocks: number;
  unlocked_item_titles: string[];
};

export type PassportVisibility = "private" | "unlisted" | "public";

export type PassportSettings = {
  username: string | null;
  display_name: string;
  avatar_url: string | null;
  tagline: string | null;
  bio: string | null;
  visibility: PassportVisibility;
  appear_in_directory: boolean;
  show_attended_events: boolean;
  show_badges: boolean;
  show_followed_hosts: boolean;
  show_reviews: boolean;
  show_vault_unlocks: boolean;
  show_city_category_stats: boolean;
  hide_private_events_always: boolean;
  share_path: string | null;
};

export type FanDirectoryCard = {
  username: string;
  /** Passport owner user id — used for own-page CTA gating. */
  user_id: string;
  display_name: string;
  avatar_url?: string | null;
  tagline?: string | null;
  city_label?: string | null;
  favorite_scene?: string | null;
  top_badges: { slug: string; name: string }[];
  gender?: string | null;
  gender_short?: string | null;
  gender_label?: string | null;
  gender_visible?: boolean;
  events_attended: number;
  hosts_followed: number;
  reviews_written: number;
  cities_explored: number;
  connections_count: number;
  badges_earned_count: number;
  vault_unlocks_count: number;
  latest_badge_name?: string | null;
  is_superfan: boolean;
  share_path: string;
  stats_limited: boolean;
};

export type FanDirectoryList = {
  items: FanDirectoryCard[];
  page: number;
  limit: number;
  total: number;
};

export type AdminFanRow = {
  user_id: string;
  username: string | null;
  display_name: string;
  visibility: PassportVisibility;
  appear_in_directory: boolean;
  admin_hidden: boolean;
  admin_hidden_at?: string | null;
  admin_hidden_reason?: string | null;
  user_active: boolean;
  share_path?: string | null;
  events_attended: number;
};

export type FanPassport = {
  id: string;
  user_id: string;
  display_name: string;
  username?: string | null;
  avatar_url?: string | null;
  tagline?: string | null;
  bio?: string | null;
  visibility: PassportVisibility;
  share_path?: string | null;
  gender?: string | null;
  gender_short?: string | null;
  gender_label?: string | null;
  gender_visible?: boolean;
  gender_visibility?: string;
  tickets_bought: number;
  events_attended: number;
  hosts_followed: number;
  vip_purchases: number;
  vault_unlocks: number;
  is_superfan: boolean;
  favorite_categories: string[] | null;
  favorite_cities?: string[];
  reviews_written?: number;
  cities_explored?: number;
  categories_explored?: number;
  completion_score?: number;
  badges_earned: FanBadge[];
  loyalty: LoyaltyRecord[];
  attended_events: PassportEvent[];
  upcoming_tickets: PassportEvent[];
  vip_history: PassportEvent[];
  recent_checkins?: PassportEvent[];
  followed_hosts: { host_id: string; display_name: string; username: string }[];
  vault_summary: VaultSummary;
  /** Count-only merch lines — never spend or order data */
  merch_proof_summaries?: string[];
  settings?: PassportSettings;
  created_at: string;
  updated_at: string;
};

export type FanPassportPublicPage = {
  username: string;
  /** Passport owner user id — preferred for own-page detection. */
  user_id: string;
  display_name: string;
  avatar_url?: string | null;
  /** Variant payload when public-media pipeline has processed the DP. */
  avatar_media?: import("@/lib/types/public-media").PublicMedia | null;
  tagline?: string | null;
  bio?: string | null;
  visibility: PassportVisibility;
  is_superfan: boolean;
  gender?: string | null;
  gender_short?: string | null;
  gender_label?: string | null;
  gender_visible?: boolean;
  events_attended: number;
  hosts_followed: number;
  badges_earned_count: number;
  reviews_written: number;
  cities_explored: number;
  categories_explored: number;
  /** Accepted Fan Connect connections. */
  connections_count: number;
  favorite_categories: string[];
  favorite_cities: string[];
  badges: FanBadge[];
  attended_events: PassportEventSafe[];
  followed_hosts: {
    host_id: string;
    display_name: string;
    username: string;
    share_path?: string | null;
    avatar_url?: string | null;
    city?: string | null;
    category?: string | null;
    is_verified?: boolean;
    legacy_tier?: string | null;
  }[];
  reviews: {
    id: string;
    rating: number;
    body?: string | null;
    event_title?: string | null;
    host_username?: string | null;
    created_at: string;
  }[];
  vault_unlocks: {
    title: string;
    host_username?: string | null;
    access_label: string;
  }[];
  /** Count-only merch lines — never spend or order data */
  merch_proof_summaries?: string[];
  share_path: string;
};

export type PassportSettingsUpdate = Partial<
  Omit<PassportSettings, "share_path">
>;
