"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  ConfirmAction,
  DataTable,
  EmptyState,
  FilterBar,
  Input,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { deactivateUser, fetchAuditLogs, restoreUser } from "@/lib/admin-lifecycle-api";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { AuditLog } from "@/lib/types/lifecycle";

export default function AdminAuditLogsPage() {
  const toast = useToast();
  const searchParams = useSearchParams();
  const [rows, setRows] = useState<AuditLog[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionFilter, setActionFilter] = useState("");
  const [resourceTypeFilter, setResourceTypeFilter] = useState(
    () => searchParams.get("resource_type") || "",
  );
  const [resourceIdFilter, setResourceIdFilter] = useState(
    () => searchParams.get("resource_id") || "",
  );
  const [busyUserId, setBusyUserId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const data = await fetchAuditLogs({
      action: actionFilter.trim() || undefined,
      resource_type: resourceTypeFilter.trim() || undefined,
      resource_id: resourceIdFilter.trim() || undefined,
      limit: 200,
    });
    setRows(data);
  }, [actionFilter, resourceTypeFilter, resourceIdFilter]);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          await load();
          if (active) setError(null);
        } catch (err) {
          if (active) {
            setError(err instanceof ApiError ? err.detail : "Failed to load audit logs");
            setRows([]);
          }
        }
      })();
    }, 300);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [load]);

  const filtered = useMemo(() => rows ?? [], [rows]);

  async function onDeactivateUser(userId: string) {
    setBusyUserId(userId);
    try {
      await deactivateUser(userId, "Deactivated from audit logs");
      toast.push({ tone: "success", title: "User deactivated" });
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Deactivate failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyUserId(null);
    }
  }

  async function onRestoreUser(userId: string) {
    setBusyUserId(userId);
    try {
      await restoreUser(userId, "Restored from audit logs");
      toast.push({ tone: "success", title: "User restored" });
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Restore failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyUserId(null);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Audit logs"
      description="Read-only platform activity trail. User lifecycle actions are separate from finance."
    >
      {error ? (
        <Alert tone="danger" title="Failed to load">
          {error}
        </Alert>
      ) : null}

      {rows ? (
        <>
          <FilterBar
            trailing={
              <span className="text-sm text-muted-foreground">
                {filtered.length} entries
              </span>
            }
          >
            <Input
              label="Action"
              placeholder="e.g. users.deactivate"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
            />
            <Input
              label="Resource type"
              placeholder="e.g. user, event"
              value={resourceTypeFilter}
              onChange={(e) => setResourceTypeFilter(e.target.value)}
            />
            <Input
              label="Resource ID"
              placeholder="UUID"
              value={resourceIdFilter}
              onChange={(e) => setResourceIdFilter(e.target.value)}
            />
          </FilterBar>

          {filtered.length === 0 && !error ? (
            <EmptyState
              title="No audit entries"
              description={
                actionFilter || resourceTypeFilter || resourceIdFilter
                  ? "Try different filters."
                  : "Platform actions will appear here as they occur."
              }
            />
          ) : (
            <DataTable
              rows={filtered}
              rowKey={(log) => log.id}
              emptyTitle="No audit entries"
              columns={[
                {
                  key: "when",
                  header: "When",
                  primary: true,
                  cell: (log) => formatDateTime(log.created_at),
                },
                {
                  key: "action",
                  header: "Action",
                  cell: (log) => (
                    <span className="font-mono text-sm">{log.action}</span>
                  ),
                },
                {
                  key: "resource",
                  header: "Resource",
                  cell: (log) =>
                    log.resource_type ? (
                      <span className="text-sm text-muted-foreground">
                        {log.resource_type}
                        {log.resource_id ? ` · ${log.resource_id.slice(0, 8)}…` : ""}
                      </span>
                    ) : (
                      "—"
                    ),
                },
                {
                  key: "actor",
                  header: "Actor",
                  cell: (log) =>
                    log.actor_user_id ? (
                      <span className="font-mono text-xs text-muted-foreground">
                        {log.actor_user_id}
                      </span>
                    ) : (
                      "—"
                    ),
                },
                {
                  key: "user_actions",
                  header: "",
                  cell: (log) =>
                    log.actor_user_id ? (
                      <div className="flex flex-wrap gap-1 opacity-80">
                        <ConfirmAction
                          label="Deactivate actor"
                          title="Deactivate this user?"
                          description="Account access is revoked. This does not affect ledger or payout records. Use Users page for targeted actions."
                          confirmLabel="Deactivate"
                          tone="danger"
                          size="sm"
                          variant="ghost"
                          requireReason
                          busy={busyUserId === log.actor_user_id}
                          onConfirm={() => onDeactivateUser(log.actor_user_id!)}
                        />
                        <ConfirmAction
                          label="Restore actor"
                          title="Restore this user?"
                          description="Re-enables account access if previously deactivated."
                          confirmLabel="Restore"
                          size="sm"
                          variant="ghost"
                          busy={busyUserId === log.actor_user_id}
                          onConfirm={() => onRestoreUser(log.actor_user_id!)}
                        />
                        <Link
                          href="/admin/users"
                          className="self-center text-xs font-semibold text-muted-foreground underline"
                        >
                          Users page
                        </Link>
                      </div>
                    ) : null,
                },
              ]}
            />
          )}
        </>
      ) : null}

      {rows == null && !error ? <SkeletonLoader lines={4} /> : null}
    </DashboardShell>
  );
}
