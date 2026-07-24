/**
 * Public /merch-guide educational page smoke.
 * Run: npm run test:merch-page
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
  "src/app/merch-guide/page.tsx",
  "src/components/marketing/merch/MerchView.tsx",
  "src/components/marketing/merch/content.ts",
  "src/components/marketing/merch/MerchHowItWorksSection.tsx",
  "src/components/marketing/merch/MerchFaqSection.tsx",
  "src/app/merch/page.tsx",
]) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const guidePage = read("src/app/merch-guide/page.tsx");
const content = read("src/components/marketing/merch/content.ts");
const view = read("src/components/marketing/merch/MerchView.tsx");

assert.match(guidePage, /buildPageMetadata|merchGuideSeo/);
assert.match(guidePage, /MerchView/);
assert.match(guidePage, /faqPageJsonLd/);
assert.match(guidePage, /merch-guide|merchGuideSeo/);

assert.match(content, /MERCH_GUIDE_PATH = "\/merch-guide"/);
assert.match(content, /Merch that moves with the moment/);
assert.match(content, /id: "how-it-works"|#how-it-works/);
assert.match(view, /MerchHowItWorksSection/);
assert.match(view, /Learn how merch works/);
assert.match(view, /href="#how-it-works"/);

assert.doesNotMatch(content, /coming soon|placeholder|lorem ipsum/i);
assert.doesNotMatch(view, /lorem ipsum/i);
assert.doesNotMatch(content, /\d+%/);

// Marketplace remains at /merch (no educational takeover)
const marketplacePage = read("src/app/merch/page.tsx");
assert.match(marketplacePage, /MerchMarketplaceView/);
assert.doesNotMatch(marketplacePage, /MerchView/);

const nav = read("src/components/layout/headerNav.ts");
assert.match(nav, /href: "\/merch-guide"/);
assert.match(nav, /label: "Merch [Gg]uide"/);
assert.match(nav, /href: "\/merch"/);
assert.match(nav, /label: "Shop"/);

const footer = read("src/components/layout/SiteFooter.tsx");
assert.match(footer, /href: "\/merch-guide"/);
assert.match(footer, /href: "\/merch"/); // Discover → marketplace
assert.match(footer, /label: "Shop"/);

const sitemap = read("src/app/sitemap.ts");
assert.match(sitemap, /\/merch-guide/);
assert.match(sitemap, /\/merch/);
assert.match(sitemap, /\/merch\/drops/);
assert.match(sitemap, /\/merch\/vault/);

assert.match(
  read("src/components/marketing/for-hosts/content.ts"),
  /\/merch-guide/,
);
assert.match(
  read("src/components/marketing/for-fans/content.ts"),
  /\/merch-guide/,
);
assert.match(
  read("src/lib/faq/faq-content.ts"),
  /\[Merch guide\]\(\/merch-guide\)/,
);
assert.match(read("src/lib/help-quick-links.ts"), /href: "\/merch-guide"/);
assert.match(read("src/app/help/page.tsx"), /href="\/merch-guide"/);
assert.match(
  read("src/components/pricing/PricingSections.tsx"),
  /href="\/merch-guide"/,
);
assert.match(
  read("src/lib/legal/refund-policy-content.tsx"),
  /href="\/merch-guide"/,
);

console.log("merch-page-smoke: ok (/merch-guide)");
