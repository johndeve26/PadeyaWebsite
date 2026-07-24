import { type ReactNode } from "react";

import { cn } from "@/lib/cn";
import { formatDate, formatNgn } from "@/lib/format";
import type { PromoCode } from "@/lib/types/promos";

import { Card } from "./Card";
import { StatusBadge } from "./StatusBadge";

function discountLabel(promo: PromoCode) {
  const value = Number(promo.discount_value);
  if (promo.discount_type === "percentage") {
    return `${value}% off`;
  }
  return `${formatNgn(value)} off`;
}

export function PromoCodeCard({
  promo,
  actions,
  meta,
  className = "",
}: {
  promo: PromoCode;
  actions?: ReactNode;
  meta?: ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="font-mono text-lg font-extrabold tracking-tight text-foreground">
            {promo.code}
          </p>
          <p className="text-sm font-semibold text-muted-foreground">
            {discountLabel(promo)}
          </p>
        </div>
        <StatusBadge status={promo.status} />
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
        <span>
          Used {promo.usage_count}
          {promo.usage_limit != null ? ` / ${promo.usage_limit}` : ""}
        </span>
        {promo.expires_at ? (
          <span>Expires {formatDate(promo.expires_at)}</span>
        ) : (
          <span>No expiry</span>
        )}
        {meta}
      </div>
      {actions ? (
        <div className="flex flex-wrap gap-2 border-t border-border pt-3">
          {actions}
        </div>
      ) : null}
    </Card>
  );
}
