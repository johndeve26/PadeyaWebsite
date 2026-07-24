import { cn } from "@/lib/cn";

/** Shared label style for Input / Textarea / Select. */
export const fieldLabelClass =
  "text-xs font-bold uppercase tracking-[0.08em] text-foreground";

/** Shared control chrome — theme-safe across light/dark. */
export function fieldControlClass({
  error,
  className = "",
}: {
  error?: boolean;
  className?: string;
} = {}) {
  return cn(
    "w-full rounded-[var(--radius-md)] border border-input-border bg-input-background text-sm text-input-foreground shadow-[var(--shadow-soft)]",
    "placeholder:text-placeholder",
    "transition-[border-color,box-shadow,background-color] duration-150",
    "focus:border-border-strong focus:outline-none focus:ring-2 focus:ring-focus-ring focus:ring-offset-2 focus:ring-offset-background",
    "disabled:cursor-not-allowed disabled:border-border disabled:bg-surface-muted disabled:text-muted-foreground disabled:opacity-80",
    "read-only:bg-surface-muted read-only:text-muted-foreground",
    error
      ? "border-danger focus:border-danger focus:ring-danger/40"
      : "hover:border-border-strong/50",
    className,
  );
}

export const fieldHintClass = "text-xs text-muted-foreground";
export const fieldErrorClass = "text-xs font-semibold text-danger";

/** Shared checkbox / radio accent chrome */
export const fieldChoiceClass = cn(
  "h-4 w-4 shrink-0 rounded border border-input-border bg-input-background text-primary",
  "accent-primary transition-colors",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
  "disabled:cursor-not-allowed disabled:border-border disabled:opacity-60",
);
