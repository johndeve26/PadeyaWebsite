/**
 * Buyer dashboard workspace nav smoke checks — grouped sidebar, no content strip.
 * Run: npm run test:buyer-dashboard-nav
 */

import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

const workspaceNav = read("src/lib/nav/workspace.ts");
assert.match(workspaceNav, /buyerNavGroups/);
assert.match(workspaceNav, /BUYER_GROUP_LABELS/);
assert.match(workspaceNav, /home: "Home"/);
assert.match(workspaceNav, /activity: "Activity"/);
assert.match(workspaceNav, /community: "Community"/);
assert.match(workspaceNav, /identity: "Identity"/);
assert.match(workspaceNav, /earn: "Earn"/);
assert.match(workspaceNav, /account: "Account"/);
assert.doesNotMatch(
  workspaceNav,
  /growth: "Growth"/,
  "Personal sidebar group Growth must be Earn",
);
assert.match(workspaceNav, /EXACT_MATCH_NAV_HREFS/);
assert.match(
  workspaceNav,
  /"\/connect":[\s\S]*\/dashboard\/connect/,
  "Connect nav active aliases must include /dashboard/connect",
);

const buyerNavBlock = workspaceNav.match(
  /export const buyerNav: NavItem\[] = \[([\s\S]*?)\];/,
)?.[1];
assert.ok(buyerNavBlock, "buyerNav array must exist");

assert.match(buyerNavBlock, /href: "\/dashboard\/hosts-for-you"[\s\S]*?label: "Hosts for you"/);

/** Final Personal sidebar order: groups + labels + routes (Phase 2). */
assert.match(
  buyerNavBlock,
  /buyerNavItem\("home".*href: "\/dashboard".*label: "Overview"[\s\S]*?buyerNavItem\("home".*href: "\/dashboard\/notifications".*label: "Alerts"[\s\S]*?buyerNavItem\("activity".*href: "\/dashboard\/tickets".*label: "Tickets"[\s\S]*?buyerNavItem\("activity".*href: "\/dashboard\/orders".*label: "Orders"[\s\S]*?buyerNavItem\("activity".*href: "\/dashboard\/merchandise".*label: "Merch"[\s\S]*?buyerNavItem\("activity".*href: "\/dashboard\/refunds".*label: "Refunds"[\s\S]*?buyerNavItem\("community".*href: "\/dashboard\/messages".*label: "Messages"[\s\S]*?buyerNavItem\("community".*href: "\/dashboard\/team".*label: "Workspaces"[\s\S]*?buyerNavItem\("community".*href: "\/connect".*label: "Connect"[\s\S]*?buyerNavItem\("community".*href: "\/dashboard\/following".*label: "Following"[\s\S]*?buyerNavItem\("identity".*href: "\/dashboard\/passport".*label: "Passport"[\s\S]*?buyerNavItem\("identity".*href: "\/dashboard\/badges".*label: "Badges"[\s\S]*?buyerNavItem\("identity".*href: "\/dashboard\/vault".*label: "Vault"[\s\S]*?buyerNavItem\("identity".*href: "\/dashboard\/reviews".*label: "Reviews"[\s\S]*?buyerNavItem\("earn".*href: "\/dashboard\/ambassador".*label: "Ambassadors"[\s\S]*?buyerNavItem\("account".*href: "\/dashboard\/support".*label: "Support"[\s\S]*?buyerNavItem\("account".*href: "\/dashboard\/settings".*label: "Settings"/s,
);
assert.doesNotMatch(
  buyerNavBlock,
  /label: "Team"/,
  "Personal sidebar must say Workspaces, not Team",
);
assert.doesNotMatch(
  buyerNavBlock,
  /href: "\/host\//,
  "personal buyerNav must not include /host paths",
);
assert.match(buyerNavBlock, /buyerNavItem/);
assert.doesNotMatch(
  buyerNavBlock,
  /hostNavItem/,
  "personal nav must not use hostNavItem helpers",
);

assert.ok(
  fs.existsSync(path.join(root, "src/app/dashboard/connect/page.tsx")),
  "legacy /dashboard/connect alias page must remain",
);

const dashboardLayout = read("src/app/dashboard/layout.tsx");
assert.match(dashboardLayout, /buyerNavGroups/);
assert.match(dashboardLayout, /navGroups=\{buyerNavGroups\}/);
assert.match(dashboardLayout, /PERSONAL_WORKSPACE_TITLE|title=\{PERSONAL_WORKSPACE_TITLE\}|title="Personal"/);
assert.match(dashboardLayout, /WorkspaceSwitcher/);

const connectLayout = read("src/app/connect/layout.tsx");
assert.match(connectLayout, /buyerNavGroups/);
assert.match(connectLayout, /PERSONAL_WORKSPACE_TITLE|title=\{PERSONAL_WORKSPACE_TITLE\}|title="Personal"/);
assert.match(connectLayout, /WorkspaceSwitcher/);
assert.match(connectLayout, /HostWorkspaceProvider/);

const dashboardSidebar = read("src/components/layout/DashboardSidebar.tsx");
const workspaceNavSections = read("src/components/layout/WorkspaceNavSections.tsx");
assert.match(dashboardSidebar, /w-80/);
assert.match(dashboardSidebar, /min-w-80/);
assert.match(dashboardSidebar, /max-w-80/);
assert.match(dashboardSidebar, /basis-80/);
assert.match(dashboardSidebar, /shrink-0/);
assert.match(dashboardSidebar, /max-h-\[calc\(100dvh-4rem\)\]/);
assert.match(dashboardSidebar, /overflow-y-auto/);
assert.match(dashboardSidebar, /overflow-x-hidden/);
assert.match(dashboardSidebar, /flex-col gap-4/);
assert.match(dashboardSidebar, /WorkspaceNavSections/);
assert.match(workspaceNavSections, /flex w-full list-none flex-col space-y-1/);
assert.match(workspaceNavSections, /flex w-full min-w-0 flex-col gap-4/);
assert.match(workspaceNavSections, /workspaceNavLinkClassName/);
assert.match(workspaceNavSections, /border-t border-border/);
assert.match(workspaceNavSections, /aria-expanded/);
assert.match(workspaceNavSections, /isNavItemActive/);
assert.match(workspaceNavSections, /w-full items-center justify-between/);
assert.doesNotMatch(
  dashboardSidebar,
  /overflow-x-auto|ScrollHintNav|flex-wrap|grid-cols|columns-/,
  "buyer sidebar must stay vertical with stable width",
);
assert.doesNotMatch(
  workspaceNavSections,
  /overflow-x-auto|ScrollHintNav|flex-wrap|grid-cols|columns-/,
  "workspace nav sections must stay vertical (no wrap/grid)",
);
// Nav item *lists* must stack; allow default flex on a single row's actions.
assert.doesNotMatch(
  workspaceNavSections,
  /<ul[^>]*flex-row|<ul[^>]*flex-wrap/,
  "nav item lists must not use horizontal or wrapping flex",
);

const dashboardTopbar = read("src/components/layout/DashboardTopbar.tsx");
assert.match(dashboardTopbar, /md:hidden/);
assert.match(dashboardTopbar, /WorkspaceNavSections/);
assert.match(dashboardTopbar, /groups/);
assert.match(dashboardTopbar, /resolveActiveNavItem|isNavItemActive/);
assert.match(dashboardTopbar, /flex-col gap-4 overflow-x-hidden/);
assert.match(dashboardTopbar, /variant="primary"/);
assert.match(dashboardTopbar, /Dashboard menu/);
assert.doesNotMatch(
  dashboardTopbar,
  /ThemeToggle/,
  "dashboard topbar must not duplicate the site header theme toggle",
);
assert.doesNotMatch(
  dashboardTopbar,
  /overflow-x-auto|ScrollHintNav|grid-cols|flex-wrap/,
  "mobile drawer must use the same vertical grouped nav",
);

const workspaceShell = read("src/components/layout/WorkspaceShell.tsx");
assert.match(workspaceShell, /navGroups/);
assert.match(
  workspaceShell,
  /DashboardSidebar[\s\S]*homeHref=\{homeHref\}/,
);
assert.match(
  workspaceShell,
  /DashboardTopbar[\s\S]*homeHref=\{homeHref\}/,
);
assert.doesNotMatch(
  workspaceShell,
  /ScrollHintNav|WorkspaceContentNav|overflow-x-auto.*nav/,
  "content area must not render workspace nav strip",
);

const breadcrumbs = read("src/lib/breadcrumbs.ts");
assert.match(breadcrumbs, /dashboard: "Personal"/);
assert.match(breadcrumbs, /team: "Workspaces"/);
assert.match(breadcrumbs, /ambassador: "Ambassadors"/);
assert.match(breadcrumbs, /desk: "Tickets & Entry"/);
assert.match(breadcrumbs, /OVERVIEW_HOME_HREFS/);
assert.match(breadcrumbs, /label: "Overview"/);
assert.match(breadcrumbs, /team: "Host Team"/);
assert.doesNotMatch(
  breadcrumbs,
  /label: ["']buyerNav|label: ["']hostNav|Buyer Nav|Host Nav/,
  "breadcrumbs must not expose internal nav identifiers",
);
assert.match(breadcrumbs, /clean === home/);

const ticketsPage = read("src/app/dashboard/tickets/page.tsx");
assert.doesNotMatch(
  ticketsPage,
  /buyerNav|AmbassadorDashNav|ScrollHintNav/,
  "tickets page must not duplicate workspace nav",
);

const dashboardHome = read("src/app/dashboard/page.tsx");
assert.match(dashboardHome, /PersonalCommandCenter/);
assert.doesNotMatch(
  dashboardHome,
  /MetricCard|Roles:/,
  "dashboard home is Personal Command Center (not metric dump)",
);

const navPreferences = read("src/lib/nav/nav-preferences.ts");
assert.match(navPreferences, /padeya:nav:collapse:/);
assert.match(navPreferences, /padeya:nav:favorites:/);
assert.match(navPreferences, /key\.startsWith\("host:"\)/);

const siteHeader = read("src/components/layout/SiteHeader.tsx");
assert.match(siteHeader, /PUBLIC_NAV|HeaderUserMenu/);
assert.match(siteHeader, /CreateEventCta/);
assert.match(siteHeader, /HeaderResourcesDropdown/);
assert.match(siteHeader, /HeaderUserMenu/);
assert.doesNotMatch(siteHeader, /HeaderWorkspaceButton/);
assert.doesNotMatch(
  siteHeader,
  /user\.full_name/,
  "SiteHeader must not render long user names as plain nav text",
);
assert.doesNotMatch(
  siteHeader,
  /loggedInNav/,
  "SiteHeader must not append role links into the public center nav",
);

const headerNav = read("src/components/layout/headerNav.ts");
assert.match(headerNav, /href: "\/events"/);
assert.match(headerNav, /href: "\/hosts"/);
assert.match(headerNav, /href: "\/fans"/);
assert.match(headerNav, /SPONSORSHIP_MARKETPLACE_PATH/);
assert.match(headerNav, /RESOURCES_NAV/);
assert.match(headerNav, /href: "\/blog"/);
assert.match(headerNav, /href: "\/support"/);
assert.match(headerNav, /href: "\/pricing"/);

const headerUserMenu = read("src/components/layout/HeaderUserMenu.tsx");
assert.match(headerUserMenu, /Personal dashboard/);
assert.match(headerUserMenu, /Host workspace/);
assert.match(headerUserMenu, /Admin panel/);
assert.match(headerUserMenu, /\/dashboard/);

const siteFooter = read("src/components/layout/SiteFooter.tsx");
assert.match(siteFooter, /Personal dashboard|Host workspace|Admin panel|Explore events/);
assert.match(siteFooter, /href: "\/blog"/);
assert.match(siteFooter, /href: "\/pricing"/);
assert.match(siteFooter, /href: "\/safety"/);
assert.match(siteFooter, /href: "\/accessibility"/);
assert.match(siteFooter, /href: "\/fans"/);

const createEventCta = read("src/components/layout/CreateEventCta.tsx");
assert.match(createEventCta, /canCreateEvents/);
assert.match(createEventCta, /\/host\/events\/new/);
assert.match(createEventCta, /\/host\/onboarding/);
assert.match(createEventCta, /login\?next=\/host\/onboarding/);
assert.match(createEventCta, /status: "hidden"/);
assert.match(createEventCta, /status: "onboarding"/);
assert.match(createEventCta, /status: "create"/);
assert.match(createEventCta, /status: "login"/);
assert.doesNotMatch(
  createEventCta,
  /href=["'`]\/dashboard/,
  "Create event CTA must not send users to Personal /dashboard",
);

const mobileBottomNav = read("src/components/layout/MobileBottomNav.tsx");
assert.match(mobileBottomNav, /Personal mobile navigation/);
assert.doesNotMatch(
  mobileBottomNav,
  /Buyer mobile navigation/,
  "mobile bottom nav chrome must say Personal, not Buyer",
);

const hostAccessLabels = read("src/lib/host-access.ts");
assert.match(hostAccessLabels, /PERSONAL_WORKSPACE_TITLE = "Personal"/);
assert.match(
  hostAccessLabels,
  /PERSONAL_WORKSPACE_SWITCHER_LABEL = "Personal account"/,
);
assert.match(hostAccessLabels, /Host: \$\{displayName\}/);
assert.match(hostAccessLabels, /workspaceSwitcherOptionLabel/);
assert.match(hostAccessLabels, /\(Owner\)/);
assert.match(hostAccessLabels, / · \$\{workspace\.role_label\}/);
assert.match(hostAccessLabels, /export function hostHomePathForWorkspace/);
assert.doesNotMatch(
  hostAccessLabels,
  /hostHomePathForWorkspace[\s\S]*return ["'`]\/host\/events["'`]/,
  "hostHomePathForWorkspace must not hardcode /host/events",
);

const switcher = read("src/components/hosts/WorkspaceSwitcher.tsx");
assert.match(switcher, /workspaceManagementHint/);
assert.match(switcher, /PERSONAL_WORKSPACE_SWITCHER_LABEL/);
assert.match(switcher, /workspaceSwitcherOptionLabel/);
assert.match(switcher, /Become a host/);
assert.match(switcher, /href="\/host\/onboarding"/);
assert.match(switcher, /router\.push\("\/dashboard"\)/);
assert.match(switcher, /writeWorkspaceMode/);
assert.match(switcher, /hostHomePathForWorkspace/);
assert.match(switcher, /setActiveHostId/);
assert.doesNotMatch(
  switcher,
  /workspaces\.length === 0\) return null/,
  "switcher must stay visible when user has zero host workspaces",
);
assert.doesNotMatch(
  switcher,
  /router\.push\(["'`]\/host\/events/,
  "switcher must not hardcode /host/events landing",
);
assert.doesNotMatch(
  switcher,
  /<option[^>]*>\s*Admin|value=["']admin["']|push\(["'`]\/admin/,
  "platform Admin must not be a workspace switcher option",
);
assert.doesNotMatch(
  switcher,
  /<option[^>]*>\s*Support|push\(["'`]\/support/,
  "Support must not be a workspace switcher option",
);

const hostWorkspace = read("src/lib/host-workspace.ts");
assert.match(hostWorkspace, /padeya-workspace-mode/);

const nextConfig = read("next.config.ts");
assert.match(nextConfig, /source: "\/dashboard\/merch"/);

console.log("buyer-dashboard-nav-smoke: ok");
