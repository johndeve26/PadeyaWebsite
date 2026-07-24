"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  DataTable,
  FilterBar,
  PageToolbar,
  Select,
  SkeletonLoader,
  StatCard,
  StatusBadge,
} from "@/components/ui";
import { fetchAdminPayments } from "@/lib/commerce-api";
import { fetchSettlement } from "@/lib/finance-api";
import { formatDate, formatDateTime, formatNgn } from "@/lib/format";
import type { Payment } from "@/lib/types/commerce";
import type { SettlementReport } from "@/lib/types/finance";

const STATUS_OPTIONS = [
  { value: "all", label: "All statuses" },
  { value: "successful", label: "Successful" },
  { value: "pending", label: "Pending" },
  { value: "failed", label: "Failed" },
];

export default function AdminPaymentsPage() {
  const [payments, setPayments] = useState<Payment[] | null>(null);
  const [report, setReport] = useState<SettlementReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [items, settlement] = await Promise.all([
          fetchAdminPayments(),
          fetchSettlement().catch(() => null),
        ]);
        if (active) {
          setPayments(items);
          setReport(settlement);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load payments");
          setPayments([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const filtered = useMemo(
    () =>
      !payments
        ? []
        : statusFilter === "all"
          ? payments
          : payments.filter((p) => p.status === statusFilter),
    [payments, statusFilter],
  );

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Payments"
      description="Provider payment references and settlement snapshot."
    >
      <PageToolbar>
        <Link href="/admin/payouts">
          <Button size="sm" variant="secondary">
            Payouts
          </Button>
        </Link>
        <Link href="/admin/ledger">
          <Button size="sm" variant="ghost">
            Ledger
          </Button>
        </Link>
        <Link href="/admin/refunds">
          <Button size="sm" variant="ghost">
            Refunds
          </Button>
        </Link>
      </PageToolbar>

      {error ? (
        <Alert tone="danger" title="Could not load payments">
          {error}
        </Alert>
      ) : null}

      {payments ? (
        <>
          {report ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard title="Available balance" value={formatNgn(report.available_balance)} />
              <StatCard
                title="Pending payouts"
                value={formatNgn(report.pending_payout_balance)}
              />
              <StatCard title="Open refunds" value={report.open_refund_requests} />
              <StatCard title="Open payouts" value={report.open_payout_requests} />
            </div>
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

          <DataTable
            rows={filtered}
            rowKey={(payment) => payment.id}
            emptyTitle="No payments found"
            emptyDescription={
              statusFilter === "all"
                ? "Provider payment records appear here after checkout."
                : "No payments match this status filter."
            }
            columns={[
              {
                key: "reference",
                header: "Reference",
                primary: true,
                cell: (payment) => (
                  <span className="font-mono font-bold">{payment.reference}</span>
                ),
              },
              {
                key: "provider",
                header: "Provider",
                cell: (payment) => payment.provider,
              },
              {
                key: "amount",
                header: "Amount",
                cell: (payment) => (
                  <span className="font-bold tabular-nums">
                    {formatNgn(payment.amount)}
                  </span>
                ),
              },
              {
                key: "paid_at",
                header: "Paid",
                cell: (payment) =>
                  payment.paid_at ? formatDateTime(payment.paid_at) : "—",
              },
              {
                key: "created",
                header: "Created",
                cell: (payment) => formatDate(payment.created_at),
              },
              {
                key: "status",
                header: "Status",
                cell: (payment) => <StatusBadge status={payment.status} />,
              },
            ]}
          />
        </>
      ) : null}

      {payments == null && !error ? <SkeletonLoader lines={5} /> : null}
    </DashboardShell>
  );
}
