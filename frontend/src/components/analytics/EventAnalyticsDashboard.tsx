"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { AnalyticsFunnel } from "@/components/analytics/AnalyticsFunnel";
import { MultiMetricTrend } from "@/components/analytics/MultiMetricTrend";
import { TrendPanel } from "@/components/analytics/TrendPanel";
import {
  Alert,
  Button,
  Card,
  DataTable,
  EmptyState,
  SectionHeader,
  Select,
  StatCard,
  StatusBadge,
} from "@/components/ui";
import {
  ANALYTICS_RANGE_OPTIONS,
  type AnalyticsRangeKey,
} from "@/lib/analytics-range";
import { formatDateTime, formatNgn, formatPercent } from "@/lib/format";
import type {
  EventAnalyticsAmbassadors,
  EventAnalyticsAudience,
  EventAnalyticsFunnel,
  EventAnalyticsOverview,
  EventAnalyticsPromos,
  EventAnalyticsSources,
  EventAnalyticsTickets,
  EventAnalyticsTimeseries,
} from "@/lib/types/analytics";

export type EventAnalyticsDashboardProps = {
  mode: "host" | "admin";
  eventId: string;
  eventTitle: string;
  eventStatus?: string | null;
  eventDate?: string | null;
  hostName?: string | null;
  eventSlug?: string | null;
  rangeKey: AnalyticsRangeKey;
  onRangeChange: (key: AnalyticsRangeKey) => void;
  overview: EventAnalyticsOverview;
  funnel: EventAnalyticsFunnel;
  timeseries: EventAnalyticsTimeseries;
  sources: EventAnalyticsSources;
  tickets: EventAnalyticsTickets;
  audience: EventAnalyticsAudience;
  promos: EventAnalyticsPromos;
  ambassadors: EventAnalyticsAmbassadors;
  onExport: () => Promise<void>;
  exporting?: boolean;
  exportNote?: string | null;
};

function num(v: string | number | null | undefined): number {
  const n = Number(v ?? 0);
  return Number.isFinite(n) ? n : 0;
}

function pct(v: string | number | null | undefined): string {
  if (v == null || v === "") return "—";
  return formatPercent(v);
}

function hasTraffic(overview: EventAnalyticsOverview): boolean {
  return (
    overview.impressions > 0 ||
    overview.event_detail_views > 0 ||
    overview.checkout_starts > 0 ||
    overview.purchases > 0 ||
    overview.tickets_sold > 0
  );
}

export function EventAnalyticsDashboard({
  mode,
  eventId,
  eventTitle,
  eventStatus,
  eventDate,
  hostName,
  eventSlug,
  rangeKey,
  onRangeChange,
  overview,
  funnel,
  timeseries,
  sources,
  tickets,
  audience,
  promos,
  ambassadors,
  onExport,
  exporting = false,
  exportNote = null,
}: EventAnalyticsDashboardProps) {
  const [compareNote, setCompareNote] = useState<string | null>(null);
  const ctr = useMemo(() => {
    if (overview.impressions <= 0) return null;
    return (overview.event_card_clicks / overview.impressions) * 100;
  }, [overview.event_card_clicks, overview.impressions]);

  const conversion =
    overview.conversion_rates.view_to_purchase ??
    overview.conversion_rates.checkout_to_purchase;

  const shareHref = eventSlug ? `/events/${eventSlug}` : `/host/events/${eventId}`;
  const empty = !hasTraffic(overview);

  const sourceRows = sources.buckets.filter(
    (b) =>
      b.impressions + b.clicks + b.detail_views + b.checkout_starts + b.purchases > 0,
  );
  const campaignRows = (sources.utm_campaigns ?? []).filter(
    (c) =>
      (c.impressions ?? 0) +
        (c.clicks ?? 0) +
        (c.detail_views ?? 0) +
        (c.checkout_starts ?? 0) +
        (c.purchases ?? 0) >
      0,
  );

  function onCompareClick() {
    if (mode === "admin") {
      window.location.href = `/admin/analytics/events?compare=${encodeURIComponent(eventId)}`;
      return;
    }
    setCompareNote(
      "Host portfolio trends are on Host analytics. Cross-event compare is available to admins.",
    );
  }

  return (
    <div className="space-y-10">
      {/* Header meta + controls */}
      <Card className="space-y-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              {eventStatus ? <StatusBadge status={eventStatus} /> : null}
              <span className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                {mode === "admin" ? "Admin event analytics" : "Event analytics"}
              </span>
            </div>
            <h2 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
              {eventTitle}
            </h2>
            <p className="text-sm text-muted-foreground">
              {[eventDate ? formatDateTime(eventDate) : null, hostName ? `Host · ${hostName}` : null]
                .filter(Boolean)
                .join(" · ") || "Performance for the selected range"}
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <Select
              label="Date range"
              value={rangeKey}
              onChange={(e) => onRangeChange(e.target.value as AnalyticsRangeKey)}
              className="min-w-[140px]"
            >
              {ANALYTICS_RANGE_OPTIONS.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label}
                </option>
              ))}
            </Select>
            <Button
              variant="dark"
              size="sm"
              disabled={exporting}
              onClick={() => void onExport()}
            >
              {exporting ? "Exporting…" : "Export CSV"}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={onCompareClick}
            >
              Compare
            </Button>
          </div>
        </div>
        {compareNote ? (
          <Alert tone="info" title="Compare">
            {compareNote}
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
      </Card>

      {empty ? (
        <>
          <EmptyState
            title="No analytics yet"
            description="When guests discover and book this event, impressions, funnel steps, sales, and audience insights will appear here."
            action={
              <Link href={shareHref} target={eventSlug ? "_blank" : undefined}>
                <Button variant="dark">
                  {eventSlug ? "Open public event page" : "Back to event"}
                </Button>
              </Link>
            }
          />
          <Alert tone="info" title="Data quality">
            Revenue, ticket sales, check-ins, and reviews are trusted server-side
            events. Impressions and clicks are client-side and deduplicated.
            {overview.traffic_source === "rollup"
              ? " Funnel traffic is served from daily rollups."
              : " Funnel traffic is computed live from the analytics stream."}
          </Alert>
        </>
      ) : (
        <>
      {/* KPI overview */}
      <section className="space-y-4">
        <SectionHeader
          title="Overview"
          description="Reach, intent, and trusted commerce outcomes"
        />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <StatCard title="Impressions" value={overview.impressions} hint={`${overview.unique_impressions} unique`} />
          <StatCard title="Event views" value={overview.event_detail_views} hint={`${overview.unique_visitors} unique`} />
          <StatCard title="CTR" value={ctr != null ? formatPercent(ctr) : "—"} hint="Clicks / impressions" />
          <StatCard title="Checkout starts" value={overview.checkout_starts} />
          <StatCard title="Purchases" value={overview.purchases} />
          <StatCard title="Tickets sold" value={overview.tickets_sold} />
          <StatCard title="Revenue" value={formatNgn(overview.revenue)} hint={overview.average_order_value != null ? `AOV ${formatNgn(overview.average_order_value)}` : undefined} />
          <StatCard title="Conversion" value={pct(conversion)} hint="Views → purchase" />
          <StatCard title="Check-ins" value={overview.check_in_count} hint={overview.check_in_rate != null ? pct(overview.check_in_rate) : undefined} />
          <StatCard
            title="Reviews"
            value={overview.review_count}
            hint={overview.average_rating != null ? `${num(overview.average_rating).toFixed(1)} avg` : undefined}
          />
        </div>
      </section>

      <AnalyticsFunnel funnel={funnel} />

      <MultiMetricTrend
        points={timeseries.points}
        granularity={timeseries.granularity}
      />

      {/* Sources */}
      <section className="space-y-4">
        <SectionHeader
          title="Sources & channels"
          description="Where discovery and purchases come from"
        />
        <DataTable
          rows={sourceRows}
          rowKey={(r) => r.source_bucket}
          emptyTitle="No attributed traffic yet"
          emptyDescription="UTM and channel buckets fill in as guests arrive with source data."
          columns={[
            {
              key: "s",
              header: "Source",
              cell: (r) => (
                <span className="font-semibold capitalize">{r.source_bucket}</span>
              ),
            },
            { key: "i", header: "Impressions", cell: (r) => r.impressions },
            { key: "v", header: "Views", cell: (r) => r.detail_views },
            { key: "c", header: "Checkout", cell: (r) => r.checkout_starts },
            { key: "p", header: "Purchases", cell: (r) => r.purchases },
            {
              key: "r",
              header: "Revenue",
              cell: (r) => formatNgn(r.revenue),
            },
            {
              key: "cr",
              header: "Conv.",
              cell: (r) =>
                r.detail_views > 0
                  ? formatPercent((r.purchases / r.detail_views) * 100)
                  : "—",
            },
          ]}
        />
        {campaignRows.length > 0 ? (
          <DataTable
            rows={campaignRows}
            rowKey={(r) =>
              `${r.source ?? "x"}|${r.medium ?? "x"}|${r.campaign ?? "x"}|${r.impressions}|${r.detail_views}|${r.purchases}`
            }
            emptyTitle="No campaigns"
            columns={[
              {
                key: "camp",
                header: "Campaign",
                cell: (r) => (
                  <span className="font-semibold">
                    {r.campaign || "(none)"}
                    <span className="mt-0.5 block text-xs font-medium text-muted-foreground">
                      {[r.source, r.medium].filter(Boolean).join(" · ") || "direct"}
                    </span>
                  </span>
                ),
              },
              { key: "i", header: "Impressions", cell: (r) => r.impressions },
              { key: "v", header: "Views", cell: (r) => r.detail_views },
              { key: "c", header: "Checkout", cell: (r) => r.checkout_starts },
              { key: "p", header: "Purchases", cell: (r) => r.purchases },
            ]}
          />
        ) : null}
      </section>

      {/* Ticket types */}
      <section className="space-y-4">
        <SectionHeader
          title="Ticket type performance"
          description="Impressions, selections, sell-through, and revenue by type"
        />
        <DataTable
          rows={tickets.ticket_types}
          rowKey={(t) => t.ticket_type_id}
          emptyTitle="No ticket types"
          columns={[
            {
              key: "n",
              header: "Ticket type",
              cell: (t) => <span className="font-semibold">{t.name}</span>,
            },
            { key: "pr", header: "Price", cell: (t) => formatNgn(t.price) },
            { key: "i", header: "Impressions", cell: (t) => t.impressions },
            { key: "sel", header: "Selections", cell: (t) => t.selections },
            { key: "s", header: "Sold", cell: (t) => t.sold },
            { key: "r", header: "Revenue", cell: (t) => formatNgn(t.revenue) },
            {
              key: "st",
              header: "Sell-through",
              cell: (t) => pct(t.sell_through_rate),
            },
            {
              key: "cr",
              header: "Conv.",
              cell: (t) => pct(t.conversion_rate),
            },
          ]}
        />
      </section>

      {/* Promos + ambassadors */}
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="space-y-4">
          <SectionHeader title="Promo performance" />
          <DataTable
            rows={promos.promos}
            rowKey={(p) => p.promo_code_id}
            emptyTitle="No promo redemptions"
            emptyDescription="Applied codes will show uses and discount totals here."
            columns={[
              {
                key: "c",
                header: "Code",
                cell: (p) => <span className="font-semibold">{p.code}</span>,
              },
              { key: "u", header: "Uses", cell: (p) => p.redemptions },
              { key: "o", header: "Orders", cell: (p) => p.orders },
              {
                key: "d",
                header: "Discount",
                cell: (p) => formatNgn(p.discount_total),
              },
            ]}
          />
        </section>
        <section className="space-y-4">
          <SectionHeader
            title="Ambassador performance"
            description="Attributed sales and commission owed from referral bookings"
          />
          <DataTable
            rows={ambassadors.ambassadors}
            rowKey={(a) => a.ambassador_id}
            emptyTitle="No ambassador sales"
            emptyDescription="Referral clicks and attributed sales appear once ambassadors drive bookings."
            columns={[
              {
                key: "n",
                header: "Ambassador",
                cell: (a) => (
                  <span className="font-semibold">
                    {a.name}
                    <span className="mt-0.5 block text-xs font-medium text-muted-foreground">
                      @{a.referral_code}
                    </span>
                  </span>
                ),
              },
              { key: "c", header: "Clicks", cell: (a) => a.clicks },
              { key: "t", header: "Tickets", cell: (a) => a.tickets_sold },
              { key: "r", header: "Sales", cell: (a) => formatNgn(a.revenue) },
              {
                key: "cr",
                header: "Conv.",
                cell: (a) => pct(a.conversion_rate),
              },
              {
                key: "cm",
                header: "Commission",
                cell: (a) => formatNgn(a.commission_owed ?? 0),
              },
            ]}
          />
        </section>
      </div>

      {/* Audience */}
      <section className="space-y-4">
        <SectionHeader
          title="Audience insights"
          description="Who is discovering and buying"
        />
        <div className="grid gap-4 lg:grid-cols-2">
          <TrendPanel
            title="Devices"
            points={audience.devices.map((d) => ({
              label: d.key,
              value: d.visitors,
              display: `${d.visitors} visitors`,
            }))}
            emptyTitle="No device data"
          />
          <TrendPanel
            title="Cities"
            points={audience.cities.slice(0, 8).map((d) => ({
              label: d.key,
              value: d.visitors,
              display: `${d.visitors}`,
            }))}
            emptyTitle="No city data"
          />
          <TrendPanel
            title="Countries"
            points={audience.countries.slice(0, 8).map((d) => ({
              label: d.key,
              value: d.visitors,
              display: `${d.visitors}`,
            }))}
            emptyTitle="No country data"
          />
          <TrendPanel
            title="New vs returning"
            points={audience.new_vs_returning.map((d) => ({
              label: d.key,
              value: d.visitors,
              display: `${d.visitors} · ${d.purchases} buyers`,
            }))}
            emptyTitle="No visitor cohorts yet"
          />
          <TrendPanel
            title="Logged-in vs anonymous"
            points={audience.auth_status.map((d) => ({
              label: d.key.replace("_", " "),
              value: d.visitors,
              display: `${d.visitors}`,
            }))}
            emptyTitle="No auth split yet"
          />
          {audience.follower_conversion ? (
            <Card className="space-y-3 padeya-stat-surface">
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
                Follower conversion
              </p>
              <p className="text-2xl font-extrabold tracking-tight text-foreground">
                {audience.follower_conversion.follower_buyers} /{" "}
                {audience.follower_conversion.buyers}
              </p>
              <p className="text-sm text-muted-foreground">
                Buyers who follow this host
                {audience.follower_conversion.rate != null
                  ? ` · ${pct(audience.follower_conversion.rate)}`
                  : ""}
              </p>
            </Card>
          ) : null}
        </div>
      </section>

      <Alert tone="info" title="Data quality">
        Revenue, ticket sales, check-ins, and reviews are trusted server-side
        events. Impressions and clicks are client-side and deduplicated.
      </Alert>
        </>
      )}
    </div>
  );
}
