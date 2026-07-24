/**
 * Phase 1A SEO smoke — sitewide Organization/WebSite, Product, eventStatus.
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

const layout = read("src/app/layout.tsx");
assert.match(layout, /siteGraphJsonLd/);
assert.match(layout, /JsonLdScript/);

const siteGraph = read("src/lib/seo/site-graph.ts");
assert.match(siteGraph, /#organization/);
assert.match(siteGraph, /#website/);
assert.match(siteGraph, /EVENTS_SEARCH_ACTION_TEMPLATE/);
assert.match(siteGraph, /\/events\?q=\{search_term_string\}/);
assert.match(
  siteGraph.match(/export const EVENTS_SEARCH_ACTION_TEMPLATE[\s\S]*?;/)?.[0] ||
    "",
  /\/events\?q=\{search_term_string\}/,
);
assert.doesNotMatch(
  siteGraph.match(/export const EVENTS_SEARCH_ACTION_TEMPLATE[\s\S]*?;/)?.[0] ||
    "",
  /\/events\/search/,
);

const jsonld = read("src/lib/seo/jsonld.tsx");
assert.match(jsonld, /websiteIdRef/);
assert.doesNotMatch(jsonld, /"@type": "WebSite"/);

const merchMeta = read("src/lib/seo/merch-metadata.ts");
assert.match(merchMeta, /Product/);
assert.match(merchMeta, /SoldOut/);
assert.match(merchMeta, /isMerchProductSchemaEligible/);

const merchPage = read("src/app/merch/[slug]/page.tsx");
assert.match(merchPage, /merchProductJsonLd/);
assert.match(merchPage, /breadcrumbJsonLd/);

const eventMeta = read("src/lib/seo/event-metadata.ts");
assert.match(eventMeta, /eventStatusSchemaUrl/);
assert.match(eventMeta, /EventScheduled/);
assert.match(eventMeta, /EventCancelled/);
assert.match(eventMeta, /EventPostponed|no first-class|do not invent/i);

assert.ok(exists("src/lib/seo/phase1a.test.ts"));

// Entity breadcrumbs
assert.match(read("src/app/u/[username]/page.tsx"), /breadcrumbJsonLd/);
assert.match(read("src/app/sponsors/[slug]/page.tsx"), /breadcrumbJsonLd/);
assert.match(read("src/app/f/[username]/page.tsx"), /breadcrumbJsonLd/);

console.log("seo-phase1a-smoke: ok");
