"use client";

import Link from "next/link";
import { useState } from "react";

import { MerchPickupQrModal } from "@/components/merch/buyer/MerchPickupQrModal";
import { SectionLabel } from "@/components/personal/command-center/SectionLabel";
import { TicketQrModal } from "@/components/tickets/TicketQrModal";
import { Button, Card, SkeletonLoader } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import type { BuyerCart } from "@/lib/merch-api";
import {
  isTicketQrSoon,
  resolveNextUp,
  safeTicketLocationLabel,
} from "@/lib/personal-command-center";
import { ticketStatusPresentation } from "@/lib/tickets/buyer-ticket-groups";
import type { Ticket } from "@/lib/types/commerce";
import type { MerchFulfillment } from "@/lib/types/merch";

/**
 * Next up priority: active ticket → merch pickup → cart → Browse events.
 * Open QR uses TicketQrModal only — never render raw QR token text here.
 * Location uses ticket.location_label from the API only.
 */
export function NextUpSection({
  loading,
  tickets,
  merch,
  cart,
}: {
  loading: boolean;
  tickets: Ticket[] | null;
  merch: MerchFulfillment[] | null;
  cart: BuyerCart | null;
}) {
  const [qrTicketId, setQrTicketId] = useState<string | null>(null);
  const [merchQrId, setMerchQrId] = useState<string | null>(null);

  if (loading) {
    return (
      <section className="min-w-0 space-y-3">
        <SectionLabel>Next up</SectionLabel>
        <SkeletonLoader lines={4} />
      </section>
    );
  }

  const { primary, merchReminder } = resolveNextUp({
    tickets: tickets ?? [],
    merch: merch ?? [],
    cart,
  });

  const nextTicket = primary.kind === "ticket" ? primary.ticket : null;
  const primaryMerch = primary.kind === "merch" ? primary.merch : null;
  const pickupMerch = merchReminder || primaryMerch;
  const canOpenQr = nextTicket
    ? ticketStatusPresentation(nextTicket).showQr
    : false;
  const entrySoon = Boolean(
    nextTicket && canOpenQr && isTicketQrSoon(nextTicket),
  );
  const location = nextTicket ? safeTicketLocationLabel(nextTicket) : null;

  return (
    <section className="min-w-0 space-y-3">
      <SectionLabel>Next up</SectionLabel>
      <Card className="min-w-0 space-y-4" variant="accent">
        {primary.kind === "empty" ? (
          <div className="min-w-0 space-y-3">
            <h2 className="text-lg font-bold tracking-tight text-foreground">
              No upcoming activity
            </h2>
            <p className="text-sm text-muted-foreground">
              Browse events on Pàdéyá to find your next night out.
            </p>
            <Link href="/events">
              <Button size="sm">Browse events</Button>
            </Link>
          </div>
        ) : null}

        {nextTicket ? (
          <div className="min-w-0 space-y-3">
            <div className="min-w-0">
              <h2 className="break-words text-lg font-bold tracking-tight text-foreground">
                {nextTicket.event_title || "Upcoming event"}
              </h2>
              <p className="mt-1 break-words text-sm text-muted-foreground">
                {formatDateTime(nextTicket.event_starts_at)}
                {nextTicket.ticket_type_name
                  ? ` · ${nextTicket.ticket_type_name}`
                  : ""}
                {location ? ` · ${location}` : ""}
              </p>
              {entrySoon ? (
                <p className="mt-2 text-sm font-semibold text-foreground">
                  Entry soon — open your QR when you arrive.
                </p>
              ) : null}
            </div>
            <div className="flex min-w-0 flex-wrap gap-2">
              {canOpenQr ? (
                <Button
                  size="sm"
                  onClick={() => setQrTicketId(nextTicket.id)}
                >
                  Open QR
                </Button>
              ) : (
                <Link href={`/dashboard/tickets/${nextTicket.id}`}>
                  <Button size="sm">View ticket</Button>
                </Link>
              )}
              <Link href={`/dashboard/tickets/${nextTicket.id}`}>
                <Button size="sm" variant="secondary">
                  Ticket details
                </Button>
              </Link>
            </div>
          </div>
        ) : null}

        {pickupMerch ? (
          <div
            className={
              nextTicket
                ? "min-w-0 space-y-2 border-t border-border/60 pt-4"
                : "min-w-0 space-y-2"
            }
          >
            <p className="text-sm font-semibold text-foreground">
              Merch ready for pickup
            </p>
            <p className="break-words text-sm text-muted-foreground">
              {pickupMerch.product_name_snapshot || "Item"}
              {pickupMerch.event_title ? ` · ${pickupMerch.event_title}` : ""}
            </p>
            <div className="flex min-w-0 flex-wrap gap-2">
              <Button
                size="sm"
                onClick={() =>
                  setMerchQrId(pickupMerch.order_item_id || pickupMerch.id)
                }
              >
                Open pickup QR
              </Button>
              <Link href="/dashboard/merchandise">
                <Button size="sm" variant="secondary">
                  Open Merch
                </Button>
              </Link>
            </div>
          </div>
        ) : null}

        {primary.kind === "cart" ? (
          <div className="min-w-0 space-y-2">
            <h2 className="text-lg font-bold tracking-tight text-foreground">
              Cart waiting
            </h2>
            <p className="text-sm text-muted-foreground">
              {primary.cartLines} item
              {primary.cartLines === 1 ? "" : "s"} left — resume checkout when
              you are ready.
            </p>
            <Link href={primary.resumePath}>
              <Button size="sm">Resume checkout</Button>
            </Link>
          </div>
        ) : null}
      </Card>

      {qrTicketId ? (
        <TicketQrModal
          ticketId={qrTicketId}
          open
          onClose={() => setQrTicketId(null)}
        />
      ) : null}
      {merchQrId && pickupMerch ? (
        <MerchPickupQrModal
          orderItemId={merchQrId}
          seed={pickupMerch}
          open
          onClose={() => setMerchQrId(null)}
        />
      ) : null}
    </section>
  );
}
