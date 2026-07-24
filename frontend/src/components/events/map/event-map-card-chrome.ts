import { cn } from "@/lib/cn";

/** Price on map cards — contrast-safe on light surfaces; lime only in dark. */
export const eventMapPriceClass =
  "text-xs font-semibold text-primary-text dark:text-primary";

/** Title hover on map cards — same light/dark contrast split. */
export const eventMapTitleClass =
  "font-bold tracking-tight text-heading transition-colors group-hover:text-primary-text dark:group-hover:text-primary dark:text-paper";

/** Shared map-panel card chrome — ink-adjacent, theme-token based. */
export function eventMapCardChrome({
  selected = false,
  className = "",
}: {
  selected?: boolean;
  className?: string;
} = {}) {
  return cn(
    "group relative overflow-hidden rounded-[var(--radius-lg)] border transition-all duration-200",
    // Light: soft elevated surface (not flat directory white). Dark: ink panel by the map.
    "bg-surface-muted text-foreground",
    "dark:bg-ink dark:text-paper",
    selected
      ? "border-primary ring-1 ring-primary/45 bg-surface-inset dark:bg-surface-dark"
      : "border-border/80 hover:border-primary/40 dark:border-white/10 dark:hover:border-primary/45",
    className,
  );
}
