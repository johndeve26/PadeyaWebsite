"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminAnalyticsSubnav } from "@/components/analytics/AdminAnalyticsSubnav";
import { TrendPanel } from "@/components/analytics/TrendPanel";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  DataTable,
  FilterBar,
  SectionHeader,
  Select,
  SkeletonLoader,
  StatCard,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  exportAdminEventsLeaderboardCsv,
  fetchAdminChannelPerformance,
  fetchAdminEventCompare,
  fetchAdminEventLeaderboard,
  fetchAdminEventsAnalytics,
} from "@/lib/analytics-api";
import {
  rangeToQuery,
  type AnalyticsRangeKey,
} from "@/lib/analytics-range";
import { formatNgn, formatPercent } from "@/lib/format";
import type {
  AdminChannelPerformance,
  AdminEventCompare,
  AdminEventLeaderboardRow,
  AdminEventsSummary,
  EventAnalyticsOverview,
} from "@/lib/types/analytics";

type SortKey =
  | "revenue"
  | "impressions"
  | "detail_views"
  | "tickets_sold"
  | "purchases"
  | "conversion_rate";

function num(v: string | number | null | undefined): number {
  const n = Number(v ?? 0);
  return Number.isFinite(n) ? n : 0;
}

function pct(v: string | number | null | undefined): string {
  if (v == null || v === "") return "—";
  return formatPercent(v);
}

function EventLink({
  id,
  title,
}: {
  id: string;
  title: string;
}) {
  return (
    <Link
      href={`/admin/events/${id}/analytics`}
      className="font-semibold text-foreground underline decoration-accent underline-offset-2"
    >
      {title}
    </Link>
  );
}

export default function AdminEventsAnalyticsPage() {
  const searchParams = useSearchParams();
  const compareSeed = searchParams.get("compare");
  const [summary, setSummary] = useState<AdminEventsSummary | null>(null);
  const [board, setBoard] = useState<AdminEventLeaderboardRow[]>([]);
  const [channels, setChannels] = useState<AdminChannelPerformance | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rangeKey, setRangeKey] = useState<AnalyticsRangeKey>("90d");
  const [sortBy, setSortBy] = useState<SortKey>("revenue");
  const [selected, setSelected] = useState<string[]>([]);
  const [compare, setCompare] = useState<AdminEventCompare | null>(null);
  const [compareBusy, setCompareBusy] = useState(false);
  const [exportNote, setExportNote] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const query = rangeToQuery(rangeKey);
    const [eventsSummary, leaderboard, channelPerf] = await Promise.all([
      fetchAdminEventsAnalytics(),
      fetchAdminEventLeaderboard({ ...query, sort_by: sortBy, limit: 50 }),
      fetchAdminChannelPerformance(query),
    ]);
    setSummary(eventsSummary);
    setBoard(leaderboard.events);
    setChannels(channelPerf);
    setCompare(null);
    setSelected(compareSeed ? [compareSeed] : []);
  }, [rangeKey, sortBy, compareSeed]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  const topConverting = useMemo(() => {
    return [...board]
      .filter((e) => e.detail_views >= 5 && e.conversion_rate != null)
      .sort((a, b) => num(b.conversion_rate) - num(a.conversion_rate))
      .slice(0, 8);
  }, [board]);

  const lowConverting = useMemo(() => {
    return [...board]
      .filter((e) => e.detail_views >= 10 && e.conversion_rate != null)
      .sort((a, b) => num(a.conversion_rate) - num(b.conversion_rate))
      .slice(0, 8);
  }, [board]);

  const highImpressionLowSales = useMemo(() => {
    return [...board]
      .filter((e) => e.impressions >= 20 && e.purchases <= 1)
      .sort((a, b) => b.impressions - a.impressions)
      .slice(0, 8);
  }, [board]);

  function toggleSelect(id: string) {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 4) return prev;
      return [...prev, id];
    });
  }

  async function onCompare() {
    if (selected.length < 2) return;
    setCompareBusy(true);
    try {
      const result = await fetchAdminEventCompare(selected, rangeToQuery(rangeKey));
      setCompare(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Compare failed");
    } finally {
      setCompareBusy(false);
    }
  }

  async function onExport() {
    setExportNote(null);
    try {
      await exportAdminEventsLeaderboardCsv({
        ...rangeToQuery(rangeKey),
        sort_by: sortBy,
        limit: 200,
      });
      setExportNote("CSV downloaded.");
    } catch {
      setExportNote("Export failed — check permissions.");
    }
  }

  const leaderboardColumns = [
    {
      key: "pick",
      header: "",
      cell: (e: AdminEventLeaderboardRow) => (
        <input
          type="checkbox"
          checked={selected.includes(e.event_id)}
          onChange={() => toggleSelect(e.event_id)}
          aria-label={`Select ${e.title}`}
          className="h-4 w-4 accent-[color:var(--brand-green)]"
        />
      ),
    },
    {
      key: "t",
      header: "Event",
      cell: (e: AdminEventLeaderboardRow) => (
        <div className="space-y-0.5">
          <EventLink id={e.event_id} title={e.title} />
          <p className="text-xs text-muted-foreground">
            {e.host_display_name ?? "Host"}
          </p>
        </div>
      ),
    },
    {
      key: "i",
      header: "Impressions",
      cell: (e: AdminEventLeaderboardRow) => e.impressions,
    },
    {
      key: "v",
      header: "Views",
      cell: (e: AdminEventLeaderboardRow) => e.detail_views,
    },
    {
      key: "s",
      header: "Tickets",
      cell: (e: AdminEventLeaderboardRow) => e.tickets_sold,
    },
    {
      key: "r",
      header: "Revenue",
      cell: (e: AdminEventLeaderboardRow) => formatNgn(e.revenue),
    },
    {
      key: "c",
      header: "Conv.",
      cell: (e: AdminEventLeaderboardRow) => pct(e.conversion_rate),
    },
  ];

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin analytics"
      title="Events"
      description="Leaderboard, conversion outliers, channels, and city/category trends."
      actions={
        <>
          <Link href="/admin/events">
            <Button variant="secondary">Manage events</Button>
          </Link>
          <Button variant="dark" onClick={() => void onExport()}>
            Export CSV
          </Button>
        </>
      }
    >
      <AdminAnalyticsSubnav />

      {error ? (
        <Alert tone="danger" title="Could not load event analytics">
          {error}
        </Alert>
      ) : null}
      {exportNote ? (
        <Alert
          tone={exportNote.includes("fail") ? "warning" : "success"}
          title={exportNote.includes("fail") ? "Export issue" : "Export"}
        >
          {exportNote}
        </Alert>
      ) : null}

      <Alert tone="info" title="Suspicious traffic / bots">
        Bot traffic is excluded from reports by default. A dedicated suspicious
        traffic review queue is coming soon.
      </Alert>

      <FilterBar>
        <Select
          label="Date range"
          value={rangeKey}
          onChange={(e) => {
            setSummary(null);
            setBoard([]);
            setRangeKey(e.target.value as AnalyticsRangeKey);
          }}
        >
          <option value="7d">7 days</option>
          <option value="30d">30 days</option>
          <option value="90d">90 days</option>
          <option value="365d">12 months</option>
        </Select>
        <Select
          label="Sort leaderboard"
          value={sortBy}
          onChange={(e) => {
            setBoard([]);
            setSortBy(e.target.value as SortKey);
          }}
        >
          <option value="revenue">Revenue</option>
          <option value="impressions">Impressions</option>
          <option value="detail_views">Views</option>
          <option value="tickets_sold">Tickets sold</option>
          <option value="purchases">Purchases</option>
          <option value="conversion_rate">Conversion</option>
        </Select>
      </FilterBar>

      {!summary && !error ? <SkeletonLoader lines={6} /> : null}

      {summary ? (
        <div className="space-y-10">
          <StatCard title="Total events" value={summary.total_events} />

          <section className="space-y-4">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <SectionHeader
                title="Event leaderboard"
                description="Select up to 4 events to compare"
              />
              <Button
                size="sm"
                variant="secondary"
                disabled={selected.length < 2 || compareBusy}
                onClick={() => void onCompare()}
              >
                {compareBusy
                  ? "Comparing…"
                  : `Compare selected (${selected.length})`}
              </Button>
            </div>
            <DataTable
              rows={board}
              rowKey={(e) => e.event_id}
              emptyTitle="No event activity in this range"
              columns={leaderboardColumns}
            />
          </section>

          {compare && compare.events.length > 0 ? (
            <section className="space-y-4">
              <SectionHeader title="Event comparison" />
              <DataTable
                rows={compare.events}
                rowKey={(e: EventAnalyticsOverview) => e.event_id}
                columns={[
                  {
                    key: "t",
                    header: "Event",
                    cell: (e: EventAnalyticsOverview) => (
                      <EventLink id={e.event_id} title={e.title} />
                    ),
                  },
                  {
                    key: "i",
                    header: "Impressions",
                    cell: (e: EventAnalyticsOverview) => e.impressions,
                  },
                  {
                    key: "v",
                    header: "Views",
                    cell: (e: EventAnalyticsOverview) => e.event_detail_views,
                  },
                  {
                    key: "c",
                    header: "Checkout",
                    cell: (e: EventAnalyticsOverview) => e.checkout_starts,
                  },
                  {
                    key: "p",
                    header: "Purchases",
                    cell: (e: EventAnalyticsOverview) => e.purchases,
                  },
                  {
                    key: "r",
                    header: "Revenue",
                    cell: (e: EventAnalyticsOverview) => formatNgn(e.revenue),
                  },
                  {
                    key: "cr",
                    header: "Conv.",
                    cell: (e: EventAnalyticsOverview) =>
                      pct(e.conversion_rates.view_to_purchase),
                  },
                ]}
              />
            </section>
          ) : null}

          <div className="grid gap-6 lg:grid-cols-3">
            <section className="space-y-4">
              <SectionHeader
                title="Top converting"
                description="Min. 5 views"
              />
              <DataTable
                rows={topConverting}
                rowKey={(e) => e.event_id}
                emptyTitle="Not enough view data"
                columns={[
                  {
                    key: "t",
                    header: "Event",
                    cell: (e) => <EventLink id={e.event_id} title={e.title} />,
                  },
                  {
                    key: "c",
                    header: "Conv.",
                    cell: (e) => pct(e.conversion_rate),
                  },
                ]}
              />
            </section>
            <section className="space-y-4">
              <SectionHeader
                title="Low converting"
                description="Min. 10 views"
              />
              <DataTable
                rows={lowConverting}
                rowKey={(e) => e.event_id}
                emptyTitle="Not enough view data"
                columns={[
                  {
                    key: "t",
                    header: "Event",
                    cell: (e) => <EventLink id={e.event_id} title={e.title} />,
                  },
                  {
                    key: "c",
                    header: "Conv.",
                    cell: (e) => pct(e.conversion_rate),
                  },
                ]}
              />
            </section>
            <section className="space-y-4">
              <SectionHeader
                title="High reach, low sales"
                description="≥20 impressions, ≤1 purchase"
              />
              <DataTable
                rows={highImpressionLowSales}
                rowKey={(e) => e.event_id}
                emptyTitle="No outliers in range"
                columns={[
                  {
                    key: "t",
                    header: "Event",
                    cell: (e) => <EventLink id={e.event_id} title={e.title} />,
                  },
                  {
                    key: "i",
                    header: "Imp.",
                    cell: (e) => e.impressions,
                  },
                  {
                    key: "p",
                    header: "Buy",
                    cell: (e) => e.purchases,
                  },
                ]}
              />
            </section>
          </div>

          <section className="space-y-4">
            <SectionHeader
              title="Source / channel performance"
              description="Platform-wide attribution buckets"
            />
            <DataTable
              rows={channels?.buckets ?? []}
              rowKey={(b) => b.source_bucket}
              emptyTitle="No channel data yet"
              columns={[
                {
                  key: "s",
                  header: "Channel",
                  cell: (b) => (
                    <span className="font-semibold capitalize">
                      {b.source_bucket}
                    </span>
                  ),
                },
                { key: "i", header: "Impressions", cell: (b) => b.impressions },
                { key: "v", header: "Views", cell: (b) => b.detail_views },
                {
                  key: "c",
                  header: "Checkout",
                  cell: (b) => b.checkout_starts,
                },
                { key: "p", header: "Purchases", cell: (b) => b.purchases },
                {
                  key: "cr",
                  header: "Conv.",
                  cell: (b) =>
                    b.detail_views > 0
                      ? formatPercent((b.purchases / b.detail_views) * 100)
                      : "—",
                },
              ]}
            />
          </section>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="space-y-4">
              <SectionHeader title="By status" />
              <DataTable
                rows={summary.by_status}
                rowKey={(s) => s.status}
                emptyTitle="No status data"
                columns={[
                  {
                    key: "s",
                    header: "Status",
                    cell: (s) => <StatusBadge status={s.status} />,
                  },
                  { key: "c", header: "Count", cell: (s) => s.count },
                ]}
              />
            </section>
            <Card className="space-y-3 padeya-stat-surface">
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
                Drill into an event
              </p>
              <p className="text-sm text-muted-foreground">
                Open any event row for funnel, tickets, audience, and export.
              </p>
              <Link href="/admin/events">
                <Button size="sm" variant="secondary">
                  Browse all events
                </Button>
              </Link>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <TrendPanel
              title="Category trends"
              points={summary.category_trends.map((c) => ({
                label: c.category,
                value: c.events,
                display: String(c.events),
              }))}
              emptyTitle="No category trends yet"
            />
            <TrendPanel
              title="City trends"
              points={summary.city_trends.map((c) => ({
                label: c.city,
                value: c.events,
                display: String(c.events),
              }))}
              emptyTitle="No city trends yet"
            />
          </div>
        </div>
      ) : null}
    </DashboardShell>
  );
}
