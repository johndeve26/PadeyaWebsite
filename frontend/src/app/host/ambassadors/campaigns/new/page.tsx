"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { HostAmbassadorsNav } from "@/components/ambassadors/HostAmbassadorsNav";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, Card, Input, Select } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchMyEvents } from "@/lib/events-api";
import { createHostCampaign } from "@/lib/promos-api";
import type { EventItem } from "@/lib/types/events";

const TYPE_OPTIONS = [
  {
    value: "event_tickets",
    label: "Event Ambassador",
    hint: "Commission from verified ticket sales for this event.",
    defaultName: "Event Ambassadors",
    defaultAppliesTo: "tickets",
  },
  {
    value: "event_merch",
    label: "Event Merch Ambassador",
    hint: "Commission from verified event-linked merch orders.",
    defaultName: "Event Merch Ambassadors",
    defaultAppliesTo: "merch",
  },
] as const;

export default function NewAmbassadorCampaignPage() {
  const router = useRouter();
  const [events, setEvents] = useState<EventItem[]>([]);
  const [eventId, setEventId] = useState("");
  const [campaignType, setCampaignType] = useState<string>("event_tickets");
  const [name, setName] = useState("Event Ambassadors");
  const [commissionType, setCommissionType] = useState("percentage");
  const [commissionValue, setCommissionValue] = useState("5");
  const [appliesTo, setAppliesTo] = useState("tickets");
  const [holdDays, setHoldDays] = useState("7");
  const [payoutMinimum, setPayoutMinimum] = useState("");
  const [maxPerOrder, setMaxPerOrder] = useState("");
  const [freeTicketAfter, setFreeTicketAfter] = useState("");
  const [leaderboardReward, setLeaderboardReward] = useState(false);
  const [leaderboardDesc, setLeaderboardDesc] = useState("");
  const [allowHostOwnerCommission, setAllowHostOwnerCommission] = useState(false);
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const rows = await fetchMyEvents();
        if (active) {
          setEvents(
            rows.filter((e) => e.status === "published" || e.status === "paused"),
          );
        }
      } catch {
        if (active) setEvents([]);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const selectedType =
    TYPE_OPTIONS.find((t) => t.value === campaignType) ?? TYPE_OPTIONS[0];

  const valueLabel =
    commissionType === "flat"
      ? "Flat commission (NGN)"
      : commissionType === "reward_only"
        ? "Commission value (unused)"
        : "Commission %";

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!eventId) {
      setError("Select an event");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const value = Number(commissionValue);
      const campaign = await createHostCampaign({
        event_id: eventId,
        name,
        campaign_type: campaignType,
        commission_type: commissionType,
        commission_value: commissionType === "reward_only" ? 0 : value,
        commission_percent:
          commissionType === "percentage" ? value : 0,
        applies_to: appliesTo,
        hold_period_days: Number(holdDays) || 7,
        payout_minimum: payoutMinimum ? Number(payoutMinimum) : null,
        max_commission_per_order: maxPerOrder ? Number(maxPerOrder) : null,
        free_ticket_after_sales: freeTicketAfter
          ? Number(freeTicketAfter)
          : null,
        leaderboard_reward_enabled: leaderboardReward,
        leaderboard_reward_description: leaderboardReward
          ? leaderboardDesc || null
          : null,
        allow_host_owner_commission: allowHostOwnerCommission,
        starts_at: startsAt ? new Date(startsAt).toISOString() : null,
        ends_at: endsAt ? new Date(endsAt).toISOString() : null,
        status: "public_open",
      });
      router.push(`/host/ambassadors/campaigns/${campaign.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not create campaign");
      setBusy(false);
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Ambassador Campaigns"
        title="New campaign"
        description="Create an Event Ambassador (tickets) or Event Merch Ambassador campaign with commission or reward rules."
        actions={
          <Link href="/host/ambassadors/campaigns">
            <Button size="sm" variant="secondary">
              Cancel
            </Button>
          </Link>
        }
      >
        <HostAmbassadorsNav />
        {error ? (
          <Alert tone="danger" title="Could not create">
            {error}
          </Alert>
        ) : null}
        <Card className="max-w-xl space-y-4">
          <form className="space-y-4" onSubmit={onSubmit}>
            <Select
              label="Event"
              value={eventId}
              onChange={(e) => setEventId(e.target.value)}
              required
            >
              <option value="">Select event…</option>
              {events.map((ev) => (
                <option key={ev.id} value={ev.id}>
                  {ev.title}
                </option>
              ))}
            </Select>
            <Select
              label="Campaign type"
              value={campaignType}
              onChange={(e) => {
                const next = e.target.value;
                setCampaignType(next);
                const opt = TYPE_OPTIONS.find((t) => t.value === next);
                if (
                  opt &&
                  (name === "Event Ambassadors" ||
                    name === "Event Merch Ambassadors")
                ) {
                  setName(opt.defaultName);
                }
                if (opt) setAppliesTo(opt.defaultAppliesTo);
              }}
              required
            >
              {TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
            <p className="text-sm text-muted-foreground">{selectedType.hint}</p>
            <Input
              label="Campaign name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <Select
              label="Commission type"
              value={commissionType}
              onChange={(e) => {
                const next = e.target.value;
                setCommissionType(next);
                if (next === "reward_only") setCommissionValue("0");
                else if (next === "percentage" && commissionValue === "0")
                  setCommissionValue("5");
              }}
            >
              <option value="percentage">Percentage</option>
              <option value="flat">
                Flat (per ticket / per merch order)
              </option>
              <option value="reward_only">Reward only (no cash commission)</option>
            </Select>
            {commissionType !== "reward_only" ? (
              <Input
                label={valueLabel}
                type="number"
                min={0}
                max={commissionType === "percentage" ? 100 : undefined}
                step="0.01"
                value={commissionValue}
                onChange={(e) => setCommissionValue(e.target.value)}
                required
              />
            ) : null}
            <Select
              label="Applies to"
              value={appliesTo}
              onChange={(e) => setAppliesTo(e.target.value)}
            >
              <option value="tickets">Tickets</option>
              <option value="merch">Merch</option>
              <option value="tickets_and_merch">Tickets and merch</option>
            </Select>
            <Input
              label="Hold period (days)"
              type="number"
              min={0}
              max={365}
              value={holdDays}
              onChange={(e) => setHoldDays(e.target.value)}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Payout minimum (optional)"
                type="number"
                min={0}
                step="0.01"
                value={payoutMinimum}
                onChange={(e) => setPayoutMinimum(e.target.value)}
              />
              <Input
                label="Max commission / order (optional)"
                type="number"
                min={0}
                step="0.01"
                value={maxPerOrder}
                onChange={(e) => setMaxPerOrder(e.target.value)}
              />
            </div>
            <Input
              label="Free ticket after X sales (optional)"
              type="number"
              min={1}
              value={freeTicketAfter}
              onChange={(e) => setFreeTicketAfter(e.target.value)}
            />
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                checked={leaderboardReward}
                onChange={(e) => setLeaderboardReward(e.target.checked)}
              />
              Leaderboard reward
            </label>
            <label className="flex items-start gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                className="mt-1"
                checked={allowHostOwnerCommission}
                onChange={(e) => setAllowHostOwnerCommission(e.target.checked)}
              />
              <span>
                Allow host owner to join as Ambassador and earn commission
                (off by default — fraud control)
              </span>
            </label>
            {leaderboardReward ? (
              <Input
                label="Leaderboard reward description"
                value={leaderboardDesc}
                onChange={(e) => setLeaderboardDesc(e.target.value)}
                maxLength={500}
              />
            ) : null}
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Starts at (optional)"
                type="datetime-local"
                value={startsAt}
                onChange={(e) => setStartsAt(e.target.value)}
              />
              <Input
                label="Ends at (optional)"
                type="datetime-local"
                value={endsAt}
                onChange={(e) => setEndsAt(e.target.value)}
              />
            </div>
            <Button type="submit" disabled={busy}>
              {busy ? "Creating…" : "Create campaign"}
            </Button>
          </form>
        </Card>
      </DashboardShell>
    </RequireHost>
  );
}
