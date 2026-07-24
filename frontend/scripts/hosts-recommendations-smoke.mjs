#!/usr/bin/env node
/**
 * Static smoke: /hosts recommendation integration strings.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const marketplace = fs.readFileSync(
  path.join(root, "src/components/hosts/HostsMarketplace.tsx"),
  "utf8",
);
const section = fs.readFileSync(
  path.join(
    root,
    "src/components/personal/command-center/HostRecommendationsSection.tsx",
  ),
  "utf8",
);
const hostsApi = fs.readFileSync(
  path.join(root, "src/lib/hosts-api.ts"),
  "utf8",
);

assert.match(marketplace, /Recommended for you/);
assert.match(marketplace, /sort=recommended|sortRecommended/);
assert.match(marketplace, /hosts_recommended_rail/);
assert.match(section, /Not interested/);
assert.match(section, /recordHostRecommendationImpressions/);
assert.match(hostsApi, /\/hosts\/recommendations\/impressions/);

console.log("hosts-recommendations-smoke: ok");
