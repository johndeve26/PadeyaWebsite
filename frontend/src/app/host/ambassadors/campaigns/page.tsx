"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { HostAmbassadorsNav } from "@/components/ambassadors/HostAmbassadorsNav";
import { RequireHost } from "@/components/hosts/RequireHost";
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
import {
  fetchHostAmbassadorAnalytics,
  type HostAnalytics,
} from "@/lib/ambassadors-api";
import { ApiError } from "@/lib/api";
import { formatNgn, formatPercent } from "@/lib/format";
import { fetchHostCampaigns } from "@/lib/promos-api";
import type { AmbassadorCampaign } from "@/lib/types/promos";

export default function HostCampaignsListPage() {
  const [campaigns, setCampaigns] = useState<AmbassadorCampaign[]>([]);
  const [analytics, setAnalytics] = useState<HostAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const rows = await fetchHostCampaigns();
        if (active) {
          setCampaigns(rows);
          setLoaded(true);
        }
        try {
          const stats = await fetchHostAmbassadorAnalytics();
          if (active) setAnalytics(stats);
        } catch {
          /* domain analytics optional while cutover */
        }
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load campaigns");
          setLoaded(true);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Ambassador Campaigns"
        title="Campaigns"
        description="Create campaigns, set commission rules, track participants, conversions, and payouts."
        actions={
          <Link href="/host/ambassadors/campaigns/new">
            <Button size="sm">New campaign</Button>
          </Link>
        }
      >
        <HostAmbassadorsNav />

        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        {analytics ? (
          <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard title="Campaigns" value={analytics.campaigns} />
            <StatCard
              title="Active participants"
              value={analytics.active_participants}
            />
            <StatCard
              title="Total clicks"
              value={analytics.total_clicks ?? analytics.clicks}
              hint="Referral link visits"
            />
            <StatCard
              title="Unique clicks"
              value={analytics.unique_clicks ?? analytics.clicks}
              hint="Estimated unique visitors"
            />
            <StatCard title="Conversions" value={analytics.conversions} />
            <StatCard
              title="Commission owed"
              value={formatNgn(Number(analytics.commission_owed))}
            />
            <StatCard
              title="Commission paid"
              value={formatNgn(Number(analytics.commission_paid))}
            />
          </div>
        ) : null}

        {!loaded ? <SkeletonLoader lines={5} /> : null}

        {loaded && campaigns.length === 0 && !error ? (
          <EmptyState
            title="No campaigns"
            description="Create a campaign to enable Promote this event on an event page."
            action={
              <Link href="/host/ambassadors/campaigns/new">
                <Button size="sm">Create campaign</Button>
              </Link>
            }
          />
        ) : null}

        <div className="space-y-3">
          {campaigns.map((c) => (
            <Card key={c.id} className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-lg font-bold">{c.name}</h2>
                  <Badge tone={c.is_live ? "success" : "neutral"}>{c.status}</Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  {c.event_title || "Event"} · {formatPercent(c.commission_percent)}{" "}
                  {c.campaign_type_label ||
                    (c.campaign_type === "event_merch"
                      ? "Event Merch Ambassador"
                      : "Event Ambassador")}{" "}
                  · {c.commission_percent}% commission ·{" "}
                  {c.active_ambassadors} ambassadors
                </p>
              </div>
              <Link href={`/host/ambassadors/campaigns/${c.id}`}>
                <Button size="sm" variant="secondary">
                  Open
                </Button>
              </Link>
            </Card>
          ))}
        </div>
      </DashboardShell>
    </RequireHost>
  );
}
