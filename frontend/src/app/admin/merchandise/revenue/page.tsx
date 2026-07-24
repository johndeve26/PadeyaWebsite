"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  EmptyState,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import {
  exportAdminMerchRevenueCsv,
  fetchAdminMerchRevenue,
} from "@/lib/merch-api";
import type { MerchAdminRevenueReport } from "@/lib/types/merch";

function money(value: string | number | undefined | null) {
  if (value == null || value === "") return "—";
  return formatNgn(value);
}

function BreakdownTable({
  title,
  empty,
  rows,
  columns,
}: {
  title: string;
  empty: string;
  rows: Array<Record<string, unknown>>;
  columns: Array<{
    key: string;
    header: string;
    cell: (row: Record<string, unknown>) => string;
  }>;
}) {
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-extrabold uppercase tracking-wide text-muted-foreground">
        {title}
      </h2>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">{empty}</p>
      ) : (
        <div className="overflow-x-auto border border-border">
          <table className="w-full min-w-[28rem] text-left text-sm">
            <thead className="border-b border-border bg-surface-muted/40">
              <tr>
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className="px-3 py-2 text-xs font-bold uppercase tracking-wide text-muted-foreground"
                  >
                    {col.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {rows.map((row, index) => (
                <tr key={`${title}-${index}`}>
                  {columns.map((col) => (
                    <td key={col.key} className="px-3 py-2 text-foreground">
                      {col.cell(row)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default function AdminMerchRevenuePage() {
  const [data, setData] = useState<MerchAdminRevenueReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const row = await fetchAdminMerchRevenue();
        if (active) setData(row);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Could not load revenue",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onExport() {
    setExportError(null);
    setExporting(true);
    try {
      await exportAdminMerchRevenueCsv();
    } catch {
      setExportError("Could not export CSV");
    } finally {
      setExporting(false);
    }
  }

  const refunds = data?.refunds;
  const pending = data?.pending_payouts;

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin"
      title="Merch revenue"
      description="Platform merch split totals after verified payment. Read-only snapshots — support cannot modify financial records."
      actions={
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="secondary"
            disabled={exporting}
            onClick={() => void onExport()}
          >
            {exporting ? "Exporting…" : "Export CSV"}
          </Button>
          <Link href="/admin/merchandise">
            <Button size="sm" variant="ghost">
              Products
            </Button>
          </Link>
          <Link href="/admin/payouts">
            <Button size="sm" variant="ghost">
              Payouts
            </Button>
          </Link>
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Unavailable">
          {error}
        </Alert>
      ) : null}
      {exportError ? (
        <Alert tone="danger" title="Export failed">
          {exportError}
        </Alert>
      ) : null}
      {!data && !error ? <SkeletonLoader lines={6} /> : null}
      {data ? (
        <div className="space-y-8">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Platform merch GMV"
              value={money(data.platform_merch_gmv ?? data.total_gross)}
              hint={`${data.units_sold ?? 0} units`}
            />
            <StatCard
              title="Platform fees"
              value={money(data.platform_fees ?? data.platform_amount)}
            />
            <StatCard
              title="Host revenue"
              value={money(data.host_revenue ?? data.host_amount)}
            />
            <StatCard
              title="Refunds"
              value={money(refunds?.gross ?? data.refunds_gross)}
              hint={`${refunds?.line_count ?? 0} reversed lines`}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Sponsor split"
              value={money(data.sponsor_split ?? data.sponsor_amount)}
            />
            <StatCard
              title="Print partner split"
              value={money(
                data.print_partner_split ?? data.print_partner_amount,
              )}
            />
            <StatCard
              title="Sponsor-branded GMV"
              value={money(data.sponsor_branded_gross)}
              hint={`${data.sponsor_branded_line_count ?? 0} lines`}
            />
            <StatCard
              title="Pending payouts"
              value={money(pending?.amount)}
              hint={`${pending?.line_count ?? 0} payable lines`}
            />
          </div>

          <BreakdownTable
            title="Top hosts"
            empty="No host merch revenue yet."
            rows={(data.top_hosts ?? []) as Array<Record<string, unknown>>}
            columns={[
              {
                key: "host",
                header: "Host",
                cell: (r) => String(r.host_name ?? "Host"),
              },
              {
                key: "units",
                header: "Units",
                cell: (r) => String(r.units ?? 0),
              },
              {
                key: "gross",
                header: "GMV",
                cell: (r) => money(r.gross as string | number),
              },
              {
                key: "host_amt",
                header: "Host share",
                cell: (r) => money(r.host_amount as string | number),
              },
            ]}
          />

          <BreakdownTable
            title="Top products"
            empty="No product revenue yet."
            rows={(data.top_products ?? []) as Array<Record<string, unknown>>}
            columns={[
              {
                key: "product",
                header: "Product",
                cell: (r) => String(r.product_name ?? "Product"),
              },
              {
                key: "units",
                header: "Units",
                cell: (r) => String(r.units ?? 0),
              },
              {
                key: "gross",
                header: "GMV",
                cell: (r) => money(r.gross as string | number),
              },
              {
                key: "platform",
                header: "Platform",
                cell: (r) => money(r.platform_amount as string | number),
              },
            ]}
          />

          <BreakdownTable
            title="Top events"
            empty="No event merch revenue yet."
            rows={(data.top_events ?? []) as Array<Record<string, unknown>>}
            columns={[
              {
                key: "event",
                header: "Event",
                cell: (r) => String(r.event_title ?? "Event"),
              },
              {
                key: "units",
                header: "Units",
                cell: (r) => String(r.units ?? 0),
              },
              {
                key: "gross",
                header: "GMV",
                cell: (r) => money(r.gross as string | number),
              },
              {
                key: "host",
                header: "Host share",
                cell: (r) => money(r.host_amount as string | number),
              },
            ]}
          />

          {(data.line_count ?? 0) === 0 &&
          (refunds?.line_count ?? 0) === 0 ? (
            <EmptyState
              title="No platform merch revenue"
              description="Splits appear after verified payment webhooks create merch_revenue_splits snapshots."
            />
          ) : null}
        </div>
      ) : null}
    </DashboardShell>
  );
}
