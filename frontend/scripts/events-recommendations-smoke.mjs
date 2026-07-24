#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const marketplace = fs.readFileSync(
  path.join(root, "src/components/events/marketplace/EventsMarketplaceClient.tsx"),
  "utf8",
);
const section = fs.readFileSync(
  path.join(root, "src/components/events/EventRecommendationsSection.tsx"),
  "utf8",
);
const api = fs.readFileSync(path.join(root, "src/lib/events-api.ts"), "utf8");

assert.match(marketplace, /Recommended for you/);
assert.match(marketplace, /fetchEventRecommendations/);
assert.match(section, /Not interested/);
assert.match(api, /\/events\/recommendations/);
assert.match(
  fs.readFileSync(
    path.join(root, "src/components/events/EventDetailRecommendationsRail.tsx"),
    "utf8",
  ),
  /event_detail_recommended/,
);

console.log("events-recommendations-smoke: ok");
