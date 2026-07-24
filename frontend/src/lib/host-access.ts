import type { HostWorkspace } from "@/lib/types/host-workspace";
import type { HostTeamPermissionKey } from "@/lib/types/lifecycle";

export function hasHostPermission(
  workspace: HostWorkspace | null | undefined,
  ...keys: HostTeamPermissionKey[]
): boolean {
  if (!workspace) return false;
  if (workspace.is_owner) return true;
  const p = workspace.permissions || {};
  return keys.some((key) => Boolean(p[key]));
}

export function canScanTickets(workspace: HostWorkspace | null): boolean {
  return hasHostPermission(
    workspace,
    "tickets.scan_qr",
    "tickets.check_in",
  );
}

export function canScanMerch(workspace: HostWorkspace | null): boolean {
  return hasHostPermission(
    workspace,
    "merch.scan_pickup_qr",
    "merch.mark_picked_up",
  );
}

export function canEditEvents(workspace: HostWorkspace | null): boolean {
  return hasHostPermission(workspace, "events.edit", "events.create");
}

export function canViewFinanceSummary(
  workspace: HostWorkspace | null,
): boolean {
  return hasHostPermission(
    workspace,
    "finance.view_sales_summary",
    "finance.view_payouts",
  );
}

export function canCreateEvents(workspace: HostWorkspace | null): boolean {
  return hasHostPermission(workspace, "events.create", "events.edit");
}

export function canCreateMerch(workspace: HostWorkspace | null): boolean {
  return hasHostPermission(workspace, "merch.create", "merch.edit");
}

export function canInviteTeam(workspace: HostWorkspace | null): boolean {
  return hasHostPermission(workspace, "team.invite");
}

export function canManageAmbassadors(workspace: HostWorkspace | null): boolean {
  return hasHostPermission(
    workspace,
    "ambassadors.create_campaigns",
    "ambassadors.view",
    "ambassadors.edit_campaigns",
  );
}

export function canViewHostAnalytics(workspace: HostWorkspace | null): boolean {
  return hasHostPermission(
    workspace,
    "analytics.view_events",
    "analytics.view_merch",
    "analytics.view_sponsors",
  );
}

export function canViewSponsorships(workspace: HostWorkspace | null): boolean {
  return hasHostPermission(workspace, "sponsors.view", "sponsors.manage_slots");
}

export function canManageSponsorshipSlots(
  workspace: HostWorkspace | null,
): boolean {
  return hasHostPermission(workspace, "sponsors.manage_slots");
}

export function canViewEvents(workspace: HostWorkspace | null): boolean {
  return (
    hasHostPermission(workspace, "events.view", "events.edit", "events.create") ||
    canScanTickets(workspace) ||
    canScanMerch(workspace)
  );
}

/** Chrome label for the host workspace switcher / shell title. */
export function hostWorkspaceChromeTitle(displayName: string): string {
  return `Host: ${displayName}`;
}

/** Base switcher/host label: `Host: {display_name}`. */
export function workspaceOptionLabel(workspace: HostWorkspace): string {
  return hostWorkspaceChromeTitle(workspace.display_name);
}

/**
 * Full workspace switcher option text.
 * Examples: `Host: DJ Maze`, `Host: DJ Maze (Owner)`, `Host: DJ Maze · Scanner`.
 */
export function workspaceSwitcherOptionLabel(workspace: HostWorkspace): string {
  const base = workspaceOptionLabel(workspace);
  if (workspace.is_owner) return `${base} (Owner)`;
  if (workspace.role_label) return `${base} · ${workspace.role_label}`;
  return base;
}

/**
 * Personal workspace mode chrome label.
 * Use for: sidebar title, mobile drawer title, breadcrumb root,
 * WorkspaceShell title, and any mode indicator.
 * Do not use for purchaser/order “buyer”, Fan Passport/Connect, or check-in attendee copy.
 */
export const PERSONAL_WORKSPACE_TITLE = "Personal";

/** Workspace switcher / chooser option (pairs with Host: {name}). */
export const PERSONAL_WORKSPACE_SWITCHER_LABEL = "Personal account";

/** Context line under the workspace switcher (mobile dashboard toolbar). */
export function workspaceManagementHint(params: {
  surface: "personal" | "host" | "admin" | "support";
  hostDisplayName?: string | null;
  hasOtherWorkspaces?: boolean;
}): string {
  switch (params.surface) {
    case "admin":
      return "You're managing the Admin panel. Pick another workspace above to leave.";
    case "support":
      return "You're managing the Support desk. Pick another workspace above to leave.";
    case "host": {
      const name = (params.hostDisplayName || "Host").trim();
      return `You're managing the ${name} workspace. Switch to Personal account for your fan tools.`;
    }
    default:
      if (params.hasOtherWorkspaces) {
        return "You're managing your personal account. Switch workspace above to open a host or staff desk.";
      }
      return "You're managing your personal account.";
  }
}

/** Ticket scanner with no merch desk grants — View + Scanner actions only on assigned events. */
export function isScannerOnlyStaff(workspace: HostWorkspace | null): boolean {
  if (!workspace || workspace.is_owner) return false;
  if (workspace.role === "scanner") return true;
  return (
    isDeskFocusedStaff(workspace) &&
    canScanTickets(workspace) &&
    !canScanMerch(workspace)
  );
}

/** Merch pickup staff with no ticket scan grants — Merch / Pickup tools only. */
export function isMerchOnlyStaff(workspace: HostWorkspace | null): boolean {
  if (!workspace || workspace.is_owner) return false;
  if (workspace.role === "merch_staff") return true;
  return (
    isDeskFocusedStaff(workspace) &&
    canScanMerch(workspace) &&
    !canScanTickets(workspace)
  );
}

/** Scanner / merch staff with no grow or manage grants — minimal sidebar + desk landing. */
export function isDeskFocusedStaff(workspace: HostWorkspace | null): boolean {
  if (!workspace || workspace.is_owner) return false;
  if (!canScanTickets(workspace) && !canScanMerch(workspace)) return false;

  const p = workspace.permissions || {};
  const hasBroaderAccess = Boolean(
    p["events.edit"] ||
      p["events.create"] ||
      p["team.view"] ||
      p["team.invite"] ||
      p["ambassadors.view"] ||
      p["sponsors.view"] ||
      p["analytics.view_events"] ||
      p["analytics.view_merch"] ||
      p["analytics.view_sponsors"] ||
      p["finance.view_sales_summary"],
  );
  return !hasBroaderAccess;
}

/**
 * Role-aware host landing after workspace switch / invite accept.
 * Callers must use this helper — never hardcode `/host/events`.
 *
 * | Actor | Path |
 * | --- | --- |
 * | Host owner | `/host` |
 * | Scanner / merch desk-focused staff | `/host/desk` |
 * | `scanner` / `merch_staff` without broader grants | `/host/desk` |
 * | `sponsor_manager` with sponsorship grants | `/host/sponsorships` |
 * | Viewer (read-only), event manager, host admin, other | `/host` |
 *
 * Platform admin (`/admin`) and Support (`/support`) are separate shells —
 * not workspace-switcher destinations and not routed here.
 *
 * @see docs/HOST_AREA_AUDIT.md · docs/FRONTEND_ROUTES.md
 */

/**
 * Host team member with sponsorship-desk grants only (no events, desk, or team admin).
 * Demo: `sponsor-observer@demo.padeye.test` on DJ Maze — not a sponsor brand login.
 */
export function isHostSponsorDeskOnlyMember(
  workspace: HostWorkspace | null,
): boolean {
  if (!workspace || workspace.is_owner) return false;
  if (!canViewSponsorships(workspace)) return false;
  if (canViewEvents(workspace)) return false;
  if (canScanTickets(workspace) || canScanMerch(workspace)) return false;
  if (canCreateEvents(workspace) || canInviteTeam(workspace)) return false;
  if (canManageAmbassadors(workspace) || canViewFinanceSummary(workspace)) {
    return false;
  }
  return true;
}

export function hostHomePathForWorkspace(workspace: HostWorkspace): string {
  if (workspace.is_owner) return "/host";
  if (isDeskFocusedStaff(workspace)) return "/host/desk";
  if (
    (workspace.role === "scanner" || workspace.role === "merch_staff") &&
    !hasHostPermission(
      workspace,
      "events.edit",
      "events.create",
      "team.invite",
      "ambassadors.view",
      "sponsors.view",
    )
  ) {
    return "/host/desk";
  }
  if (
    workspace.role === "sponsor_manager" &&
    canViewSponsorships(workspace)
  ) {
    return "/host/sponsorships";
  }
  if (isHostSponsorDeskOnlyMember(workspace)) {
    return "/host/sponsorships";
  }
  // event_manager, viewer, host admin, and other team members → Command Center / member overview
  return "/host";
}

/** Team member with read-only grants (viewer preset or no mutating toggles). */
export function isHostReadOnlyMember(
  workspace: HostWorkspace | null,
): boolean {
  if (!workspace || workspace.is_owner) return false;
  if (workspace.role === "viewer") return true;
  return !hasHostPermission(
    workspace,
    "events.create",
    "events.edit",
    "events.publish",
    "events.cancel",
    "events.archive",
    "tickets.scan_qr",
    "tickets.check_in",
    "tickets.manage_pricing",
    "tickets.manage_capacity",
    "merch.create",
    "merch.edit",
    "merch.scan_pickup_qr",
    "merch.mark_picked_up",
    "team.invite",
    "team.edit_permissions",
    "team.remove_members",
    "sponsors.manage_slots",
    "sponsors.accept_or_reject",
    "sponsors.reply",
    "ambassadors.create_campaigns",
    "ambassadors.edit_campaigns",
    "ambassadors.approve_rewards",
    "finance.manage_payouts",
  );
}

/**
 * Whether a team member may open a host path.
 * Owners always pass. Unknown owner-only tools default to deny for members.
 */
export function canAccessHostPath(
  pathname: string,
  workspace: HostWorkspace | null,
): boolean {
  if (!workspace) return false;
  if (workspace.is_owner) return true;

  const path = pathname.split("?")[0] || pathname;
  const p = workspace.permissions || {};

  if (
    path === "/host" ||
    path === "/host/" ||
    path.startsWith("/host/access-denied") ||
    path.startsWith("/host/onboarding") ||
    path.startsWith("/host/desk") ||
    path.startsWith("/host/support")
  ) {
    return true;
  }

  if (path.startsWith("/host/roadmap")) {
    if (isDeskFocusedStaff(workspace) || isHostReadOnlyMember(workspace)) {
      return false;
    }
    return hasHostPermission(
      workspace,
      "events.edit",
      "events.create",
      "team.invite",
    );
  }

  // Bank / payout APIs remain owner-scoped in v1 — hide even if flags are stored.
  if (path.startsWith("/host/payouts") || path.startsWith("/host/bank-accounts")) {
    return false;
  }

  if (path.startsWith("/host/team")) {
    return Boolean(
      p["team.view"] ||
        p["team.invite"] ||
        p["team.edit_permissions"] ||
        p["team.remove_members"],
    );
  }

  if (path.startsWith("/host/settings")) {
    return Boolean(p["team.view"] || p["team.edit_permissions"]);
  }

  if (
    path.includes("/check-in") ||
    path.includes("/offline-check-in") ||
    path.startsWith("/staff/check-in")
  ) {
    return canScanTickets(workspace);
  }

  if (path.includes("/merchandise/fulfillment")) {
    return canScanMerch(workspace) || Boolean(p["merch.view"]);
  }

  if (
    path.startsWith("/host/merchandise") ||
    path.includes("/merchandise") ||
    path.includes("/merch") ||
    path.includes("/bundles") ||
    path.includes("/post-event-drops")
  ) {
    return Boolean(
      p["merch.view"] ||
        p["merch.create"] ||
        p["merch.edit"] ||
        canScanMerch(workspace),
    );
  }

  if (path === "/host/events/new" || /\/host\/events\/[^/]+\/edit/.test(path)) {
    return canEditEvents(workspace);
  }

  if (/\/host\/events\/[^/]+\/earnings/.test(path)) {
    return Boolean(
      p["finance.view_sales_summary"] || p["finance.view_payouts"],
    );
  }

  if (path.startsWith("/host/events")) {
    return canViewEvents(workspace);
  }

  if (path.startsWith("/host/messages")) {
    return Boolean(p["messages.view"] || p["messages.reply"]);
  }

  if (path.startsWith("/host/sponsorships")) {
    return Boolean(p["sponsors.view"] || p["sponsors.manage_slots"]);
  }

  if (path.startsWith("/host/analytics")) {
    return Boolean(
      p["analytics.view_events"] ||
        p["analytics.view_merch"] ||
        p["analytics.view_sponsors"],
    );
  }

  if (path.startsWith("/host/earnings")) {
    return Boolean(
      p["finance.view_sales_summary"] || p["finance.view_payouts"],
    );
  }

  if (path.startsWith("/host/audience") || path.startsWith("/host/followers")) {
    return Boolean(p["events.view"] || p["analytics.view_events"]);
  }

  if (path.startsWith("/host/ambassadors/payouts")) {
    return Boolean(
      p["ambassadors.view_payouts"] ||
        p["ambassadors.mark_rewards_paid"] ||
        p["finance.manage_payouts"] ||
        p["finance.view_payouts"],
    );
  }

  if (path.startsWith("/host/ambassadors")) {
    return Boolean(
      p["ambassadors.view"] ||
        p["ambassadors.create_campaigns"] ||
        p["ambassadors.edit_campaigns"] ||
        p["ambassadors.pause_campaigns"] ||
        p["ambassadors.view_conversions"] ||
        p["ambassadors.view_payouts"] ||
        p["ambassadors.approve_rewards"] ||
        p["ambassadors.mark_rewards_paid"] ||
        p["ambassadors.reverse_rewards"] ||
        p["events.edit"] ||
        p["events.create"],
    );
  }

  // Owner-leaning studio tools — require explicit admin-ish grants.
  if (
    path.startsWith("/host/vault") ||
    path.startsWith("/host/legacy") ||
    path.startsWith("/host/promos") ||
    path.startsWith("/host/templates") ||
    path.startsWith("/host/ai") ||
    path.startsWith("/host/announcements") ||
    path.startsWith("/host/reviews")
  ) {
    return Boolean(
      p["events.edit"] ||
        p["events.create"] ||
        p["team.edit_permissions"] ||
        p["finance.view_sales_summary"],
    );
  }

  return false;
}
