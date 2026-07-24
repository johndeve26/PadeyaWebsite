import { cn } from "@/lib/cn";

const MAX_BADGE = 9;

function densityLabel(count: number): string {
  if (count > 99) return "99+";
  if (count > MAX_BADGE) return `${MAX_BADGE}+`;
  return String(count);
}

/**
 * Quick-read density indicator for calendar day cells — compact count badge.
 */
export function CalendarDayDensityDots({
  count,
  selected = false,
  className = "",
}: {
  count: number;
  selected?: boolean;
  className?: string;
}) {
  if (count <= 0) {
    return (
      <span
        className={cn("flex h-4 items-center justify-center", className)}
        aria-hidden
      >
        <span className="h-1 w-1 rounded-full bg-transparent" />
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex h-4 min-w-4 items-center justify-center rounded-full px-1",
        "text-[9px] font-extrabold leading-none tabular-nums",
        selected
          ? "bg-primary text-primary-foreground"
          : "bg-primary/25 text-primary-text ring-1 ring-inset ring-primary/30 dark:bg-primary/35 dark:text-primary dark:ring-primary/40",
        className,
      )}
      aria-hidden
    >
      {densityLabel(count)}
    </span>
  );
}
