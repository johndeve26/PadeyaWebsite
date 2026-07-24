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

export default function AdminUsersPage() {
  const toast = useToast();
  const router = useRouter();
  const { user } = useAuth();
  const canView = userHasPermission(user, "admin.users.view");
  const canSuspend = userHasPermission(user, "admin.users.suspend");

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
              <DataTable
                rows={rows}
                rowKey={(row) => row.id}
                emptyTitle="No users"
                columns={[
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
                              busy={busyId === row.id}
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
                              busy={busyId === row.id}
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
