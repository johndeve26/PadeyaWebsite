/** Active host workspace selection (multi-team / owner) + last surface mode. */

const HOST_ID_KEY = "padeya-active-host-id";
const MODE_KEY = "padeya-workspace-mode";

export type WorkspaceMode = "personal" | "host" | "admin" | "support" | "sponsor";

export function readActiveHostId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(HOST_ID_KEY);
  } catch {
    return null;
  }
}

export function writeActiveHostId(hostId: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (!hostId) localStorage.removeItem(HOST_ID_KEY);
    else localStorage.setItem(HOST_ID_KEY, hostId);
  } catch {
    /* ignore */
  }
}

export function readWorkspaceMode(): WorkspaceMode {
  if (typeof window === "undefined") return "personal";
  try {
    const raw = localStorage.getItem(MODE_KEY);
    if (raw === "host" || raw === "admin" || raw === "support" || raw === "sponsor") {
      return raw;
    }
    return "personal";
  } catch {
    return "personal";
  }
}

export function writeWorkspaceMode(mode: WorkspaceMode): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(MODE_KEY, mode);
  } catch {
    /* ignore */
  }
}

/** Sync last-used mode from the current path (deep links, back/forward). */
export function syncWorkspaceModeFromPath(pathname: string | null | undefined): void {
  if (!pathname) return;
  if (pathname === "/host" || pathname.startsWith("/host/")) {
    writeWorkspaceMode("host");
    return;
  }
  if (pathname === "/admin" || pathname.startsWith("/admin/")) {
    writeWorkspaceMode("admin");
    return;
  }
  if (
    pathname === "/support/desk" ||
    pathname.startsWith("/support/desk/") ||
    pathname === "/support/cases" ||
    pathname.startsWith("/support/cases/") ||
    pathname === "/support/refunds" ||
    pathname.startsWith("/support/refunds/")
  ) {
    writeWorkspaceMode("support");
    return;
  }
  if (pathname === "/sponsor" || pathname.startsWith("/sponsor/")) {
    writeWorkspaceMode("sponsor");
    return;
  }
  if (
    pathname === "/dashboard" ||
    pathname.startsWith("/dashboard/") ||
    pathname === "/connect" ||
    pathname.startsWith("/connect/")
  ) {
    writeWorkspaceMode("personal");
  }
}
