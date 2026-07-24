/**
 * Pricing page smoke — structure, fee categories, no draft/legal warnings.
 * Run: node scripts/pricing-smoke.mjs
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

const page = "src/app/pricing/page.tsx";
const sections = "src/components/pricing/PricingSections.tsx";
const content = "src/lib/legal/pricing-content.tsx";
const api = "src/lib/pricing-api.ts";

assert.ok(exists(page), "pricing page missing");
assert.ok(exists(sections), "PricingSections missing");
assert.ok(exists(content), "pricing-content missing");
assert.ok(exists(api), "pricing-api missing");

const pageSrc = read(page);
const sectionsSrc = read(sections);
const contentSrc = read(content);
const apiSrc = read(api);

assert.match(pageSrc, /buildPageMetadata/);
assert.match(pageSrc, /fetchPublicPricing/);
assert.match(pageSrc, /PricingTier/);
assert.match(pageSrc, /FeeCategoriesSection/);
assert.match(pageSrc, /BuyerFeesSection/);
assert.match(pageSrc, /HostEarningsSection/);
assert.match(pageSrc, /HighVolumeSection/);
assert.match(pageSrc, /PricingPlatformRelationship/);
assert.match(pageSrc, /PricingFaqSection/);
assert.doesNotMatch(
  pageSrc,
  /legal review recommended|AI-generated|not legal advice|policy draft|placeholder|TODO draft/i,
);

assert.match(sectionsSrc, /data-testid="pricing-tiers"/);
assert.match(sectionsSrc, /data-testid="fee-category-cards"/);
assert.match(sectionsSrc, /data-testid="fee-category-table"/);
assert.match(sectionsSrc, /data-testid="buyer-fees-section"/);
assert.match(sectionsSrc, /data-testid="host-earnings-section"/);
assert.match(sectionsSrc, /data-testid="custom-pricing-section"/);
assert.match(sectionsSrc, /Know what you earn before you sell/);
assert.match(sectionsSrc, /Buyer platform fee is paid by the buyer/);
assert.match(sectionsSrc, /Host net earnings/);
assert.match(sectionsSrc, /Explore events/);
assert.match(sectionsSrc, /Become a host/);
assert.match(sectionsSrc, /Contact support/);

assert.match(contentSrc, /Pàdéyá/);
assert.match(contentSrc, /may differ by host|may vary by host/i);
assert.match(contentSrc, /PRICING_FAQ/);
assert.match(contentSrc, /FALLBACK_FEE_CATEGORIES/);
assert.match(contentSrc, /Ticket sales/);
assert.match(contentSrc, /Merch sales/);
assert.match(contentSrc, /Vault sales/);
assert.match(contentSrc, /Buyer platform \/ service fee/);
assert.match(contentSrc, /Payment \/ fiat processing fee/);
assert.match(contentSrc, /Refund handling/);
assert.match(contentSrc, /High-volume \/ custom/);
assert.match(contentSrc, /Is Pàdéyá free for fans/);
assert.match(contentSrc, /Can different hosts have different fees/);
assert.match(contentSrc, /platform and marketplace/i);
assert.doesNotMatch(
  contentSrc,
  /legal review recommended|AI-generated|not legal advice|policy draft/i,
);

assert.match(apiSrc, /pricing\/public/);

// Mobile-friendly layout cues: grid + overflow table
assert.match(sectionsSrc, /sm:grid-cols-2|lg:grid-cols-3/);
assert.match(sectionsSrc, /overflow-x-auto/);

console.log("Pricing smoke checks passed:");
console.log("  ✓ /pricing page renders structure");
console.log("  ✓ pricing cards + fee categories");
console.log("  ✓ buyer fee + host earnings explanations");
console.log("  ✓ custom host pricing + platform relationship");
console.log("  ✓ no draft/legal warning text");
console.log("  ✓ public pricing API client wired");
