/**
 * Admin Users UI acceptance smoke (phase 14) — static source asserts.
 * Run: npm run test:admin-users
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

// --- Sidebar: Users for permitted admin; hidden without permission ---
const adminNav = read("src/lib/nav/workspace.ts");
assert.match(adminNav, /href: "\/admin\/users"/);
assert.match(adminNav, /label: "Users"/);
assert.match(adminNav, /permissions: \["admin\.users\.view"\]/);

const adminNavTest = read("src/lib/nav/admin-nav.test.ts");
assert.match(adminNavTest, /shows Users for admin\.users\.view/);
assert.match(adminNavTest, /hides Users without view permission/);
assert.match(adminNavTest, /includes Users in flat nav used by mobile drawer/);
assert.match(adminNavTest, /places Users immediately after Overview/);

const activeTest = read("src/lib/nav/workspace.active.test.ts");
assert.match(
  activeTest,
  /highlights Admin Users on list and nested detail routes/,
);
assert.match(activeTest, /resolves Users for admin user detail paths/);
assert.match(activeTest, /\/admin\/users\/abc-123/);

// --- /admin/users list: table, search, filters ---
const usersPage = read("src/app/admin/users/page.tsx");
assert.match(usersPage, /admin\.users\.view/);
assert.match(usersPage, /Permission denied/);
assert.match(usersPage, /DataTable/);
assert.match(usersPage, /FilterBar/);
assert.match(usersPage, /label="Search"/);
assert.match(usersPage, /label="Status"/);
assert.match(usersPage, /label="Role"/);
assert.match(usersPage, /EmptyState/);
assert.match(usersPage, /AdminUserSignalBadges/);
assert.match(usersPage, /fetchAdminUsers/);

// --- User detail: safe fields, tabs, no password/token UI ---
const detailPage = read("src/app/admin/users/[userId]/page.tsx");
assert.match(detailPage, /AdminUserDetailSections/);
assert.match(detailPage, /detail\.email/);
assert.match(detailPage, /requireReason/);
assert.match(detailPage, /Add note/);
assert.match(detailPage, /Add flag/);
assert.match(detailPage, /Mark under review|Suspend|Emergency: block login/);
assert.doesNotMatch(detailPage, /password_hash|access_token|refresh_token/);
assert.doesNotMatch(
  detailPage,
  /type=["']password["']|revealPassword|showPassword/,
);

const detailSections = read(
  "src/components/admin/AdminUserDetailSections.tsx",
);
assert.match(detailSections, /id: "overview"/);
assert.match(detailSections, /AdminUserActivityPanel|Platform activity/);
assert.match(detailSections, /id: "activity"/);
assert.match(detailSections, /id: "restrictions"/);
assert.match(detailSections, /id: "flags"/);
assert.match(detailSections, /id: "notes"/);
assert.match(detailSections, /id: "security"/);
assert.match(detailSections, /id: "audit"/);
assert.match(detailSections, /label="Email"/);
assert.match(detailSections, /detail\.email/);
assert.match(detailSections, /Safe account view/);
assert.match(
  detailSections,
  /Passwords, password hashes, session tokens/,
);
assert.doesNotMatch(detailSections, /password_hash|access_token/);

// --- Flag / note / status reason gates ---
assert.match(
  detailPage,
  /disabled=\{busy \|\| flagReason\.trim\(\)\.length < 3\}/,
);
assert.match(
  detailPage,
  /disabled=\{busy \|\| noteBody\.trim\(\)\.length < 3\}/,
);
assert.match(detailPage, /requireReason/);
assert.match(detailPage, /reasonLabel="Reason for suspension"|Reason for suspension/);
assert.match(detailPage, /resolveAdminUserFlag|dismissAdminUserFlag/);
assert.match(detailPage, /addAdminUserNote/);
assert.match(detailPage, /addAdminUserFlag/);
assert.match(detailPage, /suspendUser|markAdminUserUnderReview/);
assert.match(detailPage, /AdminUserRestrictionsPanel/);
assert.match(detailPage, /applyAdminUserRestrictions/);

assert.ok(exists("src/components/admin/AdminUserActivityPanel.tsx"));
const activityPanel = read("src/components/admin/AdminUserActivityPanel.tsx");
assert.match(activityPanel, /View details/);
assert.match(activityPanel, /fetchAdminUserActivityDetail/);
assert.match(activityPanel, /kind: "tickets"/);
assert.match(activityPanel, /kind: "orders"/);
assert.match(activityPanel, /kind: "reviews"/);
assert.match(activityPanel, /EmptyState/);
assert.match(activityPanel, /SkeletonLoader/);
assert.match(activityPanel, /Pagination/);
assert.match(activityPanel, /Drawer/);
assert.match(activityPanel, /Restricted/);
assert.doesNotMatch(activityPanel, /password_hash|access_token|raw_response/);

assert.ok(exists("src/components/admin/AdminUserBadges.tsx"));
assert.ok(exists("src/components/admin/AdminUserRestrictionsPanel.tsx"));
assert.ok(exists("src/components/ui/ConfirmAction.tsx"));
const confirm = read("src/components/ui/ConfirmAction.tsx");
assert.match(confirm, /requireReason/);

const restrictionsPanel = read(
  "src/components/admin/AdminUserRestrictionsPanel.tsx",
);
assert.match(restrictionsPanel, /Selective presets/);
assert.match(restrictionsPanel, /Emergency: full account block/);
assert.match(restrictionsPanel, /Apply restrictions/);
assert.match(restrictionsPanel, /Revoke/);

const lifecycleApi = read("src/lib/admin-lifecycle-api.ts");
assert.match(lifecycleApi, /fetchAdminUserActivityDetail/);
assert.match(lifecycleApi, /\/admin\/users\/\$\{userId\}\/activity\/\$\{kind\}/);

console.log("admin-users-smoke: ok");
