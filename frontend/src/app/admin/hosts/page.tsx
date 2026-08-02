"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  ConfirmAction,
  DataTable,
  Dropdown,
  EmptyState,
  FilterBar,
  Modal,
  Select,
  SkeletonLoader,
  StatusBadge,
  Textarea,
  useToast,
  type DropdownItem,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import { formatDateTime } from "@/lib/format";
import {
  approveHostVerification,
  fetchAdminVerifications,
  forceDeleteHostWorkspace,
  rejectHostVerification,
  restoreHostWorkspace,
  suspendHostWorkspace,
} from "@/lib/hosts-lifecycle-api";
import type { HostVerification } from "@/lib/types/lifecycle";

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Verified / approved" },
  { value: "rejected", label: "Rejected" },
];

function hostLabel(v: HostVerification): string {
  return v.host_display_name?.trim() || "Unnamed host";
}

function isPending(status: string): boolean {
  return status === "pending";
}

function workspaceStatus(v: HostVerification): string {
  return (v.host_status || "").toLowerCase();
}

function isSelectableForDeactivate(v: HostVerification): boolean {
  const status = workspaceStatus(v);
  return status === "active" || status === "pending_verification";
}

function isSelectableForForceDelete(v: HostVerification): boolean {
  return workspaceStatus(v) === "suspended";
}

function isSelectable(
  v: HostVerification,
  canSuspend: boolean,
  canForceDelete: boolean,
): boolean {
  if (canSuspend && isSelectableForDeactivate(v)) return true;
  if (canForceDelete && isSelectableForForceDelete(v)) return true;
  return false;
}

export default function AdminHostsPage() {
  const toast = useToast();
  const router = useRouter();
  const { user } = useAuth();
  const canVerify = userHasPermission(user, "hosts.verify");
  const canSuspend = userHasPermission(user, "hosts.suspend");
  const canForceDelete = userHasPermission(user, "hosts.force_delete");
  const canViewUsers = userHasPermission(user, "admin.users.view");
  const canSelect = canSuspend || canForceDelete;

  const [rows, setRows] = useState<HostVerification[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [selectedHostIds, setSelectedHostIds] = useState<Set<string>>(
    new Set(),
  );
  const [rejectTarget, setRejectTarget] = useState<HostVerification | null>(
    null,
  );
  const [rejectNotes, setRejectNotes] = useState("");
  const [rejectError, setRejectError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const status = statusFilter === "all" ? undefined : statusFilter;
    const data = await fetchAdminVerifications(status);
    setRows(data);
  }, [statusFilter]);

  useEffect(() => {
    setSelectedHostIds(new Set());
  }, [statusFilter]);

  useEffect(() => {
    if (!canVerify) return;
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load verifications",
          );
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [canVerify, load]);

  const filtered = useMemo(() => rows ?? [], [rows]);

  const hostById = useMemo(() => {
    const map = new Map<string, HostVerification>();
    for (const row of filtered) {
      if (!map.has(row.host_id)) map.set(row.host_id, row);
    }
    return map;
  }, [filtered]);

  const selectableHostIds = useMemo(() => {
    if (!canSelect) return [];
    const ids: string[] = [];
    for (const [hostId, row] of hostById) {
      if (isSelectable(row, canSuspend, canForceDelete)) ids.push(hostId);
    }
    return ids;
  }, [hostById, canSelect, canSuspend, canForceDelete]);

  const selectedActiveCount = useMemo(() => {
    if (!canSuspend) return 0;
    return [...selectedHostIds].filter((id) => {
      const row = hostById.get(id);
      return row ? isSelectableForDeactivate(row) : false;
    }).length;
  }, [selectedHostIds, hostById, canSuspend]);

  const selectedForceDeleteCount = useMemo(() => {
    if (!canForceDelete) return 0;
    return [...selectedHostIds].filter((id) => {
      const row = hostById.get(id);
      return row ? isSelectableForForceDelete(row) : false;
    }).length;
  }, [selectedHostIds, hostById, canForceDelete]);

  const selectedCount = selectedActiveCount + selectedForceDeleteCount;

  const allSelectableChecked =
    selectableHostIds.length > 0 &&
    selectableHostIds.every((id) => selectedHostIds.has(id));
  const someSelectableChecked =
    selectableHostIds.some((id) => selectedHostIds.has(id)) &&
    !allSelectableChecked;

  function toggleSelect(hostId: string) {
    setSelectedHostIds((prev) => {
      const next = new Set(prev);
      if (next.has(hostId)) next.delete(hostId);
      else next.add(hostId);
      return next;
    });
  }

  function toggleSelectAll() {
    setSelectedHostIds((prev) => {
      if (allSelectableChecked) {
        const next = new Set(prev);
        for (const id of selectableHostIds) next.delete(id);
        return next;
      }
      const next = new Set(prev);
      for (const id of selectableHostIds) next.add(id);
      return next;
    });
  }

  async function onApprove(id: string) {
    setBusyId(id);
    try {
      await approveHostVerification(id);
      toast.push({ tone: "success", title: "Verification approved" });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Approval failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onReject(id: string, notes?: string) {
    const trimmed = (notes ?? rejectNotes).trim();
    if (trimmed.length < 3) {
      setRejectError("Enter at least 3 characters.");
      return;
    }
    setBusyId(id);
    try {
      await rejectHostVerification(id, trimmed);
      toast.push({ tone: "success", title: "Verification rejected" });
      setRejectTarget(null);
      setRejectNotes("");
      setRejectError(null);
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Rejection failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onDeactivate(hostId: string, reason?: string) {
    setBusyId(hostId);
    try {
      await suspendHostWorkspace(
        hostId,
        reason?.trim() || "Deactivated by admin",
      );
      toast.push({ tone: "success", title: "Host workspace deactivated" });
      setSelectedHostIds((prev) => {
        if (!prev.has(hostId)) return prev;
        const next = new Set(prev);
        next.delete(hostId);
        return next;
      });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Deactivate failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onBulkDeactivate(reason?: string) {
    if (selectedActiveCount === 0) return;
    const targets = [...selectedHostIds].filter((id) => {
      const row = hostById.get(id);
      return row ? isSelectableForDeactivate(row) : false;
    });
    if (targets.length === 0) return;

    const cleaned = reason?.trim() || "Bulk deactivated by admin";
    setBulkBusy(true);
    let ok = 0;
    let fail = 0;
    let lastError: string | null = null;
    try {
      for (const hostId of targets) {
        try {
          await suspendHostWorkspace(hostId, cleaned);
          ok += 1;
        } catch (err) {
          fail += 1;
          lastError = err instanceof ApiError ? err.detail : "Try again";
        }
      }
      setSelectedHostIds(new Set());
      await load();
      if (fail === 0) {
        toast.push({
          tone: "success",
          title: `${ok} host workspace${ok === 1 ? "" : "s"} deactivated`,
        });
      } else if (ok === 0) {
        toast.push({
          tone: "danger",
          title: "Bulk deactivate failed",
          description: lastError ?? "Try again",
        });
      } else {
        toast.push({
          tone: "danger",
          title: `${ok} deactivated, ${fail} failed`,
          description: lastError ?? "Review remaining workspaces and retry",
        });
      }
    } finally {
      setBulkBusy(false);
    }
  }

  async function onRestore(hostId: string, reason?: string) {
    setBusyId(hostId);
    try {
      await restoreHostWorkspace(
        hostId,
        reason?.trim() || "Restored by admin",
      );
      toast.push({ tone: "success", title: "Host workspace restored" });
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

  async function onForceDelete(hostId: string, reason?: string) {
    setBusyId(hostId);
    try {
      await forceDeleteHostWorkspace(
        hostId,
        reason?.trim() || "Force-deleted by admin",
      );
      toast.push({ tone: "success", title: "Host workspace force-deleted" });
      setSelectedHostIds((prev) => {
        if (!prev.has(hostId)) return prev;
        const next = new Set(prev);
        next.delete(hostId);
        return next;
      });
      await load();
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Force delete failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusyId(null);
    }
  }

  async function onBulkForceDelete(reason?: string) {
    if (selectedForceDeleteCount === 0) return;
    const targets = [...selectedHostIds].filter((id) => {
      const row = hostById.get(id);
      return row ? isSelectableForForceDelete(row) : false;
    });
    if (targets.length === 0) return;

    const cleaned = reason?.trim() || "Bulk force-deleted by admin";
    setBulkBusy(true);
    let ok = 0;
    let fail = 0;
    let lastError: string | null = null;
    try {
      for (const hostId of targets) {
        try {
          await forceDeleteHostWorkspace(hostId, cleaned);
          ok += 1;
        } catch (err) {
          fail += 1;
          lastError = err instanceof ApiError ? err.detail : "Try again";
        }
      }
      setSelectedHostIds(new Set());
      await load();
      if (fail === 0) {
        toast.push({
          tone: "success",
          title: `${ok} host workspace${ok === 1 ? "" : "s"} force-deleted`,
        });
      } else if (ok === 0) {
        toast.push({
          tone: "danger",
          title: "Bulk force delete failed",
          description: lastError ?? "Try again",
        });
      } else {
        toast.push({
          tone: "danger",
          title: `${ok} force-deleted, ${fail} failed`,
          description:
            lastError ?? "Only suspended workspaces can be force-deleted",
        });
      }
    } finally {
      setBulkBusy(false);
    }
  }

  function actionItems(v: HostVerification): DropdownItem[] {
    const items: DropdownItem[] = [];
    if (canViewUsers && v.owner_user_id) {
      items.push({
        id: "owner",
        label: "View owner account",
        onSelect: () =>
          router.push(`/admin/users/${encodeURIComponent(v.owner_user_id!)}`),
      });
    }
    items.push({
      id: "events",
      label: `Events (${v.events_count ?? 0})`,
      onSelect: () => router.push("/admin/events"),
    });
    items.push({
      id: "fees",
      label: "Fee overrides",
      onSelect: () =>
        router.push(`/admin/hosts/${encodeURIComponent(v.host_id)}/fees`),
    });
    items.push({
      id: "earnings",
      label: "Earnings",
      onSelect: () =>
        router.push(`/admin/hosts/${encodeURIComponent(v.host_id)}/earnings`),
    });
    items.push({
      id: "legacy",
      label: "Legacy reputation",
      onSelect: () => router.push("/admin/legacy"),
    });
    items.push({
      id: "reviews",
      label: "Reviews queue",
      onSelect: () => router.push("/admin/reviews"),
    });
    items.push({
      id: "ambassadors",
      label: "Ambassadors",
      onSelect: () => router.push("/admin/ambassadors"),
    });
    if (isPending(v.status)) {
      items.push({
        id: "approve",
        label: "Approve verification",
        onSelect: () => void onApprove(v.id),
        disabled: busyId === v.id,
      });
      items.push({
        id: "reject",
        label: "Reject verification",
        danger: true,
        onSelect: () => setRejectTarget(v),
        disabled: busyId === v.id,
      });
    }
    return items;
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Hosts"
      description="Verify host accounts, manage workspace lifecycle, and jump to host-related admin tools."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/legacy">
            <Button variant="secondary">Legacy tiers</Button>
          </Link>
          <Link href="/admin/events">
            <Button variant="secondary">Events</Button>
          </Link>
          <Link href="/admin/users">
            <Button variant="secondary">Users</Button>
          </Link>
        </div>
      }
    >
      {!canVerify ? (
        <Alert tone="danger" title="Permission denied">
          You need <code className="text-xs">hosts.verify</code> to manage host
          verifications.
        </Alert>
      ) : null}

      {error ? (
        <Alert tone="danger" title="Failed to load">
          {error}
        </Alert>
      ) : null}

      {canVerify && canSelect ? (
        <Alert tone="info" title="Workspace soft delete only">
          Deactivate and force-delete apply to the host workspace only — the
          owner user account is unchanged. Suspend first, then force-delete for
          soft end-of-life. Hard delete stays blocked.
        </Alert>
      ) : null}

      {canVerify && rows ? (
        <>
          <FilterBar
            trailing={
              <span className="text-sm text-muted-foreground">
                {filtered.length} verification
                {filtered.length === 1 ? "" : "s"}
              </span>
            }
          >
            <Select
              label="Status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
          </FilterBar>

          {filtered.length === 0 && !error ? (
            <EmptyState
              title="No verifications"
              description={
                statusFilter === "pending"
                  ? "Pending host verification requests appear here."
                  : "No verifications match this status filter."
              }
            />
          ) : (
            <>
              {canSelect ? (
                <div className="mb-4 flex flex-col gap-3 rounded-[var(--radius-lg)] border border-border bg-card px-4 py-3 sm:flex-row sm:items-center sm:justify-between dark:bg-surface-elevated">
                  <div className="flex flex-wrap items-center gap-4">
                    <label className="inline-flex cursor-pointer items-center gap-2.5 text-sm text-foreground">
                      <input
                        id="admin-hosts-select-all"
                        type="checkbox"
                        checked={allSelectableChecked}
                        ref={(el) => {
                          if (el) el.indeterminate = someSelectableChecked;
                        }}
                        onChange={() => toggleSelectAll()}
                        disabled={selectableHostIds.length === 0 || bulkBusy}
                        className="h-4 w-4 accent-[color:var(--brand-green)] disabled:cursor-not-allowed disabled:opacity-40"
                      />
                      <span>Select all on page</span>
                    </label>
                    <span className="text-sm text-muted-foreground">
                      {selectedCount > 0
                        ? `${selectedCount} selected${
                            selectedForceDeleteCount > 0
                              ? ` (${selectedForceDeleteCount} suspended)`
                              : ""
                          }`
                        : canForceDelete && canSuspend
                          ? "Select active to deactivate, or suspended to force-delete"
                          : canForceDelete
                            ? "Select suspended workspaces to force-delete"
                            : "Select active workspaces to deactivate"}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {canSuspend ? (
                      <ConfirmAction
                        label="Deactivate selected"
                        title={`Deactivate ${selectedActiveCount} host workspace${selectedActiveCount === 1 ? "" : "s"}?`}
                        description="Blocks host studio access for each selected workspace. Owner login stays intact. Events and commerce history remain."
                        confirmLabel="Deactivate selected"
                        tone="danger"
                        size="sm"
                        disabled={selectedActiveCount === 0}
                        busy={bulkBusy}
                        requireReason
                        reasonLabel="Reason for deactivation"
                        onConfirm={(reason) => onBulkDeactivate(reason)}
                      />
                    ) : null}
                    {canForceDelete ? (
                      <ConfirmAction
                        label="Force delete selected"
                        title={`Force-delete ${selectedForceDeleteCount} suspended workspace${selectedForceDeleteCount === 1 ? "" : "s"}?`}
                        description="Only already-suspended workspaces are included. Soft EOL keeps history; the owner user account is not deleted."
                        confirmLabel="Force delete selected"
                        tone="danger"
                        size="sm"
                        disabled={selectedForceDeleteCount === 0}
                        busy={bulkBusy}
                        requireReason
                        reasonLabel="Reason for force delete"
                        onConfirm={(reason) => onBulkForceDelete(reason)}
                      />
                    ) : null}
                  </div>
                </div>
              ) : null}

              <DataTable
                rows={filtered}
                rowKey={(v) => v.id}
                emptyTitle="No verifications"
                columns={[
                  ...(canSelect
                    ? [
                        {
                          key: "select",
                          header: "",
                          className: "w-10",
                          cell: (v: HostVerification) => {
                            const selectable = isSelectable(
                              v,
                              canSuspend,
                              canForceDelete,
                            );
                            return (
                              <input
                                type="checkbox"
                                checked={selectedHostIds.has(v.host_id)}
                                disabled={!selectable || bulkBusy}
                                onChange={() => toggleSelect(v.host_id)}
                                aria-label={`Select ${hostLabel(v)}`}
                                className="h-4 w-4 accent-[color:var(--brand-green)] disabled:cursor-not-allowed disabled:opacity-40"
                              />
                            );
                          },
                        },
                      ]
                    : []),
                  {
                    key: "host",
                    header: "Host",
                    primary: true,
                    cell: (v) => (
                      <div className="min-w-0">
                        <p className="font-semibold text-foreground">
                          {hostLabel(v)}
                        </p>
                        <p className="truncate text-sm text-muted-foreground">
                          {v.host_slug ? `@${v.host_slug}` : null}
                          {v.host_slug && v.owner_email ? " · " : null}
                          {v.owner_email ?? null}
                          {!v.host_slug && !v.owner_email
                            ? v.host_id.slice(0, 8)
                            : null}
                        </p>
                      </div>
                    ),
                  },
                  {
                    key: "host_status",
                    header: "Workspace",
                    cell: (v) =>
                      v.host_status ? (
                        <StatusBadge status={v.host_status} />
                      ) : (
                        "—"
                      ),
                  },
                  {
                    key: "status",
                    header: "Verification",
                    cell: (v) => <StatusBadge status={v.status} />,
                  },
                  {
                    key: "events",
                    header: "Events",
                    cell: (v) => (
                      <span className="text-sm text-foreground">
                        {v.events_count ?? 0}
                      </span>
                    ),
                  },
                  {
                    key: "submitted",
                    header: "Submitted",
                    cell: (v) => formatDateTime(v.created_at),
                  },
                  {
                    key: "reviewed",
                    header: "Reviewed",
                    cell: (v) =>
                      v.reviewed_at ? formatDateTime(v.reviewed_at) : "—",
                  },
                  {
                    key: "notes",
                    header: "Notes",
                    cell: (v) => (
                      <span className="text-sm text-muted-foreground">
                        {v.notes ?? "—"}
                      </span>
                    ),
                  },
                  {
                    key: "actions",
                    header: "Actions",
                    cell: (v) => (
                      <div className="flex flex-wrap items-center gap-2">
                        {canViewUsers && v.owner_user_id ? (
                          <Link
                            href={`/admin/users/${encodeURIComponent(v.owner_user_id)}`}
                          >
                            <Button variant="secondary" size="sm">
                              View owner
                            </Button>
                          </Link>
                        ) : null}
                        {canSuspend && isSelectableForDeactivate(v) ? (
                          <ConfirmAction
                            label="Deactivate"
                            title="Deactivate this host workspace?"
                            description="Blocks host studio access. The owner user can still log in. Commerce history stays."
                            confirmLabel="Deactivate"
                            tone="danger"
                            size="sm"
                            busy={busyId === v.host_id || bulkBusy}
                            requireReason
                            reasonLabel="Reason for deactivation"
                            onConfirm={(reason) =>
                              onDeactivate(v.host_id, reason)
                            }
                          />
                        ) : null}
                        {canSuspend && workspaceStatus(v) === "suspended" ? (
                          <ConfirmAction
                            label="Restore"
                            title="Restore this host workspace?"
                            description="Re-enables host studio access for this organizer workspace."
                            confirmLabel="Restore"
                            size="sm"
                            busy={busyId === v.host_id || bulkBusy}
                            onConfirm={(reason) =>
                              onRestore(v.host_id, reason)
                            }
                          />
                        ) : null}
                        {canForceDelete && isSelectableForForceDelete(v) ? (
                          <ConfirmAction
                            label="Force delete"
                            title="Force-delete this suspended workspace?"
                            description="Soft end-of-life only. Events and commerce history stay. The owner user account is not deleted."
                            confirmLabel="Force delete"
                            tone="danger"
                            size="sm"
                            busy={busyId === v.host_id || bulkBusy}
                            requireReason
                            reasonLabel="Reason for force delete"
                            onConfirm={(reason) =>
                              onForceDelete(v.host_id, reason)
                            }
                          />
                        ) : null}
                        {isPending(v.status) ? (
                          <>
                            <ConfirmAction
                              label="Approve"
                              title="Approve verification?"
                              description="This marks the host as verified and allows full platform access."
                              confirmLabel="Approve"
                              size="sm"
                              busy={busyId === v.id}
                              onConfirm={() => onApprove(v.id)}
                            />
                            <Button
                              variant="danger"
                              size="sm"
                              disabled={busyId === v.id}
                              onClick={() => {
                                setRejectTarget(v);
                                setRejectNotes("");
                                setRejectError(null);
                              }}
                            >
                              Reject
                            </Button>
                          </>
                        ) : null}
                        <Dropdown
                          label="More"
                          align="right"
                          items={actionItems(v)}
                        />
                      </div>
                    ),
                  },
                ]}
              />
            </>
          )}
        </>
      ) : null}

      {canVerify && rows == null && !error ? (
        <SkeletonLoader lines={4} />
      ) : null}

      <Modal
        open={Boolean(rejectTarget)}
        onClose={() => {
          if (busyId) return;
          setRejectTarget(null);
          setRejectNotes("");
          setRejectError(null);
        }}
        title={
          rejectTarget
            ? `Reject ${hostLabel(rejectTarget)}?`
            : "Reject verification?"
        }
        description="The host will be notified. Provide clear notes for the rejection."
        footer={
          <>
            <Button
              variant="ghost"
              size="sm"
              disabled={Boolean(busyId)}
              onClick={() => {
                setRejectTarget(null);
                setRejectNotes("");
                setRejectError(null);
              }}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              variant="danger"
              disabled={Boolean(busyId) || !rejectTarget}
              onClick={() => {
                if (rejectTarget) void onReject(rejectTarget.id);
              }}
            >
              {busyId ? "Working…" : "Reject"}
            </Button>
          </>
        }
      >
        <Textarea
          label="Rejection notes"
          hint="Required for verification rejection."
          placeholder="Explain what is missing or invalid…"
          value={rejectNotes}
          error={rejectError ?? undefined}
          onChange={(e) => {
            setRejectNotes(e.target.value);
            if (rejectError) setRejectError(null);
          }}
          rows={3}
        />
      </Modal>
    </DashboardShell>
  );
}
