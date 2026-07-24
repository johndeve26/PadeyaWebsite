/**
 * Lightweight CTA / route smoke for /for-hosts and /for-fans marketing pages.
 * Complements vitest content checks.
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
  "src/app/for-hosts/page.tsx",
  "src/app/for-fans/page.tsx",
  "src/components/marketing/for-hosts/ForHostsView.tsx",
  "src/components/marketing/for-fans/ForFansView.tsx",
  "src/components/marketing/for-hosts/content.ts",
  "src/components/marketing/for-fans/content.ts",
  "src/components/marketing/for-fans/PassportPreview.tsx",
  "src/components/marketing/for-fans/FansBenefitsSection.tsx",
  "src/components/marketing/for-hosts/HostsToolsSection.tsx",
  "src/components/marketing/MarketingAudienceHero.tsx",
  "src/components/marketing/MarketingFaq.tsx",
]) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const hostsPage = read("src/app/for-hosts/page.tsx");
const fansPage = read("src/app/for-fans/page.tsx");
assert.match(hostsPage, /buildPageMetadata|forHostsSeo/);
assert.match(hostsPage, /faqPageJsonLd/);
assert.match(fansPage, /buildPageMetadata|forFansSeo/);
assert.match(fansPage, /faqPageJsonLd/);

const hostsContent = read("src/components/marketing/for-hosts/content.ts");
const fansContent = read("src/components/marketing/for-fans/content.ts");

for (const href of [
  "/host/events/new",
  "/host/onboarding",
  "/support",
  "/pricing",
  "/hosts",
  "/events",
]) {
  assert.match(hostsContent, new RegExp(href.replace(/[/?]/g, "\\$&")));
}

for (const href of [
  "/events",
  "/register?next=/dashboard/passport",
  "/support",
  "/fans",
  "/connect",
  "/dashboard/passport",
]) {
  assert.match(fansContent, new RegExp(href.replace(/[/?]/g, "\\$&")));
}

assert.match(hostsContent, /How do I create an event\?/);
assert.match(hostsContent, /How do payouts work\?/);
assert.match(fansContent, /What is Fan Passport\?/);
assert.match(fansContent, /What is Fan Connect\?/);
assert.doesNotMatch(hostsContent, /coming soon/i);
assert.doesNotMatch(fansContent, /coming soon/i);

const footer = read("src/components/layout/SiteFooter.tsx");
assert.match(footer, /\/for-hosts/);
assert.match(footer, /\/for-fans/);

const homeHosts = read("src/components/home/HomeForHosts.tsx");
const homeFans = read("src/components/home/HomeForFans.tsx");
assert.match(homeHosts, /\/for-hosts/);
assert.match(homeFans, /\/for-fans/);

const home = read("src/app/page.tsx");
assert.match(home, /HomeForFans/);
// Host marketing lives via Legacy / Create event CTAs; HomeForHosts component remains available.
assert.match(home, /HomeLegacyCta|\/for-hosts|Create event/);

const sitemap = read("src/app/sitemap.ts");
assert.match(sitemap, /\/for-hosts/);
assert.match(sitemap, /\/for-fans/);
assert.match(sitemap, /\/merch-guide/);
assert.match(sitemap, /\/merch/);

console.log("for-audience-pages-smoke: ok");
