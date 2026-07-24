/**
 * Admin Runtime Settings UI — structural smoke checks.
 * Run: npm run test:runtime-settings
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
  "src/lib/runtime-settings-api.ts",
  "src/lib/runtime-settings-display.ts",
  "src/lib/runtime-settings-permissions.ts",
  "src/lib/runtime-settings.test.ts",
  "src/components/admin/runtime-settings/RuntimeSettingsDashboard.tsx",
  "src/components/admin/runtime-settings/RuntimeSettingsCategoryPage.tsx",
  "src/components/admin/runtime-settings/RuntimeSettingField.tsx",
  "src/components/admin/runtime-settings/SecretSettingField.tsx",
  "src/components/admin/runtime-settings/RuntimeSettingSourceBadge.tsx",
  "src/components/admin/runtime-settings/RuntimeSettingTestButton.tsx",
  "src/components/admin/runtime-settings/RuntimeSettingsAuditTable.tsx",
  "src/app/admin/settings/runtime/page.tsx",
  "src/app/admin/settings/runtime/[category]/page.tsx",
  "src/app/admin/settings/runtime/audit/page.tsx",
];

for (const rel of requiredFiles) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const api = read("src/lib/runtime-settings-api.ts");
assert.match(api, /\/admin\/settings\/runtime/);
assert.match(api, /method:\s*"PUT"/);
assert.match(api, /method:\s*"DELETE"/);
assert.match(api, /\/override/);
assert.match(api, /\/test/);
assert.match(api, /\/audit/);
assert.match(api, /masked_value/);
assert.doesNotMatch(api, /secret_plaintext|raw_secret/);

const display = read("src/lib/runtime-settings-display.ts");
assert.match(display, /Configured · ending in/);
assert.match(display, /Not configured/);
assert.match(display, /env_fallback/);
assert.match(display, /db_override/);
assert.match(display, /\/admin\/email\/settings/);
assert.match(display, /\/admin\/push\/settings/);

const secretField = read(
  "src/components/admin/runtime-settings/SecretSettingField.tsx",
);
assert.match(secretField, /Replace secret/);
assert.match(secretField, /formatSecretDisplay/);
assert.match(secretField, /type="password"/);
assert.doesNotMatch(secretField, /Show secret|type="text"/i);
assert.doesNotMatch(secretField, /\breveal\b/i);

const categoryPage = read(
  "src/components/admin/runtime-settings/RuntimeSettingsCategoryPage.tsx",
);
assert.match(categoryPage, /Open specialist editor/);
assert.match(categoryPage, /does not write a second copy/);
assert.match(categoryPage, /admin\.settings/);
assert.match(categoryPage, /Clear DB override|clearOverride/);
assert.match(categoryPage, /RuntimeSettingTestButton/);
assert.match(categoryPage, /runtime_setting_/);

const dashboard = read(
  "src/components/admin/runtime-settings/RuntimeSettingsDashboard.tsx",
);
assert.match(dashboard, /Permission denied/);
assert.match(dashboard, /RuntimeSettingTestButton/);
assert.match(dashboard, /RuntimeSettingSourceBadge/);
assert.match(dashboard, /dark:bg-surface/);

const perms = read("src/lib/runtime-settings-permissions.ts");
for (const code of [
  "admin.settings.view",
  "admin.settings.edit_runtime",
  "admin.settings.edit_secrets",
  "admin.settings.test_integrations",
  "admin.settings.view_system_status",
  "admin.settings.clear_overrides",
  "admin.settings.view_audit",
]) {
  assert.match(perms, new RegExp(code.replace(/\./g, "\\.")));
}

const nav = read("src/lib/nav/workspace.ts");
assert.match(nav, /href: "\/admin\/settings\/runtime"/);

const pushRedirect = read("src/app/admin/settings/push/page.tsx");
assert.match(pushRedirect, /\/admin\/settings\/runtime\/push/);

const field = read(
  "src/components/admin/runtime-settings/RuntimeSettingField.tsx",
);
assert.match(field, /restart_required/);
assert.match(field, /Clear DB override/);
assert.match(field, /Validation|validation_error/);

const themeTokens = [
  dashboard,
  categoryPage,
  secretField,
  field,
  read("src/components/admin/runtime-settings/RuntimeSettingSourceBadge.tsx"),
].join("\n");
assert.doesNotMatch(themeTokens, /#[0-9a-fA-F]{6}/);
assert.doesNotMatch(themeTokens, /purple|indigo-500|from-purple/);
assert.match(themeTokens, /text-heading|bg-card|border-border|text-muted-foreground/);

console.log("runtime-settings smoke OK");
