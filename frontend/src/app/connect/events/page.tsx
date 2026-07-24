"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ConnectShell } from "@/components/fan-connect/ConnectShell";
import {
  Alert,
  EmptyState,
  SkeletonLoader,
} from "@/components/ui";
import { ApiError } from "@/lib/api";
import { fetchConnectEvents } from "@/lib/fan-connect-api";
import type { ConnectEvent } from "@/lib/types/fan-connect";
import { formatDate } from "@/lib/format";

export default function ConnectEventsPage() {
  const [items, setItems] = useState<ConnectEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const data = await fetchConnectEvents();
        if (!active) return;
        setItems(data.items);
      } catch (err) {
        if (!active) return;
        setError(
          err instanceof ApiError ? err.detail : "Could not load connect events.",
        );
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <ConnectShell
      title="Events"
      description="Public-safe nights from your Passport that can unlock Fan Connect — attendee lists are never shown."
    >
      {loading ? <SkeletonLoader className="h-32" /> : null}
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {!loading && !error && items.length === 0 ? (
        <EmptyState
          title="No Connect nights yet"
          description="Check in at public events and turn on Fan Connect to see nights here."
        />
      ) : null}
      {!loading && items.length > 0 ? (
        <ul className="divide-y divide-border rounded-[var(--radius-lg)] border border-border bg-surface">
          {items.map((ev) => (
            <li
              key={ev.event_id}
              className="flex flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-5"
            >
              <div>
                <Link
                  href={ev.path}
                  className="font-semibold text-heading hover:text-primary"
                >
                  {ev.title}
                </Link>
                <p className="text-sm text-muted-foreground">
                  {[ev.city, ev.start_datetime ? formatDate(ev.start_datetime) : null]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <p className="text-sm text-muted-foreground">
                  {ev.suggestion_count === 1
                    ? "1 fan to meet"
                    : `${ev.suggestion_count} fans to meet`}
                </p>
                <Link
                  href={`/connect/suggestions?event=${ev.event_id}`}
                  className="text-sm font-semibold text-primary"
                >
                  View →
                </Link>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </ConnectShell>
  );
}
