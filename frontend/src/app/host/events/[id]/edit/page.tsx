"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  EventStudio,
  eventToStudioValues,
  type EventStudioValues,
} from "@/components/events/studio";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import {
  approveEvent,
  archiveEvent,
  discardEvent,
  fetchEventById,
  submitEvent,
  updateEvent,
} from "@/lib/events-api";
import type { EventItem } from "@/lib/types/events";

export default function EditEventPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [event, setEvent] = useState<EventItem | null>(null);

  useEffect(() => {
    void fetchEventById(params.id).then(setEvent);
  }, [params.id]);

  async function onSave(_values: EventStudioValues, payload: Record<string, unknown>) {
    try {
      const updated = await updateEvent(params.id, payload);
      setEvent(updated);
      return updated;
    } catch (err) {
      throw new Error(err instanceof ApiError ? err.detail : "Unable to update event");
    }
  }

  async function onSubmitReview(eventId: string) {
    try {
      await submitEvent(eventId);
      router.push(`/host/events/${eventId}`);
    } catch (err) {
      throw new Error(err instanceof ApiError ? err.detail : "Unable to submit event");
    }
  }

  async function onPublish(eventId: string) {
    try {
      // Approve publishes pending_review; for drafts submit then approve.
      const current = await fetchEventById(eventId);
      if (current.status === "draft" || current.status === "rejected") {
        await submitEvent(eventId);
      }
      await approveEvent(eventId);
      router.push(`/host/events/${eventId}`);
    } catch (err) {
      throw new Error(err instanceof ApiError ? err.detail : "Unable to publish event");
    }
  }

  async function onArchiveDraft(eventId: string) {
    try {
      await archiveEvent(eventId);
      router.push("/host/events");
    } catch (err) {
      throw new Error(err instanceof ApiError ? err.detail : "Unable to archive draft");
    }
  }

  async function onDeleteDraft(eventId: string) {
    try {
      await discardEvent(eventId);
      router.push("/host/events");
    } catch (err) {
      throw new Error(err instanceof ApiError ? err.detail : "Unable to delete draft");
    }
  }

  return (
    <RequireHost>
      <DashboardShell tone="soft" hideHeader>
        {event ? (
          <EventStudio
            key={event.id}
            mode="edit"
            eventId={event.id}
            eventStatus={event.status}
            initial={eventToStudioValues(event)}
            checklist={event.publish_checklist}
            onSave={onSave}
            onSubmitReview={onSubmitReview}
            onPublish={onPublish}
            onArchiveDraft={onArchiveDraft}
            onDeleteDraft={onDeleteDraft}
          />
        ) : (
          <div className="max-w-3xl">
            <SkeletonLoader lines={10} />
          </div>
        )}
      </DashboardShell>
    </RequireHost>
  );
}
