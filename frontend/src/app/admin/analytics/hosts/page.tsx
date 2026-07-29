"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

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
import { fetchAdminHostsAnalytics } from "@/lib/analytics-api";
import { formatNgn } from "@/lib/format";
import type { AdminHostsSummary } from "@/lib/types/analytics";

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

export default function AdminHostsAnalyticsPage() {
  const [data, setData] = useState<AdminHostsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchAdminHostsAnalytics()
      .then(setData)
      .catch((err) =>
        setError(err instanceof ApiError ? err.detail : "Failed to load"),
      );
  }, []);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin analytics"
      title="Hosts"
      description="Active hosts and top earners by paid order revenue."
      actions={
        <Link href="/admin/analytics">
          <Button variant="ghost">Back</Button>
        </Link>
      }
    >
      <AnalyticsSubnav />

      {error ? (
        <Alert tone="danger" title="Could not load host analytics">
          {error}
        </Alert>
      ) : null}
      {!data && !error ? <SkeletonLoader lines={4} /> : null}
      {data ? (
        <div className="space-y-8">
          <div className="grid gap-4 sm:grid-cols-2">
            <StatCard title="Total hosts" value={data.total_hosts} />
            <StatCard title="Active hosts" value={data.active_hosts} />
          </div>
          <section className="space-y-4">
            <SectionHeader title="Top hosts" />
            <DataTable
              rows={data.top_hosts}
              rowKey={(h) => h.host_id}
              emptyTitle="No host revenue yet"
              columns={[
                { key: "n", header: "Host", cell: (h) => h.display_name },
                {
                  key: "u",
                  header: "Username",
                  cell: (h) => `@${h.username}`,
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
      ) : null}
    </DashboardShell>
  );
}
