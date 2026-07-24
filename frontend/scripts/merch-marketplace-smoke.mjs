/**
 * Merch marketplace smoke checks.
 * Run: node scripts/merch-marketplace-smoke.mjs
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

function exists(rel) {
  return fs.existsSync(path.join(root, rel));
}

for (const rel of [
  "src/app/merch/page.tsx",
  "src/app/merch/[slug]/page.tsx",
  "src/app/merch/drops/page.tsx",
  "src/app/merch/vault/page.tsx",
  "src/app/merch/hosts/[username]/page.tsx",
  "src/app/u/[username]/shop/page.tsx",
  "src/app/host/merchandise/orders/page.tsx",
  "src/app/host/merchandise/fulfillment/page.tsx",
  "src/app/admin/merch/page.tsx",
  "src/app/admin/merch/categories/page.tsx",
  "src/components/merch/marketplace/MerchMarketplaceView.tsx",
  "src/components/merch/marketplace/MerchMarketplaceHero.tsx",
  "src/components/merch/marketplace/MarketplaceProductCard.tsx",
  "src/components/merch/marketplace/MarketplaceProductRail.tsx",
  "src/components/merch/marketplace/MarketplaceHostShopCard.tsx",
  "src/components/merch/marketplace/MarketplaceFilters.tsx",
  "src/components/merch/marketplace/MarketplaceEmptyState.tsx",
  "src/components/merch/marketplace/MerchProductDetailView.tsx",
  "src/components/merch/marketplace/MerchDropsView.tsx",
  "src/components/merch/marketplace/MerchVaultView.tsx",
  "src/components/merch/marketplace/MerchHostShopView.tsx",
  "src/components/merch/marketplace/HostShopCheckoutView.tsx",
  "src/app/merch/hosts/[username]/checkout/page.tsx",
  "src/lib/merch-api.ts",
  "src/lib/types/merch.ts",
  "src/lib/merch-product-types.ts",
]) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const page = read("src/app/merch/page.tsx");
assert.match(page, /MerchMarketplaceView/);
assert.match(page, /buildPageMetadata|merchSeo/);

const content = read("src/components/marketing/merch/content.ts");
assert.match(content, /Shop the night\. Wear the memory\./);
assert.match(
  content,
  /Discover host merch, event add-ons, post-event drops, and Vault exclusives/,
);

const hero = read("src/components/merch/marketplace/MerchMarketplaceHero.tsx");
assert.match(hero, /Shop the night\. Wear the memory\./);
assert.match(hero, /#catalog|Shop merch/);
assert.match(hero, /\/merch\/drops/);
assert.match(hero, /\/host\/merchandise\/new/);
assert.match(hero, /bg-ink/);
assert.doesNotMatch(hero, /shadow-\[var\(--shadow\)\]/);
assert.doesNotMatch(hero, /border border-border bg-card/);

const api = read("src/lib/merch-api.ts");
for (const fn of [
  "fetchMerchMarketplaceHome",
  "fetchMerchMarketplace",
  "fetchMerchDrops",
  "fetchMerchVault",
  "fetchMerchHostShops",
  "fetchMerchHostShop",
  "fetchMerchProductBySlug",
  "createStandaloneMerchProduct",
]) {
  assert.match(api, new RegExp(`export async function ${fn}`));
}

const types = read("src/lib/types/merch.ts");
assert.match(types, /export type MarketplaceProduct/);
assert.match(types, /marketplace_kind/);
assert.match(types, /more_by_host/);
assert.match(types, /indexable/);

const kindConsts = read("src/lib/merch-product-types.ts");
assert.match(kindConsts, /export const MERCH_KINDS/);
assert.match(kindConsts, /export const MERCH_CATEGORIES/);

const hostNew = read("src/app/host/merchandise/new/page.tsx");
assert.match(hostNew, /allowStandalone/);
assert.match(hostNew, /Standalone shop product/);
assert.doesNotMatch(hostNew, /Create an event first/);

const hostHub = read("src/app/host/merchandise/page.tsx");
assert.match(hostHub, /\/host\/merchandise\/orders/);
assert.match(hostHub, /\/host\/merchandise\/fulfillment/);

const shopRedirect = read("src/app/u/[username]/shop/page.tsx");
assert.match(shopRedirect, /permanentRedirect/);
assert.match(shopRedirect, /\/merch\/hosts\//);

const sitemap = read("src/app/sitemap.ts");
assert.match(sitemap, /\/merch\/drops/);
assert.match(sitemap, /\/merch\/vault/);
assert.match(sitemap, /changeFrequency: "daily"/);

const detail = read("src/app/merch/[slug]/page.tsx");
assert.match(detail, /indexable/);
assert.match(detail, /robots/);

const detailView = read("src/components/merch/marketplace/MerchProductDetailView.tsx");
assert.match(detailView, /buildHostShopCheckoutHref|HostShopCheckoutView/);
assert.match(
  read("src/components/merch/marketplace/HostShopCheckoutView.tsx"),
  /createOrder|checkoutOrder|openPaystackPopup/,
);
assert.doesNotMatch(
  read("src/components/merch/marketplace/MerchMarketplaceView.tsx"),
  /lorem ipsum/i,
);

console.log("merch-marketplace-smoke: ok");
