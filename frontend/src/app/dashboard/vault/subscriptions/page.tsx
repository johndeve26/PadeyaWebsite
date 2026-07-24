"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  ConfirmAction,
  DataTable,
  EmptyState,
  FilterBar,
  SkeletonLoader,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime, formatNgn } from "@/lib/format";
import type { VaultSubscription } from "@/lib/types/lifecycle";
import {
  archiveVaultSubscription,
  cancelVaultSubscription,
  fetchMyVaultSubscriptions,
  restoreVaultSubscription,
} from "@/lib/vault-subscriptions-api";

export default function DashboardVaultSubscriptionsPage() {
  const toast = useToast();
  const [rows, setRows] = useState<VaultSubscription[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [includeArchived, setIncludeArchived] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const data = await fetchMyVaultSubscriptions(includeArchived);
    setRows(data);
  }, [includeArchived]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load subscriptions",
          );
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  async function onCancel(id: string) {
    setBusyId(id);
    try {
      await cancelVaultSubscription(id);
      toast.push({ tone: "success", title: "Subscription cancelled" });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Cancel failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onArchive(id: string) {
    setBusyId(id);
    try {
      await archiveVaultSubscription(id);
      toast.push({ tone: "success", title: "Subscription archived" });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Archive failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onRestore(id: string) {
    setBusyId(id);
    try {
      await restoreVaultSubscription(id);
      toast.push({ tone: "success", title: "Subscription restored" });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Restore failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  function subscriptionActions(sub: VaultSubscription) {
    const busy = busyId === sub.id;
    if (sub.status === "active") {
      return (
        <ConfirmAction
          label="Cancel"
          title="Cancel subscription?"
          description="Access ends at the current billing period. This cannot be undone without support."
          confirmLabel="Cancel subscription"
          tone="danger"
          requireReason
          reasonLabel="Reason for cancellation"
          busy={busy}
          onConfirm={() => onCancel(sub.id)}
        />
      );
    }
    if (sub.status === "cancelled" && !sub.archived_at) {
      return (
        <ConfirmAction
          label="Archive"
          title="Archive subscription?"
          description="Hides this from your active list. You can restore it later."
          confirmLabel="Archive"
          busy={busy}
          onConfirm={() => onArchive(sub.id)}
        />
      );
    }
    if (sub.archived_at) {
      return (
        <ConfirmAction
          label="Restore"
          title="Restore subscription?"
          description="Returns this subscription to your list."
          confirmLabel="Restore"
          busy={busy}
          onConfirm={() => onRestore(sub.id)}
        />
      );
    }
    return null;
  }

  const visible = rows ?? [];

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Vault"
      title="My subscriptions"
      description="Vault host subscriptions you've joined. Cancel active plans or archive past ones."
      actions={
        <Link href="/dashboard/vault">
          <Button variant="secondary">Vault unlocks</Button>
        </Link>
      }
    >
      {error ? (
        <Alert tone="danger" title="Failed to load">
          {error}
        </Alert>
      ) : null}

      {rows ? (
        <>
          <FilterBar>
            <label className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-border accent-primary"
                checked={includeArchived}
                onChange={(e) => setIncludeArchived(e.target.checked)}
              />
              Include archived
            </label>
          </FilterBar>

          {visible.length === 0 && !error ? (
            <EmptyState
              title="No subscriptions"
              description="When you subscribe to a host Vault plan, it appears here."
              action={
                <Link href="/hosts">
                  <Button>Browse hosts</Button>
                </Link>
              }
            />
          ) : (
            <DataTable
              rows={visible}
              rowKey={(s) => s.id}
              emptyTitle="No subscriptions"
              columns={[
                {
                  key: "plan",
                  header: "Plan",
                  primary: true,
                  cell: (s) => (
                    <span className="font-semibold text-foreground">
                      {s.plan_label}
                    </span>
                  ),
                },
                {
                  key: "host",
                  header: "Host",
                  cell: (s) => (
                    <span className="font-mono text-xs text-muted-foreground">
                      {s.host_id.slice(0, 8)}…
                    </span>
                  ),
                },
                {
                  key: "price",
                  header: "Price",
                  cell: (s) => formatNgn(s.price),
                },
                {
                  key: "status",
                  header: "Status",
                  cell: (s) => (
                    <StatusBadge
                      status={s.archived_at ? "archived" : s.status}
                    />
                  ),
                },
                {
                  key: "started",
                  header: "Started",
                  cell: (s) =>
                    s.started_at ? formatDateTime(s.started_at) : "—",
                },
                {
                  key: "actions",
                  header: "",
                  cell: (s) => (
                    <div className="flex flex-wrap gap-2">{subscriptionActions(s)}</div>
                  ),
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
