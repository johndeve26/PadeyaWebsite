"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { EventOpsNav } from "@/components/host/EventOpsNav";
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
import { ApiError } from "@/lib/api";
import { fetchEventById } from "@/lib/events-api";
import { formatNgn, formatPercent } from "@/lib/format";
import {
  createHostCampaign,
  fetchEventCampaigns,
  pauseHostCampaign,
  resumeHostCampaign,
} from "@/lib/promos-api";
import type { EventItem } from "@/lib/types/events";
import type { AmbassadorCampaign } from "@/lib/types/promos";

export default function HostEventAmbassadorsPage() {
  const params = useParams<{ id: string }>();
  const eventId = params.id;
  const [event, setEvent] = useState<EventItem | null>(null);
  const [campaigns, setCampaigns] = useState<AmbassadorCampaign[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  async function loadCampaigns() {
    setCampaigns(await fetchEventCampaigns(eventId));
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const ev = await fetchEventById(eventId);
        if (!active) return;
        setEvent(ev);
        const rows = await fetchEventCampaigns(eventId);
        if (active) setCampaigns(rows);
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load");
        }
      } finally {
        if (active) setLoaded(true);
      }
    })();
    return () => {
      active = false;
    };
  }, [eventId]);

  async function enableCampaign(campaignType: "event_tickets" | "event_merch") {
    setBusy(true);
    setError(null);
    try {
      const label =
        campaignType === "event_merch"
          ? "Event Merch Ambassadors"
          : "Event Ambassadors";
      await createHostCampaign({
        event_id: eventId,
        name: `${event?.title || "Event"} · ${label}`,
        campaign_type: campaignType,
        commission_percent: Number(
          event?.open_ambassador_commission_percent ?? 5,
        ),
        status: "public_open",
      });
      await loadCampaigns();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not enable Ambassadors");
    } finally {
      setBusy(false);
    }
  }

  async function togglePause(campaign: AmbassadorCampaign) {
    setBusy(true);
    setError(null);
    try {
      if (campaign.status === "paused") {
        await resumeHostCampaign(campaign.id);
      } else {
        await pauseHostCampaign(campaign.id);
      }
      await loadCampaigns();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not update campaign");
    } finally {
      setBusy(false);
    }
  }

  const hasTickets = campaigns.some((c) => c.campaign_type === "event_tickets");
  const hasMerch = campaigns.some((c) => c.campaign_type === "event_merch");

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Event"
        title={event?.title || "Ambassadors"}
        description="Enable Event Ambassador (tickets) and/or Event Merch Ambassador campaigns for this event."
        actions={<EventOpsNav eventId={eventId} />}
      >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        {!loaded ? <SkeletonLoader lines={5} /> : null}

        {loaded && campaigns.length === 0 ? (
          <EmptyState
            title="Ambassadors not enabled"
            description="Create a public_open campaign so fans can promote tickets and/or merch."
            action={
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  disabled={busy}
                  onClick={() => void enableCampaign("event_tickets")}
                >
                  Enable Event Ambassador
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void enableCampaign("event_merch")}
                >
                  Enable Merch Ambassador
                </Button>
                <Link href="/host/ambassadors/campaigns/new">
                  <Button size="sm" variant="secondary">
                    Advanced setup
                  </Button>
                </Link>
              </div>
            }
          />
        ) : null}

        {loaded && campaigns.length > 0 ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {!hasTickets ? (
                <Button
                  size="sm"
                  disabled={busy}
                  onClick={() => void enableCampaign("event_tickets")}
                >
                  Add Event Ambassador
                </Button>
              ) : null}
              {!hasMerch ? (
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void enableCampaign("event_merch")}
                >
                  Add Merch Ambassador
                </Button>
              ) : null}
            </div>
            {campaigns.map((campaign) => (
              <Card key={campaign.id} className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-xl font-bold">{campaign.name}</h2>
                  <Badge tone={campaign.is_live ? "success" : "neutral"}>
                    {campaign.status}
                  </Badge>
                  <Badge tone="accent">
                    {campaign.campaign_type_label ||
                      (campaign.campaign_type === "event_merch"
                        ? "Event Merch Ambassador"
                        : "Event Ambassador")}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  {formatPercent(campaign.commission_percent)} commission ·{" "}
                  {campaign.campaign_type === "event_merch"
                    ? "Merch orders only"
                    : "Ticket sales only"}
                </p>
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <StatCard title="Ambassadors" value={campaign.active_ambassadors} />
                  <StatCard title="Clicks" value={campaign.clicks} />
                  <StatCard title="Sales" value={campaign.confirmed_sales} />
                  <StatCard
                    title="Est. commission"
                    value={formatNgn(campaign.estimated_earnings)}
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link href={`/host/ambassadors/campaigns/${campaign.id}`}>
                    <Button size="sm">Open campaign</Button>
                  </Link>
                  {campaign.status !== "ended" ? (
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={busy}
                      onClick={() => void togglePause(campaign)}
                    >
                      {campaign.status === "paused" ? "Resume" : "Pause"}
                    </Button>
                  ) : null}
                </div>
              </Card>
            ))}
          </div>
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
