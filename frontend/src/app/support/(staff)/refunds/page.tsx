"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  ConfirmAction,
  EmptyState,
  FilterBar,
  PageToolbar,
  Select,
  SkeletonLoader,
  StatCard,
  SupportCaseCard,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { escalateRefund, fetchStaffRefunds } from "@/lib/finance-api";
import type { RefundRequest } from "@/lib/types/finance";

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "requested", label: "Requested" },
  { value: "under_review", label: "Under review" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

export default function SupportRefundsPage() {
  const [rows, setRows] = useState<RefundRequest[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");

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
      inbox: (rows ?? []).filter(
        (r) => r.status === "requested" || r.status === "under_review",
      ).length,
      requested: (rows ?? []).filter((r) => r.status === "requested").length,
      underReview: (rows ?? []).filter((r) => r.status === "under_review").length,
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

  async function onEscalate(id: string) {
    setError(null);
    setSuccess(null);
    setBusyId(id);
    try {
      const note = (notes[id] || "").trim() || "Support escalation";
      await escalateRefund(id, note);
      setNotes((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      setSuccess("Case escalated to finance.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Escalate failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Support"
      title="Refund queue"
      description="View and escalate refund requests on Pàdéyá. Support cannot approve refunds or edit financial records."
    >
      <PageToolbar>
        <Link href="/support/desk">
          <Button size="sm" variant="ghost">
            Support home
          </Button>
        </Link>
      </PageToolbar>

      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}
      {success ? (
        <Alert tone="success" title="Escalated">
          {success}
        </Alert>
      ) : null}

      {rows ? (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard title="Inbox (open)" value={counts.inbox} />
            <StatCard title="New requests" value={counts.requested} />
            <StatCard title="Under review" value={counts.underReview} />
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
            {filtered.map((r) => (
              <SupportCaseCard
                key={r.id}
                refund={r}
                actions={
                  r.status === "requested" || r.status === "under_review" ? (
                    <div className="w-full space-y-3">
                      <Textarea
                        label="Escalation note"
                        hint="Optional context for finance"
                        value={notes[r.id] ?? ""}
                        onChange={(e) =>
                          setNotes((prev) => ({ ...prev, [r.id]: e.target.value }))
                        }
                      />
                      <ConfirmAction
                        label="Escalate to finance"
                        title="Escalate to finance?"
                        description="Finance will review this refund. You cannot approve or reject from support."
                        confirmLabel="Escalate case"
                        busy={busyId === r.id}
                        onConfirm={() => onEscalate(r.id)}
                      />
                    </div>
                  ) : undefined
                }
              />
            ))}
            {filtered.length === 0 && !error ? (
              <EmptyState
                title="No refund requests"
                description={
                  statusFilter === "all"
                    ? "When buyers submit refunds, they appear here for triage."
                    : "No cases match this status filter."
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
