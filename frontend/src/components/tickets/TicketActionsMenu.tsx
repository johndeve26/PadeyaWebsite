"use client";

import { useRouter } from "next/navigation";

import { Dropdown } from "@/components/ui";
import {
  trackTicketDetailsClicked,
  trackTicketDownloaded,
  trackTicketEventClicked,
} from "@/lib/analytics";
import { downloadTicketPdf } from "@/lib/commerce-api";
import {
  isCancelledLike,
  shortenPublicCode,
  ticketStatusPresentation,
} from "@/lib/tickets/buyer-ticket-groups";
import type { Ticket } from "@/lib/types/commerce";

async function copyText(value: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    return false;
  }
}

function eventHref(ticket: Ticket): string | null {
  if (ticket.event_slug) return `/events/${ticket.event_slug}`;
  return null;
}

export function TicketActionsMenu({
  ticket,
  hostId,
  onMessageHost,
  onCopied,
  onError,
  align = "right",
}: {
  ticket: Ticket;
  hostId?: string | null;
  hostUsername?: string | null;
  onMessageHost?: () => void;
  onCopied?: (label: string) => void;
  onError?: (message: string) => void;
  align?: "left" | "right";
}) {
  const router = useRouter();
  const presentation = ticketStatusPresentation(ticket);
  const href = eventHref(ticket);
  const inactive = isCancelledLike(ticket);

  return (
    <Dropdown
      label="More"
      align={align}
      menuPlacement="auto"
      items={[
        {
          id: "download",
          label: "Download PDF",
          disabled: !presentation.canDownloadPdf,
          onSelect: () => {
            void (async () => {
              try {
                await downloadTicketPdf(ticket.id);
                trackTicketDownloaded({
                  targetEventId: ticket.event_id,
                  ticketStatus: ticket.status,
                });
              } catch (err) {
                onError?.(
                  err instanceof Error ? err.message : "PDF download failed",
                );
              }
            })();
          },
        },
        {
          id: "copy",
          label: "Copy entry code",
          onSelect: () => {
            void (async () => {
              const ok = await copyText(ticket.public_code);
              if (ok) {
                onCopied?.(
                  `Copied ${shortenPublicCode(ticket.public_code)}`,
                );
              } else {
                onError?.("Could not copy entry code");
              }
            })();
          },
        },
        {
          id: "event",
          label: "View event",
          disabled: !href,
          onSelect: () => {
            if (!href) return;
            trackTicketEventClicked({
              targetEventId: ticket.event_id,
              hostId: hostId || undefined,
            });
            router.push(href);
          },
        },
        ...(onMessageHost
          ? [
              {
                id: "message",
                label: "Message host",
                disabled: !hostId || inactive,
                onSelect: () => {
                  onMessageHost();
                },
              },
            ]
          : []),
        {
          id: "details",
          label: "View ticket details",
          onSelect: () => {
            trackTicketDetailsClicked({
              targetEventId: ticket.event_id,
              ticketStatus: ticket.status,
            });
            router.push(`/dashboard/tickets/${ticket.id}`);
          },
        },
        {
          id: "transfer",
          label: "Transfer ticket",
          disabled:
            inactive ||
            (ticket.status || "").toLowerCase() !== "active" ||
            Boolean(ticket.checked_in_at),
          onSelect: () => {
            router.push(`/dashboard/tickets/${ticket.id}/transfer`);
          },
        },
        {
          id: "support",
          label: inactive ? "Contact support" : "Report issue",
          onSelect: () => {
            router.push("/support");
          },
        },
        ...(inactive
          ? [
              {
                id: "order",
                label: "View order",
                onSelect: () => {
                  router.push(`/dashboard/orders/${ticket.order_id}`);
                },
              },
            ]
          : []),
      ]}
    />
  );
}
