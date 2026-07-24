"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  ConfirmAction,
  EmptyState,
  FilterBar,
  Input,
  PageToolbar,
  PayoutCard,
  SectionHeader,
  Select,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import { userHasRole } from "@/lib/auth/permissions";
import {
  fetchAdminPayouts,
  fetchSettlement,
  markPayoutPaid,
  reviewPayout,
} from "@/lib/finance-api";
import type { PayoutRequest, SettlementReport } from "@/lib/types/finance";

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "requested", label: "Requested" },
  { value: "under_review", label: "Under review" },
  { value: "approved", label: "Approved" },
  { value: "paid", label: "Paid" },
  { value: "rejected", label: "Rejected" },
];

export default function AdminPayoutsPage() {
  const { user } = useAuth();
  const isSuper = userHasRole(user, "super_admin");
  const [rows, setRows] = useState<PayoutRequest[] | null>(null);
  const [report, setReport] = useState<SettlementReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [transferRef, setTransferRef] = useState("");
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [adminNote, setAdminNote] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load() {
    const [payouts, settlement] = await Promise.all([
      fetchAdminPayouts(),
      fetchSettlement(),
    ]);
    setRows(payouts);
    setReport(settlement);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load payouts");
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const filtered = useMemo(
    () =>
      !rows
        ? []
        : statusFilter === "all"
          ? rows
          : rows.filter((p) => p.status === statusFilter),
    [rows, statusFilter],
  );

  const selectedPayout = useMemo(
    () => (rows ?? []).find((p) => p.id === selectedId) ?? null,
    [rows, selectedId],
  );

  async function onReview(
    id: string,
    action: "approve" | "reject" | "under_review",
  ) {
    setError(null);
    setSuccess(null);
    setBusyId(id);
    try {
      await reviewPayout(id, action);
      setSuccess(
        action === "approve"
          ? "Payout approved."
          : action === "reject"
            ? "Payout rejected."
            : "Marked under review.",
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Review failed");
    } finally {
      setBusyId(null);
    }
  }

  async function onMarkPaid() {
    if (!selectedId) return;
    setError(null);
    setSuccess(null);
    setBusyId(selectedId);
    try {
      await markPayoutPaid(selectedId, {
        bank_transfer_reference: transferRef,
        evidence_file_url: evidenceUrl,
        admin_note: adminNote || undefined,
      });
      setTransferRef("");
      setEvidenceUrl("");
      setAdminNote("");
      setSelectedId(null);
      setSuccess("Payout marked paid with evidence on file.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Mark paid failed");
    } finally {
      setBusyId(null);
    }
  }

  function resetMarkPaidForm() {
    setSelectedId(null);
    setTransferRef("");
    setEvidenceUrl("");
    setAdminNote("");
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Payouts"
      description="Finance can approve/reject. Only super admin can mark paid — evidence required, no automatic completion."
    >
      <PageToolbar>
        <Link href="/admin/ledger">
          <Button size="sm" variant="secondary">
            Ledger
          </Button>
        </Link>
        <Link href="/admin/payments">
          <Button size="sm" variant="ghost">
            Payments
          </Button>
        </Link>
        <Link href="/admin/refunds">
          <Button size="sm" variant="ghost">
            Refunds
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
          {report ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard title="Platform available" value={formatNgn(report.available_balance)} />
              <StatCard title="Pending payouts" value={formatNgn(report.pending_payout_balance)} />
              <StatCard title="Open requests" value={report.open_payout_requests} />
              <StatCard title="Paid out" value={formatNgn(report.total_paid_out)} />
            </div>
          ) : null}

          {isSuper && selectedId && selectedPayout ? (
            <Card className="max-w-xl space-y-4 border-accent/30">
              <SectionHeader
                eyebrow="Super admin"
                title="Mark payout paid"
                description={`Record bank transfer evidence for ${selectedPayout.host_display_name || selectedPayout.host_id} · ${formatNgn(selectedPayout.amount)}. Immutable once saved.`}
              />
          <Input
            label="Bank transfer reference"
            value={transferRef}
            onChange={(e) => setTransferRef(e.target.value)}
            required
          />
          <Input
            label="Evidence file URL"
            hint="Link to receipt or transfer screenshot"
            value={evidenceUrl}
            onChange={(e) => setEvidenceUrl(e.target.value)}
            required
          />
          <Input
            label="Admin note"
            hint="Optional internal note"
            value={adminNote}
            onChange={(e) => setAdminNote(e.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <ConfirmAction
              label="Confirm paid"
              title="Confirm payout as paid?"
              description="This records immutable transfer evidence. Verify the bank reference and file URL before confirming."
              confirmLabel="Mark paid"
              tone="danger"
              size="md"
              disabled={!transferRef.trim() || !evidenceUrl.trim()}
              busy={busyId === selectedId}
              onConfirm={() => onMarkPaid()}
            />
            <Button size="sm" variant="ghost" onClick={resetMarkPaidForm}>
              Cancel
            </Button>
          </div>
        </Card>
      ) : null}

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
        {filtered.map((p) => (
          <PayoutCard
            key={p.id}
            payout={p}
            showHost
            actions={
              <>
                {p.status === "requested" || p.status === "under_review" ? (
                  <>
                    <ConfirmAction
                      label="Under review"
                      title="Mark under review?"
                      description="Moves this payout into active finance review without approving funds."
                      confirmLabel="Mark under review"
                      busy={busyId === p.id}
                      onConfirm={() => onReview(p.id, "under_review")}
                    />
                    <ConfirmAction
                      label="Approve"
                      title="Approve payout?"
                      description={`Approve ${formatNgn(p.amount)} for transfer. Super admin must still mark paid with evidence.`}
                      confirmLabel="Approve payout"
                      tone="danger"
                      busy={busyId === p.id}
                      onConfirm={() => onReview(p.id, "approve")}
                    />
                    <ConfirmAction
                      label="Reject"
                      title="Reject payout?"
                      description="The host will not receive this payout. This is recorded in the audit trail."
                      confirmLabel="Reject payout"
                      variant="ghost"
                      busy={busyId === p.id}
                      onConfirm={() => onReview(p.id, "reject")}
                    />
                  </>
                ) : null}
                {isSuper && p.status === "approved" ? (
                  <Button
                    size="sm"
                    variant="dark"
                    onClick={() => setSelectedId(p.id)}
                  >
                    Mark paid…
                  </Button>
                ) : null}
                {p.evidence ? (
                  <a
                    className="inline-flex items-center text-sm font-semibold text-foreground underline"
                    href={p.evidence.evidence_file_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    View evidence
                  </a>
                ) : null}
              </>
            }
          />
        ))}
        {filtered.length === 0 && !error ? (
          <EmptyState
            title="No payout requests"
            description={
              statusFilter === "all"
                ? "Host payout requests awaiting finance review appear here."
                : "No payouts match this status filter."
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
