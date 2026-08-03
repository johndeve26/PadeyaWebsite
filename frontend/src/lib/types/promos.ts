export type PromoCode = {
  id: string;
  host_id: string;
  code: string;
  discount_type: "percentage" | "fixed" | string;
  discount_value: string | number;
  usage_limit: number | null;
  usage_count: number;
  expires_at: string | null;
  event_id: string | null;
  ticket_type_id: string | null;
  status: string;
  max_per_user: number;
  created_at: string;
};

export type PromoValidateResult = {
  valid: boolean;
  code: string | null;
  discount_amount: string | number;
  subtotal_amount: string | number;
  total_amount: string | number;
  reason: string | null;
};

export type Ambassador = {
  id: string;
  host_id: string;
  event_id?: string | null;
  campaign_id?: string | null;
  user_id: string | null;
  program_kind?: "host_curated" | "open_event" | string;
  campaign_type?: string | null;
  campaign_type_label?: string | null;
  referral_code: string;
  referral_code_display?: string | null;
  display_name: string;
  email: string | null;
  status: string;
  commission_rate_percent: string | number;
  created_at: string;
  event_title?: string | null;
  event_slug?: string | null;
  clicks: number;
  total_clicks?: number;
  unique_clicks?: number;
  qualified_clicks?: number;
  tickets_sold: number;
  merch_units_sold?: number;
  revenue_generated: string | number;
  conversion_rate: string | number;
  commission_owed: string | number;
};

export type AmbassadorCampaignType = "event_tickets" | "event_merch" | string;

export type AmbassadorCommissionType =
  | "percentage"
  | "flat"
  | "reward_only"
  | string;

export type AmbassadorAppliesTo =
  | "tickets"
  | "merch"
  | "tickets_and_merch"
  | string;

export type OpenAmbassadorCampaignOption = {
  id: string;
  campaign_type: AmbassadorCampaignType;
  campaign_type_label: string;
  commission_percent: string | number;
  commission_type?: AmbassadorCommissionType;
  commission_value?: string | number;
  applies_to?: AmbassadorAppliesTo;
  merch_included: boolean;
  is_live: boolean;
};

export type OpenAmbassadorProgram = {
  event_id: string;
  enabled: boolean;
  commission_percent: string | number;
  commission_type?: AmbassadorCommissionType;
  commission_value?: string | number;
  event_slug: string | null;
  event_title: string | null;
  terms_version: string;
  campaign_id?: string | null;
  campaign_type?: AmbassadorCampaignType;
  merch_included?: boolean;
  campaigns?: OpenAmbassadorCampaignOption[];
};

/** Ambassador self view — no order_id / payment refs (phase 13). */
export type AmbassadorSale = {
  id: string;
  ambassador_id: string;
  tickets_sold: number;
  merch_units_sold?: number;
  revenue_amount: string | number;
  commission_owed: string | number;
  status: string;
  created_at: string;
  event_title: string | null;
};

/** Host ops view — may include order reference; still no buyer PII. */
export type HostAmbassadorSale = AmbassadorSale & {
  order_id: string | null;
  event_id: string;
  order_reference: string | null;
};

export type AmbassadorDashboard = {
  ambassador: Ambassador;
  sales: AmbassadorSale[];
  clicks: number;
  tickets_sold: number;
  merch_units_sold?: number;
  revenue_generated: string | number;
  conversion_rate: string | number;
  commission_owed: string | number;
};

export type HostAmbassadorDashboard = {
  ambassador: Ambassador;
  sales: HostAmbassadorSale[];
  clicks: number;
  tickets_sold: number;
  merch_units_sold?: number;
  revenue_generated: string | number;
  conversion_rate: string | number;
  commission_owed: string | number;
};

export type AmbassadorEnrollmentList = {
  enrollments: AmbassadorDashboard[];
};

export type EligibleAmbassadorEvent = {
  id: string;
  title: string;
  slug: string;
  city: string | null;
  start_datetime: string;
  banner_url: string | null;
  host_display_name: string | null;
  open_ambassador_commission_percent: string | number;
  open_ambassadors_enabled: boolean;
};

export type AmbassadorEarningsSummary = {
  clicks: number;
  total_clicks?: number;
  unique_clicks?: number;
  tickets_sold: number;
  merch_units_sold: number;
  confirmed_sales: number;
  revenue_generated: string | number;
  estimated_earnings: string | number;
  approved_earnings: string | number;
  payable_earnings: string | number;
  paid_earnings: string | number;
  payout_status: string;
  payout_status_label: string;
  enrollments_active: number;
};

export type AmbassadorCampaign = {
  id: string;
  host_id: string;
  event_id: string;
  name: string;
  status: "public_open" | "paused" | "ended" | string;
  source?: "host" | "platform" | string;
  created_by_user_id?: string | null;
  host_display_name?: string | null;
  campaign_type?: AmbassadorCampaignType;
  campaign_type_label?: string;
  commission_percent: string | number;
  commission_type?: AmbassadorCommissionType;
  commission_value?: string | number;
  applies_to?: AmbassadorAppliesTo;
  hold_period_days?: number;
  payout_minimum?: string | number | null;
  max_commission_per_order?: string | number | null;
  free_ticket_after_sales?: number | null;
  leaderboard_reward_enabled?: boolean;
  leaderboard_reward_description?: string | null;
  allow_host_owner_commission?: boolean;
  merch_included: boolean;
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
  updated_at: string;
  event_title: string | null;
  event_slug: string | null;
  is_live: boolean;
  active_ambassadors: number;
  total_ambassadors: number;
  clicks: number;
  confirmed_sales: number;
  tickets_sold: number;
  merch_units_sold: number;
  revenue_generated: string | number;
  conversion_rate: string | number;
  commission_owed: string | number;
  estimated_earnings: string | number;
  approved_earnings: string | number;
  payable_earnings: string | number;
  paid_earnings: string | number;
};

export type AmbassadorPlatformSettings = {
  enabled: boolean;
  updated_at: string | null;
  updated_by_user_id: string | null;
};

export type AdminAmbassadorRow = {
  id: string;
  /** Null for platform-wide (Pàdéyá-funded) enrollments. */
  host_id: string | null;
  event_id: string | null;
  campaign_id: string | null;
  user_id: string | null;
  program_id?: string | null;
  program_kind: string;
  referral_code: string;
  display_name: string;
  email: string | null;
  status: string;
  commission_rate_percent: string | number;
  created_at: string;
  event_title: string | null;
  ambassadors_blocked: boolean;
};

export type AmbassadorConversionAdmin = {
  id: string;
  ambassador_id: string;
  order_id: string;
  event_id: string;
  tickets_sold: number;
  merch_units_sold: number;
  revenue_amount: string | number;
  commission_owed: string | number;
  status: string;
  created_at: string;
  reversed_at: string | null;
  reversed_by_user_id: string | null;
  reversal_reason: string | null;
  reward_status_updated_at: string | null;
  event_title: string | null;
  ambassador_display_name: string | null;
  ambassador_referral_code: string | null;
  ambassador_user_id: string | null;
};

export type AmbassadorReportsSummary = {
  feature_enabled: boolean;
  campaigns_total: number;
  campaigns_live: number;
  campaigns_paused: number;
  campaigns_platform: number;
  ambassadors_total: number;
  ambassadors_active: number;
  clicks: number;
  total_clicks?: number;
  unique_clicks?: number;
  conversions_total: number;
  conversions_active: number;
  conversions_reversed: number;
  revenue_generated: string | number;
  commission_owed: string | number;
  estimated_earnings: string | number;
  approved_earnings: string | number;
  payable_earnings: string | number;
  paid_earnings: string | number;
};

export type CampaignLeaderboardRow = {
  ambassador_id: string;
  display_name: string;
  referral_code: string;
  status: string;
  clicks: number;
  confirmed_sales: number;
  tickets_sold: number;
  merch_units_sold: number;
  revenue_generated: string | number;
  conversion_rate: string | number;
  commission_owed: string | number;
};
