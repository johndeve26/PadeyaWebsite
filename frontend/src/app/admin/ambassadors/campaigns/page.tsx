"use client";

import { useEffect, useState, type FormEvent } from "react";

import { AdminAmbassadorsNav } from "@/components/ambassadors/AdminAmbassadorsNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Select,
  SkeletonLoader,
  StatCard,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn, formatPercent } from "@/lib/format";
import {
  createAdminCampaign,
  fetchAdminCampaigns,
  pauseAdminCampaign,
  resumeAdminCampaign,
} from "@/lib/promos-api";
import type { AmbassadorCampaign } from "@/lib/types/promos";

export default function AdminAmbassadorCampaignsPage() {
  const [rows, setRows] = useState<AmbassadorCampaign[] | null>(null);
  const [eventId, setEventId] = useState("");
  const [name, setName] = useState("Platform Ambassadors");
  const [campaignType, setCampaignType] = useState("event_tickets");
  const [commissionType, setCommissionType] = useState("percentage");
  const [commission, setCommission] = useState("5");
  const [holdDays, setHoldDays] = useState("7");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setRows(await fetchAdminCampaigns());
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load campaigns");
          setRows([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!eventId.trim()) {
      setError("Event id is required");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const value = Number(commission);
      await createAdminCampaign({
        event_id: eventId.trim(),
        name,
        campaign_type: campaignType,
        commission_type: commissionType,
        commission_value: commissionType === "reward_only" ? 0 : value,
        commission_percent: commissionType === "percentage" ? value : 0,
        hold_period_days: Number(holdDays) || 7,
        status: "public_open",
      });
      setEventId("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not create campaign");
    } finally {
      setBusy(false);
    }
  }

  async function onPause(id: string) {
    const reason = window.prompt("Reason for pausing (optional)") || undefined;
    setBusy(true);
    setError(null);
    try {
      await pauseAdminCampaign(id, reason);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Pause failed");
    } finally {
      setBusy(false);
    }
  }

  async function onResume(id: string) {
    setBusy(true);
    setError(null);
    try {
      await resumeAdminCampaign(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Resume failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin · Ambassadors"
      title="Campaigns"
      description="View all host and platform Ambassadors campaigns. Create event-scoped platform campaigns here; for platform-wide programs (one link, tickets + merch, funded by Pàdéyá) use Programs."
    >
      <AdminAmbassadorsNav />
      {error ? <Alert tone="danger" title="Something went wrong">{error}</Alert> : null}

      <Card className="mb-6 space-y-4 p-5">
        <h2 className="text-base font-semibold text-foreground">
          Create platform campaign
        </h2>
        <form onSubmit={onCreate} className="grid gap-3 sm:grid-cols-2">
          <Input
            label="Event id"
            value={eventId}
            onChange={(e) => setEventId(e.target.value)}
            placeholder="UUID of published event"
            required
          />
          <Input
            label="Campaign name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <Select
            label="Campaign type"
            value={campaignType}
            onChange={(e) => setCampaignType(e.target.value)}
          >
            <option value="event_tickets">Event Ambassador (tickets)</option>
            <option value="event_merch">Event Merch Ambassador</option>
          </Select>
          <Select
            label="Commission type"
            value={commissionType}
            onChange={(e) => setCommissionType(e.target.value)}
          >
            <option value="percentage">Percentage</option>
            <option value="flat">Flat</option>
            <option value="reward_only">Reward only</option>
          </Select>
          {commissionType !== "reward_only" ? (
            <Input
              label={
                commissionType === "flat" ? "Flat amount (NGN)" : "Commission %"
              }
              type="number"
              min={0}
              max={commissionType === "percentage" ? 100 : undefined}
              step="0.01"
              value={commission}
              onChange={(e) => setCommission(e.target.value)}
            />
          ) : null}
          <Input
            label="Hold period (days)"
            type="number"
            min={0}
            max={365}
            value={holdDays}
            onChange={(e) => setHoldDays(e.target.value)}
          />
          <div className="sm:col-span-2">
            <Button type="submit" disabled={busy}>
              Create platform campaign
            </Button>
          </div>
        </form>
      </Card>

      {rows === null ? (
        <SkeletonLoader lines={4} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No campaigns"
          description="Host or platform campaigns will appear here."
        />
      ) : (
        <div className="space-y-4">
          {rows.map((c) => (
            <Card key={c.id} className="space-y-3 p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-foreground">{c.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {c.event_title || c.event_id}
                    {c.host_display_name ? ` · ${c.host_display_name}` : ""}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Badge tone={c.is_live ? "success" : "neutral"}>{c.status}</Badge>
                  <Badge tone={c.source === "platform" ? "accent" : "neutral"}>
                    {c.source === "platform" ? "Platform" : "Host"}
                  </Badge>
                  <Badge tone="neutral">
                    {c.campaign_type_label ||
                      (c.campaign_type === "event_merch"
                        ? "Merch"
                        : "Tickets")}
                  </Badge>
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-4">
                <StatCard title="Clicks" value={String(c.clicks)} />
                <StatCard title="Sales" value={String(c.confirmed_sales)} />
                <StatCard title="Conversion"
                  value={formatPercent(Number(c.conversion_rate))}
                />
                <StatCard title="Commission"
                  value={formatNgn(Number(c.commission_owed))}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                {c.status === "public_open" ? (
                  <Button
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void onPause(c.id)}
                  >
                    Pause
                  </Button>
                ) : null}
                {c.status === "paused" ? (
                  <Button disabled={busy} onClick={() => void onResume(c.id)}>
                    Resume
                  </Button>
                ) : null}
              </div>
            </Card>
          ))}
        </div>
      )}
    </DashboardShell>
  );
}
