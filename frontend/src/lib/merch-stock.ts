import type { MerchCatalogProduct, MerchVariant } from "@/lib/types/merch";

export type MerchStockStatus = "available" | "low_stock" | "sold_out";

const LOW_STOCK_THRESHOLD = 5;

export function variantAvailable(variant: MerchVariant): number {
  return Math.max(0, variant.available_quantity ?? variant.inventory_count ?? 0);
}

export function productStockTotal(product: MerchCatalogProduct): number {
  return product.variants.reduce((n, v) => n + variantAvailable(v), 0);
}

export function stockStatus(available: number): MerchStockStatus {
  if (available <= 0) return "sold_out";
  if (available <= LOW_STOCK_THRESHOLD) return "low_stock";
  return "available";
}

export function stockStatusLabel(status: MerchStockStatus): string {
  if (status === "sold_out") return "Sold out";
  if (status === "low_stock") return "Low stock";
  return "Available";
}

export function productStockStatus(
  product: MerchCatalogProduct,
): MerchStockStatus {
  return stockStatus(productStockTotal(product));
}

export function buildMerchCheckoutHref(opts: {
  eventSlug: string;
  productId: string;
  variantId: string;
  quantity?: number;
  referralCode?: string;
}): string {
  const qs = new URLSearchParams();
  qs.set("merch", opts.productId);
  qs.set("variant", opts.variantId);
  if (opts.quantity && opts.quantity > 1) {
    qs.set("qty", String(opts.quantity));
  }
  if (opts.referralCode) qs.set("ref", opts.referralCode);
  return `/events/${opts.eventSlug}/checkout?${qs.toString()}`;
}

/** Standalone host-shop checkout (no event). */
export function buildHostShopCheckoutHref(opts: {
  hostSlug: string;
  productId?: string;
  variantId?: string;
  quantity?: number;
}): string {
  const qs = new URLSearchParams();
  if (opts.productId) qs.set("merch", opts.productId);
  if (opts.variantId) qs.set("variant", opts.variantId);
  if (opts.quantity && opts.quantity > 1) {
    qs.set("qty", String(opts.quantity));
  }
  const q = qs.toString();
  return `/merch/hosts/${opts.hostSlug}/checkout${q ? `?${q}` : ""}`;
}
