"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AdminAnalyticsSubnav } from "@/components/analytics/AdminAnalyticsSubnav";
import { TrendPanel } from "@/components/analytics/TrendPanel";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  DataTable,
  SectionHeader,
  Select,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchAdminEventLeaderboard,
  fetchAdminRevenue,
} from "@/lib/analytics-api";
import {
  rangeToQuery,
  type AnalyticsRangeKey,
} from "@/lib/analytics-range";
import { formatNgn } from "@/lib/format";
import type {
  AdminEventLeaderboardRow,
  AdminRevenueSummary,
} from "@/lib/types/analytics";

export default function AdminRevenueAnalyticsPage() {
  const [data, setData] = useState<AdminRevenueSummary | null>(null);
  const [events, setEvents] = useState<AdminEventLeaderboardRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [rangeKey, setRangeKey] = useState<AnalyticsRangeKey>("90d");

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const query = rangeToQuery(rangeKey);
        const [revenue, board] = await Promise.all([
          fetchAdminRevenue(),
          fetchAdminEventLeaderboard({
            ...query,
            sort_by: "revenue",
            limit: 20,
          }),
        ]);
        if (!active) return;
        setData(revenue);
        setEvents(board.events);
        setError(null);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [rangeKey]);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin analytics"
      title="Revenue"
      description="Gross GMV, fees, refunds, payouts — with event-level drilldown."
      actions={
        <>
          <Link href="/admin/analytics/events">
            <Button variant="secondary">Events analytics</Button>
          </Link>
          <Link href="/admin/analytics">
            <Button variant="ghost">Back</Button>
          </Link>
        </>
      }
    >
      <AdminAnalyticsSubnav />

      <Select
        label="Event drilldown range"
        value={rangeKey}
        onChange={(e) => {
          setEvents([]);
          setRangeKey(e.target.value as AnalyticsRangeKey);
        }}
        className="max-w-xs"
      >
        <option value="7d">7 days</option>
        <option value="30d">30 days</option>
        <option value="90d">90 days</option>
        <option value="365d">12 months</option>
      </Select>

      {error ? (
        <Alert tone="danger" title="Could not load revenue">
          {error}
        </Alert>
      ) : null}
      {!data && !error ? <SkeletonLoader lines={5} /> : null}
      {data ? (
        <div className="space-y-8">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <StatCard title="Gross revenue" value={formatNgn(data.gross_revenue)} />
            <StatCard title="Platform fees" value={formatNgn(data.platform_fees)} />
            <StatCard
              title="Net after refunds"
              value={formatNgn(data.net_after_refunds)}
            />
            <StatCard title="Refunds" value={formatNgn(data.refund_amount)} />
            <StatCard title="Payouts" value={formatNgn(data.payout_totals)} />
            <StatCard title="Vault revenue" value={formatNgn(data.vault_revenue)} />
          </div>
          <TrendPanel
            title="Sales over time"
            points={data.sales_over_time.map((p) => ({
              label: p.date,
              value: Number(p.value),
              display: formatNgn(p.value),
            }))}
            emptyTitle="No sales in range"
          />

          <section className="space-y-4">
            <SectionHeader
              title="Top events by revenue"
              description="Open an event for funnel and ticket drilldown"
            />
            <DataTable
              rows={events}
              rowKey={(e) => e.event_id}
              emptyTitle="No event revenue in this range"
              columns={[
                {
                  key: "t",
                  header: "Event",
                  cell: (e) => (
                    <div className="space-y-0.5">
                      <Link
                        href={`/admin/events/${e.event_id}/analytics`}
                        className="font-semibold text-foreground underline decoration-accent underline-offset-2"
                      >
                        {e.title}
                      </Link>
                      <p className="text-xs text-muted-foreground">
                        {e.host_display_name ?? "Host"}
                      </p>
                    </div>
                  ),
                },
                {
                  key: "s",
                  header: "Tickets",
                  cell: (e) => e.tickets_sold,
                },
                {
                  key: "p",
                  header: "Purchases",
                  cell: (e) => e.purchases,
                },
                {
                  key: "r",
                  header: "Revenue",
                  cell: (e) => formatNgn(e.revenue),
                },
                {
                  key: "a",
                  header: "",
                  cell: (e) => (
                    <Link href={`/admin/events/${e.event_id}/analytics`}>
                      <Button size="sm" variant="ghost">
                        Open
                      </Button>
                    </Link>
                  ),
                },
              ]}
            />
          </section>
        </div>
      ) : null}
    </DashboardShell>
  );
}
