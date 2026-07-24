"use client";

import { useMemo, useState } from "react";

import { EventCalendarDateStrip } from "@/components/events/discovery/EventCalendarDateStrip";
import { EventCalendarDayPanel } from "@/components/events/discovery/EventCalendarDayPanel";
import { EventCalendarMonth } from "@/components/events/discovery/EventCalendarMonth";
import {
  eventDateKey,
  groupEventsByDay,
  shiftMonth,
  toMonthKey,
  todayKey,
} from "@/lib/events/calendar-grouping";
import type { EventItem } from "@/lib/types/events";

function findAdjacentDayWithEvents(
  selected: string,
  datesWithEvents: string[],
  direction: -1 | 1,
): string | null {
  if (!datesWithEvents.length) return null;
  if (direction < 0) {
    for (let i = datesWithEvents.length - 1; i >= 0; i--) {
      const d = datesWithEvents[i]!;
      if (d < selected) return d;
    }
    return null;
  }
  for (const d of datesWithEvents) {
    if (d > selected) return d;
  }
  return null;
}

/**
 * Calendar view for /events marketplace — groups already-filtered events
 * client-side so filters stay in sync.
 */
export function MarketplaceCalendarView({
  events,
  hasLocationFilter = false,
  dateFilterActive = false,
  onClearDateFilter,
}: {
  events: EventItem[];
  hasLocationFilter?: boolean;
  dateFilterActive?: boolean;
  onClearDateFilter?: () => void;
}) {
  const today = todayKey();
  const [month, setMonth] = useState(() => toMonthKey(new Date()));
  const [selectedDate, setSelectedDate] = useState(today);

  const days = useMemo(() => groupEventsByDay(events, month), [events, month]);
  const { counts, eventsByDate, sortedDates } = useMemo(() => {
    const eventMap = new Map<string, EventItem[]>();
    for (const event of events) {
      const key = eventDateKey(event);
      if (!key) continue;
      const list = eventMap.get(key) ?? [];
      list.push(event);
      eventMap.set(key, list);
    }
    for (const [, list] of eventMap) {
      list.sort(
        (a, b) =>
          Number(b.featured) - Number(a.featured) ||
          Date.parse(a.start_datetime) - Date.parse(b.start_datetime),
      );
    }
    const countMap = new Map<string, number>();
    for (const [date, list] of eventMap) {
      countMap.set(date, list.length);
    }
    const sorted = Array.from(eventMap.keys()).sort();
    return {
      counts: countMap,
      eventsByDate: eventMap,
      sortedDates: sorted,
    };
  }, [events]);

  // Keep selection in the active month when navigating months
  const effectiveDate = selectedDate.startsWith(month)
    ? selectedDate
    : (days[0]?.date ?? `${month}-01`);

  const selectedEvents = useMemo(() => {
    const bucket = days.find((d) => d.date === effectiveDate);
    if (bucket) return bucket.events;
    return eventsByDate.get(effectiveDate) ?? [];
  }, [days, eventsByDate, effectiveDate]);

  const adjacentPrev = useMemo(
    () => findAdjacentDayWithEvents(effectiveDate, sortedDates, -1),
    [effectiveDate, sortedDates],
  );
  const adjacentNext = useMemo(
    () => findAdjacentDayWithEvents(effectiveDate, sortedDates, 1),
    [effectiveDate, sortedDates],
  );

  const monthEmpty = days.length === 0;
  const emptyMonthMessage = hasLocationFilter
    ? "No events this month in this location."
    : "No events this month.";
  const emptyHint = "Try another city, category, or wider radius.";

  function selectDate(date: string) {
    setSelectedDate(date);
    setMonth(date.slice(0, 7));
  }

  function goToday() {
    const now = new Date();
    setMonth(toMonthKey(now));
    setSelectedDate(todayKey(now));
  }

  function shiftWeek(deltaDays: number) {
    const d = new Date(effectiveDate + "T12:00:00");
    d.setDate(d.getDate() + deltaDays);
    const next = toMonthKey(d);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    setSelectedDate(key);
    setMonth(next);
  }

  function changeMonth(delta: number) {
    const next = shiftMonth(month, delta);
    const nextDays = groupEventsByDay(events, next);
    setMonth(next);
    setSelectedDate(nextDays[0]?.date ?? `${next}-01`);
  }

  return (
    <div className="min-w-0 space-y-5 overflow-x-clip sm:space-y-6">
      {/* Desktop month grid */}
      <div className="hidden lg:block">
        <EventCalendarMonth
          month={month}
          days={days}
          selectedDate={effectiveDate}
          onSelectDate={(date) => {
            setSelectedDate(date);
            if (!date.startsWith(month)) {
              setMonth(date.slice(0, 7));
            }
          }}
          onPrevMonth={() => changeMonth(-1)}
          onNextMonth={() => changeMonth(1)}
          onToday={goToday}
        />
      </div>

      {/* Mobile / tablet date strip */}
      <div className="lg:hidden">
        <EventCalendarDateStrip
          selectedDate={effectiveDate}
          onSelectDate={selectDate}
          counts={counts}
          onPrevWeek={() => shiftWeek(-7)}
          onNextWeek={() => shiftWeek(7)}
        />
      </div>

      {monthEmpty ? (
        <div className="space-y-3 rounded-[var(--radius-xl)] border border-border/80 bg-card px-4 py-6 shadow-[var(--shadow-soft)] dark:bg-surface-elevated sm:px-5">
          <div className="space-y-1">
            <p className="text-sm font-semibold text-foreground">
              {emptyMonthMessage}
            </p>
            <p className="text-sm text-muted-foreground">{emptyHint}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {dateFilterActive && onClearDateFilter ? (
              <button
                type="button"
                onClick={onClearDateFilter}
                className="min-h-9 rounded-[var(--radius-md)] border border-border bg-surface-muted px-3 text-xs font-bold text-foreground transition hover:border-primary/40 dark:bg-surface-elevated"
              >
                Clear date filter
              </button>
            ) : null}
            <button
              type="button"
              onClick={goToday}
              className="min-h-9 rounded-[var(--radius-md)] border border-border bg-surface-muted px-3 text-xs font-bold text-foreground transition hover:border-primary/40 dark:bg-surface-elevated"
            >
              Jump to today
            </button>
          </div>
        </div>
      ) : (
        <EventCalendarDayPanel
          date={effectiveDate}
          events={selectedEvents}
          emptyMessage="No events on this day."
          adjacentPrev={adjacentPrev}
          adjacentNext={adjacentNext}
          onSelectDate={selectDate}
          dateFilterActive={dateFilterActive}
          onClearDateFilter={onClearDateFilter}
        />
      )}
    </div>
  );
}
