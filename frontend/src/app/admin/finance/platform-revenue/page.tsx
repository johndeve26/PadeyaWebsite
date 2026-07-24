"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AdminFinanceSubnav } from "@/components/admin/AdminFinanceSubnav";
import { useAuth } from "@/components/auth/AuthProvider";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  DataTable,
  EmptyState,
  Input,
  PageToolbar,
  Select,
  SkeletonLoader,
  StatCard,
  type DataTableColumn,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission, userHasRole } from "@/lib/auth/permissions";
import {
  exportPlatformRevenueCsv,
  fetchPlatformRevenue,
} from "@/lib/finance-api";
import { formatDateTime, formatNgn } from "@/lib/format";
import type {
  PlatformLedgerEntryRow,
  PlatformRevenueReport,
} from "@/lib/types/finance";

export default function AdminPlatformRevenuePage() {
  const { user } = useAuth();
  const canView =
    userHasRole(user, "finance_admin", "super_admin") ||
    userHasPermission(
      user,
      "admin.finance.view_fees",
      "admin.finance.export_event_sales",
      "payouts.review",
      "admin.full_access",
    );
  const [report, setReport] = useState<PlatformRevenueReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hostId, setHostId] = useState("");
  const [eventId, setEventId] = useState("");
  const [revenueType, setRevenueType] = useState("all");
  const [exporting, setExporting] = useState(false);

  async function load() {
    setError(null);
    try {
      const data = await fetchPlatformRevenue({
        hostId: hostId.trim() || undefined,
        eventId: eventId.trim() || undefined,
        revenueType: revenueType === "all" ? undefined : revenueType,
      });
      setReport(data);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Failed to load platform revenue",
      );
    }
  }

  useEffect(() => {
    if (!canView) return;
    let active = true;
    const handle = window.setTimeout(() => {
      void (async () => {
        try {
          const data = await fetchPlatformRevenue({
            hostId: hostId.trim() || undefined,
            eventId: eventId.trim() || undefined,
            revenueType: revenueType === "all" ? undefined : revenueType,
          });
          if (active) {
            setReport(data);
            setError(null);
          }
        } catch (err) {
          if (active) {
            setError(
              err instanceof ApiError
                ? err.detail
                : "Failed to load platform revenue",
            );
          }
        }
      })();
    }, 0);
    return () => {
      active = false;
      window.clearTimeout(handle);
    };
    // Initial load when permission is available
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canView]);

  async function onExport() {
    setExporting(true);
    try {
      await exportPlatformRevenueCsv({
        hostId: hostId.trim() || undefined,
        eventId: eventId.trim() || undefined,
        revenueType: revenueType === "all" ? undefined : revenueType,
      });
    } catch {
      setError("Export failed — finance export permission required");
    } finally {
      setExporting(false);
    }
  }

  const columns: DataTableColumn<PlatformLedgerEntryRow>[] = [
    {
      key: "type",
      header: "Type",
      primary: true,
      cell: (row) => (
        <div>
          <p className="font-semibold">{row.entry_type}</p>
          <p className="text-xs text-muted-foreground">{row.description}</p>
        </div>
      ),
    },
    {
      key: "direction",
      header: "Dir",
      cell: (row) => row.direction,
    },
    {
      key: "amount",
      header: "Amount",
      cell: (row) => (
        <span className="tabular-nums">{formatNgn(row.amount)}</span>
      ),
    },
    {
      key: "ref",
      header: "Reference",
      cell: (row) => (
        <span className="text-xs tabular-nums text-muted-foreground">
          {row.payment_reference_masked || row.reference_id || "—"}
        </span>
      ),
    },
    {
      key: "when",
      header: "When",
      cell: (row) => formatDateTime(row.created_at),
    },
  ];

  if (!canView) {
    return (
      <DashboardShell tone="soft" eyebrow="Admin" title="Platform revenue">
        <Alert tone="warning">Finance permission required.</Alert>
      </DashboardShell>
    );
  }

  const s = report?.summary;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Platform revenue"
      description="Pàdéyá ledger totals for payment volume, fees, refunds, and payouts. Entries are append-only."
    >
      <div className="space-y-6">
        <AdminFinanceSubnav />
        <Alert tone="info" title="Platform revenue">
          Buyer platform fee is paid by the buyer. Host commission is deducted
          from host earnings. Fee settings can differ by host. Order fee
          snapshots preserve the fee terms used at the time of sale.
        </Alert>
        <PageToolbar>
          <Link href="/admin/finance/earnings">
            <Button size="sm" variant="ghost">
              Host earnings
            </Button>
          </Link>
          <Link href="/admin/ledger">
            <Button size="sm" variant="ghost">
              Host ledger
            </Button>
          </Link>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => void onExport()}
            disabled={exporting}
          >
            {exporting ? "Exporting…" : "Export CSV"}
          </Button>
        </PageToolbar>

        <Card className="space-y-3 p-5">
          <form
            className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
            onSubmit={(e) => {
              e.preventDefault();
              void load();
            }}
          >
            <Input
              label="Host ID"
              value={hostId}
              onChange={(e) => setHostId(e.target.value)}
              placeholder="Optional UUID"
            />
            <Input
              label="Event ID"
              value={eventId}
              onChange={(e) => setEventId(e.target.value)}
              placeholder="Optional UUID"
            />
            <Select
              label="Revenue type"
              value={revenueType}
              onChange={(e) => setRevenueType(e.target.value)}
            >
              <option value="all">All</option>
              <option value="buyer_fee">Buyer service fees</option>
              <option value="ticket_commission">Ticket commission</option>
              <option value="merch_commission">Merch commission</option>
              <option value="vault_commission">Vault commission</option>
              <option value="payments">Payments</option>
              <option value="refunds">Refunds</option>
              <option value="payouts">Payouts</option>
            </Select>
            <div className="flex items-end">
              <Button type="submit" size="sm">
                Apply filters
              </Button>
            </div>
          </form>
        </Card>

        {error ? <Alert tone="danger">{error}</Alert> : null}
        {!report && !error ? <SkeletonLoader lines={6} /> : null}

        {s ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Gross payment volume"
              value={formatNgn(s.gross_payment_volume)}
            />
            <StatCard
              title="Platform revenue"
              value={formatNgn(s.platform_revenue)}
            />
            <StatCard
              title="Buyer service fees"
              value={formatNgn(s.buyer_service_fee_revenue)}
            />
            <StatCard
              title="Ticket commission"
              value={formatNgn(s.ticket_commission_revenue)}
            />
            <StatCard
              title="Merch commission"
              value={formatNgn(s.merch_commission_revenue)}
            />
            <StatCard
              title="Vault commission"
              value={formatNgn(s.vault_commission_revenue)}
            />
            <StatCard title="Refunds" value={formatNgn(s.refunds)} />
            <StatCard
              title="Host net payable"
              value={formatNgn(s.host_net_payable)}
            />
            <StatCard
              title="Pending payouts"
              value={formatNgn(s.pending_payouts)}
            />
            <StatCard
              title="Payouts completed"
              value={formatNgn(s.payouts_completed)}
            />
          </div>
        ) : null}

        <Alert tone="info" title="Append-only ledger">
          Platform ledger entries are never edited or deleted. Corrections use
          adjustment rows. Payment references are masked; raw payment payloads
          are never exposed here.
        </Alert>

        {report && report.entries.length === 0 ? (
          <EmptyState
            title="No ledger entries"
            description="Verified payments will create platform ledger rows automatically."
          />
        ) : report ? (
          <DataTable
            columns={columns}
            rows={report.entries}
            rowKey={(row) => row.id}
          />
        ) : null}
      </div>
    </DashboardShell>
  );
}
