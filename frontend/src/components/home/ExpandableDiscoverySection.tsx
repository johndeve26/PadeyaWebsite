"use client";

import { useId, useState } from "react";

import {
  DiscoveryBranchCard,
  type DiscoveryBranchItem,
} from "@/components/home/DiscoveryBranchCard";
import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";

const VISIBLE_MOBILE = 2;
const VISIBLE_DESKTOP = 4;

export function ExpandableDiscoverySection({
  eyebrow,
  title,
  description,
  items,
  className = "",
  /** Compact mode: hide eyebrow/title block (parent already labels the rail). */
  compact = false,
  tone = "default",
}: {
  eyebrow: string;
  title: string;
  description: string;
  items: DiscoveryBranchItem[];
  className?: string;
  compact?: boolean;
  tone?: "default" | "accent";
}) {
  const [expanded, setExpanded] = useState(false);
  const panelId = useId();

  if (!items.length) return null;

  const canExpand = items.length > VISIBLE_MOBILE;
  const remaining = Math.max(0, items.length - VISIBLE_DESKTOP);

  return (
    <div className={cn(compact ? "space-y-3" : "space-y-4", className)}>
      {!compact ? (
        <div className="max-w-2xl space-y-1">
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
            {eyebrow}
          </p>
          <h3 className="text-lg font-extrabold tracking-tight text-foreground sm:text-xl">
            {title}
          </h3>
          <p className="max-w-xl text-sm leading-relaxed text-muted-foreground">
            {description}
          </p>
        </div>
      ) : null}

      <ul
        id={panelId}
        className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 xl:grid-cols-4"
      >
        {items.map((item, index) => {
          const hideMobile =
            !expanded && index >= VISIBLE_MOBILE && index < VISIBLE_DESKTOP;
          const hideAllCollapsed = !expanded && index >= VISIBLE_DESKTOP;
          return (
            <li
              key={`${item.href}-${item.label}`}
              className={cn(
                "h-full",
                hideAllCollapsed && "hidden",
                hideMobile && "hidden sm:block",
              )}
            >
              <DiscoveryBranchCard
                item={item}
                tone={index === 0 && !expanded ? "accent" : tone}
              />
            </li>
          );
        })}
      </ul>

      {canExpand ? (
        <div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            aria-expanded={expanded}
            aria-controls={panelId}
            className="font-semibold text-foreground"
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded
              ? "Show less"
              : remaining > 0
                ? `Show ${remaining} more`
                : "Show more"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
