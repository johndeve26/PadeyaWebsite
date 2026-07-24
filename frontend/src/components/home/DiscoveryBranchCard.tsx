import Link from "next/link";
import type { MouseEventHandler } from "react";

import { Media } from "@/components/ui";
import { cn } from "@/lib/cn";

export type DiscoveryBranchItem = {
  label: string;
  href: string;
  hint: string;
  image: string;
  count?: number | null;
  /** Unit for `count` — defaults to events (marketplace rails). */
  countNoun?: "event" | "host";
};

function monogram(label: string): string {
  const parts = label.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ""}${parts[1]![0] ?? ""}`.toUpperCase();
}

const cardClassName = cn(
  "group relative flex h-full min-h-[4.75rem] w-full items-center gap-3.5 overflow-hidden rounded-[var(--radius-md)] border border-border bg-card px-3.5 py-3 text-left",
  "dark:bg-surface-elevated dark:shadow-[var(--shadow-soft)]",
  "transition-[border-color,box-shadow,transform,background-color] duration-200",
  "hover:-translate-y-0.5 hover:border-border-strong/30 hover:bg-muted/40 hover:shadow-[var(--shadow-soft)]",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background",
);

function BranchCardInner({
  item,
  tone = "default",
}: {
  item: DiscoveryBranchItem;
  tone?: "default" | "accent";
}) {
  const hasCount = typeof item.count === "number" && item.count >= 0;
  const noun = item.countNoun ?? "event";
  const countLabel = hasCount
    ? `${item.count} ${item.count === 1 ? noun : `${noun}s`}`
    : null;
  const mark = monogram(item.label);

  return (
    <>
      <span
        className={cn(
          "relative flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-[var(--radius-sm)]",
          tone === "accent"
            ? "bg-accent text-primary-foreground"
            : "bg-ink text-accent",
        )}
      >
        {item.image ? (
          <>
            <Media
              src={item.image}
              alt=""
              className="absolute inset-0 h-full w-full object-cover opacity-55 transition-opacity duration-300 group-hover:opacity-70"
            />
            <span
              aria-hidden
              className="absolute inset-0 bg-gradient-to-br from-ink/55 via-transparent to-ink/40"
            />
          </>
        ) : null}
        <span className="relative text-sm font-extrabold tracking-tight">
          {mark}
        </span>
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-baseline justify-between gap-2">
          <span className="truncate text-[0.95rem] font-extrabold tracking-tight text-foreground">
            {item.label}
          </span>
          {countLabel ? (
            <span className="shrink-0 text-xs font-bold tabular-nums text-foreground/70">
              {countLabel}
            </span>
          ) : null}
        </span>
        <span className="mt-0.5 block truncate text-sm leading-snug text-muted-foreground">
          {item.hint}
        </span>
      </span>
      <span
        aria-hidden
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border text-sm font-bold text-foreground/40 transition-colors group-hover:border-accent group-hover:bg-accent group-hover:text-primary-foreground"
      >
        →
      </span>
    </>
  );
}

/** Compact taxonomy shortcut — monogram + art, one-line hint. */
export function DiscoveryBranchCard({
  item,
  className = "",
  onClick,
  pressed,
  tone = "default",
}: {
  item: DiscoveryBranchItem;
  className?: string;
  /** When set, renders a button (for in-page filters) instead of a link. */
  onClick?: MouseEventHandler<HTMLButtonElement>;
  pressed?: boolean;
  tone?: "default" | "accent";
}) {
  const classes = cn(
    cardClassName,
    pressed && "border-ink bg-muted/50 shadow-[var(--shadow-soft)]",
    className,
  );

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        aria-pressed={pressed}
        className={classes}
      >
        <BranchCardInner item={item} tone={tone} />
      </button>
    );
  }

  return (
    <Link href={item.href} className={classes}>
      <BranchCardInner item={item} tone={tone} />
    </Link>
  );
}
