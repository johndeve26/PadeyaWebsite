/**
 * Merch commerce smoke checks — no browser / React test runner required.
 * Mirrors vault-smoke / studio-smoke patterns.
 * Run: npm run test:merch
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

// --- Host storefront loads ---
const storefrontPage = "src/app/u/[username]/merch/page.tsx";
const storefrontDetail = "src/app/u/[username]/merch/[productId]/page.tsx";
assert.ok(exists(storefrontPage), `missing ${storefrontPage}`);
assert.ok(exists(storefrontDetail), `missing ${storefrontDetail}`);
const storefront = read(storefrontPage);
assert.match(storefront, /fetchHostMerchStorefront/);
assert.match(storefront, /Pàdéyá|Padeya|merch/i);
assert.match(storefront, /access_locked|teaser_only|Vault exclusive|Post-event drop/);
assert.match(storefront, /sm:grid-cols-|lg:grid-cols-|md:grid/);

// --- Shipping form works ---
const shippingForm = "src/components/merch/ShippingAddressForm.tsx";
assert.ok(exists(shippingForm), `missing ${shippingForm}`);
const shipping = read(shippingForm);
assert.match(shipping, /export function ShippingAddressForm/);
assert.match(shipping, /isShippingAddressComplete/);
assert.match(shipping, /shippingAddressToApiPayload/);
assert.match(shipping, /recipient_name|phone_number|address_line_1/);
assert.match(shipping, /Kept private|private/i);

const checkoutPage = "src/app/events/[slug]/checkout/page.tsx";
assert.ok(exists(checkoutPage), `missing ${checkoutPage}`);
const checkout = read(checkoutPage);
assert.match(checkout, /ShippingAddressForm/);
assert.match(checkout, /fulfillment_method|shipping/);

// --- Bundle selection works ---
const bundlePicker = "src/components/merch/CheckoutBundlePicker.tsx";
assert.ok(exists(bundlePicker), `missing ${bundlePicker}`);
assert.match(read(bundlePicker), /export function CheckoutBundlePicker/);
assert.match(read(bundlePicker), /Ticket \+ merch bundles|bundle_price/);
assert.match(checkout, /CheckoutBundlePicker/);

const hostBundles = "src/app/host/events/[id]/bundles/page.tsx";
assert.ok(exists(hostBundles), `missing ${hostBundles}`);

// --- Discount code works ---
const discountsPage = "src/app/host/merchandise/discounts/page.tsx";
assert.ok(exists(discountsPage), `missing ${discountsPage}`);
const discounts = read(discountsPage);
assert.match(discounts, /Merch discount|discount_type|Create merch discount/i);
assert.match(read("src/lib/merch-api.ts"), /\/merch\/discounts\/validate/);
assert.match(checkout, /discount|merch_discount|validateMerchDiscount/i);

// --- Merch QR pickup UI works ---
const pickupQr = "src/components/merch/MerchPickupQr.tsx";
assert.ok(exists(pickupQr), `missing ${pickupQr}`);
assert.match(read(pickupQr), /export function MerchPickupQr/);
assert.match(read(pickupQr), /QR|pickup/i);
const buyerMerchDetail = "src/app/dashboard/merchandise/[orderItemId]/page.tsx";
assert.ok(exists(buyerMerchDetail), `missing ${buyerMerchDetail}`);
assert.match(read(buyerMerchDetail), /MerchPickupQr/);
const pickupDesk = "src/components/merch/host/HostMerchPickupDesk.tsx";
assert.ok(exists(pickupDesk), `missing ${pickupDesk}`);
assert.match(read(pickupDesk), /scan|QR|pickup/i);

// --- Stock alerts page works ---
const stockAlerts = "src/app/host/merchandise/stock-alerts/page.tsx";
assert.ok(exists(stockAlerts), `missing ${stockAlerts}`);
const alertsPage = read(stockAlerts);
assert.match(alertsPage, /fetchHostStockAlerts|Low stock|Sold out/);
assert.match(alertsPage, /RequireHost|DashboardShell/);

// --- Size guide works ---
const sizeGuide = "src/components/merch/MerchSizeGuideModal.tsx";
assert.ok(exists(sizeGuide), `missing ${sizeGuide}`);
assert.match(read(sizeGuide), /export function MerchSizeGuideModal/);
assert.match(read(sizeGuide), /chart_json|Size/);
assert.match(read("src/components/merch/EventMerchDetail.tsx"), /MerchSizeGuideModal/);
assert.ok(exists("src/app/host/merchandise/size-charts/page.tsx"));

// --- Product reviews render ---
const hostReviews = "src/app/host/merchandise/reviews/page.tsx";
const adminReviews = "src/app/admin/merchandise/reviews/page.tsx";
assert.ok(exists(hostReviews), `missing ${hostReviews}`);
assert.ok(exists(adminReviews), `missing ${adminReviews}`);
assert.match(read(hostReviews), /review|reply/i);
assert.match(read("src/components/merch/EventMerchDetail.tsx"), /review/i);

// --- Sponsor-branded merch renders ---
const sponsorMark = "src/components/merch/SponsorBrandedMark.tsx";
assert.ok(exists(sponsorMark), `missing ${sponsorMark}`);
assert.match(read(sponsorMark), /export function SponsorBrandedMark/);
assert.match(read("src/components/merch/MerchProductCard.tsx"), /SponsorBrandedMark/);
assert.match(read("src/components/merch/EventMerchCard.tsx"), /MerchProductCard/);
assert.ok(exists("src/components/merch/EventMerchHero.tsx"));
assert.ok(exists("src/components/merch/MerchCartSummary.tsx"));
assert.ok(exists("src/components/merch/MerchFilterChips.tsx"));
assert.ok(exists("src/components/merch/MerchFallbackVisual.tsx"));
assert.match(read("src/app/events/[slug]/merch/page.tsx"), /EventMerchHero|MerchCartSummary|Official event merch/i);
assert.match(storefront, /sponsor|is_sponsor_branded/i);

// --- POD admin/host UI renders ---
const hostPod = "src/app/host/merchandise/print-on-demand/page.tsx";
const adminPod = "src/app/admin/merchandise/print-on-demand/page.tsx";
assert.ok(exists(hostPod), `missing ${hostPod}`);
assert.ok(exists(adminPod), `missing ${adminPod}`);
assert.match(read(hostPod), /print-on-demand|POD|Print on demand/i);
assert.match(read(adminPod), /print-on-demand|POD|Print on demand/i);

// --- Revenue report renders ---
const hostRevenue = "src/app/host/merchandise/revenue/page.tsx";
const adminRevenue = "src/app/admin/merchandise/revenue/page.tsx";
assert.ok(exists(hostRevenue), `missing ${hostRevenue}`);
assert.ok(exists(adminRevenue), `missing ${adminRevenue}`);
assert.match(read(hostRevenue), /revenue|export|discount_impact/i);
assert.match(read(adminRevenue), /revenue|export/i);

// --- Abandoned cart demo / cart recover surface ---
const cartPage = "src/app/dashboard/cart/page.tsx";
assert.ok(exists(cartPage), `missing ${cartPage}`);
const cart = read(cartPage);
assert.match(cart, /fetchBuyerCart|Resume checkout|merch cart/i);
assert.match(cart, /DashboardShell/);
assert.match(read("src/lib/merch-api.ts"), /\/dashboard\/cart/);

// --- Post-event drop renders (storefront labels + product flags) ---
assert.match(storefront, /Post-event drop|is_post_event_drop|coming_soon/);
assert.match(read(storefrontDetail), /access_locked|Vault|Exclusive|Locked|Unlocked/i);

// --- Vault-exclusive locked/unlocked states ---
assert.match(storefront, /access_locked|Vault exclusive|teaser_only/);
assert.match(read(storefrontDetail), /access_locked|Locked|Exclusive/);

// --- Fan Passport badge appears ---
const badgesPage = "src/app/dashboard/badges/page.tsx";
const passportPublic = "src/components/passport/FanPassportPublicClient.tsx";
assert.ok(exists(badgesPage), `missing ${badgesPage}`);
assert.ok(exists(passportPublic), `missing ${passportPublic}`);
assert.match(read(badgesPage), /fetchMyBadges|earned/);
assert.match(read(passportPublic), /PassportStampGrid|MerchProofSection|badges|merch_proof/);
assert.ok(exists("src/components/passport/PassportStampCard.tsx"));
assert.ok(exists("src/components/passport/FanPassportHero.tsx"));
assert.match(read("src/components/passport/FanPassportCard.tsx"), /top_badges|badge/i);

// --- Mobile works (responsive breakpoints on merch surfaces) ---
assert.match(storefront, /sm:|md:|lg:/);
assert.match(checkout, /lg:hidden|sm:|md:/);
assert.match(read("src/components/merch/EventMerchDetail.tsx"), /md:hidden|sm:|lg:/);

// --- Dark mode works on merch / passport cards ---
assert.match(read("src/components/passport/FanPassportCard.tsx"), /dark:/);
assert.match(read("src/app/layout.tsx"), /ThemeProvider/);
assert.ok(exists("src/lib/theme.ts"));
assert.ok(exists("src/components/theme/ThemeToggle.tsx"));

// --- Host merch hub + settings ---
assert.ok(exists("src/app/host/merchandise/page.tsx"));
assert.ok(exists("src/components/merch/host/HostStorefrontSettingsCard.tsx"));
assert.match(
  read("src/components/merch/host/HostStorefrontSettingsCard.tsx"),
  /storefront|visibility/i,
);
assert.ok(exists("src/app/host/merchandise/new/page.tsx"));
assert.match(read("src/app/host/merchandise/new/page.tsx"), /HostMerchProductForm|MerchProductForm|studio/);
assert.match(read("src/components/merch/host/HostMerchProductForm.tsx"), /MerchFormStepper|MerchVariantsEditor|MerchStickyActions/);
assert.ok(exists("src/components/merch/host/form/MerchFormStepper.tsx"));
assert.ok(exists("src/components/merch/host/form/MerchVariantsEditor.tsx"));
assert.match(read("src/app/host/merchandise/page.tsx"), /Add product|Shipping zones|Size charts|Discount/);

// --- Host shipping zones UI ---
const shippingZones = "src/app/host/merchandise/shipping-zones/page.tsx";
assert.ok(exists(shippingZones), `missing ${shippingZones}`);
const zonesPage = read(shippingZones);
assert.match(zonesPage, /fetchHostShippingZones|Create shipping zone|flat_fee|Archive/i);
assert.match(read("src/lib/merch-api.ts"), /\/host\/merchandise\/shipping-zones/);
assert.match(read("src/app/host/merchandise/page.tsx"), /shipping-zones/);

console.log("merch-smoke: ok");
