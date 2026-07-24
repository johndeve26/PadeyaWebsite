/**
 * Phase 1B SEO smoke — faceted nav, location hubs, image alts.
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

const searchPage = read("src/app/events/search/page.tsx");
assert.match(searchPage, /noIndex:\s*searchPolicy\.noIndex|noIndex:\s*true/);
assert.match(searchPage, /canonicalPath/);
assert.match(searchPage, /EVENTS_FACET_CANONICAL_PATH|canonicalPath:\s*searchPolicy/);

const eventsPage = read("src/app/events/page.tsx");
assert.match(eventsPage, /generateMetadata/);
assert.match(eventsPage, /hasEventsFacetQuery/);

const facet = read("src/lib/seo/facet-policy.ts");
assert.match(facet, /EVENTS_FACET_QUERY_KEYS/);
assert.match(facet, /hasEventsFacetQuery/);

const eligibility = read("src/lib/seo/hub-eligibility.ts");
assert.match(eligibility, /HUB_ELIGIBILITY/);
assert.match(eligibility, /force_index/);
assert.match(eligibility, /force_noindex/);
assert.match(eligibility, /isLocationInSitemap/);
assert.match(eligibility, /isCityCategoryInSitemap/);

const sitemap = read("src/app/sitemap.ts");
assert.match(sitemap, /isLocationInSitemap/);
assert.match(sitemap, /isCityCategoryInSitemap/);
assert.match(sitemap, /buildHubInventoryFromEvents/);

const locationHub = read("src/lib/discovery/location-hub-page.tsx");
assert.match(locationHub, /evaluateLocationHubEligibility|evaluateCityCategoryHubEligibility/);
assert.match(locationHub, /introContent|locationHubIntroParagraph/);

assert.match(read("src/lib/seo/image-alt.ts"), /eventCoverAlt/);
assert.match(read("src/components/events/EventPublicView.tsx"), /eventCoverAlt/);
assert.match(
  read("src/components/merch/marketplace/MerchProductDetailView.tsx"),
  /merchImageAlt/,
);
assert.match(
  read("src/components/sponsors/SponsorBrandProfileHero.tsx"),
  /sponsorLogoAlt/,
);

assert.ok(exists("src/lib/seo/phase1b.test.ts"));

const mig = path.join(
  root,
  "..",
  "backend",
  "alembic",
  "versions",
  "20260724_0141_location_seo_fields.py",
);
assert.ok(fs.existsSync(mig), `location SEO migration missing at ${mig}`);

console.log("seo-phase1b-smoke: ok");
