/** Capability packs carried on an impersonation session (from /auth/me). */

export const IMPERSONATION_SCOPE_VIEW = "view";
export const IMPERSONATION_SCOPE_HOST_EVENTS = "host_events";
export const IMPERSONATION_SCOPE_CREDENTIALS = "credentials";

export type ImpersonationScope =
  | typeof IMPERSONATION_SCOPE_VIEW
  | typeof IMPERSONATION_SCOPE_HOST_EVENTS
  | typeof IMPERSONATION_SCOPE_CREDENTIALS;

export type ImpersonationPack = "view" | "host_events" | "full" | "none";

const PACK_LABELS: Record<ImpersonationPack, string> = {
  view: "View only",
  host_events: "View + host events",
  full: "Full (incl. credentials)",
  none: "None",
};

/** Permissions that unlock packs before starting impersonation (admin session). */
export const PERM_IMPERSONATE = "admin.users.impersonate";
export const PERM_IMPERSONATE_HOST_EVENTS =
  "admin.users.impersonate.host_events";
export const PERM_FULL_ACCESS = "admin.full_access";

export function packLabel(pack: string | null | undefined): string {
  if (!pack) return PACK_LABELS.view;
  return PACK_LABELS[pack as ImpersonationPack] ?? pack;
}

export function hasImpersonationScope(
  scopes: string[] | null | undefined,
  scope: ImpersonationScope | string,
): boolean {
  return Boolean(scopes?.includes(scope));
}

/** Predict scopes from the actor admin's permissions (pre-start UI). */
export function resolveActorImpersonationScopes(
  permissions: string[] | null | undefined,
): { scopes: ImpersonationScope[]; pack: ImpersonationPack } {
  const perms = new Set(permissions ?? []);
  const full = perms.has(PERM_FULL_ACCESS);
  if (!full && !perms.has(PERM_IMPERSONATE)) {
    return { scopes: [], pack: "none" };
  }
  const scopes: ImpersonationScope[] = [IMPERSONATION_SCOPE_VIEW];
  if (full || perms.has(PERM_IMPERSONATE_HOST_EVENTS)) {
    scopes.push(IMPERSONATION_SCOPE_HOST_EVENTS);
  }
  if (full) {
    scopes.push(IMPERSONATION_SCOPE_CREDENTIALS);
  }
  const pack: ImpersonationPack = full
    ? "full"
    : scopes.includes(IMPERSONATION_SCOPE_HOST_EVENTS)
      ? "host_events"
      : "view";
  return { scopes, pack };
}
