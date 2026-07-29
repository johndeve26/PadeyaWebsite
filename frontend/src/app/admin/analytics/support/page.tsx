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
import { fetchAdminSupportAnalytics } from "@/lib/analytics-api";
import type { AdminSupportSummary } from "@/lib/types/analytics";

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

export default function AdminSupportAnalyticsPage() {
  const [data, setData] = useState<AdminSupportSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchAdminSupportAnalytics()
      .then(setData)
      .catch((err) =>
        setError(err instanceof ApiError ? err.detail : "Failed to load"),
      );
  }, []);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin analytics"
      title="Support"
      description="Support volume proxy and fraud signal placeholders — live triage happens in refund queues."
      actions={
        <>
          <Link href="/admin/refunds">
            <Button variant="secondary">Admin refunds</Button>
          </Link>
          <Link href="/support/refunds">
            <Button variant="ghost">Support refunds</Button>
          </Link>
        </>
      }
    >
      <AnalyticsSubnav />

      <Alert tone="info" title="Placeholder metrics">
        These figures summarize support load for dashboards. For case work, use the
        refund queues linked above.
      </Alert>

      {error ? (
        <Alert tone="danger" title="Could not load support analytics">
          {error}
        </Alert>
      ) : null}
      {!data && !error ? <SkeletonLoader lines={4} /> : null}
      {data ? (
        <div className="space-y-8">
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard title="Support volume" value={data.support_volume} />
            <StatCard
              title="Open refunds"
              value={data.open_refund_requests}
              href="/admin/refunds"
            />
            <StatCard title="Under review" value={data.escalated_refunds} />
          </div>
          {data.note ? (
            <Alert tone="warning" title="Data note">
              {data.note}
            </Alert>
          ) : null}
          <section className="space-y-4">
            <SectionHeader
              title="Fraud signals"
              description="Early-warning placeholders — not automated enforcement."
            />
            <DataTable
              rows={data.fraud_signals}
              rowKey={(f) => f.code}
              emptyTitle="No fraud signals recorded"
              columns={[
                { key: "l", header: "Signal", cell: (f) => f.label },
                { key: "c", header: "Code", cell: (f) => f.code },
                { key: "s", header: "Severity", cell: (f) => f.severity },
              ]}
            />
          </section>
        </div>
      ) : null}
    </DashboardShell>
  );
}
