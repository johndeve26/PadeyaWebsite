"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Button,
  Card,
  Dropdown,
  EmptyState,
  SectionHeader,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  claimTicketTransferById,
  declineTicketTransfer,
  fetchMyTicketTransfers,
  fetchTicketTransferClaimLink,
  resendTicketTransferInvite,
  revokeTicketTransfer,
} from "@/lib/advanced-tickets-api";
import { formatDateTime } from "@/lib/format";
import {
  absoluteClaimUrl,
  buildRegisterLink,
  buildTransferInviteMessage,
} from "@/lib/tickets/transfer-invite-message";
import type { TicketTransferActivity } from "@/lib/types/advanced-tickets";

function transferStatusLabel(status: string): string {
  const s = status.toLowerCase();
  if (s === "completed") return "accepted";
  if (s === "pending") return "pending";
  if (s === "declined") return "declined";
  if (s === "revoked") return "cancelled";
  return status;
}

function transferStatusCopy(status: string): string {
  const s = status.toLowerCase();
  if (s === "completed") return "Accepted";
  if (s === "pending") return "Pending";
  if (s === "declined") return "Declined";
  if (s === "revoked") return "Cancelled";
  return status;
}

function transferRouteLabel(row: TicketTransferActivity): string {
  const name = row.recipient_name || row.to_email;
  if (row.role === "sent") return `You → ${name}`;
  return `${name} → You`;
}

function TransferHistoryCard({
  row,
  busy,
  onCopyInvite,
  onCopyClaim,
  onCopySignup,
  onResend,
  onRevoke,
  onDecline,
  onClaim,
}: {
  row: TicketTransferActivity;
  busy: boolean;
  onCopyInvite: () => void;
  onCopyClaim: () => void;
  onCopySignup: () => void;
  onResend: () => void;
  onRevoke: () => void;
  onDecline: () => void;
  onClaim: () => void;
}) {
  const isPending = row.status === "pending";
  const showSenderTools = row.can_resend_invite;

  const copyItems = showSenderTools
    ? [
        {
          id: "invite",
          label: "Copy invite message",
          onSelect: onCopyInvite,
          disabled: busy,
        },
        {
          id: "claim",
          label: "Copy claim link",
          onSelect: onCopyClaim,
          disabled: busy,
        },
        {
          id: "signup",
          label: "Copy sign-up link",
          onSelect: onCopySignup,
          disabled: busy,
        },
      ]
    : [];

  return (
    <Card className="min-w-0 space-y-4 p-4 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-base font-extrabold tracking-tight text-foreground">
              {row.event_title ?? "Event"}
            </h4>
            <StatusBadge
              status={transferStatusLabel(row.status)}
              label={transferStatusCopy(row.status)}
            />
          </div>
          {row.ticket_public_code ? (
            <p className="font-mono text-xs text-muted-foreground">{row.ticket_public_code}</p>
          ) : null}
          <p className="text-sm text-foreground">{transferRouteLabel(row)}</p>
          <p className="text-xs text-muted-foreground">{formatDateTime(row.created_at)}</p>
          {isPending && showSenderTools ? (
            <p className="text-xs text-muted-foreground">
              Waiting for {row.recipient_name || row.to_email} to claim. Email slow? Copy links
              below or resend.
            </p>
          ) : null}
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2 sm:justify-end">
          {row.status === "pending" && row.role === "received" ? (
            <Button size="sm" disabled={busy} onClick={() => onClaim()}>
              {busy ? "Claiming…" : "Claim ticket"}
            </Button>
          ) : null}
          {showSenderTools ? (
            <>
              <Button size="sm" disabled={busy} onClick={() => onResend()}>
                {busy ? "Working…" : "Resend email"}
              </Button>
              {copyItems.length > 0 ? (
                <Dropdown
                  label="Copy links"
                  align="right"
                  menuPlacement="auto"
                  items={copyItems}
                />
              ) : null}
              <Button
                size="sm"
                variant="secondary"
                disabled={busy}
                className="text-danger hover:text-danger"
                onClick={() => onRevoke()}
              >
                Revoke
              </Button>
            </>
          ) : null}
          {!showSenderTools && row.can_decline ? (
            <Button size="sm" variant="secondary" disabled={busy} onClick={() => onDecline()}>
              Decline
            </Button>
          ) : null}
        </div>
      </div>
    </Card>
  );
}

export function TicketTransferHistoryPanel({
  onTicketsChanged,
}: {
  onTicketsChanged?: () => void;
}) {
  const router = useRouter();
  const [rows, setRows] = useState<TicketTransferActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await fetchMyTicketTransfers();
      setRows(items);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not load transfer history");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function withClaimPath(
    row: TicketTransferActivity,
    fn: (claimPath: string | null) => Promise<void>,
  ) {
    setBusyId(row.id);
    setError(null);
    setNotice(null);
    try {
      const updated = await fetchTicketTransferClaimLink(row.id);
      await fn(updated.claim_path ?? null);
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong");
    } finally {
      setBusyId(null);
    }
  }

  async function onCopyClaimLink(row: TicketTransferActivity) {
    await withClaimPath(row, async (claimPath) => {
      if (!claimPath) {
        setError("Could not generate a claim link for this transfer.");
        return;
      }
      await navigator.clipboard.writeText(absoluteClaimUrl(claimPath));
      setNotice(`Claim link copied for ${row.to_email}.`);
    });
  }

  async function onCopySignupLink(row: TicketTransferActivity) {
    await withClaimPath(row, async (claimPath) => {
      await navigator.clipboard.writeText(
        buildRegisterLink(row.to_email, claimPath),
      );
      setNotice(`Sign-up link copied for ${row.to_email}.`);
    });
  }

  async function onCopyInviteMessage(row: TicketTransferActivity) {
    await withClaimPath(row, async (claimPath) => {
      const message = buildTransferInviteMessage(row.to_email, { claimPath });
      await navigator.clipboard.writeText(message);
      setNotice(`Invite message copied — paste into WhatsApp or email.`);
    });
  }

  async function onResendInvite(row: TicketTransferActivity) {
    setBusyId(row.id);
    setError(null);
    setNotice(null);
    try {
      const updated = await resendTicketTransferInvite(row.id);
      setNotice(`Invite email sent again to ${row.to_email}.`);
      if (updated.claim_path) {
        try {
          const message = buildTransferInviteMessage(row.to_email, {
            claimPath: updated.claim_path,
          });
          await navigator.clipboard.writeText(message);
          setNotice(
            (prev) =>
              `${prev ?? ""} Invite message also copied with the fresh claim link.`,
          );
        } catch {
          // optional
        }
      }
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not resend invite email");
    } finally {
      setBusyId(null);
    }
  }

  async function onRevoke(row: TicketTransferActivity) {
    setBusyId(row.id);
    setError(null);
    try {
      await revokeTicketTransfer(row.id);
      setNotice("Transfer revoked — the ticket is back on your account.");
      await reload();
      onTicketsChanged?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not revoke transfer");
    } finally {
      setBusyId(null);
    }
  }

  async function onClaimTransfer(row: TicketTransferActivity) {
    setBusyId(row.id);
    setError(null);
    setNotice(null);
    try {
      await claimTicketTransferById(row.id);
      setNotice("Ticket claimed — it is now on your account.");
      await reload();
      onTicketsChanged?.();
      router.push("/dashboard/tickets");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not claim this ticket");
    } finally {
      setBusyId(null);
    }
  }

  async function onDecline(row: TicketTransferActivity) {
    setBusyId(row.id);
    setError(null);
    try {
      await declineTicketTransfer(row.id);
      await reload();
      onTicketsChanged?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not decline transfer");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="space-y-4">
      <SectionHeader
        title="Transfer history"
        description="Pending, accepted, declined, or cancelled — resend or copy links anytime."
      />
      {notice ? (
        <Alert tone="success" title="Done">
          {notice}
        </Alert>
      ) : null}
      {error ? (
        <Alert tone="danger" title="Transfer history">
          {error}
        </Alert>
      ) : null}
      {loading ? <SkeletonLoader lines={3} /> : null}
      {!loading && rows.length === 0 && !error ? (
        <EmptyState
          title="No transfers yet"
          description="When you transfer a ticket or someone sends one to your email, it appears here."
        />
      ) : null}
      {!loading && rows.length > 0 ? (
        <ul className="space-y-3">
          {rows.map((row) => (
            <li key={row.id}>
              <TransferHistoryCard
                row={row}
                busy={busyId === row.id}
                onCopyInvite={() => void onCopyInviteMessage(row)}
                onCopyClaim={() => void onCopyClaimLink(row)}
                onCopySignup={() => void onCopySignupLink(row)}
                onResend={() => void onResendInvite(row)}
                onRevoke={() => void onRevoke(row)}
                onDecline={() => void onDecline(row)}
                onClaim={() => void onClaimTransfer(row)}
              />
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
