"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AdminAmbassadorsNav } from "@/components/ambassadors/AdminAmbassadorsNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import { fetchAdminAmbassadorReports } from "@/lib/promos-api";
import type { AmbassadorReportsSummary } from "@/lib/types/promos";

export default function AdminAmbassadorReportsPage() {
  const [summary, setSummary] = useState<AmbassadorReportsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const report = await fetchAdminAmbassadorReports();
        if (active) setSummary(report);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load reports");
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
      eyebrow="Admin · Ambassadors"
      title="Reports"
      description="Platform-wide Ambassadors snapshot. Drill into audit logs for create, pause, reverse, and block actions."
      actions={
        <Link href="/admin/audit-logs">
          <Button variant="secondary">Audit logs</Button>
        </Link>
      }
    >
      <AdminAmbassadorsNav />
      {error ? <Alert tone="danger" title="Something went wrong">{error}</Alert> : null}

      {!summary ? (
        <SkeletonLoader lines={4} />
      ) : (
        <div className="space-y-6">
          <Card className="flex flex-wrap items-center gap-3 p-4">
            <span className="text-sm text-muted-foreground">Feature</span>
            <Badge tone={summary.feature_enabled ? "success" : "warning"}>
              {summary.feature_enabled ? "Enabled" : "Disabled"}
            </Badge>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard title="Campaigns" value={String(summary.campaigns_total)} />
            <StatCard title="Live" value={String(summary.campaigns_live)} />
            <StatCard title="Paused" value={String(summary.campaigns_paused)} />
            <StatCard title="Platform campaigns"
              value={String(summary.campaigns_platform)}
            />
            <StatCard title="Ambassadors"
              value={String(summary.ambassadors_total)}
            />
            <StatCard title="Active" value={String(summary.ambassadors_active)} />
            <StatCard title="Total clicks" value={String(summary.total_clicks ?? summary.clicks)} />
            <StatCard title="Unique clicks" value={String(summary.unique_clicks ?? summary.clicks)} />
            <StatCard title="Conversions"
              value={String(summary.conversions_active)}
            />
            <StatCard title="Reversed"
              value={String(summary.conversions_reversed)}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard title="Revenue"
              value={formatNgn(Number(summary.revenue_generated))}
            />
            <StatCard title="Commission owed"
              value={formatNgn(Number(summary.commission_owed))}
            />
            <StatCard title="Payable"
              value={formatNgn(Number(summary.payable_earnings))}
            />
            <StatCard title="Paid"
              value={formatNgn(Number(summary.paid_earnings))}
            />
          </div>

          <Card className="space-y-2 p-5">
            <h2 className="text-base font-semibold text-foreground">Audit</h2>
            <p className="text-sm text-muted-foreground">
              Filter platform audit logs by ambassador actions:
              <code className="mx-1">ambassadors.campaign_*</code>,
              <code className="mx-1">ambassadors.sale_reversed</code>,
              <code className="mx-1">users.ambassadors_block</code>.
            </p>
            <div className="flex flex-wrap gap-2 pt-2">
              <Link href="/admin/audit-logs">
                <Button variant="secondary">Open audit logs</Button>
              </Link>
            </div>
          </Card>
        </div>
      )}
    </DashboardShell>
  );
}
