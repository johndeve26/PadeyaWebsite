"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { HostAmbassadorsNav } from "@/components/ambassadors/HostAmbassadorsNav";
import { RequireHost } from "@/components/hosts/RequireHost";
import { useHostWorkspace } from "@/components/hosts/HostWorkspaceProvider";
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
  endHostDomainCampaign,
  fetchHostCampaignParticipants,
  fetchHostDomainCampaign,
  pauseHostDomainCampaign,
  removeHostParticipant,
  type DomainCampaign,
  type HostParticipantRow,
} from "@/lib/ambassadors-api";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import { hasHostPermission } from "@/lib/host-access";

function formatCommission(campaign: DomainCampaign): string {
  if (campaign.commission_type === "flat") {
    return `${formatNgn(Number(campaign.commission_value))} flat`;
  }
  if (campaign.commission_type === "reward_only") {
    return "reward only";
  }
  return `${campaign.commission_value}% commission`;
}

function campaignTypeLabel(campaign: DomainCampaign): string {
  if (campaign.campaign_type === "event_merch") {
    return "Event Merch Ambassador";
  }
  return "Event Ambassador";
}

export default function HostCampaignDetailPage() {
  const params = useParams<{ id: string }>();
  const campaignId = params.id;
  const { active } = useHostWorkspace();
  const hostId = active?.host_id ?? null;
  const canPause = hasHostPermission(active, "ambassadors.pause_campaigns");
  const canRemove = hasHostPermission(
    active,
    "ambassadors.remove_participants",
  );

  const [campaign, setCampaign] = useState<DomainCampaign | null>(null);
  const [participants, setParticipants] = useState<HostParticipantRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const stats = useMemo(() => {
    return participants.reduce(
      (acc, row) => ({
        clicks: acc.clicks + row.clicks,
        conversions: acc.conversions + row.conversions,
        commission:
          acc.commission + Number(row.commission_amount || 0),
      }),
      { clicks: 0, conversions: 0, commission: 0 },
    );
  }, [participants]);

  const load = useCallback(async () => {
    const c = await fetchHostDomainCampaign(campaignId, hostId);
    setCampaign(c);
    try {
      setParticipants(
        await fetchHostCampaignParticipants(campaignId, hostId),
      );
    } catch {
      setParticipants([]);
    }
  }, [campaignId, hostId]);

  useEffect(() => {
    if (!hostId && !active?.is_owner) return;
    let alive = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (alive) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load campaign",
          );
        }
      }
    })();
    return () => {
      alive = false;
    };
  }, [load, hostId, active?.is_owner]);

  async function run(action: () => Promise<DomainCampaign>) {
    setBusy(true);
    setError(null);
    try {
      setCampaign(await action());
      setParticipants(
        await fetchHostCampaignParticipants(campaignId, hostId),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  async function onRemove(participantId: string) {
    if (!window.confirm("Remove this ambassador from the campaign?")) return;
    setBusy(true);
    setError(null);
    try {
      await removeHostParticipant(participantId, hostId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Remove failed");
    } finally {
      setBusy(false);
    }
  }

  const isLive =
    campaign?.status === "active" && Boolean(campaign?.is_joinable);

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Ambassador Campaigns"
        title={campaign?.name || "Campaign"}
        description={
          campaign
            ? `${campaign.event_title || "Event"} · ${formatCommission(campaign)} · ${campaignTypeLabel(campaign)}${
                campaign.hold_period_days != null
                  ? ` · ${campaign.hold_period_days}d hold`
                  : ""
              }`
            : "Loading campaign…"
        }
        actions={
          campaign?.event_id ? (
            <Link href={`/host/events/${campaign.event_id}/ambassadors`}>
              <Button size="sm" variant="secondary">
                Event Ambassadors
              </Button>
            </Link>
          ) : null
        }
      >
        <HostAmbassadorsNav />

        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        {!campaign && !error ? <SkeletonLoader lines={6} /> : null}

        {campaign ? (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={isLive ? "success" : "neutral"}>
                {campaign.status}
              </Badge>
              {isLive ? <Badge tone="accent">Live</Badge> : null}
            </div>

            <div className="flex flex-wrap gap-2">
              {campaign.status === "active" && canPause ? (
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busy}
                  onClick={() =>
                    void run(() => pauseHostDomainCampaign(campaignId, hostId))
                  }
                >
                  Pause campaign
                </Button>
              ) : null}
              {campaign.status !== "ended" && canPause ? (
                <Button
                  size="sm"
                  variant="danger"
                  disabled={busy}
                  onClick={() =>
                    void run(() => endHostDomainCampaign(campaignId, hostId))
                  }
                >
                  End campaign
                </Button>
              ) : null}
              {!canPause && !active?.is_owner ? (
                <Badge tone="neutral">Campaign actions read-only</Badge>
              ) : null}
            </div>

            <Card className="space-y-3">
              <h2 className="text-lg font-bold">Performance</h2>
              <p className="text-sm text-muted-foreground">
                Verified paid sales attributed to this campaign. Pending
                checkouts never count.
              </p>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <StatCard title="Participants" value={participants.length} />
                <StatCard
                  title="Total clicks"
                  value={stats.total_clicks ?? stats.clicks}
                  hint="Referral link visits"
                />
                <StatCard
                  title="Unique clicks"
                  value={stats.unique_clicks ?? stats.clicks}
                  hint="Estimated unique visitors"
                />
                <StatCard title="Conversions" value={stats.conversions} />
                <StatCard
                  title="Commission"
                  value={formatNgn(stats.commission)}
                />
              </div>
            </Card>

            <Card className="space-y-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-bold">Conversions & rewards</h2>
                  <p className="text-sm text-muted-foreground">
                    Approve, reject, mark paid, or reverse rewards for
                    conversions from this campaign on the conversions page.
                  </p>
                </div>
                <Link href="/host/ambassadors/conversions">
                  <Button size="sm">View conversions & rewards</Button>
                </Link>
              </div>
            </Card>

            <Card className="space-y-3">
              <h2 className="text-lg font-bold">Participants</h2>
              <p className="text-sm text-muted-foreground">
                Everyone who joined this campaign. Sorted by commission earned.
              </p>
              {participants.length === 0 ? (
                <EmptyState
                  title="No participants yet"
                  description="When fans join via Promote this event, they appear here."
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[720px] text-left text-sm">
                    <thead className="text-xs uppercase tracking-wide text-muted-foreground">
                      <tr>
                        <th className="py-2 pr-3">Ambassador</th>
                        <th className="py-2 pr-3">Code</th>
                        <th className="py-2 pr-3">Status</th>
                        <th className="py-2 pr-3">Total clicks</th>
                        <th className="py-2 pr-3">Unique</th>
                        <th className="py-2 pr-3">Conversions</th>
                        <th className="py-2 pr-3">Commission</th>
                        <th className="py-2"> </th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...participants]
                        .sort(
                          (a, b) =>
                            Number(b.commission_amount) -
                            Number(a.commission_amount),
                        )
                        .map((row) => (
                          <tr key={row.id} className="border-t border-border">
                            <td className="py-2 pr-3 font-semibold">
                              {row.display_name || "Ambassador"}
                            </td>
                            <td className="py-2 pr-3 font-mono text-xs">
                              {row.ambassador_code}
                            </td>
                            <td className="py-2 pr-3">{row.status}</td>
                            <td className="py-2 pr-3">
                              {row.total_clicks ?? row.clicks}
                            </td>
                            <td className="py-2 pr-3">
                              {row.unique_clicks ?? row.clicks}
                            </td>
                            <td className="py-2 pr-3">{row.conversions}</td>
                            <td className="py-2 pr-3">
                              {formatNgn(Number(row.commission_amount))}
                            </td>
                            <td className="py-2">
                              {row.status === "active" && canRemove ? (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  disabled={busy}
                                  onClick={() => void onRemove(row.id)}
                                >
                                  Remove
                                </Button>
                              ) : null}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
