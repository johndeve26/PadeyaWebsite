import Link from "next/link";
import { type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { Card } from "./Card";

export type StatCardProps = {
  title: string;
  value: string | number;
  trend?: string;
  trendPositive?: boolean;
  hint?: string;
  href?: string;
  onClick?: () => void;
  active?: boolean;
  actionLabel?: string;
  className?: string;
  /** Optional sparkline heights 0–100; omit when no real trend data */
  sparkline?: number[];
  icon?: ReactNode;
};

export function StatCard({
  title,
  value,
  trend,
  trendPositive,
  hint,
  href,
  onClick,
  active = false,
  actionLabel,
  className = "",
  sparkline,
  icon,
}: StatCardProps) {
  const interactive = Boolean(href || onClick);
  const body = (
    <Card
      hover={interactive}
      className={cn(
        "relative overflow-hidden space-y-3 padeya-stat-surface",
        href || onClick ? "h-full" : "",
        active
          ? "border-primary/50 ring-1 ring-primary/40 dark:border-primary/40"
          : "",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
          {title}
        </p>
        {icon ? (
          <span className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] bg-muted text-xs font-bold text-foreground">
            {icon}
          </span>
        ) : null}
      </div>
      <p className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
        {value}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        {trend ? (
          <span
            className={cn(
              "text-xs font-bold",
              trendPositive === false ? "text-danger" : "text-success",
            )}
          >
            {trend}
          </span>
        ) : null}
        {hint ? <span className="text-sm text-muted-foreground">{hint}</span> : null}
        {actionLabel ? (
          <span className="text-xs font-semibold text-primary-text">{actionLabel}</span>
        ) : null}
      </div>
      {sparkline && sparkline.length > 0 ? (
        <div aria-hidden className="mt-1 flex h-8 items-end gap-0.5">
          {sparkline.map((h, i) => (
            <span
              key={i}
              className="w-1.5 rounded-sm bg-chart-4 opacity-80"
              style={{ height: `${Math.max(8, Math.min(100, h))}%` }}
            />
          ))}
        </div>
      ) : null}
    </Card>
  );

  if (href) {
    return (
      <Link href={href} className="block h-full">
        {body}
      </Link>
    );
  }
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        aria-pressed={active}
        className="block h-full w-full text-left"
      >
        {body}
      </button>
    );
  }
  return body;
}
