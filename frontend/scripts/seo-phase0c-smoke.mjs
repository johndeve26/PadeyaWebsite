/**
 * Phase 0C SEO smoke — privacy-safe sitemap completeness.
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

const sitemap = read("src/app/sitemap.ts");
const filter = read("src/lib/seo/sitemap-filter.ts");

// Removed search landing from sitemap
assert.doesNotMatch(sitemap, /\/events\/search/);

// Canonical origin helper
assert.match(sitemap, /getCanonicalSiteOrigin/);

// New entity sources from public-safe APIs
assert.match(sitemap, /\/legacy\/discover\/hosts/);
assert.match(sitemap, /\/fans\?/);
assert.match(sitemap, /\/sponsors\/public\/directory/);
assert.match(sitemap, /\/u\/\$\{/);
assert.match(sitemap, /\/f\/\$\{/);
assert.match(sitemap, /\/sponsors\/\$\{/);
assert.match(sitemap, /\/fans/);
assert.match(sitemap, /\/ambassadors/);
assert.match(sitemap, /blog\/category/);
assert.match(sitemap, /blog\/tag/);
assert.match(sitemap, /blog\/author/);

// Privacy filters wired
assert.match(sitemap, /filterListedEventsForSitemap/);
assert.match(sitemap, /filterHostsForSitemap/);
assert.match(sitemap, /filterFansForSitemap/);
assert.match(sitemap, /filterSponsorsForSitemap/);
assert.match(sitemap, /filterMerchForSitemap/);
assert.match(sitemap, /sitemapLastModified/);
assert.match(sitemap, /collectNonEmptyBlogHubSlugs/);

// lastModified must not invent now for entities
assert.match(filter, /never invent/i);
assert.match(filter, /sitemapLastModified/);
assert.match(filter, /isForbiddenSitemapPath/);
assert.match(filter, /SITEMAP_FORBIDDEN/);

// Entity lastModified uses helper (not bare `now` fallback on events/merch)
assert.match(sitemap, /sitemapLastModified\(event\.updated_at/);
assert.match(sitemap, /sitemapLastModified\(item\.updated_at\)/);

assert.ok(
  fs.existsSync(path.join(root, "src/lib/seo/phase0c.test.ts")),
  "phase0c vitest file missing",
);

console.log("seo-phase0c-smoke: ok");
