"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { EventAnalyticsDashboard } from "@/components/analytics/EventAnalyticsDashboard";
import { EventOpsNav } from "@/components/host/EventOpsNav";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  exportAdminEventAnalyticsCsv,
  fetchAdminEventAnalyticsAmbassadors,
  fetchAdminEventAnalyticsAudience,
  fetchAdminEventAnalyticsBundle,
  fetchAdminEventAnalyticsPromos,
  fetchAdminEventAnalyticsTimeseries,
} from "@/lib/analytics-api";
import {
  rangeToQuery,
  type AnalyticsRangeKey,
} from "@/lib/analytics-range";
import { fetchEventById } from "@/lib/events-api";
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
import type { EventItem } from "@/lib/types/events";

type Bundle = {
  overview: EventAnalyticsOverview;
  funnel: EventAnalyticsFunnel;
  timeseries: EventAnalyticsTimeseries;
  sources: EventAnalyticsSources;
  tickets: EventAnalyticsTickets;
  audience: EventAnalyticsAudience;
  promos: EventAnalyticsPromos;
  ambassadors: EventAnalyticsAmbassadors;
};

export default function AdminEventAnalyticsPage() {
  const params = useParams<{ id: string }>();
  const [event, setEvent] = useState<EventItem | null>(null);
  const [data, setData] = useState<Bundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rangeKey, setRangeKey] = useState<AnalyticsRangeKey>("90d");
  const [exporting, setExporting] = useState(false);
  const [exportNote, setExportNote] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const query = rangeToQuery(rangeKey);
    const [eventRow, bundle, timeseries, audience, promos, ambassadors] =
      await Promise.all([
        fetchEventById(params.id),
        fetchAdminEventAnalyticsBundle(params.id, query),
        fetchAdminEventAnalyticsTimeseries(params.id, query),
        fetchAdminEventAnalyticsAudience(params.id, query),
        fetchAdminEventAnalyticsPromos(params.id, query),
        fetchAdminEventAnalyticsAmbassadors(params.id, query),
      ]);
    setEvent(eventRow);
    setData({
      overview: bundle.overview,
      funnel: bundle.funnel,
      sources: bundle.sources,
      tickets: bundle.tickets,
      timeseries,
      audience,
      promos,
      ambassadors,
    });
  }, [params.id, rangeKey]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof ApiError ? err.detail : "Failed to load analytics");
          setData(null);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  async function onExport() {
    setExporting(true);
    setExportNote(null);
    try {
      await exportAdminEventAnalyticsCsv(params.id, rangeToQuery(rangeKey));
      setExportNote("CSV downloaded.");
    } catch {
      setExportNote("Export failed — check permissions.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin analytics"
      title="Event analytics"
      description="Platform view of funnel, attribution, and trusted commerce for one event."
      actions={
        <>
          <Link href="/admin/events">
            <Button size="sm" variant="secondary">
              All events
            </Button>
          </Link>
          <Link href="/admin/analytics/events">
            <Button size="sm" variant="ghost">
              Events analytics
            </Button>
          </Link>
        </>
      }
    >
      {error ? (
        <Alert tone="danger" title="Unable to load analytics">
          {error}
        </Alert>
      ) : null}
      <EventOpsNav eventId={params.id} base="admin" />
      {!data && !error ? <SkeletonLoader lines={8} /> : null}
      {data && event ? (
        <EventAnalyticsDashboard
          mode="admin"
          eventId={event.id}
          eventTitle={event.title}
          eventStatus={event.status}
          eventDate={event.start_datetime}
          hostName={event.host_display_name}
          eventSlug={event.slug}
          rangeKey={rangeKey}
          onRangeChange={(key) => {
            setData(null);
            setRangeKey(key);
          }}
          overview={data.overview}
          funnel={data.funnel}
          timeseries={data.timeseries}
          sources={data.sources}
          tickets={data.tickets}
          audience={data.audience}
          promos={data.promos}
          ambassadors={data.ambassadors}
          onExport={onExport}
          exporting={exporting}
          exportNote={exportNote}
        />
      ) : null}
    </DashboardShell>
  );
}
