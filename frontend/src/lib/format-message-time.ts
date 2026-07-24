/**
 * Display-only chat timestamps. ISO instants from the API remain source of truth;
 * never persist or round-trip these labels.
 */

const LOCALE = "en-NG";

function asDate(value: string | Date | null | undefined): Date | null {
  if (value == null || value === "") return null;
  const d = typeof value === "string" ? new Date(value) : value;
  return Number.isNaN(d.getTime()) ? null : d;
}

function startOfLocalDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function calendarDayDiff(a: Date, b: Date): number {
  const ms = startOfLocalDay(a).getTime() - startOfLocalDay(b).getTime();
  return Math.round(ms / 86_400_000);
}

function formatClock(d: Date): string {
  return d.toLocaleTimeString(LOCALE, {
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatMonthDay(d: Date, withYear: boolean): string {
  return d.toLocaleDateString(LOCALE, {
    month: "short",
    day: "numeric",
    ...(withYear ? { year: "numeric" } : {}),
  });
}

/** Local calendar key for grouping (YYYY-MM-DD). */
export function messageDayKey(
  value: string | Date | null | undefined,
): string | null {
  const d = asDate(value);
  if (!d) return null;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Bubble timestamp. */
export function formatMessageSentAt(
  value: string | Date | null | undefined,
  now: Date = new Date(),
): string {
  const d = asDate(value);
  if (!d) return "";
  const diff = calendarDayDiff(now, d);
  const clock = formatClock(d);
  if (diff === 0) return clock;
  if (diff === 1) return `Yesterday, ${clock}`;
  const withYear = d.getFullYear() !== now.getFullYear();
  return `${formatMonthDay(d, withYear)}, ${clock}`;
}

/** Thread list relative stamp. */
export function formatThreadListTime(
  value: string | Date | null | undefined,
  now: Date = new Date(),
): string {
  const d = asDate(value);
  if (!d) return "";
  const diffMs = now.getTime() - d.getTime();
  const sec = Math.round(diffMs / 1000);
  if (sec < 45) return "now";
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m`;
  const hr = Math.round(min / 60);
  if (hr < 24 && calendarDayDiff(now, d) === 0) return `${hr}h`;
  if (calendarDayDiff(now, d) === 1) return "Yesterday";
  // Older than yesterday (or >24h spanning midnight): short calendar date.
  const withYear = d.getFullYear() !== now.getFullYear();
  return formatMonthDay(d, withYear);
}

/** Day separator label between message groups. */
export function formatMessageDaySeparator(
  value: string | Date | null | undefined,
  now: Date = new Date(),
): string {
  const d = asDate(value);
  if (!d) return "";
  const diff = calendarDayDiff(now, d);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  if (d.getFullYear() !== now.getFullYear()) {
    return formatMonthDay(d, true);
  }
  return d.toLocaleDateString(LOCALE, {
    weekday: "long",
    month: "short",
    day: "numeric",
  });
}
