"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { EventPublicView } from "@/components/events/EventPublicView";
import { RequireHost } from "@/components/hosts/RequireHost";
import {
  Button,
  Container,
  EmptyState,
  SkeletonCard,
} from "@/components/ui";
import { asGuestPublicEvent } from "@/lib/event-privacy";
import { fetchEventById } from "@/lib/events-api";
import type { EventItem } from "@/lib/types/events";

export default function HostEventPreviewPage() {
  const params = useParams<{ id: string }>();
  const [event, setEvent] = useState<EventItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void fetchEventById(params.id)
      .then((item) => {
        if (active) setEvent(item);
      })
      .catch(() => {
        if (active) setError("Unable to load this event preview.");
      });
    return () => {
      active = false;
    };
  }, [params.id]);

  const guestEvent = useMemo(
    () => (event ? asGuestPublicEvent(event) : null),
    [event],
  );

  return (
    <RequireHost>
      {error ? (
        <main className="bg-background py-20">
          <Container width="narrow">
            <EmptyState
              title="Preview unavailable"
              description={error}
              action={
                <Link href={`/host/events/${params.id}/edit`}>
                  <Button variant="secondary">Back to editor</Button>
                </Link>
              }
            />
          </Container>
        </main>
      ) : !guestEvent ? (
        <main className="bg-background">
          <div className="h-[42vh] animate-pulse bg-surface-dark sm:h-[52vh]" />
          <Container className="grid gap-6 py-10 lg:grid-cols-[minmax(0,1fr)_320px]">
            <div className="space-y-4">
              <SkeletonCard />
              <SkeletonCard />
            </div>
            <SkeletonCard />
          </Container>
        </main>
      ) : (
        <EventPublicView event={guestEvent} previewMode />
      )}
    </RequireHost>
  );
}
