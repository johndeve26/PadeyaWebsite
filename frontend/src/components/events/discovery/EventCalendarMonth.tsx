"use client";

import { CalendarDayDensityDots } from "@/components/events/discovery/CalendarDayDensityDots";
import { CalendarDayEventThumbs } from "@/components/events/discovery/CalendarDayEventThumbs";
import {
  calendarMonthDayClass,
  calendarNavBtnClass,
} from "@/components/events/discovery/calendar-day-chrome";
import { cn } from "@/lib/cn";
import {
  buildMonthGrid,
  monthLabel,
  todayKey,
  type CalendarDayBucket,
} from "@/lib/events/calendar-grouping";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

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

export function EventCalendarMonth({
  month,
  days,
  selectedDate,
  onSelectDate,
  onPrevMonth,
  onNextMonth,
  onToday,
  className = "",
}: {
  month: string;
  days: CalendarDayBucket[];
  selectedDate: string | null;
  onSelectDate: (date: string) => void;
  onPrevMonth: () => void;
  onNextMonth: () => void;
  onToday?: () => void;
  className?: string;
}) {
  const grid = buildMonthGrid(month);
  const byDate = new Map(days.map((d) => [d.date, d]));
  const today = todayKey();

  if (!grid) return null;

  return (
    <div className={cn("min-w-0 space-y-4", className)}>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0 space-y-0.5">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
            Month
          </p>
          <h3 className="text-xl font-extrabold tracking-tight text-foreground sm:text-2xl">
            {monthLabel(month)}
          </h3>
        </div>
        <div className="flex items-center gap-1.5">
          {onToday ? (
            <button
              type="button"
              onClick={onToday}
              className={cn(
                "min-h-9 rounded-[var(--radius-md)] border border-border/80 bg-surface-muted px-3",
                "text-xs font-bold text-foreground transition",
                "hover:border-primary/40 hover:bg-surface-inset",
                "dark:bg-surface-elevated",
              )}
            >
              Today
            </button>
          ) : null}
          <button
            type="button"
            aria-label="Previous month"
            onClick={onPrevMonth}
            className={calendarNavBtnClass}
          >
            <ChevronIcon direction="left" />
          </button>
          <button
            type="button"
            aria-label="Next month"
            onClick={onNextMonth}
            className={calendarNavBtnClass}
          >
            <ChevronIcon direction="right" />
          </button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-[var(--radius-xl)] border border-border/80 bg-card shadow-[var(--shadow-soft)] dark:bg-surface-elevated">
        <div className="grid min-w-[36rem] grid-cols-7 border-b border-border bg-surface-muted/60 dark:bg-surface-inset/80">
          {WEEKDAYS.map((d) => (
            <div
              key={d}
              className="px-2 py-2.5 text-center text-[10px] font-bold uppercase tracking-[0.12em] text-muted-foreground"
            >
              {d}
            </div>
          ))}
        </div>
        <div className="grid min-w-[36rem] grid-cols-7">
          {grid.cells.map((cell) => {
            const bucket = byDate.get(cell.date);
            const count = bucket?.eventCount ?? 0;
            const selected = selectedDate === cell.date;
            const isToday = cell.date === today;
            const dayEvents = bucket?.events ?? [];

            return (
              <button
                key={cell.date}
                type="button"
                disabled={!cell.inMonth}
                onClick={() => onSelectDate(cell.date)}
                aria-pressed={selected}
                aria-label={
                  count
                    ? `${cell.date}, ${count} event${count === 1 ? "" : "s"}`
                    : cell.date
                }
                className={calendarMonthDayClass({
                  inMonth: cell.inMonth,
                  selected,
                  isToday,
                  hasEvents: count > 0,
                })}
              >
                <div className="flex shrink-0 items-center justify-between gap-1">
                  <span
                    className={cn(
                      "inline-flex h-7 min-w-7 items-center justify-center rounded-full text-xs font-extrabold tabular-nums",
                      selected &&
                        "bg-ink text-paper ring-2 ring-primary/60 dark:bg-paper dark:text-ink",
                      isToday &&
                        !selected &&
                        "text-primary-text dark:text-primary",
                      !selected &&
                        !isToday &&
                        cell.inMonth &&
                        count > 0 &&
                        "text-foreground",
                      !selected &&
                        !isToday &&
                        cell.inMonth &&
                        count === 0 &&
                        "text-muted-foreground/75",
                    )}
                  >
                    {Number(cell.date.slice(-2))}
                  </span>
                  {count > 0 ? (
                    <CalendarDayDensityDots count={count} selected={selected} />
                  ) : (
                    <span className="h-4 w-4 shrink-0" aria-hidden />
                  )}
                </div>
                {dayEvents.length ? (
                  <CalendarDayEventThumbs
                    events={dayEvents}
                    variant="month"
                    className="min-h-0 flex-1"
                  />
                ) : null}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
