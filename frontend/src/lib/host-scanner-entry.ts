import type { User } from "@/lib/auth/types";
import { userHasRole } from "@/lib/auth/permissions";
import { canScanMerch, canScanTickets } from "@/lib/host-access";
import type { HostWorkspace } from "@/lib/types/host-workspace";
import { userHasRestriction } from "@/lib/user-restrictions";

const LAST_SCANNER_KEY = "padeya.host.last_scanner_event";
const LAST_PICKUP_EVENT_KEY = "padeya.host.last_pickup_event";

export function rememberScannerEvent(eventId: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(LAST_SCANNER_KEY, eventId);
  } catch {
    // ignore
  }
}

export function rememberPickupEvent(eventId: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(LAST_PICKUP_EVENT_KEY, eventId);
  } catch {
    // ignore
  }
}

function readLastScannerEvent(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(LAST_SCANNER_KEY);
  } catch {
    return null;
  }
}

function readLastPickupEvent(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(LAST_PICKUP_EVENT_KEY);
  } catch {
    return null;
  }
}

export type HostScanHeaderAction = {
  id: "ticket" | "pickup";
  label: string;
  href: string;
};

function hostEventIdFromPath(pathname: string): string | null {
  const match = pathname.match(/\/host\/events\/([^/]+)/);
  const id = match?.[1];
  if (!id || id === "new") return null;
  return id;
}

function ticketScannerHref(
  user: User,
  pathname: string,
): string {
  const staffOnly =
    userHasRole(user, "host_staff") && !userHasRole(user, "host", "super_admin");
  const checkInMatch = pathname.match(/\/(?:host\/events|staff\/check-in)\/([^/]+)/);
  const pathEventId =
    checkInMatch?.[1] && checkInMatch[1] !== "new" ? checkInMatch[1] : null;
  if (pathEventId) rememberScannerEvent(pathEventId);
  const eventId = pathEventId ?? readLastScannerEvent();
  if (eventId) {
    return staffOnly
      ? `/staff/check-in/${eventId}`
      : `/host/events/${eventId}/check-in`;
  }
  return staffOnly ? "/host/desk" : "/host/events";
}

function pickupScannerHref(pathname: string): string {
  const fromMerch = pathname.match(
    /\/host\/events\/([^/]+)\/merchandise/,
  )?.[1];
  const pathEventId =
    fromMerch && fromMerch !== "new" ? fromMerch : hostEventIdFromPath(pathname);
  if (pathEventId) rememberPickupEvent(pathEventId);
  const eventId = pathEventId ?? readLastPickupEvent();
  if (eventId) {
    return `/host/events/${eventId}/merchandise/fulfillment`;
  }
  return "/host/merchandise/fulfillment";
}

function canUseTicketScanner(
  user: User,
  workspace: HostWorkspace | null | undefined,
): boolean {
  if (userHasRestriction(user, "cannot_scan_tickets")) return false;
  if (!workspace) {
    return userHasRole(user, "host", "super_admin");
  }
  return workspace.is_owner || canScanTickets(workspace);
}

function canUsePickupScanner(
  workspace: HostWorkspace | null | undefined,
  user: User,
): boolean {
  if (!workspace) {
    return userHasRole(user, "host", "super_admin");
  }
  return workspace.is_owner || canScanMerch(workspace);
}

/** Mobile header scan shortcuts (ticket door + merch pickup). */
export function hostScanHeaderActions(
  user: User | null | undefined,
  pathname: string,
  workspace: HostWorkspace | null | undefined,
): HostScanHeaderAction[] {
  if (!user) return [];
  if (!userHasRole(user, "host", "host_staff", "super_admin")) return [];
  if (pathname.startsWith("/admin") || pathname.startsWith("/dashboard")) {
    return [];
  }

  const onTicketScanner =
    pathname.includes("/check-in") && !pathname.includes("offline-check-in");
  const onPickupScanner = pathname.includes("/merchandise/fulfillment");

  const actions: HostScanHeaderAction[] = [];

  if (!onTicketScanner && canUseTicketScanner(user, workspace)) {
    actions.push({
      id: "ticket",
      label: "Scan ticket",
      href: ticketScannerHref(user, pathname),
    });
  }

  if (!onPickupScanner && canUsePickupScanner(workspace, user)) {
    actions.push({
      id: "pickup",
      label: "Scan merch",
      href: pickupScannerHref(pathname),
    });
  }

  return actions;
}

/** @deprecated Use hostScanHeaderActions */
export function hostScannerEntryForUser(
  user: User | null | undefined,
  pathname: string,
): { href: string } | null {
  const actions = hostScanHeaderActions(user, pathname, null);
  const ticket = actions.find((a) => a.id === "ticket");
  return ticket ? { href: ticket.href } : null;
}
