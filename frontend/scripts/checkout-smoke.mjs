/**
 * Checkout redesign smoke — purchase modes + stepped UI contracts.
 * Run: node scripts/checkout-smoke.mjs
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

const page = "src/app/events/[slug]/checkout/page.tsx";
assert.ok(exists(page), "checkout page missing");
const checkout = read(page);

assert.match(checkout, /CheckoutStepper/);
assert.match(checkout, /CheckoutTicketSelector/);
assert.match(checkout, /CheckoutPurchaseMode/);
assert.match(checkout, /CheckoutAttendeeDetails/);
assert.match(checkout, /Continue as guest|guest_buyer|Guest checkout/);
assert.match(checkout, /purchase_mode|purchaseMode/);
assert.ok(exists("src/app/checkout/claim/page.tsx"));
assert.match(read("src/app/checkout/claim/page.tsx"), /claimGuestOrder|Claim your tickets/);
assert.match(read("src/lib/commerce-api.ts"), /guest_buyer_email|claimGuestOrder/);
assert.match(checkout, /fixed inset-x-0 bottom-0/);
assert.match(checkout, /lg:sticky/);
assert.match(checkout, /Complete free order|Get free/);
assert.match(checkout, /validateMerchDiscount|merch_discount/);
assert.match(checkout, /ShippingAddressForm/);
assert.match(checkout, /cannot_checkout|checkoutBlocked/);

// Checkout must always re-fetch the public event (never trust cached list/detail).
assert.match(checkout, /fetchPublicEvent\(params\.slug\)/);
assert.match(checkout, /useEffect/);

assert.ok(exists("src/components/checkout/CheckoutStepper.tsx"));
assert.ok(exists("src/components/checkout/CheckoutTicketSelector.tsx"));
assert.ok(exists("src/components/checkout/CheckoutPurchaseMode.tsx"));
assert.ok(exists("src/components/checkout/CheckoutAttendeeDetails.tsx"));
assert.ok(exists("src/components/checkout/types.ts"));

const types = read("src/components/checkout/types.ts");
assert.match(types, /validateAttendeeDrafts/);
assert.match(types, /"self".*"other".*"group"|PurchaseMode/);

const api = read("src/lib/commerce-api.ts");
assert.match(api, /purchase_mode/);
assert.match(api, /recipient_email|send_ticket_to_recipient/);

const success = read("src/app/checkout/success/page.tsx");
assert.match(success, /gift|recipient|My Tickets/i);
assert.match(success, /Confirming payment|payment is confirmed|My Tickets/i);

const failed = read("src/app/checkout/failed/page.tsx");
assert.match(failed, /payloads|card data|gateway/i);

console.log("checkout-smoke: ok");
