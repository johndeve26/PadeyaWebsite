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
import { ApiError } from "@/lib/api";
import { fetchAdminLedger, fetchSettlement } from "@/lib/finance-api";
import { formatDateTime, formatNgn } from "@/lib/format";
import type { LedgerEntry, SettlementReport } from "@/lib/types/finance";

export default function AdminLedgerPage() {
  const [rows, setRows] = useState<LedgerEntry[] | null>(null);
  const [report, setReport] = useState<SettlementReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [entryTypeFilter, setEntryTypeFilter] = useState("all");
  const [directionFilter, setDirectionFilter] = useState("all");

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [ledger, settlement] = await Promise.all([
          fetchAdminLedger(),
          fetchSettlement(),
        ]);
        if (active) {
          setRows(ledger);
          setReport(settlement);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load ledger");
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const entryTypes = useMemo(
    () => [...new Set((rows ?? []).map((e) => e.entry_type))].sort(),
    [rows],
  );

  const filtered = useMemo(
    () =>
      (rows ?? []).filter((e) => {
        if (entryTypeFilter !== "all" && e.entry_type !== entryTypeFilter) {
          return false;
        }
        if (directionFilter !== "all" && e.direction !== directionFilter) {
          return false;
        }
        return true;
      }),
    [rows, entryTypeFilter, directionFilter],
  );

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Ledger"
      description="Append-only host balance journal. Entries are immutable after creation — every credit and debit is preserved for audit."
    >
      <PageToolbar>
        <Link href="/admin/payouts">
          <Button size="sm" variant="secondary">
            Payouts
          </Button>
        </Link>
        <Link href="/admin/payments">
          <Button size="sm" variant="ghost">
            Payments
          </Button>
        </Link>
      </PageToolbar>

      {error ? (
        <Alert tone="danger" title="Could not load ledger">
          {error}
        </Alert>
      ) : null}

      <Alert tone="info" title="Audit trail">
        This ledger is append-only. Corrections appear as new entries — existing
        rows are never edited or deleted.
      </Alert>

      {rows ? (
        <>
          {report ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard title="Total earned" value={formatNgn(report.total_earned)} />
              <StatCard title="Total refunded" value={formatNgn(report.total_refunded)} />
              <StatCard title="Paid out" value={formatNgn(report.total_paid_out)} />
              <StatCard title="Ledger entries" value={report.ledger_entry_count} />
            </div>
          ) : null}

          <FilterBar>
            <Select
              label="Entry type"
              value={entryTypeFilter}
              onChange={(e) => setEntryTypeFilter(e.target.value)}
            >
              <option value="all">All types</option>
              {entryTypes.map((type) => (
                <option key={type} value={type}>
                  {type.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
            <Select
              label="Direction"
              value={directionFilter}
              onChange={(e) => setDirectionFilter(e.target.value)}
            >
              <option value="all">All directions</option>
              <option value="credit">Credit</option>
              <option value="debit">Debit</option>
            </Select>
          </FilterBar>

          <DataTable
            rows={filtered}
            rowKey={(e) => e.id}
            emptyTitle="No ledger entries"
            emptyDescription={
              entryTypeFilter !== "all" || directionFilter !== "all"
                ? "No entries match the current filters."
                : "Host balance movements will appear here as they occur."
            }
            columns={[
              {
                key: "type",
                header: "Type",
                primary: true,
                cell: (e) => (
                  <span className="font-semibold capitalize">
                    {e.entry_type.replace(/_/g, " ")}
                  </span>
                ),
              },
              {
                key: "direction",
                header: "Direction",
                cell: (e) => <StatusBadge status={e.direction} />,
              },
              {
                key: "amount",
                header: "Amount",
                cell: (e) => (
                  <span className="font-bold tabular-nums">{formatNgn(e.amount)}</span>
                ),
              },
              {
                key: "description",
                header: "Description",
                cell: (e) => (
                  <span className="text-muted-foreground">
                    {e.description || `${e.reference_type ?? "ref"} ${e.reference_id ?? ""}`}
                  </span>
                ),
              },
              {
                key: "balance",
                header: "Avail. after",
                cell: (e) => (
                  <span className="tabular-nums text-muted-foreground">
                    {formatNgn(e.available_balance_after)}
                  </span>
                ),
              },
              {
                key: "date",
                header: "Date",
                cell: (e) => formatDateTime(e.created_at),
              },
            ]}
          />
        </>
      ) : null}

      {rows == null && !error ? <SkeletonLoader lines={5} /> : null}
    </DashboardShell>
  );
}
