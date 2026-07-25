"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { SupportConversation } from "@/components/support/SupportConversation";
import { SupportRequesterReplyForm } from "@/components/support/SupportRequesterReplyForm";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Badge,
  Button,
  EmptyState,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  fetchSupportTicket,
  replySupportTicket,
  supportTicketNumber,
} from "@/lib/support-api";
import { formatSupportLabel, priorityTone } from "@/lib/support-ui";
import type { SupportCase } from "@/lib/types/support";

function HostSupportDetailInner() {
  const params = useParams<{ ticketId: string }>();
  const [ticket, setTicket] = useState<SupportCase | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const data = await fetchSupportTicket(params.ticketId);
    setTicket(data);
  }, [params.ticketId]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load ticket",
          );
          setTicket(null);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  if (error) {
    return (
      <DashboardShell
        tone="soft"
        eyebrow="Host workspace"
        title="Ticket unavailable"
        description="This ticket could not be loaded."
        actions={
          <Link href="/host/support">
            <Button variant="secondary">Host tickets</Button>
          </Link>
        }
      >
        <EmptyState title="Not found" description={error} />
      </DashboardShell>
    );
  }

  if (!ticket) {
    return (
      <DashboardShell
        tone="soft"
        eyebrow="Host workspace"
        title="Loading ticket…"
        description="Fetching conversation."
      >
        <SkeletonLoader lines={6} />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Host workspace"
      title={ticket.subject}
      description={`${supportTicketNumber(ticket)} · ${formatSupportLabel(ticket.category)}`}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={ticket.status} />
          <Badge tone={priorityTone(ticket.priority)}>
            {formatSupportLabel(ticket.priority)}
          </Badge>
          <Link href="/host/support">
            <Button variant="secondary" size="sm">
              All tickets
            </Button>
          </Link>
        </div>
      }
    >
      <div className="space-y-4">
        <SupportConversation ticket={ticket} />
        <SupportRequesterReplyForm
          ticket={ticket}
          onSent={setTicket}
          sendReply={(body) => replySupportTicket(ticket.id, body)}
        />
      </div>
    </DashboardShell>
  );
}

export default function HostSupportTicketDetailPage() {
  return (
    <RequireHost>
      <HostSupportDetailInner />
    </RequireHost>
  );
}
