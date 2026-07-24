"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { HostEventAnalyticsPeek } from "@/components/host/HostEventAnalyticsPeek";
import { HostEventRowActions } from "@/components/host/events/HostEventRowActions";
import type { EventRowActions } from "@/components/host/events/event-list-types";
import { StatusBadge } from "@/components/events/StatusBadge";
import {
  Button,
  ConfirmAction,
  Media,
} from "@/components/ui";
import { fetchHostEventAnalyticsOverview } from "@/lib/analytics-api";
import { cn } from "@/lib/cn";
import { formatDateTime, formatNgn } from "@/lib/format";
import { resolveEventImage } from "@/lib/legacy-presentation";
import type { EventItem } from "@/lib/types/events";

type Props = {
  event: EventItem;
  deletable: boolean;
  discardable: boolean;
  /** When false, hide Edit and other destructive studio actions. */
  editable?: boolean;
  canCheckIn?: boolean;
  /**
   * Permission flags shared with table/list.
   * Required for scanner-only / merch-only / desk-focused grid safety.
   */
  rowActions?: EventRowActions;
  onView: () => void;
  onDelete: () => Promise<void>;
};

type PeekMetrics = {
  views: number;
  clicks: number;
  sales: number;
  revenue: string | number;
};

function MetricChip({
  label,
  value,
  loading,
}: {
  label: string;
  value: string;
  loading?: boolean;
}) {
  return (
    <div className="min-w-[4.5rem]">
      <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
        {label}
      </p>
      <p
        className={cn(
          "mt-0.5 text-sm font-extrabold tabular-nums text-foreground",
          loading && "animate-pulse text-muted-foreground",
        )}
      >
        {loading ? "…" : value}
      </p>
    </div>
  );
}

export function HostEventListCard({
  event,
  deletable,
  discardable,
  editable = true,
  canCheckIn = true,
  rowActions,
  onView,
  onDelete,
}: Props) {
  const [peekOpen, setPeekOpen] = useState(false);
  const [metrics, setMetrics] = useState<PeekMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(true);

  const deskConstrained = Boolean(
    rowActions?.scannerOnly || rowActions?.merchOnly || rowActions?.deskOnly,
  );
  const showStudioActions = editable && !deskConstrained;
  const image = resolveEventImage(event.slug, event.title, event.banner_url);

  useEffect(() => {
    // Desk / scanner / merch grid must not fetch portfolio analytics or revenue.
    if (deskConstrained) return;

    let active = true;
    void fetchHostEventAnalyticsOverview(event.id)
      .then((overview) => {
        if (!active) return;
        setMetrics({
          views: overview.event_detail_views,
          clicks: overview.event_card_clicks,
          sales: overview.purchases,
          revenue: overview.revenue,
        });
      })
      .catch(() => {
        if (active) setMetrics(null);
      })
      .finally(() => {
        if (active) setMetricsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [event.id, deskConstrained]);

  return (
    <>
      <article className="group padeya-card-hover overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow-soft)]">
        <div className="flex flex-col lg:flex-row">
          <div className="relative aspect-[16/10] w-full shrink-0 overflow-hidden bg-surface-dark sm:aspect-[21/9] lg:aspect-auto lg:w-56 xl:w-64">
            <Media
              src={image}
              alt=""
              className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03] lg:static lg:min-h-[168px]"
            />
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 bg-gradient-to-t from-ink/55 via-ink/10 to-transparent lg:bg-gradient-to-r lg:from-transparent lg:via-transparent lg:to-ink/25"
            />
            <div className="absolute left-3 top-3 lg:hidden">
              <StatusBadge status={event.status} />
            </div>
          </div>

          <div className="flex min-w-0 flex-1 flex-col gap-4 p-5 sm:p-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0 space-y-2">
                <div className="hidden lg:block">
                  <StatusBadge status={event.status} />
                </div>
                <div className="flex min-w-0 flex-wrap items-center gap-2">
                  <h3 className="min-w-0 text-balance text-xl font-extrabold tracking-tight text-foreground sm:text-2xl">
                    {event.title}
                  </h3>
                  {showStudioActions ? (
                    <Link
                      href={`/host/events/${event.id}/edit`}
                      className="shrink-0 rounded-full bg-primary px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.06em] text-primary-foreground shadow-[var(--shadow-soft)] transition-colors hover:bg-primary-hover"
                    >
                      Edit
                    </Link>
                  ) : null}
                </div>
                <p className="text-sm font-medium text-muted-foreground">
                  {formatDateTime(event.start_datetime)}
                  <span className="mx-1.5 text-border">·</span>
                  {event.city || "Venue TBA"}
                </p>
              </div>

              {!deskConstrained ? (
                <div className="flex shrink-0 gap-4 rounded-[var(--radius-md)] border border-border bg-muted/50 px-4 py-3 padeya-stat-surface sm:gap-5">
                  <MetricChip
                    label="Views"
                    value={metrics ? String(metrics.views) : "—"}
                    loading={metricsLoading}
                  />
                  <MetricChip
                    label="Clicks"
                    value={metrics ? String(metrics.clicks) : "—"}
                    loading={metricsLoading}
                  />
                  <MetricChip
                    label="Sales"
                    value={metrics ? String(metrics.sales) : "—"}
                    loading={metricsLoading}
                  />
                  <div className="hidden border-l border-border pl-4 sm:block">
                    <MetricChip
                      label="Revenue"
                      value={metrics ? formatNgn(metrics.revenue) : "—"}
                      loading={metricsLoading}
                    />
                  </div>
                </div>
              ) : null}
            </div>

            <div className="flex flex-col gap-2 border-t border-border/80 pt-4 sm:flex-row sm:flex-wrap sm:items-center">
              {deskConstrained ? (
                // Same permission matrix as table/list — never fall back to studio CTAs.
                rowActions ? (
                  <HostEventRowActions
                    event={event}
                    actions={rowActions}
                    onView={() => onView()}
                  />
                ) : null
              ) : (
                <>
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    className="w-full sm:w-auto"
                    onClick={onView}
                  >
                    View
                  </Button>
                  <Link href={`/host/events/${event.id}`}>
                    <Button size="sm" variant="dark" className="w-full sm:w-auto">
                      {editable ? "Manage" : "Open"}
                    </Button>
                  </Link>
                  {showStudioActions ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      className="w-full sm:w-auto"
                      onClick={() => setPeekOpen(true)}
                    >
                      Analytics
                    </Button>
                  ) : null}
                  {showStudioActions ? (
                    <Link href={`/host/events/${event.id}/edit`}>
                      <Button size="sm" variant="ghost" className="w-full sm:w-auto">
                        Edit
                      </Button>
                    </Link>
                  ) : null}
                  {showStudioActions ? (
                    <Link href={`/host/events/${event.id}/tickets`}>
                      <Button size="sm" variant="ghost" className="w-full sm:w-auto">
                        Tickets
                      </Button>
                    </Link>
                  ) : null}
                  {canCheckIn ? (
                    <Link href={`/host/events/${event.id}/check-in`}>
                      <Button size="sm" variant="ghost" className="w-full sm:w-auto">
                        Check-in
                      </Button>
                    </Link>
                  ) : null}
                  {deletable && showStudioActions ? (
                    <ConfirmAction
                      label="Delete"
                      title={
                        discardable
                          ? "Delete this event permanently?"
                          : "Cancel and remove this listing?"
                      }
                      description={
                        discardable
                          ? "Draft and rejected events with no sales are permanently deleted. This cannot be undone."
                          : "Events that are live or in review are cancelled (not hard-deleted) so ticket and payment history stay intact."
                      }
                      confirmLabel={discardable ? "Delete forever" : "Cancel event"}
                      tone="danger"
                      variant="ghost"
                      size="sm"
                      onConfirm={onDelete}
                    />
                  ) : null}
                </>
              )}
            </div>
          </div>
        </div>
      </article>

      {peekOpen && !deskConstrained ? (
        <HostEventAnalyticsPeek
          key={event.id}
          eventId={event.id}
          eventTitle={event.title}
          onClose={() => setPeekOpen(false)}
        />
      ) : null}
    </>
  );
}
