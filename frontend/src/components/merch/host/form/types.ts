export type MerchVariantFormRow = {
  key: string;
  id?: string;
  label: string;
  size: string;
  color: string;
  option_1_name: string;
  option_1_value: string;
  option_2_name: string;
  option_2_value: string;
  sku: string;
  price_override: string;
  inventory: string;
  status: string;
  print_on_demand_variant_ref: string;
};

export type MerchProductFormValues = {
  name: string;
  description: string;
  short_description: string;
  product_type: string;
  category: string;
  tags: string[];
  cover_image_url: string;
  gallery_urls: string;
  use_fallback_visual: boolean;
  base_price: string;
  currency: string;
  status: string;
  sales_start_at: string;
  sales_end_at: string;
  requires_ticket: boolean;
  requires_vip: boolean;
  max_per_buyer: string;
  show_on_event_page: boolean;
  is_featured: boolean;
  pickup_enabled: boolean;
  shipping_enabled: boolean;
  print_on_demand_enabled: boolean;
  pod_provider: string;
  pod_product_ref: string;
  pickup_instructions: string;
  pickup_location_label: string;
  pickup_time_window: string;
  fulfillment_notes: string;
  restock_on_refund: boolean;
  size_chart_id: string;
  is_sponsor_branded: boolean;
  sponsor_brand_name: string;
  sponsor_logo_url: string;
  sponsor_description: string;
  sponsor_split_type: string;
  sponsor_split_value: string;
  is_vault_exclusive: boolean;
  required_access_type: string;
  required_vault_item_id: string;
  requires_check_in: boolean;
  storefront_visibility: string;
  variants: MerchVariantFormRow[];
};

export type MerchFormSectionId =
  | "basics"
  | "media"
  | "pricing"
  | "sales"
  | "access"
  | "fulfillment"
  | "review";

export type MerchSectionStatus = "complete" | "needs_info" | "optional";

export const MERCH_FORM_SECTIONS: {
  id: MerchFormSectionId;
  label: string;
  short: string;
  compactLabel: string;
}[] = [
  { id: "basics", label: "Basics", short: "1", compactLabel: "Basics" },
  { id: "media", label: "Media", short: "2", compactLabel: "Media" },
  {
    id: "pricing",
    label: "Pricing & variants",
    short: "3",
    compactLabel: "Pricing",
  },
  { id: "sales", label: "Sales rules", short: "4", compactLabel: "Sales" },
  { id: "access", label: "Access", short: "5", compactLabel: "Access" },
  {
    id: "fulfillment",
    label: "Fulfillment",
    short: "6",
    compactLabel: "Fulfill",
  },
  { id: "review", label: "Review & publish", short: "7", compactLabel: "Review" },
];

export const ACCESS_TYPE_OPTIONS = [
  { value: "", label: "Any Vault unlock (host)" },
  { value: "follower", label: "Follower" },
  { value: "ticket_holder", label: "Ticket holder" },
  { value: "checked_in_attendee", label: "Checked-in attendee" },
  { value: "vip_ticket_holder", label: "VIP ticket holder" },
  { value: "paid_vault_member", label: "Paid Vault member" },
  { value: "invite_only", label: "Invite only (linked Vault item)" },
] as const;

export const STOREFRONT_VISIBILITY_OPTIONS = [
  { value: "event_only", label: "Event only" },
  { value: "host_storefront", label: "Host storefront" },
  { value: "post_event_drop", label: "Post-event drop" },
  { value: "vault_exclusive", label: "Vault exclusive" },
  { value: "hidden", label: "Hidden" },
] as const;

let variantKey = 0;

export function newVariantKey(): string {
  variantKey += 1;
  return `v-${variantKey}-${Date.now()}`;
}

export function createDefaultVariant(
  overrides?: Partial<MerchVariantFormRow>,
): MerchVariantFormRow {
  return {
    key: newVariantKey(),
    label: "One size",
    size: "",
    color: "",
    option_1_name: "",
    option_1_value: "",
    option_2_name: "",
    option_2_value: "",
    sku: "",
    price_override: "",
    inventory: "20",
    status: "active",
    print_on_demand_variant_ref: "",
    ...overrides,
  };
}

export const DEFAULT_MERCH_FORM_VALUES: MerchProductFormValues = {
  name: "",
  description: "",
  short_description: "",
  product_type: "t_shirt",
  category: "",
  tags: [],
  cover_image_url: "",
  gallery_urls: "",
  use_fallback_visual: true,
  base_price: "5000",
  currency: "NGN",
  status: "draft",
  sales_start_at: "",
  sales_end_at: "",
  requires_ticket: false,
  requires_vip: false,
  max_per_buyer: "",
  show_on_event_page: true,
  is_featured: false,
  pickup_enabled: true,
  shipping_enabled: false,
  print_on_demand_enabled: false,
  pod_provider: "manual",
  pod_product_ref: "",
  pickup_instructions: "Collect at the merch stand — bring your pickup code.",
  pickup_location_label: "Merch stand",
  pickup_time_window: "",
  fulfillment_notes: "",
  restock_on_refund: false,
  size_chart_id: "",
  is_sponsor_branded: false,
  sponsor_brand_name: "",
  sponsor_logo_url: "",
  sponsor_description: "",
  sponsor_split_type: "",
  sponsor_split_value: "",
  is_vault_exclusive: false,
  required_access_type: "",
  required_vault_item_id: "",
  requires_check_in: false,
  storefront_visibility: "event_only",
  variants: [createDefaultVariant()],
};

export function toLocalInput(value?: string | null): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function fromLocalInput(value: string): string | null {
  if (!value.trim()) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

export function parseGallery(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 20);
}

export function variantEffectivePrice(
  basePrice: string,
  variant: MerchVariantFormRow,
): number {
  if (variant.price_override.trim()) {
    const n = Number(variant.price_override);
    if (Number.isFinite(n)) return n;
  }
  const base = Number(basePrice);
  return Number.isFinite(base) ? base : 0;
}

export function variantSummary(values: MerchProductFormValues) {
  const variants = values.variants;
  const prices = variants.map((v) => variantEffectivePrice(values.base_price, v));
  const stock = variants.reduce(
    (sum, v) => sum + Math.max(0, Number(v.inventory) || 0),
    0,
  );
  return {
    totalVariants: variants.length,
    totalStock: stock,
    lowestPrice: prices.length ? Math.min(...prices) : 0,
    highestPrice: prices.length ? Math.max(...prices) : 0,
  };
}
