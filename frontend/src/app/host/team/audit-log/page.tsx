"use client";

import { useEffect, useState } from "react";

import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
import { RequireHostTeamManage } from "@/components/hosts/RequireHostTeamManage";
import { HostTeamSubnav } from "@/components/hosts/team/HostTeamSubnav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Card,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  auditActionLabel,
  auditEntityLabel,
  formatAuditMetadata,
} from "@/lib/host-team-helpers";
import { fetchHostTeamAudit } from "@/lib/hosts-lifecycle-api";
import type { HostTeamAuditItem } from "@/lib/types/lifecycle";

export default function HostTeamAuditLogPage() {
  const { active } = useHostWorkspace();
  const hostId = active?.host_id ?? null;
  const [rows, setRows] = useState<HostTeamAuditItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!hostId) return;
    let alive = true;
    void (async () => {
      try {
        const logs = await fetchHostTeamAudit(100, hostId);
        if (alive) setRows(logs);
      } catch (err) {
        if (alive) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load audit log",
          );
        }
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [hostId]);

  return (
    <RequireHostTeamManage>
      <DashboardShell
        tone="soft"
        eyebrow="Host Team"
        title="Team audit log"
        description="Invite, member, permission, scope, and desk scan activity for this host workspace."
      >
        <HostTeamSubnav />

        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        {loading ? <SkeletonLoader lines={6} /> : null}

        {!loading && rows.length === 0 ? (
          <EmptyState
            title="No team activity yet"
            description="Actions on invites, members, and desk scans will appear here."
          />
        ) : null}

        {!loading && rows.length > 0 ? (
          <Card className="space-y-0 overflow-x-auto p-0">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="border-b border-border bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-medium">Actor</th>
                  <th className="px-4 py-3 font-medium">Action</th>
                  <th className="px-4 py-3 font-medium">Target</th>
                  <th className="px-4 py-3 font-medium">Entity</th>
                  <th className="px-4 py-3 font-medium">When</th>
                  <th className="px-4 py-3 font-medium">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map((item) => {
                  const meta = formatAuditMetadata(item.details);
                  return (
                    <tr key={item.id} className="align-top">
                      <td className="px-4 py-3 text-foreground">
                        {item.actor_label || "—"}
                      </td>
                      <td className="px-4 py-3 font-medium text-foreground">
                        {auditActionLabel(item.action, item.action_label)}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {item.target_label || "—"}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {auditEntityLabel(item)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-muted-foreground">
                        {formatDateTime(item.created_at)}
                      </td>
                      <td className="max-w-xs px-4 py-3 text-muted-foreground">
                        {meta || "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        ) : null}
      </DashboardShell>
    </RequireHostTeamManage>
  );
}
