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
import {
  fetchSponsorWorkspaces,
  type SponsorWorkspace,
} from "@/lib/sponsor-profiles-api";
import {
  readActiveSponsorId,
  writeActiveSponsorId,
} from "@/lib/sponsor-workspace";

type SponsorWorkspaceContextValue = {
  workspaces: SponsorWorkspace[];
  active: SponsorWorkspace | null;
  loading: boolean;
  error: string | null;
  setActiveSponsorId: (id: string) => void;
  refresh: () => Promise<void>;
};

const SponsorWorkspaceContext =
  createContext<SponsorWorkspaceContextValue | null>(null);

function pickActive(
  workspaces: SponsorWorkspace[],
  preferredId: string | null,
): SponsorWorkspace | null {
  if (!workspaces.length) return null;
  if (preferredId) {
    const match = workspaces.find((w) => w.sponsor_id === preferredId);
    if (match) return match;
  }
  const owned = workspaces.find((w) => w.is_owner);
  return owned ?? workspaces[0] ?? null;
}

export function SponsorWorkspaceProvider({ children }: { children: ReactNode }) {
  const { user, loading: authLoading, refreshUser } = useAuth();
  const [workspaces, setWorkspaces] = useState<SponsorWorkspace[]>([]);
  const [active, setActive] = useState<SponsorWorkspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!user) {
      setWorkspaces([]);
      setActive(null);
      return;
    }
    const rows = await fetchSponsorWorkspaces();
    setWorkspaces(rows);
    const next = pickActive(rows, readActiveSponsorId());
    setActive(next);
    if (next) writeActiveSponsorId(next.sponsor_id);
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
        if (err instanceof ApiError && err.status === 401) {
          setWorkspaces([]);
          setActive(null);
          setError(null);
          await refreshUser();
          return;
        }
        setError(
          err instanceof ApiError ? err.detail : "Sponsor workspace unavailable",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, refresh, refreshUser, user]);

  const setActiveSponsorId = useCallback(
    (id: string) => {
      const match = workspaces.find((w) => w.sponsor_id === id);
      if (!match) return;
      setActive(match);
      writeActiveSponsorId(id);
    },
    [workspaces],
  );

  const value = useMemo(
    () => ({
      workspaces,
      active,
      loading,
      error,
      setActiveSponsorId,
      refresh,
    }),
    [workspaces, active, loading, error, setActiveSponsorId, refresh],
  );

  return (
    <SponsorWorkspaceContext.Provider value={value}>
      {children}
    </SponsorWorkspaceContext.Provider>
  );
}

export function useSponsorWorkspace() {
  const ctx = useContext(SponsorWorkspaceContext);
  if (!ctx) {
    throw new Error("useSponsorWorkspace requires SponsorWorkspaceProvider");
  }
  return ctx;
}

/** Safe when SponsorWorkspaceProvider is not mounted (switcher on partial trees). */
export function useOptionalSponsorWorkspace() {
  return useContext(SponsorWorkspaceContext);
}
