"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AmbassadorDashNav } from "@/components/ambassadors/AmbassadorDashNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { fetchDomainEarnings, type DomainEarnings } from "@/lib/ambassadors-api";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import { fetchAmbassadorEarningsSummary } from "@/lib/promos-api";
import type { AmbassadorEarningsSummary } from "@/lib/types/promos";

export default function AmbassadorDashboardOverviewPage() {
  const [summary, setSummary] = useState<AmbassadorEarningsSummary | null>(null);
  const [domain, setDomain] = useState<DomainEarnings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchAmbassadorEarningsSummary();
        if (active) setSummary(data);
        try {
          const d = await fetchDomainEarnings();
          if (active) setDomain(d);
        } catch {
          /* domain earnings optional during cutover */
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Could not load ambassador summary",
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
      title="Pàdéyá Ambassadors"
      description="Promote eligible events, share your Ambassador links, and track confirmed sales and earnings."
      actions={
        <Link href="/ambassadors/events">
          <Button size="sm">Find events to promote</Button>
        </Link>
      }
    >
      <AmbassadorDashNav />

      {error ? (
        <Alert tone="danger" title="Unable to load">
          {error}
        </Alert>
      ) : null}

      {!summary && !error ? <SkeletonLoader lines={5} /> : null}

      {summary ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard title="Active promotions" value={summary.enrollments_active} />
            <StatCard
              title="Total clicks"
              value={summary.total_clicks ?? summary.clicks}
              hint="Visits from your referral links"
            />
            <StatCard
              title="Unique clicks"
              value={summary.unique_clicks ?? summary.clicks}
              hint="Estimated unique visitors (24h)"
            />
            <StatCard title="Ticket sales" value={summary.tickets_sold} />
            <StatCard title="Merch sales" value={summary.merch_units_sold} />
          </div>

          <Card className="space-y-3">
            <h2 className="text-lg font-bold">Earnings snapshot</h2>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                title="Estimated"
                value={formatNgn(
                  domain
                    ? Number(domain.pending_amount)
                    : summary.estimated_earnings,
                )}
              />
              <StatCard
                title="Approved"
                value={formatNgn(
                  domain
                    ? Number(domain.approved_amount)
                    : summary.approved_earnings,
                )}
              />
              <StatCard
                title="Payable"
                value={formatNgn(
                  domain
                    ? Number(domain.payable_amount)
                    : summary.payable_earnings,
                )}
              />
              <StatCard
                title="Paid"
                value={formatNgn(
                  domain ? Number(domain.paid_amount) : summary.paid_earnings,
                )}
              />
            </div>
            <p className="text-sm text-muted-foreground">{summary.payout_status_label}</p>
            <div className="flex flex-wrap gap-2 pt-1">
              <Link href="/dashboard/ambassador/earnings">
                <Button size="sm" variant="secondary">
                  Earnings detail
                </Button>
              </Link>
              <Link href="/dashboard/ambassador/links">
                <Button size="sm" variant="ghost">
                  Links & QR
                </Button>
              </Link>
              <Link href="/dashboard/ambassador/leaderboard">
                <Button size="sm" variant="ghost">
                  Leaderboard
                </Button>
              </Link>
              <Link href="/dashboard/ambassador/payouts">
                <Button size="sm" variant="ghost">
                  Payout status
                </Button>
              </Link>
            </div>
          </Card>
        </div>
      ) : null}
    </DashboardShell>
  );
}
