import { describe, expect, it } from "vitest";

import {
  curateMarketplaceHome,
  dropEligibilityLabel,
  excludeShown,
  limitProducts,
  markShown,
  MERCH_SECTION_LIMITS,
  productKey,
} from "./marketplace-curation";
import type { MarketplaceHome, MarketplaceProduct } from "@/lib/types/merch";

function product(id: string, host = "host-a"): MarketplaceProduct {
  return {
    id,
    name: `Product ${id}`,
    slug: `product-${id}`,
    base_price: 5000,
    currency: "NGN",
    variants: [],
    host_slug: host,
    host_id: host,
  };
}

describe("marketplace curation", () => {
  it("limits featured merch to max 6", () => {
    const home: MarketplaceHome = {
      featured: Array.from({ length: 12 }, (_, i) => product(`f${i}`)),
      event_merch: [],
      host_shops: [],
      drops: [],
      vault_exclusives: [],
      categories: [],
      empty: false,
    };
    const curated = curateMarketplaceHome(home);
    expect(curated.featured).toHaveLength(MERCH_SECTION_LIMITS.featured);
    expect(curated.featured.length).toBeLessThanOrEqual(6);
  });

  it("dedupes featured vs event merch but keeps drops and vault rails", () => {
    const shared = product("shared");
    const home: MarketplaceHome = {
      featured: [shared, product("f2")],
      event_merch: [shared, product("e2")],
      host_shops: [],
      drops: [shared, product("d2")],
      vault_exclusives: [shared, product("v2")],
      categories: [],
      empty: false,
    };
    const curated = curateMarketplaceHome(home);
    expect(curated.featured.some((p) => productKey(p) === productKey(shared))).toBe(
      true,
    );
    expect(curated.eventMerch.some((p) => productKey(p) === productKey(shared))).toBe(
      false,
    );
    expect(curated.drops.some((p) => productKey(p) === productKey(shared))).toBe(
      true,
    );
    expect(curated.vault.some((p) => productKey(p) === productKey(shared))).toBe(
      true,
    );
  });

  it("limits event merch, drops, vault, and host shops", () => {
    const home: MarketplaceHome = {
      featured: [],
      event_merch: Array.from({ length: 20 }, (_, i) => product(`e${i}`)),
      host_shops: Array.from({ length: 10 }, (_, i) => ({
        host_id: `h${i}`,
        host_name: `Host ${i}`,
        host_slug: `host-${i}`,
        merch_count: 3,
      })),
      drops: Array.from({ length: 10 }, (_, i) => product(`d${i}`)),
      vault_exclusives: Array.from({ length: 10 }, (_, i) => product(`v${i}`)),
      categories: [],
      empty: false,
    };
    const curated = curateMarketplaceHome(home);
    expect(curated.eventMerch).toHaveLength(MERCH_SECTION_LIMITS.eventMerch);
    expect(curated.drops).toHaveLength(MERCH_SECTION_LIMITS.drops);
    expect(curated.vault).toHaveLength(MERCH_SECTION_LIMITS.vault);
    expect(curated.hostShops).toHaveLength(MERCH_SECTION_LIMITS.hostShops);
  });

  it("maps drop eligibility labels", () => {
    expect(dropEligibilityLabel("checked_in")).toBe("Checked-in fans only");
    expect(dropEligibilityLabel("ticket_buyers")).toBe("Ticket buyers only");
    expect(dropEligibilityLabel("vip")).toBe("VIP only");
    expect(dropEligibilityLabel("vault_members")).toBe("Vault members only");
  });

  it("excludeShown and limitProducts work", () => {
    const shown = new Set<string>();
    const items = [product("1"), product("2"), product("3")];
    markShown(shown, [product("1")]);
    const filtered = excludeShown(items, shown);
    expect(filtered).toHaveLength(2);
    expect(limitProducts(filtered, 1)).toHaveLength(1);
  });
});
