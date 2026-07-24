/** Client-side calendar grouping for marketplace filter sync. */

import type { EventItem } from "@/lib/types/events";

export type CalendarDayBucket = {
  date: string;
  eventCount: number;
  events: EventItem[];
};

export function toMonthKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function parseMonthKey(month: string): { year: number; month: number } | null {
  const m = /^(\d{4})-(\d{2})$/.exec(month.trim());
  if (!m) return null;
  const year = Number(m[1]);
  const mon = Number(m[2]);
  if (year < 2000 || year > 2100 || mon < 1 || mon > 12) return null;
  return { year, month: mon };
}

export function shiftMonth(month: string, delta: number): string {
  const parsed = parseMonthKey(month);
  if (!parsed) return month;
  const d = new Date(parsed.year, parsed.month - 1 + delta, 1);
  return toMonthKey(d);
}

export function eventDateKey(event: EventItem): string | null {
  const t = Date.parse(event.start_datetime);
  if (!Number.isFinite(t)) return null;
  const d = new Date(t);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Group filtered events by local start date within a YYYY-MM month. */
export function groupEventsByDay(
  events: EventItem[],
  month: string,
): CalendarDayBucket[] {
  const parsed = parseMonthKey(month);
  if (!parsed) return [];
  const byDay = new Map<string, EventItem[]>();

  for (const event of events) {
    const key = eventDateKey(event);
    if (!key) continue;
    const [y, m] = key.split("-").map(Number);
    if (y !== parsed.year || m !== parsed.month) continue;
    const list = byDay.get(key) ?? [];
    list.push(event);
    byDay.set(key, list);
  }

  return Array.from(byDay.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, rows]) => {
      const sorted = [...rows].sort(
        (a, b) =>
          Number(b.featured) - Number(a.featured) ||
          Date.parse(a.start_datetime) - Date.parse(b.start_datetime),
      );
      return { date, eventCount: sorted.length, events: sorted };
    });
}

/** Build a full month grid (Sun–Sat) including leading/trailing padding days. */
export function buildMonthGrid(month: string): {
  year: number;
  month: number;
  cells: { date: string; inMonth: boolean }[];
} | null {
  const parsed = parseMonthKey(month);
  if (!parsed) return null;
  const { year, month: mon } = parsed;
  const first = new Date(year, mon - 1, 1);
  const daysInMonth = new Date(year, mon, 0).getDate();
  const startPad = first.getDay(); // 0 = Sunday
  const cells: { date: string; inMonth: boolean }[] = [];

  for (let i = 0; i < startPad; i++) {
    const d = new Date(year, mon - 1, 1 - (startPad - i));
    cells.push({ date: formatDateKey(d), inMonth: false });
  }
  for (let day = 1; day <= daysInMonth; day++) {
    cells.push({
      date: formatDateKey(new Date(year, mon - 1, day)),
      inMonth: true,
    });
  }
  while (cells.length % 7 !== 0) {
    const last = cells[cells.length - 1]!;
    const d = new Date(last.date + "T12:00:00");
    d.setDate(d.getDate() + 1);
    cells.push({ date: formatDateKey(d), inMonth: false });
  }

  return { year, month: mon, cells };
}

function formatDateKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function todayKey(now = new Date()): string {
  return formatDateKey(now);
}

export function monthLabel(month: string): string {
  const parsed = parseMonthKey(month);
  if (!parsed) return month;
  return new Date(parsed.year, parsed.month - 1, 1).toLocaleDateString(
    undefined,
    { month: "long", year: "numeric" },
  );
}

/** Sunday (local) of the week that contains `dateKey` (YYYY-MM-DD). */
export function sundayOf(dateKey: string): string {
  const base = new Date(dateKey + "T12:00:00");
  if (Number.isNaN(base.getTime())) return dateKey;
  const start = new Date(base);
  start.setDate(base.getDate() - start.getDay());
  return formatDateKey(start);
}

/** Shift a YYYY-MM-DD by `deltaDays` (local noon to avoid DST edges). */
export function shiftDateKey(dateKey: string, deltaDays: number): string {
  const d = new Date(dateKey + "T12:00:00");
  if (Number.isNaN(d.getTime())) return dateKey;
  d.setDate(d.getDate() + deltaDays);
  return formatDateKey(d);
}

/** Flat list of dates starting Sunday of `selected`, length `count`. */
export function weekStripDates(selected: string, count = 14): string[] {
  const startKey = sundayOf(selected);
  const start = new Date(startKey + "T12:00:00");
  if (Number.isNaN(start.getTime())) return [];
  const out: string[] = [];
  for (let i = 0; i < count; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    out.push(formatDateKey(d));
  }
  return out;
}

/**
 * Stacked week rows for the calendar day grid.
 * Each row is Sun–Sat starting at `windowStart` (expected to be a Sunday).
 */
export function weekGridRows(
  windowStart: string,
  weekCount: number,
): string[][] {
  const start = new Date(sundayOf(windowStart) + "T12:00:00");
  if (Number.isNaN(start.getTime()) || weekCount < 1) return [];
  const rows: string[][] = [];
  for (let w = 0; w < weekCount; w++) {
    const row: string[] = [];
    for (let d = 0; d < 7; d++) {
      const cell = new Date(start);
      cell.setDate(start.getDate() + w * 7 + d);
      row.push(formatDateKey(cell));
    }
    rows.push(row);
  }
  return rows;
}

/** True when `dateKey` falls in [windowStart, windowStart + weekCount*7). */
export function dateInWeekWindow(
  dateKey: string,
  windowStart: string,
  weekCount: number,
): boolean {
  if (weekCount < 1) return false;
  const start = sundayOf(windowStart);
  const end = shiftDateKey(start, weekCount * 7 - 1);
  return dateKey >= start && dateKey <= end;
}
