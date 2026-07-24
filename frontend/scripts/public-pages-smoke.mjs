/**
 * Public pages / legal / system routes smoke.
 * Run: npm run test:public-pages
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

const pages = [
  "src/app/pricing/page.tsx",
  "src/app/about/page.tsx",
  "src/app/for-hosts/page.tsx",
  "src/app/for-fans/page.tsx",
  "src/app/merch/page.tsx",
  "src/app/merch-guide/page.tsx",
  "src/app/contact/page.tsx",
  "src/app/faq/page.tsx",
  "src/app/terms/page.tsx",
  "src/app/privacy/page.tsx",
  "src/app/cookies/page.tsx",
  "src/app/refund-policy/page.tsx",
  "src/app/ticket-policy/page.tsx",
  "src/app/community-guidelines/page.tsx",
  "src/app/safety/page.tsx",
  "src/app/report/page.tsx",
  "src/app/accessibility/page.tsx",
  "src/app/unauthorized/page.tsx",
  "src/app/account/appeal/page.tsx",
  "src/app/events/today/page.tsx",
  "src/app/events/search/page.tsx",
  "src/app/checkout/success/page.tsx",
  "src/app/checkout/failed/page.tsx",
  "src/app/error.tsx",
  "src/app/global-error.tsx",
  "src/app/hosts/[slug]/page.tsx",
  "src/app/passport/[username]/page.tsx",
];

for (const rel of pages) {
  assert.ok(exists(rel), `missing ${rel}`);
}

for (const rel of [
  "src/app/terms/page.tsx",
  "src/app/privacy/page.tsx",
  "src/app/cookies/page.tsx",
  "src/app/refund-policy/page.tsx",
  "src/app/ticket-policy/page.tsx",
  "src/app/community-guidelines/page.tsx",
  "src/app/accessibility/page.tsx",
]) {
  const src = read(rel);
  assert.match(src, /buildPageMetadata/);
  assert.match(src, /LegalDocument/);
  assert.doesNotMatch(
    src,
    /legal review recommended|AI-generated|not legal advice|policy draft/i,
  );
}

for (const rel of [
  "src/app/safety/page.tsx",
  "src/app/report/page.tsx",
  "src/app/pricing/page.tsx",
]) {
  const src = read(rel);
  assert.match(src, /buildPageMetadata/);
  assert.doesNotMatch(
    src,
    /legal review recommended|AI-generated|not legal advice|policy draft/i,
  );
}

{
  const pricing = read("src/app/pricing/page.tsx");
  assert.match(pricing, /fetchPublicPricing|PricingTiers|FeeCategoriesSection/);
  assert.ok(exists("src/components/pricing/PricingSections.tsx"));
  assert.ok(exists("src/lib/legal/pricing-content.tsx"));
}

assert.ok(exists("src/lib/legal/terms-content.tsx"));
assert.ok(exists("src/lib/legal/privacy-content.tsx"));
assert.ok(exists("src/lib/legal/platform-relationship.tsx"));
assert.match(read("src/components/legal/LegalDocument.tsx"), /LegalToc/);

assert.match(read("src/app/unauthorized/page.tsx"), /noIndex:\s*true/);
assert.match(read("src/app/account/appeal/page.tsx"), /noIndex:\s*true/);
assert.match(read("src/app/checkout/success/layout.tsx"), /noIndex:\s*true/);
assert.match(read("src/app/checkout/failed/layout.tsx"), /noIndex:\s*true/);

assert.match(read("src/app/events/today/page.tsx"), /isTodayEvent|Today/);
assert.match(read("src/app/events/search/page.tsx"), /EventsMarketplaceClient/);

assert.match(
  read("src/app/checkout/success/page.tsx"),
  /payment payloads|raw payment/i,
);
assert.match(read("src/app/checkout/failed/page.tsx"), /payloads|card data/i);

assert.match(read("src/app/account/appeal/page.tsx"), /SuspendedAccountPage/);
assert.match(read("src/app/hosts/[slug]/page.tsx"), /redirect\(`\/u\//);
assert.match(read("src/app/passport/[username]/page.tsx"), /redirect\(`\/f\//);

const config = read("next.config.ts");
assert.match(config, /dashboard\/passport\/edit/);
assert.match(config, /dashboard\/ambassadors/);
assert.match(config, /admin\/sponsors/);

const footer = read("src/components/layout/SiteFooter.tsx");
for (const href of [
  "/about",
  "/pricing",
  "/blog",
  "/support",
  "/faq",
  "/contact",
  "/for-hosts",
  "/for-fans",
  "/merch",
  "/merch-guide",
  "/terms",
  "/privacy",
  "/cookies",
  "/refund-policy",
  "/ticket-policy",
  "/community-guidelines",
  "/safety",
  "/report",
  "/accessibility",
]) {
  assert.match(footer, new RegExp(href.replace("/", "\\/")));
}

assert.match(read("src/app/for-hosts/page.tsx"), /forHostsSeo|Host Events on Pàdéyá/);
assert.match(read("src/app/for-fans/page.tsx"), /forFansSeo|Discover Events on Pàdéyá/);
assert.match(read("src/app/merch/page.tsx"), /merchSeo|MerchMarketplaceView/);
assert.match(read("src/app/merch-guide/page.tsx"), /merchGuideSeo|MerchView|Merch that moves/);

console.log("public-pages-smoke: ok");
