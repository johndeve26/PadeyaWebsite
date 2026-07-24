"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  Alert,
  DataTable,
  EmptyState,
  FilterBar,
  Input,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  fetchRuntimeSettingsAudit,
  type RuntimeSettingsAuditEntry,
} from "@/lib/runtime-settings-api";
import { canViewRuntimeAudit } from "@/lib/runtime-settings-permissions";

export function RuntimeSettingsAuditTable() {
  const { user } = useAuth();
  const canView = canViewRuntimeAudit(user);
  const [rows, setRows] = useState<RuntimeSettingsAuditEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionFilter, setActionFilter] = useState("runtime_setting");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!canView) return;
    let active = true;
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const data = await fetchRuntimeSettingsAudit({
            action: actionFilter.trim() || undefined,
            limit: 200,
          });
          if (!active) return;
          setRows(data.items ?? []);
          setError(null);
        } catch (err) {
          if (!active) return;
          // Fallback: empty with help text pointing at platform audit.
          setError(
            err instanceof ApiError
              ? err.detail
              : "Could not load runtime settings audit",
          );
          setRows([]);
        } finally {
          if (active) setLoading(false);
        }
      })();
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [canView, actionFilter]);

  if (!canView) {
    return (
      <Alert tone="danger" title="Permission denied">
        You need <code className="font-mono text-xs">admin.settings.view_audit</code>{" "}
        to view runtime settings audit history.
      </Alert>
    );
  }

  if (loading && !rows) {
    return <SkeletonLoader lines={6} />;
  }

  return (
    <div className="space-y-4">
      {error ? (
        <Alert tone="warning" title="Audit endpoint unavailable">
          {error}. You can also browse{" "}
          <Link
            href="/admin/audit-logs?action=runtime_setting"
            className="font-semibold underline-offset-2 hover:underline"
          >
            platform audit logs
          </Link>{" "}
          for <code className="font-mono text-xs">runtime_setting_*</code> actions.
        </Alert>
      ) : null}

      <FilterBar
        trailing={
          <span className="text-sm text-muted-foreground">
            {(rows ?? []).length} entries
          </span>
        }
      >
        <Input
          label="Action filter"
          placeholder="runtime_setting_update"
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          hint="Matches runtime_setting_update, runtime_setting_reset, and related actions"
        />
      </FilterBar>

      {(rows ?? []).length === 0 ? (
        <EmptyState
          title="No runtime settings audit entries"
          description="Updates, clears, and tests appear as runtime_setting_* actions when recorded."
        />
      ) : (
        <DataTable
          rows={rows ?? []}
          rowKey={(row) => row.id}
          emptyTitle="No entries"
          columns={[
            {
              key: "when",
              header: "When",
              primary: true,
              cell: (row) => formatDateTime(row.created_at),
            },
            {
              key: "action",
              header: "Action",
              cell: (row) => (
                <span className="font-mono text-sm">{row.action}</span>
              ),
            },
            {
              key: "resource",
              header: "Resource",
              cell: (row) =>
                row.resource_type ? (
                  <span className="text-sm text-muted-foreground">
                    {row.resource_type}
                    {row.resource_id
                      ? ` · ${String(row.resource_id).slice(0, 12)}`
                      : ""}
                  </span>
                ) : (
                  "—"
                ),
            },
            {
              key: "actor",
              header: "Actor",
              cell: (row) =>
                row.actor_user_id ? (
                  <span className="font-mono text-xs text-muted-foreground">
                    {row.actor_user_id}
                  </span>
                ) : (
                  "—"
                ),
            },
          ]}
        />
      )}
    </div>
  );
}
