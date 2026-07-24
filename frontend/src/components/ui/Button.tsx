import { type ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type Variant =
  | "primary"
  | "secondary"
  | "ghost"
  | "ghost-dark"
  | "dark"
  | "outline-dark"
  | "danger";
type Size = "sm" | "md" | "lg";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
};

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-primary text-primary-foreground shadow-[var(--shadow-soft)] hover:bg-primary-hover hover:shadow-[var(--shadow-glow)] active:translate-y-px focus-visible:ring-focus-ring",
  secondary:
    "bg-surface-elevated text-foreground border border-border shadow-[var(--shadow-soft)] hover:border-border-strong/50 hover:bg-surface-muted active:bg-surface-muted focus-visible:ring-focus-ring",
  ghost:
    "bg-transparent text-foreground hover:bg-surface-muted active:bg-surface-inset focus-visible:ring-focus-ring",
  "ghost-dark":
    "bg-transparent text-paper/80 hover:bg-paper/5 hover:text-paper active:bg-paper/10 focus-visible:ring-focus-ring",
  dark:
    "bg-ink text-paper shadow-[var(--shadow-soft)] hover:bg-surface-dark hover:shadow-[var(--shadow)] active:translate-y-px focus-visible:ring-focus-ring",
  "outline-dark":
    "bg-transparent text-paper border border-paper/40 hover:border-primary hover:text-primary active:bg-paper/5 focus-visible:ring-focus-ring",
  danger:
    "bg-danger text-paper shadow-[var(--shadow-soft)] hover:bg-[color-mix(in_srgb,var(--danger)_88%,var(--ink))] active:translate-y-px focus-visible:ring-danger dark:text-ink dark:hover:text-ink",
};

const sizeClasses: Record<Size, string> = {
  sm: "h-9 min-h-9 px-3.5 text-sm rounded-[var(--radius-sm)]",
  md: "h-11 min-h-11 px-5 text-sm rounded-[var(--radius-md)]",
  lg: "h-12 min-h-12 px-7 text-base rounded-[var(--radius-md)]",
};

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex cursor-pointer items-center justify-center gap-2 font-semibold tracking-tight transition-all duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-55 disabled:saturate-50",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    />
  );
}
