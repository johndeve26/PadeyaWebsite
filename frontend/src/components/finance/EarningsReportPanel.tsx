"use client";

import Link from "next/link";

import {
  Alert,
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  SectionHeader,
  StatCard,
  StatusBadge,
  type DataTableColumn,
} from "@/components/ui";
import { formatDateTime, formatNgn } from "@/lib/format";
import { FEE_HELP_COPY } from "@/lib/types/fees";
import type {
  EarningsOrderRow,
  HostEarningsReport,
  HostFeeTerm,
} from "@/lib/types/finance";

function feeTermRate(term: HostFeeTerm): string {
  const parts: string[] = [];
  if (term.percentage_value != null && Number(term.percentage_value) !== 0) {
    parts.push(`${Number(term.percentage_value)}%`);
  }
  if (term.fixed_value_major != null && Number(term.fixed_value_major) !== 0) {
    parts.push(formatNgn(term.fixed_value_major));
  }
  if (parts.length === 0) {
    if (term.fee_type === "percentage") return "0%";
    return "—";
  }
  return parts.join(" + ");
}

function payerLabel(payer: string): string {
  if (payer === "buyer") return "Buyer-paid";
  if (payer === "host") return "Host-paid";
  return "Platform";
}

export function EarningsReportPanel({
  report,
  showHostNote = true,
  showHostLinks = true,
  exportLabel = "Export CSV",
  onExport,
  exporting = false,
}: {
  report: HostEarningsReport;
  showHostNote?: boolean;
  showHostLinks?: boolean;
  exportLabel?: string;
  onExport?: () => void;
  exporting?: boolean;
}) {
  const s = report.summary;
  const columns: DataTableColumn<EarningsOrderRow>[] = [
    {
      key: "reference",
      header: "Order ref",
      primary: true,
      cell: (row) => (
        <div>
          <p className="font-semibold text-foreground">{row.reference}</p>
          <p className="text-xs text-muted-foreground">{row.item_label}</p>
        </div>
      ),
    },
    {
      key: "event",
      header: "Event / item",
      cell: (row) => (
        <span className="text-sm">
          {row.event_title || (row.row_kind === "vault" ? "Vault" : "—")}
        </span>
      ),
    },
    {
      key: "gross",
      header: "Gross",
      cell: (row) => (
        <span className="tabular-nums">{formatNgn(row.host_gross)}</span>
      ),
    },
    {
      key: "fees",
      header: "Fees deducted",
      cell: (row) => (
        <span className="tabular-nums">
          {formatNgn(Number(row.host_fee_total) + Number(row.ambassador_reward ?? 0))}
        </span>
      ),
    },
    {
      key: "refunds",
      header: "Refunds",
      cell: (row) => (
        <span className="tabular-nums">{formatNgn(row.refund_amount)}</span>
      ),
    },
    {
      key: "net",
      header: "Net",
      cell: (row) => (
        <span className="font-semibold tabular-nums">
          {formatNgn(row.host_net)}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      cell: (row) => (
        <div className="space-y-1">
          <StatusBadge status={row.payment_status} />
          <p className="text-xs text-muted-foreground">{row.payout_status}</p>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {showHostNote ? (
        <Alert tone="info" title="How host earnings work">
          <div className="space-y-2">
            {report.note ? <p>{report.note}</p> : null}
            <ul className="list-disc space-y-1 pl-4">
              {FEE_HELP_COPY.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </div>
        </Alert>
      ) : (
        <Alert tone="info" title="How fees affect earnings">
          <ul className="list-disc space-y-1 pl-4">
            {FEE_HELP_COPY.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </Alert>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard title="Gross sales" value={formatNgn(s.host_gross)} />
        <StatCard
          title="Deductions"
          value={formatNgn(s.deductions_total)}
          hint="Commission, host-paid fees, ambassadors, refunds"
        />
        <StatCard title="Net earnings" value={formatNgn(s.net_earnings)} />
        <StatCard title="Pending payout" value={formatNgn(s.pending_payout)} />
        <StatCard title="Paid out" value={formatNgn(s.paid_out)} />
      </div>

      <Card className="space-y-3 p-5">
        <SectionHeader
          title="Sales breakdown"
          description="Gross is item value after discounts. Buyer-paid Pàdéyá fees are excluded from host gross."
        />
        <div className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <div className="flex justify-between gap-3 border-b border-border/60 py-2">
            <span className="text-muted-foreground">Ticket sales</span>
            <span className="tabular-nums">{formatNgn(s.gross_ticket_sales)}</span>
          </div>
          <div className="flex justify-between gap-3 border-b border-border/60 py-2">
            <span className="text-muted-foreground">Merch sales</span>
            <span className="tabular-nums">{formatNgn(s.gross_merch_sales)}</span>
          </div>
          <div className="flex justify-between gap-3 border-b border-border/60 py-2">
            <span className="text-muted-foreground">Vault sales</span>
            <span className="tabular-nums">{formatNgn(s.gross_vault_sales)}</span>
          </div>
          <div className="flex justify-between gap-3 border-b border-border/60 py-2">
            <span className="text-muted-foreground">Discounts</span>
            <span className="tabular-nums text-success">
              −{formatNgn(s.discounts_total)}
            </span>
          </div>
          <div className="flex justify-between gap-3 border-b border-border/60 py-2">
            <span className="text-muted-foreground">Pàdéyá commission</span>
            <span className="tabular-nums">
              −{formatNgn(s.padeya_commission)}
            </span>
          </div>
          {Number(s.processing_fees_host_paid) > 0 ? (
            <div className="flex justify-between gap-3 border-b border-border/60 py-2">
              <span className="text-muted-foreground">
                Processing (host-paid)
              </span>
              <span className="tabular-nums">
                −{formatNgn(s.processing_fees_host_paid)}
              </span>
            </div>
          ) : null}
          {Number(s.ambassador_rewards) > 0 ? (
            <div className="flex justify-between gap-3 border-b border-border/60 py-2">
              <span className="text-muted-foreground">Ambassador rewards</span>
              <span className="tabular-nums">
                −{formatNgn(s.ambassador_rewards)}
              </span>
            </div>
          ) : null}
          <div className="flex justify-between gap-3 border-b border-border/60 py-2">
            <span className="text-muted-foreground">Refunds</span>
            <span className="tabular-nums">−{formatNgn(s.refunds_total)}</span>
          </div>
          <div className="flex justify-between gap-3 border-b border-border/60 py-2">
            <span className="text-muted-foreground">
              Buyer service fees (Pàdéyá)
            </span>
            <span className="tabular-nums">
              {formatNgn(s.buyer_platform_fees)}
            </span>
          </div>
          <div className="flex justify-between gap-3 py-2 font-semibold">
            <span>Net earnings</span>
            <span className="tabular-nums">{formatNgn(s.net_earnings)}</span>
          </div>
        </div>
      </Card>

      {report.fee_terms.length > 0 ? (
        <Card className="space-y-3 p-5">
          <SectionHeader
            title="Your fee terms"
            description="Rates that apply to this host. Other hosts’ commercial terms are never shown."
          />
          <ul className="space-y-2">
            {report.fee_terms.map((term) => (
              <li
                key={term.fee_key}
                className="flex flex-wrap items-center justify-between gap-2 border-b border-border/50 py-2 text-sm last:border-0"
              >
                <div>
                  <p className="font-medium text-foreground">{term.label}</p>
                  <p className="text-xs text-muted-foreground">
                    {term.category} · {term.source === "host_override" ? "Custom override" : "Platform default"}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone="neutral">{payerLabel(term.payer)}</Badge>
                  <span className="tabular-nums font-semibold">
                    {feeTermRate(term)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <SectionHeader
            title="Order breakdown"
            description={`${s.paid_order_count} paid orders${s.vault_sale_count ? ` · ${s.vault_sale_count} Vault unlocks` : ""}`}
          />
          {onExport ? (
            <Button
              size="sm"
              variant="secondary"
              onClick={onExport}
              disabled={exporting}
            >
              {exporting ? "Exporting…" : exportLabel}
            </Button>
          ) : null}
        </div>
        {report.rows.length === 0 ? (
          <EmptyState
            title="No paid sales yet"
            description="Paid ticket, merch, and Vault sales will appear here with gross and net after deductions."
          />
        ) : (
          <DataTable
            columns={columns}
            rows={report.rows}
            rowKey={(row) => `${row.row_kind}-${row.reference}`}
            emptyTitle="No rows"
          />
        )}
      </div>

      {report.rows.some((r) => Number(r.buyer_fee_total) > 0) ? (
        <p className="text-xs text-muted-foreground">
          Buyer-paid totals include service fees kept by Pàdéyá. Those fees are
          listed under platform revenue and do not increase host gross.
          {report.rows[0]?.paid_at
            ? ` Latest sale ${formatDateTime(report.rows[0].paid_at)}.`
            : null}
        </p>
      ) : null}

      {showHostLinks ? (
        <div className="flex flex-wrap gap-2 text-sm">
          <Link
            href="/host/payouts"
            className="text-heading underline-offset-2 hover:underline"
          >
            Request payout
          </Link>
          <span className="text-muted-foreground">·</span>
          <Link
            href="/host/analytics"
            className="text-heading underline-offset-2 hover:underline"
          >
            Analytics
          </Link>
        </div>
      ) : null}
    </div>
  );
}
