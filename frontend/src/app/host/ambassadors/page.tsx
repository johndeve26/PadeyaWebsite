"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { HostAmbassadorsNav } from "@/components/ambassadors/HostAmbassadorsNav";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  AmbassadorCard,
  Button,
  Card,
  EmptyState,
  Input,
  SectionHeader,
  Select,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { buildAmbassadorReferralLink } from "@/lib/ambassador-referral";
import { fetchMyEvents } from "@/lib/events-api";
import { createAmbassador, fetchHostAmbassadors } from "@/lib/promos-api";
import type { EventItem } from "@/lib/types/events";
import type { Ambassador } from "@/lib/types/promos";

export default function HostAmbassadorsPage() {
  const [rows, setRows] = useState<Ambassador[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [eventId, setEventId] = useState("");
  const [referralCode, setReferralCode] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [userEmail, setUserEmail] = useState("");
  const [commission, setCommission] = useState("10");
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  async function load() {
    setRows(await fetchHostAmbassadors());
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [items, eventRows] = await Promise.all([
          fetchHostAmbassadors(),
          fetchMyEvents(),
        ]);
        if (!active) return;
        setRows(items);
        const selectable = eventRows.filter(
          (e) =>
            Boolean(e.slug) &&
            (e.status === "published" ||
              e.status === "paused" ||
              e.status === "draft"),
        );
        setEvents(selectable);
        if (selectable.length === 0) setEventId("all");
        else if (selectable.length === 1) setEventId(selectable[0].id);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load ambassadors",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!eventId) {
      setError("Select an event, or All events, for this ambassador.");
      return;
    }
    try {
      await createAmbassador({
        referral_code: referralCode,
        display_name: displayName,
        user_email: userEmail || null,
        event_id: eventId === "all" ? null : eventId,
        commission_rate_percent: Number(commission),
      });
      setReferralCode("");
      setDisplayName("");
      setUserEmail("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Create failed");
    }
  }

  async function copyReferralLink(amb: Ambassador) {
    const link = buildAmbassadorReferralLink(amb.referral_code, {
      slug: amb.event_slug,
      merch: amb.campaign_type === "event_merch",
    });
    try {
      await navigator.clipboard.writeText(link);
      setCopiedId(amb.id);
      window.setTimeout(() => setCopiedId(null), 1600);
    } catch {
      setError("Could not copy — open the partner to copy manually");
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Grow"
        title="Ambassador Campaigns"
        description="Host-curated partners tied to a selected event. For open public promotion, create a campaign under Campaigns."
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

        <Card className="mb-8 max-w-2xl space-y-4">
          <SectionHeader
            title="Add curated partner"
            description="Pick the event this partner promotes — their referral link points at that event page."
          />
          <form className="space-y-4" onSubmit={onCreate}>
            <Select
              label="Event"
              value={eventId}
              onChange={(e) => setEventId(e.target.value)}
              hint="One event builds /events/{slug}?ref=… — All events uses /events?ref=…"
              required
            >
              <option value="">Select an event</option>
              <option value="all">All events</option>
              {events.map((ev) => (
                <option key={ev.id} value={ev.id}>
                  {ev.title}
                  {ev.status !== "published" ? ` (${ev.status})` : ""}
                </option>
              ))}
            </Select>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Referral code"
                value={referralCode}
                onChange={(e) => setReferralCode(e.target.value)}
                placeholder="tola"
                hint="Used in ?ref= query param."
                required
              />
              <Input
                label="Display name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Linked user email (optional)"
                value={userEmail}
                onChange={(e) => setUserEmail(e.target.value)}
                placeholder="Must already be registered"
                hint="Connect to an existing Pàdéyá account."
              />
              <Input
                label="Commission % (placeholder owed)"
                type="number"
                value={commission}
                onChange={(e) => setCommission(e.target.value)}
                hint="Tracking only — payout handled separately."
              />
            </div>
            <Button type="submit">
              Create ambassador
            </Button>
            {events.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No events yet — you can still create with All events, or add an
                event first for an event-specific link.
              </p>
            ) : null}
          </form>
        </Card>

        <div className="space-y-4">
          <SectionHeader
            title="Your ambassadors"
            description={`${rows.length} partner${rows.length === 1 ? "" : "s"} in your program.`}
          />
          {rows.length === 0 ? (
            <EmptyState
              title="No ambassadors yet"
              description="Create a referral ambassador to track partner sales."
            />
          ) : (
            <div className="space-y-3">
              {rows.map((amb) => (
                <AmbassadorCard
                  key={amb.id}
                  ambassador={amb}
                  href={`/host/ambassadors/${amb.id}`}
                  actions={
                    <>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => void copyReferralLink(amb)}
                      >
                        {copiedId === amb.id ? "Copied link" : "Copy link"}
                      </Button>
                      <Link href={`/host/ambassadors/${amb.id}`}>
                        <Button size="sm" variant="secondary">
                          View performance
                        </Button>
                      </Link>
                    </>
                  }
                />
              ))}
            </div>
          )}
        </div>
      </DashboardShell>
    </RequireHost>
  );
}
