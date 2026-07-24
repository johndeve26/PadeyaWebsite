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
  rejectHostVerification,
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

export default function AdminHostsPage() {
  const toast = useToast();
  const router = useRouter();
  const { user } = useAuth();
  const canVerify = userHasPermission(user, "hosts.verify");
  const canViewUsers = userHasPermission(user, "admin.users.view");

  const [rows, setRows] = useState<HostVerification[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [busyId, setBusyId] = useState<string | null>(null);
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
      description="Verify host accounts and jump to host-related admin tools."
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
            <DataTable
              rows={filtered}
              rowKey={(v) => v.id}
              emptyTitle="No verifications"
              columns={[
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
                      <Dropdown label="More" align="right" items={actionItems(v)} />
                    </div>
                  ),
                },
              ]}
            />
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
