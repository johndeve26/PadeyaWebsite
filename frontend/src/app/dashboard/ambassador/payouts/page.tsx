"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AmbassadorDashNav } from "@/components/ambassadors/AmbassadorDashNav";
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
import { fetchAmbassadorEarningsSummary } from "@/lib/promos-api";
import type { AmbassadorEarningsSummary } from "@/lib/types/promos";

export default function AmbassadorPayoutsPage() {
  const [summary, setSummary] = useState<AmbassadorEarningsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchAmbassadorEarningsSummary();
        if (active) setSummary(data);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Could not load payout status",
          );
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
      title="Payouts & rewards"
      description="Track payout and reward status for your Ambassador earnings. Payout rails are rolling out — estimated balances update from confirmed sales today."
      actions={
        <Link href="/dashboard/ambassador/earnings">
          <Button size="sm" variant="secondary">
            Earnings detail
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

      {!summary && !error ? <SkeletonLoader lines={4} /> : null}

      {summary ? (
        <div className="space-y-6">
          <Card className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-bold">Current status</h2>
              <Badge tone="neutral">{summary.payout_status}</Badge>
            </div>
            <p className="text-sm text-body">{summary.payout_status_label}</p>
          </Card>

          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard
              title="Payable now"
              value={formatNgn(summary.payable_earnings)}
            />
            <StatCard
              title="Approved"
              value={formatNgn(summary.approved_earnings)}
            />
            <StatCard title="Paid out" value={formatNgn(summary.paid_earnings)} />
          </div>

          <Card className="space-y-2">
            <h3 className="font-bold">Payout history</h3>
            <p className="text-sm text-muted-foreground">
              No Ambassador payouts have been issued yet. When payouts are enabled,
              completed transfers and reward redemptions will appear here.
            </p>
          </Card>
        </div>
      ) : null}
    </DashboardShell>
  );
}
