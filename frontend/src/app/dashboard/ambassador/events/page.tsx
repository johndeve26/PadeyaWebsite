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
  EmptyState,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  buildAmbassadorReferralLink,
  formatAmbassadorCodeDisplay,
} from "@/lib/ambassador-referral";
import { formatNgn } from "@/lib/format";
import { fetchMyAmbassadorEnrollments } from "@/lib/promos-api";
import type { AmbassadorDashboard } from "@/lib/types/promos";

export default function AmbassadorEventsPage() {
  const [enrollments, setEnrollments] = useState<AmbassadorDashboard[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchMyAmbassadorEnrollments();
        if (active) {
          setEnrollments(data.enrollments);
          setLoaded(true);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Could not load your events",
          );
          setLoaded(true);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const active = enrollments.filter((e) => e.ambassador.status === "active");

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Ambassadors"
      title="My events"
      description="Events and host programs you are promoting as a Pàdéyá Ambassador."
      actions={
        <Link href="/ambassadors/events">
          <Button size="sm">Promote another event</Button>
        </Link>
      }
    >
      <AmbassadorDashNav />

      {error ? (
        <Alert tone="danger" title="Unable to load">
          {error}
        </Alert>
      ) : null}

      {!loaded ? <SkeletonLoader lines={5} /> : null}

      {loaded && active.length === 0 && !error ? (
        <EmptyState
          title="No events yet"
          description="Browse ambassador-eligible events and tap Promote this event to get started."
          action={
            <Link href="/ambassadors/events">
              <Button size="sm">Browse eligible events</Button>
            </Link>
          }
        />
      ) : null}

      {active.map((data) => {
        const amb = data.ambassador;
        const referralLink = buildAmbassadorReferralLink(amb.referral_code, {
          slug: amb.event_slug,
          merch: amb.campaign_type === "event_merch",
        });
        const codeDisplay =
          amb.referral_code_display ||
          formatAmbassadorCodeDisplay(amb.referral_code);
        return (
          <Card key={amb.id} className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-bold">
                {amb.event_title || amb.display_name}
              </h2>
              <Badge tone="accent">{codeDisplay}</Badge>
              {amb.program_kind === "open_event" ? (
                <Badge tone="neutral">Open</Badge>
              ) : (
                <Badge tone="neutral">Host partner</Badge>
              )}
            </div>
            <p className="break-all text-sm text-muted-foreground">{referralLink}</p>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              <StatCard title="Clicks" value={data.clicks} />
              <StatCard title="Tickets" value={data.tickets_sold} />
              <StatCard title="Merch" value={data.merch_units_sold ?? 0} />
              <StatCard title="Revenue" value={formatNgn(data.revenue_generated)} />
              <StatCard title="Est. earnings" value={formatNgn(data.commission_owed)} />
            </div>
            {amb.event_slug ? (
              <Link href={`/events/${amb.event_slug}?ref=${amb.referral_code}`}>
                <Button size="sm" variant="secondary">
                  Open event page
                </Button>
              </Link>
            ) : null}
          </Card>
        );
      })}
    </DashboardShell>
  );
}
