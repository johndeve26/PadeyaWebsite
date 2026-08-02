"use client";

import Link from "next/link";

import { StatusBadge } from "@/components/events/StatusBadge";
import { Media } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { resolveEventImage } from "@/lib/legacy-presentation";

import { HostEventRowActions } from "./HostEventRowActions";
import {
  HostEventAmbassadorCell,
  HostEventCheckInCell,
  HostEventMerchCell,
  HostEventRevenueCell,
  HostEventSoldCell,
  HostEventSponsorCell,
  HostEventVisibilityCell,
} from "./HostEventOpsCells";
import type { HostEventsViewProps } from "./event-list-types";

const emptyCell = "text-muted-foreground";
const cellPad = "px-3 py-3.5";
const headPad = "px-3 py-3";

export function HostEventsTable({
  events,
  actions,
  metrics,
  metricsLoading,
  onView,
}: HostEventsViewProps) {
  const showOps = actions.showOpsMetrics;
  const canEdit = actions.canEdit && !actions.deskOnly;

  return (
    <div className="min-w-0 overflow-x-auto rounded-[var(--radius-lg)] border border-border bg-card shadow-[var(--shadow-soft)] dark:bg-surface-elevated">
      <table className="min-w-[720px] w-full text-left text-sm">
        <thead className="sticky top-0 z-10 border-b border-border bg-card/95 text-[11px] font-bold uppercase tracking-[0.08em] text-muted-foreground backdrop-blur-sm dark:bg-surface-elevated/95">
          <tr>
            <th className={`pl-4 ${headPad}`}>Event</th>
            <th className={headPad}>Status</th>
            <th className={headPad}>Date</th>
            <th className={`hidden ${headPad} lg:table-cell`}>City</th>
            <th className={`hidden ${headPad} xl:table-cell`}>Visibility</th>
            {showOps ? (
              <>
                <th className={`hidden ${headPad} md:table-cell`}>Sold</th>
                {actions.showFinance ? (
                  <th className={`hidden ${headPad} lg:table-cell`}>Revenue</th>
                ) : null}
                <th className={`hidden ${headPad} lg:table-cell`}>Check-in</th>
                <th className={`hidden ${headPad} xl:table-cell`}>Merch</th>
                <th className={`hidden ${headPad} xl:table-cell`}>Ambassadors</th>
                <th className={`hidden ${headPad} xl:table-cell`}>Sponsors</th>
              </>
            ) : null}
            <th className={`${headPad} pr-4 text-right`}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => {
            const rowMetrics = metrics[event.id];
            const image = resolveEventImage(
              event.slug,
              event.title,
              event.banner_url,
            );
            return (
              <tr
                key={event.id}
                className="group border-b border-border/70 transition-colors last:border-b-0 hover:bg-muted/35"
              >
                <td className={`pl-4 ${cellPad}`}>
                  <div className="flex min-w-[11rem] max-w-[18rem] items-center gap-3">
                    <div className="relative h-10 w-14 shrink-0 overflow-hidden rounded-[var(--radius-sm)] bg-surface-dark">
                      <Media
                        src={image}
                        alt=""
                        className="absolute inset-0 h-full w-full object-cover"
                      />
                    </div>
                    <div className="min-w-0">
                      <div className="flex min-w-0 items-center gap-2">
                        <Link
                          href={`/host/events/${event.id}`}
                          className="min-w-0 truncate font-semibold text-foreground group-hover:underline"
                          title="Open event hub"
                        >
                          {event.title}
                        </Link>
                        {canEdit && event.status === "completed" ? (
                          <Link
                            href={`/host/events/${event.id}/memory`}
                            className="shrink-0 rounded-full bg-primary px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.06em] text-primary-foreground shadow-[var(--shadow-soft)] transition-colors hover:bg-primary-hover"
                          >
                            Memories
                          </Link>
                        ) : canEdit ? (
                          <Link
                            href={`/host/events/${event.id}/edit`}
                            className="shrink-0 rounded-full bg-primary px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.06em] text-primary-foreground shadow-[var(--shadow-soft)] transition-colors hover:bg-primary-hover"
                          >
                            Edit
                          </Link>
                        ) : null}
                      </div>
                      {event.venue_name ? (
                        <p className="mt-0.5 truncate text-xs text-muted-foreground">
                          {event.venue_name}
                        </p>
                      ) : null}
                    </div>
                  </div>
                </td>
                <td className={cellPad}>
                  <StatusBadge status={event.status} />
                </td>
                <td className={`whitespace-nowrap ${cellPad} text-foreground`}>
                  {formatDateTime(event.start_datetime)}
                </td>
                <td className={`hidden ${cellPad} lg:table-cell`}>
                  <span className={event.city ? "text-foreground" : emptyCell}>
                    {event.city || "—"}
                  </span>
                </td>
                <td className={`hidden ${cellPad} xl:table-cell`}>
                  <HostEventVisibilityCell event={event} />
                </td>
                {showOps ? (
                  <>
                    <td className={`hidden ${cellPad} md:table-cell`}>
                      <HostEventSoldCell
                        event={event}
                        metrics={rowMetrics}
                        loading={metricsLoading}
                      />
                    </td>
                    {actions.showFinance ? (
                      <td className={`hidden ${cellPad} lg:table-cell`}>
                        <HostEventRevenueCell
                          event={event}
                          metrics={rowMetrics}
                          loading={metricsLoading}
                          showFinance
                        />
                      </td>
                    ) : null}
                    <td className={`hidden ${cellPad} lg:table-cell`}>
                      <HostEventCheckInCell
                        event={event}
                        metrics={rowMetrics}
                        loading={metricsLoading}
                      />
                    </td>
                    <td className={`hidden ${cellPad} xl:table-cell`}>
                      <HostEventMerchCell
                        event={event}
                        metrics={rowMetrics}
                        loading={metricsLoading}
                        canEditMerch={actions.canMerch}
                      />
                    </td>
                    <td className={`hidden ${cellPad} xl:table-cell`}>
                      <HostEventAmbassadorCell event={event} metrics={rowMetrics} />
                    </td>
                    <td className={`hidden ${cellPad} xl:table-cell`}>
                      <HostEventSponsorCell event={event} metrics={rowMetrics} />
                    </td>
                  </>
                ) : null}
                <td className={`whitespace-nowrap ${cellPad} pr-4 text-right`}>
                  <HostEventRowActions
                    event={event}
                    actions={actions}
                    onView={onView}
                    hideEdit={canEdit}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
