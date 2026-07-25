"use client";

import { useState, type FormEvent } from "react";

import { Alert, Button, Card, Textarea, useToast } from "@/components/ui";
import { ApiError } from "@/lib/api";
import type { SupportCase } from "@/lib/types/support";

type Props = {
  ticket: SupportCase;
  /** Called with the updated ticket after a successful send. */
  onSent: (updated: SupportCase) => void;
  /** Authenticated dashboard reply, or public email/token track reply. */
  sendReply: (body: string) => Promise<SupportCase>;
};

export function isSupportTicketClosed(ticket: SupportCase): boolean {
  return (
    ticket.status === "closed" ||
    ticket.status === "archived" ||
    ticket.archived_at != null
  );
}

/**
 * Requester follow-up box — used on dashboard detail and public track pages.
 * Never used for staff replies.
 */
export function SupportRequesterReplyForm({
  ticket,
  onSent,
  sendReply,
}: Props) {
  const toast = useToast();
  const [replyBody, setReplyBody] = useState("");
  const [busy, setBusy] = useState(false);
  const closed = isSupportTicketClosed(ticket);

  if (closed) {
    return (
      <Alert tone="warning" title="Ticket closed">
        This conversation is closed. Open a new ticket if you need more help.
      </Alert>
    );
  }

  async function onReply(event: FormEvent) {
    event.preventDefault();
    const body = replyBody.trim();
    if (!body) return;
    setBusy(true);
    try {
      const updated = await sendReply(body);
      onSent(updated);
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

  const waiting = ticket.status === "waiting_on_user";

  return (
    <Card className="space-y-4 p-5">
      <div className="space-y-1">
        <h2 className="text-lg font-extrabold text-foreground">
          {waiting ? "Reply to support" : "Add a follow-up"}
        </h2>
        <p className="text-sm text-muted-foreground">
          {waiting
            ? "Support is waiting on your reply. Share any extra details below."
            : "Send more detail anytime — your message stays on this ticket."}
        </p>
      </div>
      <form onSubmit={onReply} className="space-y-3">
        <Textarea
          label="Message"
          value={replyBody}
          onChange={(e) => setReplyBody(e.target.value)}
          rows={4}
          placeholder="Add more detail for support…"
          required
        />
        <Button type="submit" disabled={busy || !replyBody.trim()}>
          {busy ? "Sending…" : "Send reply"}
        </Button>
      </form>
    </Card>
  );
}
