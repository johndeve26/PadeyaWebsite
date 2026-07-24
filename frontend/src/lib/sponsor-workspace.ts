const STORAGE_KEY = "padeya.activeSponsorId";

export function readActiveSponsorId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(STORAGE_KEY);
}

export function writeActiveSponsorId(id: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, id);
}

export function clearActiveSponsorId(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export type WorkspaceSurface = "personal" | "host" | "sponsor" | "admin" | "support";

export function syncSponsorModeFromPath(pathname: string | null): void {
  if (typeof window === "undefined" || !pathname) return;
  const onSponsor =
    pathname === "/sponsor" || pathname.startsWith("/sponsor/");
  if (onSponsor) {
    window.localStorage.setItem("padeya.workspaceMode", "sponsor");
  }
}
