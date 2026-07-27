/**
 * Domain + legacy redirect smoke (structural).
 * Run: node scripts/domain-redirects-smoke.mjs
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

const map = read("src/lib/seo/legacy-redirects.ts");
const cfg = read("next.config.ts");
const robots = read("src/app/robots.ts");
const sitemap = read("src/app/sitemap.ts");
const envPolicy = read("src/lib/seo/env-policy.ts");
const notFound = read("src/app/not-found.tsx");
const middleware = read("src/middleware.ts");

assert.match(envPolicy, /LIVE_SITE_ORIGIN = "https:\/\/padeya\.com"/);
assert.match(map, /WWW_HOST = "www\.padeya\.com"/);
assert.match(map, /wwwToApexRedirects|buildAppRedirects/);
assert.match(map, /member-register[\s\S]*\/register/);
assert.match(map, /member-login[\s\S]*\/login/);
assert.match(map, /LEGACY_NO_REDIRECT_PATHS/);
assert.doesNotMatch(map, /destination:\s*["']\/["']/); // no homepage redirects in map entries for WP

assert.match(cfg, /buildAppRedirects/);
assert.match(cfg, /legacy-redirects/);
// No second www→apex layer in middleware
assert.doesNotMatch(middleware, /www\.padeya\.com/);

assert.match(robots, /getCanonicalSiteOrigin/);
assert.match(robots, /sitemap:\s*`\$\{origin\}\/sitemap\.xml`/);
assert.doesNotMatch(robots, /www\.padeya\.com/);
assert.doesNotMatch(robots, /Disallow:\s*\/favicon/);
assert.doesNotMatch(robots, /Disallow:\s*\/icons/);

assert.match(sitemap, /getCanonicalSiteOrigin/);
assert.doesNotMatch(sitemap, /member-register|member-login/);
assert.doesNotMatch(sitemap, /www\.padeya\.com|smartlancedesigns/);

assert.match(notFound, /index:\s*false/);
assert.doesNotMatch(notFound, /redirect\(|permanentRedirect/);
assert.doesNotMatch(notFound, /canonical/);

// Favicon paths must not be blocked by domain redirects logic
assert.match(cfg, /images:|remotePatterns/);

console.log("domain-redirects-smoke: ok");
console.log("  ✓ www→apex map + next.config wiring");
console.log("  ✓ member-register→/register, member-login→/login");
console.log("  ✓ no middleware www duplicate");
console.log("  ✓ robots/sitemap apex-only; legacy auth not in sitemap");
console.log("  ✓ not-found remains noindex (no homepage redirect)");
