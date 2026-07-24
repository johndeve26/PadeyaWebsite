import { cn } from "@/lib/cn";

/** Shared calendar selection / density chrome — brand tokens only. */

export const calendarNavBtnClass = cn(
  "inline-flex h-9 w-9 shrink-0 items-center justify-center",
  "rounded-[var(--radius-md)] border border-border/80 bg-surface-muted",
  "text-foreground transition",
  "hover:border-primary/40 hover:bg-surface-inset",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
  "dark:bg-surface-elevated dark:hover:bg-surface-inset",
);

/** Day cell in the stacked week grid — equal column width, touch-friendly. */
export function calendarStripDayClass({
  selected,
  isToday,
  hasEvents,
}: {
  selected: boolean;
  isToday: boolean;
  hasEvents: boolean;
}) {
  return cn(
    "group relative flex min-h-[3.75rem] min-w-0 w-full flex-col items-center justify-between gap-0.5",
    "rounded-[var(--radius-md)] border px-0.5 py-1.5 transition sm:min-h-[4.25rem] sm:px-1 sm:py-2",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
    selected
      ? "border-primary/60 bg-ink text-paper shadow-[var(--shadow-soft)] ring-2 ring-primary/55 ring-offset-1 ring-offset-background sm:ring-offset-2 dark:bg-surface-elevated dark:text-paper dark:border-primary/50"
      : hasEvents
        ? "border-primary/45 bg-primary/[0.12] text-foreground shadow-[var(--shadow-soft)] hover:border-primary/55 hover:bg-primary/[0.16] dark:border-primary/50 dark:bg-primary/[0.14] dark:hover:bg-primary/[0.18]"
        : "border-border/45 bg-muted/35 text-muted-foreground/80 hover:border-border/65 hover:bg-surface-muted hover:text-muted-foreground dark:border-white/8 dark:bg-surface-elevated/55",
    hasEvents &&
      !selected &&
      "before:pointer-events-none before:absolute before:inset-x-1 before:top-0.5 before:h-0.5 before:rounded-full before:bg-primary/75 sm:before:inset-x-1.5",
    isToday && !selected && "border-primary/50 text-foreground",
    isToday && !selected && hasEvents && "border-primary/60",
  );
}

/** Month-grid day cell selection — elevated surface + accent ring, not lime text. */
export function calendarMonthDayClass({
  inMonth,
  selected,
  isToday,
  hasEvents,
}: {
  inMonth: boolean;
  selected: boolean;
  isToday: boolean;
  hasEvents: boolean;
}) {
  return cn(
    "group relative flex min-h-[10.5rem] flex-col gap-1.5 overflow-hidden border-b border-r border-border p-2 text-left transition sm:min-h-[12.5rem]",
    "focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring",
    !inMonth && "bg-muted/35 text-muted-foreground/45",
    inMonth &&
      !selected &&
      !hasEvents &&
      "bg-card/90 text-muted-foreground/85 hover:bg-surface-muted dark:bg-surface-elevated/75 dark:hover:bg-surface-inset/80",
    inMonth &&
      !selected &&
      hasEvents &&
      "bg-primary/[0.08] ring-1 ring-inset ring-primary/25 hover:bg-primary/[0.12] dark:bg-primary/[0.11] dark:ring-primary/35 dark:hover:bg-primary/[0.15]",
    selected &&
      "bg-surface-inset ring-2 ring-inset ring-primary/55 dark:bg-ink/80",
    isToday && inMonth && !selected && !hasEvents && "bg-surface-muted/90 dark:bg-surface-inset",
    isToday &&
      inMonth &&
      !selected &&
      hasEvents &&
      "bg-primary/[0.12] dark:bg-primary/[0.14]",
  );
}

export const calendarAgendaPriceClass =
  "text-xs font-semibold text-primary-text dark:text-primary";

export const calendarAgendaTitleClass =
  "truncate text-sm font-bold tracking-tight text-foreground transition-colors group-hover:text-primary-text dark:group-hover:text-primary";
