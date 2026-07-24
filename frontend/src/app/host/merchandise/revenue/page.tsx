"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
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
  exportHostMerchRevenueCsv,
  fetchHostMerchRevenue,
} from "@/lib/merch-api";
import type { MerchHostRevenueReport } from "@/lib/types/merch";

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
  columns: Array<{ key: string; header: string; cell: (row: Record<string, unknown>) => string }>;
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

export default function HostMerchRevenuePage() {
  const [data, setData] = useState<MerchHostRevenueReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const row = await fetchHostMerchRevenue();
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
      await exportHostMerchRevenueCsv();
    } catch {
      setExportError("Could not export CSV");
    } finally {
      setExporting(false);
    }
  }

  const payout = data?.payout_status;
  const refunds = data?.refunds;

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Merch Studio"
        title="Merch revenue"
        description="Paid merch splits on Pàdéyá after verified payment. Snapshots only — no buyer addresses or payment secrets."
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
            <Link href="/host/merchandise">
              <Button size="sm" variant="ghost">
                Back to merch
              </Button>
            </Link>
            <Link href="/host/payouts">
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
                title="Total merch GMV"
                value={money(data.total_merch_gmv ?? data.total_gross)}
                hint="Gross paid merch lines"
              />
              <StatCard
                title="Units sold"
                value={data.units_sold ?? 0}
                hint={`${data.line_count ?? 0} paid lines`}
              />
              <StatCard
                title="Refunds"
                value={money(refunds?.gross ?? data.refunds_gross)}
                hint={`${refunds?.units ?? 0} units reversed`}
              />
              <StatCard
                title="Net revenue"
                value={money(data.net_revenue ?? data.host_amount)}
                hint="Your host share after fees"
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                title="Platform fees"
                value={money(data.platform_amount)}
              />
              <StatCard
                title="Sponsor share"
                value={money(data.sponsor_amount)}
              />
              <StatCard
                title="Bundle revenue"
                value={money(data.bundle_revenue)}
              />
              <StatCard
                title="Discount impact"
                value={money(data.discount_impact)}
                hint="Merch discounts on paid orders"
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <StatCard
                title="Sponsor-branded GMV"
                value={money(data.sponsor_branded_revenue)}
                hint={`${data.sponsor_branded_line_count ?? 0} lines`}
              />
              <StatCard
                title="Pending payout"
                value={money(
                  payout?.pending_payout_amount ?? payout?.payable?.amount,
                )}
                hint={`${payout?.pending_payout_line_count ?? payout?.payable?.line_count ?? 0} payable lines`}
              />
              <StatCard
                title="Paid out (splits)"
                value={money(payout?.paid?.amount)}
                hint={`${payout?.paid?.line_count ?? 0} lines marked paid`}
              />
            </div>

            <BreakdownTable
              title="Top products"
              empty="No paid merch products yet."
              rows={(data.top_products ?? []) as Array<Record<string, unknown>>}
              columns={[
                {
                  key: "name",
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
                  key: "host",
                  header: "Your share",
                  cell: (r) => money(r.host_amount as string | number),
                },
              ]}
            />

            <BreakdownTable
              title="Revenue by event"
              empty="No event merch revenue yet."
              rows={(data.by_event ?? []) as Array<Record<string, unknown>>}
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
                  header: "Your share",
                  cell: (r) => money(r.host_amount as string | number),
                },
              ]}
            />

            <BreakdownTable
              title="Revenue by variant"
              empty="No variant sales yet."
              rows={(data.by_variant ?? []) as Array<Record<string, unknown>>}
              columns={[
                {
                  key: "variant",
                  header: "Variant",
                  cell: (r) =>
                    String(
                      r.variant_label ??
                        r.product_name ??
                        "Variant",
                    ),
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
              ]}
            />

            <BreakdownTable
              title="By fulfillment method"
              empty="No fulfillment breakdown yet."
              rows={
                (data.by_fulfillment_method ?? []) as Array<
                  Record<string, unknown>
                >
              }
              columns={[
                {
                  key: "method",
                  header: "Method",
                  cell: (r) =>
                    String(r.fulfillment_method ?? "unknown"),
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
              ]}
            />

            {(data.by_bundle ?? []).length > 0 ? (
              <BreakdownTable
                title="Bundle revenue"
                empty="No bundle sales."
                rows={(data.by_bundle ?? []) as Array<Record<string, unknown>>}
                columns={[
                  {
                    key: "bundle",
                    header: "Bundle",
                    cell: (r) => String(r.bundle_name ?? "Bundle"),
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
                ]}
              />
            ) : null}

            {(data.sponsor_branded_lines ?? []).length > 0 ? (
              <BreakdownTable
                title="Sponsor-branded lines"
                empty="None"
                rows={
                  (data.sponsor_branded_lines ?? []) as Array<
                    Record<string, unknown>
                  >
                }
                columns={[
                  {
                    key: "product",
                    header: "Product",
                    cell: (r) => String(r.product_name ?? "Product"),
                  },
                  {
                    key: "sponsor",
                    header: "Sponsor",
                    cell: (r) => String(r.sponsor_brand_name ?? "—"),
                  },
                  {
                    key: "gross",
                    header: "GMV",
                    cell: (r) => money(r.gross as string | number),
                  },
                  {
                    key: "sponsor_amt",
                    header: "Sponsor share",
                    cell: (r) => money(r.sponsor_amount as string | number),
                  },
                ]}
              />
            ) : null}

            {(data.line_count ?? 0) === 0 &&
            (refunds?.line_count ?? 0) === 0 ? (
              <EmptyState
                title="No merch revenue yet"
                description="Splits appear here after a verified payment for merch lines."
              />
            ) : null}
          </div>
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
