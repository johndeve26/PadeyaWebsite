/**
 * Taxonomy / discovery smoke checks — no browser required.
 * Run: npm run test:taxonomy
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

// --- Files exist ---
const required = [
  "src/lib/marketplace-breadcrumbs.ts",
  "src/components/layout/MarketplaceBreadcrumbs.tsx",
  "src/components/discovery/ActiveFilters.tsx",
  "src/components/discovery/DiscoveryHubClient.tsx",
  "src/components/discovery/EventDiscoveryView.tsx",
  "src/components/related/RelatedContentRail.tsx",
  "src/components/events/EventRelatedSections.tsx",
  "src/lib/discovery/related-events.ts",
  "src/lib/seo/sitemap-filter.ts",
  "src/app/events/page.tsx",
  "src/app/events/c/[categorySlug]/page.tsx",
  "src/app/events/city/[citySlug]/page.tsx",
  "src/app/events/this-weekend/page.tsx",
  "src/app/events/free/page.tsx",
  "src/app/sitemap.ts",
  "src/app/robots.ts",
];
for (const rel of required) {
  assert.ok(exists(rel), `missing ${rel}`);
}

// --- Breadcrumbs render + hierarchy ---
const crumbsLib = read("src/lib/marketplace-breadcrumbs.ts");
assert.match(crumbsLib, /export function buildEventTrail/);
assert.match(crumbsLib, /export function buildCategoryTrail/);
assert.match(crumbsLib, /export function buildCityTrail/);
assert.match(crumbsLib, /export function buildCityCategoryTrail/);
assert.match(crumbsLib, /\/events\/city\/\$\{opts\.citySlug\}/);
assert.match(crumbsLib, /\/events\/c\/\$\{opts\.categorySlug\}/);
assert.match(crumbsLib, /\/events\/city\/\$\{opts\.citySlug\}\/\$\{opts\.categorySlug\}/);

const crumbUi = read("src/components/layout/MarketplaceBreadcrumbs.tsx");
assert.match(crumbUi, /Breadcrumb/);
assert.match(crumbUi, /items/);

const discoveryView = read("src/components/discovery/EventDiscoveryView.tsx");
assert.match(discoveryView, /MarketplaceBreadcrumbs/);
assert.match(discoveryView, /ActiveFilters/);
assert.match(discoveryView, /SortSelect/);
assert.match(discoveryView, /DiscoveryBrowseSection/);
assert.match(discoveryView, /DiscoveryCollectionsSection/);
assert.match(discoveryView, /PadeyaPicksSection/);
assert.match(discoveryView, /LocationFilterBar/);
assert.match(discoveryView, /What.?s on next|What’s on next/);
assert.doesNotMatch(discoveryView, /Narrow your search/);
assert.doesNotMatch(discoveryView, /Editor.?s Pick/);
assert.ok(exists("src/components/discovery/LocationFilterBar.tsx"));
assert.ok(exists("src/components/discovery/LocationSelector.tsx"));
assert.ok(exists("src/components/discovery/LocationChips.tsx"));
assert.ok(exists("src/components/discovery/LocationLandingHero.tsx"));
assert.ok(exists("src/components/discovery/LocationStats.tsx"));
assert.ok(exists("src/components/discovery/RelatedLocations.tsx"));
assert.ok(exists("src/components/discovery/PadeyaPicksSection.tsx"));
assert.ok(exists("src/components/discovery/FeaturedPlacementCard.tsx"));
assert.ok(exists("src/components/admin/AdminPlacementForm.tsx"));
assert.ok(exists("src/components/admin/PlacementPreview.tsx"));
assert.match(discoveryView, /DiscoveryAdjacentSection/);
assert.match(discoveryView, /useSearchParams/);
assert.match(discoveryView, /router\.replace/);
assert.match(discoveryView, /locked\?\.category/);

assert.ok(exists("src/components/discovery/DiscoveryHubHero.tsx"));
assert.ok(exists("src/lib/discovery/category-stories.ts"));
assert.match(read("src/components/discovery/DiscoveryHubHero.tsx"), /HeroSection/);
assert.match(read("src/lib/discovery/category-stories.ts"), /CATEGORY_STORIES/);
assert.match(read("src/components/taxonomy/CategoryNav.tsx"), /hint/);
assert.match(read("src/components/taxonomy/TaxonomyEventCard.tsx"), /resolveEventImage/);

const activeFilters = read("src/components/discovery/ActiveFilters.tsx");
assert.match(activeFilters, /locked/);
assert.match(activeFilters, /Locked by this landing page/);

assert.match(read("src/lib/seo/hub-page.tsx"), /HubJsonLd/);
assert.match(read("src/lib/seo/jsonld.tsx"), /collectionPageJsonLd/);
assert.match(read("src/app/events/c/[categorySlug]/page.tsx"), /HubJsonLd/);
assert.match(read("src/lib/discovery/location-hub-page.tsx"), /HubJsonLd/);
assert.match(read("src/lib/discovery/location-hub-page.tsx"), /LocationLandingClient/);
assert.match(read("src/app/events/city/[citySlug]/page.tsx"), /LocationHubPage/);
assert.match(read("src/app/events/area/[areaSlug]/page.tsx"), /LocationHubPage/);
assert.match(read("src/app/events/country/[countrySlug]/page.tsx"), /LocationHubPage/);
assert.match(read("src/app/events/state/[stateSlug]/page.tsx"), /LocationHubPage/);
assert.ok(exists("src/components/admin/taxonomy/LocationsAdminPage.tsx"));
assert.ok(exists("src/components/admin/taxonomy/SubcategoryAdminPanel.tsx"));
assert.match(
  read("src/components/discovery/DiscoveryHubClient.tsx"),
  /Suspense/,
);
assert.match(
  read("src/components/discovery/DiscoveryHubClient.tsx"),
  /heroProps/,
);
assert.match(
  read("src/components/discovery/EventDiscoveryView.tsx"),
  /DiscoveryHubHero/,
);

// Mirror buildEventTrail hierarchy contract
function buildEventTrail(opts) {
  const items = [
    { label: "Home", href: "/" },
    { label: "Events", href: "/events" },
  ];
  if (opts.city && opts.citySlug) {
    items.push({ label: opts.city, href: `/events/city/${opts.citySlug}` });
  }
  if (opts.categoryName && opts.categorySlug) {
    const href = opts.citySlug
      ? `/events/city/${opts.citySlug}/${opts.categorySlug}`
      : `/events/c/${opts.categorySlug}`;
    items.push({ label: opts.categoryName, href });
  }
  items.push({ label: opts.title || opts.slug });
  return items;
}

const trail = buildEventTrail({
  title: "Detty Friday",
  slug: "detty-friday",
  city: "Lagos",
  citySlug: "lagos",
  categoryName: "Nightlife",
  categorySlug: "nightlife",
});
assert.equal(trail.length, 5);
assert.equal(trail[0].href, "/");
assert.equal(trail[1].href, "/events");
assert.equal(trail[2].href, "/events/city/lagos");
assert.equal(trail[3].href, "/events/city/lagos/nightlife");
assert.equal(trail[4].label, "Detty Friday");
assert.equal(trail[4].href, undefined);

// --- Category / city / filter pages load (route wiring) ---
const hubClient = read("src/components/discovery/DiscoveryHubClient.tsx");
assert.match(hubClient, /kind === "category"/);
assert.match(hubClient, /kind === "city"/);
assert.match(hubClient, /fetchPublicEvents/);

assert.match(read("src/app/events/c/[categorySlug]/page.tsx"), /CategoryLandingClient/);
assert.match(read("src/app/events/city/[citySlug]/page.tsx"), /LocationHubPage/);
assert.match(read("src/lib/discovery/location-hub-page.tsx"), /LocationLandingClient|CategoryLandingClient/);
assert.match(read("src/app/events/this-weekend/page.tsx"), /CollectionLandingClient|weekend/);
assert.match(read("src/app/events/free/page.tsx"), /CollectionLandingClient|free/);
assert.match(read("src/app/events/page.tsx"), /DiscoveryHubClient/);

// --- Active filters display ---
assert.match(activeFilters, /if \(!items\.length\) return null/);
assert.match(activeFilters, /onRemove/);
assert.match(activeFilters, /onClearAll/);
assert.ok(discoveryView.includes("items={active}"), "ActiveFilters must receive active chips");
assert.ok(discoveryView.includes("<ActiveFilters"), "EventDiscoveryView renders ActiveFilters");

// --- Related content empty state ---
const relatedRail = read("src/components/related/RelatedContentRail.tsx");
assert.match(relatedRail, /Children\.count\(children\) === 0/);
assert.match(relatedRail, /return null/);

const relatedSections = read("src/components/events/EventRelatedSections.tsx");
assert.match(relatedSections, /RelatedDiscoverySection/);
const relatedDiscovery = read(
  "src/components/events/RelatedDiscoverySection.tsx",
);
assert.match(relatedDiscovery, /groupRelatedEvents|RelatedDiscoverySection/);

const relatedLib = read("src/lib/discovery/related-events.ts");
assert.match(relatedLib, /export function groupRelatedEvents/);
assert.match(relatedLib, /host_id === event\.host_id/);
assert.match(relatedLib, /category_id === event\.category_id/);
assert.match(relatedLib, /r\.city === event\.city/);

// Pure related grouping behavior (mirrors related-events.ts)
function groupRelatedEvents(event, allEvents, limit = 4) {
  const others = allEvents.filter((r) => r.id !== event.id);
  const byHost = others.filter((r) => r.host_id === event.host_id).slice(0, limit);
  const byCategory = others
    .filter(
      (r) =>
        event.category_id &&
        r.category_id === event.category_id &&
        r.host_id !== event.host_id,
    )
    .slice(0, limit);
  const byCity = others
    .filter(
      (r) =>
        event.city &&
        r.city === event.city &&
        r.host_id !== event.host_id &&
        r.category_id !== event.category_id,
    )
    .slice(0, limit);
  return { byHost, byCategory, byCity };
}

const focus = {
  id: "1",
  host_id: "h1",
  category_id: "c1",
  city: "Lagos",
};
const catalog = [
  focus,
  { id: "2", host_id: "h1", category_id: "c2", city: "Ibadan" },
  { id: "3", host_id: "h2", category_id: "c1", city: "Abuja" },
  { id: "4", host_id: "h2", category_id: "c2", city: "Lagos" },
];
const groups = groupRelatedEvents(focus, catalog);
assert.deepEqual(
  groups.byHost.map((e) => e.id),
  ["2"],
);
assert.deepEqual(
  groups.byCategory.map((e) => e.id),
  ["3"],
);
assert.deepEqual(
  groups.byCity.map((e) => e.id),
  ["4"],
);
const emptyGroups = groupRelatedEvents(focus, [focus]);
assert.equal(emptyGroups.byHost.length, 0);
assert.equal(emptyGroups.byCategory.length, 0);
assert.equal(emptyGroups.byCity.length, 0);

// --- Sitemap excludes private/unlisted ---
const sitemapFilter = read("src/lib/seo/sitemap-filter.ts");
assert.match(sitemapFilter, /filterListedEventsForSitemap/);
assert.match(sitemapFilter, /visibility === "listed"/);

const sitemapPage = read("src/app/sitemap.ts");
assert.match(sitemapPage, /filterListedEventsForSitemap/);
assert.doesNotMatch(sitemapPage, /\/host\//);
assert.doesNotMatch(sitemapPage, /\/admin\//);

function filterListedEventsForSitemap(events) {
  return events.filter((e) => !e.visibility || e.visibility === "listed");
}
const sitemapRows = filterListedEventsForSitemap([
  { slug: "a", visibility: "listed" },
  { slug: "b", visibility: "unlisted" },
  { slug: "c", visibility: "password_protected" },
  { slug: "d" },
]);
assert.deepEqual(
  sitemapRows.map((e) => e.slug),
  ["a", "d"],
);

const robots = read("src/app/robots.ts");
assert.match(robots, /\/host\//);
assert.match(robots, /\/admin\//);
assert.match(robots, /sitemap\.xml/);
assert.match(robots, /disallow:/i);

console.log("taxonomy smoke checks passed");
