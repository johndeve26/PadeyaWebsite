export type SeriesPoint = { date: string; value: string | number };

export type TicketTypeBreakdown = {
  ticket_type_id: string | null;
  name: string;
  tickets_sold: number;
  revenue: string | number;
};

export type PromoPerfRow = {
  promo_code_id: string;
  code: string;
  redemptions: number;
  discount_total: string | number;
  orders: number;
};

export type AmbassadorPerfRow = {
  ambassador_id: string;
  name: string;
  referral_code: string;
  clicks: number;
  tickets_sold: number;
  revenue: string | number;
  conversion_rate: string | number | null;
};

export type HostAnalyticsSummary = {
  host_id: string;
  range_start: string;
  range_end: string;
  tickets_sold: number;
  revenue: string | number;
  check_ins: number;
  no_shows: number;
  page_views: number;
  event_impressions: number;
  event_clicks: number;
  unique_impressions?: number;
  unique_clicks?: number;
  unique_detail_views?: number;
  checkout_starts: number;
  checkout_completes: number;
  conversion_rate: string | number | null;
  repeat_buyers: number;
  unique_buyers: number;
  vault_earnings: string | number;
  ticket_type_breakdown: TicketTypeBreakdown[];
  promo_performance: PromoPerfRow[];
  ambassador_performance: AmbassadorPerfRow[];
  sales_over_time: SeriesPoint[];
  page_views_over_time: SeriesPoint[];
  legacy_score_trend: SeriesPoint[];
};

export type EventAnalyticsSummary = {
  event_id: string;
  host_id: string;
  title: string;
  tickets_sold: number;
  revenue: string | number;
  check_ins: number;
  no_shows: number;
  page_views: number;
  impressions: number;
  clicks: number;
  unique_impressions?: number;
  unique_clicks?: number;
  unique_detail_views?: number;
  checkout_starts: number;
  checkout_completes: number;
  conversion_rate: string | number | null;
  ticket_type_breakdown: TicketTypeBreakdown[];
  sales_over_time: SeriesPoint[];
};

/* ---------- Detailed per-event analytics ---------- */

export type EventAnalyticsFilterEcho = {
  date_from: string;
  date_to: string;
  source?: string | null;
  medium?: string | null;
  campaign?: string | null;
  ticket_type_id?: string | null;
  device_type?: string | null;
  city?: string | null;
  include_bots: boolean;
};

export type ConversionRates = {
  impression_to_click?: string | number | null;
  click_to_detail?: string | number | null;
  detail_to_ticket_selection?: string | number | null;
  ticket_selection_to_checkout?: string | number | null;
  checkout_to_purchase?: string | number | null;
  view_to_purchase?: string | number | null;
  impression_to_purchase?: string | number | null;
};

export type EventAnalyticsOverview = {
  event_id: string;
  host_id: string;
  title: string;
  filters: EventAnalyticsFilterEcho;
  impressions: number;
  unique_impressions: number;
  event_card_clicks: number;
  event_detail_views: number;
  unique_visitors: number;
  ticket_selections: number;
  checkout_starts: number;
  purchases: number;
  tickets_sold: number;
  revenue: string | number;
  conversion_rates: ConversionRates;
  average_order_value?: string | number | null;
  refund_count: number;
  refund_rate?: string | number | null;
  check_in_count: number;
  check_in_rate?: string | number | null;
  review_count: number;
  average_rating?: string | number | null;
  /** Funnel traffic from daily rollups when unfiltered; commerce still from orders/tickets. */
  traffic_source?: "rollup" | "live";
};

export type EventAnalyticsFunnel = {
  event_id: string;
  host_id: string;
  filters: EventAnalyticsFilterEcho;
  impressions: number;
  card_clicks: number;
  detail_views: number;
  ticket_selections: number;
  checkout_starts: number;
  payment_starts: number;
  purchases: number;
  tickets_issued: number;
  check_ins: number;
  reviews: number;
  dropoffs: Record<string, number>;
};

export type TimeseriesPoint = {
  bucket: string;
  impressions: number;
  views: number;
  checkout_starts: number;
  purchases: number;
  revenue: string | number;
};

export type EventAnalyticsTimeseries = {
  event_id: string;
  host_id: string;
  filters: EventAnalyticsFilterEcho;
  granularity: "hour" | "day" | "week";
  points: TimeseriesPoint[];
};

export type SourceBreakdownRow = {
  source_bucket: string;
  impressions: number;
  clicks: number;
  detail_views: number;
  checkout_starts: number;
  purchases: number;
  revenue: string | number;
};

export type EventAnalyticsSources = {
  event_id: string;
  host_id: string;
  filters: EventAnalyticsFilterEcho;
  buckets: SourceBreakdownRow[];
  utm_campaigns: {
    source?: string | null;
    medium?: string | null;
    campaign?: string | null;
    impressions: number;
    clicks: number;
    detail_views: number;
    checkout_starts: number;
    purchases: number;
  }[];
};

export type TicketTypeAnalyticsRow = {
  ticket_type_id: string;
  name: string;
  price: string | number;
  impressions: number;
  selections: number;
  sold: number;
  revenue: string | number;
  conversion_rate?: string | number | null;
  remaining_inventory: number;
  sell_through_rate?: string | number | null;
};

export type EventAnalyticsTickets = {
  event_id: string;
  host_id: string;
  filters: EventAnalyticsFilterEcho;
  ticket_types: TicketTypeAnalyticsRow[];
};

export type AudienceBucketRow = {
  key: string;
  visitors: number;
  detail_views: number;
  purchases: number;
};

export type EventAnalyticsAudience = {
  event_id: string;
  host_id: string;
  filters: EventAnalyticsFilterEcho;
  new_vs_returning: AudienceBucketRow[];
  auth_status: AudienceBucketRow[];
  devices: AudienceBucketRow[];
  cities: AudienceBucketRow[];
  countries: AudienceBucketRow[];
  browsers: AudienceBucketRow[];
  follower_conversion?: {
    buyers: number;
    follower_buyers: number;
    rate?: string | number | null;
  } | null;
};

export type EventAnalyticsPromos = {
  event_id: string;
  host_id: string;
  filters: EventAnalyticsFilterEcho;
  promos: {
    promo_code_id: string;
    code: string;
    redemptions: number;
    discount_total: string | number;
    orders: number;
  }[];
};

export type EventAnalyticsAmbassadors = {
  event_id: string;
  host_id: string;
  filters: EventAnalyticsFilterEcho;
  ambassadors: {
    ambassador_id: string;
    name: string;
    referral_code: string;
    clicks: number;
    tickets_sold: number;
    revenue: string | number;
    commission_owed?: string | number;
    conversion_rate?: string | number | null;
  }[];
};

export type AdminEventAnalyticsBundle = {
  overview: EventAnalyticsOverview;
  funnel: EventAnalyticsFunnel;
  sources: EventAnalyticsSources;
  tickets: EventAnalyticsTickets;
};

export type EventAnalyticsQuery = {
  date_from?: string;
  date_to?: string;
  source?: string;
  medium?: string;
  campaign?: string;
  ticket_type_id?: string;
  device_type?: string;
  city?: string;
  include_bots?: boolean;
};

export type AdminEventLeaderboardRow = {
  event_id: string;
  host_id: string;
  title: string;
  host_display_name?: string | null;
  impressions: number;
  detail_views: number;
  checkout_starts: number;
  purchases: number;
  tickets_sold: number;
  revenue: string | number;
  conversion_rate?: string | number | null;
};

export type AdminEventLeaderboard = {
  filters: EventAnalyticsFilterEcho;
  sort_by: string;
  events: AdminEventLeaderboardRow[];
};

export type AdminEventCompare = {
  filters: EventAnalyticsFilterEcho;
  events: EventAnalyticsOverview[];
};

export type AdminChannelPerformance = {
  filters: EventAnalyticsFilterEcho;
  buckets: {
    source_bucket: string;
    impressions: number;
    clicks: number;
    detail_views: number;
    checkout_starts: number;
    purchases: number;
  }[];
};

export type AdminPlatformSummary = {
  range_start: string;
  range_end: string;
  total_users: number;
  total_hosts: number;
  total_events: number;
  tickets_sold: number;
  gross_revenue: string | number;
  platform_fees: string | number;
  refund_rate: string | number | null;
  refund_amount: string | number;
  payout_totals: string | number;
  vault_revenue: string | number;
  failed_payments: number;
  support_volume: number;
  fraud_signals: { code: string; label: string; severity: number }[];
  top_events: { event_id: string; title: string; tickets_sold: number; revenue: string }[];
  top_hosts: {
    host_id: string;
    display_name: string;
    username: string;
    revenue: string;
  }[];
  category_trends: { category: string; events: number }[];
  city_trends: { city: string; events: number }[];
  sales_over_time: SeriesPoint[];
};

export type AdminRevenueSummary = {
  gross_revenue: string | number;
  platform_fees: string | number;
  refund_amount: string | number;
  payout_totals: string | number;
  vault_revenue: string | number;
  net_after_refunds: string | number;
  sales_over_time: SeriesPoint[];
};

export type AdminEventsSummary = {
  total_events: number;
  by_status: { status: string; count: number }[];
  top_events: AdminPlatformSummary["top_events"];
  category_trends: AdminPlatformSummary["category_trends"];
  city_trends: AdminPlatformSummary["city_trends"];
};

export type AdminHostsSummary = {
  total_hosts: number;
  active_hosts: number;
  top_hosts: AdminPlatformSummary["top_hosts"];
};

export type AdminSupportSummary = {
  support_volume: number;
  open_refund_requests: number;
  escalated_refunds: number;
  note: string;
  fraud_signals: { code: string; label: string; severity: number }[];
};

export type AdminBlogAnalyticsSummary = {
  range_start: string;
  range_end: string;
  include_internal: boolean;
  totals: {
    index_views: number;
    card_impressions: number;
    card_clicks: number;
    post_views: number;
    unique_visitors: number;
    scroll_50: number;
    scroll_100: number;
    shares: number;
    related_clicks: number;
    cta_clicks: number;
    filter_uses: number;
    comments: number;
    publishes: number;
    bot_events: number;
    internal_admin_events: number;
  };
  funnel: {
    index_views: number;
    card_impressions: number;
    card_clicks: number;
    post_views: number;
    scroll_50: number;
    engaged: number;
    click_through_rate: number;
    view_from_click_rate: number;
    read_50_rate: number;
    share_rate: number;
    cta_rate: number;
  };
  top_posts: {
    post_id: string;
    title: string;
    slug: string | null;
    views: number;
    shares: number;
    cta_clicks: number;
    scroll_50: number;
    comments: number;
  }[];
  publishing: {
    posts_published: number;
    cadence: { date: string; published: number }[];
    avg_draft_age_hours: number | null;
    draft_age_samples: number;
  };
  ai_studio: {
    operations: number;
    successes: number;
    success_rate: number;
    by_operation: { operation: string; count: number }[];
  };
  timeseries: {
    date: string;
    post_views: number;
    shares: number;
    cta_clicks: number;
    card_clicks: number;
  }[];
};

export type AdminBlogPostAnalytics = {
  post: {
    id: string;
    title: string;
    slug: string;
    status: string;
    published_at: string | null;
    created_at: string | null;
  };
  range_start: string;
  range_end: string;
  include_internal: boolean;
  totals: {
    post_views: number;
    unique_visitors: number;
    scroll_milestones: Record<string, number>;
    shares: number;
    related_clicks: number;
    cta_clicks: number;
    comments: number;
    bot_events: number;
    internal_admin_events: number;
  };
  rates: {
    read_50_rate: number;
    read_100_rate: number;
    share_rate: number;
    cta_rate: number;
  };
  sources: { source: string; views: number }[];
  devices: { device: string; views: number }[];
  share_channels: { channel: string; count: number }[];
  cta_breakdown: { cta: string; count: number }[];
  publishing: { draft_age_hours: number | null; status: string };
  ai_studio: {
    operations: number;
    successes: number;
    recent: Record<string, unknown>[];
  };
  timeseries: AdminBlogAnalyticsSummary["timeseries"];
};
