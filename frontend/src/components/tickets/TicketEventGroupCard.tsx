"use client";

import Link from "next/link";
import { useState } from "react";

import { StartMessageButton } from "@/components/messaging/StartMessageButton";
import { TicketPassCard } from "@/components/tickets/TicketPassCard";
import { Badge, Button, Media, useToast } from "@/components/ui";
import {
  trackTicketDownloaded,
  trackTicketEventClicked,
  trackTicketGroupExpanded,
} from "@/lib/analytics";
import { cn } from "@/lib/cn";
import { downloadTicketPdf } from "@/lib/commerce-api";
import {
  groupCheckedInCount,
  groupReadyCount,
  isCancelledLike,
  ticketStatusPresentation,
  type TicketEventGroup,
} from "@/lib/tickets/buyer-ticket-groups";
import type { Ticket } from "@/lib/types/commerce";

function formatEventWhen(startsAt: string | null): string {
  if (!startsAt) return "Date TBA";
  const d = new Date(startsAt);
  if (Number.isNaN(d.getTime())) return "Date TBA";
  const date = d.toLocaleDateString("en-NG", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
  const time = d.toLocaleTimeString("en-NG", {
    hour: "numeric",
    minute: "2-digit",
  });
  return `${date} · ${time}`;
}

function eventHref(group: TicketEventGroup): string | null {
  if (group.eventSlug) return `/events/${group.eventSlug}`;
  return null;
}

function calendarHref(group: TicketEventGroup): string | null {
  if (!group.startsAt) return null;
  const start = new Date(group.startsAt);
  if (Number.isNaN(start.getTime())) return null;
  const end = group.endsAt ? new Date(group.endsAt) : new Date(start.getTime() + 3 * 3600_000);
  const fmt = (d: Date) =>
    d
      .toISOString()
      .replace(/[-:]/g, "")
      .replace(/\.\d{3}Z$/, "Z");
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: group.eventTitle,
    dates: `${fmt(start)}/${fmt(end)}`,
    details: "Pàdéyá ticket — open your QR at entry.",
    location: group.locationLabel || "",
  });
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

export function TicketEventGroupCard({
  group,
  defaultOpen = false,
  tone = "active",
  onViewQr,
  showLeaveReview = true,
  showMessageHost = true,
}: {
  group: TicketEventGroup;
  defaultOpen?: boolean;
  tone?: "active" | "past" | "cancelled";
  onViewQr: (ticket: Ticket) => void;
  /** Hide leave-review CTA for events the viewer owns (not team/staff). */
  showLeaveReview?: boolean;
  /** Hide Personal→own-host messaging CTAs. */
  showMessageHost?: boolean;
}) {
  const { push } = useToast();
  const [open, setOpen] = useState(defaultOpen);
  const [downloadingAll, setDownloadingAll] = useState(false);
  const href = eventHref(group);
  const readyCount = groupReadyCount(group);
  const checkedInCount = groupCheckedInCount(group);
  const inactiveCount = group.tickets.filter((t) => isCancelledLike(t)).length;
  const allInactive =
    inactiveCount === group.tickets.length && group.tickets.length > 0;
  const messageBtnId = `msg-host-${group.eventId}`;
  const cal = calendarHref(group);

  function toggleTickets() {
    const next = !open;
    setOpen(next);
    trackTicketGroupExpanded({
      targetEventId: group.eventId,
      expanded: next,
    });
  }

  async function downloadAll() {
    const downloadable = group.tickets.filter(
      (t) => ticketStatusPresentation(t).canDownloadPdf,
    );
    if (!downloadable.length || downloadingAll) return;
    setDownloadingAll(true);
    try {
      for (const ticket of downloadable) {
        await downloadTicketPdf(ticket.id);
        trackTicketDownloaded({
          targetEventId: ticket.event_id,
          ticketStatus: ticket.status,
        });
      }
      push({
        title: "Downloads started",
        description: `${downloadable.length} pass${downloadable.length === 1 ? "" : "es"}`,
        tone: "success",
      });
    } catch (err) {
      push({
        title: "Download failed",
        description: err instanceof Error ? err.message : "Try again",
        tone: "danger",
      });
    } finally {
      setDownloadingAll(false);
    }
  }

  return (
    <article
      className={cn(
        "rounded-[var(--radius-xl)] border bg-card shadow-[var(--shadow-soft)] dark:bg-surface-elevated",
        tone === "active" && readyCount > 0 && "border-border",
        tone === "past" && "border-border/80 bg-card/80",
        tone === "cancelled" && "border-border/70 opacity-95",
        allInactive && "opacity-90",
      )}
    >
      <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-stretch sm:p-5">
        <button
          type="button"
          onClick={toggleTickets}
          className={cn(
            "relative h-24 w-full shrink-0 overflow-hidden rounded-[var(--radius-md)] bg-muted text-left sm:h-auto sm:w-32",
            (allInactive || tone !== "active") && "grayscale-[0.25]",
          )}
          aria-expanded={open}
          aria-label={`${open ? "Hide" : "Show"} tickets for ${group.eventTitle}`}
        >
          {group.eventCoverUrl ? (
            <Media
              src={group.eventCoverUrl}
              alt=""
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full min-h-[6rem] items-center justify-center bg-ink text-sm font-extrabold text-accent sm:min-h-full">
              Pàdéyá
            </div>
          )}
        </button>

        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <button
            type="button"
            onClick={toggleTickets}
            className="min-w-0 space-y-1.5 text-left"
            aria-expanded={open}
          >
            <h3
              className={cn(
                "text-balance text-lg font-extrabold tracking-tight sm:text-xl",
                allInactive || tone === "cancelled"
                  ? "text-muted-foreground"
                  : "text-heading",
              )}
            >
              {group.eventTitle}
            </h3>
            <p className="text-sm text-muted-foreground">
              {[formatEventWhen(group.startsAt), group.locationLabel, group.hostName]
                .filter(Boolean)
                .join(" · ") || "Details on the event page"}
            </p>
            <div className="flex flex-wrap items-center gap-2 pt-0.5">
              <Badge tone="outline" size="sm">
                {group.tickets.length} ticket
                {group.tickets.length === 1 ? "" : "s"}
              </Badge>
              {tone === "active" && readyCount > 0 ? (
                <Badge tone="success" size="sm">
                  {readyCount} ready
                </Badge>
              ) : null}
              {tone === "past" ? (
                <Badge tone="neutral" size="sm">
                  {checkedInCount} checked in
                </Badge>
              ) : null}
              {tone === "cancelled" || allInactive ? (
                <Badge tone="neutral" size="sm">
                  Not valid for entry
                </Badge>
              ) : null}
            </div>
          </button>

          <div className="mt-auto flex flex-wrap gap-2">
            <Button
              size="sm"
              variant={readyCount > 0 && tone === "active" ? "primary" : "secondary"}
              aria-expanded={open}
              onClick={toggleTickets}
            >
              {open ? "Hide tickets" : "View tickets"}
            </Button>
            {href ? (
              <Link
                href={href}
                onClick={() =>
                  trackTicketEventClicked({
                    targetEventId: group.eventId,
                    hostId: group.hostId || undefined,
                  })
                }
              >
                <Button size="sm" variant="secondary">
                  View event
                </Button>
              </Link>
            ) : null}
            {group.hostId && tone !== "cancelled" && showMessageHost ? (
              <StartMessageButton
                id={messageBtnId}
                hostId={group.hostId}
                hostUsername={group.hostUsername || undefined}
                relatedEventId={group.eventId}
                label="Message host"
                size="sm"
                variant="ghost"
                returnPath="/dashboard/tickets"
              />
            ) : null}
            {tone === "active" && group.tickets.length > 1 ? (
              <Button
                size="sm"
                variant="ghost"
                disabled={downloadingAll}
                onClick={() => void downloadAll()}
              >
                {downloadingAll ? "Downloading…" : "Download all"}
              </Button>
            ) : null}
            {tone === "past" && showLeaveReview ? (
              <Link href={`/dashboard/reviews?ticket_id=${group.tickets[0]?.id ?? ""}`}>
                <Button size="sm" variant="ghost">
                  Leave review
                </Button>
              </Link>
            ) : null}
            {tone === "cancelled" ? (
              <>
                <Link href={`/dashboard/orders/${group.tickets[0]?.order_id}`}>
                  <Button size="sm" variant="secondary">
                    View order
                  </Button>
                </Link>
                <Link href="/support">
                  <Button size="sm" variant="ghost">
                    Contact support
                  </Button>
                </Link>
              </>
            ) : null}
            {cal && tone === "active" ? (
              <a href={cal} target="_blank" rel="noopener noreferrer">
                <Button size="sm" variant="ghost">
                  Add to calendar
                </Button>
              </a>
            ) : null}
          </div>
        </div>
      </div>

      {open ? (
        <div
          className={cn(
            "space-y-3 border-t px-4 py-4 sm:px-5",
            tone === "cancelled"
              ? "border-border/70 bg-muted/40"
              : "border-border bg-muted/25",
          )}
        >
          {tone === "cancelled" ? (
            <p className="text-sm text-muted-foreground">
              This ticket is no longer valid for entry.
            </p>
          ) : null}
          <div className="space-y-2.5">
            {group.tickets.map((ticket) => (
              <TicketPassCard
                key={ticket.id}
                ticket={ticket}
                hostId={group.hostId}
                hostUsername={group.hostUsername}
                onViewQr={onViewQr}
                onMessageHost={
                  showMessageHost
                    ? () => {
                        document.getElementById(messageBtnId)?.click();
                      }
                    : undefined
                }
                onNotice={(message) =>
                  push({ title: message, tone: "success" })
                }
                onError={(message) =>
                  push({ title: message, tone: "danger" })
                }
              />
            ))}
          </div>
        </div>
      ) : null}
    </article>
  );
}
