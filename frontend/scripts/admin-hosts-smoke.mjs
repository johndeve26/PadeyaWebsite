/**
 * Admin Hosts page — names + host-related actions.
 * Run: node scripts/admin-hosts-smoke.mjs
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

const page = read("src/app/admin/hosts/page.tsx");
assert.match(page, /host_display_name/);
assert.match(page, /hostLabel/);
assert.match(page, /View owner/);
assert.match(page, /Dropdown/);
assert.match(page, /Legacy reputation/);
assert.match(page, /View owner account/);
assert.match(page, /Approve/);
assert.match(page, /Reject/);
assert.doesNotMatch(page, /cell: \(v\) => \(\s*<span[^>]*>\{v\.host_id\}/);

const types = read("src/lib/types/lifecycle.ts");
assert.match(types, /host_display_name\?:/);
assert.match(types, /owner_user_id\?:/);
assert.match(types, /events_count\?:/);

console.log("admin-hosts-smoke: ok");
