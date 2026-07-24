"use client";

import Link from "next/link";

import {
  calendarAgendaPriceClass,
  calendarAgendaTitleClass,
} from "@/components/events/discovery/calendar-day-chrome";
import { eventMapCardChrome } from "@/components/events/map/event-map-card-chrome";
import { Button, Media } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  isFreeEvent,
  minTicketPrice,
} from "@/lib/discovery/event-filters";
import { formatPublicPlaceLabel } from "@/lib/event-privacy";
import { formatNgn } from "@/lib/format";
import { resolveEventImage } from "@/lib/legacy-presentation";
import type { EventItem } from "@/lib/types/events";

function formatTime(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("en-NG", {
    hour: "numeric",
    minute: "2-digit",
  });
}

function priceLabel(event: EventItem): string {
  if (isFreeEvent(event)) return "Free";
  const min = minTicketPrice(event);
  if (min == null) return "See tickets";
  return `From ${formatNgn(min)}`;
}

function CalendarAgendaRow({ event }: { event: EventItem }) {
  const cover = resolveEventImage(
    event.slug,
    event.title,
    event.mobile_banner_url || event.banner_url,
    event.category?.name || event.category?.slug,
  );
  const place = formatPublicPlaceLabel(event);
  const time = formatTime(event.start_datetime);
  const href = `/events/${event.slug}`;

  return (
    <article className={eventMapCardChrome()}>
      <Link
        href={href}
        className="flex w-full min-w-0 gap-3 p-2.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        <div className="relative h-[4.5rem] w-[5.5rem] shrink-0 overflow-hidden rounded-[var(--radius-md)] bg-ink">
          {cover ? (
            <Media src={cover} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="padeya-hero-glow absolute inset-0 opacity-80" />
          )}
          {event.featured ? (
            <span className="absolute left-1 top-1 rounded-[3px] bg-primary px-1 py-px text-[8px] font-bold uppercase tracking-wide text-primary-foreground">
              Feat
            </span>
          ) : null}
        </div>
        <div className="min-w-0 flex-1 space-y-1 py-0.5">
          <p className={calendarAgendaTitleClass}>{event.title}</p>
          <p className="text-xs text-muted-foreground">
            {time || "Time TBA"}
            {place ? ` · ${place}` : ""}
          </p>
          <p className={calendarAgendaPriceClass}>{priceLabel(event)}</p>
        </div>
      </Link>
    </article>
  );
}

export function EventCalendarDayPanel({
  date,
  events,
  emptyMessage = "No events on this day.",
  className = "",
  adjacentPrev,
  adjacentNext,
  onSelectDate,
  onClearDateFilter,
  dateFilterActive = false,
}: {
  date: string | null;
  events: EventItem[];
  emptyMessage?: string;
  className?: string;
  /** Nearest prior day (in filtered set) with events. */
  adjacentPrev?: string | null;
  /** Nearest following day (in filtered set) with events. */
  adjacentNext?: string | null;
  onSelectDate?: (date: string) => void;
  onClearDateFilter?: () => void;
  dateFilterActive?: boolean;
}) {
  const label = date
    ? new Date(date + "T12:00:00").toLocaleDateString(undefined, {
        weekday: "long",
        month: "long",
        day: "numeric",
      })
    : "Select a day";

  const prevLabel = adjacentPrev
    ? new Date(adjacentPrev + "T12:00:00").toLocaleDateString(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
      })
    : null;
  const nextLabel = adjacentNext
    ? new Date(adjacentNext + "T12:00:00").toLocaleDateString(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
      })
    : null;

  return (
    <div
      className={cn(
        "min-w-0 space-y-4 rounded-[var(--radius-xl)] border border-border/80",
        "bg-card p-3 shadow-[var(--shadow-soft)] dark:bg-surface-elevated sm:p-5",
        className,
      )}
      aria-live="polite"
    >
      <div className="flex flex-wrap items-end justify-between gap-2 border-b border-border/70 pb-3">
        <div className="min-w-0 space-y-0.5">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
            Selected day
          </p>
          <h3 className="text-base font-extrabold tracking-tight text-foreground sm:text-lg">
            {label}
          </h3>
        </div>
        {events.length > 0 ? (
          <p className="text-sm font-medium text-muted-foreground">
            {events.length} event{events.length === 1 ? "" : "s"}
          </p>
        ) : null}
      </div>

      {events.length === 0 ? (
        <div className="space-y-3 px-0.5 py-2 sm:py-3">
          <div className="space-y-1">
            <p className="text-sm font-semibold text-foreground">
              {emptyMessage}
            </p>
            <p className="text-sm text-muted-foreground">
              Pick another day, or browse everything on Pàdéyá.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {adjacentPrev && onSelectDate ? (
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => onSelectDate(adjacentPrev)}
              >
                ← {prevLabel}
              </Button>
            ) : null}
            {adjacentNext && onSelectDate ? (
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => onSelectDate(adjacentNext)}
              >
                {nextLabel} →
              </Button>
            ) : null}
            {dateFilterActive && onClearDateFilter ? (
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={onClearDateFilter}
              >
                Clear date filter
              </Button>
            ) : null}
            <Link href="/events?view=list">
              <Button type="button" size="sm" variant="ghost">
                Browse all events
              </Button>
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-2.5">
          {events.map((event) => (
            <CalendarAgendaRow key={event.id} event={event} />
          ))}
        </div>
      )}
    </div>
  );
}
