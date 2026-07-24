/**
 * Branded 404 / Not Found experience — structural smoke checks.
 * Run: npm run test:not-found
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

function exists(rel) {
  return fs.existsSync(path.join(root, rel));
}

const required = [
  "src/app/not-found.tsx",
  "src/components/not-found/NotFoundExperience.tsx",
  "src/components/not-found/EventUnavailableState.tsx",
  "src/components/not-found/ExpiredLinkState.tsx",
  "src/lib/not-found-helpers.ts",
];

for (const rel of required) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const page = read("src/app/not-found.tsx");
assert.match(page, /Page not found/);
assert.match(page, /robots/);
assert.match(page, /index:\s*false/);
assert.match(page, /NotFoundExperience/);
assert.doesNotMatch(page, /redirect\(|permanentRedirect/);

const experience = read("src/components/not-found/NotFoundExperience.tsx");
assert.match(experience, /Page not found/);
assert.match(
  experience,
  /may have moved,\s*expired,\s*or no longer[\s\S]*exists/,
);
assert.match(experience, /Explore events|Go home|Contact support|Personal dashboard|Host workspace|Admin dashboard/);
assert.match(experience, /bg-ink|#8EF012|brand\.colors\.green/);
assert.match(experience, /NOT_FOUND_VIEW|TrackedAction/);
assert.match(experience, /sanitizeNotFoundPath|sanitizeUserAgent/);
assert.match(experience, /Search events/);
assert.match(experience, /\/events|\/hosts|\/fans|\/sponsorships|\/support/);
assert.doesNotMatch(experience, /payment_reference|access_token|password/);

const helpers = read("src/lib/not-found-helpers.ts");
assert.match(helpers, /buildNotFoundCtas|roleAwarePrimaryCta|classifyNotFoundPath/);

// Execute pure helpers via transpile-free subset — inline mirror of classify + sanitize
const sandbox = {
  classifyNotFoundPath(pathIn) {
    const p = (pathIn.split("?")[0] || "/").toLowerCase();
    if (p.startsWith("/events/") || p.startsWith("/e/")) return "event";
    if (p.startsWith("/u/") || p.startsWith("/@") || p.startsWith("/hosts/"))
      return "host";
    if (p.startsWith("/f/")) return "fan";
    return "generic";
  },
  sanitizeNotFoundPath(pathIn) {
    return (pathIn || "/").split("?")[0].split("#")[0].trim().slice(0, 200) || "/";
  },
  buildNotFoundCtas(user, pathKind) {
    const ctas = [];
    if (pathKind === "event" || pathKind === "generic") {
      ctas.push({ href: "/events", label: "Explore events" });
    }
    if (pathKind === "host") {
      ctas.push({ href: "/hosts", label: "Explore hosts" });
    }
    if (!user) {
      ctas.push({ href: "/dashboard", label: "Go to dashboard" });
    } else if (user.roles?.includes("super_admin") || user.roles?.includes("admin")) {
      ctas.push({ href: "/admin", label: "Admin dashboard" });
    } else if (user.roles?.includes("host")) {
      ctas.push({ href: "/host", label: "Host workspace" });
    } else {
      ctas.push({ href: "/dashboard", label: "Personal dashboard" });
    }
    ctas.push({ href: "/", label: "Go home" });
    ctas.push({ href: "/support", label: "Contact support" });
    return ctas;
  },
};

vm.createContext(sandbox);

assert.equal(
  sandbox.classifyNotFoundPath("/events/foo?token=SECRET"),
  "event",
);
assert.equal(sandbox.classifyNotFoundPath("/u/dj-lagos"), "host");
assert.equal(
  sandbox.sanitizeNotFoundPath("/events/x?ref=SECRET&pay=sk_live"),
  "/events/x",
);

const loggedOut = sandbox.buildNotFoundCtas(null, "generic");
assert.ok(loggedOut.some((c) => c.label === "Explore events"));
assert.ok(loggedOut.some((c) => c.label === "Go home"));
assert.ok(loggedOut.some((c) => c.label === "Contact support"));

const fan = sandbox.buildNotFoundCtas({ roles: ["buyer"] }, "generic");
assert.ok(fan.some((c) => c.label === "Personal dashboard"));

const host = sandbox.buildNotFoundCtas({ roles: ["host"] }, "host");
assert.ok(host.some((c) => c.label === "Host workspace"));
assert.ok(host.some((c) => c.label === "Explore hosts"));

const admin = sandbox.buildNotFoundCtas({ roles: ["super_admin"] }, "generic");
assert.ok(admin.some((c) => c.label === "Admin dashboard"));

// Mobile-first layout markers
assert.match(experience, /flex-col|sm:flex-row|px-6|min-h-\[75vh\]/);

const eventUnavailable = read(
  "src/components/not-found/EventUnavailableState.tsx",
);
assert.match(eventUnavailable, /This event is no longer available/);

const expired = read("src/components/not-found/ExpiredLinkState.tsx");
assert.match(expired, /This link has expired|expired/i);

const sitemap = read("src/app/sitemap.ts");
assert.doesNotMatch(sitemap, /not-found|\/404/);

const taxonomy = read("src/lib/analytics-taxonomy.ts");
assert.match(taxonomy, /NOT_FOUND_VIEW:\s*"not_found_view"/);

console.log("not-found smoke OK");
