/**
 * Homepage / public marketing refresh smoke.
 * Run: npm run test:home-refresh
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

const home = read("src/app/page.tsx");
assert.match(home, /HomeForFans/);
assert.match(home, /HomeBlogTeaser/);
assert.match(home, /HomeLegacyCta/);
assert.match(home, /HomePadeyaPicks/);
assert.match(home, /HomeBrowseTaxonomy/);
assert.match(home, /loadHomepagePublicData|HomeNearbyEventsSection/);
assert.match(home, /brand\.tagline/);
assert.match(home, /Explore events/);
assert.match(home, /Create event|Become a host/);
assert.doesNotMatch(home, /HomeTrustSafety/);
assert.doesNotMatch(home, /HomeLegacyShowcase|HomeLoyalty|HomeHowItWorks|HomeHostTools/);
assert.doesNotMatch(home, /coming soon/i);
assert.ok(!exists("src/components/home/HomeTrustSafety.tsx"), "HomeTrustSafety should be removed");
assert.match(read("src/components/home/HomeForFans.tsx"), /\/for-fans/);
if (exists("src/components/home/HomeForHosts.tsx")) {
  assert.match(read("src/components/home/HomeForHosts.tsx"), /\/for-hosts/);
}

for (const rel of [
  "src/components/home/HomeForFans.tsx",
  "src/components/home/HomeBlogTeaser.tsx",
  "src/components/home/HomeLegacyCta.tsx",
]) {
  assert.ok(exists(rel), `missing ${rel}`);
  assert.doesNotMatch(read(rel), /coming soon/i);
  assert.doesNotMatch(read(rel), /Afrobeats Night Live|DJ Maze|Ada Okoro/);
}

const header = read("src/components/layout/headerNav.ts");
for (const href of ["/events", "/hosts", "/fans", "/merch"]) {
  assert.match(header, new RegExp(href.replace("/", "\\/")));
}
assert.match(header, /SPONSORSHIP_MARKETPLACE_PATH/);
assert.match(header, /RESOURCES_NAV/);
assert.match(header, /label: "Shop"/);
for (const href of ["/blog", "/support", "/pricing", "/for-hosts", "/for-fans", "/merch-guide"]) {
  assert.match(header, new RegExp(href.replace("/", "\\/")));
}
assert.match(read("src/components/layout/SiteHeader.tsx"), /PUBLIC_NAV|HeaderUserMenu|HeaderResourcesDropdown/);

const footer = read("src/components/layout/SiteFooter.tsx");
assert.match(footer, /href: "\/fans"/);
for (const href of [
  "/about",
  "/pricing",
  "/faq",
  "/for-hosts",
  "/for-fans",
  "/terms",
  "/privacy",
  "/refund-policy",
  "/ticket-policy",
  "/community-guidelines",
  "/safety",
  "/support",
  "/help",
  "/report",
  "/accessibility",
]) {
  assert.match(footer, new RegExp(href.replace("/", "\\/")));
}
assert.match(footer, /label: "Safety"/);
assert.match(footer, /label: "Support"/);
assert.match(footer, /label: "Help"/);
assert.match(footer, /brand\.tagline/);

assert.match(read("src/app/about/page.tsx"), /Fan Passport|Legacy/);
assert.match(read("src/app/pricing/page.tsx"), /Fee on sales|platform fees/i);
assert.match(
  read("src/components/support/SupportGuidedFlow.tsx"),
  /fans, hosts, and visitors/i,
);

console.log("home-refresh-smoke: ok");
