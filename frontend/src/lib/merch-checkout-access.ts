import type { MerchBundle, MerchCatalogProduct } from "@/lib/types/merch";

/** Logged-out buyers cannot complete checkout for these products. */
export function merchProductNeedsSignIn(product: MerchCatalogProduct): boolean {
  if (product.access_eligible) return false;
  if (product.is_vault_exclusive || product.requires_vault_access) {
    return true;
  }
  return Boolean(
    product.access_locked ||
      product.access_reason === "vault_login_required" ||
      product.access_reason === "login_required",
  );
}

export function findCatalogProductByProductId(
  catalog: MerchCatalogProduct[],
  productId: string,
): MerchCatalogProduct | undefined {
  return catalog.find((product) => product.id === productId);
}

export function findCatalogProductByVariantId(
  catalog: MerchCatalogProduct[],
  variantId: string,
): MerchCatalogProduct | undefined {
  for (const product of catalog) {
    if (product.variants.some((variant) => variant.id === variantId)) {
      return product;
    }
  }
  return undefined;
}

export function cartRequiresSignInForMerch(opts: {
  catalog: MerchCatalogProduct[];
  selectedMerch: { product: MerchCatalogProduct }[];
  selectedBundles: { bundle: MerchBundle }[];
}): boolean {
  for (const row of opts.selectedMerch) {
    if (merchProductNeedsSignIn(row.product)) return true;
  }
  for (const { bundle } of opts.selectedBundles) {
    for (const rule of bundle.merch_variant_rules ?? []) {
      if (rule.is_vault_exclusive || rule.requires_vault_access) {
        return true;
      }
      let product: MerchCatalogProduct | undefined;
      if (rule.product_id) {
        product = findCatalogProductByProductId(opts.catalog, rule.product_id);
      }
      if (!product && rule.variant_id) {
        product = findCatalogProductByVariantId(opts.catalog, rule.variant_id);
      }
      if (product && merchProductNeedsSignIn(product)) return true;
    }
  }
  return false;
}
