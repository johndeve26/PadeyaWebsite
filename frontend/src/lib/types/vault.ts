export type VaultAccessRule = {
  access_type: string;
  price: string | number;
  currency: string;
  required_event_id: string | null;
  event_id: string | null;
  required_ticket_type_id: string | null;
  ticket_type_ids: string[] | null;
  require_check_in: boolean;
  required_legacy_tier: string | null;
  access_code: string | null;
  access_code_set: boolean;
  max_unlocks: number | null;
  starts_at: string | null;
  ends_at: string | null;
};

export type VaultMedia = {
  id: string;
  media_type: string;
  url: string | null;
  label: string | null;
  is_preview: boolean;
  sort_order: number;
  locked: boolean;
};

export type VaultRelatedEvent = {
  id: string;
  title: string;
  slug: string;
  href: string;
};

export type VaultRelatedMemory = {
  id: string;
  event_id: string;
  event_title: string;
  event_slug: string;
  host_username: string;
  href: string;
};

/** Slim public catalog card from GET /vault/public/{username} */
export type VaultCatalogCard = {
  id: string;
  host_username: string | null;
  title: string;
  slug: string;
  preview_text: string | null;
  cover_url: string | null;
  content_type?: string;
  access_type: string;
  locked: boolean;
  has_access: boolean;
  price: string | number | null;
  currency: string | null;
  related_event: VaultRelatedEvent | null;
  related_memory?: VaultRelatedMemory | null;
  share_path: string | null;
  cta_label: string;
  expired: boolean;
  featured?: boolean;
};

export type VaultItem = {
  id: string;
  host_id: string;
  host_username: string | null;
  host_display_name: string | null;
  title: string;
  slug: string;
  content_type: string;
  status: string;
  description: string | null;
  preview_text: string | null;
  body: string | null;
  cover_url: string | null;
  file_url: string | null;
  external_url: string | null;
  related_event_id: string | null;
  related_memory_id: string | null;
  related_event?: VaultRelatedEvent | null;
  related_memory?: VaultRelatedMemory | null;
  tags: string[];
  price: string | number;
  currency: string;
  moderation_status: string;
  moderation_note?: string | null;
  moderated_at?: string | null;
  published_at: string | null;
  expires_at: string | null;
  archived_at?: string | null;
  created_at: string;
  access: VaultAccessRule | null;
  media: VaultMedia[];
  has_access: boolean;
  access_reason: string | null;
  lock_reason?: string | null;
  locked: boolean;
  expired?: boolean;
  share_path?: string | null;
  cta_label?: string | null;
};

/** Admin moderation list row with unlock/purchase summary */
export type VaultAdminItem = VaultItem & {
  access_type?: string | null;
  view_count?: number;
  unlock_count?: number;
  paid_purchase_count?: number;
  grant_count?: number;
  gross_revenue?: string | number;
  report_count?: number;
};

export type AdminVaultFilters = {
  status?: string;
  moderation_status?: string;
  access_type?: string;
  host_username?: string;
  q?: string;
  limit?: number;
  offset?: number;
};

export type VaultPurchase = {
  id: string;
  vault_item_id: string;
  host_id: string;
  amount: string | number;
  currency: string;
  status: string;
  payment_reference: string;
  authorization_url: string | null;
  access_code: string | null;
  paid_at: string | null;
  created_at: string;
  item_title: string | null;
  item_slug: string | null;
  free_checkout: boolean;
};

export type VaultLibraryItem = VaultItem & {
  access_label: string;
  library_group: string;
};

export type VaultLibraryActivity = {
  id: string;
  kind: string;
  title: string;
  detail: string | null;
  at: string;
  href: string | null;
  access_label: string | null;
  host_username: string | null;
};

export type VaultLibraryStats = {
  unlocked_count: number;
  followed_count: number;
  ticket_count: number;
  unlockable_count: number;
  purchase_count: number;
};

export type VaultLibrarySummary = {
  unlocked: VaultLibraryItem[];
  followed_host_drops: VaultLibraryItem[];
  ticket_holder_content: VaultLibraryItem[];
  unlockable: VaultLibraryItem[];
  activity: VaultLibraryActivity[];
  purchases: VaultPurchase[];
  stats: VaultLibraryStats;
};

export type VaultCheckout = {
  purchase: VaultPurchase;
  public_key: string | null;
};

export type VaultEarnings = {
  host_id: string;
  currency: string;
  gross_revenue: string | number;
  purchase_count: number;
  paid_purchase_count: number;
  view_count: number;
  published_item_count: number;
};

export type VaultStudioItem = VaultItem & {
  view_count: number;
  unlock_count: number;
  earnings: string | number;
  is_access_gated: boolean;
  is_paid: boolean;
  is_ticket_gated: boolean;
  is_expired: boolean;
  is_archived: boolean;
  is_scheduled?: boolean;
  is_hidden_by_admin?: boolean;
};

export type VaultLifecycleStatus =
  | "draft"
  | "published"
  | "scheduled"
  | "expired"
  | "archived"
  | "hidden_by_admin";

export type VaultStudioTopItem = {
  id: string;
  title: string;
  slug: string;
  cover_url: string | null;
  view_count: number;
  unlock_count: number;
  earnings: string | number;
  access_type: string | null;
};

export type VaultStudioStats = {
  total_items: number;
  published_items: number;
  locked_items: number;
  free_items: number;
  paid_unlocks: number;
  view_count: number;
  gross_revenue: string | number;
  draft_items: number;
  archived_items: number;
  expired_items: number;
  paid_items: number;
  ticket_holder_items: number;
};

export type VaultStudioSummary = {
  host_id: string;
  host_username: string;
  share_path: string;
  earnings: VaultEarnings;
  stats: VaultStudioStats;
  items: VaultStudioItem[];
  top_item: VaultStudioTopItem | null;
  featured_vault_item_id: string | null;
  legacy_vault_block_visible: boolean;
};

export type VaultStudioFilter =
  | "all"
  | "draft"
  | "published"
  | "scheduled"
  | "locked"
  | "free"
  | "paid"
  | "ticket-holder"
  | "expired"
  | "archived"
  | "hidden";

export type VaultMediaDraft = {
  url: string;
  media_type: string;
  label: string;
  is_preview: boolean;
  sort_order: number;
};

export type VaultAccessDraft = {
  access_type: string;
  price: string;
  currency: string;
  required_event_id: string;
  required_ticket_type_id: string;
  require_check_in: boolean;
  required_legacy_tier: string;
  access_code: string;
  max_unlocks: string;
  starts_at: string;
  ends_at: string;
};

export const ACCESS_TYPE_HINTS: Record<string, string> = {
  free: "Anyone can open this published drop.",
  followers_only: "Requires following the host.",
  ticket_holder_only: "Requires a valid ticket/order for the related event.",
  checked_in_attendee_only: "Requires a checked-in ticket for the related event.",
  vip_ticket_holder_only: "Requires a matching VIP/VVIP ticket type.",
  one_time_unlock: "Requires payment (or demo unlock flow).",
  invite_only: "Requires access code redeem or a manual host grant.",
  admin_hidden: "Not publicly visible — host/admin only.",
};

export const CONTENT_TYPE_HINTS: Record<string, string> = {
  text_post: "Written exclusive — notes, private posts, long-form drops.",
  image_gallery: "Photo set — VIP galleries, BTS stills, lookbooks.",
  video: "Video drop or clip.",
  audio: "Unreleased DJ set, interview, or soundtrack.",
  file_download: "Downloadable file or PDF (use file URL).",
  early_access: "Early-access ticket or asset drop.",
  discount_drop: "Discount / promo code exclusive.",
  ticket_holder_recap: "Recap for ticket holders after the night.",
  vip_content: "VIP / VVIP exclusive content.",
  external_link: "Unlock reveals a private external URL.",
  announcement: "Private host announcement for entitled fans.",
};

export const CONTENT_TYPES = [
  "text_post",
  "image_gallery",
  "video",
  "audio",
  "file_download",
  "early_access",
  "discount_drop",
  "ticket_holder_recap",
  "vip_content",
  "external_link",
  "announcement",
] as const;

export const ACCESS_TYPES = [
  "free",
  "followers_only",
  "ticket_holder_only",
  "checked_in_attendee_only",
  "vip_ticket_holder_only",
  "one_time_unlock",
  "invite_only",
  "admin_hidden",
] as const;
