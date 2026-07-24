"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { ApiError } from "@/lib/api";
import { readActiveHostId, writeActiveHostId } from "@/lib/host-workspace";
import {
  fetchHostWorkspaces,
  setActiveHostWorkspace,
} from "@/lib/hosts-api";
import type { HostWorkspace } from "@/lib/types/host-workspace";

/**
 * Active host org for `/host/*` chrome (switcher, filtered nav, landings).
 * Does not own personal `/dashboard` data planes.
 */
type HostWorkspaceContextValue = {
  workspaces: HostWorkspace[];
  active: HostWorkspace | null;
  loading: boolean;
  error: string | null;
  setActiveHostId: (hostId: string) => void;
  refresh: () => Promise<void>;
  isOwner: boolean;
};

const HostWorkspaceContext = createContext<HostWorkspaceContextValue | null>(
  null,
);

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

export function HostWorkspaceProvider({ children }: { children: ReactNode }) {
  const { user, loading: authLoading, refreshUser } = useAuth();
  const [workspaces, setWorkspaces] = useState<HostWorkspace[]>([]);
  const [active, setActive] = useState<HostWorkspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!user) {
      setWorkspaces([]);
      setActive(null);
      return;
    }
    const rows = await fetchHostWorkspaces();
    setWorkspaces(rows);
    const next = pickActive(rows, readActiveHostId());
    setActive(next);
    if (next) writeActiveHostId(next.host_id);
  }, [user]);

  useEffect(() => {
    if (authLoading) return;
    let cancelled = false;
    void (async () => {
      setLoading(true);
      try {
        if (!user) {
          if (!cancelled) {
            setWorkspaces([]);
            setActive(null);
            setError(null);
          }
          return;
        }
        await refresh();
        if (!cancelled) setError(null);
      } catch (err) {
        if (cancelled) return;
        // Session dead — drop auth so RequireAuth sends the user to login
        // instead of a dead-end "workspace unavailable" screen.
        if (err instanceof ApiError && err.status === 401) {
          setWorkspaces([]);
          setActive(null);
          setError(null);
          await refreshUser();
          return;
        }
        setError(
          err instanceof ApiError ? err.detail : "Failed to load workspaces",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, user, refresh, refreshUser]);

  const setActiveHostId = useCallback(
    (hostId: string) => {
      const match = workspaces.find((w) => w.host_id === hostId);
      if (!match) return;
      setActive(match);
      writeActiveHostId(hostId);
      void setActiveHostWorkspace(hostId).catch(() => {
        /* local selection still applies if persist fails */
      });
    },
    [workspaces],
  );

  const value = useMemo(
    () => ({
      workspaces,
      active,
      loading,
      error,
      setActiveHostId,
      refresh,
      isOwner: Boolean(active?.is_owner),
    }),
    [workspaces, active, loading, error, setActiveHostId, refresh],
  );

  return (
    <HostWorkspaceContext.Provider value={value}>
      {children}
    </HostWorkspaceContext.Provider>
  );
}

export function useHostWorkspace(): HostWorkspaceContextValue {
  const ctx = useContext(HostWorkspaceContext);
  if (!ctx) {
    throw new Error("useHostWorkspace must be used within HostWorkspaceProvider");
  }
  return ctx;
}
