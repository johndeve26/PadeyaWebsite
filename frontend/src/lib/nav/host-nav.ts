/**
 * Host sidebar filter — permission + desk-focused IA.
 * Personal (`buyerNav`) stays in `workspace.ts`; never merge the two trees here.
 */
import type { NavGroup, NavItem } from "@/lib/nav/workspace";
import { flattenNavGroups, hostNavGroups } from "@/lib/nav/workspace";
import {
  canScanMerch,
  canScanTickets,
  canViewEvents,
  hasHostPermission,
  isDeskFocusedStaff,
  isHostReadOnlyMember,
} from "@/lib/host-access";
import type { HostWorkspace } from "@/lib/types/host-workspace";

export function canSeeNavHref(workspace: HostWorkspace, href: string): boolean {
  if (workspace.is_owner) return true;
  const p = workspace.permissions || {};

  switch (href) {
    case "/host":
      return true;
    case "/host/notifications":
      return true;
    case "/host/roadmap":
      if (isHostReadOnlyMember(workspace)) return false;
      return hasHostPermission(
        workspace,
        "events.edit",
        "events.create",
        "team.invite",
      );
    case "/host/desk":
      return canScanTickets(workspace) || canScanMerch(workspace);
    case "/host/events":
      return canViewEvents(workspace);
    case "/host/merchandise":
      return Boolean(
        p["merch.view"] ||
          p["merch.create"] ||
          p["merch.edit"] ||
          canScanMerch(workspace),
      );
    case "/host/messages":
      return Boolean(p["messages.view"] || p["messages.reply"]);
    case "/host/ambassadors":
      return hasHostPermission(
        workspace,
        "ambassadors.view",
        "ambassadors.create_campaigns",
        "ambassadors.edit_campaigns",
        "events.edit",
      );
    case "/host/sponsorships":
      return Boolean(p["sponsors.view"] || p["sponsors.manage_slots"]);
    case "/host/audience":
      return Boolean(p["events.view"] || p["analytics.view_events"]);
    case "/host/legacy":
    case "/host/vault":
      return hasHostPermission(
        workspace,
        "events.edit",
        "events.create",
        "team.edit_permissions",
      );
    case "/host/analytics":
      return hasHostPermission(
        workspace,
        "analytics.view_events",
        "analytics.view_merch",
        "analytics.view_sponsors",
      );
    case "/host/team":
      return hasHostPermission(
        workspace,
        "team.view",
        "team.invite",
        "team.edit_permissions",
        "team.remove_members",
      );
    case "/host/settings":
      return Boolean(p["team.view"] || p["team.edit_permissions"]);
    case "/host/support":
      return (
        workspace.is_owner ||
        Boolean(p["messages.view"] || p["messages.reply"])
      );
    default:
      return false;
  }
}

function filterGroupsForDeskStaff(
  groups: NavGroup[],
  workspace: HostWorkspace,
): NavGroup[] {
  const operateItems: NavItem[] = [];
  for (const group of groups) {
    if (group.label !== "Operate") continue;
    for (const item of group.items) {
      if (item.href === "/host/desk" || item.href === "/host/events") {
        operateItems.push(item);
      }
    }
  }
  const merchItem =
    canScanMerch(workspace) || Boolean(workspace.permissions?.["merch.view"])
      ? groups
          .find((g) => g.label === "Operate")
          ?.items.find((i) => i.href === "/host/merchandise")
      : undefined;

  const operate: NavItem[] = [...operateItems];
  if (merchItem) operate.push(merchItem);
  if (operate.length === 0) return [];
  return [{ label: "Operate", items: operate }];
}

/** Grouped nav for the active workspace — members see permission-gated links only. */
export function navGroupsForWorkspace(
  workspace: HostWorkspace | null,
): NavGroup[] {
  if (!workspace || workspace.is_owner) return hostNavGroups;

  const deskFocused = isDeskFocusedStaff(workspace);
  const source = deskFocused
    ? filterGroupsForDeskStaff(hostNavGroups, workspace)
    : hostNavGroups;

  return source
    .map((group) => ({
      label: group.label,
      items: group.items.filter((item) => {
        if (deskFocused && item.href === "/host/roadmap") return false;
        if (deskFocused && group.label === "Grow") return false;
        if (deskFocused && group.label === "Manage") return false;
        if (deskFocused && item.href === "/host/messages") {
          return canSeeNavHref(workspace, item.href);
        }
        return canSeeNavHref(workspace, item.href);
      }),
    }))
    .filter((group) => group.items.length > 0);
}

/** Nav for the active workspace — flat list for mobile topbar. */
export function navForWorkspace(workspace: HostWorkspace | null): NavItem[] {
  return flattenNavGroups(navGroupsForWorkspace(workspace));
}
