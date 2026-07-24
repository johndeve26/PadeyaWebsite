import { type HTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export type CardProps = HTMLAttributes<HTMLDivElement> & {
  padded?: boolean;
  hover?: boolean;
  variant?: "default" | "muted" | "dark" | "accent";
};

const variants = {
  default: cn(
    "border-border bg-card text-card-foreground shadow-[var(--shadow-soft)]",
    "dark:border-border dark:bg-surface-elevated dark:shadow-[var(--shadow)]",
  ),
  muted:
    "border-border/60 bg-muted text-card-foreground dark:bg-surface-inset dark:border-border",
  dark: "border-paper/12 bg-ink text-paper shadow-[var(--shadow)]",
  accent: cn(
    "border-primary/40 text-card-foreground",
    "bg-[linear-gradient(135deg,color-mix(in_srgb,var(--primary)_14%,var(--card)),color-mix(in_srgb,var(--primary)_4%,var(--surface-elevated))_55%)]",
    "dark:border-primary/35",
  ),
};

export function Card({
  padded = true,
  hover = false,
  variant = "default",
  className = "",
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-lg)] border",
        variants[variant],
        padded ? "p-5 sm:p-6" : "",
        hover ? "padeya-card-hover" : "",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
