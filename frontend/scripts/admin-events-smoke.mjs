/**
 * Admin events review + flag UI smoke.
 * Run: node scripts/admin-events-smoke.mjs
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

const listPage = read("src/app/admin/events/page.tsx");
assert.match(listPage, /\/admin\/events\/\$\{e\.id\}\/review/);
assert.match(listPage, /Flag/);
assert.match(listPage, /flagEvent/);
assert.match(listPage, /clearEventFlag/);
assert.match(listPage, /admin_flagged/);
assert.match(listPage, /Flagged only/);

assert.ok(exists("src/app/admin/events/[id]/review/page.tsx"));
const detail = read("src/app/admin/events/[id]/review/page.tsx");
assert.match(detail, /approveEvent/);
assert.match(detail, /rejectEvent/);
assert.match(detail, /flagEvent/);
assert.match(detail, /pauseEvent/);
assert.match(detail, /Flag listing/);

const api = read("src/lib/events-api.ts");
assert.match(api, /\/events\/by-id\/\$\{id\}\/flag/);
assert.match(api, /\/events\/by-id\/\$\{id\}\/clear-flag/);

console.log("admin-events-smoke: ok");
