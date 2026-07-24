"use client";

import Link from "next/link";

import {
  Badge,
  StatusBadge,
} from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { supportTicketNumber } from "@/lib/support-api";
import { formatSupportLabel, priorityTone } from "@/lib/support-ui";
import type { SupportCase } from "@/lib/types/support";

export function SupportTicketListItem({
  ticket,
  href,
}: {
  ticket: SupportCase;
  href: string;
}) {
  const number = supportTicketNumber(ticket);
  return (
    <Link
      href={href}
      className="block rounded-[var(--radius-lg)] border border-border bg-card p-4 shadow-[var(--shadow-soft)] transition-colors hover:bg-surface-muted/80 dark:bg-surface-elevated"
    >
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <p className="font-extrabold text-foreground">{number}</p>
          <p className="text-sm text-foreground">{ticket.subject}</p>
        </div>
        <StatusBadge status={ticket.status} />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <div className="flex flex-wrap gap-2">
          <Badge tone={priorityTone(ticket.priority)}>
            {formatSupportLabel(ticket.priority)}
          </Badge>
          <Badge tone="outline">{formatSupportLabel(ticket.category)}</Badge>
        </div>
        <span className="text-muted-foreground">
          {formatDateTime(ticket.updated_at)}
        </span>
      </div>
    </Link>
  );
}
