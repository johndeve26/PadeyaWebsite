"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { EligibleEventsGrid } from "@/components/ambassadors/EligibleEventsGrid";
import { Button, Container, SkeletonLoader } from "@/components/ui";
import { fetchEligibleAmbassadorEvents } from "@/lib/promos-api";
import type { EligibleAmbassadorEvent } from "@/lib/types/promos";

export default function AmbassadorsEventsPage() {
  const [events, setEvents] = useState<EligibleAmbassadorEvent[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const rows = await fetchEligibleAmbassadorEvents();
        if (active) {
          setEvents(rows);
          setError(null);
        }
      } catch {
        if (active) {
          setEvents([]);
          setError("Could not load ambassador-eligible events");
        }
      } finally {
        if (active) setLoaded(true);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="min-w-0 bg-surface py-10 sm:py-14">
      <Container className="space-y-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-muted-foreground">
              Pàdéyá Ambassadors
            </p>
            <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-heading sm:text-4xl">
              Ambassador-eligible events
            </h1>
            <p className="mt-2 max-w-xl text-body">
              These events have open Ambassadors enabled. Click Promote this event,
              accept terms, and get your unique Ambassador link.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/ambassadors/how-it-works">
              <Button size="sm" variant="secondary">
                How it works
              </Button>
            </Link>
            <Link href="/dashboard/ambassador">
              <Button size="sm">My dashboard</Button>
            </Link>
          </div>
        </div>

        {error ? <p className="text-sm text-danger">{error}</p> : null}
        {!loaded ? <SkeletonLoader lines={6} /> : <EligibleEventsGrid events={events} />}
      </Container>
    </main>
  );
}
