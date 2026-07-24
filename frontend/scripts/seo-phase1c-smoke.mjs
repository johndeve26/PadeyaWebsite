/**
 * Phase 1C SEO smoke — GSC/Bing verification, GA consent, production smoke tooling.
 * Run via: npm run test:seo
 *
 * Live checks against padeya.com:
 *   SEO_BASE_URL=https://padeya.com node scripts/seo-production-smoke.mjs
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

assert.ok(exists("src/lib/seo/verification.ts"));
assert.ok(exists("src/lib/analytics-consent.ts"));
assert.ok(exists("src/lib/seo/production-checks.ts"));
assert.ok(exists("src/components/analytics/Ga4Script.tsx"));
assert.ok(exists("src/components/legal/OptionalAnalyticsConsentControls.tsx"));
assert.ok(exists("scripts/seo-production-smoke.mjs"));
assert.ok(exists("src/lib/seo/phase1c.test.ts"));
assert.ok(exists("../docs/SEO_LAUNCH_CHECKLIST.md"));

const verification = read("src/lib/seo/verification.ts");
assert.match(verification, /GOOGLE_SITE_VERIFICATION/);
assert.match(verification, /BING_SITE_VERIFICATION/);
assert.match(verification, /buildSiteVerificationMetadata/);
assert.match(verification, /msvalidate\.01/);

const site = read("src/lib/seo/site.ts");
assert.match(site, /buildSiteVerificationMetadata/);
assert.match(site, /verification/);

const layout = read("src/app/layout.tsx");
assert.match(layout, /seoRoot\.verification/);

const consent = read("src/lib/analytics-consent.ts");
assert.match(consent, /shouldLoadGa4/);
assert.match(consent, /ANALYTICS_CONSENT_STORAGE_KEY/);
assert.match(consent, /granted/);
assert.match(consent, /denied/);
assert.match(consent, /unset/);

const ga4 = read("src/components/analytics/Ga4Script.tsx");
assert.match(ga4, /shouldLoadGa4/);
assert.match(ga4, /isClientProductionSeoEnvironment/);
assert.match(ga4, /googletagmanager\.com\/gtag\/js/);

const provider = read("src/components/analytics/AnalyticsProvider.tsx");
assert.match(provider, /Ga4Script/);

const cookiesPage = read("src/app/cookies/page.tsx");
assert.match(cookiesPage, /OptionalAnalyticsConsentControls/);

const envExample = read(".env.example");
assert.match(envExample, /GOOGLE_SITE_VERIFICATION/);
assert.match(envExample, /BING_SITE_VERIFICATION/);
assert.match(envExample, /NEXT_PUBLIC_GA_MEASUREMENT_ID/);

const smoke = read("scripts/seo-production-smoke.mjs");
assert.match(smoke, /SEO_BASE_URL/);
assert.doesNotMatch(smoke, /from ["'].*\.ts["']/);
assert.match(smoke, /sitemap\.xml/);
assert.match(smoke, /robots\.txt/);
assert.match(smoke, /extractJsonLd|ld\+json/);
assert.match(smoke, /padeya\.com/);
assert.doesNotMatch(smoke, /SEO_BASE_URL\s*=\s*["']http:\/\/localhost/);

const pkg = JSON.parse(read("package.json"));
assert.match(pkg.scripts["test:seo"], /seo-phase1c-smoke/);
assert.ok(pkg.scripts["seo:production-smoke"]);

const checklist = read("../docs/SEO_LAUNCH_CHECKLIST.md");
assert.match(checklist, /Google Search Console/);
assert.match(checklist, /seo:production-smoke|seo-production-smoke/);
assert.match(checklist, /LCP/);
assert.match(checklist, /PageSpeed/);

console.log("seo-phase1c-smoke: ok");
