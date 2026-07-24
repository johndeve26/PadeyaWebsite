"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { AdminEventBuyersNav } from "@/components/admin/AdminEventBuyersNav";
import { AdminEventBuyersPanel } from "@/components/admin/AdminEventBuyersPanel";
import { DashboardShell } from "@/components/layout/DashboardShell";
import { Alert, Button, SkeletonLoader } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchEventById } from "@/lib/events-api";
import type { EventItem } from "@/lib/types/events";

export default function AdminEventAttendeesPage() {
  const params = useParams<{ id: string }>();
  const [event, setEvent] = useState<EventItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const row = await fetchEventById(params.id);
        if (active) setEvent(row);
      } catch (err) {
        if (active) {
          setError(
            err instanceof ApiError ? err.detail : "Failed to load event",
          );
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [params.id]);

  return (
    <DashboardShell
      tone="soft"
      compact
      eyebrow="Admin"
      title={event ? `${event.title} · Attendees` : "Event attendees"}
      description="Checked-in ticket holders. Same export modes, permissions, and audit rules as buyers."
      actions={
        <Link href="/admin/events">
          <Button size="sm" variant="ghost">
            All events
          </Button>
        </Link>
      }
    >
      <AdminEventBuyersNav eventId={params.id} />
      {error ? (
        <Alert tone="danger" title="Something went wrong">
          {error}
        </Alert>
      ) : null}
      {!event ? (
        <SkeletonLoader lines={5} />
      ) : (
        <AdminEventBuyersPanel eventId={params.id} mode="attendees" />
      )}
    </DashboardShell>
  );
}
