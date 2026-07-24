/**
 * Host Command Center smoke checks — routes, redirects, nav groups, roadmap.
 * Run: npm run test:host-command-center
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

const nextConfig = read("next.config.ts");
assert.match(
  nextConfig,
  /source: "\/host\/dashboard"[\s\S]*?destination: "\/host"/,
);
assert.match(
  nextConfig,
  /source: "\/host\/events\/:id\/merch"[\s\S]*?destination: "\/host\/events\/:id\/merchandise"/,
);
assert.match(
  nextConfig,
  /source: "\/host\/settings\/notifications"[\s\S]*?destination: "\/dashboard\/settings\/notifications"/,
);
assert.match(nextConfig, /permanent: true/);
assert.doesNotMatch(
  nextConfig,
  /source: "\/dashboard\/host/,
  "do not add /dashboard/host alias this phase",
);
assert.doesNotMatch(
  nextConfig,
  /destination: "\/dashboard\/host/,
  "do not make /dashboard/host canonical",
);

assert.ok(exists("src/app/host/dashboard/page.tsx"));
const dashboardAlias = read("src/app/host/dashboard/page.tsx");
assert.match(dashboardAlias, /permanentRedirect\("\/host"\)/);
assert.ok(
  !exists("src/app/dashboard/host"),
  "no /dashboard/host route tree this phase",
);

assert.ok(exists("src/app/host/roadmap/page.tsx"));
assert.ok(exists("src/app/host/support/page.tsx"));
assert.ok(exists("src/lib/host-roadmap.ts"));
assert.ok(exists("src/components/host/command-center/OwnerCommandCenter.tsx"));

const workspaceNav = read("src/lib/nav/workspace.ts");
assert.match(workspaceNav, /hostNavGroups/);
assert.match(workspaceNav, /HOST_GROUP_LABELS/);
assert.match(workspaceNav, /operate: "Operate"/);
assert.match(workspaceNav, /grow: "Grow"/);
assert.match(workspaceNav, /manage: "Manage"/);
assert.match(workspaceNav, /Tickets & Entry/);
assert.match(workspaceNav, /Roadmap/);
assert.match(workspaceNav, /label: "Merch Studio"/);
assert.match(workspaceNav, /label: "Host Inbox"/);
assert.match(workspaceNav, /label: "Ambassador Campaigns"/);
assert.match(workspaceNav, /label: "Audience CRM"/);
assert.match(workspaceNav, /label: "Legacy Page"/);
assert.match(workspaceNav, /label: "Vault Studio"/);
assert.match(workspaceNav, /label: "Host Team"/);
assert.match(workspaceNav, /label: "Host Settings"/);
assert.match(workspaceNav, /href: "\/host\/events"/);
assert.match(workspaceNav, /href: "\/host\/desk"/);
assert.match(workspaceNav, /href: "\/host\/merchandise"/);
assert.match(workspaceNav, /href: "\/host\/messages"/);
assert.match(workspaceNav, /href: "\/host\/ambassadors"/);
assert.match(workspaceNav, /href: "\/host\/sponsorships"/);
assert.match(workspaceNav, /href: "\/host\/audience"/);
assert.match(workspaceNav, /href: "\/host\/legacy"/);
assert.match(workspaceNav, /href: "\/host\/vault"/);
assert.match(workspaceNav, /href: "\/host\/analytics"/);
assert.match(workspaceNav, /href: "\/host\/team"/);
assert.match(workspaceNav, /href: "\/host\/settings"/);
assert.match(workspaceNav, /href: "\/host\/support"/);
assert.match(workspaceNav, /EXACT_MATCH_NAV_HREFS/);
assert.doesNotMatch(
  workspaceNav,
  /href: "\/host\/payouts"/,
  "payouts should not be in primary host sidebar",
);

const hostNavBlock = workspaceNav.match(
  /export const hostNav: NavItem\[] = \[([\s\S]*?)\];/,
)?.[1];
assert.ok(hostNavBlock, "hostNav array must exist");

/** Final Host sidebar order: groups + disambiguated labels + routes. */
assert.match(
  hostNavBlock,
  /hostNavItem\("home".*href: "\/host".*label: "Overview"[\s\S]*?hostNavItem\("home".*href: "\/host\/notifications".*label: "Alerts"[\s\S]*?hostNavItem\("home".*href: "\/host\/roadmap".*label: "Roadmap"[\s\S]*?hostNavItem\("operate".*href: "\/host\/events".*label: "Events"[\s\S]*?hostNavItem\("operate".*href: "\/host\/desk".*label: "Tickets & Entry"[\s\S]*?hostNavItem\("operate".*href: "\/host\/merchandise".*label: "Merch Studio"[\s\S]*?hostNavItem\("operate".*href: "\/host\/messages".*label: "Host Inbox"[\s\S]*?hostNavItem\("grow".*href: "\/host\/ambassadors".*label: "Ambassador Campaigns"[\s\S]*?hostNavItem\("grow".*href: "\/host\/sponsorships".*label: "Sponsorships"[\s\S]*?hostNavItem\("grow".*href: "\/host\/audience".*label: "Audience CRM"[\s\S]*?hostNavItem\("grow".*href: "\/host\/legacy".*label: "Legacy Page"[\s\S]*?hostNavItem\("grow".*href: "\/host\/vault".*label: "Vault Studio"[\s\S]*?hostNavItem\("manage".*href: "\/host\/analytics".*label: "Analytics"[\s\S]*?hostNavItem\("manage".*href: "\/host\/team".*label: "Host Team"[\s\S]*?hostNavItem\("manage".*href: "\/host\/settings".*label: "Host Settings"[\s\S]*?hostNavItem\("manage".*href: "\/host\/support".*label: "Support"/s,
);

assert.doesNotMatch(
  hostNavBlock,
  /href: "\/dashboard\//,
  "host nav must not include /dashboard paths",
);
assert.match(hostNavBlock, /hostNavItem/);
assert.doesNotMatch(
  hostNavBlock,
  /buyerNavItem/,
  "host nav must not use buyerNavItem helpers",
);
// Personal buyer labels must not leak into hostNav item list (exact label strings).
assert.doesNotMatch(
  hostNavBlock,
  /label: "(Merch|Messages|Ambassadors|Audience|Vault|Team|Settings|Workspaces)"[,}\n]/,
  "host nav labels must stay disambiguated from Personal",
);

const hostNav = read("src/lib/nav/host-nav.ts");
assert.match(hostNav, /navGroupsForWorkspace/);
assert.match(hostNav, /isDeskFocusedStaff/);
assert.match(hostNav, /isHostReadOnlyMember/);

const hostLayout = read("src/app/host/layout.tsx");
assert.match(hostLayout, /navGroupsForWorkspace/);
assert.match(hostLayout, /navGroups=\{navGroups\}/);
assert.match(hostLayout, /WorkspaceShell/);
assert.match(hostLayout, /hostWorkspaceChromeTitle/);
assert.match(hostLayout, /WorkspaceSwitcher/);
assert.doesNotMatch(
  hostLayout,
  /buyerNav|PERSONAL_WORKSPACE_TITLE/,
  "host layout must not mount Personal chrome title/nav",
);

const personalLayout = read("src/app/dashboard/layout.tsx");
assert.match(personalLayout, /buyerNav/);
assert.match(personalLayout, /buyerNavGroups/);
assert.doesNotMatch(
  personalLayout,
  /hostNav|navGroupsForWorkspace/,
  "personal layout must not mount host nav config",
);

const dashboardSidebar = read("src/components/layout/DashboardSidebar.tsx");
const workspaceNavSections = read("src/components/layout/WorkspaceNavSections.tsx");
assert.match(dashboardSidebar, /md:block/);
assert.match(dashboardSidebar, /WorkspaceNavSections/);
assert.match(
  dashboardSidebar,
  /homeHref\?: string|homeHref,/,
  "sidebar must accept shell homeHref for role-aware active state",
);
assert.doesNotMatch(
  dashboardSidebar,
  /const homeHref = items\[0\]/,
  "sidebar must not infer homeHref from items[0] (breaks desk nav)",
);
assert.doesNotMatch(
  dashboardSidebar,
  /overflow-x-auto.*items\.map|ScrollHintNav/,
  "workspace sidebar must stay vertical",
);
assert.doesNotMatch(
  workspaceNavSections,
  /overflow-x-auto.*items\.map|ScrollHintNav/,
  "workspace nav sections must stay vertical",
);

const dashboardTopbar = read("src/components/layout/DashboardTopbar.tsx");
assert.match(dashboardTopbar, /md:hidden/);
assert.match(dashboardTopbar, /WorkspaceNavSections/);
assert.doesNotMatch(
  dashboardTopbar,
  /overflow-x-auto|ScrollHintNav|rounded-full px-3/,
  "workspace topbar must not render horizontal pill nav",
);

const hostAccess = read("src/lib/host-access.ts");
assert.match(hostAccess, /hostHomePathForWorkspace/);
assert.match(hostAccess, /isDeskFocusedStaff\(workspace\).*\/host\/desk/s);
assert.match(hostAccess, /role === "scanner".*\/host\/desk/s);
assert.match(hostAccess, /role === "merch_staff".*\/host\/desk/s);
assert.match(
  hostAccess,
  /role === "sponsor_manager"[\s\S]*?return "\/host\/sponsorships"/,
);
assert.match(hostAccess, /Host: \$\{displayName\}/);
assert.match(hostAccess, /hostWorkspaceChromeTitle/);
assert.match(hostAccess, /PERSONAL_WORKSPACE_TITLE = "Personal"/);

const homePathFn = hostAccess.match(
  /export function hostHomePathForWorkspace\([\s\S]*?\n\}/,
)?.[0];
assert.ok(homePathFn, "hostHomePathForWorkspace body must be extractable");
assert.match(homePathFn, /is_owner\) return "\/host"/);
assert.match(homePathFn, /return "\/host\/desk"/);
assert.match(homePathFn, /return "\/host\/sponsorships"/);
assert.match(homePathFn, /return "\/host"/);
assert.doesNotMatch(
  homePathFn,
  /\/host\/events/,
  "hostHomePathForWorkspace must not hardcode /host/events",
);

const commandCenterHeader = read(
  "src/components/host/command-center/CommandCenterHeader.tsx",
);
assert.doesNotMatch(
  commandCenterHeader,
  /WorkspaceSwitcher/,
  "Command Center must not duplicate the shell workspace switcher",
);
assert.match(
  commandCenterHeader,
  /Host Command Center/,
  "preserve Host Command Center eyebrow",
);
assert.match(
  commandCenterHeader,
  />\s*Overview\s*</,
  "Command Center H1 is Overview (shell already shows Host: name)",
);
assert.match(commandCenterHeader, /Legacy Page/);
assert.doesNotMatch(
  commandCenterHeader,
  /Legacy studio/,
  "Legacy CTA must match sidebar Legacy Page label",
);

const ownerCc = read("src/components/host/command-center/OwnerCommandCenter.tsx");
assert.match(ownerCc, /NextBestActionCard/);
assert.match(ownerCc, /ReadinessGapsSection/);
assert.match(ownerCc, /UpcomingEventsSection/);
assert.match(ownerCc, /TodaysOperationsSection/);
assert.match(ownerCc, /SalesSnapshotSection/);
assert.match(ownerCc, /PendingTasksSection/);
assert.match(ownerCc, /QuickActionsRow/);
assert.match(
  ownerCc,
  /active\?\.host_id/,
  "Command Center data effect depends on active host",
);
assert.match(
  ownerCc,
  /startTransition/,
  "host switch clears stale CC snapshot before refetch",
);
assert.match(
  ownerCc,
  /setEvents\(null\)|setTodayOpsSnapshot\(null\)/,
  "host switch must drop previous host events/metrics",
);
assert.match(
  ownerCc,
  /canScan=\{canScan\}/,
  "Today ops Scanner must be permission-gated",
);
assert.match(
  ownerCc,
  /canMerchPickup=\{canMerchPickup\}/,
  "Today ops Pickup must use canScanMerch (not merch.view)",
);
assert.match(ownerCc, /canScanTickets\(active\)/);
assert.match(ownerCc, /canScanMerch\(active\)/);
assert.match(
  ownerCc,
  /assignedEventIds=\{assignedEventIds\}/,
  "Today ops supports selected-events desk scope",
);

const pendingTasks = read(
  "src/components/host/command-center/PendingTasksSection.tsx",
);
assert.match(pendingTasks, /Needs attention/);
assert.doesNotMatch(
  pendingTasks,
  />\s*Inbox\s*</,
  "Pending tasks eyebrow must not clash with Host Inbox",
);

const todayOps = read(
  "src/components/host/command-center/CommandCenterSections.tsx",
);
assert.match(todayOps, /canScan = false/);
assert.match(todayOps, /canMerchPickup = false/);
assert.match(todayOps, /assignedEventIds/);
assert.match(todayOps, /canScan && canActOnEvent/);
assert.match(todayOps, /canMerchPickup && canActOnEvent/);
assert.doesNotMatch(
  todayOps,
  /canScan = true|canMerch = true/,
  "Today ops CTAs must default closed without grants",
);

const rowActions = read("src/components/host/events/HostEventRowActions.tsx");
assert.match(rowActions, /label: "Merch Studio"/);
assert.match(rowActions, /label: "Ambassador Campaigns"/);
assert.match(
  rowActions,
  /label: "Merch Studio",\s*\n\s*href: `\/host\/events\/\$\{id\}\/merchandise`/,
);
assert.match(
  rowActions,
  /label: "Ambassador Campaigns",\s*\n\s*href: `\/host\/events\/\$\{id\}\/ambassadors`/,
);
assert.doesNotMatch(
  rowActions,
  /label: "Merch"|label: "Ambassadors"/,
  "event row action labels must stay disambiguated",
);

const eventOpsNav = read("src/components/host/EventOpsNav.tsx");
assert.match(
  eventOpsNav,
  /suffix: "\/merchandise", label: "Merch Studio"/,
);
assert.match(
  eventOpsNav,
  /suffix: "\/ambassadors", label: "Ambassador Campaigns"/,
);
assert.doesNotMatch(
  eventOpsNav,
  /suffix: "\/merchandise", label: "Merch"|suffix: "\/ambassadors", label: "Ambassadors"/,
);

const listCard = read("src/components/host/HostEventListCard.tsx");
assert.match(
  listCard,
  /HostEventRowActions/,
  "grid view must reuse desk-safe row actions",
);
assert.match(listCard, /deskConstrained/);
assert.match(listCard, /scannerOnly|merchOnly|deskOnly/);
assert.match(
  listCard,
  /if \(deskConstrained\) return/,
  "desk grid must skip analytics/revenue fetch",
);

const hostEventsToolbar = read(
  "src/components/host/events/HostEventsToolbar.tsx",
);
assert.match(hostEventsToolbar, /allowGridView/);

const hostHome = read("src/app/host/page.tsx");
assert.match(hostHome, /OwnerCommandCenter/);
assert.match(
  hostHome,
  /OwnerCommandCenter key=\{active\.host_id\}/,
  "owner Command Center remounts on host switch (no stale snapshot)",
);
assert.match(hostHome, /MemberDeskOverview|function MemberDeskOverview/);
assert.match(hostHome, /eyebrow="Overview"/);
assert.match(hostHome, /Scanner workspace/);
assert.match(hostHome, /Merch pickup desk/);
assert.match(hostHome, /Read-only host workspace/);
assert.match(hostHome, /Sponsor workspace/);
assert.match(hostHome, /isOwner \? \(/);
assert.match(
  hostHome,
  /OwnerCommandCenter key=\{active\.host_id\}/,
);
assert.doesNotMatch(
  hostHome,
  /isOwner \|\|.*OwnerCommandCenter|role === "host_admin".*OwnerCommandCenter/,
  "OwnerCommandCenter stays owner-only (not host admins)",
);
assert.doesNotMatch(hostHome, /WorkspaceNavGrid/);

const eventsPage = read("src/app/host/events/page.tsx");
assert.match(eventsPage, /HostEventsTable/);
assert.match(eventsPage, /HostEventsListView/);
assert.match(eventsPage, /HostEventListCard/);
assert.match(eventsPage, /rowActions=\{rowActions\}/);
assert.match(eventsPage, /EVENT_LIST_TABS/);
assert.match(eventsPage, /effectiveViewMode/);
assert.match(
  eventsPage,
  /deskOnly && viewMode === "grid" \? "table"/,
  "desk staff must not land on studio grid view",
);
assert.match(eventsPage, /allowGridView=\{!deskOnly\}/);
assert.match(eventsPage, /fetchWorkspaceDeskEvents/);
assert.match(eventsPage, /scannerOnly/);
assert.match(eventsPage, /merchOnly/);

const deskPage = read("src/app/host/desk/page.tsx");
assert.match(deskPage, /eyebrow="Tickets & Entry"/);

const legacyPage = read("src/app/host/legacy/page.tsx");
assert.match(legacyPage, /title="Legacy Page"/);

assert.ok(exists("src/app/host/events/[id]/merch/page.tsx"));
const merchAlias = read("src/app/host/events/[id]/merch/page.tsx");
assert.match(merchAlias, /permanentRedirect\(`\/host\/events\/\$\{id\}\/merchandise`\)/);

assert.ok(exists("src/app/host/settings/notifications/page.tsx"));
const notifAlias = read("src/app/host/settings/notifications/page.tsx");
assert.match(notifAlias, /permanentRedirect\("\/dashboard\/settings\/notifications"\)/);

assert.ok(exists("src/components/host/onboarding/HostOnboardingRedirectGuard.tsx"));
const onboardingGuard = read("src/components/host/onboarding/HostOnboardingRedirectGuard.tsx");
assert.match(onboardingGuard, /router\.replace\("\/host\/roadmap"\)/);
assert.match(onboardingGuard, /fetchMyHost/);

const onboarding = read("src/app/host/onboarding/page.tsx");
assert.match(onboarding, /HostOnboardingRedirectGuard/);
assert.match(onboarding, /HostOnboardingForm/);

console.log("host-command-center-smoke: ok");
