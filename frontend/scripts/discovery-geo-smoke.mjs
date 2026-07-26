/**
 * Homepage + /events SSR / geolocation progressive enhancement smoke.
 * Run: node scripts/discovery-geo-smoke.mjs
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

// --- Homepage SSR public data ---
const home = read("src/app/page.tsx");
assert.match(home, /loadHomepagePublicData/);
assert.match(home, /HomePadeyaPicks/);
assert.match(home, /initialEvents=\{data\.picks\}/);
assert.match(home, /HomeNearbyEventsSection/);
assert.match(home, /HomeDiscoveryRails/);
assert.match(home, /revalidate/);
assert.doesNotMatch(home, /await requestNearMe|await autoLocate/);

assert.ok(exists("src/lib/home/load-homepage-public.ts"));
assert.ok(exists("src/lib/events/public-server.ts"));
assert.ok(exists("src/lib/discovery/geo-session.ts"));
assert.ok(exists("src/lib/discovery/default-market.ts"));

const featured = read("src/components/home/FeaturedEvents.tsx");
assert.match(featured, /initialEvents/);
assert.match(featured, /Show events near me/);
assert.match(featured, /GEO_DECLINED_COPY|No location access\? No problem/);
assert.match(featured, /Choose your city|chooseCityCta/);
assert.match(featured, /Popular events/);
assert.match(featured, /Finding events near you/);
assert.doesNotMatch(featured, /setEvents\(null\).*loadTrending/);

const nearbySection = read("src/components/home/HomeNearbyEventsSection.tsx");
assert.match(nearbySection, /initialEvents/);
assert.match(nearbySection, /Popular events|defaultCityLabel/);

const geoSession = read("src/lib/discovery/geo-session.ts");
assert.match(geoSession, /GEO_DECLINED_SESSION_KEY/);
assert.match(geoSession, /markGeoDeclinedSession/);
assert.match(geoSession, /readGeoDeclinedSession/);
assert.match(geoSession, /No problem — you can still browse/);

const hook = read("src/hooks/useDiscoveryLocation.ts");
assert.match(hook, /readGeoDeclinedSession/);
assert.match(hook, /markGeoDeclinedSession/);
assert.match(hook, /declined/);
assert.match(hook, /noteDeclined/);

// --- /events SSR ---
const eventsPage = read("src/app/events/page.tsx");
assert.match(eventsPage, /fetchPublicEventsServer/);
assert.match(eventsPage, /initialEvents=\{events\}/);
// Geo/facet filters stay client-side so the RSC route remains ISR-cacheable.
assert.match(eventsPage, /Near-me|never SSR exact GPS|client-side/i);

const marketplace = read(
  "src/components/events/marketplace/EventsMarketplaceClient.tsx",
);
assert.match(marketplace, /initialEvents/);
assert.match(marketplace, /if \(initialEvents != null\) return/);
assert.match(marketplace, /declined/);
assert.match(marketplace, /No location access\? No problem/);
assert.match(marketplace, /proximityActive.*!declined|!declined/);

const connectSuggestions = read(
  "src/components/fan-connect/ConnectSuggestions.tsx",
);
assert.doesNotMatch(connectSuggestions, /NearbyLocationControls/);
assert.doesNotMatch(connectSuggestions, /useDiscoveryLocation/);

// --- Checkout always revalidates availability ---
const checkout = read("src/app/events/[slug]/checkout/page.tsx");
assert.match(checkout, /fetchPublicEvent\(params\.slug\)/);

console.log("discovery-geo-smoke: ok");
