/**
 * Admin + end-user restrictions UI smoke — static source asserts.
 * Run: npm run test:user-restrictions
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

// --- Catalog + presets (selective first; emergency secondary) ---
const catalog = read("src/lib/account-status.ts");
assert.match(catalog, /RESTRICTION_PRESETS/);
assert.match(catalog, /Messaging/);
assert.match(catalog, /Buyer/);
assert.match(catalog, /alsoSuspend:\s*true/);
assert.match(catalog, /Emergency: full account block/);
assert.match(catalog, /deriveDisplayAccountStatus/);
assert.match(catalog, /FULL_SUSPENSION_RESTRICTIONS/);

// --- API client (POST/PATCH/revoke — not PUT) ---
const api = read("src/lib/admin-lifecycle-api.ts");
assert.match(api, /fetchAdminUserRestrictions/);
assert.match(api, /applyAdminUserRestrictions/);
assert.match(api, /extendAdminUserRestriction/);
assert.match(api, /revokeAdminUserRestriction/);
assert.match(api, /restriction_keys/);
assert.match(api, /method:\s*"POST"/);
assert.match(api, /method:\s*"PATCH"/);
assert.match(api, /\/revoke/);
assert.doesNotMatch(
  api.replace(/@deprecated[\s\S]*?updateAdminUserRestrictions[\s\S]*?\.then/, ""),
  /method:\s*"PUT"/,
);

// --- Permissions ---
const perms = read("src/lib/auth/permissions.ts");
assert.match(perms, /admin\.users\.view_restrictions/);
assert.match(perms, /admin\.users\.add_restriction/);
assert.match(perms, /admin\.users\.revoke_restriction/);

// --- Admin Restrictions panel ---
assert.ok(exists("src/components/admin/AdminUserRestrictionsPanel.tsx"));
const panel = read("src/components/admin/AdminUserRestrictionsPanel.tsx");
assert.match(panel, /Selective presets/);
assert.match(panel, /Individual activities/);
assert.match(panel, /Apply restrictions/);
assert.match(panel, /label="Revoke"|Revoke/);
assert.match(panel, /Extend/);
assert.match(panel, /Emergency: full account block/);
assert.match(panel, /Emergency only/);
assert.match(panel, /Reason/);
assert.match(panel, /length >= 3|reasonOk/);
assert.match(panel, /confirm-apply-restrictions|I confirm these restrictions/);
assert.match(panel, /Current restrictions/);
assert.match(panel, /canAddRestriction/);
assert.match(panel, /canRevokeRestriction/);
assert.match(panel, /canViewRestrictions/);
assert.match(panel, /canSuspend/);
assert.match(panel, /canBan/);
assert.doesNotMatch(panel, /internal_note.*user-facing|show.*internal_note.*user/i);

// --- Detail tab wiring ---
const sections = read("src/components/admin/AdminUserDetailSections.tsx");
assert.match(sections, /id: "restrictions"/);
assert.match(sections, /restrictionsPanel/);
assert.match(sections, /canViewRestrictions/);

const detailPage = read("src/app/admin/users/[userId]/page.tsx");
assert.match(detailPage, /AdminUserRestrictionsPanel/);
assert.match(detailPage, /restrictionsPanel:/);
assert.match(detailPage, /applyAdminUserRestrictions/);
assert.match(detailPage, /revokeAdminUserRestriction/);
assert.match(detailPage, /extendAdminUserRestriction/);
assert.match(detailPage, /admin\.users\.view_restrictions/);
assert.match(detailPage, /admin\.users\.add_restriction/);
assert.match(detailPage, /admin\.users\.revoke_restriction/);
assert.match(detailPage, /admin\.users\.ban/);
assert.match(detailPage, /Emergency: block login/);
assert.match(detailPage, /Prefer the Restrictions tab/);
assert.doesNotMatch(detailPage, /password_hash|access_token|refresh_token/);

// --- End-user restriction helper ---
assert.ok(exists("src/lib/user-restrictions.ts"));
const userRestr = read("src/lib/user-restrictions.ts");
assert.match(
  userRestr,
  /This action isn’t available on your account\.|This action isn't available on your account\./,
);
assert.match(userRestr, /userHasRestriction/);
assert.match(userRestr, /userRestrictionKeys/);
assert.doesNotMatch(userRestr, /internal_note/);

assert.ok(exists("src/hooks/useUserRestrictions.ts"));

// --- Restricted user surfaces ---
const createCta = read("src/components/layout/CreateEventCta.tsx");
assert.match(createCta, /cannot_create_events/);

const connectBtn = read("src/components/fan-connect/ConnectButton.tsx");
assert.match(connectBtn, /cannot_use_fan_connect/);
assert.match(connectBtn, /cannot_message/);
assert.match(connectBtn, /USER_RESTRICTION_ACTION_MESSAGE/);

const inbox = read("src/components/messaging/MessagesInbox.tsx");
assert.match(inbox, /cannot_message/);
assert.match(inbox, /USER_RESTRICTION_ACTION_MESSAGE/);

const eventView = read("src/components/events/EventPublicView.tsx");
assert.match(eventView, /cannot_checkout/);
assert.match(eventView, /checkoutBlocked/);

const checkout = read("src/app/events/[slug]/checkout/page.tsx");
assert.match(checkout, /checkoutBlocked|RestrictedActionNotice/);
assert.match(checkout, /cannot_checkout/);

const newEvent = read("src/app/host/events/new/page.tsx");
assert.match(newEvent, /cannot_create_events/);
assert.match(newEvent, /RestrictedActionNotice/);

const desk = read("src/app/host/desk/page.tsx");
assert.match(desk, /cannot_scan_tickets/);

const staffScan = read("src/app/staff/check-in/[eventId]/page.tsx");
assert.match(staffScan, /cannot_scan_tickets/);
assert.match(staffScan, /RestrictedActionNotice/);

const dock = read("src/lib/host-scanner-entry.ts");
assert.match(dock, /cannot_scan_tickets/);
assert.match(dock, /Scan merch|pickupScannerHref|canScanMerch/);

// --- Suspended / banned session handling ---
const requireAuth = read("src/components/auth/RequireAuth.tsx");
assert.match(requireAuth, /suspended/);
assert.match(requireAuth, /banned/);
assert.match(requireAuth, /SuspendedAccountPage/);

assert.ok(exists("src/components/account/SuspendedAccountPage.tsx"));
const suspendedPage = read("src/components/account/SuspendedAccountPage.tsx");
assert.match(suspendedPage, /Appeal|appeal/);
assert.doesNotMatch(suspendedPage, /internal_note/);

const authTypes = read("src/lib/auth/types.ts");
assert.match(authTypes, /account_restrictions\?/);
assert.match(authTypes, /suspension\?/);

console.log("user-restrictions-smoke: ok");
