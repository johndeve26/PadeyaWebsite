"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmAction,
  SkeletonLoader,
  StatusBadge,
  Textarea,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  clearEventPadeyaPick,
  setEventPadeyaPick,
} from "@/lib/admin-lifecycle-api";
import {
  clearEventFlag,
  fetchEventById,
  flagEvent,
  pauseEvent,
  regeocodeAdminEvent,
  rejectEvent,
  resumeEvent,
} from "@/lib/events-api";
import { formatDateTime } from "@/lib/format";
import { fetchFeaturedPlacements } from "@/lib/placements-api";
import type { EventItem } from "@/lib/types/events";

export default function AdminEventReviewDetailPage() {
  const params = useParams();
  const eventId = String(params.id ?? "");
  const toast = useToast();
  const [event, setEvent] = useState<EventItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [flagReason, setFlagReason] = useState("");
  const [isPadeyaPick, setIsPadeyaPick] = useState(false);
  const [pickLabel, setPickLabel] = useState<string | null>(null);

  const load = useCallback(async () => {
    const data = await fetchEventById(eventId);
    setEvent(data);
    try {
      const slots = await fetchFeaturedPlacements({ context_type: "homepage" });
      const hit = slots.find(
        (s) =>
          s.event_id === eventId &&
          (s.status === "active" || s.status === "scheduled"),
      );
      setIsPadeyaPick(Boolean(hit));
      setPickLabel(hit?.slot_label ?? null);
    } catch {
      setIsPadeyaPick(false);
      setPickLabel(null);
    }
  }, [eventId]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await load();
        if (active) setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load event",
          );
          setEvent(null);
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [load]);

  async function run(action: () => Promise<EventItem>, success: string) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await load();
      toast.push({ tone: "success", title: success });
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Action failed";
      setError(detail);
      toast.push({ tone: "danger", title: "Action failed", description: detail });
    } finally {
      setBusy(false);
    }
  }

  const location = event
    ? [event.venue_name, event.city, event.state].filter(Boolean).join(", ")
    : "";
  const ticketCount = event?.ticket_types?.length ?? 0;
  const flagged = Boolean(event?.admin_flagged || event?.admin_flagged_at);

  return (
    <DashboardShell
      tone="soft"
      eyebrow="Admin review"
      title={event?.title ?? "Event review"}
      description="Inspect any listing, approve pending events, pause live ones, or flag for ops follow-up."
      actions={
        <div className="flex flex-wrap gap-2">
          <Link href="/admin/events">
            <Button variant="secondary">All events</Button>
          </Link>
          <Link href="/admin/events/review">
            <Button variant="secondary">Pending queue</Button>
          </Link>
          {event ? (
            <Link href={`/events/${encodeURIComponent(event.slug)}`}>
              <Button variant="ghost">Public page</Button>
            </Link>
          ) : null}
        </div>
      }
    >
      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}

      {loading ? <SkeletonLoader lines={8} /> : null}

      {!loading && event ? (
        <div className="space-y-4">
          <Card className="space-y-4">
            <div className="flex flex-col gap-4 sm:flex-row">
              {event.banner_url ? (
                <div className="shrink-0 overflow-hidden rounded-[var(--radius-md)] border border-border sm:w-44">
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
                  <h2 className="text-xl font-extrabold tracking-tight text-heading">
                    {event.title}
                  </h2>
                  <StatusBadge status={event.status} />
                  {flagged ? <Badge tone="warning">Flagged</Badge> : null}
                  {event.featured ? <Badge tone="accent">Featured</Badge> : null}
                  {isPadeyaPick ? (
                    <Badge tone="accent">
                      Pàdéyá Pick{pickLabel ? ` · ${pickLabel}` : ""}
                    </Badge>
                  ) : null}
                </div>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {event.description}
                </p>
                <dl className="grid gap-3 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                      Host
                    </dt>
                    <dd className="font-semibold text-foreground">
                      {event.host_display_name ?? "—"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
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
                    <dt className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                      Location
                    </dt>
                    <dd className="text-foreground">{location || "TBA"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-bold uppercase tracking-[0.08em] text-muted-foreground">
                      Details
                    </dt>
                    <dd className="text-foreground">
                      {event.capacity
                        ? `${event.capacity} capacity`
                        : "Capacity TBA"}
                      {ticketCount > 0
                        ? ` · ${ticketCount} ticket type${ticketCount === 1 ? "" : "s"}`
                        : ""}
                    </dd>
                  </div>
                </dl>
                {event.rejection_reason ? (
                  <Alert tone="warning" title="Rejection reason on file">
                    {event.rejection_reason}
                  </Alert>
                ) : null}
                {flagged && event.admin_flag_reason ? (
                  <Alert tone="warning" title="Admin flag">
                    {event.admin_flag_reason}
                  </Alert>
                ) : null}
                {event.has_valid_coordinates === false ||
                (!event.latitude && !event.longitude) ? (
                  <Alert tone="warning" title="Missing map coordinates">
                    This event won’t rank in nearby discovery until lat/lng are
                    set. Re-geocode from the address if Google Places is
                    configured on the API.
                    <div className="mt-3">
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={busy}
                        onClick={() =>
                          void run(
                            () => regeocodeAdminEvent(event.id),
                            "Coordinates updated",
                          )
                        }
                      >
                        Re-geocode location
                      </Button>
                    </div>
                  </Alert>
                ) : (
                  <p className="text-xs font-semibold text-primary">
                    Coordinates present
                    {event.google_place_id ? " · Places ID saved" : ""}.
                  </p>
                )}
              </div>
            </div>
          </Card>

          <Card className="space-y-4">
            <h3 className="text-base font-bold text-heading">Moderation</h3>
            <div className="flex flex-wrap gap-2">
              <Link href={`/admin/events/${event.id}/buyers`}>
                <Button size="sm" variant="secondary">
                  Buyers
                </Button>
              </Link>
              <Link href={`/admin/events/${event.id}/exports`}>
                <Button size="sm" variant="secondary">
                  Exports
                </Button>
              </Link>
              <Link href={`/admin/events/${event.id}/analytics`}>
                <Button size="sm" variant="secondary">
                  Analytics
                </Button>
              </Link>
              <Link href="/admin/events/picks">
                <Button size="sm" variant="ghost">
                  Manage Pàdéyá Picks
                </Button>
              </Link>
            </div>

            {event.status === "published" ? (
              <div className="space-y-2 border-t border-border pt-4">
                <p className="text-sm text-muted-foreground">
                  Homepage Pàdéyá Picks use Featured Placement Slots. Only
                  published, public-safe listings appear on the public surface.
                </p>
                {isPadeyaPick ? (
                  <ConfirmAction
                    label="Remove Pàdéyá Pick"
                    title="Remove from homepage Pàdéyá Picks?"
                    description={`“${event.title}” will leave the homepage spotlights.`}
                    confirmLabel="Remove Pick"
                    size="md"
                    busy={busy}
                    onConfirm={() =>
                      run(
                        () =>
                          clearEventPadeyaPick(event.id, {
                            context_type: "homepage",
                          }),
                        "Removed from Pàdéyá Picks",
                      )
                    }
                  />
                ) : (
                  <ConfirmAction
                    label="Add as Pàdéyá Pick"
                    title="Add to homepage Pàdéyá Picks?"
                    description={`“${event.title}” will fill the next empty Primary/Secondary spotlight on the homepage.`}
                    confirmLabel="Add Pick"
                    size="md"
                    busy={busy}
                    onConfirm={() =>
                      run(
                        () =>
                          setEventPadeyaPick(event.id, {
                            context_type: "homepage",
                          }),
                        "Added to Pàdéyá Picks",
                      )
                    }
                  />
                )}
              </div>
            ) : null}

            {event.status === "published" && flagged ? (
              <div className="space-y-3 border-t border-border pt-4">
                <p className="text-sm text-muted-foreground">
                  This listing is live and flagged for post-publish review. Mark
                  reviewed when checked, reject to take it down, or pause sales.
                </p>
                <Textarea
                  label="Rejection reason"
                  hint="Required if you reject. Sent to the host with audit trail."
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Explain why this listing must come down…"
                />
                <div className="flex flex-wrap gap-2">
                  <ConfirmAction
                    label="Mark reviewed"
                    title="Mark this event reviewed?"
                    description="Clears the review flag. The listing stays published."
                    confirmLabel="Mark reviewed"
                    size="md"
                    variant="dark"
                    busy={busy}
                    onConfirm={() =>
                      run(
                        () => clearEventFlag(event.id),
                        "Review flag cleared",
                      )
                    }
                  />
                  <ConfirmAction
                    label="Reject"
                    title="Reject this event?"
                    description={`Take down “${event.title}”. The host receives your reason.`}
                    confirmLabel="Reject event"
                    tone="danger"
                    size="md"
                    busy={busy}
                    disabled={rejectReason.trim().length < 3}
                    onConfirm={() =>
                      run(
                        () => rejectEvent(event.id, rejectReason.trim()),
                        "Event rejected",
                      )
                    }
                  />
                </div>
              </div>
            ) : null}

            {event.status === "published" ? (
              <div className="border-t border-border pt-4">
                <ConfirmAction
                  label="Pause listing"
                  title="Pause this published event?"
                  description="Sales and public discovery pause until the event is resumed."
                  confirmLabel="Pause"
                  tone="danger"
                  size="md"
                  busy={busy}
                  onConfirm={() =>
                    run(() => pauseEvent(event.id), "Event paused")
                  }
                />
              </div>
            ) : null}

            {event.status === "paused" ? (
              <div className="border-t border-border pt-4">
                <ConfirmAction
                  label="Resume listing"
                  title="Resume this event?"
                  description="Restores the event to published status."
                  confirmLabel="Resume"
                  size="md"
                  busy={busy}
                  onConfirm={() =>
                    run(() => resumeEvent(event.id), "Event resumed")
                  }
                />
              </div>
            ) : null}

            <div className="space-y-3 border-t border-border pt-4">
              <Textarea
                label={flagged ? "Clear-flag note (optional)" : "Flag reason"}
                hint={
                  flagged
                    ? "Clearing removes the ops flag. Listing status is unchanged."
                    : "Flags mark the listing for follow-up without unpublishing it."
                }
                value={flagReason}
                onChange={(e) => setFlagReason(e.target.value)}
                placeholder={
                  flagged
                    ? "Optional note for the audit trail…"
                    : "Why does this listing need attention?"
                }
              />
              {flagged ? (
                <ConfirmAction
                  label="Clear flag"
                  title="Clear admin flag?"
                  description="Removes the ops flag from this listing."
                  confirmLabel="Clear flag"
                  size="md"
                  busy={busy}
                  onConfirm={() =>
                    run(
                      () => clearEventFlag(event.id, flagReason.trim() || undefined),
                      "Flag cleared",
                    )
                  }
                />
              ) : (
                <ConfirmAction
                  label="Flag listing"
                  title="Flag this event?"
                  description="Adds an admin flag for ops follow-up. Does not hide or unpublish the listing."
                  confirmLabel="Flag"
                  tone="danger"
                  size="md"
                  busy={busy}
                  disabled={flagReason.trim().length < 3}
                  onConfirm={() =>
                    run(
                      () => flagEvent(event.id, flagReason.trim()),
                      "Event flagged",
                    )
                  }
                />
              )}
            </div>
          </Card>
        </div>
      ) : null}
    </DashboardShell>
  );
}
