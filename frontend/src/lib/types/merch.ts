export type MerchVariant = {
  id: string;
  product_id: string;
  label: string;
  name?: string | null;
  sku?: string | null;
  size?: string | null;
  color?: string | null;
  option_1_name?: string | null;
  option_1_value?: string | null;
  option_2_name?: string | null;
  option_2_value?: string | null;
  price?: string | number | null;
  price_override?: string | number | null;
  effective_price: string | number;
  inventory_count: number;
  stock_quantity?: number;
  reserved_quantity?: number;
  sold_quantity?: number;
  available_quantity?: number;
  status: string;
  print_on_demand_variant_ref?: string | null;
  archived_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type MerchProduct = {
  id: string;
  event_id: string;
  host_id: string;
  name: string;
  slug: string;
  description?: string | null;
  short_description?: string | null;
  product_type?: string | null;
  base_price: string | number;
  currency: string;
  image_url?: string | null;
  cover_image_url?: string | null;
  gallery_urls?: string[];
  status: string;
  sales_start_at?: string | null;
  sales_end_at?: string | null;
  pickup_instructions?: string | null;
  pickup_location_label?: string | null;
  pickup_time_window?: string | null;
  fulfillment_notes?: string | null;
  show_on_event_page?: boolean;
  is_featured?: boolean;
  requires_ticket?: boolean;
  pickup_enabled?: boolean;
  shipping_enabled?: boolean;
  print_on_demand_enabled?: boolean;
  max_per_order?: number | null;
  max_per_buyer?: number | null;
  restock_on_refund: boolean;
  moderation_status?: string;
  moderation_note?: string | null;
  moderated_at?: string | null;
  archived_at?: string | null;
  created_at: string;
  updated_at: string;
  variants: MerchVariant[];
  variant_count?: number;
  total_inventory?: number;
  sold_count?: number;
  price_min?: string | number | null;
  price_max?: string | number | null;
  event_title?: string | null;
  size_chart_id?: string | null;
  is_sponsor_branded?: boolean;
  sponsor_id?: string | null;
  sponsor_brand_name?: string | null;
  sponsor_logo_url?: string | null;
  sponsor_description?: string | null;
  sponsor_split_type?: "percent" | "fixed" | string | null;
  sponsor_split_value?: string | number | null;
  is_vault_exclusive?: boolean;
  requires_vault_access?: boolean;
  required_vault_item_id?: string | null;
  required_access_type?: string | null;
  requires_check_in?: boolean;
  requires_vip?: boolean;
  is_event_linked?: boolean;
  is_post_event_drop?: boolean;
  storefront_visibility?: string | null;
  marketplace_kind?: string | null;
  category?: string | null;
  tags?: string[];
  post_event_drop_at?: string | null;
  audience?: string;
  drop_description?: string | null;
  is_drop_live?: boolean;
  drop_live_notified_at?: string | null;
};

export type PostEventDropAudience =
  | "public"
  | "ticket_buyers"
  | "checked_in"
  | "vip"
  | "vault_members";

export type PostEventDrop = MerchProduct & {
  audience: PostEventDropAudience | string;
  drop_description?: string | null;
  is_drop_live?: boolean;
};

export type MerchHostEventStats = {
  event_id: string;
  event_title: string;
  sales_status: string;
  currency: string;
  total_merch_revenue: string | number;
  items_sold: number;
  pending_pickup: number;
  picked_up: number;
  active_products: number;
  sold_out_variants: number;
  product_count: number;
};

export type MerchAdminProduct = MerchProduct & {
  host_name?: string | null;
  host_status?: string | null;
  event_status?: string | null;
  open_report_count?: number;
  report_count?: number;
};

export type MerchAdminOrder = {
  id: string;
  order_id: string;
  order_reference?: string | null;
  order_status?: string | null;
  event_id: string;
  event_title?: string | null;
  event_status?: string | null;
  host_id: string;
  host_name?: string | null;
  host_status?: string | null;
  buyer_name?: string | null;
  product_name: string;
  variant_label: string;
  quantity: number;
  status: string;
  pickup_code: string;
  fulfilled_at?: string | null;
  created_at: string;
  updated_at: string;
  is_issue: boolean;
};

export type MerchReportProductSnapshot = {
  id: string;
  name: string;
  status: string;
  moderation_status: string;
  product_type?: string | null;
  base_price: string;
  currency: string;
  image_url?: string | null;
  short_description?: string | null;
  moderation_note?: string | null;
};

export type MerchReport = {
  id: string;
  product_id: string;
  product_name?: string | null;
  product_status?: string | null;
  moderation_status?: string | null;
  product_snapshot?: MerchReportProductSnapshot | null;
  event_id?: string | null;
  event_title?: string | null;
  host_id?: string | null;
  host_name?: string | null;
  reporter_user_id: string;
  reporter_name?: string | null;
  reason: string;
  details?: string | null;
  status: string;
  admin_notes?: string | null;
  resolved_at?: string | null;
  resolved_by_user_id?: string | null;
  resolved_by_name?: string | null;
  resolution_note?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type MerchModerateAction =
  | "flag"
  | "clear"
  | "hide"
  | "remove"
  | "archive"
  | "restore";

export type MerchCatalogProduct = {
  id: string;
  event_id?: string | null;
  event_slug?: string | null;
  event_title?: string | null;
  name: string;
  slug: string;
  description?: string | null;
  short_description?: string | null;
  product_type?: string | null;
  base_price: string | number;
  currency: string;
  image_url?: string | null;
  cover_image_url?: string | null;
  gallery_urls?: string[];
  show_on_event_page?: boolean;
  is_featured?: boolean;
  requires_ticket?: boolean;
  pickup_location_label?: string | null;
  pickup_time_window?: string | null;
  pickup_instructions?: string | null;
  max_per_order?: number | null;
  max_per_buyer?: number | null;
  variants: MerchVariant[];
  is_sponsor_branded?: boolean;
  sponsor_brand_name?: string | null;
  sponsor_logo_url?: string | null;
  sponsor_description?: string | null;
  is_vault_exclusive?: boolean;
  requires_vault_access?: boolean;
  required_access_type?: string | null;
  required_vault_item_id?: string | null;
  is_event_linked?: boolean;
  is_merch_only?: boolean;
  is_post_event_drop?: boolean;
  is_drop_live?: boolean;
  post_event_drop_at?: string | null;
  sales_start_at?: string | null;
  sales_end_at?: string | null;
  storefront_visibility?: string | null;
  access_locked?: boolean;
  access_eligible?: boolean;
  access_reason?: string | null;
  access_label?: string | null;
  access_requirements?: string[];
  unlock_hint?: string | null;
  teaser_only?: boolean;
  availability?: string | null;
  event_is_private?: boolean;
  shipping_enabled?: boolean;
  pickup_enabled?: boolean;
  size_chart?: {
    id: string;
    name: string;
    units: string;
    chart_json: unknown;
    fit_notes?: string | null;
  } | null;
  average_rating?: number | null;
  review_count?: number;
};

export type MarketplaceKind =
  | "standalone"
  | "event_addon"
  | "event_merch"
  | "post_event_drop"
  | "vault_exclusive"
  | "bundle"
  | string;

/** Cross-host marketplace catalog row (extends public catalog product). */
export type MarketplaceProduct = MerchCatalogProduct & {
  host_id?: string | null;
  host_name?: string | null;
  host_slug?: string | null;
  host_username?: string | null;
  marketplace_kind?: MarketplaceKind | null;
  marketplace_listed?: boolean;
  category?: string | null;
  tags?: string[];
  badges?: string[];
  marketplace_path?: string | null;
  event_start_at?: string | null;
  event_location_label?: string | null;
  more_by_host?: MarketplaceProduct[];
  host_shop_path?: string | null;
  host_public_path?: string | null;
  indexable?: boolean;
  audience?: string | null;
  drop_description?: string | null;
};

export type MarketplaceCategory = {
  id?: string | null;
  slug: string;
  name: string;
  description?: string | null;
  sort_order?: number;
};

export type MarketplaceHostShop = {
  host_id: string;
  host_name: string;
  host_slug: string;
  host_username?: string | null;
  host_avatar_url?: string | null;
  merch_count: number;
  shop_badges?: string[];
  latest_products?: MarketplaceProduct[];
  shop_path?: string;
  storefront_path?: string;
};

export type MarketplaceHome = {
  featured: MarketplaceProduct[];
  event_merch: MarketplaceProduct[];
  host_shops: MarketplaceHostShop[];
  drops: MarketplaceProduct[];
  vault_exclusives: MarketplaceProduct[];
  categories: MarketplaceCategory[];
  empty: boolean;
};

export type MarketplaceListResult = {
  items: MarketplaceProduct[];
  total: number;
  limit: number;
  offset: number;
  sort?: string;
};

export type MarketplaceHostShopDetail = {
  host_id?: string;
  host_name?: string;
  host_slug?: string;
  host_username?: string;
  host?: {
    id?: string;
    slug?: string;
    username?: string;
    display_name?: string;
    name?: string;
  };
  products: MarketplaceProduct[];
  product_count?: number;
  shop_path?: string;
  storefront_path?: string;
  empty?: boolean;
  empty_message?: string;
  filters?: {
    events?: Array<{
      event_id?: string | null;
      event_slug?: string | null;
      event_title?: string | null;
    }>;
    product_types?: string[];
    availabilities?: string[];
  };
  storefront_title?: string | null;
  storefront_description?: string | null;
};

export type MerchBundleRule = {
  product_id?: string | null;
  variant_id: string;
  quantity: number;
  product_name?: string | null;
  variant_label?: string | null;
  unit_price?: string | number;
  is_vault_exclusive?: boolean;
  requires_vault_access?: boolean;
};

export type MerchBundle = {
  id: string;
  host_id: string;
  event_id: string;
  name: string;
  slug: string;
  description?: string | null;
  status: "draft" | "active" | "paused" | "archived" | string;
  bundle_price: string | number;
  currency: string;
  ticket_type_id: string;
  ticket_type_name?: string | null;
  ticket_type_price?: string | number | null;
  merch_variant_rules: MerchBundleRule[];
  component_list_total?: string | number;
  savings?: string | number;
  inventory_limit?: number | null;
  available_packs?: number | null;
  max_per_buyer?: number | null;
  sales_start_at?: string | null;
  sales_end_at?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type MerchDiscountCode = {
  id: string;
  host_id: string;
  event_id?: string | null;
  code: string;
  description?: string | null;
  discount_type: "percent" | "fixed_amount" | "free_shipping" | string;
  discount_value: string | number;
  value?: string | number;
  currency?: string | null;
  applies_to: string;
  product_ids?: string[];
  min_order_amount?: string | number | null;
  usage_limit?: number | null;
  per_buyer_limit?: number | null;
  usage_count: number;
  usage_count_paid?: number;
  status: "active" | "paused" | "expired" | "archived" | string;
  starts_at?: string | null;
  ends_at?: string | null;
  created_at: string;
  updated_at?: string;
  archived_at?: string | null;
};

export type MerchDiscountValidateResult = {
  valid: boolean;
  code: string | null;
  discount_amount: string | number;
  shipping_amount: string | number;
  discount_type?: string;
  reason: string | null;
};

export type MerchFulfillment = {
  id: string;
  order_id: string;
  order_item_id: string;
  event_id?: string | null;
  host_id: string;
  buyer_user_id: string;
  merch_variant_id: string;
  quantity: number;
  status: string;
  fulfillment_method?: string | null;
  display_status?: string | null;
  pickup_code: string;
  pickup_instructions_snapshot?: string | null;
  pickup_location_label?: string | null;
  pickup_time_window?: string | null;
  fulfillment_notes?: string | null;
  product_name_snapshot: string;
  variant_label_snapshot: string;
  product_image_url?: string | null;
  qr_token?: string | null;
  qr_typ?: string | null;
  tracking_number?: string | null;
  carrier?: string | null;
  shipped_at?: string | null;
  delivered_at?: string | null;
  /** Buyer: city/state/country only. Host with fulfill: decrypted ship-to. */
  shipping_address?: {
    recipient_name?: string | null;
    phone?: string | null;
    line1?: string | null;
    line2?: string | null;
    notes?: string | null;
    city?: string | null;
    state?: string | null;
    country?: string | null;
    postal_code?: string | null;
  } | null;
  fulfilled_at?: string | null;
  fulfilled_by_user_id?: string | null;
  fulfilled_by_name?: string | null;
  created_at: string;
  updated_at?: string | null;
  event_title?: string | null;
  event_slug?: string | null;
  host_name?: string | null;
  host_slug?: string | null;
  buyer_email?: string | null;
  buyer_name?: string | null;
  order_reference?: string | null;
  order_status?: string | null;
  has_ticket?: boolean | null;
  ticket_count?: number | null;
};

export type MerchRevenueMoneyBucket = {
  gross?: string | number;
  host_amount?: string | number;
  platform_amount?: string | number;
  sponsor_amount?: string | number;
  print_partner_amount?: string | number;
  units?: number;
  line_count?: number;
};

export type MerchRevenueRefunds = {
  gross?: string | number;
  host_amount?: string | number;
  platform_amount?: string | number;
  units?: number;
  line_count?: number;
};

export type MerchRevenuePayoutStatus = {
  payable?: { amount?: string | number; line_count?: number };
  paid?: { amount?: string | number; line_count?: number };
  pending_payout_amount?: string | number;
  pending_payout_line_count?: number;
};

export type MerchHostRevenueReport = {
  host_id?: string;
  event_id?: string | null;
  currency?: string;
  total_gross?: string | number;
  total_merch_gmv?: string | number;
  host_amount?: string | number;
  net_revenue?: string | number;
  platform_amount?: string | number;
  sponsor_amount?: string | number;
  print_partner_amount?: string | number;
  units_sold?: number;
  line_count?: number;
  refunds?: MerchRevenueRefunds;
  refunds_gross?: string | number;
  discount_impact?: string | number;
  bundle_revenue?: string | number;
  sponsor_branded_revenue?: string | number;
  sponsor_branded_line_count?: number;
  payout_status?: MerchRevenuePayoutStatus;
  top_products?: Array<
    MerchRevenueMoneyBucket & {
      product_id?: string | null;
      product_name?: string | null;
      is_sponsor_branded?: boolean;
      sponsor_brand_name?: string | null;
    }
  >;
  by_product?: Array<
    MerchRevenueMoneyBucket & {
      product_id?: string | null;
      product_name?: string | null;
      is_sponsor_branded?: boolean;
      sponsor_brand_name?: string | null;
    }
  >;
  by_event?: Array<
    MerchRevenueMoneyBucket & {
      event_id?: string | null;
      event_title?: string | null;
    }
  >;
  by_variant?: Array<
    MerchRevenueMoneyBucket & {
      variant_id?: string | null;
      variant_label?: string | null;
      product_id?: string | null;
      product_name?: string | null;
    }
  >;
  by_fulfillment_method?: Array<
    MerchRevenueMoneyBucket & { fulfillment_method?: string | null }
  >;
  by_bundle?: Array<
    MerchRevenueMoneyBucket & {
      bundle_id?: string | null;
      bundle_name?: string | null;
    }
  >;
  sponsor_branded_lines?: Array<{
    product_id?: string | null;
    product_name?: string | null;
    sponsor_brand_name?: string | null;
    gross?: string | number;
    sponsor_amount?: string | number;
    host_amount?: string | number;
  }>;
};

export type MerchAdminRevenueReport = {
  currency?: string;
  total_gross?: string | number;
  platform_merch_gmv?: string | number;
  platform_amount?: string | number;
  platform_fees?: string | number;
  host_amount?: string | number;
  host_revenue?: string | number;
  sponsor_amount?: string | number;
  sponsor_split?: string | number;
  print_partner_amount?: string | number;
  print_partner_split?: string | number;
  units_sold?: number;
  line_count?: number;
  refunds?: MerchRevenueRefunds;
  refunds_gross?: string | number;
  discount_impact?: string | number;
  sponsor_branded_line_count?: number;
  sponsor_branded_gross?: string | number;
  pending_payouts?: { amount?: string | number; line_count?: number };
  payout_status?: MerchRevenuePayoutStatus;
  top_hosts?: Array<
    MerchRevenueMoneyBucket & {
      host_id?: string;
      host_name?: string | null;
    }
  >;
  top_products?: Array<
    MerchRevenueMoneyBucket & {
      product_id?: string | null;
      product_name?: string | null;
      host_id?: string;
      is_sponsor_branded?: boolean;
    }
  >;
  top_events?: Array<
    MerchRevenueMoneyBucket & {
      event_id?: string | null;
      event_title?: string | null;
      host_id?: string;
    }
  >;
};
