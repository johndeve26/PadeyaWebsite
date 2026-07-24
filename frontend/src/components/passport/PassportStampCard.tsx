"use client";

import { cn } from "@/lib/cn";
import { formatDate } from "@/lib/format";
import type { FanBadge } from "@/lib/types/passport";

import { stampInitials, stampSourceForBadge } from "./badge-source";

type Props = {
  badge: FanBadge;
  emphasized?: boolean;
};

export function PassportStampCard({ badge, emphasized = false }: Props) {
  const source = stampSourceForBadge(badge);
  const initials = stampInitials(badge.name);
  const isMerch = source === "Merch" || emphasized;

  return (
    <article
      className={cn(
        "flex h-full flex-col gap-4 rounded-[var(--radius-xl)] border bg-card p-5 shadow-[var(--shadow-soft)]",
        isMerch ? "border-primary/40" : "border-border",
      )}
    >
      <div className="flex items-center gap-3">
        <div
          className={cn(
            "flex h-14 w-14 shrink-0 items-center justify-center rounded-full text-base font-extrabold",
            isMerch
              ? "bg-primary text-primary-foreground"
              : "bg-surface-muted text-foreground ring-1 ring-border",
          )}
        >
          {initials}
        </div>
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
            {source}
          </p>
          <h3 className="mt-0.5 line-clamp-2 text-base font-extrabold tracking-tight text-foreground">
            {badge.name}
          </h3>
        </div>
      </div>

      <p className="line-clamp-2 flex-1 text-sm leading-relaxed text-muted-foreground">
        {badge.description}
      </p>

      {badge.awarded_at ? (
        <p className="text-xs font-semibold text-muted-foreground">
          Earned {formatDate(badge.awarded_at)}
        </p>
      ) : null}
    </article>
  );
}
