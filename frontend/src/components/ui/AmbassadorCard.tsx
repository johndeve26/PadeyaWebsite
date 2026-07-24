import Link from "next/link";
import { type ReactNode } from "react";

import { cn } from "@/lib/cn";
import { formatNgn } from "@/lib/format";
import type { Ambassador } from "@/lib/types/promos";

import { Card } from "./Card";
import { StatusBadge } from "./StatusBadge";

export function AmbassadorCard({
  ambassador,
  href,
  actions,
  className = "",
}: {
  ambassador: Ambassador;
  href?: string;
  actions?: ReactNode;
  className?: string;
}) {
  const titleClass =
    "block text-lg font-extrabold tracking-tight text-foreground";

  return (
    <Card className={cn("space-y-4", className)}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          {href ? (
            <Link href={href} className={cn(titleClass, "hover:underline")}>
              {ambassador.display_name}
            </Link>
          ) : (
            <p className={titleClass}>{ambassador.display_name}</p>
          )}
          <p className="font-mono text-sm text-muted-foreground">
            {ambassador.referral_code}
          </p>
          {ambassador.program_kind === "open_event" ? (
            <p className="text-sm text-muted-foreground">
              Open · {ambassador.event_title || "Event Ambassadors"}
            </p>
          ) : ambassador.event_title ? (
            <p className="text-sm text-muted-foreground">
              Event · {ambassador.event_title}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">
              Host partner · All events
            </p>
          )}
          {ambassador.email ? (
            <p className="text-sm text-muted-foreground">{ambassador.email}</p>
          ) : null}
        </div>
        <StatusBadge status={ambassador.status} />
      </div>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          {
            label: "Total clicks",
            value: ambassador.total_clicks ?? ambassador.clicks,
          },
          {
            label: "Unique clicks",
            value: ambassador.unique_clicks ?? ambassador.clicks,
          },
          { label: "Orders", value: ambassador.tickets_sold + (ambassador.merch_units_sold ?? 0) },
          {
            label: "Revenue",
            value: formatNgn(ambassador.revenue_generated),
          },
        ].map((stat) => (
          <div key={stat.label} className="space-y-0.5">
            <dt className="text-[11px] font-bold uppercase tracking-[0.1em] text-muted-foreground">
              {stat.label}
            </dt>
            <dd className="text-sm font-extrabold text-foreground">
              {stat.value ?? 0}
            </dd>
          </div>
        ))}
      </dl>
      {actions ? (
        <div className="flex flex-wrap gap-2 border-t border-border pt-3">
          {actions}
        </div>
      ) : null}
    </Card>
  );
}
