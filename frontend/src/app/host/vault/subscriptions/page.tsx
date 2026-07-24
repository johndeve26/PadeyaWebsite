"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  Alert,
  Button,
  Card,
  ConfirmAction,
  DataTable,
  EmptyState,
  FilterBar,
  SectionHeader,
  Select,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { VaultStudioShell } from "@/components/vault/studio/VaultStudioShell";
import { ApiError } from "@/lib/api";
import { formatDateTime, formatNgn } from "@/lib/format";
import {
  archiveVaultSubscription,
  cancelVaultSubscription,
  fetchHostVaultSubscriptions,
  restoreVaultSubscription,
} from "@/lib/vault-subscriptions-api";
import type { VaultSubscription } from "@/lib/types/lifecycle";

export default function HostVaultSubscriptionsPage() {
  const toast = useToast();
  const [rows, setRows] = useState<VaultSubscription[]>([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load(include = includeArchived) {
    setRows(await fetchHostVaultSubscriptions(include));
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const items = await fetchHostVaultSubscriptions(includeArchived);
        if (active) setRows(items);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load subscriptions",
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [includeArchived]);

  const statusOptions = useMemo(() => {
    const set = new Set(rows.map((r) => r.status));
    return Array.from(set).sort();
  }, [rows]);

  const filtered = useMemo(() => {
    return rows.filter((row) => {
      if (statusFilter !== "all" && row.status !== statusFilter) return false;
      return true;
    });
  }, [rows, statusFilter]);

  async function onCancel(id: string) {
    setBusyId(id);
    setError(null);
    try {
      await cancelVaultSubscription(id);
      toast.push({ title: "Subscription cancelled", tone: "success" });
      await load();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Cancel failed";
      setError(detail);
      toast.push({ title: "Cancel failed", description: detail, tone: "danger" });
    } finally {
      setBusyId(null);
    }
  }

  async function onArchive(id: string) {
    setBusyId(id);
    setError(null);
    try {
      await archiveVaultSubscription(id);
      toast.push({ title: "Subscription archived", tone: "success" });
      await load();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Archive failed";
      setError(detail);
      toast.push({ title: "Archive failed", description: detail, tone: "danger" });
    } finally {
      setBusyId(null);
    }
  }

  async function onRestore(id: string) {
    setBusyId(id);
    setError(null);
    try {
      await restoreVaultSubscription(id);
      toast.push({ title: "Subscription restored", tone: "success" });
      await load();
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Restore failed";
      setError(detail);
      toast.push({ title: "Restore failed", description: detail, tone: "danger" });
    } finally {
      setBusyId(null);
    }
  }

  function renderActions(row: VaultSubscription) {
    const busy = busyId === row.id;
    const archived = row.archived_at != null;
    const cancelled = row.status === "cancelled" || row.cancelled_at != null;

    return (
      <div className="flex flex-wrap justify-end gap-1.5 md:justify-start">
        {archived ? (
          <ConfirmAction
            label="Restore"
            title="Restore subscription record?"
            description="Restore this cancelled subscription to your active list."
            confirmLabel="Restore"
            disabled={busy}
            busy={busy}
            onConfirm={() => onRestore(row.id)}
          />
        ) : cancelled ? (
          <ConfirmAction
            label="Archive"
            title="Archive subscription?"
            description="Hide this cancelled subscription from your active subscriber list."
            confirmLabel="Archive"
            tone="danger"
            disabled={busy}
            busy={busy}
            onConfirm={() => onArchive(row.id)}
          />
        ) : row.status === "active" ? (
          <ConfirmAction
            label="Cancel subscription"
            title="Cancel buyer subscription?"
            description="Cancel this active Vault subscription on behalf of the buyer. This stops future billing and access per your Vault policy."
            confirmLabel="Cancel subscription"
            tone="danger"
            requireReason
            reasonLabel="Reason for cancellation"
            reasonPlaceholder="Explain why you are cancelling this buyer's subscription…"
            disabled={busy}
            busy={busy}
            onConfirm={() => onCancel(row.id)}
          />
        ) : null}
      </div>
    );
  }

  return (
    <VaultStudioShell
      title="Vault subscribers"
      description="Buyers subscribed to your Vault content. Cancel active subscriptions only when necessary — archived records are for cancelled subscriptions."
      actions={
        <Link href="/host/vault">
          <Button variant="ghost" size="sm">
            Back to Vault
          </Button>
        </Link>
      }
    >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        <div className="space-y-4">
          <SectionHeader
            title="Subscribers"
            description={`${filtered.length} subscription${filtered.length === 1 ? "" : "s"}${includeArchived ? " (including archived)" : ""}.`}
          />

          {!loading && rows.length > 0 ? (
            <FilterBar
              trailing={
                <label className="flex cursor-pointer items-center gap-2 text-sm text-foreground">
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-primary"
                    checked={includeArchived}
                    onChange={(e) => setIncludeArchived(e.target.checked)}
                  />
                  <span className="font-semibold">Show archived</span>
                </label>
              }
            >
              <Select
                label="Status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="all">All statuses</option>
                {statusOptions.map((status) => (
                  <option key={status} value={status}>
                    {status.replace(/_/g, " ")}
                  </option>
                ))}
              </Select>
            </FilterBar>
          ) : null}

          {loading ? null : rows.length === 0 ? (
            <EmptyState
              title="No Vault subscribers yet"
              description="When buyers subscribe to your Vault, they will appear here."
            />
          ) : (
            <DataTable
              rows={filtered}
              rowKey={(row) => row.id}
              emptyTitle="No matching subscriptions"
              emptyDescription="Try a different status filter."
              columns={[
                {
                  key: "plan",
                  header: "Plan",
                  primary: true,
                  cell: (row) => (
                    <div className="space-y-0.5">
                      <p className="font-semibold text-foreground">{row.plan_label}</p>
                      <p className="font-mono text-xs text-muted-foreground">
                        Buyer {row.buyer_user_id.slice(0, 8)}…
                      </p>
                    </div>
                  ),
                },
                {
                  key: "status",
                  header: "Status",
                  cell: (row) => (
                    <div className="flex flex-wrap gap-1.5">
                      <StatusBadge status={row.status} />
                      {row.archived_at ? <StatusBadge status="archived" /> : null}
                    </div>
                  ),
                },
                {
                  key: "price",
                  header: "Price",
                  cell: (row) => (
                    <span className="font-semibold">
                      {formatNgn(row.price)} {row.currency}
                    </span>
                  ),
                },
                {
                  key: "started",
                  header: "Started",
                  cell: (row) => (
                    <span className="text-sm text-muted-foreground">
                      {formatDateTime(row.started_at)}
                    </span>
                  ),
                },
                {
                  key: "ends",
                  header: "Ends",
                  cell: (row) => (
                    <span className="text-sm text-muted-foreground">
                      {formatDateTime(row.ends_at)}
                    </span>
                  ),
                },
                {
                  key: "actions",
                  header: "Actions",
                  cell: (row) => renderActions(row),
                },
              ]}
              mobileCard={(row) => (
                <Card className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-bold text-foreground">{row.plan_label}</h3>
                    <StatusBadge status={row.status} />
                    {row.archived_at ? <StatusBadge status="archived" /> : null}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {formatNgn(row.price)} {row.currency} · Started{" "}
                    {formatDateTime(row.started_at)}
                  </p>
                  {renderActions(row)}
                </Card>
              )}
            />
          )}
        </div>
    </VaultStudioShell>
  );
}
