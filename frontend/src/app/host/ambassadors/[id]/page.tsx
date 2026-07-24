"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  SectionHeader,
  Select,
  SkeletonLoader,
  StatCard,
  StatusBadge,
} from "@/components/ui";
import {
  buildAmbassadorReferralLink,
  formatAmbassadorCodeDisplay,
} from "@/lib/ambassador-referral";
import { ApiError } from "@/lib/api";
import { fetchMyEvents } from "@/lib/events-api";
import { formatDateTime, formatNgn, formatPercent } from "@/lib/format";
import { fetchHostAmbassador, updateAmbassador } from "@/lib/promos-api";
import type { EventItem } from "@/lib/types/events";
import type { HostAmbassadorDashboard } from "@/lib/types/promos";

export default function HostAmbassadorDetailPage() {
  const params = useParams<{ id: string }>();
  const [data, setData] = useState<HostAmbassadorDashboard | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [eventId, setEventId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [savingEvent, setSavingEvent] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [detail, eventRows] = await Promise.all([
          fetchHostAmbassador(params.id),
          fetchMyEvents(),
        ]);
        if (!active) return;
        setData(detail);
        setEventId(detail.ambassador.event_id || "all");
        setEvents(
          eventRows.filter(
            (e) =>
              Boolean(e.slug) &&
              (e.status === "published" ||
                e.status === "paused" ||
                e.status === "draft"),
          ),
        );
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load ambassador",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id]);

  async function toggleStatus() {
    if (!data) return;
    try {
      await updateAmbassador(data.ambassador.id, {
        status: data.ambassador.status === "active" ? "inactive" : "active",
      });
      setData(await fetchHostAmbassador(params.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Update failed");
    }
  }

  async function saveEvent() {
    if (!data || !eventId) {
      setError("Select an event, or All events.");
      return;
    }
    setSavingEvent(true);
    setError(null);
    try {
      await updateAmbassador(data.ambassador.id, {
        event_id: eventId === "all" ? null : eventId,
      });
      const detail = await fetchHostAmbassador(params.id);
      setData(detail);
      setEventId(detail.ambassador.event_id || "all");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not update event");
    } finally {
      setSavingEvent(false);
    }
  }

  const referralLink = useMemo(() => {
    if (!data) return "";
    const amb = data.ambassador;
    return buildAmbassadorReferralLink(amb.referral_code, {
      slug: amb.event_slug,
      merch: amb.campaign_type === "event_merch",
    });
  }, [data]);

  const codeDisplay = data
    ? data.ambassador.referral_code_display ||
      formatAmbassadorCodeDisplay(data.ambassador.referral_code)
    : "";

  const isCurated = data?.ambassador.program_kind !== "open_event";
  const savedEventKey = data?.ambassador.event_id || "all";
  const eventDirty = Boolean(data && eventId !== savedEventKey);

  async function copyReferralLink() {
    if (!referralLink) return;
    try {
      await navigator.clipboard.writeText(referralLink);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setError("Could not copy — select the link manually");
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Ambassador Campaigns"
        title={data?.ambassador.display_name ?? "Ambassador"}
        description="Performance for this referral code."
        actions={
          <Link href="/host/ambassadors">
            <Button variant="ghost">Back to ambassadors</Button>
          </Link>
        }
      >
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        {!data && !error ? (
          <SkeletonLoader lines={5} />
        ) : data ? (
          <div className="space-y-6">
            <Card className="space-y-5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="accent">{codeDisplay}</Badge>
                <StatusBadge status={data.ambassador.status} />
                {data.ambassador.event_title ? (
                  <Badge tone="neutral">{data.ambassador.event_title}</Badge>
                ) : null}
              </div>

              {isCurated ? (
                <div className="space-y-3">
                  <Select
                    label="Event"
                    value={eventId}
                    onChange={(e) => setEventId(e.target.value)}
                    hint="One event builds /events/{slug}?ref=… — All events uses /events?ref=…"
                  >
                    <option value="all">All events</option>
                    {events.map((ev) => (
                      <option key={ev.id} value={ev.id}>
                        {ev.title}
                        {ev.status !== "published" ? ` (${ev.status})` : ""}
                      </option>
                    ))}
                  </Select>
                  {eventDirty ? (
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={savingEvent || !eventId}
                      onClick={() => void saveEvent()}
                    >
                      {savingEvent ? "Saving…" : "Save event"}
                    </Button>
                  ) : null}
                </div>
              ) : null}

              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Referral link
                </p>
                <p className="break-all text-sm font-medium text-foreground">
                  {referralLink}
                </p>
                {!data.ambassador.event_slug ? (
                  <p className="text-xs text-muted-foreground">
                    All events — opens the events browse page with this code;
                    clicks are tracked when someone lands with `?ref=`.
                  </p>
                ) : null}
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => void copyReferralLink()}
                >
                  {copied ? "Copied link" : "Copy link"}
                </Button>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
                <StatCard title="Clicks" value={data.clicks} />
                <StatCard title="Tickets sold" value={data.tickets_sold} />
                <StatCard
                  title="Revenue"
                  value={formatNgn(data.revenue_generated)}
                />
                <StatCard
                  title="Conversion"
                  value={formatPercent(data.conversion_rate)}
                />
                <StatCard
                  title="Commission owed"
                  value={formatNgn(data.commission_owed)}
                />
              </div>
              <div className="border-t border-border pt-4">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => void toggleStatus()}
                >
                  {data.ambassador.status === "active"
                    ? "Deactivate"
                    : "Activate"}
                </Button>
              </div>
            </Card>

            <Card className="space-y-4">
              <SectionHeader
                title="Attributed sales"
                description="Paid orders linked to this referral code."
              />
              {data.sales.length === 0 ? (
                <EmptyState
                  title="No attributed sales yet"
                  description="Share the referral link to start tracking partner conversions."
                />
              ) : (
                <ul className="divide-y divide-border">
                  {data.sales.map((sale) => (
                    <li
                      key={sale.id}
                      className="flex flex-wrap items-start justify-between gap-3 py-3 text-sm"
                    >
                      <div>
                        <p className="font-bold text-foreground">
                          {sale.event_title ?? "Event"} · {sale.order_reference}
                        </p>
                        <p className="text-muted-foreground">
                          {sale.tickets_sold} tickets ·{" "}
                          {formatNgn(sale.revenue_amount)}
                        </p>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {formatDateTime(sale.created_at)}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
