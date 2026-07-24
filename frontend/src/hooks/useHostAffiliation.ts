"use client";

import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  isAffiliatedWithHost,
  type HostAffiliationTarget,
} from "@/lib/host-affiliation";
import { fetchHostWorkspaces } from "@/lib/hosts-api";
import type { HostWorkspace } from "@/lib/types/host-workspace";

type Cache = {
  userId: string;
  workspaces: HostWorkspace[];
};

/**
 * Whether the signed-in user **owns** a public host workspace.
 * Team/staff workspaces do not count. Logged-out viewers are never own-host.
 */
export function useHostAffiliation(target: HostAffiliationTarget): {
  affiliated: boolean;
  loading: boolean;
  workspaces: HostWorkspace[];
} {
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const [cache, setCache] = useState<Cache | null>(null);

  const hostId = target.hostId || null;
  const hostSlug = target.hostSlug || null;

  useEffect(() => {
    if (!userId) return;
    let alive = true;
    void fetchHostWorkspaces()
      .then((rows) => {
        if (!alive) return;
        setCache({ userId, workspaces: rows });
      })
      .catch(() => {
        if (!alive) return;
        setCache({ userId, workspaces: [] });
      });
    return () => {
      alive = false;
    };
  }, [userId]);

  const workspaces = useMemo(
    () => (userId && cache?.userId === userId ? cache.workspaces : []),
    [userId, cache],
  );
  const loading = Boolean(userId) && cache?.userId !== userId;

  const affiliated = useMemo(
    () =>
      Boolean(userId) &&
      isAffiliatedWithHost(workspaces, { hostId, hostSlug }),
    [userId, workspaces, hostId, hostSlug],
  );

  return { affiliated, loading, workspaces };
}
