/**
 * Product / Offer JSON-LD for public indexable merch (Phase 1A).
 * Privacy-safe: no inventory internals, vault secrets, buyer data, or fabricated ratings.
 */

import type { MarketplaceProduct } from "@/lib/types/merch";
import { resolvePublicAssetUrl } from "@/lib/seo/public-asset";
import { absoluteUrl } from "@/lib/seo/site";
import { LIVE_SITE_ORIGIN } from "@/lib/seo/env-policy";

export type MerchProductSeoInput = Pick<
  MarketplaceProduct,
  | "name"
  | "slug"
  | "description"
  | "short_description"
  | "base_price"
  | "currency"
  | "cover_image_url"
  | "image_url"
  | "gallery_urls"
  | "availability"
  | "indexable"
  | "host_name"
  | "host_slug"
  | "sponsor_brand_name"
  | "is_sponsor_branded"
  | "teaser_only"
  | "access_locked"
>;

export function isMerchProductSchemaEligible(
  product: Pick<MerchProductSeoInput, "slug" | "name" | "indexable"> | null | undefined,
): boolean {
  if (!product) return false;
  if (!product.slug?.trim() || !product.name?.trim()) return false;
  return product.indexable !== false;
}

/**
 * Map public merch availability → schema.org ItemAvailability.
 * Unsupported / locked states return null (omit Offer rather than guess).
 */
export function merchOfferAvailability(
  availability: string | null | undefined,
): string | null {
  const v = (availability || "").trim().toLowerCase();
  switch (v) {
    case "purchasable":
      return "https://schema.org/InStock";
    case "sold_out":
      return "https://schema.org/SoldOut";
    case "coming_soon":
      // Sales window not open yet (storefront maps future sales_start_at here).
      return "https://schema.org/PreOrder";
    default:
      // locked / unavailable / unknown — do not invent Offer availability
      return null;
  }
}

function publicImages(product: MerchProductSeoInput): string[] {
  const urls: string[] = [];
  for (const raw of [
    product.cover_image_url,
    product.image_url,
    ...(product.gallery_urls ?? []),
  ]) {
    const resolved = resolvePublicAssetUrl(raw);
    if (resolved && !urls.includes(resolved)) urls.push(resolved);
  }
  return urls;
}

function brandNode(
  product: MerchProductSeoInput,
): Record<string, unknown> | undefined {
  if (product.is_sponsor_branded && product.sponsor_brand_name?.trim()) {
    return {
      "@type": "Brand",
      name: product.sponsor_brand_name.trim(),
    };
  }
  if (product.host_name?.trim()) {
    const brand: Record<string, unknown> = {
      "@type": "Brand",
      name: product.host_name.trim(),
    };
    if (product.host_slug?.trim()) {
      brand.url = absoluteUrl(`/u/${encodeURIComponent(product.host_slug.trim())}`);
    }
    return brand;
  }
  return undefined;
}

/**
 * Product + Offer for eligible public merch.
 * Returns null when missing, private/noindex, or insufficient public data.
 */
export function merchProductJsonLd(
  product: MerchProductSeoInput | null | undefined,
): Record<string, unknown> | null {
  if (!isMerchProductSchemaEligible(product)) return null;
  const p = product!;

  const path = `/merch/${encodeURIComponent(p.slug.trim())}`;
  const url = absoluteUrl(path);
  const description = (
    p.short_description ||
    p.description ||
    `${p.name} on Pàdéyá`
  )
    .trim()
    .slice(0, 500);

  const currency = (p.currency || "").trim().toUpperCase();
  if (!currency || p.base_price === undefined || p.base_price === null) {
    return null;
  }

  const node: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "Product",
    "@id": `${LIVE_SITE_ORIGIN}${path}#product`,
    name: p.name.trim(),
    description,
    url,
  };

  const images = publicImages(p);
  if (images.length === 1) node.image = images[0];
  else if (images.length > 1) node.image = images;

  const brand = brandNode(p);
  if (brand) node.brand = brand;

  const availability = merchOfferAvailability(p.availability);
  // Teaser / access-locked catalog rows: Product OK when indexable; skip Offer.
  if (
    availability &&
    !p.teaser_only &&
    p.access_locked !== true
  ) {
    node.offers = {
      "@type": "Offer",
      url,
      price: String(p.base_price),
      priceCurrency: currency,
      availability,
    };
  }

  return node;
}
