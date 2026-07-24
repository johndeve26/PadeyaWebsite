"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  SectionHeader,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { fetchCheckInStats, type CheckInStats } from "@/lib/checkin-api";

function CheckInProgress({
  checkedIn,
  total,
}: {
  checkedIn: number;
  total: number;
}) {
  const rate = total > 0 ? Math.round((checkedIn / total) * 100) : 0;
  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
            Check-in rate
          </p>
          <p className="text-3xl font-extrabold tracking-tight text-foreground">
            {rate}%
          </p>
        </div>
        <p className="text-sm text-muted-foreground">
          {checkedIn.toLocaleString()} of {total.toLocaleString()} tickets
        </p>
      </div>
      <div
        className="h-3 overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuenow={rate}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Check-in rate"
      >
        <div
          className="h-full rounded-full bg-accent transition-all duration-500"
          style={{ width: `${rate}%` }}
        />
      </div>
    </Card>
  );
}

export default function CheckInAnalyticsPage() {
  const params = useParams<{ id: string }>();
  const [stats, setStats] = useState<CheckInStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void fetchCheckInStats(params.id)
      .then((data) => {
        if (active) setStats(data);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Failed to load stats");
      });
    return () => {
      active = false;
    };
  }, [params.id]);

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Check-in analytics"
        title="Door stats"
        description="Live counts for capacity, successful scans, duplicates, and invalid attempts."
        actions={
          <Link href={`/host/events/${params.id}/check-in`}>
            <Button size="sm" variant="secondary">
              Back to scanner
            </Button>
          </Link>
        }
      >
        {error ? (
          <Alert tone="danger" title="Unable to load stats">
            {error}
          </Alert>
        ) : null}

        {!stats && !error ? <SkeletonLoader lines={4} /> : null}

        {stats ? (
          <div className="space-y-8">
            <CheckInProgress checkedIn={stats.checked_in} total={stats.total_tickets} />

            <section className="space-y-4">
              <SectionHeader
                eyebrow="Capacity"
                title="Ticket status"
                description="How many guests have arrived vs. still expected at the door."
              />
              <div className="grid gap-4 sm:grid-cols-3">
                <StatCard title="Total tickets" value={stats.total_tickets} />
                <StatCard title="Checked in" value={stats.checked_in} />
                <StatCard title="Remaining" value={stats.remaining} />
              </div>
            </section>

            <section className="space-y-4">
              <SectionHeader
                eyebrow="Scanner"
                title="Scan outcomes"
                description="Breakdown of all scan attempts at the gate."
              />
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <StatCard title="Successful scans" value={stats.successful_scans} />
                <StatCard title="Duplicate scans" value={stats.duplicate_scans} />
                <StatCard title="Invalid scans" value={stats.invalid_scans} />
                <StatCard title="Override scans" value={stats.override_scans} />
              </div>
            </section>
          </div>
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
