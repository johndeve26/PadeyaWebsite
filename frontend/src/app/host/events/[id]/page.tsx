"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { StatusBadge } from "@/components/events/StatusBadge";
import { EventOpsNav } from "@/components/host/EventOpsNav";
import { HostEventPostponeModal } from "@/components/host/HostEventPostponeModal";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { ImageUrlOrUploadField } from "@/components/media/ImageUrlOrUploadField";
import {
  Alert,
  Button,
  ConfirmAction,
  Media,
  SkeletonLoader,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { formatDateTime } from "@/lib/format";
import {
  addEventMedia,
  archiveEvent,
  cancelEvent,
  completeEvent,
  discardEvent,
  fetchEventById,
  pauseEvent,
  restoreArchivedEvent,
  resumeEvent,
  submitEvent,
} from "@/lib/events-api";
import { resolveEventImage } from "@/lib/legacy-presentation";
import type { EventItem } from "@/lib/types/events";

function ActionPanel({
  title,
  hint,
  children,
  className,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow-soft)]",
        className,
      )}
    >
      <div className="border-b border-border bg-muted/50 px-5 py-4 padeya-stat-surface">
        <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
          {title}
        </p>
        {hint ? (
          <p className="mt-1 text-sm leading-snug text-muted-foreground">{hint}</p>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-2 p-5">{children}</div>
    </section>
  );
}

function MetaCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-subtle-foreground/80">
        {label}
      </p>
      <p className="mt-1 truncate text-sm font-semibold text-paper">{value}</p>
    </div>
  );
}

export default function HostEventDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const [event, setEvent] = useState<EventItem | null>(null);
  const [bannerUrl, setBannerUrl] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [postponeOpen, setPostponeOpen] = useState(false);

  useEffect(() => {
    void fetchEventById(params.id)
      .then(setEvent)
      .catch((err) => setError(err instanceof ApiError ? err.detail : "Not found"));
  }, [params.id]);

  async function onSubmitReview() {
    try {
      const updated = await submitEvent(params.id);
      setEvent(updated);
      setMessage("Submitted for review.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Submit failed");
    }
  }

  async function onComplete() {
    try {
      const updated = await completeEvent(params.id);
      setEvent(updated);
      setMessage("Event marked completed. Memory page created.");
      router.push(`/host/events/${params.id}/memory`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Complete failed");
    }
  }

  async function onPause() {
    setError(null);
    try {
      const updated = await pauseEvent(params.id);
      setEvent(updated);
      setMessage("Event paused — sales and listing are hidden from public browse.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Pause failed");
    }
  }

  async function onResume() {
    setError(null);
    try {
      const updated = await resumeEvent(params.id);
      setEvent(updated);
      setMessage("Event resumed and published again.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Resume failed");
    }
  }

  async function onCancel() {
    setError(null);
    try {
      const updated = await cancelEvent(params.id);
      setEvent(updated);
      setMessage("Event cancelled.");
      toast.push({ tone: "success", title: "Event cancelled" });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Cancel failed");
      throw err;
    }
  }

  async function onDiscard() {
    setError(null);
    try {
      await discardEvent(params.id);
      toast.push({ tone: "success", title: "Draft discarded" });
      router.push("/host/events");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Discard failed");
      throw err;
    }
  }

  async function onArchive() {
    setError(null);
    try {
      const updated = await archiveEvent(params.id);
      setEvent(updated);
      setMessage("Event archived.");
      toast.push({ tone: "success", title: "Event archived" });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Archive failed");
      throw err;
    }
  }

  async function onRestoreArchive() {
    setError(null);
    try {
      const updated = await restoreArchivedEvent(params.id);
      setEvent(updated);
      setMessage(
        updated.status === "draft"
          ? "Archived draft restored."
          : "Archived event restored to cancelled — edit or resubmit as needed.",
      );
      toast.push({ tone: "success", title: "Event restored" });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Restore failed");
      throw err;
    }
  }

  async function onAttachBanner() {
    try {
      const updated = await addEventMedia(params.id, {
        url: bannerUrl,
        media_type: "banner",
        set_as_banner: true,
      });
      setEvent(updated);
      setMessage("Banner attached.");
      setBannerUrl("");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Media update failed");
    }
  }

  if (error && !event) {
    return (
      <RequireHost>
        <DashboardShell
          tone="soft"
          eyebrow="Event"
          title="Unavailable"
          description={error}
        />
      </RequireHost>
    );
  }

  if (!event) {
    return (
      <RequireHost>
        <DashboardShell
          tone="soft"
          eyebrow="Event"
          title="Event details"
          description="Fetching event details."
        >
          <SkeletonLoader lines={6} />
        </DashboardShell>
      </RequireHost>
    );
  }

  const cover = resolveEventImage(event.slug, event.title, event.banner_url);
  const where =
    [event.venue_name, event.city].filter(Boolean).join(", ") || "Location TBA";
  const canPostpone = ["published", "paused"].includes(event.status);

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Event ops"
        title={event.title}
        description="Command center for listing, door, tickets, and insights."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={event.status} />
            <Link href="/host/events">
              <Button variant="secondary">All events</Button>
            </Link>
          </div>
        }
      >
        <EventOpsNav eventId={event.id} />
        {message ? (
          <Alert tone="success" title="Update saved">
            {message}
          </Alert>
        ) : null}
        {error ? (
          <Alert tone="danger" title="Something went wrong">
            {error}
          </Alert>
        ) : null}

        <article className="overflow-hidden rounded-[var(--radius-xl)] border border-border bg-ink text-paper shadow-[var(--shadow)]">
          <div className="relative aspect-[21/9] min-h-[200px] sm:min-h-[240px]">
            <Media
              src={cover}
              alt=""
              className="absolute inset-0 h-full w-full object-cover opacity-75"
            />
            <div
              aria-hidden
              className="absolute inset-0 bg-gradient-to-t from-ink via-ink/50 to-ink/10"
            />
            <div className="absolute inset-x-0 bottom-0 space-y-3 p-5 sm:p-7">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={event.status} />
                {event.short_tagline ? (
                  <span className="text-xs font-medium uppercase tracking-[0.14em] text-subtle-foreground">
                    {event.short_tagline}
                  </span>
                ) : null}
              </div>
              <h2 className="max-w-3xl text-balance text-2xl font-extrabold tracking-tight sm:text-4xl">
                {event.title}
              </h2>
              <p className="text-sm text-subtle-foreground sm:text-base">
                {formatDateTime(event.start_datetime)} · {where}
              </p>
            </div>
          </div>

          <div className="grid gap-4 border-t border-paper/10 bg-ink/90 px-5 py-4 sm:grid-cols-3 sm:px-7">
            <MetaCell
              label="When"
              value={`${formatDateTime(event.start_datetime)} → ${formatDateTime(event.end_datetime)}`}
            />
            <MetaCell
              label="Where"
              value={
                [event.venue_name, event.address, event.city]
                  .filter(Boolean)
                  .join(", ") || "TBA"
              }
            />
            <MetaCell
              label="Capacity"
              value={event.capacity != null ? String(event.capacity) : "—"}
            />
          </div>
        </article>

        <div className="grid gap-4 lg:grid-cols-2">
          <ActionPanel
            title="Manage listing"
            hint="Edit the page, tickets, and lifecycle — pause, postpone, or wrap the night."
          >
            <Button
              size="sm"
              variant="secondary"
              onClick={() =>
                window.open(
                  event.status === "published" && event.slug
                    ? `/events/${event.slug}`
                    : `/host/events/${event.id}/preview`,
                  "_blank",
                  "noopener,noreferrer",
                )
              }
            >
              View event
            </Button>
            <Link href={`/host/events/${event.id}/edit`}>
              <Button size="sm" variant="secondary">
                Open Event Studio
              </Button>
            </Link>
            <Link href={`/host/events/${event.id}/tickets`}>
              <Button size="sm" variant="dark">
                Ticket types
              </Button>
            </Link>
            {["draft", "rejected", "paused"].includes(event.status) ? (
              <ConfirmAction
                label="Submit for review"
                title="Submit this event for review?"
                description="Pàdéyá will review listing details before it goes live."
                confirmLabel="Submit for review"
                onConfirm={onSubmitReview}
              />
            ) : null}
            {event.status === "published" ? (
              <ConfirmAction
                label="Pause"
                title="Pause this published event?"
                description="Sales and public listing are hidden until you resume."
                confirmLabel="Pause event"
                onConfirm={onPause}
              />
            ) : null}
            {event.status === "paused" ? (
              <ConfirmAction
                label="Resume"
                title="Resume this event?"
                description="The listing becomes published again and sales reopen."
                confirmLabel="Resume"
                onConfirm={onResume}
              />
            ) : null}
            {event.status === "archived" ? (
              <ConfirmAction
                label="Restore"
                title="Restore this archived event?"
                description="Unused archives return to draft. Events that had sales restore to cancelled so you can manage history safely."
                confirmLabel="Restore"
                onConfirm={onRestoreArchive}
              />
            ) : null}
            {canPostpone ? (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setPostponeOpen(true)}
              >
                Postpone
              </Button>
            ) : null}
            {["published", "paused"].includes(event.status) ? (
              <Button size="sm" variant="dark" onClick={() => void onComplete()}>
                Mark completed
              </Button>
            ) : null}
            {["draft", "rejected", "pending_review", "published", "paused"].includes(
              event.status,
            ) ? (
              <ConfirmAction
                label="Cancel event"
                title="Cancel this event?"
                description="Cancellation is permanent for this listing. Use Pause for a temporary hold, or Postpone to move the date."
                confirmLabel="Cancel event"
                tone="danger"
                variant="ghost"
                onConfirm={onCancel}
              />
            ) : null}
            {["draft", "rejected"].includes(event.status) ? (
              <ConfirmAction
                label="Delete event"
                title="Delete this event permanently?"
                description="Only works for draft/rejected events with no sales. This cannot be undone."
                confirmLabel="Delete forever"
                tone="danger"
                variant="ghost"
                onConfirm={onDiscard}
              />
            ) : null}
            {event.status === "completed" ? (
              <Link href={`/host/events/${event.id}/memory`}>
                <Button size="sm">Event Memory</Button>
              </Link>
            ) : null}
            {["completed", "cancelled"].includes(event.status) ? (
              <ConfirmAction
                label="Archive"
                title="Archive this event?"
                description="Archived events leave the active host list but remain for history and reporting."
                confirmLabel="Archive"
                variant="ghost"
                onConfirm={onArchive}
              />
            ) : null}
          </ActionPanel>

          <ActionPanel
            title="Door & guests"
            hint="Run the door, review guests, and manage tables."
          >
            <Link href={`/host/events/${event.id}/check-in`}>
              <Button size="sm">Check-in</Button>
            </Link>
            <Link href={`/host/events/${event.id}/offline-check-in`}>
              <Button size="sm" variant="secondary">
                Offline check-in
              </Button>
            </Link>
            <Link href={`/host/events/${event.id}/attendees`}>
              <Button size="sm" variant="ghost">
                Attendees
              </Button>
            </Link>
            <Link href={`/host/events/${event.id}/tables`}>
              <Button size="sm" variant="ghost">
                Tables
              </Button>
            </Link>
          </ActionPanel>

          <ActionPanel
            title="Insights & tools"
            hint="Traffic, sales, and check-in performance for this night."
          >
            <Link href={`/host/events/${event.id}/analytics`}>
              <Button size="sm" variant="secondary">
                Analytics
              </Button>
            </Link>
            <Link href={`/host/events/${event.id}/check-in/analytics`}>
              <Button size="sm" variant="ghost">
                Check-in stats
              </Button>
            </Link>
            <Link href={`/host/events/${event.id}/ai`}>
              <Button size="sm" variant="ghost">
                AI Copilot
              </Button>
            </Link>
          </ActionPanel>

          <section className="overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card shadow-[var(--shadow-soft)]">
            <div className="border-b border-border bg-muted/50 px-5 py-4 padeya-stat-surface">
              <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-muted-foreground">
                Banner media
              </p>
              <p className="mt-1 text-sm leading-snug text-muted-foreground">
                Upload a banner image or paste a public URL.
              </p>
            </div>
            <div className="space-y-3 p-5">
              <ImageUrlOrUploadField
                label="Banner image"
                value={bannerUrl}
                onChange={setBannerUrl}
                eventId={params.id}
                mediaType="banner"
                setAsBanner
                previewClassName="h-14 w-28"
                onUploaded={async () => {
                  const updated = await fetchEventById(params.id);
                  setEvent(updated);
                  setBannerUrl("");
                  setMessage("Banner attached.");
                }}
              />
              <Button
                type="button"
                disabled={!bannerUrl.trim()}
                onClick={() => void onAttachBanner()}
              >
                Attach pasted URL
              </Button>
            </div>
          </section>
        </div>

        <section className="overflow-hidden rounded-[var(--radius-xl)] border border-border bg-card p-5 shadow-[var(--shadow-soft)] sm:p-7">
          <h3 className="text-lg font-extrabold tracking-tight text-foreground">
            About this night
          </h3>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground sm:text-base">
            {event.description}
          </p>
          {event.rejection_reason ? (
            <div className="mt-4">
              <Alert tone="danger" title="Rejected">
                {event.rejection_reason}
              </Alert>
            </div>
          ) : null}
        </section>

        {canPostpone ? (
          <HostEventPostponeModal
            key={`${event.id}-${event.start_datetime}-${event.end_datetime}`}
            open={postponeOpen}
            event={event}
            onClose={() => setPostponeOpen(false)}
            onPostponed={(updated) => {
              setEvent(updated);
              setMessage("Event postponed to the new dates.");
              toast.push({ tone: "success", title: "Event postponed" });
            }}
          />
        ) : null}
      </DashboardShell>
    </RequireHost>
  );
}
