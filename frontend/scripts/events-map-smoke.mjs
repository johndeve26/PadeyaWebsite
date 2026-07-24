/**
 * Events Map View smoke checks — no browser required.
 * Run: node scripts/events-map-smoke.mjs
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
  "src/components/events/map/EventMapView.tsx",
  "src/components/events/map/EventMap.tsx",
  "src/components/events/map/EventMapMarker.tsx",
  "src/components/events/map/EventMapPreviewCard.tsx",
  "src/components/events/map/EventMapList.tsx",
  "src/components/events/map/EventViewSwitcher.tsx",
  "src/components/events/map/MapMobileBottomSheet.tsx",
  "src/components/events/map/event-map-card-chrome.ts",
  "src/lib/maps/provider.ts",
  "src/lib/maps/types.ts",
  "src/lib/maps/cluster.ts",
  "src/app/events/map/page.tsx",
]) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const switcher = read("src/components/events/map/EventViewSwitcher.tsx");
assert.match(switcher, /value: "map"/);
assert.match(switcher, /label: "Map"/);
assert.match(switcher, /desktopOnly: true/);
assert.match(switcher, /useEventsLgUp/);
assert.match(switcher, /MODES\.filter\(\(mode\) => isLgUp \|\| !mode\.desktopOnly\)/);
assert.doesNotMatch(switcher, /hidden lg:inline-flex/);
assert.match(switcher, /Grid/);
assert.match(switcher, /List/);
assert.match(switcher, /Calendar/);
assert.match(switcher, /bg-ink text-paper/);
assert.match(switcher, /bg-surface-elevated/);
assert.doesNotMatch(switcher, /text-accent/);

const lgHook = read("src/hooks/useEventsLgUp.ts");
assert.match(lgHook, /EVENTS_LG_MEDIA_QUERY/);
assert.match(lgHook, /useSyncExternalStore/);

const toolbar = read(
  "src/components/events/marketplace/EventsResultsToolbar.tsx",
);
assert.doesNotMatch(toolbar, /onOpenFilters/);
assert.doesNotMatch(toolbar, /Filters/);
assert.doesNotMatch(toolbar, /activeFilterCount/);
assert.doesNotMatch(toolbar, /text-accent/);
assert.match(toolbar, /EventsViewToggle/);

const listing = read("src/lib/events/marketplace-listing.ts");
assert.match(listing, /"map"/);
assert.match(listing, /EVENTS_DESKTOP_ONLY_VIEWS/);
assert.match(listing, /EVENTS_LG_MEDIA_QUERY/);
assert.match(listing, /min-width: 1024px/);
assert.match(listing, /clampEventsViewForViewport/);
assert.match(listing, /parseEventsView/);
assert.match(listing, /raw === "map"/);

const results = read("src/components/events/marketplace/EventsResults.tsx");
assert.match(results, /view === "map"/);
assert.match(results, /EventMapView/);

const client = read(
  "src/components/events/marketplace/EventsMarketplaceClient.tsx",
);
assert.match(client, /view === "map"/);
assert.match(client, /clampEventsViewForViewport/);
assert.match(client, /mapFilters/);
assert.match(client, /EventsFilterBar/);
assert.match(client, /EventsFilterDrawer/);
assert.match(client, /setDrawerOpen\(true\)/);
assert.match(client, /lg:hidden/);

const mapPage = read("src/app/events/map/page.tsx");
assert.match(mapPage, /permanentRedirect/);
assert.match(mapPage, /\/events\?view=map/);

const api = read("src/lib/events-api.ts");
assert.match(api, /fetchMapEvents/);
assert.match(api, /\/events\/map/);

const provider = read("src/lib/maps/provider.ts");
assert.match(provider, /detectMapProvider/);
assert.match(provider, /createMapController/);
assert.match(provider, /Mapbox|Leaflet|google/i);

const mapView = read("src/components/events/map/EventMapView.tsx");
assert.match(mapView, /Search this area/);
assert.match(mapView, /Use my location/);
assert.match(mapView, /No events in this area|EventMapList/);
assert.match(mapView, /mobilePane/);

const googleMaps = read("src/lib/google-maps.ts");
assert.match(googleMaps, /NEXT_PUBLIC_GOOGLE_MAPS_API_KEY/);
assert.match(googleMaps, /hasGoogleMapsApiKey/);

const list = read("src/components/events/map/EventMapList.tsx");
assert.doesNotMatch(list, /View event/);
assert.match(list, /eventMapCardChrome/);
assert.match(list, /eventMapPriceClass/);
assert.match(list, /href=\{href\}/);

const preview = read("src/components/events/map/EventMapPreviewCard.tsx");
assert.doesNotMatch(preview, /View event/);
assert.match(preview, /eventMapCardChrome/);
assert.match(preview, /eventMapPriceClass/);

const chrome = read("src/components/events/map/event-map-card-chrome.ts");
assert.match(chrome, /dark:bg-ink/);
assert.match(chrome, /border-primary/);
assert.match(chrome, /bg-surface-muted/);
assert.match(chrome, /text-primary-text dark:text-primary/);

console.log("events-map-smoke: ok");
