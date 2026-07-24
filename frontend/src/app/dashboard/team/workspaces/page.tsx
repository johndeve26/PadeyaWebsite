"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  SectionHeader,
  SkeletonLoader,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { hostHomePathForWorkspace } from "@/lib/host-access";
import {
  fetchHostWorkspaces,
  setActiveHostWorkspace,
} from "@/lib/hosts-api";
import {
  writeActiveHostId,
  writeWorkspaceMode,
} from "@/lib/host-workspace";
import type { HostWorkspace } from "@/lib/types/host-workspace";

export default function DashboardTeamWorkspacesPage() {
  const router = useRouter();
  const toast = useToast();
  const { setActiveHostId, refresh } = useHostWorkspace();
  const [rows, setRows] = useState<HostWorkspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load() {
    const data = await fetchHostWorkspaces();
    setRows(data);
  }

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const data = await fetchHostWorkspaces();
        if (alive) setRows(data);
      } catch (err) {
        if (alive) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load workspaces",
          );
        }
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  async function setActive(hostId: string, openHost: boolean) {
    setBusyId(hostId);
    setError(null);
    try {
      await setActiveHostWorkspace(hostId);
      writeActiveHostId(hostId);
      setActiveHostId(hostId);
      await refresh();
      await load();
      toast.push({ title: "Active workspace updated", tone: "success" });
      if (openHost) {
        writeWorkspaceMode("host");
        const match = rows.find((w) => w.host_id === hostId);
        router.push(match ? hostHomePathForWorkspace(match) : "/host");
      }
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.detail : "Could not set workspace";
      setError(detail);
      toast.push({
        title: "Workspace update failed",
        description: detail,
        tone: "danger",
      });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Workspaces"
      title="Manage workspaces"
      description="Choose which host workspace is active. Your selection is saved for desk and team tools."
      actions={
        <Link href="/dashboard/team">
          <Button variant="ghost">Back to workspaces</Button>
        </Link>
      }
    >
      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}

      {loading ? <SkeletonLoader lines={4} /> : null}

      {!loading && rows.length === 0 ? (
        <EmptyState
          title="No workspaces"
          description="Own a host or accept a team invite to get a workspace here."
        />
      ) : null}

      {!loading && rows.length > 0 ? (
        <section className="space-y-4">
          <SectionHeader
            title="Available workspaces"
            description={`${rows.length} workspace${rows.length === 1 ? "" : "s"} you can open.`}
          />
          <ul className="space-y-3">
            {rows.map((w) => (
              <Card
                key={w.host_id}
                className="flex flex-wrap items-center justify-between gap-3 p-4"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-foreground">
                      {w.display_name}
                    </p>
                    {w.is_active ? <StatusBadge status="active" /> : null}
                    {w.is_owner ? (
                      <span className="rounded-md bg-surface-muted px-2 py-0.5 text-xs font-semibold text-muted-foreground">
                        Owner
                      </span>
                    ) : null}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {w.role_label || w.role} · {w.kind.replace(/_/g, " ")} ·{" "}
                    {w.slug}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {!w.is_active ? (
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={busyId === w.host_id}
                      onClick={() => void setActive(w.host_id, false)}
                    >
                      Set active
                    </Button>
                  ) : null}
                  <Button
                    size="sm"
                    disabled={busyId === w.host_id}
                    onClick={() => void setActive(w.host_id, true)}
                  >
                    Open host desk
                  </Button>
                </div>
              </Card>
            ))}
          </ul>
        </section>
      ) : null}
    </DashboardShell>
  );
}
