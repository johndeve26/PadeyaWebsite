/**
 * Support Center smoke checks — routes, nav, API helpers.
 * Run: npm run test:support
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

const required = [
  "src/app/support/page.tsx",
  "src/app/support/new/page.tsx",
  "src/app/support/tickets/lookup/page.tsx",
  "src/app/support/tickets/[ticketNumber]/page.tsx",
  "src/app/support/(staff)/layout.tsx",
  "src/app/support/(staff)/desk/page.tsx",
  "src/app/support/(staff)/cases/page.tsx",
  "src/app/support/(staff)/cases/[id]/page.tsx",
  "src/app/support/(staff)/cases/new/page.tsx",
  "src/app/support/(staff)/refunds/page.tsx",
  "src/app/dashboard/support/page.tsx",
  "src/app/dashboard/support/new/page.tsx",
  "src/app/dashboard/support/[ticketId]/page.tsx",
  "src/app/host/support/page.tsx",
  "src/app/host/support/new/page.tsx",
  "src/app/host/support/[ticketId]/page.tsx",
  "src/app/admin/support/page.tsx",
  "src/app/admin/support/[ticketId]/page.tsx",
  "src/app/admin/support/settings/page.tsx",
  "src/components/support/SupportTicketForm.tsx",
  "src/components/support/SupportConversation.tsx",
  "src/components/support/SupportTicketListItem.tsx",
  "src/lib/support-api.ts",
  "src/lib/types/support.ts",
  "src/lib/support-ui.ts",
];

for (const rel of required) {
  assert.ok(exists(rel), `missing ${rel}`);
}

const publicLanding = read("src/app/support/page.tsx");
assert.match(publicLanding, /SupportGuidedFlowPage|Support Center/);
assert.match(
  read("src/components/support/SupportGuidedFlow.tsx"),
  /\/support\/tickets\/lookup/,
);
assert.doesNotMatch(publicLanding, /RequireAuth/);

const publicLayout = read("src/app/support/layout.tsx");
assert.doesNotMatch(publicLayout, /RequireAuth/);
assert.doesNotMatch(publicLayout, /supportNav/);

const staffLayout = read("src/app/support/(staff)/layout.tsx");
assert.match(staffLayout, /RequireAuth/);
assert.match(staffLayout, /supportNav/);
assert.match(staffLayout, /homeHref="\/support\/desk"/);

const api = read("src/lib/support-api.ts");
assert.match(api, /\/support\/tickets/);
assert.match(api, /\/support\/tickets\/public/);
assert.match(api, /\/support\/tickets\/by-number/);
assert.match(api, /\/admin\/support\/tickets/);
assert.match(api, /\/admin\/support\/settings/);
assert.match(api, /createPublicSupportTicket/);
assert.match(api, /fetchAdminSupportTickets/);
assert.match(api, /adminReplySupportTicket/);
assert.match(api, /adminAddInternalNote/);
assert.match(api, /website/);

const types = read("src/lib/types/support.ts");
assert.match(types, /requester_context/);
assert.match(types, /ticket_number/);
assert.match(types, /SupportSettings/);
assert.match(types, /related_host_id/);

const form = read("src/components/support/SupportTicketForm.tsx");
assert.match(form, /name=["']website["']/);
assert.match(form, /createPublicSupportTicket/);
assert.match(form, /createSupportTicket/);

const conversation = read("src/components/support/SupportConversation.tsx");
assert.match(conversation, /NEVER render internal_notes/);
assert.doesNotMatch(conversation, /internal_notes\.map/);

const dashboardDetail = read("src/app/dashboard/support/[ticketId]/page.tsx");
assert.doesNotMatch(dashboardDetail, /internal_notes\.map/);
assert.match(dashboardDetail, /replySupportTicket/);

const hostPage = read("src/app/host/support/page.tsx");
assert.match(hostPage, /requesterContext|requester_context|host/);
assert.match(hostPage, /\/host\/support\/new/);

const hostNew = read("src/app/host/support/new/page.tsx");
assert.match(hostNew, /requesterContext="host"/);
assert.match(hostNew, /relatedHostId/);

const adminQueue = read("src/app/admin/support/page.tsx");
assert.match(adminQueue, /fetchAdminSupportTickets/);
assert.match(adminQueue, /status/);
assert.match(adminQueue, /priority/);
assert.match(adminQueue, /category/);
assert.match(adminQueue, /\/admin\/support\/settings/);
assert.match(adminQueue, /\/admin\/support\/ai-summary/);

const adminDetail = read("src/app/admin/support/[ticketId]/page.tsx");
assert.match(adminDetail, /Reply/);
assert.match(adminDetail, /Internal note/);
assert.match(adminDetail, /adminEscalateSupportTicket/);
assert.match(adminDetail, /adminReopenSupportTicket/);
assert.match(adminDetail, /adminResolveSupportTicket/);
assert.match(adminDetail, /adminCloseSupportTicket/);

const nav = read("src/lib/nav/workspace.ts");
assert.match(nav, /href: "\/dashboard\/support"/);
assert.match(nav, /href: "\/host\/support"/);
assert.match(nav, /href: "\/support\/desk"/);
assert.match(nav, /admin\.support\.view/);
assert.doesNotMatch(
  nav,
  /supportNav: NavItem\[] = \[[\s\S]*?href: "\/support"/,
);

const footer = read("src/components/layout/SiteFooter.tsx");
assert.match(footer, /href: "\/support"/);

const headerNav = read("src/components/layout/headerNav.ts");
assert.match(headerNav, /RESOURCES_NAV/);
assert.match(headerNav, /RESOURCES_SUPPORT/);
assert.match(headerNav, /href: "\/support"/);
assert.match(
  read("src/components/layout/HeaderResourcesDropdown.tsx"),
  /ResourcesMegaPanel/,
);
assert.match(
  read("src/components/layout/ResourcesMegaPanel.tsx"),
  /RESOURCES_SUPPORT/,
);

const workspacePath = read("src/components/layout/workspacePath.ts");
assert.match(workspacePath, /\/support\/tickets/);
assert.match(workspacePath, /return false/);

console.log("support-smoke: ok");
