/**
 * Admin impersonation UI wiring smoke checks — Phase 14B frontend matrix.
 * Run: npm run test:impersonation
 *
 * Covers:
 * - Impersonate button appears only with permission
 * - Modal requires reason
 * - Banner appears during impersonation
 * - Exit impersonation works
 * - Personal dashboard renders as target user
 * - Host workspace renders only if target user has host access
 * - /admin is blocked while impersonating
 * - Sensitive settings actions are disabled
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

// --- Admin user detail: Impersonate button only with permission ---
const userDetail = read("src/app/admin/users/[userId]/page.tsx");
assert.match(userDetail, /admin\.users\.impersonate/);
assert.match(userDetail, /canImpersonate/);
assert.match(userDetail, /Impersonate user/);
assert.match(userDetail, /ImpersonationStartModal/);
assert.match(
  userDetail,
  /canImpersonate[\s\S]*?Impersonate user/,
  "Impersonate CTA must be gated by canImpersonate",
);

const usersIndex = read("src/app/admin/users/page.tsx");
assert.match(usersIndex, /\/admin\/users\/\$\{|\/admin\/users\/\$\{encodeURIComponent/);
assert.match(
  usersIndex,
  /Open user|Browse and manage/,
  "Users list must deep-link into detail where impersonation lives",
);

const impersonationPage = read(
  "src/app/admin/users/[userId]/impersonation/page.tsx",
);
assert.match(
  impersonationPage,
  /You need admin impersonation permission/,
);

// --- Modal / form requires reason ---
const startForm = read("src/components/admin/ImpersonationStartForm.tsx");
assert.match(startForm, /reason\.trim\(\)\.length >= 3/);
assert.match(startForm, /canSubmit = reasonOk && confirmed/);
assert.match(startForm, /name="reason"/);
assert.match(startForm, /disabled=\{!canSubmit\}/);
assert.match(startForm, /impersonation-confirm/);
assert.match(startForm, /sensitive actions are\s+blocked/);
assert.match(startForm, /Start impersonation|submitLabel/);
assert.match(startForm, /router\.push\(redirectTo \|\| "\/dashboard"\)/);
assert.match(startForm, /resolveActorImpersonationScopes/);
assert.match(startForm, /\/admin\/orders/);
assert.match(startForm, /\/support\/desk/);
assert.match(startForm, /\/admin\/message-reports/);

assert.ok(exists("src/components/admin/ImpersonationStartModal.tsx"));
const startModal = read("src/components/admin/ImpersonationStartModal.tsx");
assert.match(startModal, /ImpersonationStartForm/);

// --- Banner appears during impersonation + Exit ---
const banner = read("src/components/auth/ImpersonationBanner.tsx");
assert.match(banner, /data-impersonation-banner/);
assert.match(banner, /if \(!isImpersonating \|\| !user\) return null/);
assert.match(banner, /Exit impersonation/);
assert.match(banner, /stopImpersonation\(\)/);
assert.match(banner, /window\.location\.assign/);
assert.match(banner, /packLabel/);
assert.match(banner, /impersonation\?\.pack/);

const scopesHelper = read("src/lib/auth/impersonation-scopes.ts");
assert.match(scopesHelper, /IMPERSONATION_SCOPE_HOST_EVENTS/);
assert.match(scopesHelper, /IMPERSONATION_SCOPE_CREDENTIALS/);
assert.match(scopesHelper, /resolveActorImpersonationScopes/);
assert.match(banner, /Impersonating \{displayName\}/);
assert.match(banner, /Pack:/);
assert.match(banner, /\/admin\/users\/\$\{targetId\}/);
assert.match(banner, /Audited session/);
assert.match(banner, /Demo seed account/);

const editEventPage = read("src/app/host/events/[id]/edit/page.tsx");
assert.match(editEventPage, /await submitEvent\(eventId\)/);
assert.doesNotMatch(editEventPage, /import \{[^}]*approveEvent/);
assert.match(
  read("src/components/events/studio/TicketTypeBuilder.tsx"),
  /allowStructuralEdits/,
);
assert.match(
  read("src/components/events/studio/EventStudio.tsx"),
  /hostEventsAllowed/,
);
assert.match(
  read("src/components/settings/AccountSecurityCard.tsx"),
  /isImpersonating/,
);
assert.match(
  read("src/components/settings/AccountSecurityCard.tsx"),
  /credentials/,
);

const rootLayout = read("src/app/layout.tsx");
assert.match(rootLayout, /ImpersonationBanner/);
assert.match(rootLayout, /<ImpersonationBanner\s*\/>/);

const authProvider = read("src/components/auth/AuthProvider.tsx");
assert.match(authProvider, /isImpersonating/);
assert.match(authProvider, /stopImpersonation/);
assert.match(authProvider, /startImpersonation/);
assert.match(authProvider, /isImpersonationSession/);
assert.match(authProvider, /restoreAdminTokens|stashAdminTokens/);

// --- Personal dashboard renders as target user ---
const dashboardPage = read("src/app/dashboard/page.tsx");
assert.match(dashboardPage, /PersonalCommandCenter/);
const dashboardLayout = read("src/app/dashboard/layout.tsx");
assert.doesNotMatch(
  dashboardLayout,
  /denyWhileImpersonating/,
  "Personal dashboard must remain available while impersonating",
);
const dashboardLayoutClient = read("src/app/dashboard/DashboardLayoutClient.tsx");
assert.match(
  dashboardLayoutClient,
  /buyerNav|buyerNavGroups|PERSONAL_WORKSPACE/,
);

// --- Host workspace only if target has host access ---
const requireHost = read("src/components/hosts/RequireHost.tsx");
assert.match(requireHost, /workspaces\.length === 0/);
assert.match(requireHost, /Become a host|host\/onboarding/);
const hostLayout = read("src/app/host/layout.tsx");
assert.match(hostLayout, /HostLayoutClient/);
const hostLayoutClient = read("src/app/host/HostLayoutClient.tsx");
assert.match(
  hostLayoutClient,
  /HostWorkspaceProvider|RequireHost|HostAccessGuard/,
);
assert.ok(exists("src/components/hosts/HostWorkspaceProvider.tsx"));
const hostProvider = read("src/components/hosts/HostWorkspaceProvider.tsx");
assert.match(hostProvider, /fetchHostWorkspaces/);

// --- /admin blocked while impersonating ---
const adminLayout = read("src/app/admin/layout.tsx");
assert.match(adminLayout, /AdminLayoutClient/);
const adminLayoutClient = read("src/app/admin/AdminLayoutClient.tsx");
assert.match(adminLayoutClient, /denyWhileImpersonating|isImpersonating/);
const requireAuth = read("src/components/auth/RequireAuth.tsx");
assert.match(requireAuth, /denyWhileImpersonating/);
assert.match(requireAuth, /Admin unavailable while impersonating/);
assert.match(requireAuth, /href="\/dashboard"/);

const siteHeader = read("src/components/layout/SiteHeader.tsx");
assert.match(siteHeader, /isImpersonating/);
const workspaceAccess = read("src/lib/auth/workspace-access.ts");
assert.match(workspaceAccess, /canAccessAdminPanel/);
assert.match(
  workspaceAccess,
  /if \(!user \|\| isImpersonating\) return false/,
);
const headerWorkspace = read("src/components/layout/HeaderWorkspaceButton.tsx");
assert.match(headerWorkspace, /canAccessAdminPanel\(user, isImpersonating\)/);

// --- Sensitive settings actions disabled ---
const passportSettings = read("src/app/dashboard/passport/settings/page.tsx");
assert.match(passportSettings, /isImpersonating/);
assert.match(passportSettings, /data-impersonation-locked/);
assert.match(passportSettings, /fieldset disabled=\{impersonationLocked\}/);
assert.match(
  passportSettings,
  /disabled=\{busy \|\| !dirty \|\| impersonationLocked\}/,
);
assert.match(
  passportSettings,
  /Passport privacy and directory settings cannot be changed|impersonationLocked/,
);
assert.match(passportSettings, /if \(!draft \|\| impersonationLocked\) return/);

// --- Auth / API contract surface ---
const storage = read("src/lib/auth/storage.ts");
assert.match(storage, /padeya\.impersonating|isImpersonationSession/);
assert.match(storage, /setImpersonationAccessToken|stashAdminTokens/);

const api = read("src/lib/api.ts");
assert.match(api, /impersonation\/start/);
assert.match(api, /admin\/impersonation\/end/);
assert.match(api, /me\/impersonation/);

console.log("impersonation-smoke: ok");
