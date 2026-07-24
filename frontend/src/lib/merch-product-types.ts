export const MERCH_PRODUCT_TYPES = [
  { value: "t_shirt", label: "T-shirt" },
  { value: "cap", label: "Cap" },
  { value: "hoodie", label: "Hoodie" },
  { value: "face_mask", label: "Face mask" },
  { value: "wristband", label: "Wristband" },
  { value: "poster", label: "Poster" },
  { value: "tote_bag", label: "Tote bag" },
  { value: "vip_pack", label: "VIP pack" },
  { value: "souvenir", label: "Souvenir" },
  { value: "other", label: "Other" },
] as const;

export type MerchProductTypeValue =
  (typeof MERCH_PRODUCT_TYPES)[number]["value"];

/** Marketplace commerce kinds (host required; event optional). */
export const MERCH_KINDS = [
  { value: "standalone", label: "Standalone" },
  { value: "event_addon", label: "Add-on" },
  { value: "event_merch", label: "Event merch" },
  { value: "post_event_drop", label: "Post-event drop" },
  { value: "vault_exclusive", label: "Vault exclusive" },
  { value: "bundle", label: "Bundle" },
] as const;

export type MerchKindValue = (typeof MERCH_KINDS)[number]["value"];

export const MERCH_KIND_LABELS = Object.fromEntries(
  MERCH_KINDS.map((k) => [k.value, k.label]),
) as Record<MerchKindValue, string>;

/** Browse categories (product.category stores slug). */
export const MERCH_CATEGORIES = [
  { value: "apparel", label: "Apparel" },
  { value: "wristbands", label: "Wristbands" },
  { value: "caps", label: "Caps" },
  { value: "masks", label: "Masks" },
  { value: "posters", label: "Posters" },
  { value: "digital", label: "Digital items" },
  { value: "bundles", label: "Bundles" },
  { value: "collectibles", label: "Collectibles" },
  { value: "food_drink", label: "Food/drink vouchers" },
  { value: "other", label: "Other" },
] as const;

export type MerchCategoryValue = (typeof MERCH_CATEGORIES)[number]["value"];

export const MERCH_CATEGORY_LABELS = Object.fromEntries(
  MERCH_CATEGORIES.map((c) => [c.value, c.label]),
) as Record<MerchCategoryValue, string>;

export const MERCH_MARKETPLACE_SORTS = [
  { value: "featured", label: "Featured" },
  { value: "newest", label: "Newest" },
  { value: "price_asc", label: "Price: low to high" },
  { value: "price_desc", label: "Price: high to low" },
  { value: "popular", label: "Popular" },
] as const;
