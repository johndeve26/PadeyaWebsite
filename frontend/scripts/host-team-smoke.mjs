/**
 * Host team UI smoke checks — no browser / React test runner required.
 * Covers section 16 frontend checklist (routes, invite modal, nav, theme tokens).
 * Run: npm run test:host-team
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

function assertThemeSafeTokens(rel, source) {
  assert.match(
    source,
    /text-foreground|text-heading|text-muted-foreground|bg-card|border-border|bg-muted/,
    `${rel} should use semantic theme tokens for light/dark`,
  );
}

// --- Routes load ---
const routes = [
  "src/app/host/team/page.tsx",
  "src/app/host/team/members/page.tsx",
  "src/app/host/team/invites/page.tsx",
  "src/app/host/team/audit-log/page.tsx",
  "src/app/host/team/[id]/page.tsx",
  "src/app/team/invite/[token]/page.tsx",
  "src/app/host/desk/page.tsx",
  "src/app/host/access-denied/page.tsx",
];
for (const rel of routes) {
  assert.ok(exists(rel), `missing ${rel}`);
}

// --- /host/team loads ---
const teamPage = read("src/app/host/team/page.tsx");
assert.match(teamPage, /TeamInviteModal/);
assert.match(teamPage, /HostTeamSubnav/);
assert.match(teamPage, /fetchHostTeam|fetchHostTeamMembers|inviteOpen/);
assertThemeSafeTokens("src/app/host/team/page.tsx", teamPage);

// --- Invite modal: role presets, permission toggles, event scope ---
const inviteModal = read("src/components/hosts/team/TeamInviteModal.tsx");
assert.match(inviteModal, /TEAM_ROLE_OPTIONS|permissionsForRole/);
assert.match(inviteModal, /TeamPermissionToggles/);
assert.match(inviteModal, /TeamEventScopePicker/);
assert.match(inviteModal, /inviteHostTeamMember/);
assert.match(inviteModal, /defaultScopeForRole|scope/);
assert.match(inviteModal, /Email or Pàdéyá username/);
assert.match(inviteModal, /name@example\.com or @username/);
assert.match(inviteModal, /lookupHostTeamInvitee|Invite will be sent to this email/);
assert.match(inviteModal, /This user will receive an invite|No Pàdéyá user found/);
assert.doesNotMatch(
  inviteModal,
  /type="email"/,
  "invite uses one text field (not a separate email-only input)",
);

// §10 Frontend checks — invite modal identifier + preview
assert.match(
  inviteModal,
  /function looksLikeEmail/,
  "invite modal accepts email",
);
assert.match(
  inviteModal,
  /value\.startsWith\("@"\)|looksLikeUsernameCandidate/,
  "invite modal accepts @username",
);
assert.match(
  inviteModal,
  /\$\{trimmed\}|`@\$\{trimmed\}`|startsWith\("@"\) \? trimmed : `@\$\{trimmed\}`/,
  "invite modal normalizes username without @",
);
assert.match(
  inviteModal,
  /This user will receive an invite/,
  "username preview works",
);
assert.match(
  inviteModal,
  /No Pàdéyá user found with that username/,
  "unknown username error works",
);
assert.match(
  inviteModal,
  /invite_identifier:\s*trimmed/,
  "submit sends invite_identifier for email and username",
);
// Username preview UI must not render account email fields
assert.doesNotMatch(
  inviteModal,
  /\{lookup\.masked_email\}|\{lookup\.email\}|account email/i,
  "username preview must not render private account email",
);

const helpers = read("src/lib/host-team-helpers.ts");
assert.match(helpers, /inviteePrimaryLabel|invited_username/);
assert.match(helpers, /invite_method.*username|username.*invite_method/);
assert.match(
  helpers,
  /invite_method === "username"|invited_username/,
  "pending invite list prefers username over private email",
);
assert.doesNotMatch(
  helpers,
  /return row\.invited_email \|\| row\.invited_username/,
  "username invites must not fall back to private email first",
);

const roleLib = read("src/lib/host-team-roles.ts");
assert.match(roleLib, /TEAM_ROLE_OPTIONS/);
assert.match(roleLib, /permissionsForRole/);
assert.match(roleLib, /scanner|merch_staff|viewer|admin/);

const toggles = read("src/components/hosts/team/TeamPermissionToggles.tsx");
assert.match(toggles, /permission|onChange|PERMISSION/);
assertThemeSafeTokens(
  "src/components/hosts/team/TeamPermissionToggles.tsx",
  toggles,
);

const scopePicker = read("src/components/hosts/team/TeamEventScopePicker.tsx");
assert.match(scopePicker, /selected_events|host_wide|scope/i);
assert.match(scopePicker, /event/i);

// --- Pending invites + revoke ---
const invitesPage = read("src/app/host/team/invites/page.tsx");
assert.match(invitesPage, /pending|invite/i);
assert.match(invitesPage, /revoke|Revoke/);
assert.match(
  invitesPage,
  /inviteePrimaryLabel|invited_username/,
  "pending invite list shows username safely",
);
assert.match(
  invitesPage,
  /invite_method === "username"/,
  "pending list branches on username invite method",
);
assert.match(
  invitesPage,
  /mobileCard/,
  "pending invites mobile card works",
);
assertThemeSafeTokens("src/app/host/team/invites/page.tsx", invitesPage);

// Team overview pending preview also prefers username
assert.match(
  teamPage,
  /invited_username \|\s*\n?\s*row\.invited_email|invited_username/,
  "team overview pending rows show username safely",
);
assertThemeSafeTokens("src/components/hosts/team/TeamInviteModal.tsx", inviteModal);

// --- Invite acceptance page ---
const acceptPage = read("src/app/team/invite/[token]/page.tsx");
assert.match(acceptPage, /accept|Accept/);
assert.match(acceptPage, /token/);
assert.match(acceptPage, /team\/invites|hosts\/team-invites|acceptTeamInvite|accept/);
assert.match(
  acceptPage,
  /This invite was sent to another Pàdéyá account/,
);
assert.match(acceptPage, /expired|revoked|already accepted/i);

// --- Member edit + suspend/remove ---
const memberEdit = read("src/app/host/team/[id]/page.tsx");
assert.match(memberEdit, /suspend|Suspend|remove|Remove/i);
assert.match(memberEdit, /TeamPermissionToggles|permissions|scope/i);

// --- Audit log displays ---
const auditPage = read("src/app/host/team/audit-log/page.tsx");
assert.match(auditPage, /actor|action|target|entity|created_at|timestamp/i);
assert.match(auditPage, /fetchHostTeamAudit|auditActionLabel|formatAuditMetadata/);
assertThemeSafeTokens("src/app/host/team/audit-log/page.tsx", auditPage);

// --- Workspace switcher ---
const switcher = read("src/components/hosts/WorkspaceSwitcher.tsx");
assert.match(switcher, /export function WorkspaceSwitcher/);
assert.match(switcher, /Personal account/);
assert.match(switcher, /Become a host/);
assert.match(switcher, /writeWorkspaceMode/);
const hostLayout = read("src/app/host/layout.tsx");
assert.match(hostLayout, /WorkspaceSwitcher/);
assert.match(hostLayout, /hostHomePathForWorkspace\(active\)/);
assert.match(hostLayout, /navGroupsForWorkspace/);
assert.match(hostLayout, /navGroups=\{navGroups\}/);

// --- Scanner / merch staff nav gating ---
const hostNav = read("src/lib/nav/host-nav.ts");
assert.match(hostNav, /canScanTickets|canScanMerch/);
assert.match(hostNav, /Tickets & Entry|Desk/);
assert.match(hostNav, /navGroupsForWorkspace|navForWorkspace/);

const hostAccess = read("src/lib/host-access.ts");
assert.match(hostAccess, /canAccessHostPath/);
assert.match(hostAccess, /finance\.view_payouts|bank-accounts|payouts/);
assert.match(hostAccess, /canScanTickets|canScanMerch/);
assert.match(hostAccess, /isDeskFocusedStaff\(workspace\).*\/host\/desk/s);
assert.match(hostAccess, /hostHomePathForWorkspace/);
assert.match(hostAccess, /isHostReadOnlyMember/);

// Restricted pages → permission denied
const accessDenied = read("src/app/host/access-denied/page.tsx");
assert.match(accessDenied, /HostPermissionDenied|access-denied|do not have access/i);
const guard = read("src/components/hosts/HostAccessGuard.tsx");
assert.match(guard, /canAccessHostPath/);
assert.match(guard, /access-denied/);

const deskPage = read("src/app/host/desk/page.tsx");
assert.match(deskPage, /scan|pickup|desk/i);
assertThemeSafeTokens("src/app/host/desk/page.tsx", deskPage);

// --- Mobile-friendly layout primitives (responsive classes on team surfaces) ---
assert.match(
  teamPage + auditPage + inviteModal,
  /sm:|md:|lg:|flex-wrap|min-w-0/,
  "team surfaces should include responsive layout classes",
);

// --- Dark/light: theme provider still wired (host shell inherits root ThemeProvider) ---
const layout = read("src/app/layout.tsx");
assert.match(layout, /ThemeProvider/);
assert.match(layout, /ThemeScript/);

console.log("host-team-smoke: ok");
