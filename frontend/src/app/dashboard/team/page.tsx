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
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { hostHomePathForWorkspace } from "@/lib/host-access";
import { writeWorkspaceMode } from "@/lib/host-workspace";
import { fetchHostWorkspaces } from "@/lib/hosts-api";
import type { HostWorkspace } from "@/lib/types/host-workspace";

export default function DashboardTeamPage() {
  const router = useRouter();
  const { setActiveHostId, refresh } = useHostWorkspace();
  const [rows, setRows] = useState<HostWorkspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const data = await fetchHostWorkspaces();
        if (alive) setRows(data);
      } catch (err) {
        if (alive) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load team workspaces",
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

  async function openWorkspace(hostId: string) {
    setBusyId(hostId);
    try {
      setActiveHostId(hostId);
      writeWorkspaceMode("host");
      await refresh();
      const match = rows.find((w) => w.host_id === hostId);
      router.push(match ? hostHomePathForWorkspace(match) : "/host");
    } finally {
      setBusyId(null);
    }
  }

  const teamRows = rows.filter((w) => !w.is_owner);
  const owned = rows.filter((w) => w.is_owner);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Workspaces"
      title="Your workspaces"
      description="Host workspaces you own or joined as a team member. Sponsor brand companies use a separate sponsor workspace (after rich sponsor seed: sponsor-owner-*@demo.padeya.test)."
      actions={
        <Link href="/dashboard/team/workspaces">
          <Button variant="secondary">Manage workspaces</Button>
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
          title="No host workspaces yet"
          description="When you become a host or accept a team invite, it will show up here."
        />
      ) : null}

      {!loading && owned.length > 0 ? (
        <section className="mb-8 space-y-4">
          <SectionHeader
            title="Owned host"
            description="You are the owner of these workspaces."
          />
          <ul className="space-y-3">
            {owned.map((w) => (
              <Card
                key={w.host_id}
                className="flex flex-wrap items-center justify-between gap-3 p-4"
              >
                <div>
                  <p className="font-semibold text-foreground">
                    {w.display_name}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Owner · {w.slug}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    disabled={busyId === w.host_id}
                    onClick={() => void openWorkspace(w.host_id)}
                  >
                    Open host desk
                  </Button>
                  <Link href="/host/team">
                    <Button size="sm" variant="secondary">
                      Manage team
                    </Button>
                  </Link>
                </div>
              </Card>
            ))}
          </ul>
        </section>
      ) : null}

      {!loading && teamRows.length > 0 ? (
        <section className="space-y-4">
          <SectionHeader
            title="Teams you joined"
            description="Active memberships on other host workspaces."
          />
          <ul className="space-y-3">
            {teamRows.map((w) => (
              <Card
                key={w.host_id}
                className="flex flex-wrap items-center justify-between gap-3 p-4"
              >
                <div>
                  <p className="font-semibold text-foreground">
                    {w.display_name}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {w.role_label || w.role} · {w.kind.replace(/_/g, " ")}
                    {w.scope === "selected_events"
                      ? " · selected events"
                      : " · host-wide"}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {w.is_active ? <StatusBadge status="active" /> : null}
                  <Button
                    size="sm"
                    disabled={busyId === w.host_id}
                    onClick={() => void openWorkspace(w.host_id)}
                  >
                    Open workspace
                  </Button>
                </div>
              </Card>
            ))}
          </ul>
        </section>
      ) : null}

      {!loading && rows.length > 0 && teamRows.length === 0 && owned.length === 0 ? (
        <EmptyState
          title="No team memberships"
          description="Accept a host team invite to join a workspace."
        />
      ) : null}
    </DashboardShell>
  );
}
