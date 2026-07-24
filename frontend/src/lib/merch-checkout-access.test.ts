import { describe, expect, it } from "vitest";

import {
  cartRequiresSignInForMerch,
  findCatalogProductByProductId,
} from "./merch-checkout-access";
import type { MerchBundle, MerchCatalogProduct } from "./types/merch";

const vaultHoodie: MerchCatalogProduct = {
  id: "prod-vault",
  name: "Backstage Hoodie",
  slug: "backstage-hoodie",
  is_vault_exclusive: true,
  requires_vault_access: true,
  access_eligible: false,
  access_locked: true,
  variants: [],
};

describe("cartRequiresSignInForMerch", () => {
  it("detects vault bundle merch by product_id when catalog variants are empty", () => {
    const bundle: MerchBundle = {
      id: "b1",
      host_id: "h1",
      event_id: "e1",
      name: "VIP + Merch Pack",
      slug: "vip-merch",
      status: "active",
      bundle_price: "45000",
      currency: "NGN",
      ticket_type_id: "tt1",
      merch_variant_rules: [
        {
          product_id: "prod-vault",
          variant_id: "var-hoodie",
          quantity: 1,
          product_name: "Backstage Hoodie",
        },
      ],
    };
    expect(
      cartRequiresSignInForMerch({
        catalog: [vaultHoodie],
        selectedMerch: [],
        selectedBundles: [{ bundle }],
      }),
    ).toBe(true);
  });

  it("detects vault flags on bundle rules without catalog lookup", () => {
    const bundle: MerchBundle = {
      id: "b2",
      host_id: "h1",
      event_id: "e1",
      name: "Vault pack",
      slug: "vault-pack",
      status: "active",
      bundle_price: "45000",
      currency: "NGN",
      ticket_type_id: "tt1",
      merch_variant_rules: [
        {
          variant_id: "var-hoodie",
          quantity: 1,
          is_vault_exclusive: true,
        },
      ],
    };
    expect(
      cartRequiresSignInForMerch({
        catalog: [],
        selectedMerch: [],
        selectedBundles: [{ bundle }],
      }),
    ).toBe(true);
  });
});

describe("findCatalogProductByProductId", () => {
  it("finds product without variants", () => {
    expect(
      findCatalogProductByProductId([vaultHoodie], "prod-vault")?.name,
    ).toBe("Backstage Hoodie");
  });
});
