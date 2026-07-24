"use client";

import { useRouter } from "next/navigation";

import { RestrictedActionNotice } from "@/components/account/RestrictedActionNotice";
import { EventStudio, type EventStudioValues } from "@/components/events/studio";
import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { useUserRestrictions } from "@/hooks/useUserRestrictions";
import { ApiError } from "@/lib/api";
import { createEvent, submitEvent } from "@/lib/events-api";

export default function NewEventPage() {
  const router = useRouter();
  const { has } = useUserRestrictions();
  const blocked = has("cannot_create_events");

  async function onSave(_values: EventStudioValues, payload: Record<string, unknown>) {
    try {
      return await createEvent(payload);
    } catch (err) {
      throw new Error(err instanceof ApiError ? err.detail : "Unable to create event");
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

  return (
    <RequireHost>
      <DashboardShell tone="soft" hideHeader>
        {blocked ? (
          <div className="mx-auto max-w-lg space-y-4 px-4 py-10">
            <RestrictedActionNotice />
          </div>
        ) : (
          <EventStudio
            mode="create"
            onSave={onSave}
            onSubmitReview={onSubmitReview}
          />
        )}
      </DashboardShell>
    </RequireHost>
  );
}
