"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  DataTable,
  Dropdown,
  EmptyState,
  Input,
  SkeletonLoader,
  StatusBadge,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import {
  fetchTicketTransfers,
  fetchTicketTransferClaimLink,
  resendTicketTransferInvite,
  transferTicket,
} from "@/lib/advanced-tickets-api";
import { fetchTicket } from "@/lib/commerce-api";
import {
  absoluteClaimUrl,
  buildRegisterLink,
  buildTransferInviteMessage,
} from "@/lib/tickets/transfer-invite-message";
import type { TicketTransfer } from "@/lib/types/advanced-tickets";
import type { Ticket } from "@/lib/types/commerce";

export default function TicketTransferPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [history, setHistory] = useState<TicketTransfer[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copiedInvite, setCopiedInvite] = useState(false);
  const [copiedClaim, setCopiedClaim] = useState(false);
  const [copiedSignup, setCopiedSignup] = useState(false);
  const [resendBusy, setResendBusy] = useState(false);
  const [copyLinkBusy, setCopyLinkBusy] = useState(false);
  const [pendingClaimPath, setPendingClaimPath] = useState<string | null>(null);
  const [pendingTransferId, setPendingTransferId] = useState<string | null>(null);

  async function resolveClaimPath(): Promise<string | null> {
    if (pendingTransferId) {
      const updated = await fetchTicketTransferClaimLink(pendingTransferId);
      if (updated.claim_path) {
        setPendingClaimPath(updated.claim_path);
        return updated.claim_path;
      }
    }
    return pendingClaimPath;
  }

  async function copyClaimLinkOnly() {
    const trimmed = email.trim();
    if (!trimmed || typeof window === "undefined") return;
    setCopyLinkBusy(true);
    setCopiedClaim(false);
    try {
      const claimPath = await resolveClaimPath();
      if (!claimPath) {
        setError("Transfer first to generate a claim link, or open My tickets → Transfer history.");
        return;
      }
      await navigator.clipboard.writeText(absoluteClaimUrl(claimPath));
      setCopiedClaim(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not copy claim link");
    } finally {
      setCopyLinkBusy(false);
    }
  }

  async function copySignupLinkOnly() {
    const trimmed = email.trim();
    if (!trimmed || typeof window === "undefined") return;
    setCopyLinkBusy(true);
    setCopiedSignup(false);
    try {
      const claimPath = pendingTransferId
        ? await resolveClaimPath()
        : pendingClaimPath;
      await navigator.clipboard.writeText(
        buildRegisterLink(trimmed, claimPath ?? undefined),
      );
      setCopiedSignup(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not copy sign-up link");
    } finally {
      setCopyLinkBusy(false);
    }
  }

  async function copyInviteLink() {
    const trimmed = email.trim();
    if (!trimmed || typeof window === "undefined") return;
    setCopyLinkBusy(true);
    setCopiedInvite(false);
    try {
      const claimPath = pendingTransferId
        ? await resolveClaimPath()
        : pendingClaimPath;
      const message = buildTransferInviteMessage(trimmed, {
        claimPath,
      });
      await navigator.clipboard.writeText(message);
      setCopiedInvite(true);
    } catch (err) {
      setCopiedInvite(false);
      if (err instanceof ApiError) {
        setError(err.detail);
      }
    } finally {
      setCopyLinkBusy(false);
    }
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      setError(null);
      setHistoryError(null);
      try {
        const t = await fetchTicket(params.id);
        if (!active) return;
        setTicket(t);
      } catch (err) {
        if (!active) return;
        const detail =
          err instanceof ApiError
            ? err.detail
            : "Could not load this ticket. Check your connection and try again.";
        setError(detail);
        setTicket(null);
        return;
      }
      try {
        const h = await fetchTicketTransfers(params.id);
        if (!active) return;
        setHistory(h);
      } catch (err) {
        if (!active) return;
        setHistory([]);
        setHistoryError(
          err instanceof ApiError
            ? err.detail
            : "Transfer history could not be loaded.",
        );
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id]);

  async function onResendInviteEmail() {
    if (!pendingTransferId) return;
    setResendBusy(true);
    setError(null);
    try {
      const updated = await resendTicketTransferInvite(pendingTransferId);
      if (updated.claim_path) {
        setPendingClaimPath(updated.claim_path);
      }
      setSuccess(
        `Invite email sent again to ${email.trim()}. We also refreshed the claim link — use Copy invite message if their inbox is slow.`,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not resend invite email");
    } finally {
      setResendBusy(false);
    }
  }

  async function onTransfer() {
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await transferTicket(params.id, {
        to_email: email.trim(),
        to_name: name.trim(),
        note: note || undefined,
      });
      if (result.status === "pending") {
        setPendingClaimPath(result.claim_path ?? null);
        setPendingTransferId(result.id);
        setSuccess(
          `We emailed ${name.trim()} at ${email.trim()} with a personalized link to claim this ticket for ${ticket?.event_title ?? "the event"}. If they do not see it, use Resend email or copy the invite message below.`,
        );
        setHistory((prev) => [result, ...prev]);
        return;
      }
      router.push("/dashboard/tickets");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Transfer failed");
    } finally {
      setBusy(false);
    }
  }

  if (error && !ticket) {
    return (
      <DashboardShell
        tone="soft"
        eyebrow="Transfer"
        title="Unavailable"
        description="This ticket could not be loaded."
        actions={
          <Link href="/dashboard/tickets">
            <Button variant="secondary">All tickets</Button>
          </Link>
        }
      >
        <EmptyState
          title="Ticket unavailable"
          description={
            error.toLowerCase().includes("not found")
              ? `${error} If you already started a transfer, this ticket may have left your account while the recipient claims it.`
              : error
          }
        />
      </DashboardShell>
    );
  }

  if (!ticket) {
    return (
      <DashboardShell
        tone="soft"
        eyebrow="Transfer"
        title="Transfer ticket"
        description="Preparing transfer form…"
      >
        <SkeletonLoader lines={4} />
      </DashboardShell>
    );
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Transfer"
      title="Transfer ticket"
      description="The previous owner loses access. Transfers are audited."
      actions={
        <Link href={`/dashboard/tickets/${ticket.id}`}>
          <Button variant="secondary">Back to ticket</Button>
        </Link>
      }
    >
      <Card className="space-y-2 border-ink/10 bg-ink text-paper">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={ticket.status} />
          <span className="text-xs font-bold uppercase tracking-[0.1em] text-subtle-foreground">
            Passing ownership
          </span>
        </div>
        <p className="text-xl font-extrabold tracking-tight">
          {ticket.event_title ?? "Event"}
        </p>
        <p className="font-mono text-accent">{ticket.public_code}</p>
        <p className="text-sm text-subtle-foreground">{ticket.ticket_type_name}</p>
      </Card>

      {historyError ? (
        <Alert tone="warning" title="Transfer history unavailable">
          {historyError} You can still transfer this ticket below.
        </Alert>
      ) : null}

      {success ? (
        <Alert tone="success" title="Transfer started">
          {success}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {pendingTransferId ? (
              <Button
                size="sm"
                disabled={resendBusy}
                onClick={() => void onResendInviteEmail()}
              >
                {resendBusy ? "Sending…" : "Resend email"}
              </Button>
            ) : null}
            {pendingTransferId ? (
              <Dropdown
                label="Copy links"
                align="left"
                items={[
                  {
                    id: "invite",
                    label: copiedInvite ? "Copied invite message" : "Copy invite message",
                    disabled: copyLinkBusy || !email.trim(),
                    onSelect: () => void copyInviteLink(),
                  },
                  {
                    id: "claim",
                    label: copiedClaim ? "Copied claim link" : "Copy claim link",
                    disabled: copyLinkBusy || !email.trim(),
                    onSelect: () => void copyClaimLinkOnly(),
                  },
                  {
                    id: "signup",
                    label: copiedSignup ? "Copied sign-up link" : "Copy sign-up link",
                    disabled: copyLinkBusy || !email.trim(),
                    onSelect: () => void copySignupLinkOnly(),
                  },
                ]}
              />
            ) : null}
            <Link href="/dashboard/tickets">
              <Button size="sm" variant="secondary">
                View transfer history
              </Button>
            </Link>
          </div>
        </Alert>
      ) : null}

      {error ? (
        <Alert tone="danger" title="Transfer failed">
          {error}
        </Alert>
      ) : null}

      <Alert tone="info" title="How it works">
        Enter their name and email. If they already have a Pàdéyá account with that email, the
        ticket moves instantly. If not, we email them a personalized claim link — they register,
        then accept the ticket.
      </Alert>

      <Card className="max-w-lg space-y-4">
        <Input
          label="Recipient name"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            setError(null);
            setSuccess(null);
          }}
          placeholder="Ada Okonkwo"
          hint="We use this in the email we send them"
        />
        <Input
          label="Recipient email"
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            setError(null);
            setSuccess(null);
            setCopiedInvite(false);
          }}
          placeholder="friend@example.com"
          hint="Must match the email they use on Pàdéyá"
        />
        <Textarea
          label="Note (optional)"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          hint="Visible in transfer history"
        />
        <Button
          size="lg"
          disabled={
            busy || !email.trim() || !name.trim() || ticket.status !== "active"
          }
          onClick={() => void onTransfer()}
        >
          {busy ? "Transferring…" : "Transfer ownership"}
        </Button>
        {email.trim() && pendingTransferId ? (
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Dropdown
              label="Copy links"
              align="left"
              items={[
                {
                  id: "invite",
                  label: "Copy invite message",
                  disabled: copyLinkBusy,
                  onSelect: () => void copyInviteLink(),
                },
                {
                  id: "claim",
                  label: "Copy claim link",
                  disabled: copyLinkBusy,
                  onSelect: () => void copyClaimLinkOnly(),
                },
                {
                  id: "signup",
                  label: "Copy sign-up link",
                  disabled: copyLinkBusy,
                  onSelect: () => void copySignupLinkOnly(),
                },
              ]}
            />
          </div>
        ) : null}
        <p className="text-xs text-muted-foreground">
          After transfer, manage pending invites from My tickets → Transfer history.
        </p>
        {ticket.status !== "active" ? (
          <p className="text-sm text-muted-foreground">
            Only active tickets can be transferred.
          </p>
        ) : null}
      </Card>

      <section className="space-y-4">
        <h3 className="text-lg font-extrabold text-foreground">Transfer history</h3>
        {history.length === 0 ? (
          <EmptyState
            title="No transfers yet"
            description="When you transfer this ticket, the trail appears here."
          />
        ) : (
          <DataTable
            rows={history}
            rowKey={(row) => row.id}
            emptyTitle="No transfers yet"
            columns={[
              {
                key: "route",
                header: "Transfer",
                primary: true,
                cell: (row) => (
                  <span className="font-bold text-foreground">
                    {row.from_email} → {row.to_email}
                    {row.recipient_name ? ` (${row.recipient_name})` : ""}
                  </span>
                ),
              },
              {
                key: "status",
                header: "Status",
                cell: (row) => (
                  <span className="text-sm capitalize text-muted-foreground">
                    {row.status}
                  </span>
                ),
              },
              {
                key: "date",
                header: "Date",
                cell: (row) => (
                  <span className="text-sm text-muted-foreground">
                    {formatDateTime(row.created_at)}
                  </span>
                ),
              },
              {
                key: "note",
                header: "Note",
                cell: (row) => (
                  <span className="text-sm text-muted-foreground">{row.note ?? "—"}</span>
                ),
              },
            ]}
          />
        )}
      </section>
    </DashboardShell>
  );
}
