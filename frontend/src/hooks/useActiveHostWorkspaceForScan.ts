"use client";

import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { userHasRole } from "@/lib/auth/permissions";
import { readActiveHostId } from "@/lib/host-workspace";
import { fetchHostWorkspaces } from "@/lib/hosts-api";
import type { HostWorkspace } from "@/lib/types/host-workspace";

function pickActive(
  workspaces: HostWorkspace[],
  preferredId: string | null,
): HostWorkspace | null {
  if (!workspaces.length) return null;
  if (preferredId) {
    const match = workspaces.find((w) => w.host_id === preferredId);
    if (match) return match;
  }
  const serverActive = workspaces.find((w) => w.is_active);
  if (serverActive) return serverActive;
  const owned = workspaces.find((w) => w.is_owner);
  return owned ?? workspaces[0] ?? null;
}

/** Active host workspace for header scan buttons (SiteHeader sits outside host layout). */
export function useActiveHostWorkspaceForScan(): HostWorkspace | null | undefined {
  const { user } = useAuth();
  const [workspace, setWorkspace] = useState<HostWorkspace | null | undefined>(
    undefined,
  );

  useEffect(() => {
    if (!user || !userHasRole(user, "host", "host_staff", "super_admin")) {
      setWorkspace(null);
      return;
    }
    let cancelled = false;
    void fetchHostWorkspaces()
      .then((rows) => {
        if (!cancelled) {
          setWorkspace(pickActive(rows, readActiveHostId()));
        }
      })
      .catch(() => {
        if (!cancelled) setWorkspace(null);
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  return workspace;
}
