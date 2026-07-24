import { type HTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type Tone =
  | "neutral"
  | "accent"
  | "dark"
  | "success"
  | "warning"
  | "danger"
  | "outline";

type Size = "sm" | "md";

export type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: Tone;
  size?: Size;
};

const toneClasses: Record<Tone, string> = {
  neutral:
    "bg-surface-muted text-foreground ring-1 ring-inset ring-border",
  accent:
    "bg-primary text-primary-foreground shadow-[0_0_0_1px_color-mix(in_srgb,var(--primary)_35%,transparent)]",
  dark: "bg-ink text-paper",
  success:
    "bg-success-surface text-success-foreground ring-1 ring-inset ring-success/45",
  warning:
    "bg-warning-surface text-warning-foreground ring-1 ring-inset ring-warning/45",
  danger:
    "bg-danger-surface text-danger-foreground ring-1 ring-inset ring-danger/45",
  outline: "bg-transparent text-foreground ring-1 ring-inset ring-border-strong/35",
};

const sizeClasses: Record<Size, string> = {
  sm: "px-2 py-0.5 text-[11px] tracking-[0.08em]",
  md: "px-2.5 py-1 text-xs tracking-[0.08em]",
};

export function Badge({
  tone = "neutral",
  size = "md",
  className = "",
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full font-bold uppercase",
        toneClasses[tone],
        sizeClasses[size],
        className,
      )}
      {...props}
    />
  );
}
