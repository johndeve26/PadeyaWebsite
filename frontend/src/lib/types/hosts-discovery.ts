export type HostDiscoveryNextEvent = {
  title: string;
  slug: string;
  start_datetime: string;
  city?: string | null;
};

/** Public host marketplace card from GET /legacy/discover/hosts */
export type HostDiscovery = {
  host_id: string;
  display_name: string;
  username: string;
  verified: boolean;
  legacy_tier: string;
  legacy_status: string;
  bio?: string | null;
  tagline?: string | null;
  avatar_url?: string | null;
  cover_url?: string | null;
  primary_city?: string | null;
  primary_category?: string | null;
  host_type?: string | null;
  upcoming_events_count: number;
  completed_events_count: number;
  verified_checkins_count: number;
  /** Legacy score ticket sales (marketplace cards). */
  tickets_sold_count?: number;
  average_rating?: number | null;
  review_count: number;
  followers_count: number;
  vault_items_count: number;
  sponsor_ready: boolean;
  next_upcoming_event?: HostDiscoveryNextEvent | null;
  share_path: string;
};

export type HostRecommendationReason = {
  code: string;
  label: string;
};

export type HostRecommendation = {
  host: HostDiscovery;
  score: number;
  reasons: HostRecommendationReason[];
  recommendation_label?: string | null;
  relationship?: string;
};

export type HostRecommendationsResponse = {
  items: HostRecommendation[];
  page: number;
  limit: number;
  total: number;
  next_cursor?: string | null;
  empty_title?: string | null;
  empty_description?: string | null;
};
