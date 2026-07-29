"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Button } from "@/components/ui";
import { useUserRestrictions } from "@/hooks/useUserRestrictions";
import { canCreateEvents } from "@/lib/host-access";
import {
  readActiveHostId,
  writeActiveHostId,
} from "@/lib/host-workspace";
import {
  fetchHostWorkspaces,
  setActiveHostWorkspace,
} from "@/lib/hosts-api";
import type { HostWorkspace } from "@/lib/types/host-workspace";

type CreateEventState =
  | { status: "loading" }
  | { status: "login" }
  | { status: "onboarding" }
  | { status: "create"; hostId: string }
  | { status: "hidden" };

function canCreateOnWorkspace(workspace: HostWorkspace): boolean {
  return workspace.is_owner || canCreateEvents(workspace);
}

function resolveCreateEventState(workspaces: HostWorkspace[]): CreateEventState {
  if (workspaces.length === 0) return { status: "onboarding" };
  const preferredId = readActiveHostId();
  const preferred =
    preferredId != null
      ? workspaces.find(
          (w) => w.host_id === preferredId && canCreateOnWorkspace(w),
        )
      : undefined;
  const creatable =
    preferred ??
    workspaces.find((w) => w.is_active && canCreateOnWorkspace(w)) ??
    workspaces.find((w) => canCreateOnWorkspace(w)) ??
    null;
  if (!creatable) return { status: "hidden" };
  return { status: "create", hostId: creatable.host_id };
}

/**
 * Top-nav Create event CTA — growth entry only, not a workspace switcher.
 * - Can create → /host/events/new (active creatable workspace)
 * - Zero host workspaces → /host/onboarding
 * - Scanner/merch-only without create permission → hidden
 */
export function CreateEventCta({
  className = "",
  mobile = false,
  onNavigate,
  buttonVariant = "primary",
  buttonSize = "sm",
}: {
  className?: string;
  /** Text link style for the mobile drawer. */
  mobile?: boolean;
  onNavigate?: () => void;
  buttonVariant?: "primary" | "primary-on-dark";
  buttonSize?: "sm" | "md" | "lg";
}) {
  const { user, loading: authLoading } = useAuth();
  const { has } = useUserRestrictions();
  const cannotCreate = has("cannot_create_events");
  const [fetched, setFetched] = useState<{
    userId: string;
    state: CreateEventState;
  } | null>(null);

  useEffect(() => {
    if (authLoading || !user) return;
    const userId = user.id;
    let cancelled = false;
    void fetchHostWorkspaces()
      .then((rows) => {
        if (!cancelled) {
          setFetched({ userId, state: resolveCreateEventState(rows) });
        }
      })
      .catch(() => {
        // Fail open to onboarding so guests/new users can still start hosting.
        if (!cancelled) {
          setFetched({ userId, state: { status: "onboarding" } });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading, user]);

  const state: CreateEventState = (() => {
    if (authLoading) return { status: "loading" };
    if (!user) return { status: "login" };
    if (!fetched || fetched.userId !== user.id) return { status: "loading" };
    return fetched.state;
  })();

  if (state.status === "hidden") return null;
  if (state.status === "loading") return null;
  if (cannotCreate) return null;

  const href =
    state.status === "login"
      ? "/login?next=/host/onboarding"
      : state.status === "create"
        ? "/host/events/new"
        : "/host/onboarding";

  function prepareCreateHost() {
    if (state.status !== "create") return;
    writeActiveHostId(state.hostId);
    void setActiveHostWorkspace(state.hostId).catch(() => undefined);
  }

  if (mobile) {
    return (
      <Link
        href={href}
        className={className}
        onClick={() => {
          prepareCreateHost();
          onNavigate?.();
        }}
      >
        Create event
      </Link>
    );
  }

  return (
    <Link
      href={href}
      className={className}
      onClick={() => {
        prepareCreateHost();
        onNavigate?.();
      }}
    >
      <Button variant={buttonVariant} size={buttonSize}>
        Create event
      </Button>
    </Link>
  );
}
