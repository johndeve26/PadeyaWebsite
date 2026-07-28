"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AdminUserSignalBadges } from "@/components/admin/AdminUserBadges";
import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  ConfirmAction,
  DataTable,
  EmptyState,
  FilterBar,
  Input,
  Pagination,
  SectionHeader,
  Select,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import {
  deactivateUser,
  fetchAdminUsers,
  lookupAdminUserByEmail,
  restoreUser,
} from "@/lib/admin-lifecycle-api";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import { formatDateTime } from "@/lib/format";
import type { AdminUserRow } from "@/lib/types/lifecycle";

const PAGE_SIZE = 40;

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "under_review", label: "Under review" },
  { value: "suspended", label: "Suspended" },
  { value: "restricted", label: "Restricted" },
  { value: "banned", label: "Banned" },
  { value: "inactive", label: "Inactive (legacy)" },
];

const ROLE_OPTIONS = [
  { value: "all", label: "All roles" },
  { value: "buyer", label: "Buyer" },
  { value: "host", label: "Host" },
  { value: "host_staff", label: "Host staff" },
  { value: "support_agent", label: "Support" },
  { value: "finance_admin", label: "Finance" },
  { value: "super_admin", label: "Super admin" },
];

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isSelectableForDeactivate(
  row: AdminUserRow,
  currentUserId: string | undefined,
): boolean {
  return row.is_active && row.id !== currentUserId;
}

export default function AdminUsersPage() {
  const toast = useToast();
  const router = useRouter();
  const { user } = useAuth();
  const canView = userHasPermission(user, "admin.users.view");
  const canSuspend = userHasPermission(user, "admin.users.suspend");
  const currentUserId = user?.id;

  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [roleFilter, setRoleFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<AdminUserRow[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [apiDenied, setApiDenied] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const [lookup, setLookup] = useState("");
  const [lookupBusy, setLookupBusy] = useState(false);
  const trimmedLookup = lookup.trim();
  const validId = UUID_RE.test(trimmedLookup);
  const looksLikeEmail = EMAIL_RE.test(trimmedLookup);
  const canLookup = validId || looksLikeEmail;
  const denied = !canView || apiDenied;

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedQ(q.trim());
      setPage(1);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [q]);

  useEffect(() => {
    setSelectedIds(new Set());
  }, [debouncedQ, statusFilter, roleFilter, page]);

  const load = useCallback(async () => {
    const data = await fetchAdminUsers({
      q: debouncedQ || undefined,
      status: statusFilter,
      role: roleFilter,
      page,
      limit: PAGE_SIZE,
    });
    setRows(data.items);
    setTotal(data.total);
  }, [debouncedQ, statusFilter, roleFilter, page]);

  useEffect(() => {
    if (!canView) return;
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) {
          setError(null);
          setApiDenied(false);
        }
      } catch (err) {
        if (!active) return;
        if (err instanceof ApiError && err.status === 403) {
          setApiDenied(true);
          setError(null);
        } else {
          setApiDenied(false);
          setError(err instanceof ApiError ? err.detail : "Failed to load users");
        }
        setRows([]);
        setTotal(0);
      }
    })();
    return () => {
      active = false;
    };
  }, [canView, load]);

  const pageCount = useMemo(
    () => Math.max(1, Math.ceil(total / PAGE_SIZE)),
    [total],
  );

  const selectableIds = useMemo(() => {
    if (!rows || !canSuspend) return [];
    return rows
      .filter((row) => isSelectableForDeactivate(row, currentUserId))
      .map((row) => row.id);
  }, [rows, canSuspend, currentUserId]);

  const selectedActiveCount = useMemo(() => {
    if (!rows) return 0;
    return [...selectedIds].filter((id) => {
      const row = rows.find((r) => r.id === id);
      return row ? isSelectableForDeactivate(row, currentUserId) : false;
    }).length;
  }, [selectedIds, rows, currentUserId]);

  const allSelectableChecked =
    selectableIds.length > 0 &&
    selectableIds.every((id) => selectedIds.has(id));
  const someSelectableChecked =
    selectableIds.some((id) => selectedIds.has(id)) && !allSelectableChecked;

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    setSelectedIds((prev) => {
      if (allSelectableChecked) {
        const next = new Set(prev);
        for (const id of selectableIds) next.delete(id);
        return next;
      }
      const next = new Set(prev);
      for (const id of selectableIds) next.add(id);
      return next;
    });
  }

  async function openLookup() {
    if (!canLookup || !canView) return;
    setLookupBusy(true);
    try {
      if (validId) {
        router.push(`/admin/users/${encodeURIComponent(trimmedLookup)}`);
        return;
      }
      const row = await lookupAdminUserByEmail(trimmedLookup);
      router.push(`/admin/users/${encodeURIComponent(row.id)}`);
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "User not found",
        description:
          err instanceof ApiError ? err.detail : "Check the UUID or email and try again",
      });
    } finally {
      setLookupBusy(false);
    }
  }

  async function onDeactivate(userId: string, reason?: string) {
    setBusyId(userId);
    try {
      await deactivateUser(userId, reason?.trim() || "Deactivated by admin");
      toast.push({ tone: "success", title: "User deactivated" });
      setSelectedIds((prev) => {
        if (!prev.has(userId)) return prev;
        const next = new Set(prev);
        next.delete(userId);
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
    if (!rows || selectedActiveCount === 0) return;
    const targets = [...selectedIds].filter((id) => {
      const row = rows.find((r) => r.id === id);
      return row ? isSelectableForDeactivate(row, currentUserId) : false;
    });
    if (targets.length === 0) return;

    const cleaned = reason?.trim() || "Bulk deactivated by admin";
    setBulkBusy(true);
    let ok = 0;
    let fail = 0;
    let lastError: string | null = null;
    try {
      for (const userId of targets) {
        try {
          await deactivateUser(userId, cleaned);
          ok += 1;
        } catch (err) {
          fail += 1;
          lastError = err instanceof ApiError ? err.detail : "Try again";
        }
      }
      setSelectedIds(new Set());
      await load();
      if (fail === 0) {
        toast.push({
          tone: "success",
          title: `${ok} user${ok === 1 ? "" : "s"} deactivated`,
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
          description: lastError ?? "Review remaining active users and retry",
        });
      }
    } finally {
      setBulkBusy(false);
    }
  }

  async function onRestore(userId: string, reason?: string) {
    setBusyId(userId);
    try {
      await restoreUser(userId, reason?.trim() || "Restored by admin");
      toast.push({ tone: "success", title: "User restored" });
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

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Users"
      description="Browse and manage Pàdéyá accounts. Passwords, tokens, and private message bodies are never shown."
    >
      {!canView || denied ? (
        <Alert tone="danger" title="Permission denied">
          You need <code className="text-xs">admin.users.view</code> to browse
          users. Ask a super admin if you need access.
        </Alert>
      ) : (
        <>
          <Alert tone="info" title="Hard delete blocked">
            Users cannot be permanently deleted. Deactivation revokes access while
            preserving orders, tickets, and ledger history.
          </Alert>

          <Card className="space-y-4">
            <SectionHeader
              eyebrow="Quick open"
              title="Open by UUID or email"
              description="Jump straight to a known account from a support ticket or audit log."
            />
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="min-w-0 flex-1">
                <Input
                  label="User UUID or email"
                  placeholder="buyer@demo.padeye.test"
                  value={lookup}
                  onChange={(e) => setLookup(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && canLookup && !lookupBusy) {
                      e.preventDefault();
                      void openLookup();
                    }
                  }}
                />
              </div>
              <Button
                type="button"
                disabled={!canLookup || lookupBusy}
                onClick={() => void openLookup()}
              >
                {lookupBusy ? "Looking up…" : "Open user"}
              </Button>
            </div>
          </Card>

          {error ? (
            <Alert tone="danger" title="Failed to load">
              {error}
            </Alert>
          ) : null}

          <FilterBar
            trailing={
              <span className="text-sm text-muted-foreground">
                {total} user{total === 1 ? "" : "s"}
              </span>
            }
          >
            <Input
              label="Search"
              placeholder="Name or email"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <Select
              label="Status"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
            <Select
              label="Role"
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setPage(1);
              }}
            >
              {ROLE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
          </FilterBar>

          {rows === null ? <SkeletonLoader lines={6} /> : null}

          {rows && rows.length === 0 && !error ? (
            <EmptyState
              title="No users match"
              description={
                debouncedQ || statusFilter !== "all" || roleFilter !== "all"
                  ? "Try a different search or filter."
                  : "Registered accounts will appear here."
              }
            />
          ) : null}

          {rows && rows.length > 0 ? (
            <>
              {canSuspend ? (
                <div className="flex flex-col gap-3 rounded-[var(--radius-lg)] border border-border bg-card px-4 py-3 sm:flex-row sm:items-center sm:justify-between dark:bg-surface-elevated">
                  <div className="flex flex-wrap items-center gap-4">
                    <label className="inline-flex cursor-pointer items-center gap-2.5 text-sm text-foreground">
                      <input
                        id="admin-users-select-all"
                        type="checkbox"
                        checked={allSelectableChecked}
                        ref={(el) => {
                          if (el) el.indeterminate = someSelectableChecked;
                        }}
                        onChange={() => toggleSelectAll()}
                        disabled={selectableIds.length === 0 || bulkBusy}
                        className="h-4 w-4 accent-[color:var(--brand-green)] disabled:cursor-not-allowed disabled:opacity-40"
                      />
                      <span>Select all on page</span>
                    </label>
                    <span className="text-sm text-muted-foreground">
                      {selectedActiveCount > 0
                        ? `${selectedActiveCount} selected`
                        : "Select active users to deactivate"}
                    </span>
                  </div>
                  <ConfirmAction
                    label="Deactivate selected"
                    title={`Deactivate ${selectedActiveCount} user${selectedActiveCount === 1 ? "" : "s"}?`}
                    description="Revokes login and platform access for each selected active account. History stays in the database. Your own account is never included."
                    confirmLabel="Deactivate selected"
                    tone="danger"
                    size="sm"
                    disabled={selectedActiveCount === 0}
                    busy={bulkBusy}
                    requireReason
                    reasonLabel="Reason for deactivation"
                    onConfirm={(reason) => onBulkDeactivate(reason)}
                  />
                </div>
              ) : null}
              <DataTable
                rows={rows}
                rowKey={(row) => row.id}
                emptyTitle="No users"
                columns={[
                  ...(canSuspend
                    ? [
                        {
                          key: "select",
                          header: "",
                          className: "w-10",
                          cell: (row: AdminUserRow) => {
                            const selectable = isSelectableForDeactivate(
                              row,
                              currentUserId,
                            );
                            return (
                              <input
                                type="checkbox"
                                checked={selectedIds.has(row.id)}
                                disabled={!selectable || bulkBusy}
                                onChange={() => toggleSelect(row.id)}
                                aria-label={
                                  selectable
                                    ? `Select ${row.full_name}`
                                    : row.id === currentUserId
                                      ? "Cannot select your own account"
                                      : "Inactive users cannot be selected"
                                }
                                className="h-4 w-4 accent-[color:var(--brand-green)] disabled:cursor-not-allowed disabled:opacity-40"
                              />
                            );
                          },
                        },
                      ]
                    : []),
                  {
                    key: "name",
                    header: "Name",
                    primary: true,
                    cell: (row) => (
                      <div className="min-w-0">
                        <Link
                          href={`/admin/users/${encodeURIComponent(row.id)}`}
                          className="font-semibold text-foreground underline-offset-2 hover:underline"
                        >
                          {row.full_name}
                        </Link>
                        <p className="truncate text-sm text-muted-foreground">
                          {row.email}
                        </p>
                      </div>
                    ),
                  },
                  {
                    key: "status",
                    header: "Status",
                    cell: (row) => (
                      <AdminUserSignalBadges
                        accountStatus={row.account_status}
                        isActive={row.is_active}
                        isVerified={row.is_verified}
                        underReview={row.under_review}
                        securityLocked={row.security_locked}
                        ambassadorsBlocked={row.ambassadors_blocked}
                      />
                    ),
                  },
                  {
                    key: "roles",
                    header: "Roles",
                    cell: (row) => (
                      <span className="text-sm text-foreground">
                        {row.roles.join(", ") || "—"}
                      </span>
                    ),
                  },
                  {
                    key: "created",
                    header: "Created",
                    cell: (row) => formatDateTime(row.created_at),
                  },
                  {
                    key: "actions",
                    header: "Actions",
                    cell: (row) => (
                      <div className="flex flex-wrap gap-2">
                        <Link href={`/admin/users/${encodeURIComponent(row.id)}`}>
                          <Button variant="secondary" size="sm">
                            View
                          </Button>
                        </Link>
                        {canSuspend ? (
                          row.is_active ? (
                            <ConfirmAction
                              label="Deactivate"
                              title="Deactivate this user?"
                              description="Revokes login and platform access. History stays in the database."
                              confirmLabel="Deactivate"
                              tone="danger"
                              size="sm"
                              busy={busyId === row.id || bulkBusy}
                              disabled={row.id === currentUserId}
                              requireReason
                              reasonLabel="Reason for deactivation"
                              onConfirm={(reason) => onDeactivate(row.id, reason)}
                            />
                          ) : (
                            <ConfirmAction
                              label="Restore"
                              title="Restore this user?"
                              description="Re-enables account access if the user was previously deactivated."
                              confirmLabel="Restore"
                              size="sm"
                              busy={busyId === row.id || bulkBusy}
                              onConfirm={(reason) => onRestore(row.id, reason)}
                            />
                          )
                        ) : null}
                      </div>
                    ),
                  },
                ]}
              />
              <Pagination
                page={page}
                pageCount={pageCount}
                onPageChange={setPage}
              />
            </>
          ) : null}
        </>
      )}
    </DashboardShell>
  );
}
