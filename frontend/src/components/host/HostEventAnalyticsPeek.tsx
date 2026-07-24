"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button, Modal, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchHostEventAnalyticsOverview } from "@/lib/analytics-api";
import { formatNgn, formatPercent } from "@/lib/format";
import type { EventAnalyticsOverview } from "@/lib/types/analytics";

type Props = {
  eventId: string;
  eventTitle: string;
  onClose: () => void;
};

function Metric({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="rounded-[var(--radius-md)] border border-border bg-muted/60 px-3 py-3 padeya-stat-surface">
      <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-xl font-extrabold tracking-tight text-foreground">
        {value}
      </p>
      {hint ? (
        <p className="mt-0.5 text-xs font-medium text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
}

/** Lightweight analytics snapshot modal for the host events list. */
export function HostEventAnalyticsPeek({
  eventId,
  eventTitle,
  onClose,
}: Props) {
  const [data, setData] = useState<EventAnalyticsOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    void fetchHostEventAnalyticsOverview(eventId)
      .then((overview) => {
        if (!active) return;
        setData(overview);
        setError(null);
      })
      .catch((err) => {
        if (!active) return;
        setError(
          err instanceof ApiError ? err.detail : "Could not load analytics",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [eventId]);

  const conv =
    data?.conversion_rates.view_to_purchase ??
    data?.conversion_rates.checkout_to_purchase;

  return (
    <Modal
      open
      onClose={onClose}
      title="Event snapshot"
      description={eventTitle}
      className="sm:max-w-xl"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
          <Link href={`/host/events/${eventId}/analytics`} onClick={onClose}>
            <Button variant="dark">Full analytics</Button>
          </Link>
        </>
      }
    >
      {loading ? <SkeletonLoader lines={5} /> : null}
      {error ? (
        <p className="text-sm font-medium text-danger">{error}</p>
      ) : null}
      {data ? (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Metric
              label="Views"
              value={data.event_detail_views}
              hint={`${data.unique_visitors} unique`}
            />
            <Metric
              label="Clicks"
              value={data.event_card_clicks}
              hint={
                data.impressions > 0
                  ? `${formatPercent((data.event_card_clicks / data.impressions) * 100)} CTR`
                  : undefined
              }
            />
            <Metric
              label="Sales"
              value={data.purchases}
              hint={`${data.tickets_sold} tickets`}
            />
            <Metric label="Impressions" value={data.impressions} />
            <Metric label="Checkouts" value={data.checkout_starts} />
            <Metric
              label="Revenue"
              value={formatNgn(data.revenue)}
              hint={
                conv != null ? `${formatPercent(conv)} view→buy` : undefined
              }
            />
          </div>
          <p className="text-xs leading-relaxed text-muted-foreground">
            Sales and revenue are trusted commerce totals. Views and clicks are
            first-party funnel signals
            {data.traffic_source === "rollup" ? " (from daily rollups)" : ""}.
          </p>
        </div>
      ) : null}
    </Modal>
  );
}
