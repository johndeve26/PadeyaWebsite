"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { SupportConversation } from "@/components/support/SupportConversation";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  SkeletonLoader,
  StatusBadge,
  Textarea,
  useToast,
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
  const toast = useToast();
  const [ticket, setTicket] = useState<SupportCase | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [replyBody, setReplyBody] = useState("");
  const [busy, setBusy] = useState(false);

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

  async function onReply(event: FormEvent) {
    event.preventDefault();
    const body = replyBody.trim();
    if (!body || !ticket) return;
    setBusy(true);
    try {
      const updated = await replySupportTicket(ticket.id, body);
      setTicket(updated);
      setReplyBody("");
      toast.push({ tone: "success", title: "Reply sent" });
    } catch (err) {
      toast.push({
        tone: "danger",
        title: "Reply failed",
        description: err instanceof ApiError ? err.detail : "Try again",
      });
    } finally {
      setBusy(false);
    }
  }

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

  const closed =
    ticket.status === "closed" ||
    ticket.status === "archived" ||
    ticket.archived_at != null;

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
      {closed ? (
        <Alert tone="warning" title="Ticket closed">
          This conversation is closed. Open a new ticket if you need more help.
        </Alert>
      ) : null}

      <SupportConversation ticket={ticket} />

      {!closed ? (
        <Card className="space-y-4 p-5">
          <h2 className="text-lg font-extrabold text-foreground">Reply</h2>
          <form onSubmit={onReply} className="space-y-3">
            <Textarea
              label="Message"
              value={replyBody}
              onChange={(e) => setReplyBody(e.target.value)}
              rows={4}
              placeholder="Add context for support…"
            />
            <Button type="submit" disabled={busy || !replyBody.trim()}>
              {busy ? "Sending…" : "Send reply"}
            </Button>
          </form>
        </Card>
      ) : null}
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
