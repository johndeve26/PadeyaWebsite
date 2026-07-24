"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import {
  TicketTypeBuilder,
  ticketDraftToPayload,
  ticketsToStudioDrafts,
  type StudioTicketDraft,
} from "@/components/events/studio";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmAction,
  EmptyState,
  StatusBadge,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { formatNgn } from "@/lib/format";
import {
  createTicketType,
  deactivateTicketType,
  deleteTicketType,
  fetchTicketTypes,
  updateTicketType,
} from "@/lib/events-api";
import type { TicketType } from "@/lib/types/events";

export default function EventTicketsPage() {
  const params = useParams<{ id: string }>();
  const toast = useToast();
  const [tickets, setTickets] = useState<TicketType[]>([]);
  const [drafts, setDrafts] = useState<StudioTicketDraft[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const loadTickets = useCallback(async () => {
    try {
      const items = await fetchTicketTypes(params.id);
      setTickets(items);
      setDrafts(ticketsToStudioDrafts(items));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load tickets");
    }
  }, [params.id]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const items = await fetchTicketTypes(params.id);
        if (!active) return;
        setTickets(items);
        setDrafts(ticketsToStudioDrafts(items));
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load tickets",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id]);

  async function onDeactivate(ticketTypeId: string) {
    setError(null);
    setMessage(null);
    try {
      await deactivateTicketType(params.id, ticketTypeId);
      setMessage("Ticket type deactivated.");
      toast.push({ tone: "success", title: "Ticket type deactivated" });
      await loadTickets();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Unable to deactivate");
      throw err;
    }
  }

  async function onDelete(ticketTypeId: string) {
    setError(null);
    setMessage(null);
    try {
      await deleteTicketType(params.id, ticketTypeId);
      setMessage("Ticket type deleted.");
      toast.push({ tone: "success", title: "Ticket type deleted" });
      await loadTickets();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Unable to delete");
      throw err;
    }
  }

  async function onSaveDrafts() {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      for (const draft of drafts) {
        if (!draft.name.trim()) continue;
        if (!draft.type.trim()) {
          throw new Error(
            `Ticket tier "${draft.name}" needs a type (preset or custom).`,
          );
        }
        const body = ticketDraftToPayload(draft);
        if (draft.id) {
          await updateTicketType(params.id, draft.id, body);
        } else {
          await createTicketType(params.id, body);
        }
      }
      setMessage("Ticket types saved.");
      toast.push({ tone: "success", title: "Ticket types saved" });
      await loadTickets();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : err instanceof Error
            ? err.message
            : "Unable to save ticket types",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Ticket types"
        title="Configure ticket tiers"
        description="Price, quantity, and visibility for checkout. Tickets issue only after payment confirms. Prefer Event Studio for the full Tickets & Access step."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href={`/host/events/${params.id}/edit?step=tickets`}>
              <Button variant="secondary">Open in Event Studio</Button>
            </Link>
            <Link href={`/host/events/${params.id}`}>
              <Button variant="secondary">Event ops</Button>
            </Link>
          </div>
        }
      >
        {error ? (
          <Alert tone="danger" title="Ticket setup error">
            {error}
          </Alert>
        ) : null}
        {message ? (
          <Alert tone="success" title="Updated">
            {message}
          </Alert>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <Card className="space-y-4 shadow-[var(--shadow-soft)]">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                  Builder
                </p>
                <h2 className="mt-1 text-xl font-extrabold text-foreground">
                  Ticket tiers
                </h2>
              </div>
              <Button
                type="button"
                disabled={saving}
                onClick={() => void onSaveDrafts()}
              >
                {saving ? "Saving…" : "Save tiers"}
              </Button>
            </div>
            <TicketTypeBuilder
              drafts={drafts}
              onChange={setDrafts}
              eventId={params.id}
              onDeactivate={async (ticketTypeId) => {
                await onDeactivate(ticketTypeId);
              }}
              onDeleteUnused={async (ticketTypeId) => {
                await onDelete(ticketTypeId);
              }}
            />
          </Card>

          <div className="space-y-4">
            <div>
              <h2 className="text-xl font-extrabold text-foreground">
                Live tiers
              </h2>
              <p className="text-sm text-muted-foreground">
                {tickets.length} configured · deactivate or delete unused tiers
                here
              </p>
            </div>
            {tickets.length === 0 ? (
              <EmptyState
                title="No ticket types yet"
                description="Add Regular, VIP, or Early Bird tiers so fans can buy."
              />
            ) : (
              <div className="grid gap-3">
                {tickets.map((ticket) => (
                  <Card
                    key={ticket.id}
                    className="space-y-3 border-border shadow-[var(--shadow-soft)]"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <h3 className="text-lg font-extrabold text-foreground">
                          {ticket.name}
                        </h3>
                        <p className="text-sm capitalize text-muted-foreground">
                          {String(ticket.type).replace(/_/g, " ")}
                        </p>
                      </div>
                      <StatusBadge status={ticket.status} />
                    </div>
                    <p className="text-2xl font-extrabold tracking-tight text-foreground">
                      {Number(ticket.price) === 0
                        ? "Free"
                        : formatNgn(ticket.price)}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Badge tone="outline">Qty {ticket.quantity}</Badge>
                      <Badge tone="neutral">{ticket.visibility}</Badge>
                      {(ticket.seats_per_unit ?? 1) > 1 ? (
                        <Badge tone="accent">
                          {ticket.seats_per_unit} seats/unit
                        </Badge>
                      ) : null}
                    </div>
                    <div className="flex flex-wrap gap-2 pt-1">
                      {ticket.status === "active" ? (
                        <ConfirmAction
                          label="Deactivate"
                          title="Deactivate this ticket type?"
                          description="Buyers will no longer see this tier. Existing orders are unchanged."
                          confirmLabel="Deactivate"
                          onConfirm={() => onDeactivate(ticket.id)}
                        />
                      ) : null}
                      {(ticket.quantity_sold ?? 0) === 0 &&
                      (ticket.quantity_reserved ?? 0) === 0 ? (
                        <ConfirmAction
                          label="Delete"
                          title="Delete unused ticket type?"
                          description="Permanent only when there are no sales or reservations. Prefer deactivate after sales begin."
                          confirmLabel="Delete permanently"
                          tone="danger"
                          variant="ghost"
                          onConfirm={() => onDelete(ticket.id)}
                        />
                      ) : null}
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      </DashboardShell>
    </RequireHost>
  );
}
