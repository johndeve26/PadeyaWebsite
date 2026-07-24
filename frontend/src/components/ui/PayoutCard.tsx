import { type ReactNode } from "react";

import { cn } from "@/lib/cn";
import { formatDateTime, formatNgn } from "@/lib/format";
import type { PayoutRequest } from "@/lib/types/finance";

import { Card } from "./Card";
import { StatusBadge } from "./StatusBadge";

export function PayoutCard({
  payout,
  showHost = false,
  actions,
  className = "",
}: {
  payout: PayoutRequest;
  showHost?: boolean;
  actions?: ReactNode;
  className?: string;
}) {
  const bank = payout.recipient_bank_snapshot ?? {};

  return (
    <Card className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-xl font-extrabold tracking-tight text-foreground">
            {formatNgn(payout.amount)}
          </p>
          {showHost && payout.host_display_name ? (
            <p className="text-sm font-semibold text-foreground">
              {payout.host_display_name}
            </p>
          ) : null}
          <p className="text-sm text-muted-foreground">
            {formatDateTime(payout.created_at)}
          </p>
        </div>
        <StatusBadge status={payout.status} />
      </div>
      <div className="space-y-0.5 text-sm text-muted-foreground">
        {bank.bank_name ? <p>{bank.bank_name}</p> : null}
        {bank.account_name ? <p>{bank.account_name}</p> : null}
        {bank.account_number ? (
          <p className="font-mono text-foreground">{bank.account_number}</p>
        ) : null}
      </div>
      {payout.host_note ? (
        <p className="text-sm text-muted-foreground">Note: {payout.host_note}</p>
      ) : null}
      {payout.evidence ? (
        <p className="text-sm font-semibold text-success">
          Paid · ref {payout.evidence.bank_transfer_reference}
        </p>
      ) : null}
      {actions ? (
        <div className="flex flex-wrap gap-2 border-t border-border pt-3">
          {actions}
        </div>
      ) : null}
    </Card>
  );
}
