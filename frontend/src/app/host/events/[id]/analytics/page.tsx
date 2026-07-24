"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { EventAnalyticsDashboard } from "@/components/analytics/EventAnalyticsDashboard";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  exportHostEventAnalyticsCsv,
  fetchHostEventAnalyticsAmbassadors,
  fetchHostEventAnalyticsAudience,
  fetchHostEventAnalyticsFunnel,
  fetchHostEventAnalyticsOverview,
  fetchHostEventAnalyticsPromos,
  fetchHostEventAnalyticsSources,
  fetchHostEventAnalyticsTickets,
  fetchHostEventAnalyticsTimeseries,
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

export default function HostEventAnalyticsPage() {
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
    const [eventRow, overview, funnel, timeseries, sources, tickets, audience, promos, ambassadors] =
      await Promise.all([
        fetchEventById(params.id),
        fetchHostEventAnalyticsOverview(params.id, query),
        fetchHostEventAnalyticsFunnel(params.id, query),
        fetchHostEventAnalyticsTimeseries(params.id, query),
        fetchHostEventAnalyticsSources(params.id, query),
        fetchHostEventAnalyticsTickets(params.id, query),
        fetchHostEventAnalyticsAudience(params.id, query),
        fetchHostEventAnalyticsPromos(params.id, query),
        fetchHostEventAnalyticsAmbassadors(params.id, query),
      ]);
    setEvent(eventRow);
    setData({
      overview,
      funnel,
      timeseries,
      sources,
      tickets,
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
      await exportHostEventAnalyticsCsv(params.id, rangeToQuery(rangeKey));
      setExportNote("CSV downloaded.");
    } catch {
      setExportNote("Export failed — check permissions.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Insights"
        title="Event analytics"
        description="Funnel, sources, ticket performance, and trusted sales for this night."
        actions={
          <>
            <Link href="/host/analytics">
              <Button size="sm" variant="ghost">
                All analytics
              </Button>
            </Link>
            <Link href={`/host/events/${params.id}`}>
              <Button size="sm" variant="ghost">
                Event
              </Button>
            </Link>
            <Link href={`/host/events/${params.id}/check-in/analytics`}>
              <Button size="sm" variant="secondary">
                Door stats
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
        {!data && !error ? <SkeletonLoader lines={8} /> : null}
        {data && event ? (
          <EventAnalyticsDashboard
            mode="host"
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
    </RequireHost>
  );
}
