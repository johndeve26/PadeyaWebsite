/**
 * Smoke checks for rich sponsor demo seed wiring (static).
 * Run: node scripts/sponsor-demo-smoke.mjs
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const backend = path.join(root, "..", "backend");

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

function readBackend(rel) {
  return fs.readFileSync(path.join(backend, rel), "utf8");
}

const seed = readBackend("app/demo/sponsor_demo_seed.py");
assert.match(seed, /NeonPalm Drinks/);
assert.match(seed, /korawave-pay/);
assert.match(seed, /campuswave/);
assert.match(seed, /novaskin-beauty/);
assert.match(seed, /pulseframe-media/);
assert.match(seed, /assert_sponsor_demo_seed_allowed/);
assert.match(seed, /PAYSTACK_REF_PREFIX/);
assert.match(seed, /DEMO-/);

const cli = readBackend("scripts/seed_sponsor_demo_data.py");
assert.match(cli, /Seeding fictional sponsor demo data only/);

const paths = read("src/lib/sponsor-marketplace-paths.ts");
assert.match(paths, /SPONSORSHIP_MARKETPLACE_PATH/);

const directory = read("src/components/sponsors/SponsorBrandDirectory.tsx");
assert.match(directory, /SponsorDirectoryCardView/);

const dirCard = read("src/components/sponsors/SponsorDirectoryCard.tsx");
assert.match(dirCard, /use_logo_fallback/);
assert.match(dirCard, /sponsored_events_count/);
assert.match(dirCard, /View partnership profile/);

const profileView = read("src/components/sponsors/PublicSponsorProfileView.tsx");
const cards = read("src/components/sponsors/SponsorPublicProfileCards.tsx");
assert.match(cards, /SponsorPublicSponsoredEventCard/);
assert.match(cards, /View event/);
assert.match(cards, /linked_sponsored_events_count/);
assert.match(profileView, /Sponsored events & placements/);
assert.match(profileView, /SponsorPublicSponsoredEventCard/);

const portfolio = readBackend("app/demo/sponsor_demo_portfolio.py");
assert.match(portfolio, /SPONSOR_EVENT_PACKS/);
assert.match(portfolio, /neon-nights-lekki/);
assert.match(portfolio, /digital-payments-meetup/);

const publicSlugs = [
  "neonpalm-drinks",
  "korawave-pay",
  "novaskin-beauty",
  "pulseframe-media",
];
for (const slug of publicSlugs) {
  assert.match(seed, new RegExp(slug));
  assert.ok(
    fs.existsSync(path.join(root, "src/app/sponsors/[slug]/page.tsx")),
    "sponsor profile route",
  );
}

for (const slug of [
  "neonpalm-drinks",
  "korawave-pay",
  "jollof-republic",
  "novaskin-beauty",
  "pulseframe-media",
]) {
  assert.ok(
    fs.existsSync(path.join(root, "public/demo/sponsors", `${slug}.svg`)),
    `missing logo ${slug}.svg`,
  );
}

const routes = [
  "src/app/sponsors/[slug]/page.tsx",
  "src/app/sponsor/page.tsx",
  "src/app/sponsor/campaigns/page.tsx",
  "src/app/sponsor/saved/page.tsx",
  "src/app/sponsor/deals/page.tsx",
  "src/app/sponsor/reports/page.tsx",
  "src/app/admin/sponsors/page.tsx",
  "src/app/admin/sponsorship-deals/page.tsx",
  "src/app/sponsorships/page.tsx",
];
for (const rel of routes) {
  assert.ok(fs.existsSync(path.join(root, rel)), `missing route ${rel}`);
}

console.log("sponsor-demo-smoke: ok");
