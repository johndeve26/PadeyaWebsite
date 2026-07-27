/**
 * Phase 0A SEO smoke — structural + policy checks.
 * Run: npm run test:seo
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

// --- Core policy modules ---
assert.ok(exists("src/lib/seo/env-policy.ts"));
assert.ok(exists("src/lib/seo/noindex.ts"));
assert.ok(exists("src/lib/seo/canonical-path.ts"));

const envPolicy = read("src/lib/seo/env-policy.ts");
assert.match(envPolicy, /LIVE_SITE_ORIGIN = "https:\/\/padeya\.com"/);
assert.match(envPolicy, /isProductionSeoEnvironment/);
assert.match(envPolicy, /shouldIndexEnvironment/);
assert.match(envPolicy, /getCanonicalSiteOrigin/);
assert.match(envPolicy, /vercel\.app/);
assert.match(envPolicy, /trycloudflare\.com/);
assert.match(envPolicy, /smartlancedesigns\.com/);
assert.match(envPolicy, /X_ROBOTS_NOINDEX/);

const site = read("src/lib/seo/site.ts");
assert.match(site, /rootSeoMetadataFields/);
assert.match(site, /getCanonicalSiteOrigin/);
assert.match(site, /metadataBase/);

const layout = read("src/app/layout.tsx");
assert.match(layout, /metadataBase/);
assert.match(layout, /rootSeoMetadataFields/);
assert.match(layout, /\/icons\/icon-48\.png/);
assert.match(layout, /sizes:\s*"48x48"/);

const legacyRedirects = read("src/lib/seo/legacy-redirects.ts");
assert.match(legacyRedirects, /buildAppRedirects/);
assert.match(legacyRedirects, /member-register/);
assert.match(legacyRedirects, /WWW_HOST/);
assert.ok(exists("src/lib/seo/legacy-redirects.ts"));

const nextConfig = read("next.config.ts");
assert.match(nextConfig, /buildAppRedirects/);
assert.doesNotMatch(nextConfig, /destination:\s*["']\/["']\s*,\s*permanent:\s*true,\s*\/\/\s*404/);

const robots = read("src/app/robots.ts");
assert.match(robots, /shouldIndexEnvironment/);
assert.match(robots, /disallow:\s*\[/);
assert.match(robots, /"\/"/); // non-prod disallow all
assert.match(robots, /\/sponsor\//);
assert.match(robots, /\/connect\//);
assert.match(robots, /\/messages\//);
assert.match(robots, /\/events\/\*\/checkout/);
assert.match(robots, /\/checkout\//);
assert.match(robots, /\/team\/invite\//);
assert.match(robots, /\/demo/);
assert.match(robots, /padeya\.com|getCanonicalSiteOrigin/);

const middleware = read("src/middleware.ts");
assert.match(middleware, /X-Robots-Tag/);
assert.match(middleware, /X_ROBOTS_NOINDEX/);
assert.match(middleware, /shouldIndexEnvironment/);
assert.match(middleware, /events.*checkout/);
assert.match(middleware, /merch.*hosts.*checkout/);

// Private layout noindex coverage
const privateLayouts = [
  "src/app/admin/layout.tsx",
  "src/app/dashboard/layout.tsx",
  "src/app/host/layout.tsx",
  "src/app/sponsor/layout.tsx",
  "src/app/connect/layout.tsx",
  "src/app/messages/layout.tsx",
  "src/app/staff/layout.tsx",
  "src/app/ambassador/layout.tsx",
  "src/app/events/[slug]/checkout/layout.tsx",
  "src/app/merch/hosts/[username]/checkout/layout.tsx",
  "src/app/support/tickets/layout.tsx",
  "src/app/team/invite/layout.tsx",
  "src/app/reset-password/layout.tsx",
  "src/app/login/page.tsx",
  "src/app/register/page.tsx",
  "src/app/forgot-password/page.tsx",
];

for (const rel of privateLayouts) {
  assert.ok(exists(rel), `missing ${rel}`);
  const src = read(rel);
  assert.match(
    src,
    /privateAreaMetadata|NOINDEX_ROBOTS|noIndex:\s*true|index:\s*false/,
    `${rel} must set noindex metadata`,
  );
}

const eventMeta = read("src/lib/seo/event-metadata.ts");
assert.match(eventMeta, /password_protected/);
assert.match(eventMeta, /unlisted/);
assert.match(eventMeta, /Password-protected event/);
assert.match(eventMeta, /isEventSeoIndexable/);

const sitemapFilter = read("src/lib/seo/sitemap-filter.ts");
assert.match(sitemapFilter, /listed/);

console.log("seo-phase0a-smoke: ok");
