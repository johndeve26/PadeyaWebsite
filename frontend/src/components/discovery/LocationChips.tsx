"use client";

import Link from "next/link";

import { cn } from "@/lib/cn";
import { locationHubPath, type LocationKind } from "@/lib/taxonomy-api";

export type LocationChipItem = {
  kind: LocationKind | string;
  slug: string;
  name: string;
  href?: string;
};

export function LocationChips({
  items,
  active,
  onSelect,
  label = "Popular",
  showLabel = true,
  className = "",
  mode = "auto",
}: {
  items: LocationChipItem[];
  /** Highlight matching chip when using button mode. */
  active?: { kind: string; slug: string } | null;
  /** When set, chips act as buttons instead of links. */
  onSelect?: (item: LocationChipItem) => void;
  label?: string;
  showLabel?: boolean;
  className?: string;
  /** auto = button if onSelect else link */
  mode?: "auto" | "link" | "button";
}) {
  if (!items.length) return null;

  const useButton =
    mode === "button" || (mode === "auto" && Boolean(onSelect));

  return (
    <div className={cn("space-y-2.5", className)}>
      {showLabel ? (
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
          {label}
        </p>
      ) : null}
      <ul className="flex flex-wrap gap-2">
        {items.map((item) => {
          const isActive =
            active?.kind === item.kind && active?.slug === item.slug;
          const chipClass = cn(
            "inline-flex items-center rounded-full border px-3 py-1.5 text-sm font-semibold transition-colors",
            isActive
              ? "border-ink bg-ink text-paper"
              : "border-border bg-surface-muted text-foreground hover:border-border-strong/40 hover:bg-surface-elevated",
          );
          const key = `${item.kind}-${item.slug}`;
          const href =
            item.href || locationHubPath(item.kind, item.slug);

          return (
            <li key={key}>
              {useButton ? (
                <button
                  type="button"
                  onClick={() => onSelect?.(item)}
                  className={chipClass}
                >
                  {item.name}
                </button>
              ) : (
                <Link href={href} className={chipClass}>
                  {item.name}
                </Link>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
