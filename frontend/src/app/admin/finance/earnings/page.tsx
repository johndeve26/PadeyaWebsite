"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AdminFinanceSubnav } from "@/components/admin/AdminFinanceSubnav";
import { EarningsReportPanel } from "@/components/finance/EarningsReportPanel";
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
  SkeletonLoader,
  StatCard,
  type DataTableColumn,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { userHasPermission } from "@/lib/auth/permissions";
import { formatNgn } from "@/lib/format";
import {
  exportAdminEarningsCsv,
  fetchAdminEarnings,
  fetchAdminEarningsHosts,
  fetchSettlement,
} from "@/lib/finance-api";
import type {
  AdminHostEarningsOverviewRow,
  HostEarningsReport,
  SettlementReport,
} from "@/lib/types/finance";

export default function AdminFinanceEarningsPage() {
  const { user } = useAuth();
  const canView = userHasPermission(
    user,
    "payments.view",
    "payouts.review",
    "admin.finance.view_fees",
    "admin.full_access",
  );
  const [settlement, setSettlement] = useState<SettlementReport | null>(null);
  const [hosts, setHosts] = useState<AdminHostEarningsOverviewRow[]>([]);
  const [report, setReport] = useState<HostEarningsReport | null>(null);
  const [hostIdInput, setHostIdInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!canView) return;
    let active = true;
    void (async () => {
      try {
        const [settle, hostRows] = await Promise.all([
          fetchSettlement(),
          fetchAdminEarningsHosts(),
        ]);
        if (active) {
          setSettlement(settle);
          setHosts(hostRows);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load earnings",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [canView]);

  async function loadHost(hostId: string) {
    setError(null);
    try {
      const data = await fetchAdminEarnings({ hostId });
      setReport(data);
      setHostIdInput(hostId);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Failed to load host earnings",
      );
    }
  }

  async function onExport() {
    if (!report) return;
    setExporting(true);
    try {
      await exportAdminEarningsCsv({ hostId: report.summary.host_id });
    } catch {
      setError("CSV export failed");
    } finally {
      setExporting(false);
    }
  }

  const hostColumns: DataTableColumn<AdminHostEarningsOverviewRow>[] = [
    {
      key: "host",
      header: "Host",
      primary: true,
      cell: (row) => (
        <Link
          href={`/admin/hosts/${row.host_id}/earnings`}
          className="font-semibold text-heading underline-offset-2 hover:underline"
        >
          {row.host_display_name}
        </Link>
      ),
    },
    {
      key: "net",
      header: "Lifetime earned",
      cell: (row) => (
        <span className="tabular-nums">{formatNgn(row.net_earnings)}</span>
      ),
    },
    {
      key: "pending",
      header: "Pending payout",
      cell: (row) => (
        <span className="tabular-nums">{formatNgn(row.pending_payout)}</span>
      ),
    },
    {
      key: "paid",
      header: "Paid out",
      cell: (row) => (
        <span className="tabular-nums">{formatNgn(row.paid_out)}</span>
      ),
    },
    {
      key: "actions",
      header: "",
      cell: (row) => (
        <Button size="sm" variant="ghost" onClick={() => void loadHost(row.host_id)}>
          View breakdown
        </Button>
      ),
    },
  ];

  if (!canView) {
    return (
      <DashboardShell tone="soft" eyebrow="Admin" title="Earnings">
        <Alert tone="warning">Finance view permission required.</Alert>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Earnings"
      description="Platform settlement plus per-host net revenue after Pàdéyá deductions."
    >
      <div className="space-y-6">
        <AdminFinanceSubnav />
        <PageToolbar>
          <Link href="/admin/finance/fees">
            <Button size="sm" variant="ghost">
              Fees
            </Button>
          </Link>
          <Link href="/admin/ledger">
            <Button size="sm" variant="ghost">
              Ledger
            </Button>
          </Link>
          <Link href="/admin/payouts">
            <Button size="sm" variant="ghost">
              Payouts
            </Button>
          </Link>
        </PageToolbar>
        {error ? <Alert tone="danger">{error}</Alert> : null}
        <Alert tone="info" title="How fees affect host earnings">
          Buyer platform fee is paid by the buyer. Host commission is deducted
          from host earnings. Fee settings can differ by host. Order fee
          snapshots preserve the fee terms used at the time of sale.
        </Alert>
        {settlement == null && !error ? (
          <SkeletonLoader lines={4} />
        ) : settlement ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Available balance"
              value={formatNgn(settlement.available_balance)}
            />
            <StatCard
              title="Pending payouts"
              value={formatNgn(settlement.pending_payout_balance)}
            />
            <StatCard
              title="Lifetime earned"
              value={formatNgn(settlement.total_earned)}
            />
            <StatCard
              title="Lifetime paid out"
              value={formatNgn(settlement.total_paid_out)}
            />
          </div>
        ) : null}

        <Card className="space-y-3 p-5">
          <p className="text-sm text-muted-foreground">
            Open a host to see gross sales, Pàdéyá commission, buyer-paid fees
            (platform only), refunds, and net earnings.
          </p>
          <form
            className="flex flex-wrap items-end gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (hostIdInput.trim()) void loadHost(hostIdInput.trim());
            }}
          >
            <div className="min-w-[240px] flex-1">
              <Input
                label="Host ID"
                value={hostIdInput}
                onChange={(e) => setHostIdInput(e.target.value)}
                placeholder="UUID"
              />
            </div>
            <Button type="submit" size="sm">
              Load host
            </Button>
          </form>
        </Card>

        {hosts.length === 0 ? (
          <EmptyState
            title="No host balances yet"
            description="Hosts with ledger activity will appear here."
          />
        ) : (
          <DataTable
            columns={hostColumns}
            rows={hosts}
            rowKey={(row) => row.host_id}
          />
        )}

        {report ? (
          <div className="space-y-3 border-t border-border pt-6">
            <h2 className="text-lg font-extrabold text-foreground">
              {report.summary.host_display_name || "Host"} breakdown
            </h2>
            <EarningsReportPanel
              report={report}
              showHostNote
              showHostLinks={false}
              onExport={() => void onExport()}
              exporting={exporting}
            />
          </div>
        ) : null}
      </div>
    </DashboardShell>
  );
}
