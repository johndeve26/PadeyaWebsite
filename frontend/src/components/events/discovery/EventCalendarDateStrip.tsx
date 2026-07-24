"use client";

import { useEffect, useState } from "react";

import { CalendarDayDensityDots } from "@/components/events/discovery/CalendarDayDensityDots";
import {
  calendarNavBtnClass,
  calendarStripDayClass,
} from "@/components/events/discovery/calendar-day-chrome";
import { cn } from "@/lib/cn";
import {
  dateInWeekWindow,
  sundayOf,
  shiftDateKey,
  todayKey,
  weekGridRows,
} from "@/lib/events/calendar-grouping";

/** Mobile: 2 weeks. md+: 3 weeks. Nav always advances by 1 week. */
const WEEK_COUNT_MOBILE = 2;
const WEEK_COUNT_DESKTOP = 3;
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MD_MIN = "(min-width: 768px)";

function ChevronIcon({ direction }: { direction: "left" | "right" }) {
  return (
    <svg aria-hidden viewBox="0 0 16 16" className="h-3.5 w-3.5" fill="none">
      <path
        d={
          direction === "left"
            ? "M10 3.5 5.5 8 10 12.5"
            : "M6 3.5 10.5 8 6 12.5"
        }
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function useVisibleWeekCount(): number {
  const [count, setCount] = useState(WEEK_COUNT_DESKTOP);

  useEffect(() => {
    const mq = window.matchMedia(MD_MIN);
    const sync = () =>
      setCount(mq.matches ? WEEK_COUNT_DESKTOP : WEEK_COUNT_MOBILE);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  return count;
}

/**
 * Stacked week grid (2 weeks on small screens, 3 on md+) for calendar discovery.
 * No horizontal overflow — seven equal day columns per row.
 */
export function EventCalendarDateStrip({
  selectedDate,
  onSelectDate,
  counts,
  onPrevWeek,
  onNextWeek,
  className = "",
}: {
  selectedDate: string;
  onSelectDate: (date: string) => void;
  /** Map of YYYY-MM-DD → event count */
  counts: Map<string, number>;
  onPrevWeek?: () => void;
  onNextWeek?: () => void;
  className?: string;
}) {
  const weekCount = useVisibleWeekCount();
  const [windowStart, setWindowStart] = useState(() => sundayOf(selectedDate));
  // Track props used to decide whether the visible week window must jump.
  // Adjust during render (React-recommended) instead of syncing in an effect.
  const [windowSyncKey, setWindowSyncKey] = useState(
    () => `${selectedDate}:${weekCount}`,
  );
  const nextSyncKey = `${selectedDate}:${weekCount}`;
  if (nextSyncKey !== windowSyncKey) {
    setWindowSyncKey(nextSyncKey);
    if (!dateInWeekWindow(selectedDate, windowStart, weekCount)) {
      setWindowStart(sundayOf(selectedDate));
    }
  }

  const today = todayKey();
  const rows = weekGridRows(windowStart, weekCount);

  function shiftWindow(direction: -1 | 1) {
    setWindowStart((start) => shiftDateKey(start, direction * 7));
    if (direction < 0) onPrevWeek?.();
    else onNextWeek?.();
  }

  const rangeEnd = shiftDateKey(windowStart, weekCount * 7 - 1);
  const startLabel = new Date(windowStart + "T12:00:00").toLocaleDateString(
    undefined,
    { month: "short", day: "numeric" },
  );
  const endLabel = new Date(rangeEnd + "T12:00:00").toLocaleDateString(
    undefined,
    { month: "short", day: "numeric", year: "numeric" },
  );
  const monthTitle = new Date(selectedDate + "T12:00:00").toLocaleDateString(
    undefined,
    { month: "long", year: "numeric" },
  );

  return (
    <div
      className={cn(
        "min-w-0 space-y-3 overflow-x-clip rounded-[var(--radius-xl)] border border-border/80",
        "bg-card p-3 shadow-[var(--shadow-soft)] dark:bg-surface-elevated sm:p-4",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0 space-y-0.5">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
            {weekCount} weeks
          </p>
          <p className="truncate text-base font-extrabold tracking-tight text-foreground sm:text-lg">
            {monthTitle}
          </p>
          <p className="truncate text-xs text-muted-foreground">
            {startLabel} – {endLabel}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <button
            type="button"
            aria-label="Previous week"
            onClick={() => shiftWindow(-1)}
            className={calendarNavBtnClass}
          >
            <ChevronIcon direction="left" />
          </button>
          <button
            type="button"
            aria-label="Next week"
            onClick={() => shiftWindow(1)}
            className={calendarNavBtnClass}
          >
            <ChevronIcon direction="right" />
          </button>
        </div>
      </div>

      <div
        className="min-w-0 space-y-1.5"
        role="listbox"
        aria-label="Select a date"
      >
        <div className="grid grid-cols-7 gap-1 sm:gap-1.5">
          {WEEKDAYS.map((d) => (
            <div
              key={d}
              className="px-0.5 text-center text-[9px] font-bold uppercase tracking-[0.1em] text-muted-foreground sm:text-[10px]"
            >
              {d}
            </div>
          ))}
        </div>

        {rows.map((week) => (
          <div
            key={week[0]}
            className="grid grid-cols-7 gap-1 sm:gap-1.5"
          >
            {week.map((date) => {
              const count = counts.get(date) ?? 0;
              const selected = date === selectedDate;
              const isToday = date === today;
              const dayNum = Number(date.slice(-2));
              const weekday = new Date(date + "T12:00:00").toLocaleDateString(
                undefined,
                { weekday: "short" },
              );
              const outsideSelectedMonth =
                date.slice(0, 7) !== selectedDate.slice(0, 7);

              return (
                <button
                  key={date}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  aria-label={
                    count
                      ? `${weekday} ${dayNum}, ${count} event${count === 1 ? "" : "s"}`
                      : `${weekday} ${dayNum}`
                  }
                  data-selected={selected ? "true" : "false"}
                  onClick={() => onSelectDate(date)}
                  className={cn(
                    calendarStripDayClass({
                      selected,
                      isToday,
                      hasEvents: count > 0,
                    }),
                    outsideSelectedMonth &&
                      !selected &&
                      "opacity-55 dark:opacity-50",
                  )}
                >
                  <span
                    className={cn(
                      "text-[9px] font-bold uppercase tracking-wide sm:text-[10px]",
                      selected
                        ? "text-paper/70"
                        : count > 0
                          ? "text-muted-foreground"
                          : "text-muted-foreground/70",
                    )}
                  >
                    {weekday.slice(0, 2)}
                  </span>
                  <span
                    className={cn(
                      "text-sm font-extrabold leading-none tabular-nums sm:text-base",
                      selected
                        ? "text-paper"
                        : isToday
                          ? "text-primary-text dark:text-primary"
                          : count > 0
                            ? "text-foreground"
                            : "text-muted-foreground/80",
                    )}
                  >
                    {dayNum}
                  </span>
                  <CalendarDayDensityDots count={count} selected={selected} />
                </button>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
