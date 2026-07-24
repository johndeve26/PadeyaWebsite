"use client";

import Link from "next/link";

import { StatusBadge } from "@/components/events/StatusBadge";
import { Media } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatDateTime, formatNgn } from "@/lib/format";
import { formatEventVisibility } from "@/lib/host-events-list";
import { resolveEventImage } from "@/lib/legacy-presentation";

import { HostEventRowActions } from "./HostEventRowActions";
import type { HostEventsViewProps } from "./event-list-types";

export function HostEventsListView({
  events,
  actions,
  metrics,
  metricsLoading,
  onView,
}: HostEventsViewProps) {
  const showOps = actions.showOpsMetrics;
  const canEdit = actions.canEdit && !actions.deskOnly;

  return (
    <div className="space-y-4">
      {events.map((event) => {
        const rowMetrics = metrics[event.id];
        const image = resolveEventImage(
          event.slug,
          event.title,
          event.banner_url,
        );
        const sold = rowMetrics?.tickets_sold;
        const revenue = rowMetrics?.revenue;
        const merchCount = rowMetrics?.merch_product_count;

        return (
          <article
            key={event.id}
            className={cn(
              "min-w-0 rounded-[var(--radius-lg)] border border-border bg-card p-5 shadow-[var(--shadow-soft)]",
              "transition-colors hover:border-border-strong/35 dark:bg-surface-elevated sm:p-6",
            )}
          >
            <div className="flex min-w-0 flex-col gap-5 sm:flex-row sm:items-start sm:gap-6">
              <Link
                href={`/host/events/${event.id}`}
                className="relative h-20 w-full shrink-0 overflow-hidden rounded-[var(--radius-md)] bg-surface-dark sm:h-24 sm:w-36"
                title="Open event hub"
              >
                <Media
                  src={image}
                  alt=""
                  className="absolute inset-0 h-full w-full object-cover"
                />
              </Link>

              <div className="flex min-w-0 flex-1 flex-col gap-4">
                <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0 space-y-2">
                    <div className="flex min-w-0 flex-wrap items-center gap-2.5">
                      <Link
                        href={`/host/events/${event.id}`}
                        className="min-w-0 text-lg font-bold tracking-tight text-foreground hover:underline sm:text-xl"
                      >
                        {event.title}
                      </Link>
                      <StatusBadge status={event.status} />
                    </div>

                    <p className="text-sm leading-relaxed text-muted-foreground">
                      {formatDateTime(event.start_datetime)}
                      <span className="mx-2 text-border">·</span>
                      {event.city || event.venue_name || "Venue TBA"}
                      <span className="mx-2 text-border">·</span>
                      {formatEventVisibility(event.visibility)}
                    </p>

                    {canEdit ? (
                      <Link
                        href={`/host/events/${event.id}/edit`}
                        className="inline-flex w-fit rounded-full bg-primary px-3 py-1 text-[11px] font-bold uppercase tracking-[0.06em] text-primary-foreground shadow-[var(--shadow-soft)] transition-colors hover:bg-primary-hover"
                      >
                        Edit
                      </Link>
                    ) : null}
                  </div>

                  <div className="shrink-0 sm:pt-0.5">
                    <HostEventRowActions
                      event={event}
                      actions={actions}
                      onView={onView}
                      compact
                      hideEdit={canEdit}
                    />
                  </div>
                </div>

                {showOps ? (
                  <div className="flex flex-wrap gap-x-6 gap-y-2 border-t border-border/60 pt-4 text-sm">
                    <p className="text-muted-foreground">
                      Sold{" "}
                      <span className="font-semibold tabular-nums text-foreground">
                        {metricsLoading
                          ? "…"
                          : sold == null
                            ? "—"
                            : String(sold)}
                      </span>
                    </p>
                    {actions.showFinance ? (
                      <p className="text-muted-foreground">
                        Revenue{" "}
                        <span className="font-semibold tabular-nums text-foreground">
                          {metricsLoading
                            ? "…"
                            : revenue == null
                              ? "—"
                              : formatNgn(revenue)}
                        </span>
                      </p>
                    ) : null}
                    {actions.canMerch ? (
                      <p className="text-muted-foreground">
                        Merch{" "}
                        <span className="font-semibold tabular-nums text-foreground">
                          {metricsLoading
                            ? "…"
                            : merchCount == null
                              ? "—"
                              : String(merchCount)}
                        </span>
                      </p>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}
