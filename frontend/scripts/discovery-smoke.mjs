/**
 * Discovery / location / Pàdéyá Picks smoke checks — no browser required.
 * Run: npm run test:discovery
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

/** Mirror of resolvePadeyaPicks (admin first, then ordered fallback) for unit checks. */
function resolvePadeyaPicks(adminPicks, fallbackPool = [], limit = 2) {
  const picked = [];
  const seen = new Set();
  for (const event of adminPicks) {
    if (!event?.id || seen.has(event.id)) continue;
    seen.add(event.id);
    picked.push(event);
    if (picked.length >= limit) return picked;
  }
  for (const event of fallbackPool) {
    if (!event?.id || seen.has(event.id)) continue;
    seen.add(event.id);
    picked.push(event);
    if (picked.length >= limit) break;
  }
  return picked;
}

// --- Files exist ---
for (const rel of [
  "src/components/discovery/LocationFilterBar.tsx",
  "src/components/discovery/LocationSelector.tsx",
  "src/components/discovery/LocationChips.tsx",
  "src/components/discovery/LocationLandingHero.tsx",
  "src/components/discovery/LocationStats.tsx",
  "src/components/discovery/RelatedLocations.tsx",
  "src/components/discovery/PadeyaPicksSection.tsx",
  "src/components/discovery/FeaturedPlacementCard.tsx",
  "src/components/discovery/LocationLandingClient.tsx",
  "src/components/layout/MarketplaceBreadcrumbs.tsx",
  "src/lib/discovery/padeya-picks.ts",
  "src/lib/marketplace-breadcrumbs.ts",
]) {
  assert.ok(exists(rel), `missing ${rel}`);
}

// --- Location filter renders in discovery ---
const filterBar = read("src/components/discovery/LocationFilterBar.tsx");
assert.match(filterBar, /LocationSelector/);
assert.match(filterBar, /LocationChips/);
assert.match(filterBar, /Where do you want to go/);

const discoveryView = read("src/components/discovery/EventDiscoveryView.tsx");
assert.match(discoveryView, /LocationFilterBar/);
assert.match(discoveryView, /PadeyaPicksSection/);
assert.match(discoveryView, /location_kind/);
assert.match(discoveryView, /setLocationFilter/);
// Cascade is primary; legacy City select only when cascade is not shown.
assert.match(discoveryView, /locationFilterValue/);
assert.match(discoveryView, /setLocationFilter/);

const locationLandingLib = read("src/lib/discovery/location-landing.ts");
assert.match(locationLandingLib, /relatedLocationCandidates/);
assert.match(locationLandingLib, /siblings/);
assert.match(locationLandingLib, /ancestors/);
assert.doesNotMatch(
  locationLandingLib,
  /lekki.*victoria-island.*ikeja/,
  "related locations must not hardcode Lagos padding as primary source",
);

// --- Location landing: breadcrumbs + picks + related ---
const landing = read("src/components/discovery/LocationLandingClient.tsx");
assert.match(landing, /MarketplaceBreadcrumbs/);
assert.match(landing, /LocationLandingHero/);
assert.match(landing, /PadeyaPicksSection/);
assert.match(landing, /RelatedLocations|DiscoveryBrowseSection/);
assert.match(landing, /resolvePadeyaPicks/);
assert.match(landing, /siblingLocations|cityLinks|related/);
assert.match(landing, /\$\{kind\}_page|placementContext/);
assert.match(landing, /items=\{crumbs\}/);

const crumbsLib = read("src/lib/marketplace-breadcrumbs.ts");
assert.match(crumbsLib, /buildLocationTrail/);

const hubPage = read("src/lib/discovery/location-hub-page.tsx");
assert.match(hubPage, /buildLocationTrail/);
assert.match(hubPage, /LocationLandingClient/);

// --- Pàdéyá Picks section: empty hides; layout for up to 2 ---
const picksSection = read("src/components/discovery/PadeyaPicksSection.tsx");
assert.match(picksSection, /events\.slice\(0, 2\)/);
assert.match(picksSection, /if \(!picks\.length\) return null/);
assert.match(picksSection, /FeaturedPlacementCard/);
assert.match(picksSection, /Primary Spotlight|spotlight/);

const picksLib = read("src/lib/discovery/padeya-picks.ts");
assert.match(picksLib, /export function resolvePadeyaPicks/);
assert.match(picksLib, /limit = 2/);
assert.match(picksLib, /adminPicks/);
assert.match(picksLib, /fallbackPool/);

const homePicks = read("src/components/home/HomePadeyaPicks.tsx");
assert.match(homePicks, /resolvePadeyaPicks/);
assert.match(homePicks, /PadeyaPicksSection/);
assert.match(homePicks, /placementContext: "homepage"/);

// --- Behavioral: resolvePadeyaPicks prefers admin, fills to 2, empty → [] ---
const admin = [
  { id: "a1", title: "Admin One" },
  { id: "a2", title: "Admin Two" },
  { id: "a3", title: "Admin Three" },
];
const pool = [
  { id: "f1", title: "Fallback One" },
  { id: "f2", title: "Fallback Two" },
  { id: "a1", title: "Dup Admin" },
];

assert.deepEqual(
  resolvePadeyaPicks([], [], 2).map((e) => e.id),
  [],
  "empty admin + empty pool → empty (section should hide)",
);

assert.deepEqual(
  resolvePadeyaPicks([], pool, 2).map((e) => e.id),
  ["f1", "f2"],
  "fallback fills when no admin placements",
);

assert.deepEqual(
  resolvePadeyaPicks(admin, pool, 2).map((e) => e.id),
  ["a1", "a2"],
  "admin picks preferred and capped at 2",
);

assert.deepEqual(
  resolvePadeyaPicks([{ id: "a1", title: "Only" }], pool, 2).map((e) => e.id),
  ["a1", "f1"],
  "partial admin fills remaining from fallback",
);

assert.deepEqual(
  resolvePadeyaPicks([{ id: "a1" }, { id: "a1" }], pool, 2).map((e) => e.id),
  ["a1", "f1"],
  "duplicate admin ids are ignored",
);

console.log("discovery-ui-smoke: ok");
