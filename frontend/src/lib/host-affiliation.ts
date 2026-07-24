import type { HostWorkspace } from "@/lib/types/host-workspace";

export type HostAffiliationTarget = {
  hostId?: string | null;
  hostSlug?: string | null;
};

type OwnHostWorkspace = Pick<
  HostWorkspace,
  "host_id" | "slug" | "is_owner" | "kind"
>;

function isOwnerWorkspace(w: OwnHostWorkspace): boolean {
  return Boolean(w.is_owner) || w.kind === "owner";
}

/**
 * True when the viewer **owns** this host (Host-as-Fan self-abuse scope).
 * Team members, event staff, and volunteers are not treated as own-host.
 */
export function isAffiliatedWithHost(
  workspaces: OwnHostWorkspace[],
  target: HostAffiliationTarget,
): boolean {
  const hostId = (target.hostId || "").trim();
  const slug = (target.hostSlug || "").replace(/^@/, "").trim().toLowerCase();
  if (!hostId && !slug) return false;
  return workspaces.some((w) => {
    if (!isOwnerWorkspace(w)) return false;
    if (hostId && w.host_id === hostId) return true;
    if (slug && w.slug.toLowerCase() === slug) return true;
    return false;
  });
}

/** Host IDs the viewer owns — for excluding own-host review/CTA surfaces. */
export function ownedHostIds(
  workspaces: Array<Pick<HostWorkspace, "host_id" | "is_owner" | "kind">>,
): string[] {
  return workspaces
    .filter((w) => Boolean(w.is_owner) || w.kind === "owner")
    .map((w) => w.host_id);
}
