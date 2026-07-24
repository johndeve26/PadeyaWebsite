"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RequireHost } from "@/components/hosts/RequireHost";
import { DashboardShell } from "@/components/layout/DashboardShell";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchMyEvents } from "@/lib/events-api";
import { formatDate } from "@/lib/format";
import type { EventItem } from "@/lib/types/events";

export default function HostMerchandiseFulfillmentHubPage() {
  const [events, setEvents] = useState<EventItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const rows = await fetchMyEvents();
        if (active) setEvents(rows);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load events",
          );
          setEvents([]);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <RequireHost>
      <DashboardShell
        tone="soft"
        eyebrow="Merch Studio"
        title="Fulfillment desks"
        description="Jump into an event pickup desk to scan QR codes and mark items fulfilled. Standalone shop items without an event use your product list and buyer order status."
        actions={
          <div className="flex flex-wrap gap-2">
            <Link href="/host/merchandise">
              <Button variant="secondary" size="sm">
                All merch
              </Button>
            </Link>
            <Link href="/host/merchandise/orders">
              <Button variant="secondary" size="sm">
                Orders hub
              </Button>
            </Link>
          </div>
        }
      >
        {error ? (
          <Alert tone="danger" title="Could not load events">
            {error}
          </Alert>
        ) : null}

        <Card className="space-y-4">
          {events === null ? (
            <SkeletonLoader lines={4} />
          ) : events.length === 0 ? (
            <EmptyState
              title="No fulfillment desks yet"
              description="Event-linked merch gets a dedicated fulfillment desk. Create an event or publish standalone merch from Merch Studio."
              action={
                <div className="flex flex-wrap justify-center gap-2">
                  <Link href="/host/events/new">
                    <Button size="sm">Create event</Button>
                  </Link>
                  <Link href="/host/merchandise/new">
                    <Button size="sm" variant="secondary">
                      Add standalone merch
                    </Button>
                  </Link>
                </div>
              }
            />
          ) : (
            <ul className="divide-y divide-border">
              {events.map((event) => (
                <li
                  key={event.id}
                  className="flex flex-wrap items-center justify-between gap-3 py-3"
                >
                  <div>
                    <p className="font-extrabold text-foreground">
                      {event.title}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {formatDate(event.start_datetime)} · {event.status}
                    </p>
                  </div>
                  <Link
                    href={`/host/events/${event.id}/merchandise/fulfillment`}
                  >
                    <Button size="sm">Open desk</Button>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </DashboardShell>
    </RequireHost>
  );
}
