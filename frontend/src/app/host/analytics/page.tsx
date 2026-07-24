"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { TrendPanel } from "@/components/analytics/TrendPanel";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  DataTable,
  SectionHeader,
  Select,
  SkeletonLoader,
  StatCard,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  exportHostAnalyticsCsv,
  fetchHostAnalytics,
  fetchHostEventAnalytics,
} from "@/lib/analytics-api";
import { fetchMyEvents } from "@/lib/events-api";
import { formatDateTime, formatNgn, formatPercent } from "@/lib/format";
import type {
  EventAnalyticsSummary,
  HostAnalyticsSummary,
} from "@/lib/types/analytics";
import type { EventItem } from "@/lib/types/events";

type EventRow = EventItem & {
  analytics: EventAnalyticsSummary | null;
};

const BATCH = 4;

async function loadEventAnalytics(
  events: EventItem[],
): Promise<Record<string, EventAnalyticsSummary>> {
  const out: Record<string, EventAnalyticsSummary> = {};
  for (let i = 0; i < events.length; i += BATCH) {
    const slice = events.slice(i, i + BATCH);
    const results = await Promise.all(
      slice.map(async (ev) => {
        try {
          return [ev.id, await fetchHostEventAnalytics(ev.id)] as const;
        } catch {
          return [ev.id, null] as const;
        }
      }),
    );
    for (const [id, summary] of results) {
      if (summary) out[id] = summary;
    }
  }
  return out;
}

export default function HostAnalyticsPage() {
  const router = useRouter();
  const [data, setData] = useState<HostAnalyticsSummary | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [eventStats, setEventStats] = useState<
    Record<string, EventAnalyticsSummary>
  >({});
  const [selectedEventId, setSelectedEventId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [exportNote, setExportNote] = useState<string | null>(null);
  const [eventsLoading, setEventsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const [summary, eventRows] = await Promise.all([
          fetchHostAnalytics(),
          fetchMyEvents(),
        ]);
        if (!active) return;
        setData(summary);
        const ranked = [...eventRows].sort((a, b) => {
          const at = a.start_datetime ? Date.parse(a.start_datetime) : 0;
          const bt = b.start_datetime ? Date.parse(b.start_datetime) : 0;
          return bt - at;
        });
        setEvents(ranked);
        if (ranked.length === 1) setSelectedEventId(ranked[0].id);
        setEventsLoading(false);
        const stats = await loadEventAnalytics(ranked);
        if (active) setEventStats(stats);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load analytics",
          );
          setEventsLoading(false);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const eventRows: EventRow[] = useMemo(
    () =>
      events.map((ev) => ({
        ...ev,
        analytics: eventStats[ev.id] ?? null,
      })),
    [events, eventStats],
  );

  async function onExport() {
    setExportNote(null);
    try {
      await exportHostAnalyticsCsv();
      setExportNote("CSV downloaded.");
    } catch {
      setExportNote("Export failed — check permissions.");
    }
  }

  function openEventAnalytics() {
    if (!selectedEventId) {
      setError("Select an event to view its analytics.");
      return;
    }
    router.push(`/host/events/${selectedEventId}/analytics`);
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Analytics"
        title="Host analytics"
        description="Portfolio totals across your events — or open any event for funnel, traffic, and ambassador detail."
        actions={
          <>
            <Link href="/host/earnings">
              <Button variant="secondary">Earnings</Button>
            </Link>
            <Button variant="secondary" onClick={() => void onExport()}>
              Export CSV
            </Button>
          </>
        }
      >
        {error ? (
          <Alert tone="danger" title="Unable to load analytics">
            {error}
          </Alert>
        ) : null}
        {exportNote ? (
          <Alert
            tone={exportNote.includes("failed") ? "warning" : "success"}
            title={
              exportNote.includes("failed") ? "Export issue" : "Export complete"
            }
          >
            {exportNote}
          </Alert>
        ) : null}

        <section className="mb-8 rounded-[var(--radius-lg)] border border-border bg-card p-4 sm:p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div className="min-w-0 flex-1 space-y-1">
              <h2 className="text-sm font-extrabold text-heading">
                Event analytics
              </h2>
              <p className="text-sm text-muted-foreground">
                Open a single event for page views, funnel, sources, tickets,
                promos, and ambassadors.
              </p>
            </div>
            <div className="flex w-full flex-col gap-2 sm:w-auto sm:min-w-[280px] sm:flex-row sm:items-end">
              <Select
                label="Event"
                value={selectedEventId}
                onChange={(e) => setSelectedEventId(e.target.value)}
                className="sm:min-w-[220px]"
              >
                <option value="">Select an event</option>
                {events.map((ev) => (
                  <option key={ev.id} value={ev.id}>
                    {ev.title}
                    {ev.status !== "published" ? ` (${ev.status})` : ""}
                  </option>
                ))}
              </Select>
              <Button
                variant="dark"
                disabled={!selectedEventId}
                onClick={openEventAnalytics}
              >
                View event analytics
              </Button>
            </div>
          </div>
        </section>

        {!data && !error ? <SkeletonLoader lines={6} /> : null}

        {data ? (
          <div className="space-y-10">
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard title="Tickets sold" value={data.tickets_sold} />
              <StatCard title="Revenue" value={formatNgn(data.revenue)} />
              <StatCard title="Check-ins" value={data.check_ins} />
              <StatCard title="No-shows" value={data.no_shows} />
              <StatCard title="Page views" value={data.page_views} />
              <StatCard title="Event clicks" value={data.event_clicks} />
              <StatCard
                title="Conversion"
                value={
                  data.conversion_rate != null
                    ? formatPercent(data.conversion_rate)
                    : "—"
                }
                hint={
                  data.conversion_rate == null ? "Not enough data" : undefined
                }
              />
              <StatCard
                title="Vault earnings"
                value={formatNgn(data.vault_earnings)}
              />
            </section>

            <section className="space-y-4">
              <SectionHeader
                title="By event"
                description="Per-event snapshot — open any row for the full event analytics dashboard."
              />
              {eventsLoading && eventRows.length === 0 ? (
                <SkeletonLoader lines={4} />
              ) : (
                <DataTable
                  rows={eventRows}
                  rowKey={(row) => row.id}
                  emptyTitle="No events yet"
                  emptyDescription="Create an event to see event-level analytics."
                  columns={[
                    {
                      key: "title",
                      header: "Event",
                      cell: (row) => (
                        <div className="min-w-0 space-y-1">
                          <Link
                            href={`/host/events/${row.id}/analytics`}
                            className="font-semibold text-foreground hover:underline"
                          >
                            {row.title}
                          </Link>
                          <div className="flex flex-wrap items-center gap-2">
                            <StatusBadge status={row.status} />
                            {row.start_datetime ? (
                              <span className="text-xs text-muted-foreground">
                                {formatDateTime(row.start_datetime)}
                              </span>
                            ) : null}
                          </div>
                        </div>
                      ),
                    },
                    {
                      key: "sold",
                      header: "Tickets",
                      cell: (row) => row.analytics?.tickets_sold ?? "—",
                    },
                    {
                      key: "rev",
                      header: "Revenue",
                      cell: (row) =>
                        row.analytics
                          ? formatNgn(row.analytics.revenue)
                          : "—",
                    },
                    {
                      key: "views",
                      header: "Views",
                      cell: (row) => row.analytics?.page_views ?? "—",
                    },
                    {
                      key: "clicks",
                      header: "Clicks",
                      cell: (row) => row.analytics?.clicks ?? "—",
                    },
                    {
                      key: "open",
                      header: "",
                      cell: (row) => (
                        <Link href={`/host/events/${row.id}/analytics`}>
                          <Button size="sm" variant="secondary">
                            Open
                          </Button>
                        </Link>
                      ),
                    },
                  ]}
                />
              )}
            </section>

            <TrendPanel
              title="Sales over time"
              description="Paid order totals by day in the selected range."
              points={data.sales_over_time.map((p) => ({
                label: p.date,
                value: Number(p.value),
                display: formatNgn(p.value),
              }))}
              emptyTitle="No paid orders in range"
            />

            <div className="grid gap-6 lg:grid-cols-2">
              <section className="space-y-4">
                <SectionHeader
                  title="Ticket types"
                  description="Sold volume and revenue"
                />
                <DataTable
                  rows={data.ticket_type_breakdown}
                  rowKey={(t) => `${t.ticket_type_id}-${t.name}`}
                  emptyTitle="No ticket breakdown yet"
                  columns={[
                    { key: "name", header: "Type", cell: (t) => t.name },
                    {
                      key: "sold",
                      header: "Sold",
                      cell: (t) => t.tickets_sold,
                    },
                    {
                      key: "rev",
                      header: "Revenue",
                      cell: (t) => formatNgn(t.revenue),
                    },
                  ]}
                />
              </section>
              <TrendPanel
                title="Legacy score trend"
                description="Composite score history when available."
                points={data.legacy_score_trend.map((p) => ({
                  label: p.date,
                  value: Number(p.value),
                  display: Number(p.value).toFixed(1),
                }))}
                emptyTitle="No score history yet"
              />
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <section className="space-y-4">
                <SectionHeader title="Promo performance" />
                <DataTable
                  rows={data.promo_performance}
                  rowKey={(p) => p.promo_code_id}
                  emptyTitle="No promo redemptions in range"
                  columns={[
                    { key: "code", header: "Code", cell: (p) => p.code },
                    {
                      key: "red",
                      header: "Redemptions",
                      cell: (p) => p.redemptions,
                    },
                    {
                      key: "disc",
                      header: "Discounted",
                      cell: (p) => formatNgn(p.discount_total),
                    },
                  ]}
                />
              </section>
              <section className="space-y-4">
                <SectionHeader title="Ambassador performance" />
                <DataTable
                  rows={data.ambassador_performance}
                  rowKey={(a) => a.ambassador_id}
                  emptyTitle="No ambassador activity in range"
                  columns={[
                    { key: "name", header: "Ambassador", cell: (a) => a.name },
                    { key: "clicks", header: "Clicks", cell: (a) => a.clicks },
                    {
                      key: "tix",
                      header: "Tickets",
                      cell: (a) => a.tickets_sold,
                    },
                    {
                      key: "rev",
                      header: "Revenue",
                      cell: (a) => formatNgn(a.revenue),
                    },
                  ]}
                />
              </section>
            </div>
          </div>
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
