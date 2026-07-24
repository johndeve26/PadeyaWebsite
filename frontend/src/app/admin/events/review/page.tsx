"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Card,
  ConfirmAction,
  EmptyState,
  SkeletonLoader,
  StatusBadge,
  Textarea,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { approveEvent, clearEventFlag, fetchPendingEvents, rejectEvent } from "@/lib/events-api";
import { formatDateTime } from "@/lib/format";
import type { EventItem } from "@/lib/types/events";

function EventPreviewCard({
  event,
  reason,
  onReasonChange,
  onApprove,
  onReject,
  onMarkReviewed,
}: {
  event: EventItem;
  reason: string;
  onReasonChange: (value: string) => void;
  onApprove: () => Promise<void>;
  onReject: () => Promise<void>;
  onMarkReviewed: () => Promise<void>;
}) {
  const location = [event.venue_name, event.city, event.state]
    .filter(Boolean)
    .join(", ");
  const ticketCount = event.ticket_types?.length ?? 0;
  const alreadyPublished = event.status === "published";
  const flagged = Boolean(event.admin_flagged || event.admin_flagged_at);

  return (
    <Card className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row">
        {event.banner_url ? (
          <div className="shrink-0 overflow-hidden rounded-[var(--radius-md)] border border-border sm:w-40">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={event.banner_url}
              alt=""
              className="aspect-video w-full object-cover sm:aspect-square"
            />
          </div>
        ) : null}
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-bold text-foreground">{event.title}</h3>
            <StatusBadge status={event.status} />
            {flagged ? <StatusBadge status="pending_review" label="Needs review" /> : null}
            {event.category?.name ? (
              <StatusBadge status="draft" label={event.category.name} />
            ) : null}
          </div>
          <p className="line-clamp-3 text-sm leading-relaxed text-muted-foreground">
            {event.description}
          </p>
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-sm font-bold uppercase tracking-[0.08em] text-muted-foreground">
                Host
              </dt>
              <dd className="font-semibold text-foreground">
                {event.host_display_name ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-bold uppercase tracking-[0.08em] text-muted-foreground">
                Schedule
              </dt>
              <dd className="text-foreground">
                {formatDateTime(event.start_datetime)}
                {event.end_datetime
                  ? ` – ${formatDateTime(event.end_datetime)}`
                  : ""}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-bold uppercase tracking-[0.08em] text-muted-foreground">
                Location
              </dt>
              <dd className="text-foreground">{location || "TBA"}</dd>
            </div>
            <div>
              <dt className="text-sm font-bold uppercase tracking-[0.08em] text-muted-foreground">
                Details
              </dt>
              <dd className="text-foreground">
                {event.capacity ? `${event.capacity} capacity` : "Capacity TBA"}
                {ticketCount > 0 ? ` · ${ticketCount} ticket type${ticketCount === 1 ? "" : "s"}` : ""}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {alreadyPublished ? (
        <Alert tone="info" title="Already live">
          This event is published. Mark reviewed when you have checked the listing,
          or open the full review page to pause or flag it.
        </Alert>
      ) : (
        <Textarea
          label="Rejection reason"
          hint="Required if you reject. Sent to the host with audit trail."
          value={reason}
          onChange={(e) => onReasonChange(e.target.value)}
          className="min-h-[80px]"
          placeholder="Explain what must change before this event can publish…"
        />
      )}

      <div className="flex flex-wrap gap-2">
        {alreadyPublished ? (
          <ConfirmAction
            label="Mark reviewed"
            title="Mark this event reviewed?"
            description={`Clear the review flag on “${event.title}”. The listing stays live.`}
            confirmLabel="Mark reviewed"
            size="md"
            variant="dark"
            onConfirm={onMarkReviewed}
          />
        ) : (
          <>
            <ConfirmAction
              label="Approve & publish"
              title="Approve this event?"
              description={`Publish “${event.title}” to Pàdéyá. The host will be notified.`}
              confirmLabel="Approve & publish"
              size="md"
              variant="dark"
              onConfirm={onApprove}
            />
            <ConfirmAction
              label="Reject"
              title="Reject this event?"
              description={`Reject “${event.title}”. The host receives your reason below.`}
              confirmLabel="Reject event"
              tone="danger"
              size="md"
              disabled={!reason.trim()}
              onConfirm={onReject}
            >
              {reason.trim() ? (
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Reason sent to host:
                  </p>
                  <p className="rounded-[var(--radius-md)] border border-border bg-muted px-3 py-2 text-sm whitespace-pre-wrap">
                    {reason.trim()}
                  </p>
                </div>
              ) : (
                <p className="text-sm text-danger">
                  Add a rejection reason before continuing.
                </p>
              )}
            </ConfirmAction>
          </>
        )}
      </div>
    </Card>
  );
}

export default function AdminEventReviewPage() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadPending = useCallback(async () => {
    const items = await fetchPendingEvents();
    setEvents(items);
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const items = await fetchPendingEvents();
        if (active) setEvents(items);
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Failed to load queue");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onMarkReviewed(id: string) {
    setError(null);
    try {
      await clearEventFlag(id);
      await loadPending();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not mark reviewed");
    }
  }

  async function onApprove(id: string) {
    setError(null);
    try {
      await approveEvent(id);
      await loadPending();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Approve failed");
    }
  }

  async function onReject(id: string) {
    const reason = reasons[id]?.trim();
    if (!reason) {
      setError("Rejection reason is required");
      return;
    }
    setError(null);
    try {
      await rejectEvent(id, reason);
      setReasons((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      await loadPending();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Reject failed");
    }
  }

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin review"
      title="Event review queue"
      description="Review newly published or pending listings. Mark reviewed when done, or approve/reject events still awaiting first publish."
    >
      {error ? (
        <Alert tone="danger" title="Action failed">
          {error}
        </Alert>
      ) : null}

      {loading && !error ? <SkeletonLoader lines={4} /> : null}

      {!loading && events.length > 0 ? (
        <Alert tone="info" title={`${events.length} event${events.length === 1 ? "" : "s"} awaiting review`}>
          Auto-published events stay live while flagged here. Legacy pending submissions still need approve or reject.
        </Alert>
      ) : null}

      {!loading ? (
      <div className="space-y-4">
        {!loading && events.length === 0 ? (
          <EmptyState
            title="Queue is clear"
            description="No flagged or pending events right now. New host publishes will appear here for post-publish review."
          />
        ) : (
          events.map((event) => (
            <div key={event.id} className="space-y-2">
              <div className="flex justify-end">
                <Link
                  href={`/admin/events/${event.id}/review`}
                  className="text-sm font-semibold text-primary hover:underline"
                >
                  Open full review →
                </Link>
              </div>
            <EventPreviewCard
              event={event}
              reason={reasons[event.id] ?? ""}
              onReasonChange={(value) =>
                setReasons((prev) => ({ ...prev, [event.id]: value }))
              }
              onApprove={() => onApprove(event.id)}
              onReject={() => onReject(event.id)}
              onMarkReviewed={() => onMarkReviewed(event.id)}
            />
            </div>
          ))
        )}
      </div>
      ) : null}
    </DashboardShell>
  );
}
