#!/usr/bin/env node
/**
 * Smoke: /events mount must not inject default price_max / lat=0 URL state.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const client = readFileSync(
  path.join(root, "src/components/events/marketplace/EventsMarketplaceClient.tsx"),
  "utf8",
);
const sync = readFileSync(
  path.join(root, "src/lib/events/events-url-sync.ts"),
  "utf8",
);

const checks = [
  [
    sync.includes("parseLatLngSearchParams") &&
      sync.includes("buildEventsListingHref"),
    true,
    "url-sync helpers exported",
  ],
  [client.includes("parseLatLngSearchParams"), true, "client uses safe lat/lng parse"],
  [client.includes("syncPriceToUrl"), true, "price URL sync is gated"],
  [client.includes("syncLocationToUrl"), true, "location URL sync is gated"],
  [
    /const lat = Number\(searchParams\.get\("lat"\)\)/.test(client),
    false,
    "no Number(null) lat seed",
  ],
];

let failed = 0;
for (const [value, expected, label] of checks) {
  const ok = Boolean(value) === expected;
  console.log(`${ok ? "ok" : "FAIL"} — ${label}`);
  if (!ok) failed += 1;
}

if (failed) {
  console.error(`events-mount-navigation-smoke: ${failed} failed`);
  process.exit(1);
}
console.log("events-mount-navigation-smoke: ok");
