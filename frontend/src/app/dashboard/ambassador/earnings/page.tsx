"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AmbassadorDashNav } from "@/components/ambassadors/AmbassadorDashNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDate, formatNgn } from "@/lib/format";
import {
  fetchAmbassadorEarningsSummary,
  fetchMyAmbassadorEnrollments,
} from "@/lib/promos-api";
import type {
  AmbassadorDashboard,
  AmbassadorEarningsSummary,
  AmbassadorSale,
} from "@/lib/types/promos";

export default function AmbassadorEarningsPage() {
  const [summary, setSummary] = useState<AmbassadorEarningsSummary | null>(null);
  const [sales, setSales] = useState<AmbassadorSale[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [sum, enrollments] = await Promise.all([
          fetchAmbassadorEarningsSummary(),
          fetchMyAmbassadorEnrollments(),
        ]);
        if (!active) return;
        setSummary(sum);
        const allSales = enrollments.enrollments.flatMap(
          (row: AmbassadorDashboard) => row.sales,
        );
        allSales.sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );
        setSales(allSales);
        setLoaded(true);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Could not load earnings",
          );
          setLoaded(true);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Ambassadors"
      title="Ambassador earnings"
      description="Estimated earnings from confirmed paid sales. Approved and payable amounts appear when payout review completes."
      actions={
        <Link href="/dashboard/ambassador/payouts">
          <Button size="sm" variant="secondary">
            Payout status
          </Button>
        </Link>
      }
    >
      <AmbassadorDashNav />

      {error ? (
        <Alert tone="danger" title="Unable to load">
          {error}
        </Alert>
      ) : null}

      {!loaded ? <SkeletonLoader lines={6} /> : null}

      {summary ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard title="Estimated" value={formatNgn(summary.estimated_earnings)} />
          <StatCard title="Approved" value={formatNgn(summary.approved_earnings)} />
          <StatCard title="Payable" value={formatNgn(summary.payable_earnings)} />
          <StatCard title="Paid" value={formatNgn(summary.paid_earnings)} />
        </div>
      ) : null}

      {summary ? (
        <Card className="space-y-2">
          <p className="text-sm text-body">{summary.payout_status_label}</p>
          <p className="text-sm text-muted-foreground">
            Confirmed sales: {summary.confirmed_sales} · Tickets:{" "}
            {summary.tickets_sold} · Merch: {summary.merch_units_sold} · Revenue:{" "}
            {formatNgn(summary.revenue_generated)}
          </p>
        </Card>
      ) : null}

      {loaded ? (
        <Card className="space-y-3">
          <h2 className="font-bold">Confirmed sales</h2>
          {sales.length === 0 ? (
            <EmptyState
              title="No confirmed sales yet"
              description="Share your Ambassador link — ticket and merch sales appear here after verified payment."
              action={
                <Link href="/dashboard/ambassador/links">
                  <Button size="sm" variant="secondary">
                    Copy links
                  </Button>
                </Link>
              }
            />
          ) : (
            sales.map((sale) => (
              <div
                key={sale.id}
                className="flex flex-wrap justify-between gap-2 border-b border-border py-2 text-sm"
              >
                <div>
                  <p className="font-semibold">{sale.event_title ?? "Event"}</p>
                  <p className="text-muted-foreground">
                    {sale.tickets_sold} tickets
                    {(sale.merch_units_sold ?? 0) > 0
                      ? ` · ${sale.merch_units_sold} merch`
                      : ""}{" "}
                    · {formatNgn(sale.revenue_amount)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-semibold">{formatNgn(sale.commission_owed)}</p>
                  <p className="text-muted-foreground">
                    {sale.status} · {formatDate(sale.created_at)}
                  </p>
                </div>
              </div>
            ))
          )}
        </Card>
      ) : null}
    </DashboardShell>
  );
}
