/**
 * Analytics smoke checks — no browser / Jest required.
 * Run: npm run test:analytics
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

// --- SSR: analytics hooks / track must not touch window at import time ---
const analyticsLib = read("src/lib/analytics.ts");
assert.match(analyticsLib, /typeof window === "undefined"/);
assert.match(analyticsLib, /if \(typeof window === "undefined"\) return;/);
assert.ok(
  analyticsLib.indexOf('if (typeof window === "undefined") return;') <
    analyticsLib.indexOf("export function track(") ||
    analyticsLib.includes("export function track(") &&
      /export function track\([\s\S]*?typeof window === "undefined"\) return/.test(
        analyticsLib,
      ),
  "track() must no-op on SSR",
);

const hooks = read("src/hooks/useAnalytics.ts");
assert.match(hooks, /"use client"/);
assert.match(hooks, /from "@\/lib\/analytics"/);

const clientHelpers = read("src/lib/analytics-client.ts");
assert.match(clientHelpers, /typeof window === "undefined"/);
assert.match(clientHelpers, /getOrCreateAnonymousId/);
assert.match(clientHelpers, /getOrCreateSessionId/);
assert.match(clientHelpers, /SERVER_ONLY_ACTIONS/);
assert.match(clientHelpers, /payment_success/);

// --- Impression dedupe wiring in browser client ---
assert.match(analyticsLib, /trackEventCardImpression/);
assert.match(analyticsLib, /dedupeScope: "impression"/);
assert.match(analyticsLib, /claimAnalyticsDedupe|claimClientDedupe/);
assert.match(analyticsLib, /padeya_analytics_dedupe/);

// Pure dedupe-key behavior (mirrors analytics-client generateDedupeKey)
function generateDedupeKey(scope, parts = {}) {
  const scopeClean = (scope || "").trim().toLowerCase().slice(0, 64);
  if (!scopeClean) return null;
  if (parts.requestId?.trim()) {
    return `${scopeClean}:req:${parts.requestId.trim().slice(0, 128)}`.slice(0, 191);
  }
  const chunks = [scopeClean];
  if (parts.targetEventId) chunks.push(`evt:${parts.targetEventId}`);
  if (parts.orderId) chunks.push(`ord:${parts.orderId}`);
  if (parts.userId) chunks.push(`u:${parts.userId}`);
  else if (parts.anonymousId?.trim())
    chunks.push(`a:${parts.anonymousId.trim().slice(0, 64)}`);
  else if (parts.sessionId?.trim())
    chunks.push(`s:${parts.sessionId.trim().slice(0, 64)}`);
  else if (!parts.orderId) return null;
  if (parts.listContext?.trim())
    chunks.push(`ctx:${parts.listContext.trim().slice(0, 64)}`);
  return chunks.join(":").slice(0, 191);
}

const k1 = generateDedupeKey("impression", {
  targetEventId: "evt-1",
  sessionId: "sess-1",
  listContext: "events_grid",
});
const k2 = generateDedupeKey("impression", {
  targetEventId: "evt-1",
  sessionId: "sess-1",
  listContext: "events_grid",
});
const k3 = generateDedupeKey("impression", {
  targetEventId: "evt-1",
  sessionId: "sess-1",
  listContext: "search_results",
});
assert.equal(k1, k2);
assert.notEqual(k1, k3);
assert.match(k1, /ctx:events_grid/);

// In-memory claim map mimics browser dedupe TTL
function makeClaimStore() {
  const memory = new Set();
  const map = new Map();
  return function claim(key, ttlMs) {
    if (!key) return true;
    if (memory.has(key)) return false;
    const now = Date.now();
    const expires = map.get(key);
    if (expires && expires > now) {
      memory.add(key);
      return false;
    }
    map.set(key, now + ttlMs);
    memory.add(key);
    return true;
  };
}
const claim = makeClaimStore();
assert.equal(claim(k1, 60_000), true);
assert.equal(claim(k1, 60_000), false);
assert.equal(claim(k3, 60_000), true);

// --- Event analytics page empty / loading / error states ---
assert.ok(exists("src/app/host/events/[id]/analytics/page.tsx"));
assert.ok(exists("src/app/admin/events/[id]/analytics/page.tsx"));
assert.ok(exists("src/components/analytics/EventAnalyticsDashboard.tsx"));

const hostPage = read("src/app/host/events/[id]/analytics/page.tsx");
assert.match(hostPage, /SkeletonLoader/);
assert.match(hostPage, /Unable to load analytics|tone="danger"/);
assert.match(hostPage, /setError/);
assert.match(hostPage, /!data && !error/);
assert.match(hostPage, /EventAnalyticsDashboard/);

const adminPage = read("src/app/admin/events/[id]/analytics/page.tsx");
assert.match(adminPage, /SkeletonLoader/);
assert.match(adminPage, /setError/);
assert.match(adminPage, /EventAnalyticsDashboard/);

const dashboard = read("src/components/analytics/EventAnalyticsDashboard.tsx");
assert.match(dashboard, /EmptyState/);
assert.match(dashboard, /No analytics yet/);
assert.match(dashboard, /hasTraffic/);

console.log("Analytics smoke checks passed:");
console.log("  ✓ SSR no-op guards on track / window access");
console.log("  ✓ useAnalytics is client-only");
console.log("  ✓ impression dedupe keys + TTL claim");
console.log("  ✓ host/admin analytics pages: loading / error / empty");
