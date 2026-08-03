"use client";

import { useEffect, useState } from "react";

import { AdminAmbassadorsNav } from "@/components/ambassadors/AdminAmbassadorsNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import {
  fetchAdminReferralLiabilities,
  fetchAdminReferralSummary,
} from "@/lib/promos-api";

function money(v: unknown): string {
  return formatNgn(Number(v ?? 0) || 0);
}

export default function AdminReferralLiabilitiesPage() {
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [rows, setRows] = useState<Array<Record<string, unknown>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [s, l] = await Promise.all([
          fetchAdminReferralSummary(),
          fetchAdminReferralLiabilities({ payer: "platform" }),
        ]);
        if (!active) return;
        setSummary(s);
        setRows(l);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.detail
              : "Could not load referral liabilities",
          );
          setSummary({});
          setRows([]);
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
      title="Referral liabilities"
      description="Host-funded and platform-funded commission stay separated. Platform liability is a Pàdéyá marketing expense and never reduces host settlement."
    >
      <AdminAmbassadorsNav />
      {error ? <Alert tone="danger" title="Error">{error}</Alert> : null}
      {!summary ? <SkeletonLoader lines={4} /> : null}
      {summary ? (
        <div className="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            title="Referred gross sales"
            value={money(summary.total_referred_gross_sales)}
          />
          <StatCard
            title="Host-funded commission"
            value={money(summary.host_funded_commission)}
          />
          <StatCard
            title="Platform-funded commission"
            value={money(summary.platform_funded_commission)}
          />
          <StatCard
            title="Pending platform liability"
            value={money(summary.pending_platform_liability)}
          />
          <StatCard
            title="Approved platform liability"
            value={money(summary.approved_platform_liability)}
          />
          <StatCard
            title="Paid platform commission"
            value={money(summary.paid_platform_commission)}
          />
          <StatCard
            title="Platform reversals"
            value={money(summary.platform_reversals)}
          />
          <StatCard
            title="Active platform programs"
            value={Number(summary.active_platform_programs ?? 0)}
          />
        </div>
      ) : null}

      <h2 className="mb-3 text-lg font-semibold">Platform ledger entries</h2>
      {rows === null ? <SkeletonLoader lines={3} /> : null}
      {rows && rows.length === 0 ? (
        <EmptyState
          title="No platform ledger entries"
          description="Earnings and reversals for platform-funded programs appear here."
        />
      ) : null}
      {rows && rows.length > 0 ? (
        <div className="space-y-2">
          {rows.map((row) => (
            <Card key={String(row.id)} className="flex flex-wrap items-center gap-3 p-4">
              <Badge tone="outline">{String(row.entry_type)}</Badge>
              <Badge>{String(row.status)}</Badge>
              <span className="text-sm">{money(row.commission_amount)}</span>
              <span className="text-sm text-muted-foreground">
                {String(row.product_type)} · order {String(row.order_id).slice(0, 8)}…
              </span>
            </Card>
          ))}
        </div>
      ) : null}
    </DashboardShell>
  );
}
