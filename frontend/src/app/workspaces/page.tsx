"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { HostWorkspaceProvider } from "@/components/hosts/HostWorkspaceProvider";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  SectionHeader,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  ADMIN_PANEL_SWITCHER_LABEL,
  SUPPORT_DESK_SWITCHER_LABEL,
  canAccessAdminPanel,
  canAccessSupportDesk,
} from "@/lib/auth/workspace-access";
import {
  hostHomePathForWorkspace,
  PERSONAL_WORKSPACE_SWITCHER_LABEL,
  workspaceOptionLabel,
} from "@/lib/host-access";
import {
  writeActiveHostId,
  writeWorkspaceMode,
} from "@/lib/host-workspace";
import {
  fetchHostWorkspaces,
  setActiveHostWorkspace,
} from "@/lib/hosts-api";
import type { HostWorkspace } from "@/lib/types/host-workspace";

function WorkspacesChooser() {
  const router = useRouter();
  const { user, isImpersonating } = useAuth();
  const showAdmin = canAccessAdminPanel(user, isImpersonating);
  const showSupport = canAccessSupportDesk(user, isImpersonating);
  const [rows, setRows] = useState<HostWorkspace[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    void fetchHostWorkspaces()
      .then((data) => {
        if (alive) setRows(data);
      })
      .catch((err) => {
        if (alive) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load workspaces",
          );
          setRows([]);
        }
      });
    return () => {
      alive = false;
    };
  }, []);

  async function openHost(workspace: HostWorkspace) {
    setBusy(workspace.host_id);
    try {
      writeActiveHostId(workspace.host_id);
      writeWorkspaceMode("host");
      await setActiveHostWorkspace(workspace.host_id).catch(() => undefined);
      router.push(hostHomePathForWorkspace(workspace));
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="mx-auto min-h-[70vh] max-w-2xl px-4 py-12 sm:px-6">
      <SectionHeader
        title="Choose a workspace"
        description="Your personal account, platform panels you’re allowed to use, or a host workspace you own or joined."
      />

      {error ? (
        <div className="mt-6">
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        </div>
      ) : null}

      {rows === null ? (
        <div className="mt-8">
          <SkeletonLoader lines={5} />
        </div>
      ) : (
        <ul className="mt-8 space-y-3">
          <li>
            <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
              <div>
                <p className="font-semibold text-foreground">
                  {PERSONAL_WORKSPACE_SWITCHER_LABEL}
                </p>
                <p className="text-sm text-muted-foreground">
                  Tickets, merch orders, Passport, and Fan Connect.
                </p>
              </div>
              <Link
                href="/dashboard"
                onClick={() => writeWorkspaceMode("personal")}
              >
                <Button size="sm">Continue</Button>
              </Link>
            </Card>
          </li>

          {showAdmin ? (
            <li>
              <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <p className="font-semibold text-foreground">
                    {ADMIN_PANEL_SWITCHER_LABEL}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Platform moderation, content, and operations tools.
                  </p>
                </div>
                <Link
                  href="/admin"
                  onClick={() => writeWorkspaceMode("admin")}
                >
                  <Button size="sm">Open</Button>
                </Link>
              </Card>
            </li>
          ) : null}

          {showSupport ? (
            <li>
              <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <p className="font-semibold text-foreground">
                    {SUPPORT_DESK_SWITCHER_LABEL}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Staff cases, refunds, and desk tools.
                  </p>
                </div>
                <Link
                  href="/support/desk"
                  onClick={() => writeWorkspaceMode("support")}
                >
                  <Button size="sm">Open</Button>
                </Link>
              </Card>
            </li>
          ) : null}

          {rows.map((w) => (
            <li key={w.host_id}>
              <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div className="min-w-0">
                  <p className="font-semibold text-foreground">
                    {workspaceOptionLabel(w)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {w.is_owner
                      ? "Owner — full host tools"
                      : `${w.role_label || w.role} — access follows your permissions`}
                  </p>
                </div>
                <Button
                  size="sm"
                  disabled={busy === w.host_id}
                  onClick={() => void openHost(w)}
                >
                  {busy === w.host_id ? "Opening…" : "Open"}
                </Button>
              </Card>
            </li>
          ))}
        </ul>
      )}

      {rows && rows.length === 0 && !error ? (
        <div className="mt-6">
          <EmptyState
            title="No host workspaces yet"
            description="Become a host or accept a team invite to see host workspaces here."
            action={
              <Link href="/host/onboarding">
                <Button>Become a host</Button>
              </Link>
            }
          />
        </div>
      ) : null}
    </main>
  );
}

export default function WorkspacesPage() {
  return (
    <RequireAuth>
      <HostWorkspaceProvider>
        <WorkspacesChooser />
      </HostWorkspaceProvider>
    </RequireAuth>
  );
}
