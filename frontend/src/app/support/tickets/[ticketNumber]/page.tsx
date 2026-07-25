"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState, type FormEvent } from "react";

import { SupportConversation } from "@/components/support/SupportConversation";
import { SupportRequesterReplyForm } from "@/components/support/SupportRequesterReplyForm";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  EmptyState,
  Input,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { brand } from "@/lib/brand";
import {
  fetchSupportTicketByNumber,
  replyPublicSupportTicket,
  supportTicketNumber,
} from "@/lib/support-api";
import { formatSupportLabel, priorityTone } from "@/lib/support-ui";
import type { SupportCase } from "@/lib/types/support";

function TrackTicketInner() {
  const params = useParams<{ ticketNumber: string }>();
  const searchParams = useSearchParams();
  const ticketNumberParam = decodeURIComponent(params.ticketNumber ?? "");

  const [email, setEmail] = useState(searchParams.get("email") ?? "");
  const [token, setToken] = useState(searchParams.get("token") ?? "");
  const [verifiedEmail, setVerifiedEmail] = useState(
    searchParams.get("email") ?? "",
  );
  const [verifiedToken, setVerifiedToken] = useState(
    searchParams.get("token") ?? "",
  );
  const [ticket, setTicket] = useState<SupportCase | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [attempted, setAttempted] = useState(false);

  const load = useCallback(
    async (mail: string, accessToken?: string) => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchSupportTicketByNumber(ticketNumberParam, {
          email: mail || undefined,
          token: accessToken || undefined,
        });
        setTicket(data);
        setVerifiedEmail(mail.trim());
        setVerifiedToken((accessToken || "").trim());
      } catch (err) {
        setTicket(null);
        setError(
          err instanceof ApiError
            ? err.detail
            : "Could not find that ticket. Check the number and email.",
        );
      } finally {
        setLoading(false);
        setAttempted(true);
      }
    },
    [ticketNumberParam],
  );

  useEffect(() => {
    const mail = searchParams.get("email");
    const access = searchParams.get("token");
    if (mail || access) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate from query
      void load(mail ?? "", access ?? undefined);
    }
  }, [load, searchParams]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void load(email.trim(), token.trim() || undefined);
  }

  return (
    <div className="space-y-6">
      {!ticket ? (
        <Card className="space-y-4 p-5 sm:p-6">
          {error && attempted ? (
            <Alert tone="danger" title="Ticket not found">
              {error}
            </Alert>
          ) : null}
          <form onSubmit={onSubmit} className="space-y-4">
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <Input
              label="Access token (optional)"
              value={token}
              onChange={(e) => setToken(e.target.value)}
            />
            <Button type="submit" disabled={loading}>
              {loading ? "Looking up…" : "View ticket"}
            </Button>
          </form>
        </Card>
      ) : null}

      {loading && !ticket ? <SkeletonLoader lines={5} /> : null}

      {ticket ? (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={ticket.status} />
            <Badge tone={priorityTone(ticket.priority)}>
              {formatSupportLabel(ticket.priority)}
            </Badge>
            <Badge tone="outline">
              {formatSupportLabel(ticket.category)}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Reference{" "}
            <span className="font-bold text-foreground">
              {supportTicketNumber(ticket)}
            </span>
          </p>
          <div className="space-y-4">
            <SupportConversation ticket={ticket} />
            <SupportRequesterReplyForm
              ticket={ticket}
              onSent={setTicket}
              sendReply={(body) =>
                replyPublicSupportTicket(ticketNumberParam, body, {
                  email: verifiedEmail || undefined,
                  token: verifiedToken || undefined,
                })
              }
            />
          </div>
          {/* Guard: never surface internal_notes on public track */}
          {ticket.internal_notes?.length ? null : null}
        </>
      ) : null}

      {attempted && !loading && !ticket && !error ? (
        <EmptyState
          title="Enter your email"
          description="We need the email on the ticket to show the conversation."
        />
      ) : null}
    </div>
  );
}

export default function PublicTrackTicketPage() {
  const params = useParams<{ ticketNumber: string }>();
  const ticketNumber = decodeURIComponent(params.ticketNumber ?? "");

  return (
    <div className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_color-mix(in_srgb,var(--primary)_12%,transparent),_transparent_50%)]"
      />
      <Container className="py-10 sm:py-14">
        <div className="mx-auto max-w-2xl">
          <p className="text-sm font-bold uppercase tracking-[0.14em] text-primary">
            {brand.name} Support
          </p>
          <h1 className="mt-2 text-3xl font-extrabold text-foreground sm:text-4xl">
            Ticket {ticketNumber}
          </h1>
          <p className="mt-2 text-muted-foreground">
            Status and conversation for your support request.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href="/support">
              <Button size="sm" variant="ghost">
                ← Support Center
              </Button>
            </Link>
            <Link href="/support/tickets/lookup">
              <Button size="sm" variant="secondary">
                Track another
              </Button>
            </Link>
          </div>
          <div className="mt-8">
            <Suspense fallback={<SkeletonLoader lines={5} />}>
              <TrackTicketInner />
            </Suspense>
          </div>
        </div>
      </Container>
    </div>
  );
}
