import { apiRequest } from "@/lib/api";
import { getApiBaseUrl, getApiPrefix } from "@/lib/api-base";
import { getAccessToken } from "@/lib/auth/storage";
import type { MerchSizeChart } from "@/lib/merch-size-chart";
import type {
  MarketplaceHome,
  MarketplaceHostShop,
  MarketplaceHostShopDetail,
  MarketplaceListResult,
  MarketplaceProduct,
  MerchAdminOrder,
  MerchAdminProduct,
  MerchAdminRevenueReport,
  MerchBundle,
  MerchCatalogProduct,
  MerchDiscountCode,
  MerchDiscountValidateResult,
  MerchFulfillment,
  MerchHostEventStats,
  MerchHostRevenueReport,
  MerchModerateAction,
  MerchProduct,
  MerchReport,
  MerchVariant,
} from "@/lib/types/merch";

const API_URL = getApiBaseUrl();
const API_PREFIX = getApiPrefix();

async function downloadMerchCsv(path: string, filename: string): Promise<void> {
  const token = getAccessToken();
  const res = await fetch(`${API_URL}${API_PREFIX}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    throw new Error("Export failed");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export type MerchBundleWriteBody = {
  name: string;
  description?: string | null;
  bundle_price: number | string;
  currency?: string;
  ticket_type_id: string;
  merch_variant_rules: Array<{
    product_id?: string;
    variant_id: string;
    quantity: number;
  }>;
  inventory_limit?: number | null;
  max_per_buyer?: number | null;
  sales_start_at?: string | null;
  sales_end_at?: string | null;
  status?: string;
};

export type MerchProductWriteBody = {
  name: string;
  description?: string | null;
  short_description?: string | null;
  product_type?: string | null;
  base_price: number;
  currency?: string;
  image_url?: string | null;
  cover_image_url?: string | null;
  gallery_urls?: string[];
  status?: string;
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
  restock_on_refund?: boolean;
  size_chart_id?: string | null;
  is_sponsor_branded?: boolean;
  sponsor_brand_name?: string | null;
  sponsor_logo_url?: string | null;
  sponsor_description?: string | null;
  sponsor_split_type?: string | null;
  sponsor_split_value?: number | null;
  is_vault_exclusive?: boolean;
  requires_vault_access?: boolean;
  required_access_type?: string | null;
  required_vault_item_id?: string | null;
  requires_check_in?: boolean;
  storefront_visibility?: string | null;
  marketplace_kind?: string | null;
  category?: string | null;
  tags?: string[];
  marketplace_listed?: boolean;
  variants?: MerchVariantWriteBody[];
};

export type MerchVariantWriteBody = {
  label: string;
  name?: string | null;
  size?: string | null;
  color?: string | null;
  option_1_name?: string | null;
  option_1_value?: string | null;
  option_2_name?: string | null;
  option_2_value?: string | null;
  sku?: string | null;
  price?: number | null;
  price_override?: number | null;
  inventory_count: number;
  stock_quantity?: number | null;
  status?: string;
  print_on_demand_variant_ref?: string | null;
};

export async function fetchMerchCatalog(
  eventId: string,
  opts?: { authenticated?: boolean },
): Promise<MerchCatalogProduct[]> {
  return apiRequest<MerchCatalogProduct[]>(
    `/merch/events/${eventId}/catalog`,
    { auth: Boolean(opts?.authenticated) },
  );
}

/** Public catalog by event slug (alias of merch catalog). */
export async function fetchMerchCatalogBySlug(
  eventSlug: string,
): Promise<MerchCatalogProduct[]> {
  return apiRequest<MerchCatalogProduct[]>(
    `/events/${encodeURIComponent(eventSlug)}/merchandise`,
    { auth: false },
  );
}

export async function fetchHostMerchProducts(
  eventId: string,
): Promise<MerchProduct[]> {
  return apiRequest<MerchProduct[]>(
    `/host/events/${eventId}/merchandise`,
  );
}

export async function fetchAllHostMerchProducts(): Promise<MerchProduct[]> {
  return apiRequest<MerchProduct[]>("/merch/host/products");
}

export async function fetchHostMerchProduct(
  productId: string,
  eventId?: string,
): Promise<MerchProduct> {
  if (eventId) {
    return apiRequest<MerchProduct>(
      `/host/events/${eventId}/merchandise/${productId}`,
    );
  }
  return apiRequest<MerchProduct>(`/merch/products/${productId}`);
}

export async function createMerchProduct(
  eventId: string,
  body: MerchProductWriteBody,
): Promise<MerchProduct> {
  return apiRequest<MerchProduct>(`/host/events/${eventId}/merchandise`, {
    method: "POST",
    body,
  });
}

export async function updateMerchProduct(
  productId: string,
  body: Partial<MerchProductWriteBody>,
  eventId?: string,
): Promise<MerchProduct> {
  if (eventId) {
    return apiRequest<MerchProduct>(
      `/host/events/${eventId}/merchandise/${productId}`,
      { method: "PATCH", body },
    );
  }
  return apiRequest<MerchProduct>(`/merch/products/${productId}`, {
    method: "PATCH",
    body,
  });
}

export async function archiveMerchProduct(
  productId: string,
  eventId?: string,
): Promise<MerchProduct> {
  if (eventId) {
    return apiRequest<MerchProduct>(
      `/host/events/${eventId}/merchandise/${productId}/archive`,
      { method: "PATCH" },
    );
  }
  return apiRequest<MerchProduct>(`/merch/products/${productId}/archive`, {
    method: "POST",
  });
}

export async function duplicateMerchProduct(
  productId: string,
): Promise<MerchProduct> {
  return apiRequest<MerchProduct>(`/merch/products/${productId}/duplicate`, {
    method: "POST",
  });
}

export async function fetchHostMerchStats(
  eventId: string,
): Promise<MerchHostEventStats> {
  return apiRequest<MerchHostEventStats>(`/merch/host/events/${eventId}/stats`);
}

export async function createMerchVariant(
  productId: string,
  body: MerchVariantWriteBody,
): Promise<MerchVariant> {
  return apiRequest<MerchVariant>(`/merch/products/${productId}/variants`, {
    method: "POST",
    body,
  });
}

export async function updateMerchVariant(
  variantId: string,
  body: Partial<MerchVariantWriteBody>,
): Promise<MerchVariant> {
  return apiRequest<MerchVariant>(`/merch/variants/${variantId}`, {
    method: "PATCH",
    body,
  });
}

export async function fetchHostMerchFulfillments(
  eventId: string,
  params?: { status?: string; q?: string },
): Promise<MerchFulfillment[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.q) qs.set("q", params.q);
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<MerchFulfillment[]>(
    `/host/events/${eventId}/merchandise/orders${suffix}`,
  );
}

export async function addMerchFulfillmentNote(
  fulfillmentId: string,
  note: string,
): Promise<MerchFulfillment> {
  return apiRequest<MerchFulfillment>(
    `/merch/fulfillments/${fulfillmentId}/notes`,
    { method: "POST", body: { note } },
  );
}

export async function fulfillMerch(
  fulfillmentId: string,
): Promise<MerchFulfillment> {
  return apiRequest<MerchFulfillment>(
    `/host/merchandise/order-items/${fulfillmentId}/picked-up`,
    { method: "PATCH" },
  );
}

export async function updateMerchFulfillmentStatus(
  fulfillmentId: string,
  status: "awaiting_pickup" | "collect_at_stand" | "fulfilled",
): Promise<MerchFulfillment> {
  if (status === "collect_at_stand") {
    return apiRequest<MerchFulfillment>(
      `/host/merchandise/order-items/${fulfillmentId}/ready`,
      { method: "PATCH" },
    );
  }
  if (status === "fulfilled") {
    return fulfillMerch(fulfillmentId);
  }
  return apiRequest<MerchFulfillment>(`/merch/fulfillments/${fulfillmentId}`, {
    method: "PATCH",
    body: { status },
  });
}

/** Pause a product via host merchandise alias (when eventId is known). */
export async function pauseMerchProduct(
  productId: string,
  eventId: string,
): Promise<MerchProduct> {
  return apiRequest<MerchProduct>(
    `/host/events/${eventId}/merchandise/${productId}/pause`,
    { method: "PATCH" },
  );
}

export async function fetchMyMerch(): Promise<MerchFulfillment[]> {
  return apiRequest<MerchFulfillment[]>("/dashboard/merchandise");
}

export async function fetchMyMerchItem(
  itemId: string,
): Promise<MerchFulfillment> {
  return apiRequest<MerchFulfillment>(
    `/dashboard/merchandise/${encodeURIComponent(itemId)}`,
  );
}

export async function reportMerchProduct(
  productId: string,
  payload: { reason: string; details?: string | null },
): Promise<MerchReport> {
  return apiRequest<MerchReport>(`/merch/products/${productId}/report`, {
    method: "POST",
    body: {
      reason: payload.reason,
      details: payload.details ?? null,
    },
  });
}

export async function fetchAdminMerchProducts(params?: {
  moderation_status?: string;
  status?: string;
  q?: string;
  is_sponsor_branded?: boolean;
  limit?: number;
}): Promise<MerchAdminProduct[]> {
  const qs = new URLSearchParams();
  if (params?.moderation_status) qs.set("moderation_status", params.moderation_status);
  if (params?.status) qs.set("status", params.status);
  if (params?.q) qs.set("q", params.q);
  if (params?.is_sponsor_branded != null) {
    qs.set("is_sponsor_branded", String(params.is_sponsor_branded));
  }
  if (params?.limit) qs.set("limit", String(params.limit));
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<MerchAdminProduct[]>(`/admin/merchandise${suffix}`);
}

export async function fetchAdminMerchProduct(
  productId: string,
): Promise<MerchAdminProduct> {
  return apiRequest<MerchAdminProduct>(`/merch/admin/products/${productId}`);
}

export async function moderateMerchProduct(
  productId: string,
  action: MerchModerateAction,
  note?: string,
): Promise<MerchAdminProduct> {
  // Prefer REST aliases for hide/restore when no custom note is required.
  if (action === "hide" && !note) {
    return apiRequest<MerchAdminProduct>(
      `/admin/merchandise/${productId}/hide`,
      { method: "PATCH" },
    );
  }
  if (action === "restore" && !note) {
    return apiRequest<MerchAdminProduct>(
      `/admin/merchandise/${productId}/restore`,
      { method: "PATCH" },
    );
  }
  return apiRequest<MerchAdminProduct>(
    `/merch/admin/products/${productId}/moderate`,
    { method: "POST", body: { action, note } },
  );
}

export async function deactivateUnsafeMerchProduct(
  productId: string,
  note?: string,
): Promise<MerchAdminProduct> {
  return apiRequest<MerchAdminProduct>(
    `/merch/admin/products/${productId}/deactivate-unsafe`,
    { method: "POST", body: { note } },
  );
}

export async function fetchAdminMerchOrders(params?: {
  status?: string;
  issues?: boolean;
  q?: string;
  limit?: number;
}): Promise<MerchAdminOrder[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.issues) qs.set("issues", "true");
  if (params?.q) qs.set("q", params.q);
  if (params?.limit) qs.set("limit", String(params.limit));
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<MerchAdminOrder[]>(`/merch/admin/orders${suffix}`);
}

export async function fetchAdminMerchReports(params?: {
  status?: string;
  limit?: number;
}): Promise<MerchReport[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.limit) qs.set("limit", String(params.limit));
  const suffix = qs.toString() ? `?${qs}` : "";
  return apiRequest<MerchReport[]>(`/merch/admin/reports${suffix}`);
}

export async function updateMerchReport(
  reportId: string,
  body: {
    status?: "open" | "reviewing";
    admin_notes?: string | null;
  },
): Promise<MerchReport> {
  return apiRequest<MerchReport>(`/merch/admin/reports/${reportId}`, {
    method: "PATCH",
    body,
  });
}

export async function resolveMerchReport(
  reportId: string,
  body: {
    resolution: "resolved" | "dismissed";
    note?: string;
    admin_notes?: string | null;
    moderate_action?: MerchModerateAction;
  },
): Promise<MerchReport> {
  return apiRequest<MerchReport>(`/merch/admin/reports/${reportId}/resolve`, {
    method: "POST",
    body,
  });
}

/* --- Advanced commerce --- */

export type HostStorefrontSettings = {
  enabled: boolean;
  title: string | null;
  description: string | null;
  visibility: "public" | "unlisted" | "hidden";
  public_path: string;
  legacy_path: string;
};

export type HostMerchStorefront = {
  host_id: string;
  host_name: string;
  host_slug: string;
  host_avatar_url?: string | null;
  legacy_path?: string;
  legacy_url?: string;
  storefront_enabled?: boolean;
  storefront_title?: string;
  storefront_description?: string;
  storefront_visibility?: "public" | "unlisted" | "hidden";
  is_listed?: boolean;
  is_preview?: boolean;
  products: MerchCatalogProduct[];
  product_count: number;
  filters?: {
    events: Array<{
      event_id?: string | null;
      event_slug?: string | null;
      event_title?: string | null;
    }>;
    product_types: string[];
    availabilities: string[];
  };
};

export type HostMerchStorefrontQuery = {
  event?: string;
  product_type?: string;
  availability?: string;
  kind?: string;
};

export async function fetchHostMerchStorefront(
  username: string,
  query: HostMerchStorefrontQuery = {},
): Promise<HostMerchStorefront> {
  const params = new URLSearchParams();
  if (query.event) params.set("event", query.event);
  if (query.product_type) params.set("product_type", query.product_type);
  if (query.availability) params.set("availability", query.availability);
  if (query.kind) params.set("kind", query.kind);
  const suffix = params.size ? `?${params.toString()}` : "";
  // Send token when present so host owners can preview hidden shops.
  return apiRequest<HostMerchStorefront>(
    `/u/${encodeURIComponent(username)}/merch${suffix}`,
  );
}

export type PostEventDropWriteBody = {
  name: string;
  base_price: number;
  audience?: string;
  drop_description?: string | null;
  post_event_drop_at?: string | null;
  currency?: string;
  product_type?: string | null;
  image_url?: string | null;
  status?: string;
  inventory_count?: number;
  variant_label?: string;
};

export type PostEventDropPatchBody = {
  name?: string;
  drop_description?: string | null;
  audience?: string;
  post_event_drop_at?: string | null;
  status?: string;
  base_price?: number;
  image_url?: string | null;
};

export async function fetchHostPostEventDrops(
  eventId: string,
): Promise<import("@/lib/types/merch").PostEventDrop[]> {
  return apiRequest(`/host/events/${eventId}/post-event-drops`);
}

export async function createHostPostEventDrop(
  eventId: string,
  body: PostEventDropWriteBody,
): Promise<import("@/lib/types/merch").PostEventDrop> {
  return apiRequest(`/host/events/${eventId}/post-event-drops`, {
    method: "POST",
    body,
  });
}

export async function patchHostPostEventDrop(
  eventId: string,
  productId: string,
  body: PostEventDropPatchBody,
): Promise<import("@/lib/types/merch").PostEventDrop> {
  return apiRequest(`/host/events/${eventId}/post-event-drops/${productId}`, {
    method: "PATCH",
    body,
  });
}

export async function fetchMyEligiblePostEventDrops(): Promise<
  MerchCatalogProduct[]
> {
  return apiRequest<MerchCatalogProduct[]>("/merch/me/post-event-drops");
}

export async function fetchHostMerchStorefrontProduct(
  username: string,
  productId: string,
): Promise<MerchCatalogProduct> {
  return apiRequest<MerchCatalogProduct>(
    `/u/${encodeURIComponent(username)}/merch/${productId}`,
  );
}

export async function fetchHostStorefrontSettings(): Promise<HostStorefrontSettings> {
  return apiRequest<HostStorefrontSettings>("/host/merchandise/storefront");
}

export async function updateHostStorefrontSettings(body: {
  enabled?: boolean;
  title?: string | null;
  description?: string | null;
  visibility?: "public" | "unlisted" | "hidden";
}): Promise<HostStorefrontSettings> {
  return apiRequest<HostStorefrontSettings>("/host/merchandise/storefront", {
    method: "PATCH",
    body,
  });
}

export async function fetchEventBundles(eventId: string): Promise<MerchBundle[]> {
  return apiRequest<MerchBundle[]>(`/events/${eventId}/bundles`, { auth: false });
}

export async function fetchHostEventBundles(
  eventId: string,
): Promise<MerchBundle[]> {
  return apiRequest<MerchBundle[]>(`/host/events/${eventId}/bundles`);
}

export async function createHostEventBundle(
  eventId: string,
  body: MerchBundleWriteBody,
): Promise<MerchBundle> {
  return apiRequest<MerchBundle>(`/host/events/${eventId}/bundles`, {
    method: "POST",
    body,
  });
}

export async function updateHostEventBundle(
  eventId: string,
  bundleId: string,
  body: Partial<MerchBundleWriteBody>,
): Promise<MerchBundle> {
  return apiRequest<MerchBundle>(
    `/host/events/${eventId}/bundles/${bundleId}`,
    { method: "PATCH", body },
  );
}

export async function archiveHostEventBundle(
  eventId: string,
  bundleId: string,
): Promise<MerchBundle> {
  return apiRequest<MerchBundle>(
    `/host/events/${eventId}/bundles/${bundleId}/archive`,
    { method: "POST" },
  );
}

export type MerchReviewPublic = {
  id: string;
  product_id: string;
  rating: number;
  body?: string | null;
  status: string;
  author_display_name: string;
  verified_purchase: boolean;
  event_title?: string | null;
  event_slug?: string | null;
  host_reply?: string | null;
  host_replied_at?: string | null;
  product_name?: string | null;
  admin_note?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export async function fetchProductReviews(productId: string) {
  return apiRequest<{
    average_rating: number | null;
    review_count: number;
    reviews: MerchReviewPublic[];
  }>(`/merch/products/${productId}/reviews`, { auth: false });
}

export async function createMerchReview(
  orderItemId: string,
  body: { rating: number; body?: string },
) {
  return apiRequest<MerchReviewPublic>(`/dashboard/merchandise/reviews`, {
    method: "POST",
    body: { order_item_id: orderItemId, rating: body.rating, body: body.body },
  });
}

export async function fetchMyMerchReviewForOrderItem(orderItemId: string) {
  return apiRequest<MerchReviewPublic | null>(
    `/dashboard/merchandise/reviews/by-order-item/${orderItemId}`,
  );
}

export async function updateMerchReview(
  reviewId: string,
  body: { rating?: number; body?: string | null },
) {
  return apiRequest<MerchReviewPublic>(
    `/dashboard/merchandise/reviews/${reviewId}`,
    { method: "PATCH", body },
  );
}

export async function removeMerchReview(reviewId: string) {
  return apiRequest<{ id: string; status: string }>(
    `/dashboard/merchandise/reviews/${reviewId}`,
    { method: "DELETE" },
  );
}

export async function fetchHostMerchReviews() {
  return apiRequest<MerchReviewPublic[]>("/host/merchandise/reviews");
}

export async function replyToMerchReview(reviewId: string, reply: string) {
  return apiRequest<MerchReviewPublic>(
    `/host/merchandise/reviews/${reviewId}/reply`,
    { method: "POST", body: { reply } },
  );
}

export async function fetchAdminMerchReviews(query?: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  const params = new URLSearchParams();
  if (query?.status) params.set("status", query.status);
  if (query?.limit != null) params.set("limit", String(query.limit));
  if (query?.offset != null) params.set("offset", String(query.offset));
  const suffix = params.size ? `?${params.toString()}` : "";
  return apiRequest<MerchReviewPublic[]>(
    `/admin/merchandise/reviews${suffix}`,
  );
}

export async function moderateMerchReview(
  reviewId: string,
  body: { action: "hide" | "restore"; note?: string | null },
) {
  return apiRequest<MerchReviewPublic>(
    `/admin/merchandise/reviews/${reviewId}/moderate`,
    { method: "POST", body },
  );
}

export type BuyerCart = {
  id: string | null;
  status: string;
  event_id?: string | null;
  event_slug?: string | null;
  host_id?: string | null;
  host_slug?: string | null;
  resume_path?: string | null;
  items: Array<{
    id: string;
    product_id: string;
    variant_id: string;
    quantity: number;
    unit_price_snapshot: string | number;
    product_name_snapshot: string;
    variant_label_snapshot: string;
  }>;
};

export async function fetchBuyerCart() {
  return apiRequest<BuyerCart>("/dashboard/cart");
}

export async function addBuyerCartItem(variantId: string, quantity: number) {
  return apiRequest<BuyerCart>("/dashboard/cart/items", {
    method: "POST",
    body: { variant_id: variantId, quantity },
  });
}

export async function updateBuyerCartItemQuantity(itemId: string, quantity: number) {
  return apiRequest<BuyerCart>(`/dashboard/cart/items/${itemId}`, {
    method: "PATCH",
    body: { quantity },
  });
}

export async function removeBuyerCartItem(itemId: string) {
  return apiRequest<BuyerCart>(`/dashboard/cart/items/${itemId}`, {
    method: "DELETE",
  });
}

export async function scanMerchPickup(
  eventId: string,
  payload: { token?: string; pickup_code?: string },
): Promise<MerchFulfillment> {
  return apiRequest<MerchFulfillment>(
    `/host/events/${eventId}/merchandise/scan-qr`,
    { method: "POST", body: payload },
  );
}

export async function fetchHostMerchRevenue(eventId?: string) {
  const qs = eventId ? `?event_id=${eventId}` : "";
  return apiRequest<MerchHostRevenueReport>(
    `/host/merchandise/revenue${qs}`,
  );
}

export async function exportHostMerchRevenueCsv(): Promise<void> {
  await downloadMerchCsv(
    "/host/merchandise/revenue/export.csv",
    "host-merch-revenue.csv",
  );
}

export async function fetchAdminMerchRevenue() {
  return apiRequest<MerchAdminRevenueReport>(`/admin/merchandise/revenue`);
}

export async function exportAdminMerchRevenueCsv(): Promise<void> {
  await downloadMerchCsv(
    "/admin/merchandise/revenue/export.csv",
    "admin-merch-revenue.csv",
  );
}

export type HostStockAlert = {
  id: string;
  host_id: string;
  event_id?: string | null;
  product_id: string;
  variant_id?: string | null;
  alert_type: string;
  threshold?: number | null;
  available_snapshot?: number | null;
  current_available?: number | null;
  status: string;
  triggered_at?: string | null;
  resolved_at?: string | null;
  product_name?: string | null;
  variant_label?: string | null;
};

export async function fetchHostStockAlerts() {
  return apiRequest<HostStockAlert[]>("/host/merchandise/stock-alerts");
}

export async function fetchHostMerchDiscounts() {
  return apiRequest<MerchDiscountCode[]>("/host/merchandise/discounts");
}

export async function createHostMerchDiscount(body: {
  code: string;
  description?: string | null;
  discount_type: string;
  discount_value: number;
  currency?: string | null;
  applies_to?: string;
  event_id?: string | null;
  product_ids?: string[] | null;
  min_order_amount?: number | null;
  usage_limit?: number | null;
  per_buyer_limit?: number | null;
  starts_at?: string | null;
  ends_at?: string | null;
  status?: string;
}) {
  return apiRequest<MerchDiscountCode>("/host/merchandise/discounts", {
    method: "POST",
    body,
  });
}

export async function updateHostMerchDiscount(
  discountId: string,
  body: {
    description?: string | null;
    discount_type?: string;
    discount_value?: number;
    currency?: string | null;
    applies_to?: string;
    event_id?: string | null;
    product_ids?: string[] | null;
    min_order_amount?: number | null;
    usage_limit?: number | null;
    per_buyer_limit?: number | null;
    starts_at?: string | null;
    ends_at?: string | null;
    status?: string;
  },
) {
  return apiRequest<MerchDiscountCode>(
    `/host/merchandise/discounts/${discountId}`,
    { method: "PATCH", body },
  );
}

export async function archiveHostMerchDiscount(discountId: string) {
  return apiRequest<MerchDiscountCode>(
    `/host/merchandise/discounts/${discountId}/archive`,
    { method: "POST" },
  );
}

export async function validateMerchDiscount(body: {
  code: string;
  event_id: string;
  items: Array<{
    merch_variant_id?: string;
    ticket_type_id?: string;
    quantity: number;
    from_bundle?: boolean;
  }>;
  shipping_amount?: number;
}) {
  return apiRequest<MerchDiscountValidateResult>("/merch/discounts/validate", {
    method: "POST",
    body,
  });
}

export async function shipMerchFulfillment(
  fulfillmentId: string,
  body?: { tracking_number?: string; carrier?: string },
): Promise<{
  id: string;
  status: string;
  tracking_number?: string | null;
  carrier?: string | null;
  shipped_at?: string | null;
}> {
  return apiRequest(
    `/host/merchandise/order-items/${fulfillmentId}/ship`,
    { method: "POST", body: body ?? {} },
  );
}

export async function deliverMerchFulfillment(
  fulfillmentId: string,
): Promise<{ id: string; status: string; delivered_at?: string | null }> {
  return apiRequest(
    `/host/merchandise/order-items/${fulfillmentId}/deliver`,
    { method: "POST" },
  );
}

export type MerchShippingZone = {
  id: string;
  name: string;
  country: string;
  state?: string | null;
  city?: string | null;
  flat_fee: string | number;
  currency?: string;
  event_id?: string | null;
  status: string;
  created_at?: string;
  updated_at?: string;
};

export async function fetchHostShippingZones() {
  return apiRequest<MerchShippingZone[]>("/host/merchandise/shipping-zones");
}

export async function createHostShippingZone(body: {
  name: string;
  country: string;
  state?: string | null;
  city?: string | null;
  flat_fee: number;
  event_id?: string | null;
}) {
  return apiRequest<MerchShippingZone>("/host/merchandise/shipping-zones", {
    method: "POST",
    body,
  });
}

export async function updateHostShippingZone(
  zoneId: string,
  body: {
    name?: string;
    country?: string;
    state?: string | null;
    city?: string | null;
    flat_fee?: number;
    event_id?: string | null;
    clear_event_id?: boolean;
    status?: string;
  },
) {
  return apiRequest<MerchShippingZone>(
    `/host/merchandise/shipping-zones/${zoneId}`,
    { method: "PATCH", body },
  );
}

export async function archiveHostShippingZone(zoneId: string) {
  return apiRequest<MerchShippingZone>(
    `/host/merchandise/shipping-zones/${zoneId}/archive`,
    { method: "POST" },
  );
}

export async function fetchHostSizeCharts() {
  return apiRequest<MerchSizeChart[]>("/host/merchandise/size-charts");
}

export async function createHostSizeChart(body: {
  name: string;
  product_type?: string | null;
  units?: string;
  chart_json: unknown;
  fit_notes?: string | null;
}) {
  return apiRequest<MerchSizeChart>("/host/merchandise/size-charts", {
    method: "POST",
    body,
  });
}

export async function updateHostSizeChart(
  chartId: string,
  body: {
    name?: string;
    product_type?: string | null;
    units?: string;
    chart_json?: unknown;
    fit_notes?: string | null;
    status?: string;
  },
) {
  return apiRequest<MerchSizeChart>(
    `/host/merchandise/size-charts/${chartId}`,
    { method: "PATCH", body },
  );
}

export async function archiveHostSizeChart(chartId: string) {
  return apiRequest<MerchSizeChart>(
    `/host/merchandise/size-charts/${chartId}/archive`,
    { method: "POST" },
  );
}

export type MerchPodIntegration = {
  id: string;
  host_id: string;
  provider: string;
  status: string;
  provider_store_ref?: string | null;
  sync_note?: string | null;
  sync_status?: string;
  has_credentials: boolean;
  created_at: string;
  updated_at: string;
};

export type MerchPodJob = {
  id: string;
  host_id?: string;
  order_id: string;
  order_item_id: string;
  merch_fulfillment_id?: string | null;
  provider: string;
  status: string;
  status_label?: string;
  manual_required: boolean;
  error_note?: string | null;
  provider_ref?: string | null;
  fulfilled_at?: string | null;
  created_at: string;
  updated_at?: string;
};

export async function fetchHostPodJobs() {
  return apiRequest<MerchPodJob[]>("/host/merchandise/print-on-demand");
}

export async function fetchHostPodIntegrations() {
  return apiRequest<MerchPodIntegration[]>(
    "/host/merchandise/print-on-demand/integrations",
  );
}

export async function upsertHostPodIntegration(body: {
  provider: string;
  status: string;
  provider_store_ref?: string | null;
  credentials?: string | null;
}) {
  return apiRequest<MerchPodIntegration>(
    "/host/merchandise/print-on-demand/integrations",
    { method: "PUT", body },
  );
}

export async function markHostPodJobFulfilled(jobId: string) {
  return apiRequest<MerchPodJob>(
    `/host/merchandise/print-on-demand/jobs/${jobId}/fulfill`,
    { method: "POST" },
  );
}

export async function retryHostPodJob(jobId: string) {
  return apiRequest<MerchPodJob>(
    `/host/merchandise/print-on-demand/jobs/${jobId}/retry`,
    { method: "POST" },
  );
}

export async function fetchAdminPodJobs() {
  return apiRequest<MerchPodJob[]>("/admin/merchandise/print-on-demand");
}

export async function markAdminPodJobFulfilled(jobId: string) {
  return apiRequest<MerchPodJob>(
    `/admin/merchandise/print-on-demand/jobs/${jobId}/fulfill`,
    { method: "POST" },
  );
}

export async function retryAdminPodJob(jobId: string) {
  return apiRequest<MerchPodJob>(
    `/admin/merchandise/print-on-demand/jobs/${jobId}/retry`,
    { method: "POST" },
  );
}

/* --- Public marketplace --- */

export type MerchMarketplaceQuery = {
  q?: string;
  host?: string;
  event?: string;
  category?: string;
  type?: string;
  fulfillment_type?: string;
  availability?: string;
  city?: string;
  vault_only?: boolean;
  drops_only?: boolean;
  price_min?: number;
  price_max?: number;
  sort?: string;
  limit?: number;
  offset?: number;
};

function marketplaceQueryString(query: MerchMarketplaceQuery = {}): string {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.host) params.set("host", query.host);
  if (query.event) params.set("event", query.event);
  if (query.category) params.set("category", query.category);
  if (query.type) params.set("type", query.type);
  if (query.fulfillment_type) params.set("fulfillment_type", query.fulfillment_type);
  if (query.availability) params.set("availability", query.availability);
  if (query.city) params.set("city", query.city);
  if (query.vault_only) params.set("vault_only", "true");
  if (query.drops_only) params.set("drops_only", "true");
  if (query.price_min != null) params.set("price_min", String(query.price_min));
  if (query.price_max != null) params.set("price_max", String(query.price_max));
  if (query.sort) params.set("sort", query.sort);
  if (query.limit != null) params.set("limit", String(query.limit));
  if (query.offset != null) params.set("offset", String(query.offset));
  const suffix = params.toString();
  return suffix ? `?${suffix}` : "";
}

export async function fetchMerchMarketplaceHome(): Promise<MarketplaceHome> {
  return apiRequest<MarketplaceHome>("/merch/home");
}

/** Home payload merged with dedicated drops/Vault lists (same sources as /merch/drops and /merch/vault). */
export async function fetchMerchMarketplaceHomeSynced(): Promise<MarketplaceHome> {
  const [home, dropsPage, vaultPage] = await Promise.all([
    fetchMerchMarketplaceHome(),
    fetchMerchDrops(12),
    fetchMerchVault(12),
  ]);

  function mergeProducts(
    primary: MarketplaceProduct[],
    extra: MarketplaceProduct[],
  ): MarketplaceProduct[] {
    const seen = new Set(primary.map((p) => p.id));
    const merged = [...primary];
    for (const row of extra) {
      if (!seen.has(row.id)) {
        seen.add(row.id);
        merged.push(row);
      }
    }
    return merged;
  }

  return {
    ...home,
    drops: mergeProducts(home.drops ?? [], dropsPage.items),
    vault_exclusives: mergeProducts(
      home.vault_exclusives ?? [],
      vaultPage.items,
    ),
  };
}

export async function fetchMerchMarketplace(
  query: MerchMarketplaceQuery = {},
): Promise<MarketplaceListResult> {
  return apiRequest<MarketplaceListResult>(
    `/merch${marketplaceQueryString(query)}`,
  );
}

export async function fetchMerchDrops(
  limit = 48,
): Promise<MarketplaceListResult> {
  return apiRequest<MarketplaceListResult>(
    `/merch/drops?limit=${Math.max(1, Math.min(limit, 100))}`,
  );
}

export async function fetchMerchVault(
  limit = 48,
): Promise<MarketplaceListResult> {
  return apiRequest<MarketplaceListResult>(
    `/merch/vault?limit=${Math.max(1, Math.min(limit, 100))}`,
  );
}

export async function fetchMerchHostShops(
  limit = 24,
): Promise<MarketplaceHostShop[]> {
  return apiRequest<MarketplaceHostShop[]>(
    `/merch/hosts?limit=${Math.max(1, Math.min(limit, 60))}`,
  );
}

export async function fetchMerchHostShop(
  username: string,
  query: { product_type?: string; kind?: string } = {},
): Promise<MarketplaceHostShopDetail> {
  const params = new URLSearchParams();
  if (query.product_type) params.set("product_type", query.product_type);
  if (query.kind) params.set("kind", query.kind);
  const suffix = params.size ? `?${params.toString()}` : "";
  return apiRequest<MarketplaceHostShopDetail>(
    `/merch/hosts/${encodeURIComponent(username)}${suffix}`,
  );
}

export async function fetchMerchProductBySlug(
  slug: string,
  hostSlug?: string | null,
): Promise<MarketplaceProduct> {
  const params = new URLSearchParams();
  if (hostSlug) params.set("h", hostSlug);
  const suffix = params.size ? `?${params.toString()}` : "";
  return apiRequest<MarketplaceProduct>(
    `/merch/${encodeURIComponent(slug)}${suffix}`,
  );
}

export async function createStandaloneMerchProduct(
  body: MerchProductWriteBody,
): Promise<MerchProduct> {
  return apiRequest<MerchProduct>("/host/merch", {
    method: "POST",
    body,
  });
}

export type MerchAdminCategory = {
  id: string;
  slug: string;
  name: string;
  description?: string | null;
  sort_order?: number;
  status?: string;
};

export async function fetchAdminMerchCategories(): Promise<MerchAdminCategory[]> {
  return apiRequest<MerchAdminCategory[]>("/admin/merch/categories");
}

export async function upsertAdminMerchCategory(body: {
  slug: string;
  name: string;
  description?: string | null;
  sort_order?: number;
  status?: string;
}): Promise<MerchAdminCategory> {
  return apiRequest<MerchAdminCategory>("/admin/merch/categories", {
    method: "POST",
    body,
  });
}
