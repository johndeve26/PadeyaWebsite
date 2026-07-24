/**
 * Phase 0B SEO smoke — SSR entity SEO + soft-404 fixes.
 * Run via: npm run test:seo
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

// Host Legacy SSR
const hostPage = read("src/app/u/[username]/page.tsx");
assert.doesNotMatch(hostPage, /^["']use client["']/m);
assert.match(hostPage, /generateMetadata/);
assert.match(hostPage, /notFound\(\)/);
assert.match(hostPage, /buildHostMetadataFromPage|hostLegacyJsonLd/);
assert.match(hostPage, /LegacyPublicClient/);
assert.ok(exists("src/app/u/[username]/LegacyPublicClient.tsx"));

const hostMeta = read("src/lib/seo/host-metadata.ts");
assert.match(hostMeta, /\/u\//);
assert.match(hostMeta, /ProfilePage/);
assert.match(hostMeta, /Organization/);
assert.doesNotMatch(hostMeta, /public_email/);

// Sponsor SSR
const sponsorPage = read("src/app/sponsors/[slug]/page.tsx");
assert.doesNotMatch(sponsorPage, /^["']use client["']/m);
assert.match(sponsorPage, /generateMetadata/);
assert.match(sponsorPage, /notFound\(\)/);
assert.match(sponsorPage, /buildSponsorMetadata|sponsorProfileJsonLd/);
assert.doesNotMatch(sponsorPage, /Alert tone="danger"/);

const sponsorMeta = read("src/lib/seo/sponsor-metadata.ts");
assert.match(sponsorMeta, /ProfilePage/);
assert.match(sponsorMeta, /Organization/);

// Sponsorships marketplace
const sponsorshipsPage = read("src/app/sponsorships/page.tsx");
assert.doesNotMatch(sponsorshipsPage, /^["']use client["']/m);
assert.match(sponsorshipsPage, /sponsorshipsIndexMetadata|metadata/);
assert.match(sponsorshipsPage, /SponsorshipsMarketplaceClient/);
assert.ok(exists("src/app/sponsorships/SponsorshipsMarketplaceClient.tsx"));

const hostsMarketplace = read("src/app/sponsorships/hosts/page.tsx");
assert.match(hostsMarketplace, /sponsorshipHostsIndexMetadata|metadata/);

// Events soft 404
const eventPage = read("src/app/events/[slug]/page.tsx");
assert.match(eventPage, /if \(!event\) notFound\(\)/);

// Merch soft 404
const merchPage = read("src/app/merch/[slug]/page.tsx");
assert.match(merchPage, /if \(!product\) notFound\(\)/);
assert.match(merchPage, /initialProduct/);

const merchView = read(
  "src/components/merch/marketplace/MerchProductDetailView.tsx",
);
assert.match(merchView, /initialProduct/);
assert.doesNotMatch(merchView, /Merch not found/);

// Fan passport
const fanPage = read("src/app/f/[username]/page.tsx");
assert.match(fanPage, /buildFanMetadata/);
assert.match(fanPage, /fanPassportJsonLd/);
const fanMeta = read("src/lib/seo/fan-metadata.ts");
assert.match(fanMeta, /Person/);
assert.match(fanMeta, /unlisted|noIndex|isFanPassportIndexable/);

console.log("seo-phase0b-smoke: ok");
