"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { TrendPanel } from "@/components/analytics/TrendPanel";
import { AdminAISummaryPanel } from "@/components/admin/AdminAISummaryPanel";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  DataTable,
  SectionHeader,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { exportAdminAnalyticsCsv, fetchAdminAnalytics } from "@/lib/analytics-api";
import { formatNgn, formatPercent } from "@/lib/format";
import type { AdminPlatformSummary } from "@/lib/types/analytics";

const ANALYTICS_NAV = [
  { href: "/admin/analytics", label: "Overview" },
  { href: "/admin/analytics/revenue", label: "Revenue" },
  { href: "/admin/analytics/events", label: "Events" },
  { href: "/admin/analytics/hosts", label: "Hosts" },
  { href: "/admin/analytics/blog", label: "Blog" },
  { href: "/admin/analytics/support", label: "Support" },
] as const;

function AnalyticsSubnav() {
  const pathname = usePathname();

  return (
    <Card className="flex flex-wrap gap-2 p-3">
      {ANALYTICS_NAV.map(({ href, label }) => (
        <Link key={href} href={href}>
          <Button size="sm" variant={pathname === href ? "dark" : "ghost"}>
            {label}
          </Button>
        </Link>
      ))}
    </Card>
  );
}

export default function AdminAnalyticsPage() {
  const [data, setData] = useState<AdminPlatformSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const summary = await fetchAdminAnalytics();
        if (active) setData(summary);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load analytics");
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
      eyebrow="Admin"
      title="Platform analytics"
      description="Users, GMV, refunds, payouts, and top performers."
      actions={
        <>
          <Link href="/admin/analytics/revenue">
            <Button variant="secondary">Revenue</Button>
          </Link>
          <Button
            variant="dark"
            onClick={() => {
              void exportAdminAnalyticsCsv()
                .then(() => setNote("CSV downloaded."))
                .catch(() => setNote("Export failed."));
            }}
          >
            Export CSV
          </Button>
        </>
      }
    >
      <AnalyticsSubnav />

      <AdminAISummaryPanel
        feature="admin.analytics.revenue_summary"
        title="Analytics AI summary"
        generateLabel="Explain this period"
        links={[
          { href: "/admin/analytics/revenue", label: "Revenue" },
          { href: "/admin/refunds", label: "Refunds" },
          { href: "/admin/payouts", label: "Payouts" },
        ]}
      />

      {error ? (
        <Alert tone="danger" title="Could not load analytics">
          {error}
        </Alert>
      ) : null}
      {note ? (
        <Alert tone={note.includes("failed") ? "warning" : "success"}>{note}</Alert>
      ) : null}
      {!data && !error ? <SkeletonLoader lines={6} /> : null}

      {data ? (
        <div className="space-y-10">
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard title="Users" value={data.total_users} />
            <StatCard title="Hosts" value={data.total_hosts} />
            <StatCard title="Events" value={data.total_events} />
            <StatCard title="Tickets sold" value={data.tickets_sold} />
            <StatCard title="Gross revenue" value={formatNgn(data.gross_revenue)} />
            <StatCard title="Platform fees" value={formatNgn(data.platform_fees)} />
            <StatCard
              title="Refund rate"
              value={
                data.refund_rate != null ? formatPercent(data.refund_rate) : "—"
              }
            />
            <StatCard title="Vault revenue" value={formatNgn(data.vault_revenue)} />
          </section>

          <TrendPanel
            title="Sales over time"
            points={data.sales_over_time.map((p) => ({
              label: p.date,
              value: Number(p.value),
              display: formatNgn(p.value),
            }))}
            emptyTitle="No sales in range"
          />

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="space-y-4">
              <SectionHeader title="Top events" />
              <DataTable
                rows={data.top_events}
                rowKey={(e) => e.event_id}
                emptyTitle="No event sales yet"
                columns={[
                  { key: "t", header: "Event", cell: (e) => e.title },
                  { key: "s", header: "Tickets", cell: (e) => e.tickets_sold },
                  {
                    key: "r",
                    header: "Revenue",
                    cell: (e) => formatNgn(e.revenue),
                  },
                ]}
              />
            </section>
            <section className="space-y-4">
              <SectionHeader title="Top hosts" />
              <DataTable
                rows={data.top_hosts}
                rowKey={(h) => h.host_id}
                emptyTitle="No host revenue yet"
                columns={[
                  {
                    key: "n",
                    header: "Host",
                    cell: (h) => (
                      <span>
                        {h.display_name}{" "}
                        <span className="text-muted-foreground">@{h.username}</span>
                      </span>
                    ),
                  },
                  {
                    key: "r",
                    header: "Revenue",
                    cell: (h) => formatNgn(h.revenue),
                  },
                ]}
              />
            </section>
          </div>
        </div>
      ) : null}
    </DashboardShell>
  );
}
