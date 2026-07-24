"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import { CancelTicketButton } from "@/components/tickets/CancelTicketButton";
import { TicketQrPanel } from "@/components/tickets/TicketQrPanel";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  SkeletonLoader,
  StatusBadge,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  bindTicketDevice,
  setTicketQrMode,
} from "@/lib/advanced-tickets-api";
import { trackTicketDownloaded } from "@/lib/analytics";
import { downloadTicketPdf, fetchTicket } from "@/lib/commerce-api";
import {
  cacheTicketForOffline,
  readCachedTicket,
} from "@/lib/pwa/offline-ticket-cache";
import { useOnlineStatus } from "@/lib/pwa/use-online-status";
import { formatDateTime, maskEmail } from "@/lib/format";
import {
  buyerMerchStatusLabel,
  resolveBuyerMerchDisplayStatus,
} from "@/lib/merch-buyer-status";
import type { Ticket } from "@/lib/types/commerce";

export default function TicketDetailPage() {
  const params = useParams<{ id: string }>();
  const online = useOnlineStatus();
  const [ticket, setTicket] = useState<Ticket | null>(() =>
    readCachedTicket(params.id),
  );
  const [fromCache, setFromCache] = useState(
    () => Boolean(readCachedTicket(params.id)),
  );
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  async function reload() {
    const item = await fetchTicket(params.id);
    cacheTicketForOffline(item);
    setTicket(item);
    setFromCache(false);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      const cached = readCachedTicket(params.id);
      try {
        const item = await fetchTicket(params.id);
        if (!active) return;
        cacheTicketForOffline(item);
        setTicket(item);
        setFromCache(false);
        setError(null);
      } catch {
        if (!active) return;
        if (cached) {
          setTicket(cached);
          setFromCache(true);
          setNote(
            "Showing cached ticket — validation still happens at the door when online.",
          );
        } else {
          setError("Ticket not found.");
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id]);

  async function onToggleQrMode() {
    if (!ticket) return;
    setError(null);
    try {
      const next = ticket.qr_mode === "rotating" ? "static" : "rotating";
      const updated = await setTicketQrMode(params.id, next);
      cacheTicketForOffline(updated);
      setTicket(updated);
      setFromCache(false);
      setNote(`QR mode set to ${next}.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "QR mode update failed");
    }
  }

  async function onBindDevice() {
    setError(null);
    try {
      const fingerprint =
        typeof navigator !== "undefined"
          ? `${navigator.userAgent.slice(0, 80)}|${screen.width}x${screen.height}`
          : "unknown-device";
      const updated = await bindTicketDevice(params.id, fingerprint);
      cacheTicketForOffline(updated);
      setTicket(updated);
      setNote("Preferred device saved for this ticket.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Bind failed");
    }
  }

  async function onDownloadPdf() {
    if (!ticket || downloadingPdf) return;
    setError(null);
    setDownloadingPdf(true);
    try {
      await downloadTicketPdf(ticket.id);
      trackTicketDownloaded({
        targetEventId: ticket.event_id,
        ticketStatus: ticket.status,
      });
      setNote(
        ticket.status === "active"
          ? "PDF downloaded. Entry uses a static QR suitable for printing — you can switch back to rotating QR anytime."
          : "PDF downloaded. This pass is marked as not valid for entry.",
      );
      await reload();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Could not download ticket PDF.",
      );
    } finally {
      setDownloadingPdf(false);
    }
  }

  if (error && !ticket) {
    return (
      <DashboardShell
        tone="soft"
        compact
        eyebrow="Ticket"
        title="Unavailable"
        description="This ticket could not be loaded."
      >
        <EmptyState
          title="Ticket unavailable"
          description={error}
          action={
            <Link href="/dashboard/tickets">
              <Button variant="secondary">All tickets</Button>
            </Link>
          }
        />
      </DashboardShell>
    );
  }

  if (!ticket) {
    return (
      <DashboardShell
        tone="soft"
        compact
        eyebrow="Ticket"
        title="Your ticket"
        description="Preparing your digital pass…"
      >
        <SkeletonLoader lines={5} />
      </DashboardShell>
    );
  }

  const checkedIn = ticket.status === "checked_in";
  const active = ticket.status === "active";
  const canDownloadPdf =
    active ||
    checkedIn ||
    ticket.status === "cancelled" ||
    ticket.status === "refunded" ||
    ticket.status === "pending";

  return (
    <DashboardShell
      tone="soft"
      compact
      eyebrow="Digital ticket"
      title={ticket.event_title ?? "Your ticket"}
      description={`${ticket.ticket_type_name} · ${ticket.public_code}`}
      actions={
        <Link href="/dashboard/tickets">
          <Button variant="secondary" size="sm">
            All tickets
          </Button>
        </Link>
      }
    >
      {!online || fromCache ? (
        <Alert tone={!online ? "warning" : "info"} title={!online ? "Offline view" : "Cached"}>
          {!online
            ? "QR shown from local cache. Door scanners still validate server-side when connected."
            : note || "Loaded from cache while refreshing…"}
        </Alert>
      ) : null}

      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}
      {note && online ? (
        <Alert tone="info" title="Update">
          {note}
        </Alert>
      ) : null}

      <div className="mx-auto w-full max-w-md min-w-0 space-y-5 sm:max-w-lg">
        <Card
          padded={false}
          className="overflow-hidden border-border shadow-[var(--shadow-strong)]"
        >
          <div className="relative bg-ink px-5 py-5 text-paper">
            <div
              aria-hidden
              className="pointer-events-none absolute -bottom-3 left-1/2 h-6 w-6 -translate-x-1/2 rounded-full bg-surface"
            />
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-primary">
                Pàdéyá ticket
              </p>
              <StatusBadge status={ticket.status} />
            </div>
            <h2 className="mt-3 text-2xl font-extrabold tracking-tight sm:text-3xl">
              {ticket.event_title ?? "Event"}
            </h2>
            <p className="mt-1 text-base text-paper/75">{ticket.ticket_type_name}</p>
          </div>

          <div className="flex flex-col items-center gap-5 bg-surface-inset px-4 py-7 sm:px-5 sm:py-8">
            {ticket.qr_payload ? (
              <TicketQrPanel value={ticket.qr_payload} />
            ) : (
              <p className="text-base text-muted-foreground">
                QR not available{fromCache ? " in cache" : ""}.
              </p>
            )}
            <div className="text-center">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-muted-foreground">
                Entry code
              </p>
              <p className="mt-1 break-all font-mono text-2xl font-extrabold tracking-wide text-foreground sm:text-3xl">
                {ticket.public_code}
              </p>
            </div>
            <p className="max-w-sm text-center text-sm leading-relaxed text-muted-foreground">
              Brighten your screen at the door. Live QR only — screenshots are not
              proof of entry.
              {ticket.qr_mode === "rotating"
                ? " Rotating mode needs a connection to refresh."
                : ""}
            </p>
          </div>

          <div className="grid gap-4 border-t border-dashed border-border px-5 py-5 sm:grid-cols-2">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
                Holder
              </p>
              <p className="mt-1 text-base font-bold text-foreground">
                {ticket.holder_name}
              </p>
              <p className="text-sm text-muted-foreground">
                {maskEmail(ticket.holder_email)}
              </p>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
                Check-in
              </p>
              <p className="mt-1 text-base font-bold text-foreground">
                {checkedIn ? "Checked in" : "Not checked in"}
              </p>
              <p className="text-sm text-muted-foreground">
                QR mode: {ticket.qr_mode ?? "static"}
                {ticket.device_bound ? " · device bound" : ""}
              </p>
            </div>
            {ticket.table_label ? (
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
                  Table / seat
                </p>
                <p className="mt-1 text-base font-bold text-foreground">
                  {ticket.table_label}
                  {ticket.seat_label ? ` · ${ticket.seat_label}` : ""}
                </p>
              </div>
            ) : null}
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground">
                Issued
              </p>
              <p className="mt-1 text-base font-semibold text-foreground">
                {formatDateTime(ticket.created_at)}
              </p>
            </div>
          </div>
        </Card>

        {(ticket.linked_merch?.length ?? 0) > 0 ? (
          <Card className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-base font-extrabold text-foreground">
                Merch included
              </h3>
              <Link href={`/dashboard/orders/${ticket.order_id}`}>
                <Button size="sm" variant="secondary">
                  Order
                </Button>
              </Link>
            </div>
            <p className="text-sm text-muted-foreground">
              Pickup at the event — codes and status also live under Merchandise.
            </p>
            <ul className="space-y-3">
              {ticket.linked_merch?.map((row) => {
                const display = resolveBuyerMerchDisplayStatus({
                  displayStatus: row.display_status,
                  fulfillmentStatus: row.status,
                });
                const label = buyerMerchStatusLabel(display);
                return (
                  <li
                    key={row.id}
                    className="space-y-1 border-b border-border pb-3 last:border-0 last:pb-0"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-bold text-foreground">
                        {row.product_name} · {row.variant_label}
                      </p>
                      <StatusBadge status={display} label={label} />
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Qty {row.quantity}
                      {row.pickup_code ? ` · ${row.pickup_code}` : ""}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Pickup status: {label}
                    </p>
                    {row.pickup_instructions ? (
                      <p className="text-xs text-muted-foreground">
                        {row.pickup_instructions}
                      </p>
                    ) : null}
                  </li>
                );
              })}
            </ul>
            <Link href="/dashboard/merchandise">
              <Button size="sm" variant="ghost">
                All merchandise
              </Button>
            </Link>
          </Card>
        ) : null}

        {canDownloadPdf && online ? (
          <div className="space-y-3">
            <Button
              size="lg"
              className="w-full"
              disabled={downloadingPdf}
              onClick={() => void onDownloadPdf()}
            >
              {downloadingPdf ? "Preparing PDF…" : "Download PDF"}
            </Button>
            {active ? (
              <>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Link
                    href={`/dashboard/tickets/${ticket.id}/transfer`}
                    className="flex-1"
                  >
                    <Button className="w-full" size="lg" variant="secondary">
                      Transfer ticket
                    </Button>
                  </Link>
                  <Button
                    size="lg"
                    variant="secondary"
                    className="w-full flex-1"
                    onClick={() => void onToggleQrMode()}
                  >
                    {ticket.qr_mode === "rotating"
                      ? "Use static QR"
                      : "Use rotating QR"}
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {!ticket.device_bound ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => void onBindDevice()}
                    >
                      Bind this device
                    </Button>
                  ) : null}
                  <CancelTicketButton
                    ticketId={ticket.id}
                    reason="Buyer cancellation"
                    onCancelled={async () => {
                      setError(null);
                      setNote(
                        "Ticket cancelled permanently. QR will fail validation and cannot be restored.",
                      );
                      await reload();
                    }}
                    onError={(message) => setError(message)}
                  />
                </div>
              </>
            ) : null}
          </div>
        ) : null}

        <Alert tone="info" title="Door tip">
          Staff scan live QR or public codes. Cancelled or already-used tickets are
          rejected at the door.
        </Alert>
      </div>
    </DashboardShell>
  );
}
