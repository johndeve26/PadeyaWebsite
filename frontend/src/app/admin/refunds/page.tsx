"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  ConfirmAction,
  EmptyState,
  FilterBar,
  PageToolbar,
  RefundCard,
  Select,
  SkeletonLoader,
  StatCard,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import { userHasPermission, userHasRole } from "@/lib/auth/permissions";
import {
  escalateRefund,
  fetchStaffRefunds,
  reviewRefund,
} from "@/lib/finance-api";
import type { RefundRequest } from "@/lib/types/finance";

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "requested", label: "Requested" },
  { value: "under_review", label: "Under review" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

export default function AdminRefundsPage() {
  const { user } = useAuth();
  const canApprove =
    userHasRole(user, "finance_admin", "super_admin") ||
    userHasPermission(user, "refunds.approve");
  const [rows, setRows] = useState<RefundRequest[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [statusFilter, setStatusFilter] = useState("all");
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load() {
    setRows(await fetchStaffRefunds());
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load refunds");
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const counts = useMemo(
    () => ({
      open: rows?.filter((r) => r.status === "requested").length ?? 0,
      underReview: rows?.filter((r) => r.status === "under_review").length ?? 0,
      approved: rows?.filter((r) => r.status === "approved").length ?? 0,
    }),
    [rows],
  );

  const filtered = useMemo(
    () =>
      !rows
        ? []
        : statusFilter === "all"
          ? rows
          : rows.filter((r) => r.status === statusFilter),
    [rows, statusFilter],
  );

  function noteFor(id: string) {
    return (notes[id] ?? "").trim();
  }

  async function onEscalate(id: string) {
    setError(null);
    setSuccess(null);
    setBusyId(id);
    try {
      await escalateRefund(id, noteFor(id) || "Escalated for finance review");
      setNotes((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      setSuccess("Refund escalated for finance review.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Escalate failed");
    } finally {
      setBusyId(null);
    }
  }

  async function onReview(id: string, action: "approve" | "reject") {
    setError(null);
    setSuccess(null);
    setBusyId(id);
    try {
      await reviewRefund(id, action, noteFor(id) || undefined);
      setNotes((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      setSuccess(
        action === "approve" ? "Refund approved." : "Refund request rejected.",
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Review failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Refund review"
      description="Support can escalate. Only finance/super admin can approve refunds that change balances."
    >
      <PageToolbar>
        <Link href="/admin">
          <Button size="sm" variant="ghost">
            Admin home
          </Button>
        </Link>
        <Link href="/admin/payouts">
          <Button size="sm" variant="secondary">
            Payouts
          </Button>
        </Link>
      </PageToolbar>

      {error ? (
        <Alert tone="danger" title="Action failed">
          {error}
        </Alert>
      ) : null}
      {success ? (
        <Alert tone="success" title="Done">
          {success}
        </Alert>
      ) : null}

      {rows ? (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard title="Open requests" value={counts.open} />
            <StatCard title="Under review" value={counts.underReview} />
            <StatCard title="Approved" value={counts.approved} />
          </div>

          <FilterBar>
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

          <div className="space-y-4">
        {filtered.map((r) => {
          const actionable =
            r.status === "requested" || r.status === "under_review";
          return (
            <RefundCard
              key={r.id}
              refund={r}
              actions={
                actionable ? (
                  <div className="w-full space-y-3">
                    <Textarea
                      label="Review / escalation note"
                      hint="Optional context recorded with the next action"
                      value={notes[r.id] ?? ""}
                      onChange={(e) =>
                        setNotes((prev) => ({ ...prev, [r.id]: e.target.value }))
                      }
                    />
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={busyId === r.id}
                        onClick={() => void onEscalate(r.id)}
                      >
                        Escalate
                      </Button>
                      {canApprove ? (
                        <>
                          <ConfirmAction
                            label="Approve full refund"
                            title="Approve full refund?"
                            description={`This will refund ${formatNgn(r.requested_amount)} to the buyer and update host balances. This cannot be undone from this screen.`}
                            confirmLabel="Approve refund"
                            tone="danger"
                            busy={busyId === r.id}
                            onConfirm={() => onReview(r.id, "approve")}
                          />
                          <ConfirmAction
                            label="Reject"
                            title="Reject refund request?"
                            description="The buyer will not receive a refund. Add a note above if helpful for the audit trail."
                            confirmLabel="Reject request"
                            variant="ghost"
                            busy={busyId === r.id}
                            onConfirm={() => onReview(r.id, "reject")}
                          />
                        </>
                      ) : null}
                    </div>
                  </div>
                ) : undefined
              }
            />
          );
        })}
        {filtered.length === 0 && !error ? (
          <EmptyState
            title="No refund requests"
            description={
              statusFilter === "all"
                ? "Buyer refunds awaiting triage appear here."
                : "No refunds match this status filter."
            }
          />
        ) : null}
          </div>
        </>
      ) : null}

      {rows == null && !error ? <SkeletonLoader lines={4} /> : null}
    </DashboardShell>
  );
}
