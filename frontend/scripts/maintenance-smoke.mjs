/**
 * Maintenance & platform status — structural smoke checks.
 * Run: npm run test:maintenance
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

const requiredFiles = [
  "src/lib/maintenance-api.ts",
  "src/lib/maintenance-read-only.ts",
  "src/components/maintenance/MaintenanceBanner.tsx",
  "src/components/maintenance/MaintenanceGate.tsx",
  "src/components/maintenance/SectionMaintenanceNotice.tsx",
  "src/app/maintenance/page.tsx",
  "src/app/admin/platform/maintenance/page.tsx",
  "src/app/admin/platform/maintenance/history/page.tsx",
  "src/app/admin/platform/maintenance/notifications/page.tsx",
];

for (const rel of requiredFiles) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const api = read("src/lib/maintenance-api.ts");
assert.match(api, /\/admin\/platform\/maintenance/);
assert.match(api, /\/maintenance\/status|fetchPublicMaintenanceStatus/);
assert.match(api, /createMaintenanceSchedule|createMaintenanceBypass|testMaintenanceNotification/);

const adminPage = read("src/app/admin/platform/maintenance/page.tsx");
assert.match(adminPage, /Global mode|MODE_OPTIONS|patchMaintenanceSettings/);
assert.match(adminPage, /Create schedule|Generate bypass/);
assert.match(adminPage, /Sections/);

const notifications = read(
  "src/app/admin/platform/maintenance/notifications/page.tsx",
);
assert.match(notifications, /testMaintenanceNotification|Test sent/);

const banner = read("src/components/maintenance/MaintenanceBanner.tsx");
assert.match(banner, /Scheduled maintenance begins|undergoing maintenance/);

const gate = read("src/components/maintenance/MaintenanceGate.tsx");
assert.match(gate, /\/maintenance/);
assert.match(gate, /mode !== "active"|mode === "active"/);

const publicPage = read("src/app/maintenance/page.tsx");
assert.match(publicPage, /fetchPublicMaintenanceStatus/);
assert.doesNotMatch(publicPage, /BrandLogo/);

const layout = read("src/app/layout.tsx");
assert.match(layout, /MaintenanceBanner/);
assert.match(layout, /MaintenanceGate/);

const nav = read("src/lib/nav/workspace.ts");
assert.match(nav, /\/admin\/platform\/maintenance/);
assert.match(nav, /admin\.maintenance\.view/);

const readOnly = read("src/lib/maintenance-read-only.ts");
assert.match(readOnly, /isWriteBlocked|writeControlProps/);
assert.match(readOnly, /read_only/);

console.log("maintenance smoke OK");
