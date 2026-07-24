/**
 * Workspace chrome unification — privacy / permission boundary locks.
 * UI unification must not mix personal, host, admin, support, or public planes.
 * Run: npm run test:workspace-privacy
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

function extractArrayBlock(source, exportName) {
  const match = source.match(
    new RegExp(`export const ${exportName}: NavItem\\[] = \\[([\\s\\S]*?)\\];`),
  );
  assert.ok(match, `${exportName} array must exist`);
  return match[1];
}

// --- Nav configs stay mode-pure ---
const workspaceNav = read("src/lib/nav/workspace.ts");
const buyerNavBlock = extractArrayBlock(workspaceNav, "buyerNav");
const hostNavBlock = extractArrayBlock(workspaceNav, "hostNav");

assert.doesNotMatch(
  buyerNavBlock,
  /href: "\/host\//,
  "personal nav must not include /host paths",
);
assert.doesNotMatch(
  buyerNavBlock,
  /payouts|bank-accounts|finance/,
  "personal nav must not include host finance tools",
);
assert.doesNotMatch(
  buyerNavBlock,
  /href: "\/host\/desk"|href: "\/host\/team"|href: "\/host\/payouts"/,
  "personal nav must not surface scanner, host team, or host finance tools",
);
assert.doesNotMatch(
  buyerNavBlock,
  /href: "\/admin|href: "\/support"/,
  "personal nav must not include admin/support shells",
);
assert.match(buyerNavBlock, /href: "\/dashboard\/tickets"/);
assert.match(
  buyerNavBlock,
  /href: "\/dashboard\/team"/,
  "Personal Workspaces bridge stays on /dashboard/team (not /host/team tools)",
);
assert.doesNotMatch(
  hostNavBlock,
  /href: "\/dashboard\//,
  "host nav must not include /dashboard paths",
);
assert.doesNotMatch(
  hostNavBlock,
  /href: "\/dashboard\/tickets"/,
  "host nav must not surface buyer tickets",
);
assert.match(hostNavBlock, /href: "\/host\/desk"/);
assert.match(hostNavBlock, /href: "\/host\/team"/);

// --- Permission gates intact ---
const hostAccess = read("src/lib/host-access.ts");
assert.match(hostAccess, /export function canAccessHostPath/);
assert.match(
  hostAccess,
  /path\.startsWith\("\/host\/payouts"\)[\s\S]*?return false/,
);
assert.match(
  hostAccess,
  /path\.startsWith\("\/host\/bank-accounts"\)[\s\S]*?return false/,
);
assert.match(hostAccess, /path\.startsWith\("\/host\/team"\)/);
assert.match(hostAccess, /isDeskFocusedStaff/);
assert.match(hostAccess, /isHostReadOnlyMember/);

const hostNavFilter = read("src/lib/nav/host-nav.ts");
assert.match(hostNavFilter, /filterGroupsForDeskStaff/);
assert.match(hostNavFilter, /navGroupsForWorkspace/);
assert.match(
  hostNavFilter,
  /deskFocused && group\.label === "Grow"\) return false/,
);
assert.match(
  hostNavFilter,
  /deskFocused && group\.label === "Manage"\) return false/,
);

const hostGuard = read("src/components/hosts/HostAccessGuard.tsx");
assert.match(hostGuard, /canAccessHostPath/);
assert.match(hostGuard, /access-denied/);

const hostLayout = read("src/app/host/layout.tsx");
assert.match(hostLayout, /HostAccessGuard/);
assert.match(hostLayout, /navGroupsForWorkspace/);
assert.doesNotMatch(hostLayout, /buyerNav/);

const personalLayout = read("src/app/dashboard/layout.tsx");
assert.match(personalLayout, /buyerNav/);
assert.doesNotMatch(personalLayout, /hostNav|navGroupsForWorkspace/);

// --- Route / shell separation ---
assert.ok(exists("src/app/dashboard/layout.tsx"));
assert.ok(exists("src/app/host/layout.tsx"));
assert.ok(exists("src/app/admin/layout.tsx"));
assert.ok(exists("src/app/support/layout.tsx"));
assert.ok(exists("src/app/support/(staff)/layout.tsx"));

const adminLayout = read("src/app/admin/layout.tsx");
assert.match(adminLayout, /navForAdmin|adminNav/);
assert.match(adminLayout, /homeHref="\/admin"/);
assert.doesNotMatch(
  adminLayout,
  /WorkspaceSwitcher/,
  "admin shell must not mount Personal/Host workspace switcher",
);
assert.doesNotMatch(adminLayout, /buyerNav|hostNav/);

const supportLayout = read("src/app/support/(staff)/layout.tsx");
assert.match(supportLayout, /supportNav/);
assert.match(supportLayout, /homeHref="\/support\/desk"/);
assert.doesNotMatch(
  supportLayout,
  /WorkspaceSwitcher/,
  "support shell must not mount Personal/Host workspace switcher",
);
assert.doesNotMatch(supportLayout, /buyerNav|hostNav/);

const publicSupportLayout = read("src/app/support/layout.tsx");
assert.doesNotMatch(
  publicSupportLayout,
  /RequireAuth/,
  "public /support must not require staff auth",
);

const switcher = read("src/components/hosts/WorkspaceSwitcher.tsx");
assert.doesNotMatch(
  switcher,
  /<option[^>]*>\s*Admin|value=["']admin["']|push\(["'`]\/admin/,
  "Admin must not be a workspace switcher option",
);
assert.doesNotMatch(
  switcher,
  /<option[^>]*>\s*Support|push\(["'`]\/support/,
  "Support must not be a workspace switcher option",
);
assert.match(switcher, /workspaceManagementHint/);
assert.match(switcher, /You're managing your personal account/);
assert.match(switcher, /PERSONAL_WORKSPACE_SWITCHER_LABEL|Personal account/);
assert.match(switcher, /hostHomePathForWorkspace/);
assert.doesNotMatch(
  switcher,
  /canAccessHostPath|canCreateEvents/,
  "switcher must not reimplement host permission grants",
);

// --- Public Legacy / profile outside private workspace prefixes ---
const workspacePath = read("src/components/layout/workspacePath.ts");
assert.match(workspacePath, /WORKSPACE_PREFIXES/);
assert.match(workspacePath, /"\/dashboard"/);
assert.match(workspacePath, /"\/host"/);
assert.match(workspacePath, /"\/admin"/);
assert.match(workspacePath, /"\/support"/);
assert.doesNotMatch(
  workspacePath,
  /"\/u"|"\/@"/,
  "public /u and /@ must not be workspace shell prefixes",
);

assert.ok(exists("src/app/u/[username]/page.tsx"));
const publicLegacy = read("src/app/u/[username]/page.tsx");
assert.match(publicLegacy, /LegacyPublicPageRenderer/);
assert.doesNotMatch(
  publicLegacy,
  /WorkspaceShell|DashboardSidebar|buyerNav|hostNav/,
  "public Legacy page must not mount private workspace shell",
);
assert.ok(
  !exists("src/app/u/layout.tsx"),
  "public /u tree must not have a private workspace layout",
);

const middleware = read("src/middleware.ts");
assert.match(middleware, /\/@/);
assert.match(middleware, /\/u\/\$\{username\}/);

assert.ok(exists("src/app/host/legacy/page.tsx"));
const hostLegacy = read("src/app/host/legacy/page.tsx");
assert.doesNotMatch(
  hostLegacy,
  /LegacyPublicPageRenderer/,
  "host Legacy studio must stay private (not the public renderer)",
);

// --- Host finance stays owner-gated on host routes ---
assert.ok(exists("src/app/host/payouts/page.tsx"));
const hostPayouts = read("src/app/host/payouts/page.tsx");
assert.match(hostPayouts, /RequireHost|RequireHostOwner|is_owner/);

// --- Redirect policy: keep /host canonical; no /dashboard/host ---
const nextConfig = read("next.config.ts");
assert.match(
  nextConfig,
  /source: "\/host\/dashboard"[\s\S]*?destination: "\/host"/,
);
assert.doesNotMatch(
  nextConfig,
  /source: "\/dashboard\/host|destination: "\/dashboard\/host/,
  "privacy/chrome unification must not nest host under /dashboard/host",
);
assert.ok(!exists("src/app/dashboard/host"));

console.log("workspace-privacy-smoke: ok");
