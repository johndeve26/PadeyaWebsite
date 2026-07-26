"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  Modal,
  SkeletonLoader,
  useToast,
} from "@/components/ui";

const TicketQrPanel = dynamic(
  () =>
    import("@/components/tickets/TicketQrPanel").then((m) => m.TicketQrPanel),
  {
    ssr: false,
    loading: () => (
      <div
        className="mx-auto h-[280px] w-full max-w-[280px] animate-pulse rounded-[var(--radius-xl)] bg-surface-inset"
        aria-busy
      />
    ),
  },
);
import { trackTicketDownloaded, trackTicketQrClicked } from "@/lib/analytics";
import { downloadTicketPdf, fetchTicket } from "@/lib/commerce-api";
import {
  cacheTicketForOffline,
  readCachedTicket,
} from "@/lib/pwa/offline-ticket-cache";
import { ticketStatusPresentation } from "@/lib/tickets/buyer-ticket-groups";
import type { Ticket } from "@/lib/types/commerce";

export function TicketQrModal({
  ticketId,
  open,
  onClose,
}: {
  ticketId: string;
  open: boolean;
  onClose: () => void;
}) {
  const { push } = useToast();
  const [ticket, setTicket] = useState<Ticket | null>(() =>
    readCachedTicket(ticketId),
  );
  const [loading, setLoading] = useState(() => !readCachedTicket(ticketId));
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const item = await fetchTicket(ticketId);
        if (cancelled) return;
        cacheTicketForOffline(item);
        setTicket(item);
        setError(null);
        trackTicketQrClicked({
          targetEventId: item.event_id,
          ticketStatus: item.status,
        });
      } catch (err) {
        if (cancelled) return;
        const cached = readCachedTicket(ticketId);
        if (cached) {
          setTicket(cached);
          setError(null);
        } else {
          setError(
            err instanceof Error ? err.message : "Could not load ticket QR",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [ticketId]);

  const presentation = ticket ? ticketStatusPresentation(ticket) : null;
  const qrValue = ticket?.qr_payload?.trim() || "";
  const showQr = Boolean(presentation?.showQr && qrValue);

  async function onDownload() {
    if (!ticket || downloading || !presentation?.canDownloadPdf) return;
    setDownloading(true);
    try {
      await downloadTicketPdf(ticket.id);
      trackTicketDownloaded({
        targetEventId: ticket.event_id,
        ticketStatus: ticket.status,
      });
      push({ title: "PDF downloaded", tone: "success" });
    } catch (err) {
      push({
        title: "Download failed",
        description: err instanceof Error ? err.message : "Try again",
        tone: "danger",
      });
    } finally {
      setDownloading(false);
    }
  }

  async function onCopy() {
    if (!ticket) return;
    try {
      await navigator.clipboard.writeText(ticket.public_code);
      push({ title: "Entry code copied", tone: "success" });
    } catch {
      push({ title: "Could not copy code", tone: "danger" });
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={ticket?.event_title || "Ticket pass"}
      description={
        presentation?.showQr && presentation.statusLabel === "Active"
          ? "Show this QR code at entry."
          : presentation?.entryNote
      }
      className="sm:max-w-md"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} className="sm:min-w-[6rem]">
            Done
          </Button>
          <Button
            variant="secondary"
            onClick={() => void onCopy()}
            disabled={!ticket}
          >
            Copy code
          </Button>
          <Button
            variant="primary"
            onClick={() => void onDownload()}
            disabled={!ticket || !presentation?.canDownloadPdf || downloading}
          >
            {downloading ? "Downloading…" : "Download PDF"}
          </Button>
        </>
      }
    >
      {error ? (
        <Alert tone="danger" title="QR unavailable">
          {error}
        </Alert>
      ) : null}

      {loading && !ticket ? <SkeletonLoader lines={4} /> : null}

      {ticket && presentation ? (
        <div className="space-y-5">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="outline" size="sm">
                {ticket.ticket_type_name || "Ticket"}
              </Badge>
              <Badge tone={presentation.statusTone} size="sm">
                {presentation.statusLabel}
              </Badge>
              {presentation.readinessLabel ? (
                <Badge
                  tone={presentation.readinessTone ?? "neutral"}
                  size="sm"
                >
                  {presentation.readinessLabel}
                </Badge>
              ) : null}
            </div>
            <p className="text-sm text-muted-foreground">
              Holder · {ticket.holder_name}
            </p>
          </div>

          <div className="flex flex-col items-center gap-3 rounded-[var(--radius-lg)] border border-border bg-muted/40 px-4 py-5">
            {showQr ? (
              <TicketQrPanel value={qrValue} size={240} />
            ) : (
              <div className="flex min-h-[200px] w-full max-w-[280px] items-center justify-center rounded-[var(--radius-xl)] bg-paper px-4 text-center ring-1 ring-border">
                <p className="text-sm font-semibold text-ink/70">
                  {presentation.entryNote}
                </p>
              </div>
            )}
            <div className="w-full max-w-[280px] space-y-1 text-center">
              <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-muted-foreground">
                Entry code
              </p>
              <p className="break-all font-mono text-base font-bold tracking-wide text-foreground">
                {ticket.public_code}
              </p>
              {showQr && presentation.statusLabel === "Active" ? (
                <p className="text-sm text-muted-foreground">
                  Show this QR code at entry.
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {presentation.entryNote}
                </p>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </Modal>
  );
}
