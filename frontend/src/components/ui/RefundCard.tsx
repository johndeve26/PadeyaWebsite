import { type ReactNode } from "react";

import { cn } from "@/lib/cn";
import { formatDateTime, formatNgn } from "@/lib/format";
import type { RefundRequest } from "@/lib/types/finance";

import { Card } from "./Card";
import { StatusBadge } from "./StatusBadge";

export function RefundCard({
  refund,
  actions,
  className = "",
}: {
  refund: RefundRequest;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <p className="text-lg font-extrabold tracking-tight text-foreground">
            {formatNgn(refund.requested_amount)}{" "}
            <span className="text-sm font-semibold text-muted-foreground">
              {refund.currency}
            </span>
          </p>
          <p className="text-sm font-semibold text-foreground">
            {refund.event_title ?? "Event"}
          </p>
          <p className="text-xs text-muted-foreground">
            {refund.order_reference ?? refund.order_id} ·{" "}
            {refund.refund_type.replace(/_/g, " ")}
          </p>
        </div>
        <StatusBadge status={refund.status} />
      </div>
      <p className="text-sm leading-relaxed text-muted-foreground">{refund.reason}</p>
      {refund.escalation_note ? (
        <p className="rounded-[var(--radius-sm)] bg-muted px-3 py-2 text-xs text-muted-foreground">
          Escalation: {refund.escalation_note}
        </p>
      ) : null}
      <p className="text-sm text-muted-foreground">
        Requested {formatDateTime(refund.created_at)}
      </p>
      {actions ? (
        <div className="flex flex-wrap gap-2 border-t border-border pt-3">
          {actions}
        </div>
      ) : null}
    </Card>
  );
}

/** Support queue alias — same entity until a dedicated case model exists. */
export function SupportCaseCard(props: {
  refund: RefundRequest;
  actions?: ReactNode;
  className?: string;
}) {
  return <RefundCard {...props} />;
}
