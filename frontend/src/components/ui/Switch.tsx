"use client";

import { cn } from "@/lib/cn";

export type SwitchProps = {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  id?: string;
  className?: string;
};

export function Switch({
  checked,
  onCheckedChange,
  label,
  description,
  disabled = false,
  id,
  className = "",
}: SwitchProps) {
  return (
    <div className={cn("flex items-start justify-between gap-4", className)}>
      {label || description ? (
        <div className="min-w-0 space-y-0.5">
          {label ? (
            <label
              htmlFor={id}
              className="text-sm font-semibold text-foreground"
            >
              {label}
            </label>
          ) : null}
          {description ? (
            <p className="text-xs text-muted-foreground">{description}</p>
          ) : null}
        </div>
      ) : null}
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onCheckedChange(!checked)}
        className={cn(
          "relative h-7 w-12 shrink-0 rounded-full border transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          "disabled:cursor-not-allowed disabled:opacity-50",
          checked
            ? "border-primary/50 bg-primary"
            : "border-border bg-surface-muted hover:border-border-strong/40",
        )}
      >
        <span
          aria-hidden
          className={cn(
            "absolute top-0.5 h-5 w-5 rounded-full bg-card shadow-[var(--shadow-soft)] transition-transform",
            "dark:bg-paper",
            checked ? "left-6" : "left-0.5",
          )}
        />
      </button>
    </div>
  );
}
